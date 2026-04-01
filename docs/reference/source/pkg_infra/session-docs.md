## Description

The `session` module defines the runtime session model and the singleton
manager used by downstream packages.

## Main Components

- `Session`: Frozen runtime metadata container
- `SessionManager`: Thread-safe singleton lifecycle manager
- `get_session`: Main public entrypoint
- `reset_session`: Test-oriented reset helper

---

::: pkg_infra.session
