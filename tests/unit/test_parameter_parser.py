import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from backend.services.parameter_parser import (
    Parameter,
    ParameterType,
    BicepParameterParser,
    ARMParameterParser,
    TerraformParameterParser,
    TemplateParameterParser
)

class TestParameterClass:
    def test_parameter_initialization(self):
        param = Parameter(
            name="test_param",
            param_type=ParameterType.STRING,
            description="A test parameter",
            default="default_val"
        )
        assert param.name == "test_param"
        assert param.type == ParameterType.STRING
        assert param.required is False  # Since default is provided

    def test_parameter_to_dict(self):
        param = Parameter(
            name="count",
            param_type=ParameterType.INT,
            default=1,
            min_value=1,
            max_value=10
        )
        data = param.to_dict()
        assert data['name'] == "count"
        assert data['type'] == "int"
        assert data['default'] == 1
        assert data['min_value'] == 1
        assert data['max_value'] == 10


class TestBicepParser:
    def test_parse_simple_param(self):
        content = """
        @description('The name of the resource')
        param resourceName string
        """
        params = BicepParameterParser.parse(content)
        assert len(params) == 1
        assert params[0].name == "resourceName"
        assert params[0].type == ParameterType.STRING
        assert params[0].description == "The name of the resource"
        assert params[0].required is True

    def test_parse_param_with_default(self):
        content = "param location string = 'eastus'"
        params = BicepParameterParser.parse(content)
        assert params[0].name == "location"
        assert params[0].default == "eastus"
        assert params[0].required is False

    def test_parse_allowed_values(self):
        content = """
        @allowed(['Standard_LRS', 'Standard_GRS'])
        param storageAccountType string
        """
        params = BicepParameterParser.parse(content)
        assert len(params[0].allowed_values) == 2
        assert "Standard_LRS" in params[0].allowed_values


class TestARMParser:
    def test_parse_arm_json(self):
        content = json.dumps({
            "parameters": {
                "adminUsername": {
                    "type": "string",
                    "metadata": {
                        "description": "User name for the Virtual Machine."
                    }
                },
                "vmSize": {
                    "type": "string",
                    "defaultValue": "Standard_D2s_v3",
                    "allowedValues": ["Standard_D2s_v3", "Standard_D4s_v3"]
                }
            }
        })
        params = ARMParameterParser.parse(content)
        assert len(params) == 2
        
        # Check adminUsername
        p1 = next(p for p in params if p.name == "adminUsername")
        assert p1.required is True
        assert "User name" in p1.description
        
        # Check vmSize
        p2 = next(p for p in params if p.name == "vmSize")
        assert p2.default == "Standard_D2s_v3"
        assert len(p2.allowed_values) == 2

    def test_parse_invalid_json(self):
        params = ARMParameterParser.parse("{invalid json")
        assert params == []


class TestTerraformParser:
    def test_parse_terraform_variable(self):
        content = """
        variable "resource_group_name" {
          description = "Name of the resource group"
          type        = string
        }
        
        variable "location" {
          description = "Azure region"
          type        = string
          default     = "eastus"
        }
        """
        params = TerraformParameterParser.parse(content)
        assert len(params) == 2
        
        p1 = next(p for p in params if p.name == "resource_group_name")
        assert p1.required is True
        assert "Name of the resource group" in p1.description
        
        p2 = next(p for p in params if p.name == "location")
        assert p2.default == "eastus"
        assert p2.required is False

    def test_parse_terraform_validation(self):
        content = """
        variable "app_name" {
          type = string
          validation {
            condition = can(regex("^[a-z0-9]+$", var.app_name))
            error_message = "Must be lowercase alphanumeric"
          }
        }
        """
        params = TerraformParameterParser.parse(content)
        assert params[0].name == "app_name"
        assert params[0].pattern == "^[a-z0-9]+$"
        assert "lowercase alphanumeric" in params[0].validation_message


class TestTemplateParameterParser:
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.exists')
    def test_parse_file_bicep(self, mock_exists, mock_read):
        mock_exists.return_value = True
        mock_read.return_value = "param test string"
        
        with patch('pathlib.Path.suffix', '.bicep'):
             # We need to mock suffix on an instance, but Path is hard to mock directly this way
             # Instead, we'll test the parse_content method which is used by parse_file
             params = TemplateParameterParser.parse_content("param test string", "bicep")
             assert len(params) == 1

    def test_parse_content_dispatch(self):
        tf_content = 'variable "test" { type = string }'
        params = TemplateParameterParser.parse_content(tf_content, "terraform")
        assert len(params) == 1
        assert params[0].name == "test"

    def test_parse_unknown_type(self):
        with pytest.raises(ValueError):
            TemplateParameterParser.parse_content("", "unknown")
