import os

from butler_cal.gcal import (
    event_exists,
    get_google_calendar_service,
    scrape_utexas_calendar,
)


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
                    "description": event["description"],
                    "start": {
                        "dateTime": event["start"],
                        "timeZone": "America/Chicago",
                    },
                    "end": {"dateTime": event["end"], "timeZone": "America/Chicago"},
                },
            ).execute()
            print(f"Added event: {event['summary']}")
        else:
            print(f"Event exists: {event['summary']}")


if __name__ == "__main__":
    main()
