import datetime
import unittest
from unittest.mock import MagicMock, patch

from butler_cal.gcal import (
    create_calendar_event,
    debug_event_format,
    delete_removed_events,
    event_exists,
    get_google_calendar_service,
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

    @patch("butler_cal.gcal.get_service_account_credentials")
    @patch("butler_cal.gcal.build")
    def test_get_google_calendar_service(self, mock_build, mock_get_credentials):
        # Setup mocks
        mock_get_credentials.return_value = "mock_credentials"
        mock_build.return_value = "mock_service"

        # Test with default setup
        service = get_google_calendar_service()

        # Verify the credentials function was called
        mock_get_credentials.assert_called_once()

        # Verify the build function was called with correct parameters
        mock_build.assert_called_with("calendar", "v3", credentials="mock_credentials")

        # Verify the service was returned correctly
        self.assertEqual(service, "mock_service")

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
            self.end_datetime,
        )

        # Verify
        self.mock_events.insert.assert_called_once()
        call_args = self.mock_events.insert.call_args[1]
        self.assertEqual(call_args["calendarId"], self.calendar_id)

        event_body = call_args["body"]
        self.assertEqual(event_body["summary"], self.event_summary)
        self.assertEqual(event_body["location"], self.event_location)
        self.assertEqual(event_body["description"], self.event_description)
        self.assertEqual(
            event_body["start"]["dateTime"], self.start_datetime.isoformat()
        )
        self.assertEqual(event_body["start"]["timeZone"], "America/Chicago")
        self.assertEqual(event_body["end"]["dateTime"], self.end_datetime.isoformat())
        self.assertEqual(event_body["end"]["timeZone"], "America/Chicago")

        self.assertEqual(result, mock_event)

    @patch("butler_cal.gcal.logger.info")
    def test_debug_event_format(self, mock_logger):
        # Test with dict start format
        event_dict = {
            "summary": "Test Event",
            "start": {"dateTime": "2023-01-01T10:00:00"},
        }

        result = debug_event_format(event_dict, prefix="Test")
        self.assertEqual(result, "2023-01-01T10:00:00")
        mock_logger.assert_any_call("Test summary: Test Event")
        mock_logger.assert_any_call("Test start (dict): 2023-01-01T10:00:00")

        # Reset mock for second test
        mock_logger.reset_mock()

        # Test with direct start format
        event_direct = {"summary": "Test Event", "start": "2023-01-01T10:00:00"}

        result = debug_event_format(event_direct, prefix="Test")
        self.assertEqual(result, "2023-01-01T10:00:00")
        mock_logger.assert_any_call("Test summary: Test Event")
        mock_logger.assert_any_call("Test start (direct): 2023-01-01T10:00:00")

    def test_event_exists(self):
        # Setup mock for event that exists
        mock_events_result = {"items": [{"id": "event1"}]}
        self.mock_events.list.return_value.execute.return_value = mock_events_result

        # Test with dict start format
        event_dict = {
            "summary": "Test Event",
            "start": {"dateTime": "2023-01-01T10:00:00"},
        }

        result = event_exists(self.mock_service, self.calendar_id, event_dict)
        self.assertTrue(result)

        # Verify correct parameters were used
        call_args = self.mock_events.list.call_args[1]
        self.assertEqual(call_args["calendarId"], self.calendar_id)
        self.assertEqual(call_args["q"], "Test Event")

        # Test with direct start format
        event_direct = {"summary": "Test Event", "start": "2023-01-01T10:00:00"}

        result = event_exists(self.mock_service, self.calendar_id, event_direct)
        self.assertTrue(result)

        # Test for event that doesn't exist
        mock_events_result = {"items": []}
        self.mock_events.list.return_value.execute.return_value = mock_events_result

        result = event_exists(self.mock_service, self.calendar_id, event_dict)
        self.assertFalse(result)
        
    def test_delete_removed_events(self):
        # Setup mock for list events
        mock_events_result = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Event 1",
                    "start": {"dateTime": "2023-01-01T10:00:00-06:00"},
                },
                {
                    "id": "event2",
                    "summary": "Event 2",
                    "start": {"dateTime": "2023-01-02T11:00:00-06:00"},
                },
                {
                    "id": "event3",
                    "summary": "Event 3",
                    "start": {"dateTime": "2023-01-03T12:00:00-06:00"},
                },
            ]
        }
        self.mock_events.list.return_value.execute.return_value = mock_events_result
        
        # Mock delete event
        mock_delete = MagicMock()
        self.mock_events.delete.return_value = mock_delete
        
        # Create scraped events (only 2 of the 3 events remain)
        scraped_events = [
            {
                "summary": "Event 1",
                "start": "2023-01-01T10:00:00-06:00",
            },
            {
                "summary": "Event 3",
                "start": "2023-01-03T12:00:00-06:00",
            },
        ]
        
        # Call the function
        result = delete_removed_events(
            self.mock_service, self.calendar_id, scraped_events
        )
        
        # Verify results
        self.assertEqual(result, 1)  # One event should be deleted
        
        # Verify the correct event was deleted
        self.mock_events.delete.assert_called_once_with(
            calendarId=self.calendar_id, eventId="event2"
        )
        
        # Test with no events to delete
        # Reset mocks
        self.mock_events.delete.reset_mock()
        
        # Now all calendar events are in scraped events
        scraped_events = [
            {
                "summary": "Event 1",
                "start": "2023-01-01T10:00:00-06:00",
            },
            {
                "summary": "Event 2",
                "start": "2023-01-02T11:00:00-06:00",
            },
            {
                "summary": "Event 3",
                "start": "2023-01-03T12:00:00-06:00",
            },
        ]
        
        # Call the function again
        result = delete_removed_events(
            self.mock_service, self.calendar_id, scraped_events
        )
        
        # Verify results
        self.assertEqual(result, 0)  # No events should be deleted
        self.mock_events.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
