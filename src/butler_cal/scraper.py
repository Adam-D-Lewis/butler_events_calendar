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
    
    # Try different possible event container classes
    event_containers = []
    
    # First try cofaevent-row divs (seen in some pages)
    event_items = soup.find_all('div', class_='cofaevent-row')
    if event_items:
        event_containers.extend(event_items)
    
    # Also try views-row divs (seen in page_example.html)
    event_items = soup.find_all('div', class_='views-row')
    if event_items:
        event_containers.extend(event_items)
    
    # Process each event container
    for container in event_containers:
        event = {}
        
        # Get event status if available
        status_container = container.find('div', class_='views-field-field-cofaevent-status')
        if status_container:
            status_item = status_container.find('div', class_='field__item')
            if status_item:
                event['status'] = status_item.text.strip()
        
        # Get event title - try different possible locations
        title_elem = container.find('h2', class_='field-content')
        if title_elem and title_elem.a:
            event['summary'] = title_elem.a.text.strip()
            event['url'] = title_elem.a.get('href', '')
            if event['url'] and not event['url'].startswith('http'):
                event['url'] = f"https://music.utexas.edu{event['url']}"
        
        # Get event long title/subtitle if available
        subtitle_elem = container.find('h3', class_='field-content')
        if subtitle_elem:
            event['details'] = subtitle_elem.text.strip()
        
        # Get event date and time
        datetime_container = container.find('div', class_='views-field-field-cofaevent-datetime')
        if datetime_container:
            time_tags = datetime_container.find_all('time')
            if len(time_tags) >= 2:
                # If we have both start and end time tags
                try:
                    start = datetime.fromisoformat(time_tags[0]["datetime"])
                    end = datetime.fromisoformat(time_tags[1]["datetime"])
                    event['start'] = start.isoformat()
                    event['end'] = end.isoformat()
                    
                    # Also extract the human-readable date/time for display
                    date_text = time_tags[0].text.strip()
                    if date_text:
                        event['date_display'] = date_text
                except (KeyError, ValueError) as e:
                    # If datetime attribute is missing or invalid, try to parse from text
                    date_text = datetime_container.get_text(strip=True)
                    event['date_display'] = date_text
            elif len(time_tags) == 1:
                # If we only have start time, set end time to 1 hour later
                try:
                    start = datetime.fromisoformat(time_tags[0]["datetime"])
                    end = start.replace(hour=start.hour + 1)
                    event['start'] = start.isoformat()
                    event['end'] = end.isoformat()
                    event['date_display'] = time_tags[0].text.strip()
                except (KeyError, ValueError):
                    date_text = datetime_container.get_text(strip=True)
                    event['date_display'] = date_text
            else:
                # If no time tags, try to parse the text content
                date_text = datetime_container.get_text(strip=True)
                event['date_display'] = date_text
        
        # Get event location
        location_container = container.find('div', class_='views-field-field-cofaevent-location-name')
        if location_container:
            location_text = location_container.get_text(strip=True)
            event['location'] = location_text
            
            # Check for map link
            map_link = location_container.find('a', href=True)
            if map_link and 'map' in map_link.get_text(strip=True).lower():
                event['map_link'] = map_link['href']
            elif map_link and map_link.get('href'):
                # Sometimes the location itself is a link
                event['map_link'] = map_link['href']
            
            # If we have a link but no text, extract text from the link
            if not location_text and map_link:
                event['location'] = map_link.get_text(strip=True)
        
        # Get admission information
        admission_container = container.find('div', class_='views-field-field-cofaevent-admission-range')
        if admission_container:
            admission_info = admission_container.get_text(strip=True)
            event['admission_info'] = admission_info
        
        # Check if event is streamable or has ticket link
        ticket_container = container.find('div', class_='views-field-field-cofaevent-ticket-button')
        if ticket_container:
            button = ticket_container.find('a')
            if button:
                button_text = button.get_text(strip=True).lower()
                button_url = button.get('href', '')
                
                if 'stream' in button_text:
                    event['streamable'] = True
                    event['stream_link'] = button_url
                elif 'ticket' in button_text or 'buy' in button_text:
                    event['ticket_link'] = button_url
                else:
                    # Generic button
                    event['action_link'] = button_url
                    event['action_text'] = button.get_text(strip=True)
        
        # Get event details/description if available
        details_container = container.find('div', class_='views-field-field-cofaevent-details')
        if details_container:
            details_text = details_container.get_text(strip=True)
            if details_text:
                if 'details' not in event:
                    event['details'] = details_text
                else:
                    event['details'] += f" - {details_text}"
        
        # Build description
        description_parts = []
        if 'details' in event:
            description_parts.append(event['details'])
        if 'admission_info' in event:
            description_parts.append(event['admission_info'])
        if event.get('streamable') and event.get('stream_link'):
            description_parts.append(f"Stream available at: {event['stream_link']}")
        if 'status' in event and event['status'].lower() != 'scheduled':
            description_parts.append(f"Status: {event['status']}")
        
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
