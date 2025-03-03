from butler_cal.utils import (
    event_exists,
    get_google_calendar_service,
    scrape_utexas_calendar,
)


def test_get_google_calendar_service(mocker):
    # Create a dummy service object you expect to be returned.
    dummy_service = object()
    # Replace the actual external dependency; adjust the path to the dependency as needed.
    mocker.patch(
        "butler_cal.utils.service_account.Credentials.from_service_account_file",
        return_value=dummy_service,
    )

    service = get_google_calendar_service()
    assert (
        service == dummy_service
    ), "The google calendar service should match the dummy service"


def test_scrape_utexas_calendar():
    events = scrape_utexas_calendar()
    assert isinstance(events, list), "Expected events to be returned as a list"


def test_event_exists():
    # Dummy placeholders; adjust based on actual event structure.
    dummy_service = mocker.Mock()  # Mock the service to be used inside event_exists.
    dummy_calendar_id = "dummy-calendar"
    dummy_event = {"id": "event123", "summary": "Test Event"}

    # Assuming that for these dummy parameters, the event does not exist.
    exists = event_exists(dummy_service, dummy_calendar_id, dummy_event)
    assert exists is False, "The dummy event should not be found and thus return False"
