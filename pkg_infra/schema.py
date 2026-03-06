from __future__ import annotations

import logging
from logging import NullHandler
from collections.abc import Mapping

from pydantic import Field, BaseModel, ConfigDict, ValidationError

try:
    from omegaconf import OmegaConf
except ImportError:  # pragma: no cover - optional in pure schema usage
    OmegaConf = None


_logger = logging.getLogger(__name__)
_logger.addHandler(NullHandler())

# ---- Models

class AppCfg(BaseModel):
    """Application-level settings."""

    model_config = ConfigDict(extra='forbid')

    name: str | None = None
    environment: str
    logger: str


class EnvironmentProfile(BaseModel):
    """Named environment profile."""

    model_config = ConfigDict(extra='forbid')

    name: str
    debug: bool


class SessionCfg(BaseModel):
    """Session metadata defaults."""

    model_config = ConfigDict(extra='forbid')

    id: str | None = None
    user: str | None = None
    workspace: str | None = None
    started_at: str | None = None
    tags: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    """Top-level merged settings schema."""

    model_config = ConfigDict(extra='forbid')

    settings_version: str
    app: AppCfg
    environment: dict[str, EnvironmentProfile]
    session: SessionCfg
    paths: dict[str, str | None]
    logging: dict[str, object]
    integrations: dict[str, object] = Field(default_factory=dict)
    ecosystems: dict[str, list[str]] = Field(default_factory=dict)


def validate_settings(
    config: Mapping[str, object] | object,
    show: bool = False,
) -> bool:
    """Validate a merged config.

    Returns True when valid. Raises ValidationError if invalid.
    """
    data = config
    if OmegaConf is not None and OmegaConf.is_config(config):
        data = OmegaConf.to_container(config, resolve=True)

    try:
        validated = Settings.model_validate(data)
        _logger.info('Valid schema: True')
        if show:
            _logger.info(validated)
        return True
    except ValidationError:
        _logger.exception('Valid schema: False')
        raise

__all__ = [
    'AppCfg',
    'EnvironmentProfile',
    'SessionCfg',
    'Settings',
    'validate_settings',
]
