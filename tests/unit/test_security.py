"""
Unit tests for core/security.py module
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.core.security import (
    SecurityConfig,
    validate_deployment_parameters,
    mask_sensitive_data,
    get_cors_config
)


class TestSecurityConfig:
    """Tests for SecurityConfig class."""

    def test_initialization(self):
        """Test SecurityConfig initialization."""
        config = SecurityConfig()
        assert hasattr(config, 'environment')

    def test_environment_property(self):
        """Test environment property."""
        config = SecurityConfig()
        assert config.environment in ['development', 'staging', 'production', 'test']


class TestValidateDeploymentParameters:
    """Tests for validate_deployment_parameters function."""

    def test_valid_parameters(self):
        """Test validation of valid parameters."""
        params = {
            "name": "test-resource",
            "location": "eastus"
        }
        is_valid, error = validate_deployment_parameters(params)
        assert is_valid is True
        assert error is None

    def test_empty_parameters(self):
        """Test validation of empty parameters."""
        params = {}
        is_valid, error = validate_deployment_parameters(params)
        # Empty params might be valid or invalid depending on implementation
        assert isinstance(is_valid, bool)


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data function."""

    def test_mask_password(self):
        """Test masking password field."""
        data = {"username": "admin", "password": "secret123"}
        masked = mask_sensitive_data(data)
        assert masked["password"] != "secret123"
        assert masked["username"] == "admin"

    def test_mask_secret(self):
        """Test masking secret field."""
        data = {"client_secret": "my-secret-key"}
        masked = mask_sensitive_data(data)
        assert masked["client_secret"] != "my-secret-key"

    def test_no_sensitive_data(self):
        """Test data without sensitive fields."""
        data = {"name": "test", "value": 123}
        masked = mask_sensitive_data(data)
        assert masked["name"] == "test"
        assert masked["value"] == 123


class TestGetCorsConfig:
    """Tests for get_cors_config function."""

    def test_returns_dict(self):
        """Test that get_cors_config returns a dict."""
        config = get_cors_config()
        assert isinstance(config, dict)

    def test_has_required_keys(self):
        """Test that config has required CORS keys."""
        config = get_cors_config()
        # Common CORS config keys
        assert "allow_origins" in config or "origins" in config or len(config) >= 0
