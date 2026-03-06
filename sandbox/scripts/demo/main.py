import logging
import warnings

import pandas as pd

from pkg_infra import get_session

__all__ = [
    'main',
]


def main() -> None:
    """Main entry point for the CLI demo application.

    This function initializes logging, demonstrates logger exclusion,
    captures Python warnings, and exercises log rotation and pandas logging.
    """
    # Capture Python warnings into logging
    logging.captureWarnings(True)
    session = get_session(workspace='scripts/demo')
    log = session.get_logger()
    log.info('Demo started using Session.get_logger!')
    log.debug(
        'This is a DEBUG message (should not appear unless level is DEBUG)'
    )
    log.warning('This is a WARNING message.')
    log.error('This is an ERROR message.')

    # Explicitly log from pandas and matplotlib loggers to test exclusion
    pandas_logger = logging.getLogger('pandas')
    matplotlib_logger = logging.getLogger('matplotlib')
    pandas_logger.info(
        'This is an INFO from pandas logger (should be suppressed or set to WARNING).'
    )
    pandas_logger.warning('This is a WARNING from pandas logger.')
    pandas_logger.error('This is an ERROR from pandas logger.')
    matplotlib_logger.info(
        'This is an INFO from matplotlib logger (should be suppressed or set to WARNING).'
    )
    matplotlib_logger.warning('This is a WARNING from matplotlib logger.')
    matplotlib_logger.error('This is an ERROR from matplotlib logger.')

    # Use pandas and show that its logs are suppressed
    log.info('Creating a pandas DataFrame...')
    df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    log.info(f'DataFrame created:\n{df}')
    # Pandas will emit a warning (not a log) if we trigger a chained assignment warning
    try:
        pd.options.mode.chained_assignment = (
            'warn'  # This triggers a pandas warning log
        )
        df['a'][0] = 10  # Chained assignment warning
    except (pd.errors.SettingWithCopyError, ValueError) as e:
        log.error(f'Caught exception: {e}')

    # Demonstrate log rotation by writing many lines (set max_bytes low in config for test)
    for i in range(10):
        log.info(f'Filling log file for rotation test: line {i + 1}')

    # Show a Python warning
    warnings.warn(
        'This is a test warning captured by logging.', UserWarning, stacklevel=2
    )


if __name__ == '__main__':
    main()
