# UT Austin Calendar Scraper

This package scrapes the UT Austin music calendar and updates a Google Calendar with the events.

## Installation

Use Hatch to build and install the package.

## Usage

Run the script using the command:

```bash
update-calendar
```

Ensure you have set up your Google Calendar API credentials correctly.


## Setup

- Set up a GCP project
- Enable Google Calendar API in project
- Create a service account in the project.
- Create service account credentials in GCP (json file)
- Share target calendar with service account email address
- run script regularly
