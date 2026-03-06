# Standard library imports
import os
import copy
import logging
from pathlib import Path
import datetime
from logging.config import dictConfig

# Third-party imports
from omegaconf import OmegaConf

# Local imports
from pkg_infra.config import read_package_default

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

DEFAULT_FILENAME_LOG_MISSING = 'logs/pkg_infra.log'
_LOGGING_CONFIGURED = False


def _uppercase_levels(d: object) -> None:
    """Recursively convert all `level` values in a dict to uppercase strings."""
    if isinstance(d, dict):
        for k, v in d.items():
            if k == 'level' and isinstance(v, str):
                d[k] = v.upper()
            else:
                _uppercase_levels(v)
    elif isinstance(d, list):
        for item in d:
            _uppercase_levels(item)


def update_log_filenames_with_timestamp(
    config_dict: dict[str, object],
    timestamp: str | None = None,
) -> dict[str, object]:
    """Add a timestamp suffix to every `filename` field in logging config.

    If timestamp is not provided, use current UTC time in YYYYMMDDHHMMSS format.
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

    def update_filename(filename: str) -> str:
        base, ext = os.path.splitext(filename)
        return f'{base}_{timestamp}{ext}'

    def recursive_update(d: object) -> None:
        if isinstance(d, dict):
            for k, v in d.items():
                if k == 'filename' and isinstance(v, str):
                    d[k] = update_filename(v)
                else:
                    recursive_update(v)
        elif isinstance(d, list):
            for item in d:
                recursive_update(item)

    recursive_update(config_dict)
    return config_dict


def configure_loggers_from_omegaconf(
    merged_config: object,
    timestamp: str | None = None,
) -> None:
    """Configure loggers using the `logging` section of an OmegaConf config object.

    Optionally updates log filenames with a timestamp.
    """
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        logger.debug('Logging is already configured; skipping reconfiguration.')
        return

    if 'logging' not in merged_config:
        raise ValueError("No 'logging' section found in config.")

    # Always convert to a pure dict (resolves all OmegaConf nodes)
    log_cfg = OmegaConf.to_container(
        merged_config['logging'], resolve=True, structured_config_mode='dict'
    )

    # Make a copy to avoid mutating the original config
    log_cfg = copy.deepcopy(log_cfg)

    # Ensure all 'level' values are uppercase
    _uppercase_levels(log_cfg)

    # Update all log filenames with the provided timestamp
    if timestamp is not None:
        log_cfg = update_log_filenames_with_timestamp(
            log_cfg, timestamp=timestamp
        )

    # Ensure file handler directories exist and set default filenames if needed
    handlers = log_cfg.get('handlers', {})
    for handler in handlers.values():
        if handler.get('class') in [
            'logging.FileHandler',
            'logging.handlers.RotatingFileHandler',
        ]:
            filename = handler.get('filename')
            if filename:
                Path(filename).parent.mkdir(parents=True, exist_ok=True)

    # Create the loggers listed in the config file
    dictConfig(log_cfg)
    _LOGGING_CONFIGURED = True


def get_root_logger_configured(timestamp: str | None = None) -> None:
    """Configure the root logger using the package default config and optional timestamp."""
    package_config = read_package_default()
    configure_loggers_from_omegaconf(package_config, timestamp=timestamp)


def list_loggers() -> list[str]:
    """Return names of all loggers currently registered in the logging manager."""

    all_loggers = list(logging.Logger.manager.loggerDict.keys())
    logger.debug(f'List of loggers: {all_loggers}')
    return all_loggers
