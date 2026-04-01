from __future__ import annotations

from datetime import datetime, timezone

from mkdocs.config.defaults import MkDocsConfig


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Set a dynamic copyright year for the MkDocs build."""
    current_year = datetime.now(timezone.utc).year
    config.copyright = (
        f'© Copyright 2021-{current_year}, Saez-lab development team.'
    )
    return config
