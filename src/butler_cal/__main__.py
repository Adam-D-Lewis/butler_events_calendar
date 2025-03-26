import argparse
import os

from loguru import logger

from butler_cal.gcal import (
    delete_all_events,
    delete_removed_events,
    event_exists,
    get_google_calendar_service,
)
from butler_cal.scraper import scrape_utexas_calendar


def main():
    parser = argparse.ArgumentParser(description="Butler Calendar Management")
    parser.add_argument(
        "--delete-all", action="store_true", help="Delete all events from the calendar"
    )
    parser.add_argument(
        "--sync", action="store_true", 
        help="Sync calendar by removing events that no longer exist on the website"
    )
    args = parser.parse_args()

    # Prepare Google Calendar service and calendar ID.
    service = get_google_calendar_service()
    calendar_id = os.environ["CALENDAR_ID"]

    if args.delete_all:
        delete_all_events(service, calendar_id)
        return

    # Scrape events from the website
    events = scrape_utexas_calendar()
    
    # Add new events to the calendar
    added_count = 0
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
            added_count += 1
        else:
            logger.info(f"Event exists: {event['summary']}")
    
    # Delete events that have been removed from the website
    if args.sync or added_count > 0:  # Always sync if we added events
        deleted_count = delete_removed_events(service, calendar_id, events)
        logger.info(f"Calendar sync complete: {added_count} events added, {deleted_count} events removed")


if __name__ == "__main__":
    main()
