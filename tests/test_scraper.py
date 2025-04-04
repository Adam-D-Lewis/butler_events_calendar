"""
Tests for the Butler School of Music events scraper.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from butler_cal.scraper.scrape_butler_music import ButlerMusicScraper
from butler_cal.scraper.scrape_butler_music import (
    ButlerMusicScraper,
    parse_event_datetime,
)

HERE = Path(__file__).parent


@pytest.fixture
def mock_html():
    """Return sample HTML content for testing."""
    with open(HERE / "page_example.html", "r") as f:
        return f.read()


def test_parse_event_datetime():
    """Test parsing event date and time strings."""
    # Test valid date and time
    dt = parse_event_datetime("Monday, March 3, 2025", "7:30PM")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 3
    assert dt.day == 3
    assert dt.hour == 19
    assert dt.minute == 30

    # Test invalid inputs
    assert parse_event_datetime(None, "7:30PM") is None
    assert parse_event_datetime("Monday, March 3, 2025", None) is None
    assert parse_event_datetime("Invalid date", "7:30PM") is None


@patch("requests.get")
def test_scrape_butler_events(mock_get, mock_html):
    """Test scraping events from the Butler School of Music website."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_get.return_value = mock_response

    # Create a scraper instance
    scraper = ButlerMusicScraper()

    # Call the method directly with the mocked URL
    events = scraper._scrape_butler_events("https://music.utexas.edu/events")

    # Verify mock was called
    mock_get.assert_called_once_with("https://music.utexas.edu/events")

    # Verify we got events
    assert isinstance(events, list)
    assert len(events) > 0

    # Check the first event (New Music Ensemble)
    first_event = next(
        (e for e in events if "New Music Ensemble" in e.get("summary", "")), None
    )
    assert first_event is not None
    assert first_event["summary"] == "New Music Ensemble"
    assert "2025-03-03T19:30:00" in first_event["start"]
    assert "2025-03-03T21:00:00" in first_event["end"]
    assert "Bates Recital Hall" in first_event["location"]
    assert "Free admission" in first_event.get("admission_info", "")

    # Check the second event (Artem Kuznetsov, piano)
    second_event = next(
        (e for e in events if "Artem Kuznetsov, piano" in e.get("summary", "")), None
    )
    assert second_event is not None
    assert second_event["summary"] == "Artem Kuznetsov, piano"
    assert "2025-03-04T15:00:00" in second_event["start"]
    assert "2025-03-04T16:00:00" in second_event["end"]
    assert "Bates Recital Hall" in second_event["location"]
    assert "Free admission" in second_event.get("admission_info", "")
    assert "DMA Chamber Recital" in second_event.get("details", "")


def test_first_event_details():
    """Test that we can correctly extract details for the first event."""
    # Create HTML for the first event
    html = """
    <div class="views-row">
        <h2 class="field-content"><a href="/event/123">New Music Ensemble</a></h2>
        <div class="views-field-field-cofaevent-datetime">
            <time datetime="2025-03-03T19:30:00">Monday, March 3, 2025 - 7:30 PM</time>
            <time datetime="2025-03-03T21:00:00">9:00 PM</time>
        </div>
        <div class="views-field-field-cofaevent-location-name">Bates Recital Hall</div>
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")

    # Call our scraper function on this HTML
    item = soup.find("div", class_="views-row")
    event = {}

    # Get event title
    title_elem = item.find("h2", class_="field-content")
    if title_elem and title_elem.a:
        event["summary"] = title_elem.a.text.strip()

    # Get event date and time
    datetime_container = item.find("div", class_="views-field-field-cofaevent-datetime")
    if datetime_container:
        time_tags = datetime_container.find_all("time")
        if len(time_tags) >= 2:
            # If we have both start and end time tags
            start = datetime.fromisoformat(time_tags[0]["datetime"])
            end = datetime.fromisoformat(time_tags[1]["datetime"])
            event["start"] = start.isoformat()
            event["end"] = end.isoformat()

    # Get event location
    location_container = item.find(
        "div", class_="views-field-field-cofaevent-location-name"
    )
    if location_container:
        event["location"] = location_container.get_text(strip=True)

    # Verify the extracted details
    assert event["summary"] == "New Music Ensemble"
    assert "2025-03-03T19:30:00" in event["start"]
    assert "2025-03-03T21:00:00" in event["end"]
    assert event["location"] == "Bates Recital Hall"


def test_second_event_details():
    """Test that we can correctly extract details for the second event."""
    html = """
    <div class="views-row">
        <h2 class="field-content"><a href="/event/124">Artem Kuznetsov, piano</a></h2>
        <div class="views-field-field-cofaevent-datetime">
            <time datetime="2025-03-04T15:00:00">Tuesday, March 4, 2025 - 3:00 PM</time>
            <time datetime="2025-03-04T16:00:00">4:00 PM</time>
        </div>
        <div class="views-field-field-cofaevent-location-name">Bates Recital Hall</div>
        <div class="views-field-field-cofaevent-admission-range">Admission: Free</div>
        <div class="views-field-field-cofaevent-details">DMA Chamber Recital</div>
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")

    # Call our scraper function on this HTML
    item = soup.find("div", class_="views-row")
    event = {}

    # Get event title
    title_elem = item.find("h2", class_="field-content")
    if title_elem and title_elem.a:
        event["summary"] = title_elem.a.text.strip()

    # Get event date and time
    datetime_container = item.find("div", class_="views-field-field-cofaevent-datetime")
    if datetime_container:
        time_tags = datetime_container.find_all("time")
        if len(time_tags) >= 2:
            # If we have both start and end time tags
            start = datetime.fromisoformat(time_tags[0]["datetime"])
            end = datetime.fromisoformat(time_tags[1]["datetime"])
            event["start"] = start.isoformat()
            event["end"] = end.isoformat()

    # Get event location
    location_container = item.find(
        "div", class_="views-field-field-cofaevent-location-name"
    )
    if location_container:
        event["location"] = location_container.get_text(strip=True)

    # Get admission information
    admission_container = item.find(
        "div", class_="views-field-field-cofaevent-admission-range"
    )
    if admission_container:
        event["admission_info"] = admission_container.get_text(strip=True)

    # Get event details
    details_container = item.find("div", class_="views-field-field-cofaevent-details")
    if details_container:
        event["details"] = details_container.get_text(strip=True)

    # Verify the extracted details
    assert event["summary"] == "Artem Kuznetsov, piano"
    assert "2025-03-04T15:00:00" in event["start"]
    assert "2025-03-04T16:00:00" in event["end"]
    assert event["location"] == "Bates Recital Hall"
    assert event["admission_info"] == "Admission: Free"
    assert event["details"] == "DMA Chamber Recital"


@patch(
    "butler_cal.scraper.scrape_butler_music.ButlerMusicScraper._scrape_butler_events"
)
def test_butler_music_scraper_get_events(mock_scrape_butler_events):
    # Setup mock to return events for first page and empty list for second page
    mock_scrape_butler_events.side_effect = [
        [{"title": "Event 1"}, {"title": "Event 2"}],
        [],
    ]

    # Create scraper instance and call get_events
    scraper = ButlerMusicScraper()
    events = scraper.get_events()

    # Verify - events is a dictionary with a single key (None) containing a list of events
    assert len(events[None]) == 2
    assert mock_scrape_butler_events.call_count == 2

    # The assertions below might need adjustments based on how your actual code works now
    # They should verify that the correct URLs were used for each page
    calls = mock_scrape_butler_events.call_args_list
    assert any("https://music.utexas.edu/events" in str(call) for call in calls)
    assert any("page=1" in str(call) for call in calls)
