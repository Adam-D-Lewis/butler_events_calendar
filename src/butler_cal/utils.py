import datetime

import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build


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
    url = "https://music.utexas.edu/calendar"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    events = []
    # Inspect the HTML and adapt selectors; for example, if events are in <a> tags:
    for a in soup.select('a[href*="/events"]'):
        event_title = a.get_text(strip=True)
        # event_link = a["href"]
        # You may need to follow event_link to extract date/time detail.
        # For now, add dummy date and description.
        event_date = datetime.datetime.now()  # TODO: replace with parsed event date
        event_description = ""
        events.append(
            {
                "summary": event_title,
                "start": event_date.isoformat(),
                "end": (event_date + datetime.timedelta(hours=1)).isoformat(),
                "description": event_description,
            }
        )
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
