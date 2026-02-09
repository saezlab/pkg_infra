
# Standard library imports
import getpass
import json
import logging
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from typing import Optional, Any

# Third-party/local imports
from saezlab_core.logger import configure_loggers_from_omegaconf
from saezlab_core.config import ConfigLoader
from saezlab_core import __log_timestamp__

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---- Classes


@dataclass(frozen=True)
class Session:
    """
    Represents a user session with environment and configuration details.

    Attributes:
        hostname: Hostname of the machine.
        username: Username of the user.
        workspace: Path to the workspace directory.
        id: Unique session identifier.
        started_at_utc: UTC timestamp when the session started.
        started_at_local: Local timestamp when the session started.
        timezone: Local timezone name.
        location: Geolocation string (city, region, country).
        config: Loaded configuration object.
        session_logger: Logger instance for the session.
    """
    hostname: str
    username: str
    workspace: Path
    id: str
    started_at_utc: str
    started_at_local: str
    timezone: Optional[str] = None
    location: Optional[str] = None
    config: Optional[Any] = None
    session_logger: Optional[logging.Logger] = None

    def __str__(self) -> str:
        """Return a human-readable string representation of the session (excluding config)."""
        lines = []
        for field_name in self.__annotations__.keys():
            if field_name == "config":
                continue
            value = getattr(self, field_name)
            lines.append(f"  {field_name}: {value}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return a detailed string representation of the session for debugging (excluding config)."""
        fields = []
        for field_name in self.__annotations__.keys():
            if field_name == "config":
                continue
            value = getattr(self, field_name)
            if isinstance(value, Path):
                fields.append(f"{field_name}=Path('{value}')")
            else:
                fields.append(f"{field_name}={value!r}")
        return f"Session({', '.join(fields)})"

    def log(self) -> None:
        """Log the string representation of the session using the module logger."""
        logger.info(str(self))

    @staticmethod
    def get_logger():
        """
        Return the logger instance from the current session, if available.

        Returns:
            logging.Logger or None: The session logger instance, if set.
        """
        global _current_session
        return _current_session.session_logger if _current_session else None


# ---- Global variables
_current_session: Optional[Session] = None

# ---- Private helper functions
def _get_hostname() -> str:
    """Get the current machine's hostname."""
    return socket.gethostname()

def _get_username() -> str:
    """Get the current user's username."""
    return getpass.getuser()

def _get_workspace(workspace: Path | str) -> Path:
    """Resolve and return the absolute path to the workspace."""
    return Path(workspace).expanduser().resolve()

def _get_process_id() -> str:
    """Generate a new unique process/session ID (UUID4)."""
    return str(uuid.uuid4())

def _get_time():
    """Get the current UTC and local datetime objects."""
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()
    return now_utc, now_local

def _get_timezone(localtime: datetime) -> str:
    """Get the timezone name from a local datetime object."""
    return localtime.tzname()

def _get_location(timeout: float = 3.0) -> Optional[str]:
    """
    Attempt to determine the user's geolocation using a public IP lookup.

    Args:
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        A string with city, region, and country if available, else None.
    """
    logger.debug("Resolving location via ipinfo.io")
    try:
        with urlopen("https://ipinfo.io/json", timeout=timeout) as response:
            data = json.load(response)
            city = data.get("city")
            region = data.get("region")
            country = data.get("country")
            parts = [p for p in (city, region, country) if p]
            location = ", ".join(parts) if parts else None
            logger.debug("Resolved location: %s", location)
            return location
    except (URLError, ValueError):
        logger.warning("Location lookup failed", exc_info=True)
        return None

def _get_configuration():
    """Load and return the merged configuration using ConfigLoader."""
    return ConfigLoader.load_config()

def _get_app_logger(merged_config) -> logging.Logger:
    """Get the application logger from the merged configuration object."""
    return logging.getLogger(merged_config.app.logger)


def get_session(workspace: str | Path, include_location: bool = True) -> Session:
    """
    Return a singleton Session object for this process, initializing it if necessary.

    Args:
        workspace: Path or string to the workspace directory.
        include_location: Whether to attempt geolocation lookup.

    Returns:
        A Session object representing the current session.
    """
    global _current_session
    logger.info("Initialization of a session:")
    if _current_session is None:
        
        config = _get_configuration()
        
        configure_loggers_from_omegaconf(config, timestamp=__log_timestamp__)
        
        app_logger = _get_app_logger(config)
        app_logger.debug("Requesting session for workspace: %s", workspace)
        
        hostname = _get_hostname()
        
        username = _get_username()
        
        resolved_workspace = _get_workspace(workspace)
        
        process_id = _get_process_id()
        
        now_utc, now_local = _get_time()
        
        timezone = _get_timezone(now_local)
        
        location = _get_location() if include_location else None
        
        logger.info("Creating new session...")
        
        _current_session = Session(
            hostname=hostname,
            username=username,
            workspace=resolved_workspace,
            id=process_id,
            started_at_utc=now_utc,
            started_at_local=now_local,
            timezone=timezone,
            location=location,
            config=config,
            session_logger=app_logger
        )

        logger.info("Session has been created")
    else:
        logger.info("Reusing existing session")
        _current_session.log()
    return _current_session



__all__ = ["Session", "get_session"]
