import abc
import importlib
import os
import pkgutil

import yaml
from loguru import logger


# Base class for all calendar scrapers
class CalendarScraper(abc.ABC):
    """Base class for all calendar scrapers."""

    def __init__(self, name=None):
        self.name = name or self.__class__.__name__

    @abc.abstractmethod
    def get_events(self, start_date=None, end_date=None):
        """Retrieve events from calendar source.

        Args:
            start_date (datetime, optional): Only return events on or after this date
            end_date (datetime, optional): Only return events on or before this date

        Returns:
            list: List of event dictionaries with standard format
        """

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


def load_config(config_path=None):
    """Load configuration from a YAML file.

    Args:
        config_path (str, optional): Path to the config file. If None, uses default location.

    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        raise FileNotFoundError(
            "No config path provided. Looking for default locations."
        )

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return {}


def get_scraper(name, scraper_config=None):
    """Get a scraper by name.

    Args:
        name: Name of the scraper to get
        config (dict, optional): Configuration dictionary for the scraper

    Returns:
        CalendarScraper: The requested scraper instance
    """
    if name not in _registered_scrapers:
        raise ValueError(f"Scraper {name} not found")

    scraper_class = _registered_scrapers[name]

    # Inspect the scraper class __init__ to determine what parameters it accepts
    # and pass the appropriate config
    try:
        return scraper_class(**scraper_config)
    except TypeError as e:
        logger.warning(f"Failed to initialize {name} with config: {e}")
        # Fall back to default initialization
        return scraper_class()


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
