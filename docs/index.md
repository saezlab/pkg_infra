# pkg_infra

<div class="pkg-hero">
  <img src="assets/project-banner-readme.png" alt="pkg_infra project banner">
  <p><a class="md-button md-button--primary" href="installation/">Install pkg_infra</a> <a class="md-button" href="learn/tutorials/quickstart/">Open Quickstart</a></p>
</div>

`pkg_infra` is a shared infrastructure package for the Saezlab Python
ecosystem. It provides a small, standardized layer on top of established
Python tools so downstream packages can rely on the same conventions for
session metadata, configuration, and logging.

## Core capabilities

### Session management

Create a process-wide session object that captures runtime metadata such as the
current workspace, user, hostname, timestamps, timezone, and optional location.

### Layered configuration

Load YAML configuration from multiple sources, merge them in a predictable
order, and validate the result against a Pydantic schema before exposing it to
the rest of the application.

### Logging infrastructure

Build validated `logging.config.dictConfig` payloads, initialize loggers, and
apply package-level or package-group policies without each project having to
recreate the same setup.

## Who this is for

This package is aimed at developers maintaining Python packages in the Saezlab
ecosystem and at projects that need a consistent runtime foundation for
configuration and logging.

## Start here

- If you are new to the package, go to the [Installation](installation.md)
  guide.
- If you want to see the main workflow quickly, start with the
  [Quickstart](learn/tutorials/quickstart.md).
- If you want the project background and motivation, visit the
  [About](pkg_infra-project/project.md) section.

## Main entrypoint

For most downstream packages, the main starting point is:

```python
from pkg_infra import get_session
```

This will initialize the session, load and validate configuration, and set up
logging for the current process.
