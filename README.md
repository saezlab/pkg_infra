![project-banner](https://raw.githubusercontent.com/saezlab/pkg_infra/main/docs/assets/project-banner-readme.png)

---


[![Tests](https://img.shields.io/github/actions/workflow/status/saezlab/pkg_infra/ci-testing-unit.yml?branch=main)](https://github.com/saezlab/pkg_infra/actions/workflows/ci-testing-unit.yml)
[![Docs](https://img.shields.io/badge/docs-MkDocs-blue)](https://saezlab.github.io/pkg_infra/)
![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
[![PyPI](https://img.shields.io/pypi/v/pkg_infra)](https://pypi.org/project/pkg_infra/)
[![Python](https://img.shields.io/pypi/pyversions/pkg_infra)](https://pypi.org/project/pkg_infra/)
[![PyPI](https://img.shields.io/pypi/v/pkg_infra)](https://pypi.org/project/pkg_infra/)
[![Python](https://img.shields.io/pypi/pyversions/pkg_infra)](https://pypi.org/project/pkg_infra/)
![License](https://img.shields.io/github/license/saezlab/pkg_infra)
![Issues](https://img.shields.io/github/issues/saezlab/pkg_infra)
![Last Commit](https://img.shields.io/github/last-commit/saezlab/pkg_infra)

`pkg_infra` provides shared infrastructure for Saezlab Python packages. It
standardizes three pieces of runtime behavior that are often reimplemented
ad hoc across projects:

- Session metadata for reproducible runs and workspace-aware execution
- Layered YAML configuration with validation and predictable precedence
- Centralized logging based on Python's standard `logging` module



## What it includes

- `pkg_infra.get_session(...)` as the main entrypoint for initializing runtime
  state
- Config loading from ecosystem, package default, user, working directory,
  environment variable, and optional custom file sources
- Pydantic-based validation for the merged settings model
- Logging configuration generation with support for file handlers, JSON output,
  package groups, and async queue-based logging
- A packaged baseline configuration in
  `src/pkg_infra/data/default_settings.yaml`

## Installation

Install the package from PyPI:

```bash
pip install pkg_infra
```

Install it from a local checkout with docs or test extras when developing:

```bash
pip install -e ".[docs,tests]"
```

## Quick Example

```python
from pathlib import Path

from pkg_infra import get_session

session = get_session(
    workspace=Path("."),
    include_location=False,
)

print(session)
print(session.get_config_dict())

corneto_settings = session.get_conf("corneto")
print(corneto_settings)
```

## Configuration Precedence

`pkg_infra` merges configuration sources in this order, where later sources
override earlier ones:

1. Ecosystem config
2. Packaged default config
3. User config
4. Working-directory config
5. Config file pointed to by `PKG_INFRA_CONFIG`
6. Explicit custom config path passed by the caller

## Documentation

The full documentation is published at
<https://saezlab.github.io/pkg_infra/>.

To serve the docs locally without the current upstream Material warning banner:

```bash
source .venv/bin/activate
export NO_MKDOCS_2_WARNING=1
PYTHONPATH=src mkdocs serve
```

Recommended starting points:

- Installation: `docs/installation.md`
- Quickstart: `docs/learn/tutorials/quickstart.md`
- Project context and rationale: `docs/pkg_infra-project/`

## Contributing

Contributions are welcome. The repository includes dedicated guides for
documentation and code contributions in `docs/community/`.

## License

This project is distributed under the MIT License. See `LICENSE` for details.
