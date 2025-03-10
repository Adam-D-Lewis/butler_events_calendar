"""Code releated to Google Calendar."""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# Path to service account credentials
CREDENTIALS_FILE = 'butler-calendar-452702-e1335e356afc.json'

# Calendar ID - 'primary' for your primary calendar or use a specific calendar ID
CALENDAR_ID = os.environ['CALENDAR_ID']

def get_google_calendar_service():
    """Get an authorized Google Calendar API service instance using service account."""
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES)
    
    return build('calendar', 'v3', credentials=credentials)

def create_event(service, summary, location, description, start_datetime, end_datetime):
    """Create a new event in Google Calendar."""
    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'America/Chicago',  # Updated to match utils.py
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'America/Chicago',  # Updated to match utils.py
        },
    }

    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')
    return event

def list_events(service):
    """List events from the Google Calendar."""
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

def main():
    service = get_google_calendar_service()
    
    # List existing events
    list_events(service)
    breakpoint()
    # Create a new event
    # Example event
    summary = 'Sample Event'
    location = 'Butler University'
    description = 'This is a sample event created using a service account'

    start_time = datetime.datetime(2025, 3, 15, 10, 0, 0)
    end_time = datetime.datetime(2025, 3, 15, 11, 0, 0)
    
    create_event(service, summary, location, description, start_time, end_time)

if __name__ == '__main__':
    main()
