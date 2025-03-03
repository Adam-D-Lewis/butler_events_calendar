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
            
            # Find the parent container that holds all event information
            # Try different possible parent elements since the structure might vary
            parent_container = None
            for parent_class in ["views-row", "event-item", "event-container"]:
                parent = link.find_parent("div", class_=parent_class)
                if parent:
                    parent_container = parent
                    break
                    
            # If we still don't have a parent, try the h2 parent as fallback
            if not parent_container:
                parent_container = link.find_parent("h2")
                
            # Extract datetime details using the datetime container
            datetime_container = None
            if parent_container:
                datetime_container = parent_container.find("div", class_="views-field-field-cofaevent-datetime")
            if datetime_container:
                # Try to find time tags which contain the ISO datetime
                time_tags = datetime_container.find_all("time")
                if len(time_tags) >= 2:
                    # If we have both start and end time tags
                    start = datetime.datetime.fromisoformat(time_tags[0]["datetime"])
                    end = datetime.datetime.fromisoformat(time_tags[1]["datetime"])
                elif len(time_tags) == 1:
                    # If we only have start time, set end time to 1 hour later
                    start = datetime.datetime.fromisoformat(time_tags[0]["datetime"])
                    end = start + datetime.timedelta(hours=1)
                else:
                    # If no time tags, try to parse the text content
                    date_text = datetime_container.get_text(strip=True)
                    try:
                        # Try different date formats that might be on the page
                        for fmt in ["%B %d, %Y", "%A, %B %d, %Y", "%m/%d/%Y"]:
                            try:
                                date_obj = datetime.datetime.strptime(date_text, fmt)
                                start = date_obj
                                end = date_obj + datetime.timedelta(hours=1)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        # Fallback to current time if parsing fails
                        start = datetime.datetime.now()
                        end = start + datetime.timedelta(hours=1)
            else:
                # If no datetime container found, check for other date indicators
                date_div = link.find_parent("div", class_="views-row").find("div", class_="date-display-single")
                if date_div:
                    try:
                        date_text = date_div.get_text(strip=True)
                        date_obj = datetime.datetime.strptime(date_text, "%B %d, %Y")
                        start = date_obj
                        end = date_obj + datetime.timedelta(hours=1)
                    except (ValueError, AttributeError):
                        start = datetime.datetime.now()
                        end = start + datetime.timedelta(hours=1)
                else:
                    # Last resort fallback
                    start = datetime.datetime.now()
                    end = start + datetime.timedelta(hours=1)
            # Extract location and map link details.
            location_container = None
            if parent_container:
                location_container = parent_container.find("div", class_="views-field-field-cofaevent-location-name")
            
            # If not found, try the old method as fallback
            if not location_container and link.find_parent("h2"):
                location_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-location-name")
            
            location = ""
            map_link = ""
            if location_container:
                a_tags = location_container.find_all("a")
                location = a_tags[0].get_text(strip=True) if a_tags else ""
                for a in a_tags:
                    if "map" in a.get_text(strip=True).lower():
                        map_link = a.get("href")
                        break
            
            # Extract admission information
            admission_container = None
            if parent_container:
                admission_container = parent_container.find("div", class_="views-field-field-cofaevent-admission-range")
            
            # If not found, try the old method as fallback
            if not admission_container and link.find_parent("h2"):
                admission_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-admission-range")
            
            admission_info = ""
            if admission_container:
                admission_info = admission_container.get_text(strip=True)
            
            # Determine whether the event is streamable and get stream link
            ticket_container = None
            if parent_container:
                ticket_container = parent_container.find("div", class_="views-field-field-cofaevent-ticket-button")
            
            # If not found, try the old method as fallback
            if not ticket_container and link.find_parent("h2"):
                ticket_container = link.find_parent("h2").find_next_sibling("div", class_="views-field-field-cofaevent-ticket-button")
            
            streamable = False
            stream_link = ""
            if ticket_container:
                stream_button = ticket_container.find("a")
                if stream_button and "stream" in stream_button.get_text(strip=True).lower():
                    streamable = True
                    stream_link = stream_button.get("href", "")

            # Build a more detailed description
            description_parts = []
            if admission_info:
                description_parts.append(admission_info)
            if streamable and stream_link:
                description_parts.append(f"Stream available at: {stream_link}")
            
            description = "\n".join(description_parts)
            
            events.append(
                {
                    "summary": event_title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "description": description,
                    "location": location,
                    "map_link": map_link,
                    "streamable": streamable,
                    "stream_link": stream_link,
                    "admission_info": admission_info
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
