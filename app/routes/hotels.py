"""Hotel routes for Hotel Deal Negotiator."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import db
from app.models import Hotel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class HotelCreate(BaseModel):
    trip_id: int
    name: str
    website: Optional[str] = None
    contact_email: str
    room_type: Optional[str] = None


class HotelResponse(BaseModel):
    id: int
    trip_id: int
    name: str
    website: Optional[str]
    contact_email: str
    room_type: Optional[str]
    created_at: Optional[str]


# API Routes
@router.post("/api/hotels", response_model=HotelResponse)
async def create_hotel_api(hotel: HotelCreate):
    """Create a new hotel target."""
    # Verify trip exists
    trip = await db.get_trip(hotel.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    hotel_obj = Hotel(
        id=None,
        trip_id=hotel.trip_id,
        name=hotel.name,
        website=hotel.website,
        contact_email=hotel.contact_email,
        room_type=hotel.room_type
    )
    hotel_id = await db.create_hotel(hotel_obj)
    created_hotel = await db.get_hotel(hotel_id)
    return HotelResponse(
        id=created_hotel.id,
        trip_id=created_hotel.trip_id,
        name=created_hotel.name,
        website=created_hotel.website,
        contact_email=created_hotel.contact_email,
        room_type=created_hotel.room_type,
        created_at=str(created_hotel.created_at) if created_hotel.created_at else None
    )


@router.get("/api/trips/{trip_id}/hotels", response_model=List[HotelResponse])
async def get_hotels_api(trip_id: int):
    """Get all hotels for a trip."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    hotels = await db.get_hotels_by_trip(trip_id)
    return [
        HotelResponse(
            id=h.id,
            trip_id=h.trip_id,
            name=h.name,
            website=h.website,
            contact_email=h.contact_email,
            room_type=h.room_type,
            created_at=str(h.created_at) if h.created_at else None
        )
        for h in hotels
    ]


@router.get("/api/hotels/{hotel_id}", response_model=HotelResponse)
async def get_hotel_api(hotel_id: int):
    """Get a specific hotel."""
    hotel = await db.get_hotel(hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return HotelResponse(
        id=hotel.id,
        trip_id=hotel.trip_id,
        name=hotel.name,
        website=hotel.website,
        contact_email=hotel.contact_email,
        room_type=hotel.room_type,
        created_at=str(hotel.created_at) if hotel.created_at else None
    )


# HTML Form Routes
@router.post("/trips/{trip_id}/hotels", response_class=HTMLResponse)
async def create_hotel_form(
    request: Request,
    trip_id: int,
    name: str = Form(...),
    contact_email: str = Form(...),
    website: Optional[str] = Form(None),
    room_type: Optional[str] = Form(None)
):
    """Create a hotel from form submission."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    hotel = Hotel(
        id=None,
        trip_id=trip_id,
        name=name,
        website=website,
        contact_email=contact_email,
        room_type=room_type
    )
    await db.create_hotel(hotel)
    return RedirectResponse(url=f"/trips/{trip_id}", status_code=303)
