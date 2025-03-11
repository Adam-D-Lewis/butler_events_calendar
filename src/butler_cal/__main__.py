import argparse
import os

from loguru import logger

from butler_cal.gcal import (
    event_exists,
    get_google_calendar_service,
)
from butler_cal.scraper import scrape_utexas_calendar


def delete_all_events(service, calendar_id):
    """Delete all events from the specified calendar."""
    # Get all events
    events_result = service.events().list(calendarId=calendar_id, maxResults=2500).execute()
    events = events_result.get('items', [])
    
    if not events:
        logger.info("No events found to delete.")
        return
    
    # Delete each event
    for event in events:
        service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
        logger.info(f"Deleted event: {event.get('summary', 'Unnamed event')}")
    
    logger.info(f"Successfully deleted {len(events)} events from the calendar.")


def main():
    parser = argparse.ArgumentParser(description="Butler Calendar Management")
    parser.add_argument("--delete-all", action="store_true", help="Delete all events from the calendar")
    args = parser.parse_args()

    # Prepare Google Calendar service and calendar ID.
    service = get_google_calendar_service()
    calendar_id = os.environ["CALENDAR_ID"]

    if args.delete_all:
        delete_all_events(service, calendar_id)
        return

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
