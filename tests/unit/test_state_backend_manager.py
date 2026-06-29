"""
Unit tests for backend/services/state_backend_manager.py

Pure logic (no cloud SDK): backend-type selection, state-key generation,
azurerm/gcs/local backend config, dict->HCL rendering, metadata, env-based
credential validation, and the create_backend_config helper.
"""

from backend.services.state_backend_manager import BackendType, StateBackendManager, create_backend_config


class TestInitAndDefaults:
    def test_azure_defaults(self):
        m = StateBackendManager("Azure", "deploy-1")
        assert m.cloud_platform == "azure"
        assert m.region == "eastus"
        assert m.backend_type == BackendType.AZURERM

    def test_gcp_defaults(self):
        m = StateBackendManager("GCP", "deploy-2")
        assert m.cloud_platform == "gcp"
        assert m.region == "us-central1"
        assert m.backend_type == BackendType.GCS

    def test_unknown_platform_falls_back_to_local(self):
        m = StateBackendManager("aws", "deploy-3")
        assert m.backend_type == BackendType.LOCAL
        assert m.region == "eastus"  # default fallback

    def test_explicit_region_preserved(self):
        m = StateBackendManager("azure", "deploy-4", region="westeurope")
        assert m.region == "westeurope"

    def test_state_key_format(self):
        m = StateBackendManager("azure", "deploy-xyz")
        assert m._generate_state_key() == "terraform-states/deploy-xyz/terraform.tfstate"


class TestBucketFromEnv:
    def test_gcp_bucket_from_env(self, monkeypatch):
        monkeypatch.setenv("TERRAFORM_STATE_GCS_BUCKET", "my-gcs-bucket")
        m = StateBackendManager("gcp", "d1")
        assert m._get_bucket_name_from_env() == "my-gcs-bucket"

    def test_azure_storage_from_env(self, monkeypatch):
        monkeypatch.setenv("TERRAFORM_STATE_STORAGE_ACCOUNT", "mystorage")
        m = StateBackendManager("azure", "d1")
        assert m._get_bucket_name_from_env() == "mystorage"

    def test_missing_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("TERRAFORM_STATE_STORAGE_ACCOUNT", raising=False)
        m = StateBackendManager("azure", "d1")
        assert m._get_bucket_name_from_env() is None


class TestAzurermBackend:
    def test_with_storage_account(self):
        m = StateBackendManager("azure", "deploy-1", "eastus")
        cfg = m.generate_backend_config("statestorage")
        az = cfg["terraform"]["backend"]["azurerm"]
        assert az["storage_account_name"] == "statestorage"
        assert az["container_name"] == "terraform-state"
        assert az["key"] == "terraform-states/deploy-1/terraform.tfstate"
        assert az["use_azuread_auth"] is True

    def test_with_resource_group_kwarg(self):
        m = StateBackendManager("azure", "deploy-1")
        cfg = m.generate_backend_config("statestorage", resource_group="rg-state")
        az = cfg["terraform"]["backend"]["azurerm"]
        assert az["resource_group_name"] == "rg-state"

    def test_without_storage_falls_back_to_local(self, monkeypatch):
        monkeypatch.delenv("TERRAFORM_STATE_STORAGE_ACCOUNT", raising=False)
        m = StateBackendManager("azure", "deploy-1")
        cfg = m.generate_backend_config()
        assert "local" in cfg["terraform"]["backend"]


class TestGcsBackend:
    def test_with_bucket(self):
        m = StateBackendManager("gcp", "deploy-9")
        cfg = m.generate_backend_config("my-bucket")
        gcs = cfg["terraform"]["backend"]["gcs"]
        assert gcs["bucket"] == "my-bucket"
        assert gcs["prefix"] == "terraform-state/deploy-9"

    def test_without_bucket_falls_back_to_local(self, monkeypatch):
        monkeypatch.delenv("TERRAFORM_STATE_GCS_BUCKET", raising=False)
        m = StateBackendManager("gcp", "deploy-9")
        cfg = m.generate_backend_config()
        assert "local" in cfg["terraform"]["backend"]


class TestLocalBackend:
    def test_local_path(self):
        m = StateBackendManager("aws", "deploy-loc")
        cfg = m.generate_backend_config()
        path = cfg["terraform"]["backend"]["local"]["path"]
        assert path == "./terraform-states/deploy-loc/terraform.tfstate"


class TestHclRendering:
    def test_renders_nested_blocks_and_types(self):
        m = StateBackendManager("azure", "deploy-1")
        hcl = m.generate_backend_tf_content("statestorage")
        assert "terraform {" in hcl
        assert "backend {" in hcl
        assert "azurerm {" in hcl
        # string quoting
        assert 'storage_account_name = "statestorage"' in hcl
        # bool lowercased and unquoted
        assert "use_azuread_auth = true" in hcl
        # balanced braces
        assert hcl.count("{") == hcl.count("}")

    def test_dict_to_hcl_handles_numbers_and_none(self):
        m = StateBackendManager("azure", "deploy-1")
        out = m._dict_to_hcl({"count": 3, "ratio": 1.5, "skip": None, "name": "x"})
        assert "count = 3" in out
        assert "ratio = 1.5" in out
        assert 'name = "x"' in out
        assert "skip" not in out  # None is omitted


class TestMetadata:
    def test_metadata_fields(self):
        m = StateBackendManager("gcp", "deploy-7", "europe-west1")
        meta = m.get_backend_metadata()
        assert meta["backend_type"] == "gcs"
        assert meta["deployment_id"] == "deploy-7"
        assert meta["cloud_platform"] == "gcp"
        assert meta["region"] == "europe-west1"
        assert meta["state_key"] == "terraform-states/deploy-7/terraform.tfstate"


class TestValidateRequirements:
    def test_azure_with_credentials(self, monkeypatch):
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub")
        monkeypatch.setenv("AZURE_CLIENT_ID", "cid")
        monkeypatch.setenv("TERRAFORM_STATE_STORAGE_ACCOUNT", "store")
        res = StateBackendManager.validate_backend_requirements("azure")
        assert res["has_credentials"] is True
        assert res["has_storage_config"] is True

    def test_gcp_without_credentials(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_CREDENTIALS", raising=False)
        monkeypatch.delenv("TERRAFORM_STATE_GCS_BUCKET", raising=False)
        res = StateBackendManager.validate_backend_requirements("gcp")
        assert res["has_credentials"] is False
        assert res["has_bucket_config"] is False

    def test_unknown_platform_returns_empty(self):
        assert StateBackendManager.validate_backend_requirements("aws") == {}


class TestCreateBackendConfigHelper:
    def test_helper_builds_azure_config(self):
        cfg = create_backend_config("azure", "deploy-1", "eastus", "statestorage")
        assert cfg["terraform"]["backend"]["azurerm"]["storage_account_name"] == "statestorage"

    def test_helper_builds_gcs_config(self):
        cfg = create_backend_config("gcp", "deploy-2", "us-central1", "bucket-x")
        assert cfg["terraform"]["backend"]["gcs"]["bucket"] == "bucket-x"
