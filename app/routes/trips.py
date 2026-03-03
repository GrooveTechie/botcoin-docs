"""Trip routes for Hotel Deal Negotiator."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import db
from app.models import Trip

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class TripCreate(BaseModel):
    destination: str
    check_in: str  # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    adults: int = 2
    budget: Optional[float] = None
    notes: Optional[str] = None


class TripResponse(BaseModel):
    id: int
    destination: str
    check_in: str
    check_out: str
    adults: int
    budget: Optional[float]
    notes: Optional[str]
    created_at: Optional[str]


# API Routes
@router.post("/api/trips", response_model=TripResponse)
async def create_trip_api(trip: TripCreate):
    """Create a new trip."""
    trip_obj = Trip(
        id=None,
        destination=trip.destination,
        check_in=trip.check_in,
        check_out=trip.check_out,
        adults=trip.adults,
        budget=trip.budget,
        notes=trip.notes
    )
    trip_id = await db.create_trip(trip_obj)
    created_trip = await db.get_trip(trip_id)
    return TripResponse(
        id=created_trip.id,
        destination=created_trip.destination,
        check_in=created_trip.check_in,
        check_out=created_trip.check_out,
        adults=created_trip.adults,
        budget=created_trip.budget,
        notes=created_trip.notes,
        created_at=str(created_trip.created_at) if created_trip.created_at else None
    )


@router.get("/api/trips", response_model=List[TripResponse])
async def get_trips_api():
    """Get all trips."""
    trips = await db.get_all_trips()
    return [
        TripResponse(
            id=t.id,
            destination=t.destination,
            check_in=t.check_in,
            check_out=t.check_out,
            adults=t.adults,
            budget=t.budget,
            notes=t.notes,
            created_at=str(t.created_at) if t.created_at else None
        )
        for t in trips
    ]


@router.get("/api/trips/{trip_id}", response_model=TripResponse)
async def get_trip_api(trip_id: int):
    """Get a specific trip."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripResponse(
        id=trip.id,
        destination=trip.destination,
        check_in=trip.check_in,
        check_out=trip.check_out,
        adults=trip.adults,
        budget=trip.budget,
        notes=trip.notes,
        created_at=str(trip.created_at) if trip.created_at else None
    )


# HTML UI Routes
@router.get("/trips", response_class=HTMLResponse)
async def trips_page(request: Request):
    """Display all trips."""
    trips = await db.get_all_trips()
    return templates.TemplateResponse(
        "trips.html",
        {"request": request, "trips": trips}
    )


@router.post("/trips", response_class=HTMLResponse)
async def create_trip_form(
    request: Request,
    destination: str = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    adults: int = Form(2),
    budget: Optional[float] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Create a trip from form submission."""
    trip = Trip(
        id=None,
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        budget=budget,
        notes=notes
    )
    await db.create_trip(trip)
    return RedirectResponse(url="/trips", status_code=303)


@router.get("/trips/{trip_id}", response_class=HTMLResponse)
async def trip_detail_page(request: Request, trip_id: int):
    """Display trip details with hotels."""
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    hotels = await db.get_hotels_by_trip(trip_id)
    return templates.TemplateResponse(
        "trip_detail.html",
        {"request": request, "trip": trip, "hotels": hotels}
    )
