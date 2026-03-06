#!/usr/bin/env python

#
# This file is part of the `pkg_infra` Python module
#
# Copyright 2025
# Heidelberg University Hospital
#
# File author(s): Edwin Carreño (ecarrenolozano@gmail.com)
#
# Distributed under the MIT license
# See the file `LICENSE` or read a copy at
# https://opensource.org/license/mit
#

"""Session handler, configuration, and logging handler for Saezlab packages and applications.
"""

import logging

from pkg_infra.logger import get_root_logger_configured
from pkg_infra.session import get_session
from pkg_infra._metadata import __author__, __version__
from pkg_infra.constants import LOG_TIMESTAMP

# Generate a single timestamp for log files
__log_timestamp__ = LOG_TIMESTAMP

get_root_logger_configured(timestamp=LOG_TIMESTAMP)

__all__ = [
    'get_session',
    '__version__',
    '__author__'
]

# Log import for debugging
logging.info(f'Importing {__name__}')
