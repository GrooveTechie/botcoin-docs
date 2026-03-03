#!/usr/bin/env python3
"""Seed script to create example data for Hotel Deal Negotiator."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import db
from app.models import Trip, Hotel


async def seed_data():
    """Create example trip and hotels."""
    # Initialize database
    await db.connect()
    
    print("Creating example trip...")
    
    # Create a sample trip
    trip = Trip(
        id=None,
        destination="Paris, France",
        check_in="2025-06-15",
        check_out="2025-06-22",
        adults=2,
        budget=2000.00,
        notes="Anniversary trip. Prefer hotels near the Eiffel Tower with breakfast included."
    )
    trip_id = await db.create_trip(trip)
    print(f"Created trip #{trip_id}: {trip.destination}")
    
    # Create sample hotels
    hotels = [
        Hotel(
            id=None,
            trip_id=trip_id,
            name="Hotel Le Bristol",
            website="https://www.oetkercollection.com/hotels/le-bristol-paris/",
            contact_email="reservations@lebristolparis.com",
            room_type="Deluxe Room"
        ),
        Hotel(
            id=None,
            trip_id=trip_id,
            name="Hotel Plaza Athenee",
            website="https://www.dorchestercollection.com/paris/hotel-plaza-athenee/",
            contact_email="reservations.hpa@dorchestercollection.com",
            room_type="Superior Room"
        ),
        Hotel(
            id=None,
            trip_id=trip_id,
            name="Pullman Paris Tour Eiffel",
            website="https://www.pullmanhotels.com/",
            contact_email="h2573-re@accor.com",
            room_type="Executive Room"
        ),
    ]
    
    for hotel in hotels:
        hotel_id = await db.create_hotel(hotel)
        print(f"  Added hotel #{hotel_id}: {hotel.name}")
    
    # Create a second trip as another example
    trip2 = Trip(
        id=None,
        destination="Tokyo, Japan",
        check_in="2025-09-01",
        check_out="2025-09-08",
        adults=2,
        budget=3000.00,
        notes="First time in Japan. Looking for hotels in Shibuya or Shinjuku area."
    )
    trip2_id = await db.create_trip(trip2)
    print(f"Created trip #{trip2_id}: {trip2.destination}")
    
    hotels2 = [
        Hotel(
            id=None,
            trip_id=trip2_id,
            name="Park Hyatt Tokyo",
            website="https://www.hyatt.com/en-US/hotel/japan/park-hyatt-tokyo/",
            contact_email="tokyo.park@hyatt.com",
            room_type="Park Room"
        ),
        Hotel(
            id=None,
            trip_id=trip2_id,
            name="Cerulean Tower Tokyu Hotel",
            website="https://www.ceruleantower-hotel.com/en/",
            contact_email="info@ceruleantower-hotel.com",
            room_type="Standard Room"
        ),
    ]
    
    for hotel in hotels2:
        hotel_id = await db.create_hotel(hotel)
        print(f"  Added hotel #{hotel_id}: {hotel.name}")
    
    await db.disconnect()
    print("\n✅ Seed data created successfully!")
    print("\nStart the app with: uvicorn app.main:app --reload")
    print("Then visit: http://localhost:8000/trips")


if __name__ == "__main__":
    asyncio.run(seed_data())
