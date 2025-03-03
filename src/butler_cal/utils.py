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
    base_url = "https://music.utexas.edu/events"
    events = []
    page = 0

    while True:
        # Use the base URL for page 0, and add the ?page= parameter for subsequent pages.
        url = base_url if page == 0 else f"{base_url}?page={page}"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Select event links that are inside h2 tags.
        # This selector ensures we only grab event items (e.g. "/events/4923-jaime-garcia-percussion")
        event_links = soup.select("h2.field-content.ut-headline a[href^='/events/']")
        if not event_links:
            break  # exit loop if no events are found on this page

        for link in event_links:
            event_title = link.get_text(strip=True)
            # NEW: Extract datetime details using the datetime container.
            datetime_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-datetime")
            if datetime_container:
                time_tags = datetime_container.find_all("time")
                if len(time_tags) >= 2:
                    start = datetime.datetime.fromisoformat(time_tags[0]["datetime"])
                    end = datetime.datetime.fromisoformat(time_tags[1]["datetime"])
                else:
                    start = datetime.datetime.now()
                    end = start + datetime.timedelta(hours=1)
            else:
                start = datetime.datetime.now()
                end = start + datetime.timedelta(hours=1)
            # NEW: Extract location and map link details.
            location_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-location")
            if location_container:
                a_tags = location_container.find_all("a")
                location = a_tags[0].get_text(strip=True) if a_tags else ""
                map_link = ""
                for a in a_tags:
                    if "map" in a.get_text(strip=True).lower():
                        map_link = a.get("href")
                        break
            else:
                location = ""
                map_link = ""

            # NEW: Determine whether the event is streamable.
            ticket_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-ticket-button")
            streamable = False
            if ticket_container:
                stream_button = ticket_container.find("a")
                if stream_button and "stream" in stream_button.get_text(strip=True).lower():
                    streamable = True

            events.append(
                {
                    "summary": event_title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "description": "",
                    "location": location,    # NEW detail
                    "map_link": map_link,    # NEW detail
                    "streamable": streamable # NEW detail
                }
            )
        page += 1

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
