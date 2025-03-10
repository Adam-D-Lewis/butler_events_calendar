from butler_cal.gcal import (
    event_exists,
    get_google_calendar_service,
    scrape_utexas_calendar,
)


# def test_get_google_calendar_service(mocker):
#     # Create a dummy service object you expect to be returned.
#     dummy_credentials = mocker.Mock()
#     dummy_credentials.authorize.return_value = object()  # dummy authorized http client
#     mocker.patch(
#         "butler_cal.utils.service_account.Credentials.from_service_account_file",
#         return_value=dummy_credentials,
#     )

#     service = get_google_calendar_service()
#     assert (
#         service == dummy_credentials.authorize.return_value
#     ), "The google calendar service should match the authorized dummy object"


# def test_scrape_utexas_calendar():
#     events = scrape_utexas_calendar()
#     assert isinstance(events, list), "Expected events to be returned as a list"


# def test_event_exists(mocker):
#     # Dummy placeholders; adjust based on actual event structure.
#     dummy_service = mocker.Mock()  # Mock the service to be used inside event_exists.
#     dummy_service.events.return_value.list.return_value.execute.return_value = {
#         "items": []
#     }
#     dummy_calendar_id = "dummy-calendar"
#     dummy_event = {
#         "id": "event123",
#         "summary": "Test Event",
#         "start": "2023-10-01T10:00:00",
#     }

#     # Assuming that for these dummy parameters, the event does not exist.
#     exists = event_exists(dummy_service, dummy_calendar_id, dummy_event)
#     assert exists is False, "The dummy event should not be found and thus return False"
import datetime
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build

from butler_cal.gcal import (
    create_calendar_event,
    debug_event_format,
    event_exists,
    get_google_calendar_service,
    scrape_utexas_calendar,
)


class TestGcalFunctions(unittest.TestCase):
    def setUp(self):
        # Create mock service for testing
        self.mock_service = MagicMock()
        self.mock_events = MagicMock()
        self.mock_service.events.return_value = self.mock_events
        
        # Sample event data
        self.calendar_id = "test_calendar_id"
        self.event_summary = "Test Event"
        self.event_location = "Test Location"
        self.event_description = "Test Description"
        self.start_datetime = datetime.datetime(2023, 1, 1, 10, 0, 0)
        self.end_datetime = datetime.datetime(2023, 1, 1, 12, 0, 0)
        
    @patch('butler_cal.gcal.service_account.Credentials.from_service_account_file')
    @patch('butler_cal.gcal.build')
    def test_get_google_calendar_service(self, mock_build, mock_credentials):
        # Setup mocks
        mock_credentials.return_value = "mock_credentials"
        mock_build.return_value = "mock_service"
        
        # Test with environment variable
        with patch.dict('os.environ', {"SA_CREDENTIALS_PATH": "test_path.json"}):
            service = get_google_calendar_service()
            mock_credentials.assert_called_with("test_path.json", scopes=["https://www.googleapis.com/auth/calendar"])
            mock_build.assert_called_with("calendar", "v3", credentials="mock_credentials")
            self.assertEqual(service, "mock_service")
        
        # Test with default path
        with patch.dict('os.environ', {}, clear=True):
            service = get_google_calendar_service()
            mock_credentials.assert_called_with('butler-calendar-452702-e1335e356afc.json', 
                                               scopes=["https://www.googleapis.com/auth/calendar"])
    
    def test_create_calendar_event(self):
        # Setup mock
        mock_event = {"htmlLink": "https://calendar.google.com/event/123"}
        self.mock_events.insert.return_value.execute.return_value = mock_event
        
        # Call function
        result = create_calendar_event(
            self.mock_service,
            self.calendar_id,
            self.event_summary,
            self.event_location,
            self.event_description,
            self.start_datetime,
            self.end_datetime
        )
        
        # Verify
        self.mock_events.insert.assert_called_once()
        call_args = self.mock_events.insert.call_args[1]
        self.assertEqual(call_args['calendarId'], self.calendar_id)
        
        event_body = call_args['body']
        self.assertEqual(event_body['summary'], self.event_summary)
        self.assertEqual(event_body['location'], self.event_location)
        self.assertEqual(event_body['description'], self.event_description)
        self.assertEqual(event_body['start']['dateTime'], self.start_datetime.isoformat())
        self.assertEqual(event_body['start']['timeZone'], 'America/Chicago')
        self.assertEqual(event_body['end']['dateTime'], self.end_datetime.isoformat())
        self.assertEqual(event_body['end']['timeZone'], 'America/Chicago')
        
        self.assertEqual(result, mock_event)
    
    @patch('butler_cal.gcal.scrape_butler_events')
    def test_scrape_utexas_calendar(self, mock_scrape_butler_events):
        # Setup mock to return events for first page and empty list for second page
        mock_scrape_butler_events.side_effect = [
            [{"title": "Event 1"}, {"title": "Event 2"}],
            []
        ]
        
        # Call function
        events = scrape_utexas_calendar()
        
        # Verify
        self.assertEqual(len(events), 2)
        self.assertEqual(mock_scrape_butler_events.call_count, 2)
        mock_scrape_butler_events.assert_any_call("https://music.utexas.edu/events")
        mock_scrape_butler_events.assert_any_call("https://music.utexas.edu/events?page=1")
    
    def test_debug_event_format(self):
        # Test with dict start format
        event_dict = {
            "summary": "Test Event",
            "start": {"dateTime": "2023-01-01T10:00:00"}
        }
        
        with patch('builtins.print') as mock_print:
            result = debug_event_format(event_dict)
            self.assertEqual(result, "2023-01-01T10:00:00")
            mock_print.assert_any_call("Event summary: Test Event")
            mock_print.assert_any_call("Event start (dict): 2023-01-01T10:00:00")
        
        # Test with direct start format
        event_direct = {
            "summary": "Test Event",
            "start": "2023-01-01T10:00:00"
        }
        
        with patch('builtins.print') as mock_print:
            result = debug_event_format(event_direct)
            self.assertEqual(result, "2023-01-01T10:00:00")
            mock_print.assert_any_call("Event summary: Test Event")
            mock_print.assert_any_call("Event start (direct): 2023-01-01T10:00:00")
    
    def test_event_exists(self):
        # Setup mock for event that exists
        mock_events_result = {"items": [{"id": "event1"}]}
        self.mock_events.list.return_value.execute.return_value = mock_events_result
        
        # Test with dict start format
        event_dict = {
            "summary": "Test Event",
            "start": {"dateTime": "2023-01-01T10:00:00"}
        }
        
        result = event_exists(self.mock_service, self.calendar_id, event_dict)
        self.assertTrue(result)
        
        # Verify correct parameters were used
        call_args = self.mock_events.list.call_args[1]
        self.assertEqual(call_args['calendarId'], self.calendar_id)
        self.assertEqual(call_args['q'], "Test Event")
        
        # Test with direct start format
        event_direct = {
            "summary": "Test Event",
            "start": "2023-01-01T10:00:00"
        }
        
        result = event_exists(self.mock_service, self.calendar_id, event_direct)
        self.assertTrue(result)
        
        # Test for event that doesn't exist
        mock_events_result = {"items": []}
        self.mock_events.list.return_value.execute.return_value = mock_events_result
        
        result = event_exists(self.mock_service, self.calendar_id, event_dict)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
