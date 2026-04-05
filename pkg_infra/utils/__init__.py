"""General-purpose utility functions.

Migrated from pypath_common._misc, _constants, and _process.
Organized into submodules for clarity; all public functions are
re-exported here for convenience::

    from pkg_infra.utils import to_set, first, ext, swap_dict
"""

from pkg_infra.utils.constants import *  # noqa: F401, F403
from pkg_infra.utils._process import swap_dict  # noqa: F401
from pkg_infra.utils._misc import *  # noqa: F401, F403

# Preserved from original utils.py
import datetime

def get_timestamp_now() -> str:
    """Get the current UTC timestamp with an explicit ``Z`` suffix."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ",
    )
