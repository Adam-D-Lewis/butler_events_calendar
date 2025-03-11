# Butler School of Music at UT Austin Calendar Scraper

| Information | Links |
| :---------- | :-----|
| Calendar Update Status | [![Calendar Update Status]](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/run_weekly.yaml) |
| CI | [![Tests](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml/badge.svg)](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml) |

This package scrapes the UT Austin music calendar and updates a Google Calendar with the events.  If you just want to subscribe to the calendar, [click this link](https://calendar.google.com/calendar/u/0?cid=OWM1NDk4ODU5NTFiOTkxMDA1YjE4NTE5OGFiYjVmN2U5ZmI2YmE4Y2E4YWExN2ZmNmMxNjZiMTYxMWU3ZjBhZkBncm91cC5jYWxlbmRhci5nb29nbGUuY29t) after logging into your Google account.

## Installation

Use Hatch to build and install the package.

## Usage

Run the script using the command:

```bash
python -m butler_cal
# or to delete events
python -m butler_cal --delete-all
```

Ensure you have set up your Google Calendar API credentials correctly.


## Setup

- Set up a GCP project
- Enable Google Calendar API in project
- Create a service account in the project.
- Create service account credentials in GCP (json file)
- Share target calendar with service account email address
- set CALENDAR_ID and one of SA_CREDENTIALS or SA_CREDENTIALS_PATH env vars.
- run script regularly
