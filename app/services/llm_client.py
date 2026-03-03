"""LLM Client interface and implementations for generating email drafts."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailDraft:
    subject: str
    body: str


@dataclass
class HotelContext:
    hotel_name: str
    destination: str
    check_in: str
    check_out: str
    adults: int
    budget: Optional[float]
    room_type: Optional[str]
    notes: Optional[str]


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def generate_initial_email(self, context: HotelContext) -> EmailDraft:
        """Generate initial negotiation email for a hotel."""
        pass
    
    @abstractmethod
    async def generate_followup_email(
        self, 
        context: HotelContext, 
        previous_subject: str,
        previous_body: str,
        reply_snippet: Optional[str] = None
    ) -> EmailDraft:
        """Generate a follow-up email for a hotel."""
        pass


class StubLLMClient(LLMClient):
    """
    Stub LLM client that uses templates for MVP.
    No external API required - generates emails from templates.
    """
    
    async def generate_initial_email(self, context: HotelContext) -> EmailDraft:
        """Generate initial negotiation email using templates."""
        
        # Format dates nicely
        nights = self._calculate_nights(context.check_in, context.check_out)
        
        # Build room type string
        room_info = f" for a {context.room_type}" if context.room_type else ""
        
        # Build budget string (never claim competitor offers per safety rules)
        budget_line = ""
        if context.budget:
            budget_line = f"\n\nOur budget for accommodations is approximately ${context.budget:.0f} for the stay."
        
        subject = f"Direct Booking Inquiry - {context.check_in} to {context.check_out}"
        
        body = f"""Dear {context.hotel_name} Reservations Team,

I am planning a trip to {context.destination} and am interested in booking directly with your hotel{room_info}.

Trip Details:
- Check-in: {context.check_in}
- Check-out: {context.check_out}
- Duration: {nights} night(s)
- Guests: {context.adults} adult(s)
{budget_line}

I am reaching out directly because I prefer to book with hotels rather than through third-party sites. I would appreciate if you could share any special rates, packages, or perks available for direct bookings.

I am flexible on room category and would be happy to discuss options that work within my budget.

Thank you for your time, and I look forward to hearing from you.

Best regards"""
        
        return EmailDraft(subject=subject, body=body)
    
    async def generate_followup_email(
        self, 
        context: HotelContext, 
        previous_subject: str,
        previous_body: str,
        reply_snippet: Optional[str] = None
    ) -> EmailDraft:
        """Generate a polite, short follow-up email."""
        
        subject = f"Re: {previous_subject}"
        
        if reply_snippet:
            # They replied, so this is a continuation
            body = f"""Dear {context.hotel_name} Team,

Thank you for your response. I wanted to follow up on my inquiry about direct booking rates for {context.check_in} to {context.check_out}.

Would you be able to share any updated availability or rates?

Thank you for your assistance.

Best regards"""
        else:
            # No reply yet - gentle reminder
            body = f"""Dear {context.hotel_name} Team,

I hope this message finds you well. I wanted to follow up on my earlier inquiry about direct booking rates for my stay from {context.check_in} to {context.check_out}.

I remain very interested in booking with your property and would appreciate any information about available rates or packages.

Thank you for your time.

Best regards"""
        
        return EmailDraft(subject=subject, body=body)
    
    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates."""
        from datetime import datetime
        try:
            ci = datetime.strptime(check_in, "%Y-%m-%d")
            co = datetime.strptime(check_out, "%Y-%m-%d")
            return (co - ci).days
        except ValueError:
            return 1


class OpenAILLMClient(LLMClient):
    """
    OpenAI-based LLM client for more sophisticated email generation.
    
    To use this client:
    1. Set OPENAI_API_KEY in .env
    2. Set LLM_PROVIDER=openai in .env
    
    This is a placeholder implementation - wire up actual OpenAI calls as needed.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def generate_initial_email(self, context: HotelContext) -> EmailDraft:
        """
        Generate initial email using OpenAI.
        
        TODO: Implement actual OpenAI API call. For now, falls back to template.
        """
        # Placeholder - would use openai library here
        # Example prompt structure:
        # "Generate a professional, friendly email to {hotel_name} requesting..."
        
        # For now, use template as fallback
        stub = StubLLMClient()
        return await stub.generate_initial_email(context)
    
    async def generate_followup_email(
        self, 
        context: HotelContext, 
        previous_subject: str,
        previous_body: str,
        reply_snippet: Optional[str] = None
    ) -> EmailDraft:
        """
        Generate follow-up email using OpenAI.
        
        TODO: Implement actual OpenAI API call. For now, falls back to template.
        """
        stub = StubLLMClient()
        return await stub.generate_followup_email(context, previous_subject, previous_body, reply_snippet)


def get_llm_client(provider: str = "stub", api_key: Optional[str] = None) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        provider: "stub" or "openai"
        api_key: Required if provider is "openai"
    
    Returns:
        LLMClient instance
    """
    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI API key required for 'openai' provider")
        return OpenAILLMClient(api_key)
    
    return StubLLMClient()
