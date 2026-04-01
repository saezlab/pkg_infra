# Writing and Overriding Configuration

This guide explains how to write your own configuration file and use it to
override the default behavior of `pkg_infra`.

## How configuration override works

`pkg_infra` merges configuration from several locations. Later sources override
earlier ones:

1. Ecosystem config
2. Packaged default config
3. User config
4. Working-directory config
5. Config file referenced by `PKG_INFRA_CONFIG`
6. Explicit custom config path passed by the caller

This means you usually do not need to rewrite the full default configuration.
You can provide only the sections or values you want to change.

## Minimal override example

The following file changes the active environment and the default logger:

```yaml
app:
  environment: prod
  logger: verbose
```

## Example with paths and integration settings

```yaml
paths:
  log_dir: ./logs
  cache_dir: ./cache

integrations:
  corneto:
    settings:
      network_path: data/networks
```

## Use a config file from the working directory

If you place a file named `04_workdir.yaml` in the working directory, it will
be picked up automatically.

Example:

```yaml
logging:
  file_output_format: json
```

## Use an explicit config file

You can also pass a custom config file directly when requesting the session:

```python
from pathlib import Path

from pkg_infra import get_session

session = get_session(
    workspace=Path("."),
    config_path=Path("my_config.yaml"),
)
```

This is the highest-precedence source and is useful for experiments,
environment-specific runs, or project-level overrides.

## Use an environment variable

You can point `pkg_infra` to a config file with `PKG_INFRA_CONFIG`:

```bash
export PKG_INFRA_CONFIG=/path/to/config.yaml
```

Then create the session normally:

```python
from pathlib import Path

from pkg_infra import get_session

session = get_session(workspace=Path("."))
```

## Practical advice

- Override only the keys you need
- Keep package-specific settings under `integrations`
- Keep logging changes inside the `logging` section
- Use a custom file path for project-specific or temporary behavior
- Validate changes by running the package and checking whether session creation
  succeeds
