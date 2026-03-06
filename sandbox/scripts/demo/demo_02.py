import logging
from pathlib import Path

# Helper to create a logger for the demo
from logging.config import dictConfig

from pydantic import ValidationError

import pkg_infra
import pkg_infra.logger
from pkg_infra.schema import validate_settings
from pkg_infra.session import get_session

def create_logger() -> logging.Logger:
    """Create and return a simple logger for the demo script."""

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'f': {
                'format': '[%(asctime)s] [%(levelname)-5s] [%(name)-25s] ▸ %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'cli': {
                'class': 'logging.StreamHandler',
                'formatter': 'f',
                'level': logging.INFO
            },
            'file':{
                'class': 'logging.FileHandler',
                'formatter': 'f',
                'level': logging.INFO,
                'filename': 'logs/demo_01.log',
            }
        },
        'root': {
            'handlers': ['cli', 'file'],
            'level': logging.INFO
        }
    }
    Path('logs').mkdir(parents=True, exist_ok=True)
    dictConfig(logging_config)
    return logging.getLogger()

def main() -> None:
    """Run the session creation and config validation demo."""

    logger = create_logger()
    logger.info('=== Demo 02: Session and Config Validation ===')

    # 1. Start a session for a new workspace
    session = get_session(workspace='demo_02_workspace')
    logger.info(f'Session created:\n{session}')

    # 2. Show session config keys
    if session.config:
        logger.info(f'Session config keys: {list(session.config.keys())}')
    else:
        logger.warning('No config found in session.')

    # 3. Validate the session config schema
    try:
        valid = validate_settings(session.config)
        logger.info(f'Config schema valid: {valid}')
    except ValidationError as e:
        logger.error(f'Config schema validation failed: {e}')

    # 4. Show logger info
    if session.session_logger:
        logger.info(f'Session logger: {session.session_logger.name}')
    else:
        logger.warning('No session logger found.')

    # 5.
    pkg_infra.logger.list_loggers()

if __name__ == '__main__':
    main()
