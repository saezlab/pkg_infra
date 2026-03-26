"""
Unit tests for logger utilities.

Unit test organization:
        - Nominal Case Tests: Test the nominal case where the function is expected
            to work correctly with typical input values.
        - Negative Case Tests: Test cases that involve invalid input values or
            scenarios where the function should handle errors gracefully.
        - Edge Case Tests: Test cases that involve boundary conditions or unusual
            input values that may not be common but should still be handled correctly
            by the function.
        - Regression Unit Tests: Test cases that ensure that previously fixed bugs
            do not reoccur and that existing functionality remains intact after
            changes to the codebase.
"""

from __future__ import annotations

# Standard imports
import logging
import sys
import io
import shutil
from pathlib import Path

# Third-party imports
import pytest
import yaml
from omegaconf import OmegaConf

# Local imports
from pkg_infra.logger import (
    initialize_logging,
    initialize_logging_from_config,
    get_logger,
    is_logging_initialized,
    list_loggers,
)


# =============================================================================
# ==== Fixtures and Setup
# =============================================================================

@pytest.fixture(autouse=True)
def isolate_environment(tmp_path):
    """Reset logging system and filesystem for full isolation."""
    logging.shutdown()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    logging.Logger.manager.loggerDict.clear()

    from pkg_infra import logger as logger_module
    logger_module._logging_initialized = False

    yield

    for p in tmp_path.glob("**/logs"):
        shutil.rmtree(p, ignore_errors=True)

    logging.shutdown()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    logging.Logger.manager.loggerDict.clear()
    logger_module._logging_initialized = False


@pytest.fixture
def minimal_logging_config(tmp_path: Path) -> dict:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    return {
        "logging": {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(levelname)s:%(name)s:%(message)s"}
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "filename": str(log_dir / "test.log"),
                    "level": "info",
                }
            },
            "loggers": {
                "test_logger": {
                    "handlers": ["file"],
                    "level": "info",
                    "propagate": False,
                }
            },
            "root": {"level": "warning", "handlers": []},
        }
    }


@pytest.fixture
def initialized_logging(minimal_logging_config):
    initialize_logging_from_config(minimal_logging_config)
    return minimal_logging_config


@pytest.fixture
def fallback_logging_config(tmp_path: Path) -> dict:
    return {
        "logging": {
            "version": 1,
            "formatters": {
                "default": {"format": "%(message)s"}
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "filename": str(tmp_path / "logs" / "root.log"),
                },
            },
            "loggers": {},
            "root": {"handlers": []},
        }
    }


@pytest.fixture
def fallback_logging_config_file(tmp_path, fallback_logging_config):
    cfg = tmp_path / "config.yaml"
    with open(cfg, "w") as f:
        yaml.dump(fallback_logging_config, f)
    return cfg



# =============================================================================
# ==== Class Test Cases
# =============================================================================

class TestInitializeLogging:
    """Tests for logging initialization APIs."""

    # ---- Nominal Case Tests
    def test_initialize_and_write_log(self, tmp_path, initialized_logging):
        logger = get_logger("test_logger")
        msg = "hello"
        logger.info(msg)

        log_files = list((tmp_path / "logs").glob("test_*.log"))
        assert len(log_files) > 0
        assert any(msg in p.read_text() for p in log_files)

    def test_initialize_from_file(self, tmp_path, minimal_logging_config):
        cfg = tmp_path / "config.yaml"
        OmegaConf.save(minimal_logging_config, cfg)

        initialize_logging(str(cfg))
        assert is_logging_initialized()

    # ---- Edge Case Tests
    def test_initialize_with_omegaconf(self, minimal_logging_config):
        cfg = OmegaConf.create(minimal_logging_config)
        initialize_logging_from_config(cfg)
        assert is_logging_initialized()

    # ---- Regression Unit Tests
    def test_initialize_idempotent(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)
        initialize_logging_from_config(minimal_logging_config)
        assert is_logging_initialized()

    def test_no_duplicate_handlers(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)

        root = logging.getLogger()
        before = len(root.handlers)

        initialize_logging_from_config(minimal_logging_config)

        after = len(root.handlers)
        assert before == after


class TestGetLogger:
    """Tests for get_logger validation and behavior."""

    # ---- Nominal Case Tests
    def test_root_logger_access(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)
        root = get_logger("root")
        assert root is logging.getLogger()

    # ---- Negative Case Tests
    def test_get_logger_before_init(self):
        with pytest.raises(RuntimeError):
            get_logger("test_logger")

    def test_invalid_logger_names(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)

        with pytest.raises(ValueError):
            get_logger("")
        with pytest.raises(ValueError):
            get_logger(None)  # type: ignore

    def test_unregistered_logger_rejected(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)

        with pytest.raises(ValueError):
            get_logger("ghost")

    def test_logger_without_handlers_and_no_propagation(self):
        config = {
            "logging": {
                "version": 1,
                "handlers": {},
                "loggers": {
                    "bad": {"handlers": [], "propagate": False}
                },
                "root": {"handlers": []},
            }
        }

        initialize_logging_from_config(config)

        with pytest.raises(ValueError):
            get_logger("bad")

    # ---- Edge Case Tests
    def test_logger_propagates_but_root_has_no_handlers(self):
        config = {
            "logging": {
                "version": 1,
                "handlers": {},
                "loggers": {
                    "test": {"handlers": [], "propagate": True}
                },
                "root": {"handlers": []},
            }
        }

        initialize_logging_from_config(config)

        with pytest.raises(ValueError):
            get_logger("test")


class TestLoggingConfiguration:
    """Tests for configuration transformations and filesystem effects."""

    # ---- Nominal Case Tests
    def test_levels_are_normalized(self, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)

        logger = get_logger("test_logger")
        assert logger.level == logging.INFO
        assert logger.handlers[0].level == logging.INFO

    def test_directory_created(self, tmp_path, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)
        assert (tmp_path / "logs").exists()

    def test_timestamped_filename(self, tmp_path, minimal_logging_config):
        initialize_logging_from_config(minimal_logging_config)

        files = list((tmp_path / "logs").glob("test_*.log"))
        assert len(files) > 0


class TestFallbackBehavior:
    """Tests for fallback handler behavior."""

    # ---- Edge Case Tests
    def test_root_fallback_handlers(self, fallback_logging_config_file, tmp_path, monkeypatch):
        buffer = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buffer)
        monkeypatch.chdir(tmp_path)
        initialize_logging(str(fallback_logging_config_file))
        root = get_logger("root")
        msg = "fallback"
        root.warning(msg)
        assert msg in buffer.getvalue()
        files = list((tmp_path / "logs").glob("root_*.log"))
        assert len(files) > 0
        assert any(msg in p.read_text() for p in files)
        handler_types = {type(h).__name__ for h in root.handlers}
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" in handler_types

    def test_no_fallback_if_root_has_handlers(self, tmp_path, monkeypatch):
        """
        If root.handlers is non-empty, fallback handlers are NOT injected.
        """
        import yaml
        config = {
            "logging": {
                "version": 1,
                "formatters": {"default": {"format": "%(message)s"}},
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "default",
                        "stream": "ext://sys.stdout",
                    },
                    "file": {
                        "class": "logging.FileHandler",
                        "formatter": "default",
                        "filename": str(tmp_path / "logs" / "root.log"),
                    },
                },
                "loggers": {},
                "root": {"handlers": ["console"]},  # Already has a handler
            }
        }
        cfg = tmp_path / "config.yaml"
        with open(cfg, "w") as f:
            yaml.dump(config, f)
        buffer = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buffer)
        monkeypatch.chdir(tmp_path)
        initialize_logging(str(cfg))
        root = get_logger("root")
        msg = "no fallback"
        root.warning(msg)
        assert msg in buffer.getvalue()
        files = list((tmp_path / "logs").glob("root_*.log"))
        # Only console handler should be present, so file should not exist
        assert not files or not any(msg in p.read_text() for p in files)
        handler_types = {type(h).__name__ for h in root.handlers}
        assert handler_types == {"StreamHandler"}

class TestLoggerIntrospection:
    """Tests for logger discovery utilities."""

    # ---- Nominal Case Tests
    def test_list_loggers_contains_registered(self, initialized_logging):
        names = list_loggers()
        assert "test_logger" in names


class TestLoggerInternals:
    """Tests targeting uncovered internal branches."""

    # ---- Negative Case Tests
    def test_missing_logging_section_raises(self):
        from pkg_infra.logger import LoggerConfigurator

        configurator = LoggerConfigurator()

        with pytest.raises(ValueError):
            configurator.logger_setup({}, timestamp="123")

    def test_dictconfig_failure_propagates(self, monkeypatch):
        from pkg_infra.logger import LoggerConfigurator

        def boom(_):
            raise ValueError("boom")

        monkeypatch.setattr("pkg_infra.logger.dictConfig", boom)

        configurator = LoggerConfigurator()

        with pytest.raises(ValueError):
            configurator.logger_setup({"logging": {"version": 1}}, timestamp="123")

    # ---- Edge Case Tests
    def test_timestamp_none_generates_new(self, minimal_logging_config):
        from pkg_infra.logger import LoggerConfigurator

        configurator = LoggerConfigurator()
        configurator.logger_setup(minimal_logging_config, timestamp=None)


class TestRecursiveUpdate:
    """Tests for deep filename recursion."""

    # ---- Edge Case Tests
    def test_nested_filename_update(self):
        from pkg_infra.logger import LogFileManager

        config = {
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "a.log",
                }
            },
            "nested": [
                {"filename": "b.log"},
                [{"filename": "c.log"}],
            ],
        }

        LogFileManager.update_log_filenames(config, timestamp="123")

        assert "a_123.log" in str(config)
        assert "b_123.log" in str(config)
        assert "c_123.log" in str(config)


class TestInitializationLocking:
    """Tests for double-checked locking branches."""

    # ---- Regression Unit Tests
    def test_initialize_logging_already_initialized(self, minimal_logging_config):
        from pkg_infra import logger as logger_module

        logger_module._logging_initialized = True

        initialize_logging_from_config(minimal_logging_config)

    def test_initialize_logging_file_already_initialized(self, tmp_path, minimal_logging_config):
        from pkg_infra import logger as logger_module

        cfg = tmp_path / "config.yaml"
        OmegaConf.save(minimal_logging_config, cfg)

        logger_module._logging_initialized = True

        initialize_logging(str(cfg))


# =============================================================================
# ==== Function Test Cases
# =============================================================================

def test_logfilemanager_create_log_directories(tmp_path):
    from pkg_infra.logger import LogFileManager
    # Multiple handlers, nested directories
    config = {
        "handlers": {
            "file1": {
                "class": "logging.FileHandler",
                "filename": str(tmp_path / "logs1" / "a.log"),
            },
            "file2": {
                "class": "logging.FileHandler",
                "filename": str(tmp_path / "logs2" / "b.log"),
            },
        }
    }
    LogFileManager.create_log_directories(config)
    assert (tmp_path / "logs1").exists()
    assert (tmp_path / "logs2").exists()


def test_patch_file_handlers_for_rotation():
    from pkg_infra.logger import _patch_file_handlers_for_rotation
    config = {
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": "foo.log",
                "maxBytes": 1000,
            },
            "file2": {
                "class": "logging.FileHandler",
                "filename": "bar.log",
                "backupCount": 2,
            },
            "plain": {
                "class": "logging.FileHandler",
                "filename": "baz.log",
            },
        }
    }
    _patch_file_handlers_for_rotation(config)
    assert config["handlers"]["file"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["file2"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["plain"]["class"] == "logging.FileHandler"
    # Defaults
    assert config["handlers"]["file"].get("maxBytes") == 1000
    assert config["handlers"]["file"].get("backupCount") == 5
    assert config["handlers"]["file2"].get("maxBytes") == 10485760
    assert config["handlers"]["file2"].get("backupCount") == 2


def test_uppercase_levels():
    from pkg_infra.logger import _uppercase_levels
    config = {
        "level": "info",
        "handlers": [
            {"level": "debug"},
            {"nested": {"level": "warning"}},
        ],
        "loggers": {
            "foo": {"level": "error"}
        }
    }
    _uppercase_levels(config)
    assert config["level"] == "INFO"
    assert config["handlers"][0]["level"] == "DEBUG"
    assert config["handlers"][1]["nested"]["level"] == "WARNING"
    assert config["loggers"]["foo"]["level"] == "ERROR"


def test_ensure_root_handlers_injects_and_skips():
    from pkg_infra.logger import _ensure_root_handlers
    # Should inject fallback
    config = {
        "handlers": {"console": {}, "file": {}},
        "root": {},
    }
    _ensure_root_handlers(config)
    assert set(config["root"]["handlers"]) == {"console", "file"}
    # Should not inject if already present
    config2 = {
        "handlers": {"console": {}, "file": {}},
        "root": {"handlers": ["console"]},
    }
    _ensure_root_handlers(config2)
    assert config2["root"]["handlers"] == ["console"]


def test_update_single_filename():
    from pkg_infra.logger import _update_single_filename
    assert _update_single_filename("foo.log", "123") == "foo_123.log"
    assert _update_single_filename("bar", "456") == "bar_456"
    assert _update_single_filename("baz.txt", "789") == "baz_789.txt"