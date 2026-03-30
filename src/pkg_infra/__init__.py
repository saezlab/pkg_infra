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

from pkg_infra._metadata import __author__, __version__

def get_session(*args: object, **kwargs: object) -> object:
    """Lazily import and return pkg_infra.session.get_session to avoid circular import.

    Args:
        workspace (str | Path):
            Path to the workspace directory (required).
        include_location (bool, optional):
            Whether to allow lazy geolocation lookup. Defaults to False.
        config_path (str | Path | None, optional):
            Optional path to a custom configuration file to merge. If provided, this config will be merged with the default config sources.
        *args:
            Additional positional arguments supported by pkg_infra.session.get_session.
        **kwargs:
            Additional keyword arguments supported by pkg_infra.session.get_session.

    Returns:
        Session: The current session instance.
    """
    from pkg_infra.session import get_session as _get_session

    return _get_session(*args, **kwargs)


__all__ = ['get_session', '__version__', '__author__']
