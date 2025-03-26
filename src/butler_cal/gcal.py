import datetime
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger


def get_service_account_credentials():
    """Get service account credentials from environment variables."""
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    if "SA_CREDENTIALS" in os.environ:
        logger.info('Loading credentials from "SA_CREDENTIALS" environment variable.')
        info = json.loads(os.environ["SA_CREDENTIALS"].replace("\n", "\\n"))
        credentials = service_account.Credentials.from_service_account_info(
            info=info,
            scopes=SCOPES,
        )
    elif "SA_CREDENTIALS_PATH" in os.environ:
        service_account_file = os.environ["SA_CREDENTIALS_PATH"]

        logger.info(
            f'Loading credentials from "{service_account_file}" environment variable.'
        )

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=SCOPES,
        )
    else:
        raise ValueError(
            "No service account credentials provided.  Please set SA_CREDENTIALS or SA_CREDENTIALS_PATH."
        )

    return credentials


def get_google_calendar_service():
    """Get an authorized Google Calendar API service instance using service account."""

    credentials = get_service_account_credentials()

    service = build("calendar", "v3", credentials=credentials)
    return service


def create_calendar_event(
    service,
    calendar_id,
    summary,
    location,
    description,
    start_datetime,
    end_datetime,
    timezone="America/Chicago",
):
    """
    Create a new event in Google Calendar.

    Args:
        service: Google Calendar API service instance
        calendar_id: ID of the calendar to add the event to
        summary: Event title/summary
        location: Event location
        description: Event description
        start_datetime: Start datetime object
        end_datetime: End datetime object
        timezone: Timezone string (default: 'America/Chicago' for Austin, TX)

    Returns:
        Created event object
    """
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
    }

    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    logger.info(f'Event created: {event.get("htmlLink")}')
    return event


def debug_event_format(event, prefix="Event"):
    """Debug helper to logger.info event format details"""
    logger.info(f"{prefix} summary: {event.get('summary')}")

    if isinstance(event.get("start"), dict):
        start_time = event["start"].get("dateTime")
        logger.info(f"{prefix} start (dict): {start_time}")
    else:
        start_time = event.get("start")
        logger.info(f"{prefix} start (direct): {start_time}")

    logger.info(f"{prefix} type: {type(event.get('start'))}")
    return start_time


def event_exists(service, calendar_id, event, debug=False):
    """
    Check if an event already exists in the calendar.

    Args:
        service: Google Calendar API service instance
        calendar_id: ID of the calendar to check
        event: Event dictionary with 'summary' and either:
               - 'start' as ISO format string, or
               - 'start' as a dictionary with 'dateTime' key

    Returns:
        Boolean indicating if the event exists
    """
    # Handle different event formats
    if debug:
        event_start_str = debug_event_format(event)
    else:
        if isinstance(event.get("start"), dict):
            # Format from gcal.py
            event_start_str = event["start"].get("dateTime")
        else:
            # Format from scraper
            event_start_str = event.get("start")

    # Parse the datetime
    event_start = datetime.datetime.fromisoformat(event_start_str.replace("Z", ""))

    # Create a time window query - properly format for RFC3339
    time_min = (event_start - datetime.timedelta(minutes=1)).isoformat()
    time_max = (event_start + datetime.timedelta(minutes=1)).isoformat()

    # Ensure proper timezone format for Google Calendar API
    if not time_min.endswith("Z") and "+" not in time_min and "-" not in time_min[-6:]:
        time_min += "Z"
    if not time_max.endswith("Z") and "+" not in time_max and "-" not in time_max[-6:]:
        time_max += "Z"

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            q=event["summary"],
        )
        .execute()
    )
    existing_events = events_result.get("items", [])
    return len(existing_events) > 0


def delete_all_events(service, calendar_id):
    """Delete all events from the specified calendar."""
    # Get all events
    events_result = (
        service.events().list(calendarId=calendar_id, maxResults=2500).execute()
    )
    events = events_result.get("items", [])

    if not events:
        logger.info("No events found to delete.")
        return

    # Delete each event
    for event in events:
        service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
        logger.info(f"Deleted event: {event.get('summary', 'Unnamed event')}")

    logger.info(f"Successfully deleted {len(events)} events from the calendar.")


def delete_removed_events(service, calendar_id, scraped_events, time_window_days=30):
    """
    Delete events from the calendar that are no longer in the scraped events list.
    
    Args:
        service: Google Calendar API service instance
        calendar_id: ID of the calendar to check
        scraped_events: List of events scraped from the website
        time_window_days: Number of days to look ahead/behind for events (default: 30)
    
    Returns:
        Number of events deleted
    """
    # Create a time window for the query
    now = datetime.datetime.utcnow()
    time_min = (now - datetime.timedelta(days=time_window_days)).isoformat() + "Z"
    time_max = (now + datetime.timedelta(days=time_window_days)).isoformat() + "Z"
    
    # Get all events in the calendar within the time window
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=2500,
        )
        .execute()
    )
    calendar_events = events_result.get("items", [])
    
    if not calendar_events:
        logger.info("No events found in calendar within the time window.")
        return 0
    
    # Create a set of (summary, start_time) tuples from scraped events for easy comparison
    scraped_event_keys = set()
    for event in scraped_events:
        # Handle different event formats
        if isinstance(event.get("start"), dict):
            event_start = event["start"].get("dateTime")
        else:
            event_start = event.get("start")
            
        # Only add if we have both summary and start time
        if event.get("summary") and event_start:
            # Normalize the datetime format by removing timezone info for comparison
            start_dt = datetime.datetime.fromisoformat(event_start.replace("Z", ""))
            scraped_event_keys.add((event["summary"], start_dt.isoformat()))
    
    # Check each calendar event
    deleted_count = 0
    for event in calendar_events:
        summary = event.get("summary")
        start_time = event.get("start", {}).get("dateTime")
        
        if summary and start_time:
            # Normalize the datetime format by removing timezone info for comparison
            start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
            event_key = (summary, start_dt.isoformat())
            
            # If the event is not in the scraped events, delete it
            if event_key not in scraped_event_keys:
                service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
                logger.info(f"Deleted removed event: {summary} at {start_time}")
                deleted_count += 1
    
    if deleted_count > 0:
        logger.info(f"Successfully deleted {deleted_count} events that were removed from the source.")
    else:
        logger.info("No removed events found to delete.")
        
    return deleted_count
