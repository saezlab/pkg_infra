from __future__ import annotations

import logging
from logging import NullHandler
from pathlib import Path
from collections.abc import Mapping

from pydantic import (
    Field,
    BaseModel,
    ConfigDict,
    ValidationError,
)

try:
    from omegaconf import OmegaConf
except ImportError:  # pragma: no cover - optional in pure schema usage
    OmegaConf = None


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


# ---- Models


# -- 1. Section: App
class AppConfigProfile(BaseModel):
    """Application-level settings."""

    model_config = ConfigDict(extra='forbid')

    name: str | None = None
    environment: str
    logger: str


# -- 2. Section: Environment
class EnvironmentProfile(BaseModel):
    """Named environment profile."""

    model_config = ConfigDict(extra='forbid')
    name: str
    debug: bool


# -- 3. Section: Session
class SessionConfigProfile(BaseModel):
    """Session metadata defaults."""

    model_config = ConfigDict(extra='forbid')

    id: str | None = None
    user: str | None = None
    workspace: str | None = None
    started_at: str | None = None
    tags: list[str] = Field(default_factory=list)


# -- 4. Section: Paths
class PathsConfigProfile(BaseModel):
    """Defaults Paths."""

    model_config = ConfigDict(extra='forbid')

    data_dir: str | Path | None = None
    cache_dir: str | Path | None = None
    log_dir: str | Path | None = None
    temp_dir: str | Path | None = None


# -- 5. Section: Logging
class FormatterProfile(BaseModel):
    format: str
    datefmt: str | None = None


class HandlerProfile(BaseModel):
    class_: str = Field(..., alias='class')
    level: str
    formatter: str
    filters: list[str] | None = None
    stream: str | None = None
    filename: str | None = None
    encoding: str | None = None
    maxBytes: int | None = None
    backupCount: int | None = None


class LoggerProfile(BaseModel):
    level: str
    handlers: list[str]
    propagate: bool


class RootLoggerProfile(BaseModel):
    level: str
    handlers: list[str]


class LoggingConfigProfile(BaseModel):
    """Full logging configuration schema."""

    version: int
    disable_existing_loggers: bool
    formatters: dict[str, FormatterProfile]
    handlers: dict[str, HandlerProfile]
    loggers: dict[str, LoggerProfile]
    filters: dict[str, object]
    root: RootLoggerProfile
    scope: str | None = None

    model_config = ConfigDict(extra='forbid', populate_by_name=True)


# -- 6. Section: Integrations


# -- 7. Section: Packages Groups


# -- 8. Top-level Settings (defined last to avoid forward reference issues)
class Settings(BaseModel):
    """Top-level merged settings schema."""

    model_config = ConfigDict(extra='forbid')

    settings_version: str
    app: AppConfigProfile
    environment: dict[str, EnvironmentProfile]
    session: SessionConfigProfile
    paths: PathsConfigProfile
    logging: LoggingConfigProfile
    integrations: dict[str, object] = Field(default_factory=dict)
    packages_groups: dict[str, list[str]] = Field(default_factory=dict)


# --- Validation Functions


def _format_validation_errors(exc: ValidationError) -> list[str]:
    """Return compact human-readable messages for a Pydantic validation error."""
    formatted_errors = []
    for err in exc.errors():
        location = (
            '.'.join(str(part) for part in err.get('loc', ())) or '<root>'
        )
        message = err.get('msg', 'Unknown validation error')
        formatted_errors.append(f'{location}: {message}')
    return formatted_errors


def validate_settings(
    config: Mapping[str, object] | object,
    show: bool = False,
) -> bool:
    """Validate a merged config.

    Returns True when valid. Raises ValidationError if invalid.
    """
    data = config
    logger.debug('Validating settings schema')
    if OmegaConf is not None and OmegaConf.is_config(config):
        data = OmegaConf.to_container(config, resolve=True)

    validated = Settings.model_validate(data)
    logger.debug('Valid schema: True')
    if show:
        logger.info(validated)
    return True


__all__ = [
    'AppConfigProfile',
    'EnvironmentProfile',
    'SessionConfigProfile',
    'PathsConfigProfile',
    'LoggingConfigProfile',
    'Settings',
    'validate_settings',
]
