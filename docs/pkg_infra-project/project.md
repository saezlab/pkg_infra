# Project

## Overview

`pkg_infra` is the Python package infrastructure layer for the Saezlab
ecosystem. Its purpose is to provide standardized logging, configuration
handling, and session management so downstream packages can stop carrying
slightly different local implementations of the same runtime concerns.

For the technical runtime view of how those pieces fit together, see the
[architecture overview](../learn/explanation/index.md).

## Scope

The project currently covers:

- Config loading from multiple locations
- Schema validation of merged settings
- Logging setup using Python's built-in `logging` library
- Session lifecycle management and runtime metadata capture
- Ecosystem-oriented settings for integrations and package groups

## Deliverables

The project context defines the following main deliverables:

- The `pkg_infra` Python package
- Project documentation
- Internal SDLC documentation
- YAML templates and baseline configuration assets

## Stakeholders

The main stakeholders identified for the project are:

- Package developers integrating shared infrastructure into their libraries
- Bioinformatics researchers who benefit indirectly from more reliable tooling
- Software engineers maintaining and extending the infrastructure package

## Constraints

- Python 3.10+
- YAML-based configuration
- Logging built on Python's standard `logging` module
- Predictable config precedence across ecosystem, package, user, local, and
  explicit override levels
