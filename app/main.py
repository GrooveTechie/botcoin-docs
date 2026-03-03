"""Hotel Deal Negotiator - Main FastAPI Application."""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import db
from app.routes import trips_router, hotels_router, drafts_router, threads_router

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    db_path = os.getenv('DATABASE_URL', 'sqlite:///./data/hotel_deals.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]  # Remove sqlite:/// prefix
    db.db_path = db_path
    await db.connect()
    
    yield
    
    # Shutdown
    await db.disconnect()


app = FastAPI(
    title="Hotel Deal Negotiator",
    description="MVP app to email hotels for direct booking deals with human approval",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(trips_router)
app.include_router(hotels_router)
app.include_router(drafts_router)
app.include_router(threads_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to trips page."""
    return RedirectResponse(url="/trips", status_code=302)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
