"""Database models and schema for Hotel Deal Negotiator."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DraftStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    SENT = "Sent"
    SKIPPED = "Skipped"


@dataclass
class Trip:
    id: Optional[int]
    destination: str
    check_in: str  # Date string YYYY-MM-DD
    check_out: str  # Date string YYYY-MM-DD
    adults: int
    budget: Optional[float]
    notes: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class Hotel:
    id: Optional[int]
    trip_id: int
    name: str
    website: Optional[str]
    contact_email: str
    room_type: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class Draft:
    id: Optional[int]
    hotel_id: int
    subject: str
    body: str
    status: DraftStatus
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    thread_id: Optional[int] = None  # Link to thread after sending


@dataclass
class Thread:
    id: Optional[int]
    draft_id: int
    gmail_thread_id: str
    gmail_message_id: str
    last_checked_at: Optional[datetime] = None
    last_snippet: Optional[str] = None
    has_reply: bool = False
    followup_count: int = 0


# SQL Schema
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    adults INTEGER NOT NULL DEFAULT 2,
    budget REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hotels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    website TEXT,
    contact_email TEXT NOT NULL,
    room_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    sent_at TIMESTAMP,
    thread_id INTEGER,
    FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    gmail_thread_id TEXT NOT NULL,
    gmail_message_id TEXT NOT NULL,
    last_checked_at TIMESTAMP,
    last_snippet TEXT,
    has_reply INTEGER DEFAULT 0,
    followup_count INTEGER DEFAULT 0,
    FOREIGN KEY (draft_id) REFERENCES drafts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hotels_trip_id ON hotels(trip_id);
CREATE INDEX IF NOT EXISTS idx_drafts_hotel_id ON drafts(hotel_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_threads_draft_id ON threads(draft_id);
"""
