from datetime import datetime, timezone
from dateutil import parser
from typing import Optional

def format_datetime(value: str, format_str: str = "%a, %d %b %H:%M") -> str:
    """Parses ISO string and formats it nicely."""
    if not value:
        return "N/A" # Or handle as needed
    try:
        # Use dateutil.parser for robust ISO parsing
        # Ensure the input is a string before parsing
        if isinstance(value, datetime):
            dt_object = value # If it's already a datetime, use it directly
        else:
             dt_object = parser.isoparse(str(value)) 
             
        # Make sure it's timezone-aware before formatting if needed, 
        # or convert to local time. For simplicity, just format.
        return dt_object.strftime(format_str)
    except (ValueError, TypeError, parser.ParserError):
        # Handle potential parsing errors gracefully
        return str(value) # Return original value (as string) if parsing fails

def datetime_now(tz: Optional[timezone] = None) -> datetime:
    """Returns the current datetime, optionally timezone-aware."""
    return datetime.now(tz) 