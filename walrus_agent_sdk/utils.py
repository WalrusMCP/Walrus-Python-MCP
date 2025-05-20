"""
Utility functions for Walrus Agent SDK.
"""
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def is_json_serializable(obj: Any) -> bool:
    """
    Check if an object is JSON serializable.
    
    Args:
        obj: The object to check
        
    Returns:
        True if serializable, False otherwise
    """
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False

def make_json_serializable(obj: Any) -> Any:
    """
    Make an object JSON serializable by converting non-serializable parts to strings.
    
    Args:
        obj: The object to convert
        
    Returns:
        JSON serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(make_json_serializable(i) for i in obj)
    elif isinstance(obj, set):
        return list(make_json_serializable(i) for i in obj)
    elif is_json_serializable(obj):
        return obj
    else:
        return str(obj)

def ensure_directory(directory_path: str):
    """
    Ensure a directory exists.
    
    Args:
        directory_path: Path to the directory
    """
    os.makedirs(directory_path, exist_ok=True)

def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a Unix timestamp as a human-readable string.
    
    Args:
        timestamp: Unix timestamp
        format_str: Format string for the output
        
    Returns:
        Formatted timestamp string
    """
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime(format_str)

def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def extract_summary(messages: List[Dict[str, str]], max_length: int = 100) -> str:
    """
    Extract a summary from conversation messages.
    
    Args:
        messages: List of conversation messages
        max_length: Maximum length of the summary
        
    Returns:
        Summary string
    """
    if not messages:
        return "No messages"
    
    # Get the last assistant message
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return truncate_text(message.get("content", ""), max_length)
    
    # If no assistant message, get the last user message
    for message in reversed(messages):
        if message.get("role") == "user":
            return f"User: {truncate_text(message.get('content', ''), max_length)}"
    
    return "No relevant messages"

def format_event_data(event_data: Dict[str, Any]) -> str:
    """
    Format event data for display.
    
    Args:
        event_data: Event data
        
    Returns:
        Formatted string
    """
    # Extract important fields
    event_type = event_data.get("type", "Unknown")
    sender = event_data.get("sender", "Unknown")
    timestamp = event_data.get("timestamp", time.time())
    
    # Format the basic info
    formatted = f"Event: {event_type}\n"
    formatted += f"Sender: {sender}\n"
    formatted += f"Time: {format_timestamp(timestamp)}\n\n"
    
    # Add other fields
    for key, value in event_data.items():
        if key not in ("type", "sender", "timestamp"):
            if isinstance(value, (dict, list)):
                formatted += f"{key}:\n{json.dumps(value, indent=2)}\n"
            else:
                formatted += f"{key}: {value}\n"
    
    return formatted

def generate_context_id() -> str:
    """
    Generate a unique context ID.
    
    Returns:
        Unique context ID string
    """
    import uuid
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries recursively.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result
