"""Logging configuration and runtime access utilities.

Provides idempotent initialization of Python logging from configuration,
as well as validated access to configured loggers.
"""

# Standard library imports
import os
import copy
import logging
from pathlib import Path
import threading
from logging.config import dictConfig

# Third-party
from omegaconf import OmegaConf

# First-party imports
from pkg_infra.utils import get_timestamp_now
from pkg_infra.config import ConfigLoader
from pkg_infra.constants import FILE_HANDLER_CLASSES

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---- Classes
class LoggerConfigurator:
    """Configure Python logging from a configuration object.

    This class is responsible for:
    - extracting the logging section
    - normalizing configuration values
    - preparing file-based handlers
    - applying logging configuration via dictConfig
    """

    def __init__(self) -> None:
        self._logging_config: dict | None = None

    def _extract_logging_config(self, config: dict | OmegaConf) -> None:
        """Extract the 'logging' section from configuration.

        Args:
            config (dict | OmegaConf): Configuration containing a 'logging' section.

        Raises:
            ValueError: If the 'logging' section is missing.
        """
        field_logging = 'logging'

        try:
            logging_config = config[field_logging]
        except KeyError as err:
            msg = f"No '{field_logging}' section found in config."
            logger.error(msg)
            raise ValueError(msg) from err

        if OmegaConf.is_config(logging_config):
            log_cfg_dict = OmegaConf.to_container(
                cfg=logging_config,
                resolve=True,
                structured_config_mode='dict',
            )
        else:
            log_cfg_dict = logging_config

        self._logging_config = log_cfg_dict

    def _configure_loggers(self, logging_config_dict: dict) -> None:
        """Apply logging configuration using dictConfig, supporting log rotation if specified.

        Args:
            logging_config_dict (dict): Logging configuration dictionary.

        Raises:
            ValueError, TypeError, ImportError: If configuration fails.
        """
        _patch_file_handlers_for_rotation(logging_config_dict)
        try:
            dictConfig(logging_config_dict)
        except (ValueError, TypeError, ImportError) as exc:
            logger.error('Failed to configure logging: %s', exc)
            raise



    def logger_setup(self, config: dict | OmegaConf, timestamp: str) -> None:
        """Configure logging from a configuration object.

        This method:
        - extracts the logging section
        - normalizes level names
        - appends timestamps to file-based handlers
        - ensures log directories exist
        - ensures root logger has both console and file handlers unless explicitly overridden
        - applies the configuration via dictConfig

        Args:
            config (dict | OmegaConf): Configuration object.
            timestamp (str): Timestamp appended to log filenames.
        """
        self._extract_logging_config(config=config)

        log_cfg_dict_copy = copy.deepcopy(self._logging_config)

        _uppercase_levels(log_cfg_dict_copy)

        LogFileManager.update_log_filenames(
            logging_config=log_cfg_dict_copy,
            timestamp=timestamp,
        )

        LogFileManager.create_log_directories(log_cfg_dict_copy)

        _ensure_root_handlers(log_cfg_dict_copy)

        self._configure_loggers(logging_config_dict=log_cfg_dict_copy)


class LogFileManager:
    """Utilities for managing file-based logging handlers."""

    @staticmethod
    def update_log_filenames(logging_config: dict, timestamp: str) -> None:
        """Recursively update all 'filename' fields by appending a timestamp.

        Modifies the configuration in-place.

        Args:
            logging_config (dict): Logging config dict.
            timestamp (str): Timestamp string.
        """
        if timestamp is None:
            logger.warning(
                'Timestamp is None (type %s). Generating a new one.',
                type(timestamp),
            )
            timestamp = get_timestamp_now()

        logger.info('Updating log filenames with timestamp: %s', timestamp)
        _recursive_update(logging_config, timestamp=timestamp)

    @staticmethod
    def create_log_directories(logging_config: dict) -> None:
        """Ensure directories for all file-based handlers exist.

        Args:
            logging_config (dict): Logging configuration.
        """
        handlers = logging_config.get('handlers', {})

        for handler in handlers.values():
            if handler.get('class') in FILE_HANDLER_CLASSES:
                filename = handler.get('filename')
                if filename:
                    Path(filename).parent.mkdir(parents=True, exist_ok=True)


# ---- Private helper functions
def _patch_file_handlers_for_rotation(logging_config_dict: dict) -> None:
    """Convert FileHandler to RotatingFileHandler if maxBytes/backupCount are present."""
    handlers = logging_config_dict.get('handlers', {})
    for handler_cfg in handlers.values():
        handler_class = handler_cfg.get('class', '')
        if handler_class == 'logging.FileHandler':
            if 'maxBytes' in handler_cfg or 'backupCount' in handler_cfg:
                handler_cfg['class'] = 'logging.handlers.RotatingFileHandler'
                handler_cfg.setdefault('maxBytes', 10485760)
                handler_cfg.setdefault('backupCount', 5)

def _ensure_root_handlers(logging_config: dict) -> None:
    """Ensure root logger has both console and file handlers unless explicitly overridden."""
    handlers = logging_config.get("handlers", {})
    root = logging_config.get("root", {})
    root_handlers = root.get("handlers")

    # Only inject fallback if handlers is missing or empty
    if not root_handlers:
        fallback = []
        if "console" in handlers:
            fallback.append("console")
        if "file" in handlers:
            fallback.append("file")
        root["handlers"] = fallback
        logging_config["root"] = root


def _uppercase_levels(d: dict | list) -> None:
    """Recursively convert all 'level' values to uppercase."""
    if isinstance(d, dict):
        for k, v in d.items():
            if k == 'level' and isinstance(v, str):
                d[k] = v.upper()
            else:
                _uppercase_levels(v)
    elif isinstance(d, list):
        for item in d:
            _uppercase_levels(item)


def _update_single_filename(filename: str, timestamp: str) -> str:
    """Append timestamp to a filename while preserving extension."""
    base, ext = os.path.splitext(filename)
    return f'{base}_{timestamp}{ext}'


def _recursive_update(d: dict | list, timestamp: str) -> None:
    """Recursively traverse a structure and update filename fields."""
    if isinstance(d, dict):
        for k, v in d.items():
            if k == 'filename' and isinstance(v, str):
                d[k] = _update_single_filename(v, timestamp)
            else:
                _recursive_update(v, timestamp)
    elif isinstance(d, list):
        for item in d:
            _recursive_update(item, timestamp)


# --- Public API ---
_logging_initialized = False
_logging_init_lock = threading.Lock()


def initialize_logging(
    config_path: str, loader=ConfigLoader.load_config
) -> None:
    """Initialize logging from a configuration file.

    This function is idempotent and thread-safe.

    Args:
        config_path (str): Path to configuration file.
        loader (callable): Function to load configuration.

    Raises:
        ValueError: If configuration is invalid.
    """
    global _logging_initialized

    if _logging_initialized:
        return

    with _logging_init_lock:
        if _logging_initialized:
            return

        config = loader(config_path)
        timestamp = get_timestamp_now()

        configurator = LoggerConfigurator()
        configurator.logger_setup(config, timestamp=timestamp)

        _logging_initialized = True


def initialize_logging_from_config(config: dict | OmegaConf) -> None:
    """Initialize logging directly from a configuration object.

    Useful for testing or programmatic configuration.

    Args:
        config (dict | OmegaConf): Configuration object.
    """
    global _logging_initialized

    if _logging_initialized:
        return

    with _logging_init_lock:
        if _logging_initialized:
            return

        timestamp = get_timestamp_now()

        configurator = LoggerConfigurator()
        configurator.logger_setup(config, timestamp=timestamp)

        _logging_initialized = True


def is_logging_initialized() -> bool:
    """Return whether logging has been initialized."""
    return _logging_initialized


def get_logger(name: str) -> logging.Logger:
    """Retrieve a configured logger with strict validation.

    Args:
        name (str): Logger name.

    Returns:
        logging.Logger: Logger instance.

    Raises:
        RuntimeError: If logging is not initialized.
        ValueError: If logger is invalid or not effectively configured.
    """
    if not _logging_initialized:
        raise RuntimeError('Logging has not been initialized.')

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Invalid logger name '{name}'.")

    if name == 'root':
        return logging.getLogger()

    logger_dict = logging.Logger.manager.loggerDict

    if name not in logger_dict:
        raise ValueError(f"Logger '{name}' is not registered.")

    logger_obj = logging.getLogger(name)

    if not logger_obj.handlers and logger_obj.propagate:
        if not logging.getLogger().handlers:
            raise ValueError(f"Logger '{name}' is not effectively configured.")
    elif not logger_obj.handlers and not logger_obj.propagate:
        raise ValueError(
            f"Logger '{name}' has no handlers and does not propagate."
        )

    return logger_obj


def list_loggers() -> list[str]:
    """Return names of loggers known to the logging manager.

    Note:
        Does not include the root logger unless explicitly registered.
    """
    return list(logging.Logger.manager.loggerDict.keys())
