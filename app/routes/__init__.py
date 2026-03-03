"""Routes package."""
from app.routes.trips import router as trips_router
from app.routes.hotels import router as hotels_router
from app.routes.drafts import router as drafts_router
from app.routes.threads import router as threads_router

__all__ = ['trips_router', 'hotels_router', 'drafts_router', 'threads_router']
