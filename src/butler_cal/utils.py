import datetime

import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from butler_cal.scraper import scrape_butler_events


def get_google_calendar_service():
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    SERVICE_ACCOUNT_FILE = (
        "path/to/service-account.json"  # TODO: replace with your service account file
    )
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=credentials)
    return service


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


def event_exists(service, calendar_id, event):
    # Create a time window query using the event start time.
    event_start = datetime.datetime.fromisoformat(event["start"])
    time_min = (event_start - datetime.timedelta(minutes=1)).isoformat() + "Z"
    time_max = (event_start + datetime.timedelta(minutes=1)).isoformat() + "Z"

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
