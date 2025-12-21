# app/request_logger.py
# Logging system for API requests and responses (max 100 entries)

from datetime import datetime
from typing import Dict, Any, List
import json
import os
from pathlib import Path
import threading

# File path for storing logs
LOG_FILE_PATH = Path(__file__).parent.parent / "logs" / "api_requests.json"

# Thread lock for file operations
_file_lock = threading.Lock()


def _ensure_log_file_exists():
    """
    Ensure the log file and directory exist.
    """
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE_PATH.exists():
        LOG_FILE_PATH.write_text("[]")


def _read_logs_from_file() -> List[Dict[str, Any]]:
    """
    Read logs from the file.
    """
    _ensure_log_file_exists()
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _write_logs_to_file(logs: List[Dict[str, Any]]):
    """
    Write logs to the file.
    """
    _ensure_log_file_exists()
    with open(LOG_FILE_PATH, 'w') as f:
        json.dump(logs, f, indent=2)


def log_request(
    request_id: str,
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    status_code: int,
    error: str = None
):
    """
    Log an API request/response pair to file.
    Automatically maintains only the last 100 entries.
    
    Args:
        request_id: Unique request identifier
        request_data: The incoming request payload (complete JSON)
        response_data: The API response payload (complete JSON)
        status_code: HTTP status code
        error: Error message if request failed
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "status_code": status_code,
        "request": request_data,  # Log complete request payload
        "response": response_data,  # Log complete response payload
        "error": error
    }
    
    with _file_lock:
        logs = _read_logs_from_file()
        logs.append(log_entry)
        
        # Keep only the last 100 entries
        if len(logs) > 100:
            logs = logs[-100:]
        
        _write_logs_to_file(logs)


def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent log entries from file.
    
    Args:
        limit: Maximum number of entries to return (default 100)
        
    Returns:
        List of log entries, most recent first
    """
    with _file_lock:
        logs = _read_logs_from_file()
        logs.reverse()  # Most recent first
        return logs[:limit]


def get_logs_json() -> str:
    """
    Get logs as formatted JSON string.
    """
    return json.dumps(get_logs(), indent=2)


def clear_logs():
    """
    Clear all log entries.
    """
    with _file_lock:
        _write_logs_to_file([])


def get_log_count() -> int:
    """
    Get the current number of log entries.
    """
    with _file_lock:
        logs = _read_logs_from_file()
        return len(logs)
