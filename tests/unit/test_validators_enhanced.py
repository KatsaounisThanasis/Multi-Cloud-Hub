
import pytest
from pydantic import ValidationError
from backend.utils.validators import validate_app_name, InvalidParameterError, MissingParameterError
from backend.api.schemas import DeploymentRequest

class TestEnhancedValidators:
    
    def test_validate_app_name_valid(self):
        """Test valid application names."""
        valid_names = ["my-app", "app1", "frontend-service", "prod_db_client"]
        for name in valid_names:
            try:
                validate_app_name(name)
            except Exception as e:
                pytest.fail(f"Valid name '{name}' raised exception: {e}")

    def test_validate_app_name_reserved_words(self):
        """Test that reserved words are rejected."""
        reserved_words = ["admin", "root", "system", "null", "test", "API"] # Mixed case for API
        
        for name in reserved_words:
            with pytest.raises(InvalidParameterError) as excinfo:
                validate_app_name(name)
            assert "reserved word" in str(excinfo.value)

    def test_validate_app_name_format_rules(self):
        """Test structural rules (start with letter, no trailing hyphen, etc.)."""
        invalid_cases = [
            ("1app", "Must start with a letter"),
            ("app-", "Cannot end with hyphen or underscore"),
            ("app_", "Cannot end with hyphen or underscore"),
            ("my@app", "Only letters, numbers, hyphens, and underscores allowed"),
            ("", "param_name") # MissingParameterError checks
        ]

        for name, error_msg in invalid_cases:
            if name == "":
                with pytest.raises(MissingParameterError):
                    validate_app_name(name)
            else:
                with pytest.raises(InvalidParameterError) as excinfo:
                    validate_app_name(name)
                if error_msg != "param_name":
                    assert error_msg in str(excinfo.value) or "Only letters" in str(excinfo.value)

    def test_deployment_request_schema_validation(self):
        """Test that Pydantic schema catches invalid app_name in parameters."""
        
        # Base valid data
        base_data = {
            "template_name": "basic-vm",
            "provider_type": "azure",
            "resource_group": "my-rg",
            "location": "eastus",
            "subscription_id": "sub-123"
        }

        # Case 1: Valid app_name
        valid_data = base_data.copy()
        valid_data["parameters"] = {"app_name": "valid-app-name"}
        try:
            req = DeploymentRequest(**valid_data)
            assert req.parameters["app_name"] == "valid-app-name"
        except ValidationError as e:
            pytest.fail(f"Valid schema data failed validation: {e}")

        # Case 2: Invalid app_name (Reserved Word) in parameters
        invalid_data = base_data.copy()
        invalid_data["parameters"] = {"app_name": "admin"}
        
        with pytest.raises(ValidationError) as excinfo:
            DeploymentRequest(**invalid_data)
        
        # Pydantic wraps the ValueError, so we check string representation
        assert "reserved word" in str(excinfo.value)

        # Case 3: Invalid 'name' parameter (also checked)
        invalid_data_name = base_data.copy()
        invalid_data_name["parameters"] = {"name": "123-invalid"}
        
        with pytest.raises(ValidationError) as excinfo:
            DeploymentRequest(**invalid_data_name)
        
        assert "Must start with a letter" in str(excinfo.value)
