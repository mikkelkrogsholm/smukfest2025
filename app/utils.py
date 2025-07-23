from datetime import datetime, timezone, timedelta
from dateutil import parser
from typing import Optional, Union

def get_festival_day(event_time: datetime) -> datetime:
    """
    Returns the festival day date for an event.
    Events between 00:00-05:59 belong to the previous day's festival program.
    
    Args:
        event_time: The actual datetime of the event
        
    Returns:
        The festival day date (as datetime with time set to 00:00)
    """
    if event_time.hour < 6:
        # Events before 6am belong to previous day's festival program
        festival_date = event_time - timedelta(days=1)
    else:
        festival_date = event_time
    
    # Return date at midnight for consistency
    return festival_date.replace(hour=0, minute=0, second=0, microsecond=0)

def get_festival_day_name(event_time: datetime, lang: str = 'da') -> str:
    """
    Returns the festival day name for an event.
    
    Args:
        event_time: The actual datetime of the event
        lang: Language code ('da' for Danish, 'en' for English)
        
    Returns:
        The day name (e.g., "Onsdag" or "Wednesday")
    """
    festival_date = get_festival_day(event_time)
    
    if lang == 'da':
        danish_days = {
            'Monday': 'Mandag',
            'Tuesday': 'Tirsdag', 
            'Wednesday': 'Onsdag',
            'Thursday': 'Torsdag',
            'Friday': 'Fredag',
            'Saturday': 'Lørdag',
            'Sunday': 'Søndag'
        }
        english_day = festival_date.strftime('%A')
        return danish_days.get(english_day, english_day)
    else:
        return festival_date.strftime('%A')

def format_datetime(value: Union[datetime, str, None], format_str: str = "%a, %d %b %H:%M", use_festival_day: bool = False) -> str:
    """
    Formats a datetime object or parses an ISO string, returns formatted string or N/A.
    
    Args:
        value: Datetime object, ISO string, or None
        format_str: strftime format string
        use_festival_day: If True, adjusts day display for festival schedule (00:00-05:59 = previous day)
    """
    dt_object: Optional[datetime] = None
    
    if isinstance(value, datetime):
        dt_object = value
    elif isinstance(value, str):
        try:
            dt_object = parser.isoparse(value)
        except (ValueError, parser.ParserError):
            pass # Failed to parse string, dt_object remains None
    
    if dt_object is None:
        return "N/A" # Return N/A if input was None or failed to parse
    
    try:
        if use_festival_day and dt_object.hour < 6:
            # For festival schedule: events between 00:00-05:59 belong to previous day
            # We need to adjust the display while keeping the time
            
            # If format includes day name (%A or %a), we need special handling
            if '%A' in format_str or '%a' in format_str:
                # Get the festival day name
                festival_day_name = get_festival_day_name(dt_object, lang='da')
                
                # Create a temporary format without day names
                temp_format = format_str.replace('%A', '{}').replace('%a', '{}')
                
                # Format the datetime normally
                time_part = dt_object.strftime(temp_format)
                
                # Insert the festival day name
                if '%A' in format_str:
                    return time_part.format(festival_day_name)
                else:  # %a - abbreviated
                    # Create abbreviated version (first 3 letters)
                    abbrev = festival_day_name[:3]
                    return time_part.format(abbrev)
            else:
                # No day names in format, just format normally
                return dt_object.strftime(format_str)
        else:
            # Normal formatting - no festival day adjustment needed
            return dt_object.strftime(format_str)
    except (ValueError, TypeError) as e:
        # Handle errors during formatting (e.g., invalid format string)
        print(f"[ERROR] Failed to format datetime '{dt_object}': {e}")
        return "Invalid Date"

def datetime_now(tz: Optional[timezone] = None) -> datetime:
    """Returns the current datetime, optionally timezone-aware."""
    return datetime.now(tz) 