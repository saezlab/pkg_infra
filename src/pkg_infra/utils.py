"""Utility functions for the pkg_infra package.

This module provides helper functions that can be used throughout the pkg_infra
package, such as timestamp generation and other general utilities.
"""

import datetime

def get_timestamp_now() -> str:
    """Get the current timestamp as a string in 'YYYYMMDDHHMMSS' format (UTC).

    Returns:
        str: The current UTC timestamp formatted as 'YYYYMMDDHHMMSS'.
    """
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
