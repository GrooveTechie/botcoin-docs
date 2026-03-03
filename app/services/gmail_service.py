"""Gmail service for sending and reading emails via OAuth."""
import base64
import os
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# Minimal scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]


class GmailService:
    """
    Gmail API service for sending and reading emails.
    
    Uses OAuth 2.0 for authentication. Requires:
    1. client_secret.json from Google Cloud Console
    2. User authorization (first run will open browser)
    
    Tokens are stored in the secrets directory.
    """
    
    def __init__(
        self, 
        client_secret_file: str = "./secrets/client_secret.json",
        token_file: str = "./secrets/token.json"
    ):
        self.client_secret_file = client_secret_file
        self.token_file = token_file
        self._service = None
        self._last_send_time: Optional[datetime] = None
        self._min_send_interval = timedelta(seconds=10)  # Safety throttle
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secret_file):
                    raise FileNotFoundError(
                        f"Client secret file not found: {self.client_secret_file}\n"
                        "Please download from Google Cloud Console and save to ./secrets/client_secret.json"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            Path(self.token_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def _get_service(self):
        """Get or create Gmail API service."""
        if not self._service:
            creds = self._get_credentials()
            self._service = build('gmail', 'v1', credentials=creds)
        return self._service
    
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        try:
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                return creds and creds.valid
            return False
        except Exception:
            return False
    
    def get_auth_url(self) -> str:
        """
        Start OAuth flow and return authorization URL.
        
        Note: For local development, run_local_server() is used instead.
        This method is for reference if you need to implement a different auth flow.
        """
        if not os.path.exists(self.client_secret_file):
            raise FileNotFoundError(
                f"Client secret file not found: {self.client_secret_file}"
            )
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.client_secret_file, SCOPES
        )
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url
    
    def _check_throttle(self) -> bool:
        """Check if enough time has passed since last send."""
        if self._last_send_time is None:
            return True
        
        elapsed = datetime.now(timezone.utc) - self._last_send_time
        return elapsed >= self._min_send_interval
    
    def get_time_until_next_send(self) -> int:
        """Get seconds until next send is allowed."""
        if self._last_send_time is None:
            return 0
        
        elapsed = datetime.now(timezone.utc) - self._last_send_time
        remaining = self._min_send_interval - elapsed
        
        if remaining.total_seconds() <= 0:
            return 0
        return int(remaining.total_seconds()) + 1
    
    def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str,
        thread_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Send an email via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional Gmail thread ID for replies
        
        Returns:
            Tuple of (gmail_thread_id, gmail_message_id)
        
        Raises:
            RuntimeError: If throttle limit not met
            Exception: If Gmail API fails
        """
        if not self._check_throttle():
            wait_time = self.get_time_until_next_send()
            raise RuntimeError(
                f"Send throttle active. Please wait {wait_time} seconds before sending."
            )
        
        service = self._get_service()
        
        # Create MIME message
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        # Encode to base64url
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Build request body
        body_data = {'raw': raw}
        if thread_id:
            body_data['threadId'] = thread_id
        
        # Send message
        result = service.users().messages().send(
            userId='me',
            body=body_data
        ).execute()
        
        # Update last send time for throttling
        self._last_send_time = datetime.now(timezone.utc)
        
        return result.get('threadId'), result.get('id')
    
    def get_thread(self, thread_id: str) -> dict:
        """
        Get a Gmail thread by ID.
        
        Returns:
            Thread data including messages and snippets
        """
        service = self._get_service()
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='metadata'
        ).execute()
        return thread
    
    def check_for_reply(self, thread_id: str, original_message_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a thread has received a reply.
        
        Args:
            thread_id: Gmail thread ID
            original_message_id: ID of the message we sent
        
        Returns:
            Tuple of (has_reply, latest_snippet)
        """
        try:
            thread = self.get_thread(thread_id)
            messages = thread.get('messages', [])
            
            if len(messages) <= 1:
                # Only our message, no reply
                return False, thread.get('snippet')
            
            # Check if there are messages after ours
            found_our_message = False
            latest_snippet = thread.get('snippet')
            
            for msg in messages:
                if msg.get('id') == original_message_id:
                    found_our_message = True
                elif found_our_message:
                    # This is a reply after our message
                    return True, latest_snippet
            
            return False, latest_snippet
            
        except Exception as e:
            # Thread might not exist or be accessible
            return False, f"Error checking thread: {str(e)}"


# Global Gmail service instance (lazy initialization)
_gmail_service: Optional[GmailService] = None


def get_gmail_service() -> GmailService:
    """Get or create Gmail service singleton."""
    global _gmail_service
    
    if _gmail_service is None:
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET_FILE', './secrets/client_secret.json')
        token_file = os.getenv('GOOGLE_TOKEN_FILE', './secrets/token.json')
        _gmail_service = GmailService(client_secret, token_file)
    
    return _gmail_service
