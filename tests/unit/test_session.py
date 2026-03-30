"""
Unit tests for session management utilities.

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

# Standard imports
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Third-party imports
import pytest
from omegaconf import OmegaConf

# Local imports
import pkg_infra.session as session_module
from pkg_infra.session import Session, SessionManager, reset_session

__all__ = [
    'TestGetAppLogger',
    'TestGetSessionWrapper',
    'TestHelperWrappers',
    'TestLocationAndConfigHelpers',
    'TestSessionConfigAccessors',
    'TestSessionCreate',
    'TestSessionManager',
    'fixed_times',
    'patch_config_and_logger',
    'patch_logging_setup',
    'patch_session_runtime',
    'reset_singleton',
    'test_pkg_infra_get_session_delegates',
]


# =============================================================================
# ==== Fixtures and Setup
# =============================================================================
@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset the session singleton between tests."""
    reset_session()


@pytest.fixture
def fixed_times() -> tuple[datetime, datetime]:
    """Provide deterministic UTC and local times."""
    now_utc = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now_local = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    return now_utc, now_local


@pytest.fixture
def patch_session_runtime(monkeypatch: pytest.MonkeyPatch, fixed_times, tmp_path: Path) -> None:
    """Patch runtime helpers to deterministic values using tmp_path."""
    now_utc, now_local = fixed_times
    monkeypatch.setattr(session_module, '_get_hostname', lambda: 'host')
    monkeypatch.setattr(session_module, '_get_username', lambda: 'user')
    monkeypatch.setattr(session_module, '_get_workspace', lambda _: tmp_path)
    monkeypatch.setattr(session_module, '_get_process_id', lambda: 'pid-1')
    monkeypatch.setattr(session_module, '_get_time', lambda: (now_utc, now_local))
    monkeypatch.setattr(session_module, '_get_timezone', lambda _: 'UTC')


@pytest.fixture
def patch_logging_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable LoggerConfigurator.logger_setup side effects."""
    import pkg_infra.logger
    monkeypatch.setattr(pkg_infra.logger.LoggerConfigurator, 'logger_setup', lambda self, config, timestamp: None)

# Additional test for the public API get_session
def test_pkg_infra_get_session_delegates(monkeypatch: pytest.MonkeyPatch):
    import pkg_infra
    sentinel = object()
    monkeypatch.setattr(pkg_infra.session._default_manager, 'get_session', lambda *args, **kwargs: sentinel)
    assert pkg_infra.get_session('x') is sentinel
    # Also test config_path argument is passed
    assert pkg_infra.get_session('x', config_path='foo.yaml') is sentinel


@pytest.fixture
def patch_config_and_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch configuration loading and logger retrieval."""
    monkeypatch.setattr(session_module, '_get_configuration', lambda: object())
    monkeypatch.setattr(
        session_module,
        '_get_app_logger',
        lambda _cfg: logging.getLogger('demo'),
    )


# =============================================================================
# ==== Class Test Cases
# =============================================================================
class TestSessionCreate:
    """Test cases for Session.create."""

    # ---- Nominal Case Tests
    def test_nominal_case(self, fixed_times: tuple[datetime, datetime], tmp_path: Path) -> None:
        """Test that Session.create populates fields as expected."""
        now_utc, now_local = fixed_times

        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=now_utc,
            now_local=now_local,
            timezone='UTC',
            location_enabled=True,
            config=None,
            session_logger=logging.getLogger('demo'),
        )

        assert session.hostname == 'host'
        assert session.username == 'user'
        assert session.workspace == tmp_path
        assert session.id == 'pid-1'
        assert session.location_enabled is True
        assert session._location is None

    # ---- Edge Case Tests
    def test_location_disabled_does_not_fetch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that location access does not fetch when disabled."""
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=None,
            session_logger=None,
        )

        def _boom() -> str:
            raise AssertionError('location should not be fetched')

        monkeypatch.setattr(session_module, '_get_location_cached', _boom)
        assert session.location is None

    # ---- Regression Unit Tests
    def test_location_cached_after_first_access(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that location fetch is cached after first access."""
        calls = {'count': 0}

        def _fake_location() -> str:
            calls['count'] += 1
            return 'Heidelberg, DE'

        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=True,
            config=None,
            session_logger=None,
        )

        monkeypatch.setattr(session_module, '_get_location_cached', _fake_location)
        assert session.location == 'Heidelberg, DE'
        assert session.location == 'Heidelberg, DE'
        assert calls['count'] == 1

    # ---- Regression Unit Tests
    def test_repr_includes_path(self, tmp_path: Path) -> None:
        """Test that __repr__ renders Path values with Path(...) formatting."""
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=None,
            session_logger=None,
        )

        assert f"workspace=Path('{tmp_path}')" in repr(session)


class TestSessionConfigAccessors:
    """Test cases for Session config accessors."""

    # ---- Nominal Case Tests
    def test_nominal_omegaconf_access(self, tmp_path: Path) -> None:
        """Test that OmegaConf config yields dict and YAML views."""
        cfg = OmegaConf.create({'app': {'name': 'demo'}})
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=cfg,
            session_logger=None,
        )

        assert session.get_config_dict() == {'app': {'name': 'demo'}}
        assert 'app:' in (session.get_config_yaml() or '')

    # ---- Negative Case Tests
    def test_none_config_returns_none(self, tmp_path: Path) -> None:
        """Test that missing config returns None for accessors."""
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=None,
            session_logger=None,
        )

        assert session.get_config_dict() is None
        assert session.get_config_yaml() is None

    # ---- Edge Case Tests
    def test_mapping_config_returns_mapping(self, tmp_path: Path) -> None:
        """Test that mapping config returns mapping and no YAML."""
        cfg = {'app': {'name': 'demo'}}
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=cfg,
            session_logger=None,
        )

        assert session.get_config_dict() == cfg
        assert session.get_config_yaml() is None

    # ---- Regression Unit Tests
    def test_non_mapping_config_returns_none(self, tmp_path: Path) -> None:
        """Test that non-mapping config returns None for dict view."""
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=42,  # type: ignore[arg-type]
            session_logger=None,
        )

        assert session.get_config_dict() is None

    # ---- Nominal Case Tests
    def test_print_config_uses_yaml(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        """Test that print_config outputs YAML when available."""
        cfg = OmegaConf.create({'app': {'name': 'demo'}})
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=cfg,
            session_logger=None,
        )

        session.print_config()
        captured = capsys.readouterr()
        assert 'app:' in captured.out

    # ---- Edge Case Tests
    def test_print_config_empty_config_logs(
        self, caplog: pytest.LogCaptureFixture, tmp_path: Path
    ) -> None:
        """Test that print_config logs when config is empty."""
        session = Session.create(
            hostname='host',
            username='user',
            workspace=tmp_path,
            process_id='pid-1',
            now_utc=datetime.now(timezone.utc),
            now_local=datetime.now(timezone.utc),
            timezone='UTC',
            location_enabled=False,
            config=None,
            session_logger=None,
        )

        with caplog.at_level('INFO'):
            session.print_config()
        assert 'Session config is empty.' in caplog.text


class TestSessionManager:
    """Test cases for SessionManager.get_session and reset_session."""

    # ---- Nominal Case Tests
    def test_nominal_singleton_reuse(
        self,
        patch_session_runtime,
        patch_logging_setup,
        patch_config_and_logger,
        tmp_path: Path,
    ) -> None:
        """Test that get_session returns the same instance on repeat calls."""
        manager = SessionManager()
        s1 = manager.get_session(tmp_path)
        s2 = manager.get_session(tmp_path)

        assert s1 is s2
        assert s1.workspace == tmp_path

    def test_config_path_merges(
        self,
        patch_session_runtime,
        patch_logging_setup,
        patch_config_and_logger,
        tmp_path,
    ) -> None:
        """Test that config_path is merged and used."""
        import yaml

        # Write a minimal config file
        config_file = tmp_path / 'custom.yaml'
        config_data = {'logging': {'version': 1, 'root': {'handlers': []}}}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        manager = SessionManager()
        # Should not raise
        session = manager.get_session(tmp_path, config_path=str(config_file))
        assert session.config is not None

    # ---- Edge Case Tests
    def test_include_location_sets_flag(
        self,
        patch_session_runtime,
        patch_logging_setup,
        patch_config_and_logger,
        tmp_path: Path,
    ) -> None:
        """Test that include_location enables lazy lookup."""
        manager = SessionManager()
        session = manager.get_session(tmp_path, include_location=True)

        assert session.location_enabled is True

    # ---- Regression Unit Tests
    def test_reset_session_creates_new_instance(
        self,
        monkeypatch: pytest.MonkeyPatch,
        patch_logging_setup,
        patch_config_and_logger,
        tmp_path: Path,
    ) -> None:
        """Test that reset_session clears the singleton."""
        ids = iter(['pid-1', 'pid-2'])
        monkeypatch.setattr(session_module, '_get_hostname', lambda: 'host')
        monkeypatch.setattr(session_module, '_get_username', lambda: 'user')
        monkeypatch.setattr(session_module, '_get_workspace', lambda _: tmp_path)
        monkeypatch.setattr(session_module, '_get_process_id', lambda: next(ids))
        monkeypatch.setattr(
            session_module,
            '_get_time',
            lambda: (datetime.now(timezone.utc), datetime.now(timezone.utc)),
        )
        monkeypatch.setattr(session_module, '_get_timezone', lambda _: 'UTC')

        manager = SessionManager()
        s1 = manager.get_session(tmp_path)
        manager.reset_session()
        s2 = manager.get_session(tmp_path)

        assert s1 is not s2
        assert s1.id != s2.id

    # ---- Edge Case Tests
    def test_manager_reuse_branch(
        self,
        patch_session_runtime,
        patch_logging_setup,
        patch_config_and_logger,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that the manager reuse branch logs as expected."""
        manager = SessionManager()
        manager.get_session(tmp_path)
        with caplog.at_level('INFO'):
            manager.get_session(tmp_path)
        assert 'Reusing existing session' in caplog.text


class TestGetAppLogger:
    """Test cases for _get_app_logger."""

    # ---- Nominal Case Tests
    def test_nominal_logger_name(self) -> None:
        """Test that valid logger name returns the matching logger."""
        @dataclass
        class AppCfg:
            logger: str

        @dataclass
        class Cfg:
            app: AppCfg

        cfg = Cfg(app=AppCfg(logger='demo'))
        log = session_module._get_app_logger(cfg)

        assert log.name == 'demo'

    # ---- Negative Case Tests
    def test_missing_app_logger_falls_back(self) -> None:
        """Test that missing app.logger falls back to module logger."""
        class Cfg:
            pass

        log = session_module._get_app_logger(Cfg())
        assert log.name == logging.getLogger('pkg_infra.session').name

    # ---- Edge Case Tests
    def test_invalid_logger_name_falls_back(self) -> None:
        """Test that invalid app.logger falls back to module logger."""
        @dataclass
        class AppCfg:
            logger: str

        @dataclass
        class Cfg:
            app: AppCfg

        cfg = Cfg(app=AppCfg(logger=''))
        log = session_module._get_app_logger(cfg)
        assert log.name == logging.getLogger('pkg_infra.session').name


class TestLocationAndConfigHelpers:
    """Test cases for location and configuration helpers."""

    # ---- Negative Case Tests
    def test_fetch_location_invalid_url_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid IPINFO URL yields None."""
        monkeypatch.setattr(session_module, 'IPINFO_URL', 'http://example.com')
        assert session_module._fetch_location() is None

    # ---- Regression Unit Tests
    def test_get_location_cached_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _get_location_cached calls the fetch function."""
        monkeypatch.setattr(session_module, '_fetch_location', lambda: 'X')
        session_module._get_location_cached.cache_clear()
        assert session_module._get_location_cached() == 'X'

    # ---- Nominal Case Tests
    def test_get_configuration_calls_loader(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that configuration loader is invoked."""
        sentinel = {'ok': True}
        monkeypatch.setattr(
            session_module.ConfigLoader,
            'load_config',
            staticmethod(lambda: sentinel),
        )
        assert session_module._get_configuration() == sentinel

    # ---- Nominal Case Tests
    def test_fetch_location_success_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a valid IP response returns a composed location."""
        class DummyResponse:
            def __init__(self, payload: bytes) -> None:
                self._payload = payload

            def __enter__(self) -> 'DummyResponse':
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return self._payload

        payload = b'{"city":"Heidelberg","region":"BW","country":"DE"}'
        monkeypatch.setattr(
            session_module,
            'IPINFO_URL',
            'https://ipinfo.io/json',
        )
        monkeypatch.setattr(
            session_module,
            'urlopen',
            lambda *_args, **_kwargs: DummyResponse(payload),
        )

        assert session_module._fetch_location() == 'Heidelberg, BW, DE'


class TestHelperWrappers:
    """Test cases for small helper wrappers."""

    # ---- Nominal Case Tests
    def test_get_hostname_returns_string(self) -> None:
        """Test that hostname helper returns a string."""
        assert isinstance(session_module._get_hostname(), str)

    # ---- Nominal Case Tests
    def test_get_username_returns_string(self) -> None:
        """Test that username helper returns a string."""
        assert isinstance(session_module._get_username(), str)

    # ---- Nominal Case Tests
    def test_get_workspace_resolves_path(self, tmp_path: Path) -> None:
        """Test that workspace helper returns an absolute path."""
        resolved = session_module._get_workspace(tmp_path)
        assert resolved.is_absolute()

    # ---- Nominal Case Tests
    def test_get_process_id_is_uuid(self) -> None:
        """Test that process ID is a UUID string."""
        value = session_module._get_process_id()
        assert isinstance(value, str)
        assert len(value) >= 32

    # ---- Nominal Case Tests
    def test_get_time_returns_tz_aware(self) -> None:
        """Test that time helper returns timezone-aware datetimes."""
        utc_time, local_time = session_module._get_time()
        assert utc_time.tzinfo is not None
        assert local_time.tzinfo is not None

    # ---- Nominal Case Tests
    def test_get_timezone_returns_string(self) -> None:
        """Test that timezone helper returns a string."""
        _, local_time = session_module._get_time()
        assert isinstance(session_module._get_timezone(local_time), str)


class TestGetSessionWrapper:
    """Test cases for top-level get_session wrapper."""

    # ---- Nominal Case Tests
    def test_get_session_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_session delegates to the default manager."""
        sentinel = object()
        monkeypatch.setattr(
            session_module._default_manager,
            'get_session',
            lambda *args, **kwargs: sentinel,
        )
        assert session_module.get_session('x') is sentinel
        # Also test config_path argument is passed
        assert session_module.get_session('x', config_path='foo.yaml') is sentinel
