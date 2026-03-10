# Standard library imports
import json
import uuid
from pprint import pprint
import socket
import getpass
import logging
from pathlib import Path
from datetime import datetime, timezone
import threading
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

# Third-party/local imports
from omegaconf import OmegaConf

from pkg_infra.config import ConfigLoader
from pkg_infra.logger import configure_loggers_from_omegaconf
from pkg_infra.constants import LOG_TIMESTAMP

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

IPINFO_URL = 'https://ipinfo.io/json'

# ---- Classes


@dataclass(frozen=True)
class Session:
    """Represents a user session with environment and configuration details.

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
    started_at_utc: datetime
    started_at_local: datetime
    timezone: str | None = None
    location: str | None = None
    config: object | None = None
    session_logger: logging.Logger | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation of the session (excluding config)."""
        lines = []
        for field_name in self.__annotations__.keys():
            if field_name == 'config':
                continue
            value = getattr(self, field_name)
            lines.append(f'  {field_name}: {value}')
        return '\n'.join(lines)

    def __repr__(self) -> str:
        """Return a detailed string representation of the session for debugging (excluding config)."""
        fields = []
        for field_name in self.__annotations__.keys():
            if field_name == 'config':
                continue
            value = getattr(self, field_name)
            if isinstance(value, Path):
                fields.append(f"{field_name}=Path('{value}')")
            else:
                fields.append(f'{field_name}={value!r}')
        return f'Session({", ".join(fields)})'

    def log(self) -> None:
        """Log the string representation of the session using the module logger."""
        logger.info(str(self))

    def print_config(self) -> None:
        """Print the session config as YAML when OmegaConf, otherwise pretty-print."""
        cfg = self.config
        if cfg is None:
            logger.info('Session config is empty.')
            return

        if OmegaConf.is_config(cfg):
            print(OmegaConf.to_yaml(cfg))
            return

        pprint(cfg)

    @staticmethod
    def get_logger() -> logging.Logger | None:
        """Return the logger instance from the current session, if available.

        Returns:
            logging.Logger or None: The session logger instance, if set.
        """
        global _current_session
        return _current_session.session_logger if _current_session else None


# ---- Global variables
_current_session: Session | None = None
_session_init_lock = threading.Lock()


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


def _get_time() -> tuple[datetime, datetime]:
    """Get the current UTC and local datetime objects."""
    now_utc = datetime.now(timezone.utc)  # noqa: UP017
    now_local = datetime.now().astimezone()
    return now_utc, now_local


def _get_timezone(localtime: datetime) -> str:
    """Get the timezone name from a local datetime object."""
    return localtime.tzname()


def _get_location(timeout: float = 3.0) -> str | None:
    """Attempt to determine the user's geolocation using a public IP lookup.

    Args:
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        A string with city, region, and country if available, else None.
    """
    logger.debug('Resolving location via ipinfo.io')
    try:
        parsed = urlparse(IPINFO_URL)
        if parsed.scheme != 'https' or parsed.netloc != 'ipinfo.io':
            raise ValueError('Unsafe location lookup URL configuration.')

        with urlopen(IPINFO_URL, timeout=timeout) as response:  # nosec B310
            data = json.load(response)
            city = data.get('city')
            region = data.get('region')
            country = data.get('country')
            parts = [p for p in (city, region, country) if p]
            location = ', '.join(parts) if parts else None
            logger.debug('Resolved location: %s', location)
            return location
    except (URLError, ValueError):
        logger.warning('Location lookup failed', exc_info=True)
        return None


def _get_configuration() -> object:
    """Load and return the merged configuration using ConfigLoader."""
    logger.debug('Loading configuration via ConfigLoader')
    return ConfigLoader.load_config()


def _get_app_logger(merged_config: object) -> logging.Logger:
    """Get the application logger from the merged configuration object."""
    logger.debug('Using app logger: %s', merged_config.app.logger)
    return logging.getLogger(merged_config.app.logger)


def get_session(
    workspace: str | Path, include_location: bool = False
) -> Session:
    """Return a singleton Session object for this process, initializing it if necessary.

    Args:
        workspace: Path or string to the workspace directory.
        include_location: Whether to attempt geolocation lookup.

    Returns:
        A Session object representing the current session.
    """
    global _current_session
    logger.debug(
        'get_session called with workspace=%s, include_location=%s',
        workspace,
        include_location,
    )
    logger.info('Initialization of a session:')
    if _current_session is not None:
        logger.info('Reusing existing session')
        _current_session.log()
        return _current_session

    with _session_init_lock:
        if _current_session is None:
            config = _get_configuration()

            configure_loggers_from_omegaconf(config, timestamp=LOG_TIMESTAMP)

            app_logger = _get_app_logger(config)
            app_logger.debug('Requesting session for workspace: %s', workspace)

            hostname = _get_hostname()
            username = _get_username()
            resolved_workspace = _get_workspace(workspace)
            process_id = _get_process_id()
            now_utc, now_local = _get_time()
            timezone = _get_timezone(now_local)
            logger.debug(
                'Session time initialized: utc=%s, local=%s, timezone=%s',
                now_utc,
                now_local,
                timezone,
            )
            if include_location:
                location = _get_location()
            else:
                logger.debug('Location lookup skipped')
                location = None

            logger.info('Creating new session...')

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
                session_logger=app_logger,
            )

            logger.info('Session has been created')
        else:
            logger.info('Reusing existing session')
            _current_session.log()

    return _current_session


__all__ = ['Session', 'get_session']
