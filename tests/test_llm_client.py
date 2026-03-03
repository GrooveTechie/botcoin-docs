"""Tests for LLM client email generation."""
import pytest
import pytest_asyncio
from app.services.llm_client import StubLLMClient, HotelContext, get_llm_client


class TestStubLLMClient:
    """Tests for stub LLM client."""
    
    @pytest.mark.asyncio
    async def test_generate_initial_email(self):
        """Verify initial email is generated correctly."""
        client = StubLLMClient()
        context = HotelContext(
            hotel_name="Grand Hotel",
            destination="Paris, France",
            check_in="2025-06-15",
            check_out="2025-06-22",
            adults=2,
            budget=2000.0,
            room_type="Deluxe",
            notes="Anniversary trip"
        )
        
        email = await client.generate_initial_email(context)
        
        assert email.subject is not None
        assert "2025-06-15" in email.subject
        assert "2025-06-22" in email.subject
        
        assert email.body is not None
        assert "Grand Hotel" in email.body
        assert "Paris" in email.body
        assert "2025-06-15" in email.body
        assert "2025-06-22" in email.body
        assert "2 adult" in email.body
        assert "$2000" in email.body
    
    @pytest.mark.asyncio
    async def test_generate_initial_email_without_budget(self):
        """Verify email works without budget."""
        client = StubLLMClient()
        context = HotelContext(
            hotel_name="Test Hotel",
            destination="London",
            check_in="2025-07-01",
            check_out="2025-07-05",
            adults=3,
            budget=None,
            room_type=None,
            notes=None
        )
        
        email = await client.generate_initial_email(context)
        
        assert email.subject is not None
        assert email.body is not None
        assert "$" not in email.body  # No budget mentioned
    
    @pytest.mark.asyncio
    async def test_generate_followup_email(self):
        """Verify follow-up email is generated."""
        client = StubLLMClient()
        context = HotelContext(
            hotel_name="Grand Hotel",
            destination="Paris",
            check_in="2025-06-15",
            check_out="2025-06-22",
            adults=2,
            budget=None,
            room_type=None,
            notes=None
        )
        
        email = await client.generate_followup_email(
            context,
            "Direct Booking Inquiry",
            "Original body...",
            reply_snippet=None
        )
        
        assert "Re:" in email.subject
        assert "follow up" in email.body.lower() or "Follow" in email.body
        assert "Grand Hotel" in email.body
    
    @pytest.mark.asyncio
    async def test_generate_followup_with_reply(self):
        """Verify follow-up acknowledges previous reply."""
        client = StubLLMClient()
        context = HotelContext(
            hotel_name="Test Hotel",
            destination="Tokyo",
            check_in="2025-09-01",
            check_out="2025-09-08",
            adults=2,
            budget=None,
            room_type=None,
            notes=None
        )
        
        email = await client.generate_followup_email(
            context,
            "Original Subject",
            "Original body...",
            reply_snippet="We have availability for your dates."
        )
        
        assert email.subject is not None
        assert email.body is not None
        assert "response" in email.body.lower() or "thank" in email.body.lower()
    
    @pytest.mark.asyncio
    async def test_email_does_not_contain_competitor_claims(self):
        """Safety: Verify emails don't claim competitor offers."""
        client = StubLLMClient()
        context = HotelContext(
            hotel_name="Test Hotel",
            destination="Paris",
            check_in="2025-06-15",
            check_out="2025-06-22",
            adults=2,
            budget=1500.0,
            room_type="Standard",
            notes="Found cheaper on Booking.com"
        )
        
        email = await client.generate_initial_email(context)
        
        # Should not mention competitor sites
        body_lower = email.body.lower()
        assert "booking.com" not in body_lower
        assert "expedia" not in body_lower
        assert "hotels.com" not in body_lower
        assert "competitor" not in body_lower
        assert "cheaper elsewhere" not in body_lower


class TestLLMClientFactory:
    """Tests for LLM client factory."""
    
    def test_get_stub_client(self):
        """Verify stub client is returned by default."""
        client = get_llm_client()
        assert isinstance(client, StubLLMClient)
    
    def test_get_stub_client_explicit(self):
        """Verify stub client is returned when specified."""
        client = get_llm_client(provider="stub")
        assert isinstance(client, StubLLMClient)
    
    def test_openai_client_requires_api_key(self):
        """Verify OpenAI client requires API key."""
        with pytest.raises(ValueError, match="API key required"):
            get_llm_client(provider="openai")
