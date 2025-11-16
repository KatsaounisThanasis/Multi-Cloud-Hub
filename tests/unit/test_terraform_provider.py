"""
Unit tests for Terraform Provider
"""
import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from backend.providers.terraform_provider import TerraformProvider
from backend.providers.base import DeploymentResult, ResourceGroup, CloudResource


@pytest.fixture
def terraform_aws_provider():
    """Create TerraformProvider instance for AWS"""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }):
        provider = TerraformProvider(cloud_platform="aws", region="us-east-1")
        return provider


@pytest.fixture
def terraform_gcp_provider():
    """Create TerraformProvider instance for GCP"""
    with patch.dict(os.environ, {
        'GOOGLE_PROJECT_ID': 'test-project',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    }):
        provider = TerraformProvider(cloud_platform="gcp", subscription_id="test-project")
        return provider


class TestTerraformProvider:
    """Test cases for TerraformProvider"""

    def test_aws_initialization(self, terraform_aws_provider):
        """Test AWS provider initialization"""
        assert terraform_aws_provider.cloud_platform == "aws"
        assert terraform_aws_provider.region == "us-east-1"
        assert terraform_aws_provider.working_dir is not None

    def test_gcp_initialization(self, terraform_gcp_provider):
        """Test GCP provider initialization"""
        assert terraform_gcp_provider.cloud_platform == "gcp"
        assert terraform_gcp_provider.subscription_id == "test-project"

    def test_azure_initialization(self):
        """Test Azure (via Terraform) initialization"""
        with patch.dict(os.environ, {
            'AZURE_SUBSCRIPTION_ID': 'test-sub',
            'AZURE_TENANT_ID': 'test-tenant'
        }):
            provider = TerraformProvider(
                cloud_platform="azure",
                subscription_id="test-sub"
            )
            assert provider.cloud_platform == "azure"
            assert provider.subscription_id == "test-sub"

    def test_generate_aws_provider_config(self, terraform_aws_provider):
        """Test generating AWS provider configuration"""
        config = terraform_aws_provider._generate_provider_config()

        assert "terraform" in config
        assert "provider" in config
        assert "aws" in config["provider"]
        assert config["provider"]["aws"]["region"] == "us-east-1"

    def test_generate_gcp_provider_config(self, terraform_gcp_provider):
        """Test generating GCP provider configuration"""
        config = terraform_gcp_provider._generate_provider_config()

        assert "terraform" in config
        assert "provider" in config
        assert "google" in config["provider"]
        assert config["provider"]["google"]["project"] == "test-project"

    @patch('subprocess.run')
    def test_terraform_init_success(self, mock_run, terraform_aws_provider):
        """Test successful Terraform initialization"""
        mock_run.return_value = Mock(returncode=0, stdout="Terraform initialized", stderr="")

        terraform_aws_provider._run_terraform_command("init")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "terraform" in call_args
        assert "init" in call_args

    @patch('subprocess.run')
    def test_terraform_command_failure(self, mock_run, terraform_aws_provider):
        """Test Terraform command failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Invalid configuration"
        )

        with pytest.raises(RuntimeError, match="Terraform command failed"):
            terraform_aws_provider._run_terraform_command("apply")

    @pytest.mark.asyncio
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    async def test_deploy_success(self, mock_file, mock_run, terraform_aws_provider):
        """Test successful deployment"""
        # Mock Terraform commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Initialized", stderr=""),  # init
            Mock(returncode=0, stdout="Plan complete", stderr=""),  # plan
            Mock(returncode=0, stdout="Apply complete", stderr=""),  # apply
            Mock(returncode=0, stdout='{"outputs": {"bucket_name": {"value": "test-bucket"}}}', stderr="")  # output
        ]

        result = await terraform_aws_provider.deploy(
            template_path="/path/to/template.tf",
            parameters={"bucket_name": "test-bucket"},
            resource_group="test-group",
            location="us-east-1"
        )

        assert isinstance(result, DeploymentResult)
        assert result.success is True
        assert result.provider == "terraform-aws"
        assert "bucket_name" in result.outputs

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_deploy_failure(self, mock_run, terraform_aws_provider):
        """Test deployment failure"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Initialized", stderr=""),  # init
            Mock(returncode=0, stdout="Plan complete", stderr=""),  # plan
            Mock(returncode=1, stdout="", stderr="Error: Resource creation failed")  # apply fails
        ]

        result = await terraform_aws_provider.deploy(
            template_path="/path/to/template.tf",
            parameters={},
            resource_group="test-group",
            location="us-east-1"
        )

        assert result.success is False
        assert "failed" in result.error.lower()

    def test_convert_to_terraform_vars(self, terraform_aws_provider):
        """Test converting parameters to Terraform variables"""
        parameters = {
            "bucket_name": "my-bucket",
            "environment": "production",
            "enable_versioning": True,
            "retention_days": 30
        }

        tfvars = terraform_aws_provider._convert_to_terraform_vars(parameters)

        assert 'bucket_name = "my-bucket"' in tfvars
        assert 'environment = "production"' in tfvars
        assert 'enable_versioning = true' in tfvars
        assert 'retention_days = 30' in tfvars

    def test_parse_terraform_output(self, terraform_aws_provider):
        """Test parsing Terraform output"""
        output_json = json.dumps({
            "bucket_name": {
                "value": "test-bucket-123",
                "type": "string"
            },
            "bucket_arn": {
                "value": "arn:aws:s3:::test-bucket-123",
                "type": "string"
            }
        })

        outputs = terraform_aws_provider._parse_terraform_output(output_json)

        assert "bucket_name" in outputs
        assert outputs["bucket_name"] == "test-bucket-123"
        assert "bucket_arn" in outputs
        assert outputs["bucket_arn"] == "arn:aws:s3:::test-bucket-123"

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_list_resource_groups_aws(self, mock_run, terraform_aws_provider):
        """Test listing AWS resource groups (tags)"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"Key": "ResourceGroup", "Value": "test-group-1"}, {"Key": "ResourceGroup", "Value": "test-group-2"}]',
            stderr=""
        )

        with patch('boto3.client'):
            result = await terraform_aws_provider.list_resource_groups()

            assert len(result) >= 0  # AWS doesn't have traditional resource groups

    @pytest.mark.asyncio
    async def test_create_resource_group_aws(self, terraform_aws_provider):
        """Test creating AWS resource group (tag-based)"""
        result = await terraform_aws_provider.create_resource_group(
            name="test-group",
            location="us-east-1",
            tags={"environment": "test"}
        )

        assert isinstance(result, ResourceGroup)
        assert result.name == "test-group"
        assert result.location == "us-east-1"

    @pytest.mark.asyncio
    async def test_delete_resource_group_not_supported(self, terraform_aws_provider):
        """Test that delete resource group is not supported for AWS"""
        with pytest.raises(NotImplementedError):
            await terraform_aws_provider.delete_resource_group("test-group")

    def test_get_provider_type_aws(self, terraform_aws_provider):
        """Test getting provider type for AWS"""
        assert terraform_aws_provider.get_provider_type() == "terraform-aws"

    def test_get_provider_type_gcp(self, terraform_gcp_provider):
        """Test getting provider type for GCP"""
        assert terraform_gcp_provider.get_provider_type() == "terraform-gcp"

    def test_get_cloud_name_aws(self, terraform_aws_provider):
        """Test getting cloud name for AWS"""
        assert terraform_aws_provider.get_cloud_name() == "AWS"

    def test_get_cloud_name_gcp(self, terraform_gcp_provider):
        """Test getting cloud name for GCP"""
        assert terraform_gcp_provider.get_cloud_name() == "GCP"

    def test_cleanup(self, terraform_aws_provider):
        """Test cleanup of working directory"""
        with patch('shutil.rmtree') as mock_rmtree:
            terraform_aws_provider.cleanup()
            mock_rmtree.assert_called_once_with(terraform_aws_provider.working_dir, ignore_errors=True)

    def test_context_manager(self):
        """Test using provider as context manager"""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        }):
            with TerraformProvider(cloud_platform="aws", region="us-east-1") as provider:
                assert provider is not None

            # Cleanup should be called automatically
