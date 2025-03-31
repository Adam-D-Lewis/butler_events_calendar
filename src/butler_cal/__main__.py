import argparse
import os
from datetime import datetime, timedelta

from loguru import logger

from butler_cal.gcal import (
    delete_all_events,
    delete_removed_events,
    get_google_calendar_service,
)
from butler_cal.scraper import (
    get_registered_scrapers,
    get_scraper,
    scrape_utexas_calendar,
)


def main():
    parser = argparse.ArgumentParser(description="Multi-source Calendar Management")
    parser.add_argument(
        "--delete-all", action="store_true", help="Delete all events from the calendar"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync calendar by removing events that no longer exist in the scraped sources",
    )
    parser.add_argument(
        "--scrapers",
        nargs="+",
        metavar="SCRAPER",
        help="List of specific scrapers to use (e.g. 'ButlerMusicScraper', 'PflugervilleLibraryScraper'). Use --list-scrapers to see available options.",
    )
    parser.add_argument(
        "--list-scrapers",
        action="store_true",
        help="List all available scrapers and exit",
    )
    parser.add_argument(
        "--calendar-id",
        help="Google Calendar ID to use (defaults to CALENDAR_ID environment variable)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=7,
        help="Number of days in the past to fetch events (default: 7)",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=90,
        help="Number of days in the future to fetch events (default: 90)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what events would be added/removed without making changes",
    )
    args = parser.parse_args()

    # List available scrapers if requested
    if args.list_scrapers:
        available_scrapers = get_registered_scrapers()
        if available_scrapers:
            print("\nAvailable calendar scrapers:")
            print("==========================")
            for name, scraper_class in available_scrapers.items():
                # Try to get the docstring for more info
                doc = scraper_class.__doc__ or "No description available"
                # Format the docstring - take the first line
                doc_line = doc.strip().split("\n")[0]
                print(f"  {name}")
                print(f"    {doc_line}")
            print(
                "\nTo use specific scrapers: --scrapers ButlerMusicScraper PflugervilleLibraryScraper"
            )
            print("To use all scrapers: (run without --scrapers option)")
        else:
            print("No calendar scrapers found. Check your installation.")
        return

    # Prepare Google Calendar service
    service = get_google_calendar_service()

    # Get calendar ID from args or environment variable
    calendar_id = args.calendar_id or os.environ.get("CALENDAR_ID")
    if not calendar_id:
        logger.error(
            "No calendar ID provided. Use --calendar-id or set the CALENDAR_ID environment variable."
        )
        return

    if args.delete_all:
        delete_all_events(service, calendar_id)
        return

    # Determine which scrapers to use
    if args.scrapers:
        scrapers_to_use = args.scrapers
    else:
        # Use all registered scrapers by default
        scrapers_to_use = list(get_registered_scrapers().keys())

    if not scrapers_to_use:
        raise Exception(
            "Error: No scrapers specified or found."
        )
    else:
        # Scrape events from all selected scrapers
        events = []
        for scraper_name in scrapers_to_use:
            try:
                logger.info(f"Scraping events using {scraper_name}...")
                scraper = get_scraper(scraper_name)

                # Use date ranges from command-line arguments
                start_date = datetime.now() - timedelta(days=args.days_back)
                end_date = datetime.now() + timedelta(days=args.days_ahead)

                scraper_events = scraper.get_events(
                    start_date=start_date, end_date=end_date
                )
                logger.info(f"Found {len(scraper_events)} events from {scraper_name}")
                events.extend(scraper_events)
            except Exception as e:
                logger.error(f"Error using scraper {scraper_name}: {e}")

    # Get existing events from the calendar
    # Look back 30 days and forward 180 days to cover all potential events
    time_min = (datetime.now() - timedelta(days=30)).isoformat() + "Z"
    time_max = (datetime.now() + timedelta(days=180)).isoformat() + "Z"

    logger.info("Fetching existing calendar events...")
    existing_events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            maxResults=2500,  # Maximum allowed by the API
        )
        .execute()
    )

    existing_events = existing_events_result.get("items", [])
    logger.info(f"Found {len(existing_events)} existing events in calendar")

    # Create a lookup dictionary of existing events by summary and start time
    existing_event_map = {}
    for existing_event in existing_events:
        if (
            "summary" in existing_event
            and "start" in existing_event
            and "dateTime" in existing_event["start"]
        ):
            key = (existing_event["summary"], existing_event["start"]["dateTime"])
            existing_event_map[key] = existing_event["id"]

    # Prepare batch request for new events
    batch = service.new_batch_http_request()
    added_count = 0

    for event in events:
        # Skip events missing required fields
        if not all(k in event for k in ("summary", "start", "end")):
            logger.warning(
                f"Skipping event missing required fields: {event.get('summary', 'Unknown')}"
            )
            continue

        # Standardize event format if needed
        if isinstance(event["start"], str):
            event_start = event["start"]
        else:
            # Handle dictionary format
            event_start = event["start"].get("dateTime")

        # Check if event already exists using our lookup map
        event_key = (event["summary"], event_start)
        if event_key not in existing_event_map:
            # Create event body
            event_body = {
                "summary": event["summary"],
                "description": event["description"]
                + (f"\n{event.get('url', '')}" if event.get("url") else ""),
                "location": event.get("location", ""),
                "start": {
                    "dateTime": event_start,
                    "timeZone": "America/Chicago",
                },
                "end": {
                    "dateTime": (
                        event["end"]
                        if isinstance(event["end"], str)
                        else event["end"].get("dateTime")
                    ),
                    "timeZone": "America/Chicago",
                },
            }

            # Add to batch request
            batch.add(service.events().insert(calendarId=calendar_id, body=event_body))
            logger.info(f"Queued event for addition: {event['summary']}")
            added_count += 1
        else:
            logger.info(f"Event exists: {event['summary']}")

    # Execute batch request if there are events to add and not in dry-run mode
    if added_count > 0:
        if args.dry_run:
            logger.info(f"Dry run: Would add {added_count} events to calendar")
        else:
            logger.info(f"Adding {added_count} events in batch...")
            batch.execute()

    # Handle event deletion
    if args.sync or added_count > 0:  # Always sync if we added events
        if args.dry_run:
            # Just calculate what would be deleted
            events_to_delete = []
            for event in existing_events:
                summary = event.get("summary")
                start_time = event.get("start", {}).get("dateTime")

                if summary and start_time:
                    # Normalize the datetime format by removing timezone info for comparison
                    start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
                    event_key = (summary, start_dt.isoformat())

                    # Check if this event is in the scraped events
                    scraped_event_keys = set()
                    for scraped_event in events:
                        # Get standardized start time
                        if isinstance(scraped_event.get("start"), str):
                            scraped_start = scraped_event["start"]
                        else:
                            scraped_start = scraped_event["start"].get("dateTime", "")

                        if scraped_event.get("summary") and scraped_start:
                            # Normalize datetime format
                            try:
                                scraped_dt = datetime.fromisoformat(
                                    scraped_start.replace("Z", "")
                                )
                                scraped_event_keys.add(
                                    (scraped_event["summary"], scraped_dt.isoformat())
                                )
                            except (KeyError, ValueError):
                                pass

                    # If event is not in scraped events, it would be deleted
                    if event_key not in scraped_event_keys:
                        events_to_delete.append(event)

            logger.info(
                f"Dry run: Would remove {len(events_to_delete)} events from calendar"
            )
            # List some of the events that would be deleted
            if events_to_delete:
                logger.info("Example events that would be removed:")
                for i, event in enumerate(
                    events_to_delete[:5]
                ):  # Show up to 5 examples
                    start = event.get("start", {}).get("dateTime", "unknown")
                    logger.info(f"  {i+1}. {event.get('summary')} at {start}")
                if len(events_to_delete) > 5:
                    logger.info(f"  ...and {len(events_to_delete) - 5} more")
        else:
            # Actually delete events
            deleted_count = delete_removed_events(service, calendar_id, events)
            logger.info(
                f"Calendar sync complete: {added_count} events added, {deleted_count} events removed"
            )


if __name__ == "__main__":
    main()
