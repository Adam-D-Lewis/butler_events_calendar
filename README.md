# Pflugerville, TX Area Event Calendar Scraper

| Information | Links |
| :---------- | :-----|
| Last Successful Calendar Sync | [![Last Calendar Sync](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.github.com%2Frepos%2FAdam-D-Lewis%2Fbutler_events_calendar%2Factions%2Fworkflows%2F148948811%2Fruns%3Fquery%3Dbranch%253Amain%2Bis%253Asuccess%26per_page%3D1&query=%24.workflow_runs%5B0%5D.run_started_at&label=Date%3A&color=brightgreen)](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/run_weekly.yaml?query=branch%3Amain+is%3Asuccess) |
| Code Test Status | [![Tests](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml/badge.svg)](https://github.com/Adam-D-Lewis/butler_events_calendar/actions/workflows/test.yaml) |

This package scrapes multiple event sources and updates a Google Calendar with the events. Originally developed for the UT Austin Butler School of Music events, it now supports additional event sources including the Pflugerville Library.

If you just want to subscribe to the calendar, log into your google account and then click the appropriate link.
| Events Calendar |
| :---- |
| [UT Austin Butler School of Music](https://calendar.google.com/calendar/u/0?cid=OWM1NDk4ODU5NTFiOTkxMDA1YjE4NTE5OGFiYjVmN2U5ZmI2YmE4Y2E4YWExN2ZmNmMxNjZiMTYxMWU3ZjBhZkBncm91cC5jYWxlbmRhci5nb29nbGUuY29t) |
| [Pflugerville Library Kids](https://calendar.google.com/calendar/embed?src=bf33977cdb5a9d9c89b82a0e58f9f65c6218fd0c0cc57d17f0457528d5776adc%40group.calendar.google.com&ctz=America%2FChicago) |
| [Pflugerville Library Tweens](https://calendar.google.com/calendar/embed?src=c12c3074906ecdee821298e9fd312fdf676a9768dcfef63ec3a798a4f77cd81e%40group.calendar.google.com&ctz=America%2FChicago) |
| [Pflugerville Library Teens](https://calendar.google.com/calendar/embed?src=acd1cb558b56fac27eb4ffc907d8af4c3d757fe7e7a4ea60ff15dc5d3218070d%40group.calendar.google.com&ctz=America%2FChicago) |
| [Pflugerville Library Adults](https://calendar.google.com/calendar/embed?src=c564684a6bab63a8c34e04623ce2fd3d2923b346c4fd88bb52ffc9055e9baf5f%40group.calendar.google.com&ctz=America%2FChicago) |
| [Pflugerville Library Senior](https://calendar.google.com/calendar/embed?src=9cf3ad7b4b9536bf3c5d7e0ec0836f8591ec9e02b43421bca387dfcf5cfa6b65%40group.calendar.google.com&ctz=America%2FChicago) |
| [Pflugerville Library Heritage House](https://calendar.google.com/calendar/embed?src=8f561b47740b57b6a5b32a3f71e371c0e7ca339ebbb19bc68c3f744bd424d8b0%40group.calendar.google.com&ctz=America%2FChicago) |

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
python -m butler_cal sync --scrapers ButlerMusicScraper --scrapers PflugervilleLibraryScraper

# Delete all events from calendar
python -m butler_cal --delete-all \<calendar-id\>
```

## Configuration

### Environment Variables

- `SA_CREDENTIALS`: Service account credentials JSON (inline)
- `SA_CREDENTIALS_PATH`: Path to service account credentials JSON file

### Configuration File

You can specify scraper configurations in a YAML file (`scraper_config.yaml`). This file is automatically loaded from the `src/butler_cal` directory, or you can specify a custom path with the `--config` option.

Example configuration:

```yaml
ButlerMusic:
  calendar_id: your_calendar_id@group.calendar.google.com

PflugervilleLibrary:
  calendar_id: default_calendar_id@group.calendar.google.com
  category_map:
    Library: library_events_calendar_id@group.calendar.google.com
    Library Kids: kids_events_calendar_id@group.calendar.google.com
    Library Adults: adults_events_calendar_id@group.calendar.google.com
```

This configuration lets you:
- Specify a default calendar ID for each scraper
- Map specific event categories to different calendars (for scrapers that support categories)

## Setup

1. Set up a Google Cloud Platform (GCP) project
2. Enable Google Calendar API in the project
3. Create a service account in the project
4. Create service account credentials in GCP (JSON file)
5. Share your target calendar with the service account email address
6. Set either `SA_CREDENTIALS` or `SA_CREDENTIALS_PATH` environment variable
7. Run the script regularly via cron or other scheduling tool

## Adding Custom Scrapers

You can add custom scrapers by creating a new class that inherits from `CalendarScraper` and implementing the required methods:

```python
from butler_cal.scraper import CalendarScraper, register_scraper

@register_scraper
class MyCustomScraper(CalendarScraper):
    """My custom event scraper."""

    def __init__(self, calendar_id=None, custom_setting=None):
        super().__init__(name="MyCustomScraper")
        self.calendar_id = calendar_id
        self.custom_setting = custom_setting
        # Your initialization code here

    def get_events(self, start_date=None, end_date=None):
        """Return events from your source."""
        # Your implementation here
        return [...]  # Return a list of event dictionaries
```

Your custom scraper can then be configured in the YAML configuration file:

```yaml
MyCustomScraper:
  calendar_id: your_calendar_id@group.calendar.google.com
  custom_setting: some_value
```


Each event dictionary should have at minimum the following fields:
- `summary`: Event title
- `start`: Start time in ISO format
- `end`: End time in ISO format
- `description`: Event description
- `location`: Event location (optional)
- `url`: Event URL (optional)
- `calendar_id`: Target Google Calendar ID (optional, uses default if not provided)
