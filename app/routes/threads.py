"""Thread routes for Hotel Deal Negotiator."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import db
from app.services import get_gmail_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class ThreadResponse(BaseModel):
    id: int
    draft_id: int
    gmail_thread_id: str
    gmail_message_id: str
    last_checked_at: Optional[str]
    last_snippet: Optional[str]
    has_reply: bool
    followup_count: int


class CheckThreadsResponse(BaseModel):
    checked: int
    with_replies: int
    errors: List[str]


# API Routes
@router.get("/api/threads", response_model=List[ThreadResponse])
async def get_threads_api():
    """Get all threads."""
    threads = await db.get_all_threads()
    return [
        ThreadResponse(
            id=t.id,
            draft_id=t.draft_id,
            gmail_thread_id=t.gmail_thread_id,
            gmail_message_id=t.gmail_message_id,
            last_checked_at=str(t.last_checked_at) if t.last_checked_at else None,
            last_snippet=t.last_snippet,
            has_reply=t.has_reply,
            followup_count=t.followup_count
        )
        for t in threads
    ]


@router.get("/api/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread_api(thread_id: int):
    """Get a specific thread."""
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadResponse(
        id=thread.id,
        draft_id=thread.draft_id,
        gmail_thread_id=thread.gmail_thread_id,
        gmail_message_id=thread.gmail_message_id,
        last_checked_at=str(thread.last_checked_at) if thread.last_checked_at else None,
        last_snippet=thread.last_snippet,
        has_reply=thread.has_reply,
        followup_count=thread.followup_count
    )


@router.post("/api/threads/check", response_model=CheckThreadsResponse)
async def check_threads_api():
    """Check all sent threads for replies."""
    threads = await db.get_all_threads()
    
    if not threads:
        return CheckThreadsResponse(checked=0, with_replies=0, errors=[])
    
    try:
        gmail = get_gmail_service()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gmail not configured: {str(e)}"
        )
    
    checked = 0
    with_replies = 0
    errors = []
    
    for thread in threads:
        try:
            has_reply, snippet = gmail.check_for_reply(
                thread.gmail_thread_id,
                thread.gmail_message_id
            )
            
            await db.update_thread_reply(thread.id, snippet or "", has_reply)
            checked += 1
            
            if has_reply:
                with_replies += 1
                
        except Exception as e:
            errors.append(f"Thread {thread.id}: {str(e)}")
    
    return CheckThreadsResponse(
        checked=checked,
        with_replies=with_replies,
        errors=errors
    )


# HTML UI Routes
@router.get("/threads", response_class=HTMLResponse)
async def threads_page(request: Request):
    """Display all threads with their info."""
    threads_info = await db.get_all_threads_with_info()
    
    # Check Gmail status
    gmail_configured = False
    try:
        gmail = get_gmail_service()
        gmail_configured = gmail.is_authenticated()
    except Exception:
        pass
    
    return templates.TemplateResponse(
        "threads.html",
        {
            "request": request,
            "threads": threads_info,
            "gmail_configured": gmail_configured
        }
    )


@router.post("/threads/check", response_class=HTMLResponse)
async def check_threads_form(request: Request):
    """Check threads from form submission."""
    await check_threads_api()
    return RedirectResponse(url="/threads", status_code=303)
