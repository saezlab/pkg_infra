"""
Unit tests for configuration loading utilities.

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
from pathlib import Path

# Third-party imports
import pytest
from pydantic import ValidationError
from omegaconf import OmegaConf

# Local imports
from pkg_infra.config import (
    USER_CONFIG_FILENAME,
    ECOSYSTEM_CONFIG_FILENAME,
    WORKING_DIRECTORY_CONFIG_FILENAME,
    ConfigLoader,
    load_existing,
    merge_configs,
    read_package_default,
)

# =============================================================================
# ==== Fixtures and Setup
# =============================================================================
@pytest.fixture
def resources_dir() -> Path:
    """Fixture to provide the directory containing YAML resource files."""
    return Path(__file__).resolve().parents[1] / 'resources'


@pytest.fixture
def valid_yaml_path(resources_dir: Path) -> Path:
    """Fixture to provide the valid YAML resource path."""
    return resources_dir / 'valid.yaml'


@pytest.fixture
def invalid_yaml_path(resources_dir: Path) -> Path:
    """Fixture to provide the invalid YAML resource path."""
    return resources_dir / 'invalid.yaml'


# =============================================================================
# ==== Class Test Cases
# =============================================================================
class TestReadPackageDefault:
    """Test cases for read_package_default."""

    # ---- Nominal Case Tests
    def test_nominal_case(self) -> None:
        """Test that the packaged default YAML loads successfully."""
        config = read_package_default()

        assert OmegaConf.is_config(config)

    # ---- Regression Unit Tests
    def test_loaded_default_config_contains_expected_top_level_keys(
        self,
    ) -> None:
        """Test that default config keeps the expected baseline keys."""
        config = read_package_default()

        assert config.settings_version == '0.0.1'
        assert 'app' in config
        assert 'logging' in config


class TestLoadExisting:
    """Test cases for load_existing."""

    # ---- Nominal Case Tests
    def test_nominal_case(self, valid_yaml_path: Path) -> None:
        """Test that an existing YAML file is loaded."""
        config = load_existing(valid_yaml_path)

        assert config is not None
        assert config.app.name == 'demo'

    # ---- Negative Case Tests
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Test that a missing file path returns None."""
        missing_path = tmp_path / 'missing.yaml'

        assert load_existing(missing_path) is None

    # ---- Edge Case Tests
    def test_none_input_returns_none(self) -> None:
        """Test that None input is handled gracefully."""
        assert load_existing(None) is None


class TestMergeConfigs:
    """Test cases for merge_configs."""

    # ---- Nominal Case Tests
    def test_later_configs_override_earlier_ones(self) -> None:
        """Test that later configurations win during merge."""
        base = OmegaConf.create({'app': {'name': 'base'}})
        override = OmegaConf.create({'app': {'name': 'override'}})

        merged = merge_configs([base, override])

        assert merged.app.name == 'override'

    # ---- Edge Case Tests
    def test_empty_input_returns_empty_config(self) -> None:
        """Test that merging no configs returns an empty config."""
        merged = merge_configs([])

        assert OmegaConf.to_container(merged, resolve=True) == {}

    def test_single_config_remains_effectively_unchanged(self) -> None:
        """Test that merging one config preserves its values."""
        single = OmegaConf.create({'app': {'name': 'demo'}})

        merged = merge_configs([single])

        assert merged.app.name == 'demo'

    # ---- Regression Unit Tests
    def test_merge_precedence_remains_stable(self) -> None:
        """Test that the last config keeps highest precedence."""
        first = OmegaConf.create({'paths': {'log_dir': 'first'}})
        second = OmegaConf.create({'paths': {'log_dir': 'second'}})
        third = OmegaConf.create({'paths': {'log_dir': 'third'}})

        merged = merge_configs([first, second, third])

        assert merged.paths.log_dir == 'third'


class TestConfigLoader:
    """Test cases for ConfigLoader.load_config."""

    # ---- Nominal Case Tests
    def test_valid_custom_yaml_loads_successfully(
        self,
        valid_yaml_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that a valid custom YAML file loads and validates."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        config = ConfigLoader.load_config(valid_yaml_path)

        assert config.app.name == 'demo'

    def test_package_default_loads_through_full_loader(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that the full loader can load the packaged defaults."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        config = ConfigLoader.load_config()

        assert config.settings_version == '0.0.1'
        assert config.app.name is None

    # ---- Negative Case Tests
    def test_invalid_schema_raises_validation_error(
        self,
        invalid_yaml_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that invalid schema input raises ValidationError."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        with pytest.raises(ValidationError):
            ConfigLoader.load_config(invalid_yaml_path)

    def test_missing_explicit_custom_path_is_ignored(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that a missing explicit custom path does not crash the load."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        with caplog.at_level('WARNING'):
            config = ConfigLoader.load_config(tmp_path / 'missing.yaml')

        assert config.settings_version == '0.0.1'
        assert 'Custom config path does not exist' in caplog.text

    # ---- Edge Case Tests
    def test_absent_optional_config_sources_do_not_break_loading(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that missing optional sources are skipped safely."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        config = ConfigLoader.load_config()

        assert config.app.environment == 'dev'

    # ---- Regression Unit Tests
    def test_validation_failure_logs_explicit_field_names(
        self,
        invalid_yaml_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that validation logs include offending field names."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(tmp_path / 'site_config'),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(tmp_path / 'user_config'),
        )
        monkeypatch.delenv('PKG_INFRA_CONFIG', raising=False)

        with pytest.raises(ValidationError):
            ConfigLoader.load_config(invalid_yaml_path)

        assert (
            'Configuration loading failed during schema validation'
            in caplog.text
        )
        assert 'my_custon_field_app' in caplog.text

    def test_env_config_keeps_highest_precedence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that environment-config file overrides lower-priority sources."""
        site_dir = tmp_path / 'site_config'
        user_dir = tmp_path / 'user_config'
        site_dir.mkdir()
        user_dir.mkdir()

        (site_dir / ECOSYSTEM_CONFIG_FILENAME).write_text(
            'settings_version: 0.0.1\napp:\n  name: ecosystem\n',
            encoding='utf-8',
        )
        (user_dir / USER_CONFIG_FILENAME).write_text(
            'app:\n  name: user\n',
            encoding='utf-8',
        )
        (tmp_path / WORKING_DIRECTORY_CONFIG_FILENAME).write_text(
            'app:\n  name: workdir\n',
            encoding='utf-8',
        )
        env_path = tmp_path / 'env.yaml'
        env_path.write_text(
            'app:\n  name: env\n',
            encoding='utf-8',
        )

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(site_dir),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(user_dir),
        )
        monkeypatch.setenv('PKG_INFRA_CONFIG', str(env_path))

        config = ConfigLoader.load_config()

        assert config.app.name == 'env'

    def test_full_source_priority_order_is_applied(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that the full source priority chain is respected."""
        site_dir = tmp_path / 'site_config'
        user_dir = tmp_path / 'user_config'
        site_dir.mkdir()
        user_dir.mkdir()

        (site_dir / ECOSYSTEM_CONFIG_FILENAME).write_text(
            'settings_version: 0.0.1\napp:\n  name: ecosystem\n',
            encoding='utf-8',
        )
        (user_dir / USER_CONFIG_FILENAME).write_text(
            'app:\n  name: user\n',
            encoding='utf-8',
        )
        (tmp_path / WORKING_DIRECTORY_CONFIG_FILENAME).write_text(
            'app:\n  name: workdir\n',
            encoding='utf-8',
        )
        env_path = tmp_path / 'env.yaml'
        env_path.write_text(
            'app:\n  name: env\n',
            encoding='utf-8',
        )
        custom_path = tmp_path / 'custom.yaml'
        custom_path.write_text(
            'app:\n  name: custom\n',
            encoding='utf-8',
        )

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.site_config_dir',
            lambda appname: str(site_dir),
        )
        monkeypatch.setattr(
            'pkg_infra.config.platformdirs.user_config_dir',
            lambda appname: str(user_dir),
        )
        monkeypatch.setenv('PKG_INFRA_CONFIG', str(env_path))

        config = ConfigLoader.load_config(custom_path)

        assert config.app.name == 'custom'
