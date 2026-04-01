# Core Concepts

This explanation summarizes the core mental model behind `pkg_infra`.

## One package, three responsibilities

`pkg_infra` is centered around three responsibilities:

- Session lifecycle management
- Layered and validated configuration
- Shared logging behavior for individual packages and package groups

These concerns are connected. A session is created with a merged config, and
that same config is used to initialize logging for the process.

## The main entrypoint

Most consumers start with:

```python
from pkg_infra import get_session
```

This is intentionally the shortest path for downstream packages. It avoids each
project having to orchestrate configuration loading and logger setup manually.

## The configuration model

The package ships a baseline YAML configuration and then overlays optional
sources from the user, workspace, environment, and an explicit custom file.
The merged result is validated against the schema before it is used.

The most important top-level config sections are:

- `app`
- `environment`
- `session`
- `paths`
- `logging`
- `integrations`
- `packages_groups`

## Logging policies

Logging is built on top of Python's standard library. `pkg_infra` does not
replace `logging`; it helps standardize how logging is configured across a
package ecosystem.

The default settings support:

- Console and file handlers
- Rotating file logs
- Optional JSON file output
- Package-specific logger entries
- Package-group policies
- Optional async queue-based logging

## What to read next

- [Quickstart](quickstart.md) for the common setup flow
- [Explanations](../explanation/index.md) for design details
- [About the project](../../pkg_infra-project/project.md) for rationale and
  context
