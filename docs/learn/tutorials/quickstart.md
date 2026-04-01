# Quickstart

This quickstart walks through the main `pkg_infra` workflow: initialize a
session, inspect the merged configuration, and retrieve integration-specific
settings.

## 1. Import the package

```python
from pathlib import Path

from pkg_infra import get_session
```

## 2. Create the session

```python
session = get_session(
    workspace=Path("."),
    include_location=False,
)
```

`get_session(...)` returns a process-wide singleton. On the first call it will:

- Load the merged configuration
- Validate the configuration schema
- Configure logging
- Capture runtime metadata for the current process

Subsequent calls reuse the same session object.

## 3. Inspect runtime metadata

```python
print(session.hostname)
print(session.username)
print(session.workspace)
print(session.started_at_utc)
```

If location lookup is enabled, `session.location` is resolved lazily on first
access.

## 4. Inspect the merged configuration

```python
config_dict = session.get_config_dict()
print(config_dict["app"])
```

If the underlying config is still represented as OmegaConf, you can also render
it as YAML:

```python
print(session.get_config_yaml())
```

## 5. Read settings for a downstream package

Integration-specific settings live under the `integrations` section of the
merged configuration.

```python
corneto_settings = session.get_conf("corneto")
print(corneto_settings)
```

If the named package is unknown or has no `settings` section, `get_conf(...)`
returns an empty dictionary.

## 6. Understand configuration precedence

`pkg_infra` merges configuration sources in this order:

1. Ecosystem defaults
2. Packaged default settings
3. User-level config
4. Working-directory config
5. Config path from the `PKG_INFRA_CONFIG` environment variable
6. Explicit custom config path passed to `get_session(...)`

Later sources override earlier ones.

## 7. Next steps

- Read the [Core Concepts](tutorial0001_basics.md) explanation for the main
  ideas
- Explore the [Explanations](../explanation/index.md) section for config and
  logging behavior
- Use the [Reference](../../reference/source/pkg_infra/pkg_infra-docs.md)
  section for API details
