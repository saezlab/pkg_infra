import copy
from importlib import resources
import logging
import os
from pathlib import Path

from omegaconf import OmegaConf
import platformdirs
from pydantic import ValidationError

from pkg_infra.constants import (
    DEFAULT_PACKAGE_CONFIG_FILENAME,
    ECOSYSTEM_CONFIG_FILENAME,
    ENV_VARIABLE_DEFAULT_CONFIG,
    USER_CONFIG_FILENAME,
    WORKING_DIRECTORY_CONFIG_FILENAME,
)
from pkg_infra.schema import (
    _format_validation_errors,
    validate_settings,
)

# Module logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ConfigLoader:
    """Loader for YAML configuration files with merging and priority logic.

    This class provides a static method to load and merge configuration files from
    package defaults, user directory, working directory, and an explicit path, returning
    a single merged DictConfig object.

    1. (lowest) ecosystem
    2. Package default
    3. User config default
    4. Working directory
    5. Environment variable
    6. Custom directory given by the user.
    """

    @staticmethod
    def load_config(config_path: str | Path | None = None) -> OmegaConf:
        """Load and merge configuration files from various sources, returning a merged OmegaConf object.

        Args:
            config_path: Optional path to a custom configuration file.

        Returns:
            OmegaConf: The merged and validated configuration object.
        """
        logger.info('Starting configuration load')
        paths = resolve_config_paths()
        logger.debug('Resolved config paths: %s', paths)
        parts = [
            load_existing(paths['ecosystem']),
            read_package_default(),
            load_existing(paths['user']),
            load_existing(paths['cwd']),
            load_existing(paths['env']),
        ]
        logger.info(
            'Merging configuration sources: ecosystem=%s, package=%s, user=%s, cwd=%s, env=%s',
            bool(paths['ecosystem'] and paths['ecosystem'].exists()),
            True,
            bool(paths['user'] and paths['user'].exists()),
            bool(paths['cwd'] and paths['cwd'].exists()),
            bool(paths['env'] and paths['env'].exists()),
        )

        if config_path:
            custom_path = Path(config_path)
            if custom_path.exists():
                logger.debug('Loading custom config: %s', custom_path)
                parts.append(load_existing(custom_path))
            else:
                logger.warning(
                    'Custom config path does not exist: %s', custom_path
                )
        else:
            logger.debug('No custom config path provided')

        config = merge_configs([p for p in parts if p is not None])

        logger.info('Validating merged configuration')
        try:
            validate_settings(config=config)
        except ValidationError as exc:
            formatted_errors = _format_validation_errors(exc)
            if not logging.getLogger().handlers:
                logging.basicConfig(level=logging.ERROR)
            logger.error(
                'Configuration loading failed during schema validation with %d error(s): %s',
                len(formatted_errors),
                '; '.join(formatted_errors),
            )
            raise
        logger.info('Configuration loaded and validated')
        return config


def resolve_config_paths() -> dict[str, Path | None]:
    """Resolve and return the standard configuration file paths for the application.

    Returns:
        dict: A dictionary mapping config source names to their resolved Path objects or None.
    """
    ecosystem_dir = Path(platformdirs.site_config_dir('pkg_infra'))
    user_dir = Path(platformdirs.user_config_dir('pkg_infra'))
    env_value = os.environ.get(ENV_VARIABLE_DEFAULT_CONFIG)
    if env_value is None:
        logger.debug(
            'Env var %s not set; skipping env config',
            ENV_VARIABLE_DEFAULT_CONFIG,
        )

    paths = {
        'ecosystem': ecosystem_dir / ECOSYSTEM_CONFIG_FILENAME,
        'package': None,
        'user': user_dir / USER_CONFIG_FILENAME,
        'cwd': Path(WORKING_DIRECTORY_CONFIG_FILENAME),
        'env': Path(env_value) if env_value else None,
        'custom_path': None,
    }
    return paths


def read_package_default() -> OmegaConf:
    """Load and return the package's default configuration as an OmegaConf object.

    Returns:
        OmegaConf: The default configuration, or an empty config if not found.
    """
    try:
        logger.debug(
            'Loading package default config: %s',
            DEFAULT_PACKAGE_CONFIG_FILENAME,
        )
        raw_config_text = (
            resources.files('pkg_infra.data')
            .joinpath(DEFAULT_PACKAGE_CONFIG_FILENAME)
            .read_text(encoding='utf-8')
        )
        return OmegaConf.create(raw_config_text)
    except FileNotFoundError:
        logger.warning(
            'Package default config not found: %s',
            DEFAULT_PACKAGE_CONFIG_FILENAME,
        )
        return OmegaConf.create({})


def load_existing(path: Path | None) -> OmegaConf | None:
    """Load a configuration file from the given path if it exists.

    Args:
        path: Path to the configuration file.

    Returns:
        OmegaConf: The loaded configuration, or None if the file does not exist.
    """
    if path and path.exists():
        logger.debug('Loading config file: %s', path)
        return OmegaConf.load(path)
    if path:
        logger.debug('Config file not found at %s; skipping', path)
    return None


def merge_configs(parts: list[OmegaConf]) -> OmegaConf:
    """Merge a list of OmegaConf configuration objects into one.

    Args:
        parts: List of OmegaConf objects to merge.

    Returns:
        OmegaConf: The merged configuration object.
    """
    if not parts:
        logger.warning('No config parts found; using empty config')
    return OmegaConf.merge(*parts) if parts else OmegaConf.create({})


def omegaconf_to_plain_dict(obj: object) -> object:
    """Recursively convert OmegaConf containers to plain Python objects.

    If ``obj`` is already a ``dict`` or ``list``, a deep copy is returned.
    """
    if 'omegaconf' in str(type(obj)):
        from omegaconf import OmegaConf

        return OmegaConf.to_container(
            obj, resolve=True, structured_config_mode='dict'
        )
    elif isinstance(obj, dict):
        return copy.deepcopy(obj)
    elif isinstance(obj, list):
        return [omegaconf_to_plain_dict(item) for item in obj]
    else:
        return obj
