"""Access built-in data files shipped with Python packages.

Provides a simple API to load YAML, JSON, and other data files from a
package's ``data/`` or ``_data/`` subdirectory.

Example::

    from pkg_infra.data import load

    # Load data from the calling package's data/ directory
    config = load('default_config.yaml')

    # Load data from a specific package
    ids = load('id_types.json', module='omnipath_utils')
"""

from __future__ import annotations

from typing import Any, Callable
import os
import json
import pathlib as pl
import functools
import collections
import logging

import yaml

__all__ = ['builtins', 'load', 'path']

_logger = logging.getLogger(__name__)

_FORMATS = {
    'json': functools.partial(
        json.load,
        object_pairs_hook=collections.OrderedDict,
    ),
    'yaml': functools.partial(yaml.load, Loader=yaml.FullLoader),
    'txt': None,
    '': None,
}


def _caller_module() -> str:
    """Get the name of the module that called this function."""

    import inspect

    frame = inspect.currentframe()

    try:
        caller = frame.f_back.f_back
        return caller.f_globals.get('__name__', '__main__').split('.')[0]
    finally:
        del frame


def _module_datadir(module: str) -> pl.Path | None:
    """Find the data directory for a module."""

    import importlib

    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError:
        return None

    if mod_path := getattr(mod, '__path__', None):
        base = pl.Path(mod_path[0])
    elif mod_file := getattr(mod, '__file__', None):
        base = pl.Path(mod_file).parent
    else:
        return None

    for dirname in ('data', '_data'):
        datadir = base / dirname
        if datadir.is_dir():
            return datadir

    return None


def path(label: str, module: str | None = None) -> pl.Path | None:
    """Find path to a data file shipped with a package.

    Args:
        label: Filename or label of a built-in dataset.
        module: Package name. Defaults to the calling package.

    Returns:
        Path to the file, or None if not found.
    """

    if os.path.exists(label):
        return pl.Path(label).absolute()

    available = builtins(module or _caller_module())
    stem = label.rsplit('.', maxsplit=1)[0] if '.' in label else label
    return available.get(label) or available.get(stem)


def load(
    label: str,
    module: str | None = None,
    reader: Callable | None = None,
    **kwargs,
) -> Any:
    """Load a data file shipped with a package.

    Args:
        label: Filename or label of a built-in dataset.
        module: Package name. Defaults to the calling package.
        reader: Custom reader function. Auto-detected from extension if None.
        kwargs: Extra arguments passed to the reader.

    Returns:
        The loaded data (typically dict or list).
    """

    module = module or _caller_module()

    if _path := path(label, module):

        if not reader:
            ext = _path.name.rsplit('.', maxsplit=1)[-1].lower()
            if ext == 'tsv':
                kwargs['sep'] = '\t'
            reader = _FORMATS.get(ext, lambda x: x.readlines())

        _logger.debug(
            'Loading built-in data `%s` from module `%s`; path: `%s`.',
            label, module, _path,
        )

        with open(_path) as fp:
            return reader(fp, **kwargs)

    else:
        _logger.debug(
            'Could not find built-in data `%s` in module `%s`.', label, module,
        )


def builtins(module: str | None = None) -> dict[str, pl.Path]:
    """List built-in data files available in a package.

    Args:
        module: Package name. Defaults to the calling package.

    Returns:
        Dict mapping filenames (without extension) to full paths.
    """

    module = module or _caller_module()
    datadir = _module_datadir(module)

    if not datadir or not datadir.is_dir():
        return {}

    return {
        str((pl.Path(d) / pl.Path(f).stem).relative_to(datadir)): pl.Path(d) / f
        for d, dirs, files in os.walk(datadir)
        for f in files
        if pl.Path(f).suffix[1:].lower() in _FORMATS
    }
