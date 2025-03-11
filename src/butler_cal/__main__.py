import os

from loguru import logger

from butler_cal.gcal import (
    event_exists,
    get_google_calendar_service,
)
from butler_cal.scraper import scrape_utexas_calendar


def main():
    # Prepare Google Calendar service and calendar ID.
    service = get_google_calendar_service()

    calendar_id = os.environ["CALENDAR_ID"]

    events = scrape_utexas_calendar()
    for event in events:
        if not event_exists(service, calendar_id, event):
            service.events().insert(
                calendarId=calendar_id,
                body={
                    "summary": event["summary"],
                    "description": event["description"] + f"\n{event['url']}",
                    "location": event["location"],
                    "start": {
                        "dateTime": event["start"],
                        "timeZone": "America/Chicago",
                    },
                    "end": {"dateTime": event["end"], "timeZone": "America/Chicago"},
                },
            ).execute()
            logger.info(f"Added event: {event['summary']}")
        else:
            logger.info(f"Event exists: {event['summary']}")


if __name__ == "__main__":
    main()
