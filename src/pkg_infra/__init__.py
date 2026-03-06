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

"""Session handler, configuration, and logging handler for Saezlab packages and applications."""

from pkg_infra.session import get_session
from pkg_infra._metadata import __author__, __version__

__all__ = ['get_session', '__version__', '__author__']
