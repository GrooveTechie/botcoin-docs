# Hotel Deal Negotiator

A minimal MVP application to help you email hotels to request better direct-booking deals, with **STRICT human approval before sending**.

## Features

- 🏨 **Trip Management**: Create trips with destination, dates, budget, and notes
- 🎯 **Hotel Targets**: Add multiple hotels per trip with contact emails
- ✉️ **Draft Generation**: AI-powered (pluggable LLM) email drafts
- ✅ **Human Approval**: Drafts MUST be approved before sending
- 📤 **Gmail Integration**: OAuth-based sending via Gmail API
- 📬 **Reply Tracking**: Check inbox for hotel responses
- 🔄 **Follow-up Generator**: Create polite follow-up emails (with approval)

## Stack

- **Backend**: Python 3.12, FastAPI
- **Database**: SQLite
- **Frontend**: Server-rendered HTML (Jinja2)
- **Email**: Gmail API (OAuth, NOT SMTP)

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd hotel-deal-negotiator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or
make install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

### 3. Set Up Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the JSON file
5. Save as `./secrets/client_secret.json`

**Required Scopes**:
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.readonly`

### 4. Seed Example Data (Optional)

```bash
python seed.py
# or
make seed
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload
# or
make dev
```

Visit: **http://localhost:8000**

### 6. First Gmail Authorization

When you first try to send an email, you'll be prompted to authorize via Google OAuth. A browser window will open for authentication. The token is saved in `./secrets/token.json`.

## Docker

### Build and Run

```bash
# Build image
docker build -t hotel-deal-negotiator .
# or
make docker-build

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/data:/app/data \
  hotel-deal-negotiator
# or
make docker-run
```

## Usage

### Workflow

1. **Create a Trip** at `/trips`
   - Enter destination, check-in/out dates, adults, budget

2. **Add Hotel Targets** at `/trips/{id}`
   - Name, contact email, website (optional), room type (optional)

3. **Generate Drafts** at `/trips/{id}/drafts`
   - Click "Generate Drafts" to create email drafts for all hotels

4. **Review & Approve** each draft
   - Read the generated email
   - Click "✓ Approve" to mark it ready for sending
   - Or "Skip" to skip this hotel

5. **Send Approved Emails**
   - Only approved drafts show the "📤 Send Email" button
   - Sends via Gmail API

6. **Track Responses** at `/threads`
   - Click "🔄 Check Inbox" to pull replies
   - See which hotels have responded

7. **Generate Follow-ups** for sent emails
   - Click "Generate Follow-up" on sent drafts
   - New follow-up requires approval before sending

## API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/trips` | List all trips |
| POST | `/api/trips` | Create a trip |
| GET | `/api/trips/{id}` | Get trip details |
| GET | `/api/trips/{id}/hotels` | List hotels for trip |
| POST | `/api/hotels` | Add a hotel target |
| POST | `/api/drafts/generate/{trip_id}` | Generate drafts for trip |
| GET | `/api/trips/{trip_id}/drafts` | List drafts for trip |
| POST | `/api/drafts/{id}/approve` | Approve a draft |
| POST | `/api/drafts/{id}/send` | Send approved draft |
| POST | `/api/drafts/{id}/skip` | Skip a draft |
| POST | `/api/drafts/{id}/generate-followup` | Generate follow-up |
| GET | `/api/threads` | List all email threads |
| POST | `/api/threads/check` | Check for replies |

## UI Pages

- `/trips` - Trip list and create form
- `/trips/{id}` - Trip details and hotel targets
- `/trips/{id}/drafts` - Draft queue (approve/send/skip)
- `/threads` - Email thread tracking

## Safety Rules

The following rules are **enforced server-side**:

1. **Human Approval Required**: Drafts start in "Draft" status and MUST be approved before sending
2. **No Competitor Claims**: Email templates never claim competitor offers (safety rule)
3. **Send Throttling**: Minimum 10 seconds between sends
4. **Follow-up Limit**: Maximum 1 follow-up per thread (configurable via `MAX_FOLLOWUPS_PER_THREAD`)

## Data Model

```sql
trips(id, destination, check_in, check_out, adults, budget, notes, created_at)
hotels(id, trip_id, name, website, contact_email, room_type, created_at)
drafts(id, hotel_id, subject, body, status, created_at, approved_at, sent_at, thread_id)
threads(id, draft_id, gmail_thread_id, gmail_message_id, last_checked_at, last_snippet, has_reply, followup_count)
```

**Draft Status Flow**: `Draft` → `Approved` → `Sent` (or `Skipped`)

## LLM Integration

The app uses a pluggable `LLMClient` interface:

```python
from app.services import get_llm_client

# Default: Stub client (template-based, no external API)
client = get_llm_client(provider="stub")

# Future: OpenAI integration
client = get_llm_client(provider="openai", api_key="sk-...")
```

To implement a custom LLM:

1. Extend `LLMClient` in `app/services/llm_client.py`
2. Implement `generate_initial_email()` and `generate_followup_email()`
3. Update the factory function `get_llm_client()`

## Tests

```bash
pytest tests/ -v
# or
make test
```

Tests cover:
- Draft approval flow
- Send gating (only approved drafts can be sent)
- Follow-up count limits
- Email template generation

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/hotel_deals.db` | Database path |
| `GOOGLE_CLIENT_SECRET_FILE` | `./secrets/client_secret.json` | Gmail OAuth credentials |
| `GOOGLE_TOKEN_FILE` | `./secrets/token.json` | OAuth token storage |
| `MIN_SEND_INTERVAL_SECONDS` | `10` | Throttle between sends |
| `MAX_FOLLOWUPS_PER_THREAD` | `1` | Max follow-ups allowed |
| `LLM_PROVIDER` | `stub` | LLM provider (stub/openai) |
| `OPENAI_API_KEY` | - | OpenAI API key (if using) |

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLite operations
│   ├── models.py            # Data models
│   ├── routes/
│   │   ├── trips.py         # Trip endpoints
│   │   ├── hotels.py        # Hotel endpoints
│   │   ├── drafts.py        # Draft endpoints
│   │   └── threads.py       # Thread endpoints
│   ├── services/
│   │   ├── llm_client.py    # LLM interface
│   │   └── gmail_service.py # Gmail API service
│   └── templates/           # Jinja2 HTML templates
├── tests/
│   ├── test_draft_approval.py
│   └── test_llm_client.py
├── secrets/                 # OAuth credentials (gitignored)
├── data/                    # SQLite database (gitignored)
├── seed.py                  # Example data script
├── Dockerfile
├── Makefile
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
