from datetime import datetime, timezone
from dateutil import parser
from typing import Optional, Union

def format_datetime(value: Union[datetime, str, None], format_str: str = "%a, %d %b %H:%M") -> str:
    """Formats a datetime object or parses an ISO string, returns formatted string or N/A."""
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
        # Attempt to format. This works reliably for naive datetimes.
        # For timezone-aware, strftime behavior can vary. 
        # Consider converting to local time first if timezone consistency is critical:
        # dt_local = dt_object.astimezone() 
        # return dt_local.strftime(format_str)
        # For now, directly format:
        return dt_object.strftime(format_str)
    except (ValueError, TypeError) as e:
        # Handle errors during formatting (e.g., invalid format string)
        print(f"[ERROR] Failed to format datetime '{dt_object}': {e}")
        return "Invalid Date"

def datetime_now(tz: Optional[timezone] = None) -> datetime:
    """Returns the current datetime, optionally timezone-aware."""
    return datetime.now(tz) 