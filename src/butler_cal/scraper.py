"""
Scraper for Butler School of Music events.
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
import requests


def scrape_butler_events(url="https://music.utexas.edu/events"):
    """
    Scrape events from the Butler School of Music website.
    
    Args:
        url: URL of the events page
        
    Returns:
        List of event dictionaries with details
    """
    response = requests.get(url)
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    events = []
    
    # Find all event items - in the example page, they're in cofaevent-row divs
    event_items = soup.find_all('div', class_='cofaevent-row')
    if not event_items:
        # Fall back to the original selector if no cofaevent-row divs are found
        event_items = soup.find_all('div', class_='views-row')
    
    for item in event_items:
        event = {}
        
        # Get event title - in the example page, it's in a h2 with class field-content
        title_elem = item.find('h2', class_='field-content')
        if title_elem and title_elem.a:
            event['summary'] = title_elem.a.text.strip()
        
        # Get event long title/subtitle if available
        subtitle_elem = item.find('h3', class_='field-content')
        if subtitle_elem:
            event['details'] = subtitle_elem.text.strip()
        
        # Get event date and time
        datetime_container = item.find('div', class_='views-field-field-cofaevent-datetime')
        if datetime_container:
            time_tags = datetime_container.find_all('time')
            if len(time_tags) >= 2:
                # If we have both start and end time tags
                start = datetime.fromisoformat(time_tags[0]["datetime"])
                end = datetime.fromisoformat(time_tags[1]["datetime"])
                event['start'] = start.isoformat()
                event['end'] = end.isoformat()
            elif len(time_tags) == 1:
                # If we only have start time, set end time to 1 hour later
                start = datetime.fromisoformat(time_tags[0]["datetime"])
                end = start.replace(hour=start.hour + 1)
                event['start'] = start.isoformat()
                event['end'] = end.isoformat()
        
        # Get event location
        location_container = item.find('div', class_='views-field-field-cofaevent-location-name')
        if location_container:
            location_text = location_container.get_text(strip=True)
            event['location'] = location_text
            
            # Check for map link
            map_link = location_container.find('a', href=True)
            if map_link and 'map' in map_link.get_text(strip=True).lower():
                event['map_link'] = map_link['href']
        
        # Get admission information
        admission_container = item.find('div', class_='views-field-field-cofaevent-admission-range')
        if admission_container:
            admission_info = admission_container.get_text(strip=True)
            event['admission_info'] = admission_info
        
        # Get event status
        status_container = item.find('div', class_='views-field-field-cofaevent-status')
        if status_container:
            status_item = status_container.find('div', class_='field__item')
            if status_item:
                event['status'] = status_item.text.strip()
        
        # Check if event is streamable
        ticket_container = item.find('div', class_='views-field-field-cofaevent-ticket-button')
        if ticket_container:
            stream_button = ticket_container.find('a')
            if stream_button:
                if 'stream' in stream_button.get_text(strip=True).lower():
                    event['streamable'] = True
                    event['stream_link'] = stream_button.get('href', '')
                else:
                    event['ticket_link'] = stream_button.get('href', '')
        
        # Build description
        description_parts = []
        if 'details' in event:
            description_parts.append(event['details'])
        if 'admission_info' in event:
            description_parts.append(event['admission_info'])
        if event.get('streamable') and event.get('stream_link'):
            description_parts.append(f"Stream available at: {event['stream_link']}")
        
        event['description'] = "\n".join(description_parts)
        
        # Only add events with a title
        if 'summary' in event:
            events.append(event)
    
    return events


def parse_event_datetime(date_str, time_str):
    """
    Parse event date and time strings into a datetime object.
    
    Args:
        date_str: Date string (e.g., "Monday, March 3, 2025")
        time_str: Time string (e.g., "7:30PM")
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not time_str:
        return None
    
    try:
        # Clean up time string
        time_str = time_str.replace(' ', '')
        
        # Try different date formats
        date_formats = [
            "%A, %B %d, %Y",  # Monday, March 3, 2025
            "%a, %B %d, %Y",  # Mon, March 3, 2025
            "%A, %b %d, %Y",  # Monday, Mar 3, 2025
            "%a, %b %d, %Y",  # Mon, Mar 3, 2025
        ]
        
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if not parsed_date:
            return None
        
        # Parse time
        if 'am' in time_str.lower() or 'pm' in time_str.lower():
            time_format = "%I:%M%p"  # 7:30PM
        else:
            time_format = "%H:%M"  # 19:30
        
        time_obj = datetime.strptime(time_str, time_format)
        
        # Combine date and time
        return datetime.combine(
            parsed_date.date(),
            time_obj.time()
        )
    
    except Exception as e:
        print(f"Error parsing date/time: {e}")
        return None
