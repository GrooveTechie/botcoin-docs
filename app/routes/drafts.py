"""Draft routes for Hotel Deal Negotiator."""
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import db
from app.models import Draft, DraftStatus
from app.services import get_llm_client, HotelContext, get_gmail_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class DraftResponse(BaseModel):
    id: int
    hotel_id: int
    subject: str
    body: str
    status: str
    created_at: Optional[str]
    approved_at: Optional[str]
    sent_at: Optional[str]
    thread_id: Optional[int]


class GenerateDraftsResponse(BaseModel):
    generated: int
    drafts: List[DraftResponse]


class SendResponse(BaseModel):
    success: bool
    thread_id: Optional[int]
    gmail_thread_id: Optional[str]
    gmail_message_id: Optional[str]
    error: Optional[str] = None


# API Routes
@router.post("/api/drafts/generate/{trip_id}", response_model=GenerateDraftsResponse)
async def generate_drafts_api(trip_id: int):
    """Generate drafts for all hotels without drafts in a trip."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get hotels without drafts
    hotels = await db.get_hotels_without_draft(trip_id)
    
    if not hotels:
        return GenerateDraftsResponse(generated=0, drafts=[])
    
    # Get LLM client
    provider = os.getenv('LLM_PROVIDER', 'stub')
    api_key = os.getenv('OPENAI_API_KEY')
    llm = get_llm_client(provider, api_key)
    
    generated_drafts = []
    
    for hotel in hotels:
        context = HotelContext(
            hotel_name=hotel.name,
            destination=trip.destination,
            check_in=trip.check_in,
            check_out=trip.check_out,
            adults=trip.adults,
            budget=trip.budget,
            room_type=hotel.room_type,
            notes=trip.notes
        )
        
        email = await llm.generate_initial_email(context)
        
        draft = Draft(
            id=None,
            hotel_id=hotel.id,
            subject=email.subject,
            body=email.body,
            status=DraftStatus.DRAFT
        )
        
        draft_id = await db.create_draft(draft)
        created_draft = await db.get_draft(draft_id)
        
        generated_drafts.append(DraftResponse(
            id=created_draft.id,
            hotel_id=created_draft.hotel_id,
            subject=created_draft.subject,
            body=created_draft.body,
            status=created_draft.status.value,
            created_at=str(created_draft.created_at) if created_draft.created_at else None,
            approved_at=str(created_draft.approved_at) if created_draft.approved_at else None,
            sent_at=str(created_draft.sent_at) if created_draft.sent_at else None,
            thread_id=created_draft.thread_id
        ))
    
    return GenerateDraftsResponse(generated=len(generated_drafts), drafts=generated_drafts)


@router.get("/api/trips/{trip_id}/drafts", response_model=List[DraftResponse])
async def get_drafts_api(trip_id: int):
    """Get all drafts for a trip."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    drafts = await db.get_drafts_by_trip(trip_id)
    return [
        DraftResponse(
            id=d.id,
            hotel_id=d.hotel_id,
            subject=d.subject,
            body=d.body,
            status=d.status.value,
            created_at=str(d.created_at) if d.created_at else None,
            approved_at=str(d.approved_at) if d.approved_at else None,
            sent_at=str(d.sent_at) if d.sent_at else None,
            thread_id=d.thread_id
        )
        for d in drafts
    ]


@router.get("/api/drafts/{draft_id}", response_model=DraftResponse)
async def get_draft_api(draft_id: int):
    """Get a specific draft."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return DraftResponse(
        id=draft.id,
        hotel_id=draft.hotel_id,
        subject=draft.subject,
        body=draft.body,
        status=draft.status.value,
        created_at=str(draft.created_at) if draft.created_at else None,
        approved_at=str(draft.approved_at) if draft.approved_at else None,
        sent_at=str(draft.sent_at) if draft.sent_at else None,
        thread_id=draft.thread_id
    )


@router.post("/api/drafts/{draft_id}/approve")
async def approve_draft_api(draft_id: int):
    """Approve a draft for sending."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.status != DraftStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve draft in '{draft.status.value}' status. Only 'Draft' status drafts can be approved."
        )
    
    success = await db.approve_draft(draft_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve draft")
    
    return {"success": True, "status": DraftStatus.APPROVED.value}


@router.post("/api/drafts/{draft_id}/send", response_model=SendResponse)
async def send_draft_api(draft_id: int):
    """Send an approved draft via Gmail."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # CRITICAL: Only approved drafts can be sent
    if draft.status != DraftStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send draft in '{draft.status.value}' status. Only 'Approved' status drafts can be sent."
        )
    
    # Get hotel info for email recipient
    draft_info = await db.get_draft_with_hotel(draft_id)
    if not draft_info:
        raise HTTPException(status_code=404, detail="Draft info not found")
    
    try:
        gmail = get_gmail_service()
        
        # Check throttle
        wait_time = gmail.get_time_until_next_send()
        if wait_time > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Send throttle active. Please wait {wait_time} seconds."
            )
        
        # Send email
        gmail_thread_id, gmail_message_id = gmail.send_email(
            to=draft_info['contact_email'],
            subject=draft.subject,
            body=draft.body
        )
        
        # Create thread record
        from app.models import Thread
        thread = Thread(
            id=None,
            draft_id=draft_id,
            gmail_thread_id=gmail_thread_id,
            gmail_message_id=gmail_message_id
        )
        thread_id = await db.create_thread(thread)
        
        # Mark draft as sent
        await db.mark_draft_sent(draft_id, thread_id)
        
        return SendResponse(
            success=True,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            gmail_message_id=gmail_message_id
        )
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gmail not configured: {str(e)}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        return SendResponse(
            success=False,
            thread_id=None,
            gmail_thread_id=None,
            gmail_message_id=None,
            error=str(e)
        )


@router.post("/api/drafts/{draft_id}/skip")
async def skip_draft_api(draft_id: int):
    """Skip a draft (won't be sent)."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.status not in [DraftStatus.DRAFT, DraftStatus.APPROVED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot skip draft in '{draft.status.value}' status"
        )
    
    success = await db.skip_draft(draft_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to skip draft")
    
    return {"success": True, "status": DraftStatus.SKIPPED.value}


@router.post("/api/drafts/{draft_id}/generate-followup", response_model=DraftResponse)
async def generate_followup_api(draft_id: int):
    """Generate a follow-up draft for an existing thread."""
    # Get original draft info
    draft_info = await db.get_draft_with_hotel(draft_id)
    if not draft_info:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    original_draft = await db.get_draft(draft_id)
    if original_draft.status != DraftStatus.SENT:
        raise HTTPException(
            status_code=400,
            detail="Can only generate follow-up for sent drafts"
        )
    
    # Get thread for this draft
    from app.models import Thread
    thread = await db.get_thread(original_draft.thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Safety: Check follow-up limit
    max_followups = int(os.getenv('MAX_FOLLOWUPS_PER_THREAD', '1'))
    if thread.followup_count >= max_followups:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum follow-ups ({max_followups}) reached for this thread"
        )
    
    # Get trip info
    trip = await db.get_trip(draft_info['trip_id'])
    hotel = await db.get_hotel(original_draft.hotel_id)
    
    # Generate follow-up
    provider = os.getenv('LLM_PROVIDER', 'stub')
    api_key = os.getenv('OPENAI_API_KEY')
    llm = get_llm_client(provider, api_key)
    
    context = HotelContext(
        hotel_name=hotel.name,
        destination=trip.destination,
        check_in=trip.check_in,
        check_out=trip.check_out,
        adults=trip.adults,
        budget=trip.budget,
        room_type=hotel.room_type,
        notes=trip.notes
    )
    
    email = await llm.generate_followup_email(
        context,
        original_draft.subject,
        original_draft.body,
        thread.last_snippet
    )
    
    # Create new draft (requires approval before sending)
    new_draft = Draft(
        id=None,
        hotel_id=hotel.id,
        subject=email.subject,
        body=email.body,
        status=DraftStatus.DRAFT
    )
    
    new_draft_id = await db.create_draft(new_draft)
    
    # Increment follow-up count
    await db.increment_followup_count(thread.id)
    
    created_draft = await db.get_draft(new_draft_id)
    return DraftResponse(
        id=created_draft.id,
        hotel_id=created_draft.hotel_id,
        subject=created_draft.subject,
        body=created_draft.body,
        status=created_draft.status.value,
        created_at=str(created_draft.created_at) if created_draft.created_at else None,
        approved_at=str(created_draft.approved_at) if created_draft.approved_at else None,
        sent_at=str(created_draft.sent_at) if created_draft.sent_at else None,
        thread_id=created_draft.thread_id
    )


# HTML UI Routes
@router.get("/trips/{trip_id}/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request, trip_id: int):
    """Display drafts for a trip."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    drafts = await db.get_drafts_by_trip(trip_id)
    hotels = await db.get_hotels_by_trip(trip_id)
    
    # Build hotel lookup
    hotel_lookup = {h.id: h for h in hotels}
    
    # Enrich drafts with hotel info
    draft_data = []
    for d in drafts:
        hotel = hotel_lookup.get(d.hotel_id)
        draft_data.append({
            "draft": d,
            "hotel": hotel
        })
    
    return templates.TemplateResponse(
        "drafts.html",
        {
            "request": request,
            "trip": trip,
            "draft_data": draft_data,
            "hotels_without_draft": await db.get_hotels_without_draft(trip_id)
        }
    )


@router.post("/trips/{trip_id}/drafts/generate", response_class=HTMLResponse)
async def generate_drafts_form(request: Request, trip_id: int):
    """Generate drafts from form submission."""
    await generate_drafts_api(trip_id)
    return RedirectResponse(url=f"/trips/{trip_id}/drafts", status_code=303)


@router.post("/drafts/{draft_id}/approve", response_class=HTMLResponse)
async def approve_draft_form(request: Request, draft_id: int):
    """Approve draft from form submission."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    hotel = await db.get_hotel(draft.hotel_id)
    trip_id = hotel.trip_id
    
    await approve_draft_api(draft_id)
    return RedirectResponse(url=f"/trips/{trip_id}/drafts", status_code=303)


@router.post("/drafts/{draft_id}/send", response_class=HTMLResponse)
async def send_draft_form(request: Request, draft_id: int):
    """Send draft from form submission."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    hotel = await db.get_hotel(draft.hotel_id)
    trip_id = hotel.trip_id
    
    await send_draft_api(draft_id)
    return RedirectResponse(url=f"/trips/{trip_id}/drafts", status_code=303)


@router.post("/drafts/{draft_id}/skip", response_class=HTMLResponse)
async def skip_draft_form(request: Request, draft_id: int):
    """Skip draft from form submission."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    hotel = await db.get_hotel(draft.hotel_id)
    trip_id = hotel.trip_id
    
    await skip_draft_api(draft_id)
    return RedirectResponse(url=f"/trips/{trip_id}/drafts", status_code=303)


@router.post("/drafts/{draft_id}/generate-followup", response_class=HTMLResponse)
async def generate_followup_form(request: Request, draft_id: int):
    """Generate follow-up from form submission."""
    draft = await db.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    hotel = await db.get_hotel(draft.hotel_id)
    trip_id = hotel.trip_id
    
    await generate_followup_api(draft_id)
    return RedirectResponse(url=f"/trips/{trip_id}/drafts", status_code=303)
