"""Logging configuration and runtime access utilities.

This module builds a validated ``dictConfig`` payload from the package
configuration and exposes a small public API for initializing and retrieving
application loggers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
import logging
from logging.config import dictConfig
from logging.handlers import QueueHandler, QueueListener
import os
from pathlib import Path
import queue
import threading
from typing import Any, TypeAlias

from omegaconf import OmegaConf
from pythonjsonlogger.json import JsonFormatter
import yaml

from pkg_infra.config import ConfigLoader, omegaconf_to_plain_dict
from pkg_infra.constants import FILE_HANDLER_CLASSES
from pkg_infra.schema import validate_logging_section
from pkg_infra.utils import get_timestamp_now

__all__ = [
    'LoggerConfigurator',
    'get_logger',
    'initialize_logging',
    'initialize_logging_from_config',
    'is_logging_initialized',
    'list_loggers',
]

ConfigValue: TypeAlias = Any
ConfigDict: TypeAlias = dict[str, ConfigValue]
ConfigLike: TypeAlias = Mapping[str, ConfigValue] | OmegaConf
LoggerEntry: TypeAlias = dict[str, ConfigValue]

_ALLOWED_LOGGING_KEYS = {
    'async_mode',
    'disable_existing_loggers',
    'file_output_format',
    'filters',
    'formatters',
    'handlers',
    'loggers',
    'queue_maxsize',
    'root',
    'version',
}

_POLICY_KEYS = {'enabled', 'handlers', 'level', 'propagate'}
_DISABLED_LOGGER_POLICY: LoggerEntry = {
    'handlers': ['null'],
    'level': 'CRITICAL',
    'propagate': False,
}


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class LoggerConfigurator:
    """Build and apply a logging configuration from merged settings.

    The configurator is intentionally narrow in responsibility: it transforms
    the relevant configuration sections into a final ``dictConfig`` payload,
    validates it, prepares any file-system prerequisites, and applies the
    configuration.
    """

    def __init__(self) -> None:
        """Initialize an empty configurator state."""
        self._initial_logging_config: ConfigLike | None = None
        self._final_config: ConfigDict | None = None

    @property
    def final_config(self) -> ConfigDict | None:
        """Return the last applied logging configuration, if any."""
        return copy.deepcopy(self._final_config)

    def configure(
        self, config: ConfigLike, timestamp: str | None = None
    ) -> None:
        """Build and apply logging from a merged application configuration.

        Args:
            config: Merged application configuration.
            timestamp: Optional timestamp suffix used for file handlers. When
                omitted, a fresh timestamp is generated.
        """
        self._initial_logging_config = config
        timestamp_value = timestamp or get_timestamp_now()

        logger.info('Setting up loggers')
        _, logging_section, integrations, packages_groups = _extract_sections(
            config,
        )

        base_logging_config = _normalize_base_logging_config(logging_section)
        group_index = _build_group_index(packages_groups)
        target_packages = _compute_target_packages(
            integrations=integrations,
            packages_groups=packages_groups,
        )
        logger_entries = _build_logger_entries(
            target_packages=target_packages,
            group_index=group_index,
            integrations=integrations,
            packages_groups=packages_groups,
            logging_section=logging_section,
        )
        final_logging_config = _merge_loggers_into_base_config(
            base_logging_config=base_logging_config,
            logger_entries=logger_entries,
        )

        _ensure_root_handlers(final_logging_config)
        _validate_final_logging_config(final_logging_config)
        _update_log_filenames(final_logging_config, timestamp_value)
        _update_file_extensions_for_structured_output(final_logging_config)
        _create_log_directories(final_logging_config)

        logger.debug(
            'Final logging configuration:\n%s',
            yaml.dump(final_logging_config, sort_keys=False),
        )
        _apply_logging_config(final_logging_config)
        self._final_config = copy.deepcopy(final_logging_config)

    def logger_setup(
        self, config: ConfigLike, timestamp: str | None = None
    ) -> None:
        """Backward-compatible wrapper around :meth:`configure`.

        Args:
            config: Merged application configuration.
            timestamp: Optional timestamp suffix used for file handlers.
        """
        self.configure(config=config, timestamp=timestamp)


def _to_plain_dict(config: ConfigLike) -> ConfigDict:
    """Convert a supported config object into a plain mutable dictionary."""
    plain_config = omegaconf_to_plain_dict(config)
    if not isinstance(plain_config, dict):
        raise TypeError(
            'Logging configuration must resolve to a mapping, '
            f'got {type(plain_config)!r}.',
        )
    return plain_config


def _update_log_filenames(
    logging_config: ConfigDict, timestamp: str | None
) -> None:
    """Append the timestamp suffix to every ``filename`` entry in-place.

    Args:
        logging_config: Logging configuration that will be mutated.
        timestamp: Timestamp suffix to append. When ``None``, a new timestamp is
            generated.
    """
    timestamp_value = timestamp or get_timestamp_now()
    logger.info('Updating log filenames with timestamp: %s', timestamp_value)
    _recursive_update(logging_config, timestamp=timestamp_value)


def _create_log_directories(logging_config: Mapping[str, ConfigValue]) -> None:
    """Create parent directories for configured file handlers when needed.

    Args:
        logging_config: Final logging configuration.
    """
    handlers = logging_config.get('handlers', {})
    if not isinstance(handlers, Mapping):
        return

    for handler in handlers.values():
        if not isinstance(handler, Mapping):
            continue
        if handler.get('class') not in FILE_HANDLER_CLASSES:
            continue
        filename = handler.get('filename')
        if isinstance(filename, str):
            Path(filename).parent.mkdir(parents=True, exist_ok=True)


def _update_file_extensions_for_structured_output(
    logging_config: ConfigDict,
) -> None:
    """Adjust file handler extensions for structured output modes.

    Args:
        logging_config: Final logging configuration to mutate.
    """
    if logging_config.get('file_output_format') != 'json':
        return

    handlers = logging_config.get('handlers', {})
    if not isinstance(handlers, dict):
        return

    for handler in handlers.values():
        if not isinstance(handler, dict):
            continue
        if handler.get('class') not in FILE_HANDLER_CLASSES:
            continue
        filename = handler.get('filename')
        if isinstance(filename, str):
            handler['filename'] = _replace_filename_extension(
                filename=filename,
                extension='.json',
            )


def _patch_file_handlers_for_rotation(logging_config: ConfigDict) -> None:
    """Upgrade eligible file handlers to rotating handlers in-place.

    A plain ``logging.FileHandler`` is converted to
    ``logging.handlers.RotatingFileHandler`` when rotation settings are
    configured.

    Args:
        logging_config: Logging configuration to mutate.
    """
    handlers = logging_config.get('handlers', {})
    if not isinstance(handlers, dict):
        return

    for handler_cfg in handlers.values():
        if not isinstance(handler_cfg, dict):
            continue
        if handler_cfg.get('class') != 'logging.FileHandler':
            continue
        if 'maxBytes' not in handler_cfg and 'backupCount' not in handler_cfg:
            continue
        handler_cfg['class'] = 'logging.handlers.RotatingFileHandler'
        handler_cfg.setdefault('maxBytes', 10 * 1024 * 1024)
        handler_cfg.setdefault('backupCount', 5)


def _ensure_root_handlers(logging_config: ConfigDict) -> None:
    """Provide sensible root handlers when the root logger omits them.

    Args:
        logging_config: Logging configuration to mutate.
    """
    handlers = logging_config.get('handlers', {})
    root = logging_config.setdefault('root', {})
    if not isinstance(handlers, dict) or not isinstance(root, dict):
        return
    if root.get('handlers'):
        return

    fallback_handlers: list[str] = []
    for handler_name in ('console', 'file'):
        if handler_name in handlers:
            fallback_handlers.append(handler_name)
    root['handlers'] = fallback_handlers


def _uppercase_levels(data: ConfigValue) -> None:
    """Recursively normalize all ``level`` values to uppercase."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'level' and isinstance(value, str):
                data[key] = value.upper()
            else:
                _uppercase_levels(value)
        return

    if isinstance(data, list):
        for item in data:
            _uppercase_levels(item)


def _update_single_filename(filename: str, timestamp: str) -> str:
    """Insert a timestamp before the filename extension.

    Args:
        filename: Original file path.
        timestamp: Timestamp suffix.

    Returns:
        The timestamped filename.
    """
    base, extension = os.path.splitext(filename)
    return f'{base}_{timestamp}{extension}'


def _replace_filename_extension(filename: str, extension: str) -> str:
    """Return ``filename`` with its extension replaced."""
    base, _original_extension = os.path.splitext(filename)
    return f'{base}{extension}'


def _recursive_update(data: ConfigValue, timestamp: str) -> None:
    """Recursively update all ``filename`` keys in a nested structure.

    Args:
        data: Nested configuration data.
        timestamp: Timestamp suffix.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'filename' and isinstance(value, str):
                data[key] = _update_single_filename(value, timestamp)
            else:
                _recursive_update(value, timestamp)
        return

    if isinstance(data, list):
        for item in data:
            _recursive_update(item, timestamp)


def _extract_sections(
    config: ConfigLike,
) -> tuple[ConfigDict, ConfigDict, ConfigDict, ConfigDict]:
    """Validate and extract the logger-relevant configuration sections.

    Args:
        config: Merged application configuration.

    Returns:
        A tuple with ``app``, ``logging``, ``integrations``, and
        ``packages_groups`` sections as plain dictionaries.

    Raises:
        ValueError: If a required section is missing.
    """
    plain_config = _to_plain_dict(config)
    required_sections = ('app', 'logging', 'integrations', 'packages_groups')

    if 'settings_version' not in plain_config:
        raise ValueError('Missing settings_version in config.')

    missing_sections = [
        section for section in required_sections if section not in plain_config
    ]
    if missing_sections:
        missing = ', '.join(missing_sections)
        raise ValueError(f'Missing required config section(s): {missing}.')

    logger.debug('App section: %s', plain_config['app'])
    logger.debug('Logging section: %s', plain_config['logging'])
    logger.debug('Integrations section: %s', plain_config['integrations'])
    logger.debug('Packages groups section: %s', plain_config['packages_groups'])

    return (
        _require_dict_section(plain_config['app'], section_name='app'),
        _require_dict_section(plain_config['logging'], section_name='logging'),
        _require_dict_section(
            plain_config['integrations'],
            section_name='integrations',
        ),
        _require_dict_section(
            plain_config['packages_groups'],
            section_name='packages_groups',
        ),
    )


def _require_dict_section(
    value: ConfigValue,
    *,
    section_name: str,
) -> ConfigDict:
    """Return a section value as a dictionary or raise a helpful error."""
    if not isinstance(value, dict):
        raise TypeError(
            f"Config section '{section_name}' must be a mapping, "
            f'got {type(value)!r}.',
        )
    return copy.deepcopy(value)


def _normalize_base_logging_config(
    logging_section: Mapping[str, ConfigValue],
) -> ConfigDict:
    """Return a validated base logging configuration.

    Args:
        logging_section: Raw logging section from the merged settings.

    Returns:
        A normalized, validated logging configuration copy.
    """
    config = copy.deepcopy(dict(logging_section))
    _uppercase_levels(config)

    handlers = _safe_dict(config.get('handlers'))
    formatters = _safe_dict(config.get('formatters'))
    filters = _safe_dict(config.get('filters'))
    loggers = _safe_dict(config.get('loggers'))
    root = _safe_dict(config.get('root'))

    _validate_handler_formatters(handlers=handlers, formatters=formatters)
    _validate_handler_filters(handlers=handlers, filters=filters)
    _validate_logger_handlers(loggers=loggers, handlers=handlers)
    _validate_root_handlers(root=root, handlers=handlers)
    _validate_logging_keys(config)
    return config


def _safe_dict(value: ConfigValue) -> ConfigDict:
    """Return ``value`` as a shallow dictionary copy when possible."""
    if isinstance(value, dict):
        return dict(value)
    return {}


def _validate_handler_formatters(
    handlers: Mapping[str, ConfigValue],
    formatters: Mapping[str, ConfigValue],
) -> None:
    """Ensure each referenced formatter exists."""
    for handler_name, handler in handlers.items():
        if not isinstance(handler, Mapping):
            continue
        formatter = handler.get('formatter')
        if formatter and formatter not in formatters:
            raise ValueError(
                f"Handler '{handler_name}' references unknown formatter "
                f"'{formatter}'.",
            )


def _validate_handler_filters(
    handlers: Mapping[str, ConfigValue],
    filters: Mapping[str, ConfigValue],
) -> None:
    """Ensure each referenced filter exists."""
    for handler_name, handler in handlers.items():
        if not isinstance(handler, Mapping):
            continue
        filter_names = handler.get('filters', [])
        if not isinstance(filter_names, list):
            raise TypeError(
                f"Handler '{handler_name}' filters must be a list, "
                f'got {type(filter_names)!r}.',
            )
        for filter_name in filter_names:
            if filter_name not in filters:
                raise ValueError(
                    f"Handler '{handler_name}' references unknown filter "
                    f"'{filter_name}'.",
                )


def _validate_logger_handlers(
    loggers: Mapping[str, ConfigValue],
    handlers: Mapping[str, ConfigValue],
) -> None:
    """Ensure each logger references known handlers."""
    for logger_name, logger_config in loggers.items():
        if not isinstance(logger_config, Mapping):
            continue
        handler_names = logger_config.get('handlers', [])
        if not isinstance(handler_names, list):
            raise TypeError(
                f"Logger '{logger_name}' handlers must be a list, "
                f'got {type(handler_names)!r}.',
            )
        for handler_name in handler_names:
            if handler_name not in handlers:
                raise ValueError(
                    f"Logger '{logger_name}' references unknown handler "
                    f"'{handler_name}'.",
                )


def _validate_root_handlers(
    root: Mapping[str, ConfigValue],
    handlers: Mapping[str, ConfigValue],
) -> None:
    """Ensure the root logger only references known handlers."""
    handler_names = root.get('handlers', [])
    if not isinstance(handler_names, list):
        raise TypeError(
            'Root logger handlers must be a list, '
            f'got {type(handler_names)!r}.',
        )
    for handler_name in handler_names:
        if handler_name not in handlers:
            raise ValueError(
                f"Root logger references unknown handler '{handler_name}'.",
            )


def _validate_logging_keys(config: Mapping[str, ConfigValue]) -> None:
    """Reject unsupported top-level keys in the logging section."""
    unexpected_keys = sorted(set(config) - _ALLOWED_LOGGING_KEYS)
    if unexpected_keys:
        keys = ', '.join(unexpected_keys)
        raise ValueError(f'Unknown key(s) in logging config: {keys}.')


def _build_group_index(
    packages_groups: Mapping[str, ConfigValue],
) -> dict[str, str]:
    """Build a ``package -> group`` index and reject duplicate membership."""
    group_index: dict[str, str] = {}
    for group_name, group_config in packages_groups.items():
        if not isinstance(group_config, Mapping):
            continue
        packages = group_config.get('packages', [])
        if not isinstance(packages, list):
            raise TypeError(
                f"Group '{group_name}' packages must be a list, "
                f'got {type(packages)!r}.',
            )
        for package in packages:
            if package in group_index:
                raise ValueError(
                    f"Package '{package}' is in multiple groups: "
                    f'{group_index[package]}, {group_name}.',
                )
            group_index[package] = group_name
    return group_index


def _compute_target_packages(
    integrations: Mapping[str, ConfigValue],
    packages_groups: Mapping[str, ConfigValue],
) -> list[str]:
    """Return all packages that require logger entries.

    Args:
        integrations: Integration-specific settings.
        packages_groups: Package group definitions.

    Returns:
        A sorted list of package names.
    """
    packages = set(integrations.keys())
    for group_config in packages_groups.values():
        if not isinstance(group_config, Mapping):
            continue
        group_packages = group_config.get('packages', [])
        if isinstance(group_packages, list):
            packages.update(group_packages)
    return sorted(packages)


def _build_logger_entries(
    *,
    target_packages: list[str],
    group_index: Mapping[str, str],
    integrations: Mapping[str, ConfigValue],
    packages_groups: Mapping[str, ConfigValue],
    logging_section: Mapping[str, ConfigValue],
) -> dict[str, LoggerEntry]:
    """Build one logger entry per target package."""
    logger_entries: dict[str, LoggerEntry] = {}
    for package in target_packages:
        _, integration_config = _resolve_package_context(
            package=package,
            group_index=group_index,
            integrations=integrations,
        )
        base_policy = _determine_base_logging_policy(
            package=package,
            group_index=group_index,
            packages_groups=packages_groups,
            logging_section=logging_section,
        )
        merged_policy = _apply_integration_overrides(
            base_policy=base_policy,
            integration_cfg=integration_config,
        )
        resolved_policy = _resolve_final_logging_policy(merged_policy)
        final_policy = _handle_disabled_logger(resolved_policy)
        package_name, entry = _build_logger_config_entry(
            package=package,
            resolved_policy=final_policy,
        )
        logger_entries[package_name] = entry
    return logger_entries


def _resolve_package_context(
    package: str,
    group_index: Mapping[str, str],
    integrations: Mapping[str, ConfigValue],
) -> tuple[str | None, ConfigDict | None]:
    """Return the package group and integration settings, if present."""
    group_name = group_index.get(package)
    integration_config = integrations.get(package)
    if isinstance(integration_config, dict):
        return group_name, copy.deepcopy(integration_config)
    return group_name, None


def _determine_base_logging_policy(
    package: str,
    group_index: Mapping[str, str],
    packages_groups: Mapping[str, ConfigValue],
    logging_section: Mapping[str, ConfigValue],
) -> ConfigDict:
    """Return the default logging policy for a package."""
    group_name = group_index.get(package)
    if group_name:
        group_config = packages_groups.get(group_name, {})
        if isinstance(group_config, Mapping):
            group_logging = group_config.get('logging', {})
            if isinstance(group_logging, dict):
                return copy.deepcopy(group_logging)

    default_logger = _safe_dict(logging_section.get('loggers')).get(
        'default', {}
    )
    if isinstance(default_logger, dict):
        return copy.deepcopy(default_logger)
    return {}


def _apply_integration_overrides(
    base_policy: Mapping[str, ConfigValue],
    integration_cfg: Mapping[str, ConfigValue] | None,
) -> ConfigDict:
    """Merge integration-level logging overrides onto a base policy."""
    if not integration_cfg:
        return copy.deepcopy(dict(base_policy))

    overrides = integration_cfg.get('logging')
    if not isinstance(overrides, dict):
        return copy.deepcopy(dict(base_policy))

    merged_policy = copy.deepcopy(dict(base_policy))
    merged_policy.update(overrides)
    return merged_policy


def _resolve_final_logging_policy(
    base_policy: Mapping[str, ConfigValue],
) -> ConfigDict:
    """Fill in default policy values expected by ``dictConfig``."""
    resolved = copy.deepcopy(dict(base_policy))
    resolved.setdefault('enabled', True)
    resolved.setdefault('propagate', False)
    return resolved


def _handle_disabled_logger(policy: Mapping[str, ConfigValue]) -> ConfigDict:
    """Return a disabled logger policy when ``enabled`` is false."""
    if not policy.get('enabled', True):
        return copy.deepcopy(_DISABLED_LOGGER_POLICY)
    return copy.deepcopy(dict(policy))


def _build_logger_config_entry(
    package: str,
    resolved_policy: Mapping[str, ConfigValue],
) -> tuple[str, LoggerEntry]:
    """Build the final logger entry consumed by ``dictConfig``."""
    entry = {
        key: value
        for key, value in resolved_policy.items()
        if key in _POLICY_KEYS - {'enabled'}
    }
    return package, entry


def _merge_loggers_into_base_config(
    *,
    base_logging_config: Mapping[str, ConfigValue],
    logger_entries: Mapping[str, LoggerEntry],
) -> ConfigDict:
    """Merge generated logger entries into the base logging config."""
    config = copy.deepcopy(dict(base_logging_config))
    config.setdefault('loggers', {})
    if not isinstance(config['loggers'], dict):
        raise TypeError(
            'Logging config "loggers" section must be a mapping.',
        )
    config['loggers'].update(logger_entries)
    return config


def _validate_final_logging_config(
    logging_config: Mapping[str, ConfigValue],
) -> None:
    """Validate the final logging configuration before applying it.

    Args:
        logging_config: Final logging configuration.

    Raises:
        ValueError: If the configuration is structurally incomplete.
        ValidationError: Propagated from schema validation.
    """
    if 'handlers' not in logging_config:
        raise ValueError('No handlers defined in logging config.')
    if 'loggers' not in logging_config:
        raise ValueError('No loggers defined in logging config.')

    validate_logging_section(logging_config=logging_config)


def _apply_logging_config(logging_config: ConfigDict) -> None:
    """Apply the final logging configuration.

    Args:
        logging_config: Final validated logging configuration.
    """
    _stop_async_logging_listener()
    _patch_file_handlers_for_rotation(logging_config)
    dictConfig(logging_config)
    if logging_config.get('file_output_format') == 'json':
        _configure_json_file_handlers()
    if logging_config.get('async_mode'):
        _configure_async_logging(logging_config)


def _configure_json_file_handlers() -> None:
    """Switch configured file handlers to newline-delimited JSON output."""
    json_formatter = JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    seen_handlers: set[int] = set()

    for handler in _iter_active_handlers():
        if id(handler) in seen_handlers:
            continue
        seen_handlers.add(id(handler))
        if isinstance(handler, logging.FileHandler):
            handler.setFormatter(json_formatter)


def _configure_async_logging(logging_config: Mapping[str, ConfigValue]) -> None:
    """Wrap active handlers behind a shared queue/listener pipeline."""
    maxsize = logging_config.get('queue_maxsize')
    if not isinstance(maxsize, int):
        maxsize = 0

    active_handlers = _collect_async_target_handlers()
    if not active_handlers:
        return

    log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=maxsize)
    queue_handler = QueueHandler(log_queue)
    listener = QueueListener(
        log_queue, *active_handlers, respect_handler_level=True
    )
    listener.start()

    _replace_handlers_with_queue_handler(queue_handler)

    global _logging_queue, _logging_listener
    _logging_queue = log_queue
    _logging_listener = listener


def _collect_async_target_handlers() -> list[logging.Handler]:
    """Return the concrete handlers that should run in the listener thread."""
    seen_handlers: set[int] = set()
    target_handlers: list[logging.Handler] = []

    for handler in _iter_active_handlers():
        if id(handler) in seen_handlers:
            continue
        if isinstance(handler, QueueHandler):
            continue
        seen_handlers.add(id(handler))
        target_handlers.append(handler)

    return target_handlers


def _replace_handlers_with_queue_handler(queue_handler: QueueHandler) -> None:
    """Replace direct handlers on active loggers with a shared queue handler."""
    root_logger = logging.getLogger()
    if _logger_has_non_null_handlers(root_logger):
        root_logger.handlers = [queue_handler]

    for logger_obj in logging.Logger.manager.loggerDict.values():
        if not isinstance(logger_obj, logging.Logger):
            continue
        if not _logger_has_non_null_handlers(logger_obj):
            continue
        logger_obj.handlers = [queue_handler]


def _logger_has_non_null_handlers(target_logger: logging.Logger) -> bool:
    """Return whether a logger owns at least one non-null concrete handler."""
    return any(
        not isinstance(handler, logging.NullHandler)
        for handler in target_logger.handlers
    )


def _iter_active_handlers() -> list[logging.Handler]:
    """Return active handlers from the root logger and registered loggers."""
    handlers: list[logging.Handler] = list(logging.getLogger().handlers)

    for logger_obj in logging.Logger.manager.loggerDict.values():
        if isinstance(logger_obj, logging.Logger):
            handlers.extend(logger_obj.handlers)

    return handlers


def _stop_async_logging_listener() -> None:
    """Stop and forget the active queue listener, if one exists."""
    global _logging_listener, _logging_queue

    if _logging_listener is not None:
        _logging_listener.stop()

    _logging_listener = None
    _logging_queue = None


_logging_initialized = False
_logging_init_lock = threading.Lock()
_logging_listener: QueueListener | None = None
_logging_queue: queue.Queue[logging.LogRecord] | None = None


def initialize_logging(
    config_path: str,
    loader: Callable[[str], ConfigLike] = ConfigLoader.load_config,
) -> None:
    """Initialize logging from a configuration file path.

    The initialization is idempotent and thread-safe.

    Args:
        config_path: Path to the configuration file.
        loader: Callable used to load the configuration.
    """
    global _logging_initialized

    if _logging_initialized:
        return

    with _logging_init_lock:
        if _logging_initialized:
            return

        config = loader(config_path)
        LoggerConfigurator().configure(
            config=config, timestamp=get_timestamp_now()
        )
        _logging_initialized = True


def initialize_logging_from_config(config: ConfigLike) -> None:
    """Initialize logging directly from an in-memory configuration object.

    Args:
        config: Configuration object compatible with the configurator.
    """
    global _logging_initialized

    if _logging_initialized:
        return

    with _logging_init_lock:
        if _logging_initialized:
            return

        LoggerConfigurator().configure(
            config=config, timestamp=get_timestamp_now()
        )
        _logging_initialized = True


def is_logging_initialized() -> bool:
    """Return whether the module-level logging setup has already run."""
    return _logging_initialized


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger after validating initialization state.

    Args:
        name: Logger name. Use ``'root'`` to retrieve the root logger.

    Returns:
        The configured logger instance.

    Raises:
        RuntimeError: If logging has not been initialized.
        ValueError: If the logger name is invalid or not effectively configured.
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

    configured_logger = logging.getLogger(name)
    if configured_logger.handlers:
        return configured_logger
    if configured_logger.propagate and logging.getLogger().handlers:
        return configured_logger

    raise ValueError(
        f"Logger '{name}' is not effectively configured: it has no handlers "
        'and cannot fall back to a configured root logger.',
    )


def list_loggers() -> list[str]:
    """Return the names currently known to the logging manager."""
    return sorted(logging.Logger.manager.loggerDict.keys())
