## Description

The `logger` module builds and applies validated logging configurations from the
merged package settings.

## Main Components

- `LoggerConfigurator`: Build and apply final logging configs
- `initialize_logging`: Initialize logging from a config path
- `initialize_logging_from_config`: Initialize logging from an in-memory config
- `get_logger`: Retrieve an initialized logger
- `list_loggers`: Inspect registered loggers

---

::: pkg_infra.logger
