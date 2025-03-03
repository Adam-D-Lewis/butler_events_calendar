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
            # Assume the datetime details (like "March 3, 2025, 7:30 - 9 p.m.") are in the next sibling element.
            datetime_sibling = link.find_parent("h2").find_next_sibling()
            datetime_str = datetime_sibling.get_text(strip=True) if datetime_sibling else ""
            # Expected format: "March 7, 2025, 6 - 7 p.m." (or similar)
            # Split into date and time parts.
            try:
                date_part, time_part = datetime_str.split(",", 1)
                date_part = date_part.strip()
                time_part = time_part.strip()
                    # Use regex to extract start and end time tokens and the meridiem.
                    import re

                    m = re.search(
                        r"(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*(a\.m\.|p\.m\.)",
                        time_part,
                    )
                    if m:
                        start_time_str, end_time_str, meridiem = m.groups()

                        # Parse the date using the known format.
                        base_date = datetime.datetime.strptime(date_part, "%B %d %Y")
                        # Ensure the meridiem is applied – append it and parse the time.
                        start_dt = datetime.datetime.strptime(
                            f"{start_time_str} {meridiem}", "%I:%M %p"
                            if ":" in start_time_str
                            else "%I %p"
                        )
                        end_dt = datetime.datetime.strptime(
                            f"{end_time_str} {meridiem}", "%I:%M %p"
                            if ":" in end_time_str
                            else "%I %p"
                        )
                        # Combine the base_date with the parsed time.
                        start = datetime.datetime(
                            base_date.year,
                            base_date.month,
                            base_date.day,
                            start_dt.hour,
                            start_dt.minute,
                        )
                        end = datetime.datetime(
                            base_date.year,
                            base_date.month,
                            base_date.day,
                            end_dt.hour,
                            end_dt.minute,
                        )
                    else:
                        # Fallback: if time format is not as expected, use dummy times.
                        start = datetime.datetime.now()
                        end = start + datetime.timedelta(hours=1)
                except Exception:
                    # On error, use dummy times.
                    start = datetime.datetime.now()
                    end = start + datetime.timedelta(hours=1)
            else:
                # If no datetime info, use dummy times.
                start = datetime.datetime.now()
                end = start + datetime.timedelta(hours=1)

            events.append(
                {
                    "summary": event_title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "description": "",
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
