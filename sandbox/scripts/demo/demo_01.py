
"""
Demo 01: Basic session and logger usage

Usage: .venv/bin/python sandbox/scripts/demo/demo_01.py
"""

from pkg_infra import get_session

def main():
    session = get_session('sandbox/scripts/demo', config_path='sandbox/scripts/demo/config.yaml')
    logger = session.session_logger
    if logger is None:
        raise RuntimeError('Session logger is not initialized.')

    # Details about the logger
    logger.info(f'Logger name: {logger.name}')
    logger.info(f'Logger level: {logger.level}')

    # Some examples
    logger.debug('This is a debug message!')
    logger.info('This is an info message!')
    logger.warning('This is a warning message')
    logger.error('This is an error message')

    logger.setLevel(10)
    logger.debug('This is a debug message (should now appear)!')

if __name__ == '__main__':
    main()
