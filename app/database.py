"""Database connection and operations."""
import aiosqlite
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from app.models import SCHEMA_SQL, Trip, Hotel, Draft, Thread, DraftStatus


class Database:
    def __init__(self, db_path: str = "./data/hotel_deals.db"):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.executescript(SCHEMA_SQL)
        await self._connection.commit()
    
    async def disconnect(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    # Trip operations
    async def create_trip(self, trip: Trip) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO trips (destination, check_in, check_out, adults, budget, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (trip.destination, trip.check_in, trip.check_out, trip.adults, trip.budget, trip.notes)
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_trip(self, trip_id: int) -> Optional[Trip]:
        cursor = await self.conn.execute(
            "SELECT * FROM trips WHERE id = ?", (trip_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Trip(
                id=row["id"],
                destination=row["destination"],
                check_in=row["check_in"],
                check_out=row["check_out"],
                adults=row["adults"],
                budget=row["budget"],
                notes=row["notes"],
                created_at=row["created_at"]
            )
        return None
    
    async def get_all_trips(self) -> List[Trip]:
        cursor = await self.conn.execute("SELECT * FROM trips ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            Trip(
                id=row["id"],
                destination=row["destination"],
                check_in=row["check_in"],
                check_out=row["check_out"],
                adults=row["adults"],
                budget=row["budget"],
                notes=row["notes"],
                created_at=row["created_at"]
            )
            for row in rows
        ]

    # Hotel operations
    async def create_hotel(self, hotel: Hotel) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO hotels (trip_id, name, website, contact_email, room_type)
               VALUES (?, ?, ?, ?, ?)""",
            (hotel.trip_id, hotel.name, hotel.website, hotel.contact_email, hotel.room_type)
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_hotel(self, hotel_id: int) -> Optional[Hotel]:
        cursor = await self.conn.execute(
            "SELECT * FROM hotels WHERE id = ?", (hotel_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Hotel(
                id=row["id"],
                trip_id=row["trip_id"],
                name=row["name"],
                website=row["website"],
                contact_email=row["contact_email"],
                room_type=row["room_type"],
                created_at=row["created_at"]
            )
        return None
    
    async def get_hotels_by_trip(self, trip_id: int) -> List[Hotel]:
        cursor = await self.conn.execute(
            "SELECT * FROM hotels WHERE trip_id = ? ORDER BY created_at DESC",
            (trip_id,)
        )
        rows = await cursor.fetchall()
        return [
            Hotel(
                id=row["id"],
                trip_id=row["trip_id"],
                name=row["name"],
                website=row["website"],
                contact_email=row["contact_email"],
                room_type=row["room_type"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    async def get_hotels_without_draft(self, trip_id: int) -> List[Hotel]:
        """Get hotels that don't have any draft yet."""
        cursor = await self.conn.execute(
            """SELECT h.* FROM hotels h
               LEFT JOIN drafts d ON h.id = d.hotel_id
               WHERE h.trip_id = ? AND d.id IS NULL
               ORDER BY h.created_at""",
            (trip_id,)
        )
        rows = await cursor.fetchall()
        return [
            Hotel(
                id=row["id"],
                trip_id=row["trip_id"],
                name=row["name"],
                website=row["website"],
                contact_email=row["contact_email"],
                room_type=row["room_type"],
                created_at=row["created_at"]
            )
            for row in rows
        ]

    # Draft operations
    async def create_draft(self, draft: Draft) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO drafts (hotel_id, subject, body, status)
               VALUES (?, ?, ?, ?)""",
            (draft.hotel_id, draft.subject, draft.body, draft.status.value)
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_draft(self, draft_id: int) -> Optional[Draft]:
        cursor = await self.conn.execute(
            "SELECT * FROM drafts WHERE id = ?", (draft_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Draft(
                id=row["id"],
                hotel_id=row["hotel_id"],
                subject=row["subject"],
                body=row["body"],
                status=DraftStatus(row["status"]),
                created_at=row["created_at"],
                approved_at=row["approved_at"],
                sent_at=row["sent_at"],
                thread_id=row["thread_id"]
            )
        return None
    
    async def get_drafts_by_trip(self, trip_id: int) -> List[Draft]:
        cursor = await self.conn.execute(
            """SELECT d.* FROM drafts d
               JOIN hotels h ON d.hotel_id = h.id
               WHERE h.trip_id = ?
               ORDER BY d.created_at DESC""",
            (trip_id,)
        )
        rows = await cursor.fetchall()
        return [
            Draft(
                id=row["id"],
                hotel_id=row["hotel_id"],
                subject=row["subject"],
                body=row["body"],
                status=DraftStatus(row["status"]),
                created_at=row["created_at"],
                approved_at=row["approved_at"],
                sent_at=row["sent_at"],
                thread_id=row["thread_id"]
            )
            for row in rows
        ]
    
    async def approve_draft(self, draft_id: int) -> bool:
        """Approve a draft. Only drafts in 'Draft' status can be approved."""
        cursor = await self.conn.execute(
            """UPDATE drafts SET status = ?, approved_at = ?
               WHERE id = ? AND status = ?""",
            (DraftStatus.APPROVED.value, datetime.now(timezone.utc).isoformat(), draft_id, DraftStatus.DRAFT.value)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    async def mark_draft_sent(self, draft_id: int, thread_id: int) -> bool:
        """Mark a draft as sent. Only approved drafts can be sent."""
        cursor = await self.conn.execute(
            """UPDATE drafts SET status = ?, sent_at = ?, thread_id = ?
               WHERE id = ? AND status = ?""",
            (DraftStatus.SENT.value, datetime.now(timezone.utc).isoformat(), thread_id, draft_id, DraftStatus.APPROVED.value)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    async def skip_draft(self, draft_id: int) -> bool:
        """Skip a draft."""
        cursor = await self.conn.execute(
            """UPDATE drafts SET status = ?
               WHERE id = ? AND status IN (?, ?)""",
            (DraftStatus.SKIPPED.value, draft_id, DraftStatus.DRAFT.value, DraftStatus.APPROVED.value)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    # Thread operations
    async def create_thread(self, thread: Thread) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO threads (draft_id, gmail_thread_id, gmail_message_id, last_checked_at)
               VALUES (?, ?, ?, ?)""",
            (thread.draft_id, thread.gmail_thread_id, thread.gmail_message_id, datetime.now(timezone.utc).isoformat())
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_thread(self, thread_id: int) -> Optional[Thread]:
        cursor = await self.conn.execute(
            "SELECT * FROM threads WHERE id = ?", (thread_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Thread(
                id=row["id"],
                draft_id=row["draft_id"],
                gmail_thread_id=row["gmail_thread_id"],
                gmail_message_id=row["gmail_message_id"],
                last_checked_at=row["last_checked_at"],
                last_snippet=row["last_snippet"],
                has_reply=bool(row["has_reply"]),
                followup_count=row["followup_count"]
            )
        return None
    
    async def get_thread_by_hotel(self, hotel_id: int) -> Optional[Thread]:
        """Get thread for a hotel via its sent draft."""
        cursor = await self.conn.execute(
            """SELECT t.* FROM threads t
               JOIN drafts d ON t.draft_id = d.id
               WHERE d.hotel_id = ? AND d.status = ?
               ORDER BY t.id DESC LIMIT 1""",
            (hotel_id, DraftStatus.SENT.value)
        )
        row = await cursor.fetchone()
        if row:
            return Thread(
                id=row["id"],
                draft_id=row["draft_id"],
                gmail_thread_id=row["gmail_thread_id"],
                gmail_message_id=row["gmail_message_id"],
                last_checked_at=row["last_checked_at"],
                last_snippet=row["last_snippet"],
                has_reply=bool(row["has_reply"]),
                followup_count=row["followup_count"]
            )
        return None
    
    async def get_all_threads(self) -> List[Thread]:
        cursor = await self.conn.execute(
            "SELECT * FROM threads ORDER BY last_checked_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            Thread(
                id=row["id"],
                draft_id=row["draft_id"],
                gmail_thread_id=row["gmail_thread_id"],
                gmail_message_id=row["gmail_message_id"],
                last_checked_at=row["last_checked_at"],
                last_snippet=row["last_snippet"],
                has_reply=bool(row["has_reply"]),
                followup_count=row["followup_count"]
            )
            for row in rows
        ]
    
    async def update_thread_reply(self, thread_id: int, snippet: str, has_reply: bool) -> bool:
        cursor = await self.conn.execute(
            """UPDATE threads SET last_checked_at = ?, last_snippet = ?, has_reply = ?
               WHERE id = ?""",
            (datetime.now(timezone.utc).isoformat(), snippet, int(has_reply), thread_id)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    async def increment_followup_count(self, thread_id: int) -> bool:
        cursor = await self.conn.execute(
            """UPDATE threads SET followup_count = followup_count + 1
               WHERE id = ?""",
            (thread_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    async def get_thread_with_hotel_info(self, thread_id: int) -> Optional[dict]:
        """Get thread with associated hotel and trip info."""
        cursor = await self.conn.execute(
            """SELECT t.*, d.subject, d.body, h.name as hotel_name, h.contact_email, 
                      tr.destination, tr.check_in, tr.check_out
               FROM threads t
               JOIN drafts d ON t.draft_id = d.id
               JOIN hotels h ON d.hotel_id = h.id
               JOIN trips tr ON h.trip_id = tr.id
               WHERE t.id = ?""",
            (thread_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def get_all_threads_with_info(self) -> List[dict]:
        """Get all threads with associated hotel and trip info."""
        cursor = await self.conn.execute(
            """SELECT t.*, d.subject, d.body, h.name as hotel_name, h.contact_email,
                      tr.destination, tr.check_in, tr.check_out
               FROM threads t
               JOIN drafts d ON t.draft_id = d.id
               JOIN hotels h ON d.hotel_id = h.id
               JOIN trips tr ON h.trip_id = tr.id
               ORDER BY t.last_checked_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # Additional helper for getting draft with hotel info
    async def get_draft_with_hotel(self, draft_id: int) -> Optional[dict]:
        cursor = await self.conn.execute(
            """SELECT d.*, h.name as hotel_name, h.contact_email, h.trip_id,
                      tr.destination, tr.check_in, tr.check_out, tr.adults, tr.budget
               FROM drafts d
               JOIN hotels h ON d.hotel_id = h.id
               JOIN trips tr ON h.trip_id = tr.id
               WHERE d.id = ?""",
            (draft_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


# Global database instance
db = Database()
