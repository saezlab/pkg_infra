
"""
Demo 02: Session and config inspection

Usage: .venv/bin/python sandbox/scripts/demo/demo_02.py
"""

from pkg_infra import get_session

def main():
    session = get_session('sandbox/scripts/demo', config_path='sandbox/scripts/demo/config.yaml')
    logger = session.session_logger
    if logger is None:
        raise RuntimeError('Session logger is not initialized.')

    logger.info('=== Demo 02: Session and Config Inspection ===')
    logger.info(f'Session created:\n{session}')

    # Show session config keys
    if session.config:
        logger.info(f'Session config keys: {list(session.config.keys())}')
    else:
        logger.warning('No config found in session.')

    # Show logger info
    logger.info(f'Session logger: {logger.name}')

    # List all known loggers
    import pkg_infra.logger
    logger.info(f'Known loggers: {pkg_infra.logger.list_loggers()}')

if __name__ == '__main__':
    main()
