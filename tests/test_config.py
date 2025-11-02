"""Tests for configuration and secrets management."""

import os

import pytest

from app.config import Config


def test_config_masks_secrets_in_repr():
    """Test that secrets are masked in string representation"""

    os.environ["SECRET_KEY"] = "sasdasd"
    config = Config()

    repr_str = repr(config)

    assert "asdad" not in repr_str
    assert "***" in repr_str

    del os.environ["SECRET_KEY"]


def test_config_loads_optional_secrets():
    """Test that optional secrets don't raise errors when missing"""
    for key in ["DATABASE_URL", "SECRET_KEY", "EXTERNAL_API_KEY"]:
        if key in os.environ:
            del os.environ[key]

    config = Config()

    assert config.database_url is None
    assert config.secret_key is None
    assert config.external_api_key is None


def test_config_loads_from_environment():
    """Test that config correctly loads from environment variables"""
    os.environ["DATABASE_URL"] = "postgresql://localhost/testdb"
    os.environ["SECRET_KEY"] = "asdasd"

    config = Config()

    assert config.database_url == "postgresql://localhost/testdb"
    assert config.secret_key == "asdasd"

    del os.environ["DATABASE_URL"]
    del os.environ["SECRET_KEY"]


def test_config_required_secret_raises_error():
    """Test that missing required secrets raise ValueError"""
    if "REQUIRED_TEST_KEY" in os.environ:
        del os.environ["REQUIRED_TEST_KEY"]

    config = Config()

    with pytest.raises(ValueError, match="Required secret.*not found"):
        config._get_secret("REQUIRED_TEST_KEY", required=True)


def test_config_debug_mode():
    """Test debug mode configuration"""
    os.environ["DEBUG"] = "true"
    config = Config()
    assert config.debug is True

    os.environ["DEBUG"] = "false"
    config = Config()
    assert config.debug is False

    if "DEBUG" in os.environ:
        del os.environ["DEBUG"]
    config = Config()
    assert config.debug is False


def test_config_environment_setting():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["SECRET_KEY"] = "test-prod-key"
    config = Config()
    assert config.environment == "production"

    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]
    config = Config()
    assert config.environment == "development"


def test_validate_production_secrets_passes_without_requirements():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["SECRET_KEY"] = "test-prod-key"
    config = Config()

    config.validate_production_secrets()

    del os.environ["ENVIRONMENT"]
    del os.environ["SECRET_KEY"]


def test_config_does_not_log_secrets():
    """Test that converting config to string doesn't expose secrets"""
    os.environ["SECRET_KEY"] = "asdasd"
    os.environ["EXTERNAL_API_KEY"] = "asdasd"

    config = Config()

    repr_str = repr(config)
    assert "asdasd" not in repr_str
    assert "asdasd" not in repr_str

    str_str = str(config)
    assert "asdasd" not in str_str
    assert "asdasd" not in str_str

    del os.environ["SECRET_KEY"]
    del os.environ["EXTERNAL_API_KEY"]


def test_config_handles_empty_string_secrets():
    """Test that empty string is treated as missing secret"""
    os.environ["SECRET_KEY"] = ""
    config = Config()

    assert not config.secret_key

    del os.environ["SECRET_KEY"]
