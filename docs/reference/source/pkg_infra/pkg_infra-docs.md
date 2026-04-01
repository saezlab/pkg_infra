## Description

The top-level `pkg_infra` package exposes the main public entrypoint used by
downstream projects. In practice, this means importing `get_session(...)`
without forcing callers to know the internal module layout.

## Main Components

- `get_session`: Initialize or retrieve the process-wide session
- `__version__`: Package version metadata
- `__author__`: Package author metadata

---

::: pkg_infra
