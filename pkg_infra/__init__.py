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

from pathlib import Path

from pkg_infra._metadata import __author__, __version__


def get_session(
    workspace: str | Path,
    include_location: bool = False,
    config_path: str | Path | None = None,
) -> object:
    """Lazily import and return ``pkg_infra.session.get_session``.

    Args:
        workspace:
            Path to the workspace directory.
        include_location:
            Whether to allow lazy geolocation lookup.
        config_path:
            Optional path to a custom configuration file to merge.

    Returns:
        Session: The current session instance.
    """
    from pkg_infra.session import get_session as _get_session

    return _get_session(
        workspace=workspace,
        include_location=include_location,
        config_path=config_path,
    )


__all__ = ['get_session', '__version__', '__author__']
