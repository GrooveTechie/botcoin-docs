"""Tests for draft approval and send gating."""
import pytest
import pytest_asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.models import Trip, Hotel, Draft, DraftStatus, Thread


@pytest_asyncio.fixture
async def test_db():
    """Create a test database."""
    db = Database(":memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def sample_data(test_db):
    """Create sample trip, hotel, and draft."""
    trip = Trip(
        id=None,
        destination="Test City",
        check_in="2025-06-01",
        check_out="2025-06-05",
        adults=2,
        budget=1000.0,
        notes="Test trip"
    )
    trip_id = await test_db.create_trip(trip)
    
    hotel = Hotel(
        id=None,
        trip_id=trip_id,
        name="Test Hotel",
        website="https://test.hotel.com",
        contact_email="test@hotel.com",
        room_type="Standard"
    )
    hotel_id = await test_db.create_hotel(hotel)
    
    draft = Draft(
        id=None,
        hotel_id=hotel_id,
        subject="Test Subject",
        body="Test body content",
        status=DraftStatus.DRAFT
    )
    draft_id = await test_db.create_draft(draft)
    
    return {"trip_id": trip_id, "hotel_id": hotel_id, "draft_id": draft_id}


class TestDraftApproval:
    """Tests for draft approval flow."""
    
    @pytest.mark.asyncio
    async def test_draft_starts_in_draft_status(self, test_db, sample_data):
        """Verify new drafts start in Draft status."""
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.DRAFT
    
    @pytest.mark.asyncio
    async def test_can_approve_draft_in_draft_status(self, test_db, sample_data):
        """Verify drafts in Draft status can be approved."""
        success = await test_db.approve_draft(sample_data["draft_id"])
        assert success is True
        
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.APPROVED
        assert draft.approved_at is not None
    
    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved_draft(self, test_db, sample_data):
        """Verify already-approved drafts cannot be approved again."""
        # First approval
        await test_db.approve_draft(sample_data["draft_id"])
        
        # Second approval attempt should fail
        success = await test_db.approve_draft(sample_data["draft_id"])
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cannot_approve_sent_draft(self, test_db, sample_data):
        """Verify sent drafts cannot be approved."""
        # Approve and simulate send
        await test_db.approve_draft(sample_data["draft_id"])
        
        # Create thread
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        
        # Approval attempt should fail
        success = await test_db.approve_draft(sample_data["draft_id"])
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cannot_approve_skipped_draft(self, test_db, sample_data):
        """Verify skipped drafts cannot be approved."""
        await test_db.skip_draft(sample_data["draft_id"])
        
        success = await test_db.approve_draft(sample_data["draft_id"])
        assert success is False


class TestSendGating:
    """Tests for send gating - only approved drafts can be sent."""
    
    @pytest.mark.asyncio
    async def test_cannot_send_unapproved_draft(self, test_db, sample_data):
        """Verify drafts in Draft status cannot be marked as sent."""
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        
        # Try to mark as sent without approval
        success = await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        assert success is False
        
        # Verify status unchanged
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.DRAFT
    
    @pytest.mark.asyncio
    async def test_can_send_approved_draft(self, test_db, sample_data):
        """Verify approved drafts can be sent."""
        # Approve first
        await test_db.approve_draft(sample_data["draft_id"])
        
        # Create thread and send
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        success = await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        
        assert success is True
        
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.SENT
        assert draft.sent_at is not None
        assert draft.thread_id == thread_id
    
    @pytest.mark.asyncio
    async def test_cannot_send_skipped_draft(self, test_db, sample_data):
        """Verify skipped drafts cannot be sent."""
        await test_db.skip_draft(sample_data["draft_id"])
        
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        
        success = await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cannot_send_already_sent_draft(self, test_db, sample_data):
        """Verify already-sent drafts cannot be sent again."""
        # Approve and send
        await test_db.approve_draft(sample_data["draft_id"])
        
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        
        # Try to send again
        success = await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        assert success is False


class TestSkipDraft:
    """Tests for draft skipping."""
    
    @pytest.mark.asyncio
    async def test_can_skip_draft_in_draft_status(self, test_db, sample_data):
        """Verify drafts in Draft status can be skipped."""
        success = await test_db.skip_draft(sample_data["draft_id"])
        assert success is True
        
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.SKIPPED
    
    @pytest.mark.asyncio
    async def test_can_skip_approved_draft(self, test_db, sample_data):
        """Verify approved drafts can be skipped."""
        await test_db.approve_draft(sample_data["draft_id"])
        
        success = await test_db.skip_draft(sample_data["draft_id"])
        assert success is True
        
        draft = await test_db.get_draft(sample_data["draft_id"])
        assert draft.status == DraftStatus.SKIPPED
    
    @pytest.mark.asyncio
    async def test_cannot_skip_sent_draft(self, test_db, sample_data):
        """Verify sent drafts cannot be skipped."""
        # Approve and send
        await test_db.approve_draft(sample_data["draft_id"])
        
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        await test_db.mark_draft_sent(sample_data["draft_id"], thread_id)
        
        success = await test_db.skip_draft(sample_data["draft_id"])
        assert success is False


class TestThreadFollowupCount:
    """Tests for thread follow-up counting."""
    
    @pytest.mark.asyncio
    async def test_thread_starts_with_zero_followups(self, test_db, sample_data):
        """Verify new threads have zero follow-up count."""
        await test_db.approve_draft(sample_data["draft_id"])
        
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        
        thread = await test_db.get_thread(thread_id)
        assert thread.followup_count == 0
    
    @pytest.mark.asyncio
    async def test_increment_followup_count(self, test_db, sample_data):
        """Verify follow-up count can be incremented."""
        await test_db.approve_draft(sample_data["draft_id"])
        
        thread = Thread(
            id=None,
            draft_id=sample_data["draft_id"],
            gmail_thread_id="test_thread_id",
            gmail_message_id="test_message_id"
        )
        thread_id = await test_db.create_thread(thread)
        
        # Increment
        success = await test_db.increment_followup_count(thread_id)
        assert success is True
        
        thread = await test_db.get_thread(thread_id)
        assert thread.followup_count == 1
        
        # Increment again
        await test_db.increment_followup_count(thread_id)
        thread = await test_db.get_thread(thread_id)
        assert thread.followup_count == 2
