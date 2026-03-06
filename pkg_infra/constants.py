"""Shared constants for pkg_infra."""

import datetime

LOG_TIMESTAMP = datetime.datetime.now(
    datetime.timezone.utc,  # noqa: UP017
).strftime('%Y%m%d%H%M%S')
