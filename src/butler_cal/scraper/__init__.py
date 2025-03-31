import importlib
import os
import pkgutil

from loguru import logger


# Base class for all calendar scrapers
class CalendarScraper:
    """Base class for all calendar scrapers."""

    def __init__(self, name=None, calendar_id=None):
        self.name = name or self.__class__.__name__
        self.calendar_id = calendar_id

    def get_events(self, start_date=None, end_date=None):
        """Retrieve events from calendar source.

        Args:
            start_date (datetime, optional): Only return events on or after this date
            end_date (datetime, optional): Only return events on or before this date

        Returns:
            list: List of event dictionaries with standard format
        """
        raise NotImplementedError("Subclasses must implement get_events()")

    def normalize_event(self, event):
        """Normalize event data to standard format.

        Args:
            event (dict): Event data in source-specific format

        Returns:
            dict: Event data in standard format
        """
        # Minimum required fields: summary, start, end
        # Additional fields: description, location, url
        return event


# Dictionary to keep track of registered scrapers
_registered_scrapers = {}


def register_scraper(scraper_class):
    """Register a calendar scraper class.

    Args:
        scraper_class: The scraper class to register

    Returns:
        The scraper class (for decorator usage)
    """
    scraper_name = scraper_class.__name__
    _registered_scrapers[scraper_name] = scraper_class
    return scraper_class


def get_registered_scrapers():
    """Get all registered calendar scrapers.

    Returns:
        dict: Dictionary mapping scraper names to scraper classes
    """
    return _registered_scrapers


def get_scraper(name):
    """Get a scraper by name.

    Args:
        name: Name of the scraper to get

    Returns:
        CalendarScraper: The requested scraper instance
    """
    if name not in _registered_scrapers:
        raise ValueError(f"Scraper {name} not found")
    return _registered_scrapers[name]()


# Import all modules in the scraper package to ensure scrapers are registered
def _discover_scrapers():
    """Discover and import all scraper modules in the package."""
    # Get the directory of the current package
    package_dir = os.path.dirname(__file__)

    # Import all modules in the directory
    for _, module_name, _ in pkgutil.iter_modules([package_dir]):
        # Don't import __init__.py
        if module_name != "__init__":
            try:
                importlib.import_module(f".{module_name}", __package__)
                logger.info(f"Imported scraper module: {module_name}")
            except ImportError as e:
                logger.error(f"Error importing {module_name}: {e}")


# Discover scrapers when this module is imported
_discover_scrapers()


# Legacy function for backward compatibility
def scrape_utexas_calendar():
    """Legacy function that gets events from the Butler Music scraper."""
    from .scrape_butler_music import ButlerMusicScraper

    return ButlerMusicScraper().get_events()
