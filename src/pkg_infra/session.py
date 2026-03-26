"""Session lifecycle management and runtime metadata helpers."""

# Standard library imports
import json
import uuid
from pprint import pprint
import socket
import getpass
import logging
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import threading
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen
from collections.abc import Mapping

# Third-party
from omegaconf import OmegaConf, DictConfig

# First-party imports
from pkg_infra.config import ConfigLoader
from pkg_infra.logger import LoggerConfigurator
from pkg_infra.constants import IPINFO_URL, LOG_TIMESTAMP

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---- Type aliases
# Flexible config type: OmegaConf or any mapping.
ConfigLike = Mapping[str, object] | DictConfig

# ---- Classes


@dataclass(frozen=True)
class Session:
    """Represents a user session with runtime metadata and configuration.

    This class is not intended to be instantiated directly; use
    SessionManager.get_session() to obtain the singleton session.

    Attributes:
        hostname: Hostname of the machine.
        username: Username of the user.
        workspace: Absolute path to the workspace directory.
        id: Unique session identifier.
        started_at_utc: UTC timestamp when the session started.
        started_at_local: Local timestamp when the session started.
        timezone: Local timezone name.
        location_enabled: Whether lazy location lookup is enabled.
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
    location_enabled: bool = False
    _location: str | None = None
    config: ConfigLike | None = None
    session_logger: logging.Logger | None = None

    @classmethod
    def create(
        cls,
        *,
        hostname: str,
        username: str,
        workspace: Path,
        process_id: str,
        now_utc: datetime,
        now_local: datetime,
        timezone: str | None,
        location_enabled: bool,
        config: ConfigLike | None,
        session_logger: logging.Logger | None,
    ) -> 'Session':
        """Create a Session from runtime-collected components.

        Args:
            hostname: Hostname of the machine.
            username: Username of the user.
            workspace: Resolved workspace path.
            process_id: Unique session identifier.
            now_utc: Session start time in UTC.
            now_local: Session start time in local timezone.
            timezone: Local timezone name.
            location_enabled: Whether lazy location lookup is enabled.
            config: Loaded configuration object.
            session_logger: Logger instance configured for the session.

        Returns:
            Session: A new Session instance.
        """
        return cls(
            hostname=hostname,
            username=username,
            workspace=workspace,
            id=process_id,
            started_at_utc=now_utc,
            started_at_local=now_local,
            timezone=timezone,
            location_enabled=location_enabled,
            _location=None,
            config=config,
            session_logger=session_logger,
        )

    def __str__(self) -> str:
        """Return a human-readable string representation (excluding config)."""
        lines = []
        field_names = [
            'hostname',
            'username',
            'workspace',
            'id',
            'started_at_utc',
            'started_at_local',
            'timezone',
            'location',
        ]
        for field_name in field_names:
            if field_name == 'location':
                value = self._location
            else:
                value = getattr(self, field_name)
            lines.append(f'  {field_name}: {value}')
        return '\n'.join(lines)

    def __repr__(self) -> str:
        """Return a detailed string representation (excluding config)."""
        fields = []
        field_names = [
            'hostname',
            'username',
            'workspace',
            'id',
            'started_at_utc',
            'started_at_local',
            'timezone',
            'location',
        ]
        for field_name in field_names:
            if field_name == 'location':
                value = self._location
            else:
                value = getattr(self, field_name)
            if isinstance(value, Path):
                fields.append(f"{field_name}=Path('{value}')")
            else:
                fields.append(f'{field_name}={value!r}')
        return f'Session({", ".join(fields)})'

    def log(self) -> None:
        """Log the string representation of the session."""
        logger.info(str(self))

    def print_config(self) -> None:
        """Print the session config in a human-friendly format."""
        yaml_text = self.get_config_yaml()
        if yaml_text is not None:
            print(yaml_text)
            return
        cfg = self.get_config_dict()
        if cfg is None:
            logger.info('Session config is empty.')
            return
        pprint(cfg)

    def get_config_dict(self) -> Mapping[str, object] | None:
        """Return the session config as a plain dictionary when possible.

        Returns:
            Mapping[str, object] | None: Resolved config mapping, or None.
        """
        cfg = self.config
        if cfg is None:
            return None
        if OmegaConf.is_config(cfg):
            return OmegaConf.to_container(cfg, resolve=True)  # type: ignore[return-value]
        if isinstance(cfg, Mapping):
            return cfg
        return None

    def get_config_yaml(self) -> str | None:
        """Return the session config as YAML when available.

        Returns:
            str | None: YAML representation of the config, or None.
        """
        cfg = self.config
        if cfg is None:
            return None
        if OmegaConf.is_config(cfg):
            return OmegaConf.to_yaml(cfg)
        return None

    @property
    def location(self) -> str | None:
        """Return location, fetching it lazily when enabled.

        Returns:
            str | None: Location string when available, otherwise None.
        """
        if self._location is not None:
            return self._location
        if not self.location_enabled:
            return None
        location = _get_location_cached()
        object.__setattr__(self, '_location', location)
        return location



class SessionManager:
    """Manage the lifecycle of the singleton session.

    This class centralizes session creation and ensures thread-safe
    initialization.
    """

    def __init__(self) -> None:
        self._current_session: Session | None = None
        self._lock = threading.Lock()

    
    def get_session(
        self, workspace: str | Path, include_location: bool = False, config_path: str | Path | None = None
    ) -> Session:
        """Return the process-wide Session, initializing if needed.

        Args:
            workspace: Path or string to the workspace directory.
            include_location: Whether to allow lazy geolocation lookup.
            config_path: Optional path to a custom configuration file to merge.

        Returns:
            Session: The current session instance.
        """
        logger.debug(
            'get_session called with workspace=%s, include_location=%s, config_path=%s',
            workspace,
            include_location,
            config_path,
        )
        logger.info('Initialization of a session:')
        if self._current_session is not None:
            logger.info('Reusing existing session')
            self._current_session.log()
            return self._current_session

        with self._lock:
            if self._current_session is None:
                # Merge config_path if provided
                if config_path is not None:
                    config = ConfigLoader.load_config(config_path)
                else:
                    config = _get_configuration()

                LoggerConfigurator().logger_setup(
                    config=config, timestamp=LOG_TIMESTAMP
                )

                app_logger = _get_app_logger(config)
                app_logger.debug(
                    'Requesting session for workspace: %s', workspace
                )

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
                    logger.debug('Location lookup deferred (lazy)')
                    location_enabled = True
                else:
                    logger.debug('Location lookup skipped')
                    location_enabled = False

                logger.info('Creating new session...')

                self._current_session = Session.create(
                    hostname=hostname,
                    username=username,
                    workspace=resolved_workspace,
                    process_id=process_id,
                    now_utc=now_utc,
                    now_local=now_local,
                    timezone=timezone,
                    location_enabled=location_enabled,
                    config=config,
                    session_logger=app_logger,
                )

                logger.info('Session has been created')
            else:
                logger.info('Reusing existing session')
                self._current_session.log()

        return self._current_session

    def reset_session(self) -> None:
        """Clear the current session.

        This is intended for tests to avoid state leakage across cases.
        """
        with self._lock:
            self._current_session = None
            _get_location_cached.cache_clear()


# ---- Global manager
_default_manager = SessionManager()


# ---- Private helper functions
def _get_hostname() -> str:
    """Return the current machine's hostname."""
    return socket.gethostname()


def _get_username() -> str:
    """Return the current user's username."""
    return getpass.getuser()


def _get_workspace(workspace: Path | str) -> Path:
    """Resolve and return the absolute workspace path.

    Args:
        workspace: Workspace path (relative or absolute).

    Returns:
        Path: Resolved absolute path.
    """
    return Path(workspace).expanduser().resolve()


def _get_process_id() -> str:
    """Generate a new unique session ID (UUID4)."""
    return str(uuid.uuid4())


def _get_time() -> tuple[datetime, datetime]:
    """Return current UTC and local datetimes.

    Returns:
        tuple[datetime, datetime]: (utc_time, local_time)
    """
    now_utc = datetime.now(timezone.utc)  # noqa: UP017
    now_local = datetime.now().astimezone()
    return now_utc, now_local


def _get_timezone(localtime: datetime) -> str:
    """Return the timezone name for a local datetime.

    Args:
        localtime: Local datetime.

    Returns:
        str: Timezone name.
    """
    return localtime.tzname()


def _fetch_location(timeout: float = 3.0) -> str | None:
    """Attempt to determine the user's geolocation via public IP lookup.

    Args:
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        str | None: A string with city, region, and country if available.
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


@lru_cache(maxsize=1)
def _get_location_cached() -> str | None:
    """Return cached location, fetching once per process.

    Returns:
        str | None: Cached location string when available.
    """
    return _fetch_location()


def _get_configuration() -> ConfigLike:
    """Load and return the merged configuration.

    Returns:
        ConfigLike: Merged configuration.
    """
    logger.debug('Loading configuration via ConfigLoader')
    return ConfigLoader.load_config()


def _get_app_logger(merged_config: ConfigLike) -> logging.Logger:
    """Return the application logger from the merged configuration.

    Args:
        merged_config: Merged configuration object.

    Returns:
        logging.Logger: Configured application logger.
    """
    try:
        logger_name = merged_config.app.logger
    except AttributeError:
        logger.warning(
            'Config missing app.logger; falling back to module logger.'
        )
        return logging.getLogger(__name__)

    if not isinstance(logger_name, str) or not logger_name.strip():
        logger.warning(
            'Invalid app.logger value %r; falling back to module logger.',
            logger_name,
        )
        return logging.getLogger(__name__)

    logger.debug('Using app logger: %s', logger_name)
    return logging.getLogger(logger_name)



def get_session(
    workspace: str | Path,
    include_location: bool = False,
    config_path: str | Path | None = None
) -> Session:
    """Return the process-wide Session.

    Args:
        workspace: Workspace path (relative or absolute).
        include_location: Whether to allow lazy geolocation lookup.
        config_path: Optional path to a custom configuration file to merge.

    Returns:
        Session: The current session instance.
    """
    return _default_manager.get_session(
        workspace=workspace, include_location=include_location, config_path=config_path
    )


def reset_session() -> None:
    """Clear the current session (intended for testing)."""
    _default_manager.reset_session()


__all__ = ['SessionManager', 'get_session', 'reset_session']
