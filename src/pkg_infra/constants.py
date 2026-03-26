"""Shared constants for pkg_infra."""

from pkg_infra.utils import get_timestamp_now

# --- General Constants
LOG_TIMESTAMP = get_timestamp_now()

# --- Constants module: config.py
ECOSYSTEM_CONFIG_FILENAME = '01_ecosystem.yaml'
DEFAULT_PACKAGE_CONFIG_FILENAME = 'default_settings.yaml'
USER_CONFIG_FILENAME = '03_user.yaml'
WORKING_DIRECTORY_CONFIG_FILENAME = '04_workdir.yaml'
ENV_VARIABLE_DEFAULT_CONFIG = 'PKG_INFRA_CONFIG'

# --- Constants module: logger.py
DEFAULT_FILENAME_LOG_MISSING = 'logs/pkg_infra.log'
FILE_HANDLER_CLASSES = {
    'logging.FileHandler',
    'logging.handlers.RotatingFileHandler',
}

# --- Constants module: session.py
IPINFO_URL = 'https://ipinfo.io/json'