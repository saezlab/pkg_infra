"""
Unit tests for schema validation utilities.

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
from copy import deepcopy

# Third-party imports
import pytest
from pydantic import ValidationError

# Local imports
from pkg_infra.schema import validate_settings

# =============================================================================
# ==== Fixtures and Setup
# =============================================================================
@pytest.fixture
def valid_config_dict() -> dict[str, object]:
    """Fixture to provide a valid configuration payload."""
    return {
        'settings_version': '0.0.1',
        'app': {
            'name': 'demo',
            'environment': 'dev',
            'logger': 'default',
        },
        'environment': {
            'dev': {
                'name': 'development',
                'debug': True,
            }
        },
        'session': {
            'id': None,
            'user': None,
            'workspace': None,
            'started_at': None,
            'tags': [],
        },
        'paths': {
            'data_dir': None,
            'cache_dir': None,
            'log_dir': None,
            'temp_dir': None,
        },
        'logging': {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {},
            'handlers': {},
            'loggers': {},
            'filters': {},
            'root': {
                'level': 'WARNING',
                'handlers': [],
            },
        },
        'integrations': {},
        'packages_groups': {},
    }


# =============================================================================
# ==== Class Test Cases
# =============================================================================
class TestValidateSettings:
    """Test cases for validate_settings."""

    # ---- Nominal Case Tests
    def test_nominal_case(self, valid_config_dict: dict[str, object]) -> None:
        """Test that a valid configuration passes schema validation."""
        assert validate_settings(valid_config_dict) is True

    # ---- Negative Case Tests
    def test_unknown_top_level_field_raises_validation_error(
        self,
        valid_config_dict: dict[str, object],
    ) -> None:
        """Test that an unknown top-level field is rejected."""
        invalid_config = deepcopy(valid_config_dict)
        invalid_config['my_custon_field_app'] = {
            'name': 'demo',
            'environment': 'dev',
            'logger': 'default',
        }

        with pytest.raises(ValidationError):
            validate_settings(invalid_config)

    def test_missing_required_section_raises_validation_error(
        self,
        valid_config_dict: dict[str, object],
    ) -> None:
        """Test that removing a required section fails validation."""
        invalid_config = deepcopy(valid_config_dict)
        invalid_config.pop('app')

        with pytest.raises(ValidationError):
            validate_settings(invalid_config)

    # ---- Edge Case Tests
    def test_nullable_session_fields_are_accepted(
        self,
        valid_config_dict: dict[str, object],
    ) -> None:
        """Test that nullable session fields remain valid."""
        config = deepcopy(valid_config_dict)
        config['session'] = {
            'id': None,
            'user': None,
            'workspace': None,
            'started_at': None,
            'tags': [],
        }

        assert validate_settings(config) is True

    # ---- Regression Unit Tests
    def test_validation_error_preserves_offending_field_name(
        self,
        valid_config_dict: dict[str, object],
    ) -> None:
        """Test that validation errors keep the invalid field name."""
        invalid_config = deepcopy(valid_config_dict)
        invalid_config['my_custon_field_app'] = {
            'name': 'demo',
            'environment': 'dev',
            'logger': 'default',
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_settings(invalid_config)

        assert 'my_custon_field_app' in str(exc_info.value)



