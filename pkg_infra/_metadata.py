#!/usr/bin/env python

#
# This file is part of the `pkg_infra` Python module
#
# Copyright 2025
# Heidelberg University Hospital
#
# File author(s): Edwin Carreño (ecarrenolozano@gmail.com)
#
# Distributed under the BSD-3-Clause license
# See the file `LICENSE` or read a copy at
# https://opensource.org/license/bsd-3-clause
#

"""Package metadata (version, authors, etc)."""

__all__ = ['get_metadata']

import importlib.metadata
import os
import pathlib

import toml

_VERSION = '0.1.1'


def get_metadata() -> dict:
    """Basic package metadata.

    Retrieves package metadata from the current project directory or from
    the installed package.
    """

    here = pathlib.Path(__file__).parent
    pyproj_toml = 'pyproject.toml'
    meta = {}

    for project_dir in (here, here.parent):
        toml_path = str(project_dir.joinpath(pyproj_toml).absolute())

        if os.path.exists(toml_path):
            pyproject = toml.load(toml_path)
            project = pyproject.get('project', {})
            authors = project.get('authors', [])
            author_names = [
                author.get('name') for author in authors if author.get('name')
            ]

            meta = {
                'name': project.get('name'),
                'version': project.get('version'),
                'author': ', '.join(author_names) if author_names else None,
                'license': project.get('license'),
                'full_metadata': pyproject,
            }

            break

    if not meta:
        try:
            meta = {
                k.lower(): v
                for k, v in importlib.metadata.metadata(here.name).items()
            }

        except importlib.metadata.PackageNotFoundError:
            pass

    meta['version'] = meta.get('version', None) or _VERSION

    return meta


metadata = get_metadata()
__version__ = metadata.get('version', None)
__author__ = metadata.get('author', None)
__license__ = 'BSD-3-Clause'
