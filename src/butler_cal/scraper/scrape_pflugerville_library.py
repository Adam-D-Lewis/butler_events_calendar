"""Scraper for Pflugerville Library events."""

import re
from typing import Literal
import warnings
from datetime import datetime, timedelta

from collections import defaultdict
from zoneinfo import ZoneInfo
import requests
from loguru import logger
from urllib3.exceptions import InsecureRequestWarning
from pydantic import BaseModel, Field

from butler_cal.scraper import CalendarScraper, register_scraper

# Suppress only the InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class CategoryMap(BaseModel):
    """Model for category mapping."""

    category: str
    calendar_id: str


class PflugervilleLibraryScraperInput(BaseModel):
    """Input model for Pflugerville Library Scraper."""

    category_calendar_id_map: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of category names to calendar ids"
    )
    default_calendar_id: str = Field(
        None, description="Default calendar ID for events without a specific category"
    )

    # Constants
    BASE_URL: Literal[
        "https://content.civicplus.com/api/content/tx-pflugerville/event"
    ] = Field(
        "https://content.civicplus.com/api/content/tx-pflugerville/event",
        description="Base URL for the API endpoint to fetch events",
    )
    TOKEN_URL: Literal["https://www.pflugervilletx.gov/372/Library-Event-Calendar"] = (
        Field(
            "https://www.pflugervilletx.gov/372/Library-Event-Calendar",
            description="URL to fetch the authentication token",
        )
    )


@register_scraper
class PflugervilleLibraryScraper(CalendarScraper):
    """Scraper for Pflugerville Library events."""

    # TODO: Add __repr__ showing input parameters

    def __init__(self, **kwargs):
        super().__init__()
        input = PflugervilleLibraryScraperInput(**kwargs)
        self.default_calendar_id = input.default_calendar_id
        self.category_calendar_id_map = input.category_calendar_id_map
        self.base_url = input.BASE_URL
        self.hcms_client_token = self._get_token_from_html(input.TOKEN_URL)
        self.headers = {
            "Authorization": self.hcms_client_token,
            "Content-Type": "application/json",
        }
        self.page_size = 50
        self.category_ids = {  # Adding the category Ids for ease of use in my script.
            "Library": "129e1957-debe-4e2e-9acb-068c54de7c71",  # TODO: Detect if these change, or if other categories show up
            "Library Adults": "aa24aafd-f4c6-42ea-a20b-2b2a9ca5871a",
            "Library Heritage House": "0cb84828-caaa-41a4-b2b1-627d1471114b",
            "Library Kids": "d26ae5af-abcd-4b92-b4d1-e6a8f8484221",
            "Library Senior": "dcef2beb-b370-4376-a147-d02ddcb99a1f",
            "Library Teens": "89c887d9-c5d7-4a2b-bcca-f0ce553b2f8e",
            "Library Tweens": "12837e41-f43f-40e2-9649-ddbd2efcfb24",
        }

    def _get_token_from_html(self, url):
        """Get authentication token from the page HTML.

        Args:
            url: URL to fetch token from

        Returns:
            str: Authentication token or None if not found
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        if url != "https://www.pflugervilletx.gov/372/Library-Event-Calendar":
            raise ValueError(
                "Invalid URL provided. Expected the library event calendar URL."
            )
        try:
            response = requests.get(
                url, headers=headers, verify=False, allow_redirects=True
            )
            response.raise_for_status()
            html = response.text
            match = re.search(r'window\.hcmsClientToken\s*=\s*"(Bearer [^"]+)"', html)
            if match:
                return match.group(1)
            else:
                # Try a broader search for the token pattern itself
                match = re.search(r'"(Bearer [a-zA-Z0-9\._\-\+/=]+)"', html)
                if match:
                    logger.debug("Found token with broader regex.")
                    return match.group(1)
                else:
                    logger.warning(
                        "hcmsClientToken not found in HTML with primary or broader regex."
                    )
                    # Print a snippet for debugging
                    snippet_length = 500
                    logger.debug(f"HTML snippet (length {len(html)}):")
                    if len(html) > snippet_length:
                        logger.debug(html[:snippet_length] + "...")
                    else:
                        logger.debug(html)
                    return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching HTML: {e}")
            return None

    def _get_events(
        self,
        skip=0,
        start_date=None,
        end_date=None,
        tag=None,
    ):
        """Internal helper function to fetch events from the API.

        Args:
            skip (int):  The number of events to skip (for pagination).
            start_date (datetime, optional): Filter events starting on or after this date. Defaults to None.
            end_date (datetime, optional): Filter events ending on or before this date. Defaults to None.
            tag (str, optional): Filter events with this tag. Defaults to None.

        Returns:
            tuple: A tuple containing:
                - (list): A list of event dictionaries, or an empty list if there's an error.
                - (int): The total number of events available (from the API's `total` field), or None if there's an error.
        """
        params = {
            "$top": self.page_size,
            "$skip": skip,
        }
        # Build the $filter string
        filter_parts = []

        if tag:
            filter_parts.append(f"tags/any(t: t eq '{tag}')")

        if start_date and end_date:
            start_date_str = (
                start_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            )  # Limit to milliseconds
            end_date_str = (
                end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            )  # Limit to milliseconds
            filter_parts.append(
                f"data/eventdate/iv/endDate ge {start_date_str} and data/eventdate/iv/startDate le {end_date_str}"
            )
        elif start_date:
            start_date_str = (
                start_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            )  # Limit to milliseconds
            filter_parts.append(f"data/eventdate/iv/endDate ge {start_date_str}")
        elif end_date:
            end_date_str = (
                end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            )  # Limit to milliseconds

        if filter_parts:
            params["$filter"] = " and ".join(filter_parts)  # Combine all conditions

        # # URL-encode the filter to handle special characters
        # if "$filter" in params:
        #     params["$filter"] = quote(params["$filter"])  # important for spaces

        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            return data.get("items", []), data.get(
                "total"
            )  # Return events and total, handle missing keys
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return [], None  # Return empty list and None on error
        except ValueError as e:
            logger.error(f"JSON decoding failed: {e}")
            return [], None

    def get_events(
        self, start_date=None, end_date=None, tag="Library", category=None
    ) -> dict[str, list]:
        """Retrieves all events, handling pagination.

        Args:
            start_date (datetime, optional): Filter events starting on or after this date. Defaults to None.
            end_date (datetime, optional): Filter events ending on or before this date. Defaults to None.
            tag (str, optional): Filter events with this tag. Defaults to "Library".
            category (str, optional): Filter events with this category id. Defaults to None.

        Returns:
            list: A list of all event dictionaries in standard format.
        """
        # Default date range is next 30 days if not specified
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=30)

        all_events = []
        skip = 0
        total_events = None  # Initialize total_events

        while True:
            events, total = self._get_events(
                skip=skip,
                start_date=start_date,
                end_date=end_date,
                tag=tag,
            )
            if events is None:  # API error
                logger.error("Error fetching events. Aborting.")
                return []

            # Normalize events to standard format
            normalized_events = [self.normalize_event(event) for event in events]
            all_events.extend(normalized_events)

            if total_events is None:  # Get the Total
                total_events = total  # Set total_events on the first iteration

            if (
                total_events is not None and len(all_events) >= total_events
            ):  # Reached the end
                break

            if (
                len(events) < self.page_size
            ):  # Last page has less than maximum, so no more pages
                break
            skip += self.page_size

        event_dict = defaultdict(
            list
        )  # Create a dictionary to categorize events by calendar_id
        for event in all_events:
            # add to dict
            for category in event.get("categories", []):
                if category in self.category_calendar_id_map:
                    calendar_id = self.category_calendar_id_map[category]
                else:
                    calendar_id = self.default_calendar_id
                event_dict[calendar_id].append(event)

        return event_dict

    def normalize_event(self, event):
        """Convert event from Pflugerville API format to standard format.

        Args:
            event (dict): Event from Pflugerville API

        Returns:
            dict: Event in standard format
        """
        try:
            # Basic information
            summary = event["data"]["title"]["en"]
            description = event["data"]["description"]["en"]

            # Date information - need to convert to standard format
            start_time = event["data"]["eventdate"]["iv"]["startDate"]
            end_time = event["data"]["eventdate"]["iv"]["endDate"]

            # Convert to datetime objects, then back to ISO format
            start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
            end_dt = datetime.fromisoformat(end_time.replace("Z", ""))

            # Apply timezone information
            utc_tz = ZoneInfo("UTC")
            local_tz = ZoneInfo("America/Chicago")

            start_dt = start_dt.replace(tzinfo=utc_tz).astimezone(local_tz)
            end_dt = end_dt.replace(tzinfo=utc_tz).astimezone(local_tz)

            # Build location if available
            location = None
            if "location" in event["data"] and "en" in event["data"]["location"]:
                location = event["data"]["location"]["en"]

            # Build URL if available
            url = None
            if "id" in event:
                url = f"https://tx-pflugerville.civicplus.com/calendar.aspx?EID={event['id']}"

            # Extract category information if available
            categories = []
            if "categories" in event:
                for category in event.get("categories", []):
                    if "name" in category:
                        categories.append(category["name"])

            # Determine calendar_id based on category
            target_calendar_id = self.default_calendar_id
            for category in categories:
                if category in self.category_calendar_id_map:
                    target_calendar_id = self.category_calendar_id_map[category]
                    break

            # Create standardized event object
            return {
                "summary": summary,
                "description": description,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "location": location,
                "url": url,
                "source": "pflugerville_library",
                "categories": categories,
                "calendar_id": target_calendar_id,
            }
        except (KeyError, ValueError) as e:
            logger.error(f"Error normalizing event: {e}")
            # Return minimal valid event if possible
            if (
                "data" in event
                and "title" in event["data"]
                and "en" in event["data"]["title"]
            ):
                return {
                    "summary": event["data"]["title"]["en"],
                    "description": "Error processing complete event data",
                    "start": datetime.now().isoformat(),
                    "end": (datetime.now() + timedelta(hours=1)).isoformat(),
                }
            return None
