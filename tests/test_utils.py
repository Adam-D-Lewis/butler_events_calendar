from butler_cal.utils import (
    event_exists,
    get_google_calendar_service,
    scrape_utexas_calendar,
)


def test_get_google_calendar_service(mocker):
    # Create a dummy service object you expect to be returned.
    dummy_credentials = mocker.Mock()
    dummy_credentials.authorize.return_value = object()  # dummy authorized http client
    mocker.patch(
        "butler_cal.utils.service_account.Credentials.from_service_account_file",
        return_value=dummy_credentials,
    )

    service = get_google_calendar_service()
    assert (
        service == dummy_credentials.authorize.return_value
    ), "The google calendar service should match the authorized dummy object"


def test_scrape_utexas_calendar():
    events = scrape_utexas_calendar()
    assert isinstance(events, list), "Expected events to be returned as a list"


def test_event_exists(mocker):
    # Dummy placeholders; adjust based on actual event structure.
    dummy_service = mocker.Mock()  # Mock the service to be used inside event_exists.
    dummy_service.events.return_value.list.return_value.execute.return_value = {
        "items": []
    }
    dummy_calendar_id = "dummy-calendar"
    dummy_event = {
        "id": "event123",
        "summary": "Test Event",
        "start": "2023-10-01T10:00:00",
    }

    # Assuming that for these dummy parameters, the event does not exist.
    exists = event_exists(dummy_service, dummy_calendar_id, dummy_event)
    assert exists is False, "The dummy event should not be found and thus return False"
