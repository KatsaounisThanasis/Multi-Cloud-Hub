# Multi-Cloud Deployment Guide

## Quick Start

This guide explains how to use the new multi-cloud capabilities of the Azure Resource Manager Portal.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Provider Selection](#provider-selection)
4. [Deployment Examples](#deployment-examples)
5. [API Usage](#api-usage)
6. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

**For Azure Native:**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login
```

**For Terraform (Multi-cloud):**
```bash
# Install Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### Install Dependencies

```bash
# Update requirements.txt first
pip install -r requirements.txt

# Install provider-specific dependencies
pip install azure-identity azure-mgmt-resource azure-mgmt-compute
```

### Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```bash
# Azure
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id

# AWS (optional, for Terraform)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# GCP (optional, for Terraform)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Configuration

### Enabling/Disabling Providers

Edit `.env`:

```bash
# Enable/disable providers
AZURE_ENABLED=true
TERRAFORM_ENABLED=true

# Default regions
AZURE_DEFAULT_REGION=eastus
TERRAFORM_DEFAULT_REGION=us-east-1
```

### Provider Configuration

Each provider can be configured independently:

```python
# backend/config.py
from backend.config import config

# Check if provider is enabled
if config.azure.enabled:
    print(f"Azure enabled with default region: {config.azure.default_region}")
```

## Provider Selection

### Available Providers

| Provider ID | Description | Requirements |
|------------|-------------|--------------|
| `azure` | Azure Bicep (Native) | Azure CLI + Azure SDK |
| `terraform-azure` | Azure via Terraform | Terraform + Azure credentials |
| `terraform-aws` | AWS via Terraform | Terraform + AWS credentials |
| `terraform-gcp` | GCP via Terraform | Terraform + GCP credentials |

### How to Choose

**Use Azure Native (`azure`) when:**
- ✅ Deploying only to Azure
- ✅ Want native Bicep support
- ✅ Need all Azure-specific features
- ✅ Maximum performance on Azure

**Use Terraform (`terraform-*`) when:**
- ✅ Need multi-cloud support
- ✅ Want infrastructure as code portability
- ✅ Deploying to AWS or GCP
- ✅ Managing cross-cloud resources

## Deployment Examples

### Example 1: Deploy to Azure (Native)

```python
from providers import get_provider

# Create Azure provider
provider = get_provider(
    provider_type="azure",
    subscription_id="your-subscription-id",
    region="eastus"
)

# Deploy Bicep template
result = await provider.deploy(
    template_path="templates/Storage Account.bicep",
    parameters={
        "storageAccountName": "mystorageacct123",
        "skuName": "Standard_LRS"
    },
    resource_group="my-resource-group",
    location="eastus"
)

print(f"Deployment ID: {result.deployment_id}")
print(f"Status: {result.status}")
```

### Example 2: Deploy to AWS (Terraform)

```python
# Create Terraform provider for AWS
provider = get_provider(
    provider_type="terraform-aws",
    subscription_id="aws-account-id",  # AWS account ID
    region="us-east-1",
    cloud_platform="aws"  # Specify cloud platform
)

# Deploy
result = await provider.deploy(
    template_path="templates/s3-bucket.tf",  # Terraform template
    parameters={
        "bucket_name": "my-unique-bucket-name",
        "environment": "production"
    },
    resource_group="my-stack",  # CloudFormation stack name
    location="us-east-1"
)
```

### Example 3: Deploy to GCP (Terraform)

```python
# Create Terraform provider for GCP
provider = get_provider(
    provider_type="terraform-gcp",
    subscription_id="gcp-project-id",
    region="us-central1",
    cloud_platform="gcp"
)

# Deploy
result = await provider.deploy(
    template_path="templates/gcs-bucket.tf",
    parameters={
        "bucket_name": "my-gcp-bucket",
        "location": "US"
    },
    resource_group="my-resources",
    location="us-central1"
)
```

## API Usage

### List Available Providers

```bash
curl http://localhost:8000/providers
```

Response:
```json
{
  "providers": [
    {
      "id": "azure",
      "name": "Azure (Bicep)",
      "description": "Native Azure deployment using Bicep templates"
    },
    {
      "id": "terraform-aws",
      "name": "AWS (Terraform)",
      "description": "AWS deployment using Terraform"
    }
  ]
}
```

### Deploy with Provider Selection

```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Storage Account",
    "parameters": {
      "storageAccountName": "mystorageacct123"
    },
    "subscription_id": "your-subscription-id",
    "resource_group": "my-rg",
    "location": "eastus",
    "provider_type": "azure"
  }'
```

### List Resource Groups (Any Provider)

```bash
# Azure
curl "http://localhost:8000/resource-groups?provider_type=azure&subscription_id=xxx"

# AWS (via Terraform)
curl "http://localhost:8000/resource-groups?provider_type=terraform-aws&subscription_id=xxx"
```

### Create Resource Group

```bash
curl -X POST http://localhost:8000/resource-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-new-rg",
    "location": "eastus",
    "subscription_id": "your-subscription-id",
    "provider_type": "azure"
  }'
```

## Frontend Integration

### Add Provider Selector to UI

Update `frontend/index.html`:

```html
<div class="mb-3">
    <label for="providerType" class="form-label">Cloud Provider</label>
    <select class="form-select" id="providerType" name="providerType">
        <option value="azure">Azure (Native Bicep)</option>
        <option value="terraform-azure">Azure (Terraform)</option>
        <option value="terraform-aws">AWS (Terraform)</option>
        <option value="terraform-gcp">GCP (Terraform)</option>
    </select>
</div>
```

### Update JavaScript

```javascript
// frontend/js/deployments.js

async function deployTemplate() {
    const providerType = document.getElementById('providerType').value;

    const payload = {
        template_name: selectedTemplate,
        parameters: collectParameters(),
        subscription_id: document.getElementById('subscription').value,
        resource_group: document.getElementById('resourceGroup').value,
        location: document.getElementById('location').value,
        provider_type: providerType  // NEW: Include provider type
    };

    const response = await fetch('/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const result = await response.json();
    console.log(`Deployed using ${providerType}:`, result);
}
```

## Template Format Support

### Bicep Templates (Azure Native)

```bicep
// templates/Storage Account.bicep
param storageAccountName string
param skuName string = 'Standard_LRS'

resource storageAccount 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: storageAccountName
  location: resourceGroup().location
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
}
```

### Terraform Templates (Multi-cloud)

**Azure:**
```hcl
// templates/azure-storage.tf
variable "storage_account_name" {}
variable "location" { default = "eastus" }

resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
```

**AWS:**
```hcl
// templates/aws-s3.tf
variable "bucket_name" {}

resource "aws_s3_bucket" "main" {
  bucket = var.bucket_name

  tags = {
    Name        = var.bucket_name
    Environment = "Production"
  }
}
```

**GCP:**
```hcl
// templates/gcp-storage.tf
variable "bucket_name" {}

resource "google_storage_bucket" "main" {
  name          = var.bucket_name
  location      = "US"
  force_destroy = true
}
```

## Advanced Usage

### Custom Provider Registration

You can register custom providers:

```python
from providers import ProviderFactory
from my_custom_provider import MyCloudProvider

# Register custom provider
ProviderFactory.register_provider("mycloud", MyCloudProvider)

# Use it
provider = get_provider("mycloud", subscription_id="xxx")
```

### Provider Capabilities Check

```python
provider = get_provider("azure", subscription_id="xxx")

# Check supported locations
locations = provider.get_supported_locations()
print(f"Supported locations: {locations}")

# Get provider type
provider_type = provider.get_provider_type()
print(f"Provider type: {provider_type.value}")
```

### Validate Before Deploy

```python
# Validate template before deploying
is_valid, error_message = await provider.validate_template(
    template_path="templates/Storage Account.bicep",
    parameters={"storageAccountName": "test"}
)

if is_valid:
    result = await provider.deploy(...)
else:
    print(f"Validation failed: {error_message}")
```

## Troubleshooting

### Issue: Provider Not Found

**Error:**
```
ProviderConfigurationError: Unsupported provider type: 'xxx'
```

**Solution:**
```python
from providers import ProviderFactory

# Check available providers
print(ProviderFactory.get_available_providers())

# Verify provider is enabled in .env
AZURE_ENABLED=true
```

### Issue: Azure CLI Not Found

**Error:**
```
ProviderConfigurationError: Azure CLI not found
```

**Solution:**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version

# Login
az login
```

### Issue: Terraform Not Installed

**Error:**
```
ProviderConfigurationError: Terraform is not installed
```

**Solution:**
```bash
# Install Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform version
```

### Issue: Credentials Not Found

**Error:**
```
DefaultAzureCredentialError: No credential available
```

**Solution:**
```bash
# Option 1: Login with Azure CLI
az login

# Option 2: Set environment variables
export AZURE_TENANT_ID="xxx"
export AZURE_CLIENT_ID="xxx"
export AZURE_CLIENT_SECRET="xxx"

# Option 3: Use managed identity (in Azure)
# No action needed - automatically detected
```

### Issue: Deployment Failed

**Check logs:**
```bash
# View backend logs
tail -f logs/backend.log

# View deployment logs
tail -f logs/deployments.log
```

**Debug mode:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### 1. Provider Selection

- Use **Azure Native** for pure Azure workloads
- Use **Terraform** for multi-cloud or hybrid scenarios
- Consider migration path when choosing

### 2. Template Organization

```
templates/
├── azure/
│   ├── bicep/
│   └── arm/
├── terraform/
│   ├── azure/
│   ├── aws/
│   └── gcp/
└── shared/
```

### 3. Configuration Management

- Use environment variables for credentials
- Never commit `.env` files
- Use Key Vault in production
- Rotate credentials regularly

### 4. Error Handling

```python
try:
    result = await provider.deploy(...)
except ProviderConfigurationError as e:
    # Configuration issue - fix and retry
    logger.error(f"Config error: {e}")
except DeploymentError as e:
    # Deployment failed - check template
    logger.error(f"Deployment error: {e}")
except Exception as e:
    # Unexpected error
    logger.exception("Unexpected error")
```

### 5. Testing

```python
# Test with all providers
providers = ["azure", "terraform-aws", "terraform-gcp"]

for provider_type in providers:
    if ProviderFactory.is_provider_available(provider_type):
        provider = get_provider(provider_type, ...)
        result = await provider.deploy(...)
        assert result.status == DeploymentStatus.SUCCEEDED
```

## Migration from v1

### Step 1: Update Backend

```bash
# Backup old main.py
cp backend/main.py backend/main_legacy.py

# Use new main.py
cp backend/main_v2.py backend/main.py
```

### Step 2: Update Requirements

```bash
pip install -r requirements.txt
```

### Step 3: Update Configuration

```bash
cp .env.example .env
# Edit .env with your settings
```

### Step 4: Test

```bash
# Start backend
cd backend
uvicorn main:app --reload

# Test provider list
curl http://localhost:8000/providers

# Test deployment
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d @test_deployment.json
```

## Next Steps

- **Add UI for Provider Selection** - Update frontend with provider dropdown
- **Create Terraform Templates** - Convert existing Bicep to Terraform
- **Set up CI/CD** - Automate multi-cloud deployments
- **Enable Monitoring** - Track deployments across providers

## Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Provider API Reference](backend/providers/base.py)
- [Configuration Guide](backend/config.py)
- [GitHub Repository](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal)

---

**Need Help?**

Open an issue on GitHub or check the troubleshooting section above.
