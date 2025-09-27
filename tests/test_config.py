"""
Unit tests for NaviLinkConfig configuration management.
"""

import os
import tempfile
from pathlib import Path

import pytest

from navilink.config import HTTPConfig, MQTTConfig, NaviLinkConfig, ReconnectConfig
from navilink.exceptions import NaviLinkError


class TestNaviLinkConfig:
    """Test cases for NaviLinkConfig."""

    def test_config_creation(self):
        """Test basic config creation."""
        config = NaviLinkConfig(email="test@example.com", password="test_password")

        assert config.email == "test@example.com"
        assert config.password == "test_password"
        assert config.log_level == "INFO"  # Default value

    def test_config_from_environment(self, monkeypatch):
        """Test config creation from environment variables."""
        monkeypatch.setenv("NAVILINK_EMAIL", "env@example.com")
        monkeypatch.setenv("NAVILINK_PASSWORD", "env_password")
        monkeypatch.setenv("NAVILINK_LOG_LEVEL", "DEBUG")

        config = NaviLinkConfig.from_environment()

        assert config.email == "env@example.com"
        assert config.password == "env_password"
        assert config.log_level == "DEBUG"

    def test_config_from_env_file(self):
        """Test config creation from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("NAVILINK_EMAIL=file@example.com\n")
            f.write("NAVILINK_PASSWORD=file_password\n")
            f.write("NAVILINK_LOG_LEVEL=WARNING\n")
            f.flush()

            try:
                config = NaviLinkConfig.from_environment(env_file=f.name)
                assert config.email == "file@example.com"
                assert config.password == "file_password"
                assert config.log_level == "WARNING"
            finally:
                os.unlink(f.name)

    def test_config_missing_required_fields(self):
        """Test that missing required fields raise appropriate errors."""
        with pytest.raises(ValueError, match="email is required"):
            NaviLinkConfig(email="", password="password")

        with pytest.raises(ValueError, match="password is required"):
            NaviLinkConfig(email="test@example.com", password="")

    def test_config_validation_email_format(self):
        """Test email format validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            NaviLinkConfig(email="invalid-email", password="password")

    def test_config_defaults(self):
        """Test default configuration values."""
        config = NaviLinkConfig(email="test@example.com", password="test_password")

        # Check defaults
        assert config.log_level == "INFO"
        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert isinstance(config.reconnect_config, ReconnectConfig)
        assert isinstance(config.mqtt_config, MQTTConfig)
        assert isinstance(config.http_config, HTTPConfig)


class TestReconnectConfig:
    """Test cases for ReconnectConfig."""

    def test_default_values(self):
        """Test default reconnection configuration."""
        config = ReconnectConfig()

        assert config.max_retries == 20
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom reconnection configuration."""
        config = ReconnectConfig(
            max_retries=10, initial_delay=1.0, max_delay=60.0, jitter=False
        )

        assert config.max_retries == 10
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is False


class TestMQTTConfig:
    """Test cases for MQTTConfig."""

    def test_default_values(self):
        """Test default MQTT configuration."""
        config = MQTTConfig()

        assert config.protocol == "MQTT3"
        assert config.keep_alive == 60
        assert config.clean_session is True
        assert config.auto_reconnect is True

    def test_mqtt5_protocol(self):
        """Test MQTT5 protocol configuration."""
        config = MQTTConfig(protocol="MQTT5")

        assert config.protocol == "MQTT5"

    def test_invalid_protocol(self):
        """Test invalid protocol raises error."""
        with pytest.raises(ValueError, match="Protocol must be"):
            MQTTConfig(protocol="INVALID")


class TestHTTPConfig:
    """Test cases for HTTPConfig."""

    def test_default_values(self):
        """Test default HTTP configuration."""
        config = HTTPConfig()

        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_backoff == 1.0
        assert config.verify_ssl is True

    def test_custom_values(self):
        """Test custom HTTP configuration."""
        config = HTTPConfig(
            timeout=60, max_retries=5, retry_backoff=2.0, verify_ssl=False
        )

        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_backoff == 2.0
        assert config.verify_ssl is False
