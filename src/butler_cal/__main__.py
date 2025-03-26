import argparse
import os
from datetime import datetime, timedelta

from loguru import logger

from butler_cal.gcal import (
    delete_all_events,
    delete_removed_events,
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
    
    # Get existing events from the calendar
    # Look back 30 days and forward 180 days to cover all potential events
    time_min = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
    time_max = (datetime.now() + timedelta(days=180)).isoformat() + 'Z'
    
    logger.info("Fetching existing calendar events...")
    existing_events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        maxResults=2500  # Maximum allowed by the API
    ).execute()
    
    existing_events = existing_events_result.get('items', [])
    logger.info(f"Found {len(existing_events)} existing events in calendar")
    
    # Create a lookup dictionary of existing events by summary and start time
    existing_event_map = {}
    for existing_event in existing_events:
        if 'summary' in existing_event and 'start' in existing_event and 'dateTime' in existing_event['start']:
            key = (existing_event['summary'], existing_event['start']['dateTime'])
            existing_event_map[key] = existing_event['id']
    
    # Prepare batch request for new events
    batch = service.new_batch_http_request()
    added_count = 0
    
    for event in events:
        # Check if event already exists using our lookup map
        event_key = (event['summary'], event['start'])
        if event_key not in existing_event_map:
            # Create event body
            event_body = {
                "summary": event["summary"],
                "description": event["description"] + f"\n{event['url']}",
                "location": event["location"],
                "start": {
                    "dateTime": event["start"],
                    "timeZone": "America/Chicago",
                },
                "end": {"dateTime": event["end"], "timeZone": "America/Chicago"},
            }
            
            # Add to batch request
            batch.add(service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ))
            logger.info(f"Queued event for addition: {event['summary']}")
            added_count += 1
        else:
            logger.info(f"Event exists: {event['summary']}")
    
    # Execute batch request if there are events to add
    if added_count > 0:
        logger.info(f"Adding {added_count} events in batch...")
        batch.execute()
    
    # Delete events that have been removed from the website
    if args.sync or added_count > 0:  # Always sync if we added events
        deleted_count = delete_removed_events(service, calendar_id, events)
        logger.info(f"Calendar sync complete: {added_count} events added, {deleted_count} events removed")


if __name__ == "__main__":
    main()
