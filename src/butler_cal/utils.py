import datetime
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from butler_cal.scraper import scrape_butler_events


def get_google_calendar_service():
    """Get an authorized Google Calendar API service instance using service account."""
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    
    # Use environment variable if available, otherwise fall back to the file path in gcal.py
    service_account_file = os.environ.get("SA_CREDENTIALS_PATH", 'butler-calendar-452702-e1335e356afc.json')
    
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=credentials)
    return service


def create_calendar_event(service, calendar_id, summary, location, description, start_datetime, end_datetime, timezone='America/Chicago'):
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
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': timezone,
        },
    }

    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')
    return event

def scrape_utexas_calendar():
    """
    Scrape events from the Butler School of Music website.
    
    Returns:
        List of event dictionaries with details
    """
    base_url = "https://music.utexas.edu/events"
    events = []
    page = 0

    while True:
        # Use the base URL for page 0, and add the ?page= parameter for subsequent pages.
        url = base_url if page == 0 else f"{base_url}?page={page}"
        
        try:
            # Use our specialized scraper to get events from this page
            page_events = scrape_butler_events(url)
            
            # If no events found on this page, we've reached the end
            if not page_events:
                break
                
            # Add events from this page to our collection
            events.extend(page_events)
            
            # Move to the next page
            page += 1
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            break

    return events


def debug_event_format(event, prefix="Event"):
    """Debug helper to print event format details"""
    print(f"{prefix} summary: {event.get('summary')}")
    
    if isinstance(event.get("start"), dict):
        start_time = event["start"].get("dateTime")
        print(f"{prefix} start (dict): {start_time}")
    else:
        start_time = event.get("start")
        print(f"{prefix} start (direct): {start_time}")
    
    print(f"{prefix} type: {type(event.get('start'))}")
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
    event_start = datetime.datetime.fromisoformat(event_start_str.replace('Z', ''))
    
    # Create a time window query - properly format for RFC3339
    time_min = (event_start - datetime.timedelta(minutes=1)).isoformat()
    time_max = (event_start + datetime.timedelta(minutes=1)).isoformat()
    
    # Ensure proper timezone format for Google Calendar API
    if not time_min.endswith('Z') and '+' not in time_min and '-' not in time_min[-6:]:
        time_min += 'Z'
    if not time_max.endswith('Z') and '+' not in time_max and '-' not in time_max[-6:]:
        time_max += 'Z'

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
