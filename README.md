# Multi-Source Event Calendar Scraper

| Information | Links |
| :---------- | :-----|
| Last Successful Calendar Sync | [![Last Calendar Sync](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.github.com%2Frepos%2FAdam-D-Lewis%2Fbutler_events_calendar%2Factions%2Fworkflows%2F148948811%2Fruns%3Fquery%3Dbranch%253Amain%2Bis%253Asuccess%26per_page%3D1&query=%24.workflow_runs%5B0%5D.run_started_at&label=Date%3A&color=brightgreen)](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/run_weekly.yaml?query=branch%3Amain+is%3Asuccess) |
| CI | [![Tests](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml/badge.svg)](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml) |

This package scrapes multiple event sources and updates a Google Calendar with the events. Originally developed for the UT Austin Butler School of Music events, it now supports additional event sources including the Pflugerville Library.

If you just want to subscribe to the calendar, [click this link](https://calendar.google.com/calendar/u/0?cid=OWM1NDk4ODU5NTFiOTkxMDA1YjE4NTE5OGFiYjVmN2U5ZmI2YmE4Y2E4YWExN2ZmNmMxNjZiMTYxMWU3ZjBhZkBncm91cC5jYWxlbmRhci5nb29nbGUuY29t) after logging into your Google account.

## Installation

Use pip to install the package:

```bash
pip install butler-cal
```

Or install from source:

```bash
pip install .
```

## Available Event Sources

The system currently supports the following event sources:

- ButlerMusicScraper: UT Austin Butler School of Music events
- PflugervilleLibraryScraper: Pflugerville Public Library events

To see all available scrapers, run:

```bash
python -m butler_cal --list-scrapers
```

## Usage

### Basic Commands

```bash
# Add events from all available scrapers
python -m butler_cal

# Add events from specific scrapers
python -m butler_cal --scrapers ButlerMusicScraper PflugervilleLibraryScraper

# Sync calendar (add new events and remove events that no longer exist)
python -m butler_cal --sync

# Delete all events from calendar
python -m butler_cal --delete-all
```

### Advanced Options

```bash
# Specify a different date range (90 days back, 180 days ahead)
python -m butler_cal --days-back 90 --days-ahead 180

# Specify a specific calendar ID
python -m butler_cal --calendar-id "your_calendar_id@group.calendar.google.com"

# Dry run (don't actually modify calendar)
python -m butler_cal --dry-run --sync
```

### Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--list-scrapers` | List all available scrapers and exit |
| `--scrapers SCRAPER [SCRAPER ...]` | List of specific scrapers to use |
| `--sync` | Sync calendar by removing events that no longer exist in the scraped sources |
| `--delete-all` | Delete all events from the calendar |
| `--calendar-id CALENDAR_ID` | Google Calendar ID to use (defaults to CALENDAR_ID environment variable) |
| `--days-back DAYS_BACK` | Number of days in the past to fetch events (default: 7) |
| `--days-ahead DAYS_AHEAD` | Number of days in the future to fetch events (default: 90) |
| `--dry-run` | Show what events would be added/removed without making changes |

## Environment Variables

- `CALENDAR_ID`: Google Calendar ID (if not specified with `--calendar-id`)
- `SA_CREDENTIALS`: Service account credentials JSON (inline)
- `SA_CREDENTIALS_PATH`: Path to service account credentials JSON file

## Setup

1. Set up a Google Cloud Platform (GCP) project
2. Enable Google Calendar API in the project
3. Create a service account in the project
4. Create service account credentials in GCP (JSON file)
5. Share your target calendar with the service account email address
6. Set the `CALENDAR_ID` environment variable to your calendar ID
7. Set either `SA_CREDENTIALS` or `SA_CREDENTIALS_PATH` environment variable
8. Run the script regularly via cron or other scheduling tool

## Adding Custom Scrapers

You can add custom scrapers by creating a new class that inherits from `CalendarScraper` and implementing the required methods:

```python
from butler_cal.scraper import CalendarScraper, register_scraper

@register_scraper
class MyCustomScraper(CalendarScraper):
    """My custom event scraper."""

    def __init__(self):
        super().__init__(name="MyCustomScraper")
        # Your initialization code here

    def get_events(self, start_date=None, end_date=None):
        """Return events from your source."""
        # Your implementation here
        return [...]  # Return a list of event dictionaries
```

Each event dictionary should have at minimum the following fields:
- `summary`: Event title
- `start`: Start time in ISO format
- `end`: End time in ISO format
- `description`: Event description
- `location`: Event location (optional)
- `url`: Event URL (optional)
