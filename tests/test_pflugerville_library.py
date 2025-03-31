"""Tests for the Pflugerville Library events scraper."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from butler_cal.scraper.scrape_pflugerville_library import (
    PflugervilleLibraryScraper,
)


@pytest.fixture
def mock_token():
    """Mock token for API requests."""
    return "Bearer mock_token_12345"


@pytest.fixture
def mock_library_events():
    """Return mock events for testing."""
    return {
        "total": 2,
        "items": [
            {
                "id": "event1",
                "data": {
                    "title": {"en": "Library Book Club"},
                    "description": {
                        "en": "Join us for a discussion of this month's book."
                    },
                    "eventdate": {
                        "iv": {
                            "startDate": "2025-03-01T14:00:00Z",
                            "endDate": "2025-03-01T15:30:00Z",
                        }
                    },
                    "location": {"en": "Pflugerville Public Library, Meeting Room A"},
                },
                "tags": ["Library", "Adults"],
            },
            {
                "id": "event2",
                "data": {
                    "title": {"en": "Kids Storytime"},
                    "description": {"en": "Storytime for children ages 3-5."},
                    "eventdate": {
                        "iv": {
                            "startDate": "2025-03-03T10:00:00Z",
                            "endDate": "2025-03-03T11:00:00Z",
                        }
                    },
                    "location": {"en": "Pflugerville Public Library, Children's Area"},
                },
                "tags": ["Library", "Kids"],
            },
        ],
    }


def test_get_token_from_html():
    """Test getting token from HTML."""
    # HTML with token in standard format
    html_with_token = """
    <html>
    <head>
    <script>
    window.hcmsClientToken = "Bearer abc123xyz";
    </script>
    </head>
    <body>Test content</body>
    </html>
    """

    # Create a mock response for successful token retrieval
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_with_token
        mock_get.return_value = mock_response

        scraper = PflugervilleLibraryScraper()
        token = scraper._get_token_from_html("https://example.com/standard")
        assert token == "Bearer abc123xyz"

    # HTML with token in alternative format
    html_with_alt_token = """
    <html>
    <head>
    <script>
    var tokens = {"auth": "Bearer def456uvw"};
    </script>
    </head>
    <body>Test content</body>
    </html>
    """

    # Test alternative token format
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_with_alt_token
        mock_get.return_value = mock_response

        scraper = PflugervilleLibraryScraper()
        token = scraper._get_token_from_html("https://example.com/alt")
        assert token == "Bearer def456uvw"

    # HTML without token
    html_without_token = """
    <html>
    <head><script>var x = 5;</script></head>
    <body>Test content</body>
    </html>
    """

    # Test no token
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_without_token
        mock_get.return_value = mock_response

        scraper = PflugervilleLibraryScraper()
        token = scraper._get_token_from_html("https://example.com/none")
        assert token is None

    # Test error handling
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("500 Server Error")

        scraper = PflugervilleLibraryScraper()
        token = scraper._get_token_from_html("https://example.com/error")
        assert token is None


@patch("butler_cal.scraper.scrape_pflugerville_library.PflugervilleLibraryScraper._get_token_from_html")
def test_pflugerville_library_init(mock_get_token, mock_token):
    """Test PflugervilleLibraryScraper initialization."""
    mock_get_token.return_value = mock_token

    scraper = PflugervilleLibraryScraper()

    # Verify token was retrieved
    mock_get_token.assert_called_once()

    # Verify scraper was initialized correctly
    assert scraper.name == "PflugervilleLibrary"
    assert scraper.hcms_client_token == mock_token
    assert scraper.headers["Authorization"] == mock_token
    assert scraper.page_size == 50
    assert "Library" in scraper.category_ids


@patch("butler_cal.scraper.scrape_pflugerville_library.PflugervilleLibraryScraper._get_token_from_html")
def test_get_events(mock_get_token, mock_token, mock_library_events):
    """Test getting events from the Pflugerville Library API."""
    mock_get_token.return_value = mock_token

    # Create a modified scraper class that overrides the _get_events method
    class TestScraper(PflugervilleLibraryScraper):
        def _get_events(
            self, skip=0, start_date=None, end_date=None, tag=None, category=None
        ):
            return mock_library_events["items"], mock_library_events["total"]

    # Create scraper and get events
    scraper = TestScraper()

    # Set specific date range for testing - use naive datetimes to avoid timezone issues
    start_date = datetime(2025, 3, 1)
    end_date = datetime(2025, 3, 31)

    events = scraper.get_events(start_date=start_date, end_date=end_date)

    # Verify events were fetched and normalized
    # Events are returned in a dictionary with calendar_id as key
    # For tests with no calendar_id specified, they'll be under None key
    assert len(events[None]) == 2

    # Check first event
    assert events[None][0]["summary"] == "Library Book Club"
    assert events[None][0]["description"] == "Join us for a discussion of this month's book."
    assert "2025-03-01" in events[None][0]["start"]  # Just check the date part
    assert "2025-03-01" in events[None][0]["end"]    # Just check the date part
    assert "Pflugerville Public Library" in events[None][0]["location"]
    assert (
        events[None][0]["url"]
        == "https://tx-pflugerville.civicplus.com/calendar.aspx?EID=event1"
    )
    assert events[None][0]["source"] == "pflugerville_library"

    # Check second event
    assert events[None][1]["summary"] == "Kids Storytime"
    assert events[None][1]["description"] == "Storytime for children ages 3-5."
    assert "2025-03-03" in events[None][1]["start"]  # Just check the date part
    assert "2025-03-03" in events[None][1]["end"]    # Just check the date part
    assert "Children's Area" in events[None][1]["location"]


@patch("butler_cal.scraper.scrape_pflugerville_library.PflugervilleLibraryScraper._get_token_from_html")
def test_get_events_pagination(mock_get_token, mock_token, mock_library_events):
    """Test event pagination."""
    mock_get_token.return_value = mock_token

    # Create a modified scraper class with an overridden get_events method
    # that directly tests the pagination behavior
    class TestPaginationScraper(PflugervilleLibraryScraper):
        def __init__(self):
            super().__init__()
            self.call_count = 0
            self.page1_data = mock_library_events.copy()
            self.page1_data["total"] = 75  # Set a large total to force pagination

            # Create page 2 with different events
            self.page2_data = {
                "items": [
                    {
                        "id": "event3",
                        "data": {
                            "title": {"en": "Teen Book Club"},
                            "description": {"en": "Book club for teens."},
                            "eventdate": {
                                "iv": {
                                    "startDate": "2025-03-05T16:00:00Z",
                                    "endDate": "2025-03-05T17:30:00Z",
                                }
                            },
                            "location": {
                                "en": "Pflugerville Public Library, Teen Room"
                            },
                        },
                        "tags": ["Library", "Teens"],
                    }
                ]
            }

        # Override _get_events to return different data based on the skip value
        def _get_events(
            self, skip=0, start_date=None, end_date=None, tag=None, category=None
        ):
            self.call_count += 1

            if skip == 0:
                # First page with items that will be less than the total,
                # which will trigger a second page request
                return self.page1_data["items"], self.page1_data["total"]
            else:
                # Second page
                return self.page2_data["items"], self.page1_data["total"]

        # Also need to override normalize_event so we don't get errors
        def normalize_event(self, event):
            """Simple normalizer for test purposes"""
            if (
                "data" in event
                and "title" in event["data"]
                and "en" in event["data"]["title"]
            ):
                summary = event["data"]["title"]["en"]
                if "eventdate" in event["data"] and "iv" in event["data"]["eventdate"]:
                    start = event["data"]["eventdate"]["iv"]["startDate"]
                    return {
                        "summary": summary,
                        "start": start,
                        "end": event["data"]["eventdate"]["iv"]["endDate"],
                        "description": event["data"]["description"]["en"],
                        "location": (
                            event["data"]["location"]["en"]
                            if "location" in event["data"]
                            else ""
                        ),
                        "url": f"https://example.com/{event['id']}",
                    }
            return {"summary": "Error", "start": "", "end": ""}

    # Create scraper and call get_events
    scraper = TestPaginationScraper()

    # We need to manually force the page_size to be small enough to trigger pagination
    # based on our test data
    scraper.page_size = 2  # Set page size to match our first page item count

    # Get events which should trigger pagination
    events = scraper.get_events()

    # Verify we got events from both pages combined
    assert len(events[None]) == 3  # 2 from page1 + 1 from page2

    # Verify _get_events was called at least twice for pagination
    assert scraper.call_count >= 2

    # Check for event from second page
    teen_event = next((e for e in events[None] if e["summary"] == "Teen Book Club"), None)
    assert teen_event is not None
    assert "2025-03-05T16:00:00" in teen_event["start"]


@patch("butler_cal.scraper.scrape_pflugerville_library.PflugervilleLibraryScraper._get_token_from_html")
def test_normalize_event(mock_get_token, mock_token):
    """Test event normalization."""
    mock_get_token.return_value = mock_token

    scraper = PflugervilleLibraryScraper()

    # Test with valid event
    valid_event = {
        "id": "event1",
        "data": {
            "title": {"en": "Library Workshop"},
            "description": {"en": "Learn new skills at our workshop."},
            "eventdate": {
                "iv": {
                    "startDate": "2025-04-10T13:00:00Z",
                    "endDate": "2025-04-10T15:00:00Z",
                }
            },
            "location": {"en": "Pflugerville Public Library, Computer Lab"},
        },
    }

    normalized = scraper.normalize_event(valid_event)
    assert normalized["summary"] == "Library Workshop"
    assert normalized["description"] == "Learn new skills at our workshop."
    assert "2025-04-10" in normalized["start"]  # Just check the date part
    assert "2025-04-10" in normalized["end"]    # Just check the date part
    assert normalized["location"] == "Pflugerville Public Library, Computer Lab"
    assert (
        normalized["url"]
        == "https://tx-pflugerville.civicplus.com/calendar.aspx?EID=event1"
    )

    # Test with invalid event (missing required fields)
    invalid_event = {
        "id": "event2",
        "data": {
            "title": {"en": "Broken Event"},
            # Missing other required fields
        },
    }

    normalized = scraper.normalize_event(invalid_event)
    assert normalized["summary"] == "Broken Event"
    assert "Error processing" in normalized["description"]
    assert "start" in normalized
    assert "end" in normalized


@patch("butler_cal.scraper.scrape_pflugerville_library.PflugervilleLibraryScraper._get_token_from_html")
def test_api_error_handling(mock_get_token, mock_token):
    """Test handling of API errors."""
    mock_get_token.return_value = mock_token

    # Create a test class that simulates an API error in _get_events
    class TestErrorScraper(PflugervilleLibraryScraper):
        def _get_events(
            self, skip=0, start_date=None, end_date=None, tag=None, category=None
        ):
            # Simulate an API error by returning None, None
            return None, None

    # Create the scraper and call get_events
    scraper = TestErrorScraper()
    events = scraper.get_events()

    # Should return empty list on error
    assert events == []
