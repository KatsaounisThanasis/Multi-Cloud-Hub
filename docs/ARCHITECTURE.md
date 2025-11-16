# Multi-Cloud Architecture Documentation

## Overview

This document describes the refactored multi-cloud architecture that eliminates vendor lock-in and enables deployment to Azure, AWS, and GCP through a unified interface.

## Architecture Principles

### 1. Provider Abstraction Layer

The core of the new architecture is the **Provider Abstraction Layer**, which defines a common interface that all cloud providers must implement.

```
┌─────────────────────────────────────────────────┐
│           Frontend (UI)                         │
│   - Provider Selection                          │
│   - Template Management                         │
│   - Deployment Dashboard                        │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTP/REST API
                  │
┌─────────────────▼───────────────────────────────┐
│           FastAPI Backend                       │
│   - API Endpoints                               │
│   - Request Validation                          │
│   - Error Handling                              │
└─────────────────┬───────────────────────────────┘
                  │
                  │ Factory Pattern
                  │
┌─────────────────▼───────────────────────────────┐
│        Provider Factory                         │
│   - Dynamic Provider Selection                  │
│   - Provider Registration                       │
│   - Configuration Management                    │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┐
        │                    │              │
┌───────▼───────┐  ┌────────▼────────┐  ┌──▼─────────┐
│ Azure Native  │  │   Terraform     │  │   Future   │
│   Provider    │  │    Provider     │  │  Providers │
│   (Bicep)     │  │ (Multi-cloud)   │  │            │
└───────┬───────┘  └────────┬────────┘  └────────────┘
        │                   │
        │                   ├───► AWS
        │                   ├───► GCP
        └───► Azure         └───► Azure (via Terraform)
```

## Component Architecture

### Core Components

#### 1. Base Provider Interface (`providers/base.py`)

Defines the contract that all providers must implement:

```python
class CloudProvider(ABC):
    @abstractmethod
    async def deploy(template_path, parameters, resource_group, location)
    @abstractmethod
    async def list_resource_groups()
    @abstractmethod
    async def create_resource_group(name, location, tags)
    @abstractmethod
    async def delete_resource_group(name)
    @abstractmethod
    async def list_resources(resource_group)
    @abstractmethod
    async def validate_template(template_path, parameters)
    @abstractmethod
    def get_supported_locations()
    @abstractmethod
    def get_provider_type()
```

**Key Features:**
- Async/await support for non-blocking operations
- Consistent return types across providers
- Standardized error handling
- Provider-agnostic data models

#### 2. Provider Implementations

**Azure Native Provider** (`providers/azure_native.py`)
- Uses Azure SDK for Python
- Compiles Bicep templates to ARM
- Native Azure integration
- Full feature parity with original implementation

**Terraform Provider** (`providers/terraform_provider.py`)
- Supports Azure, AWS, and GCP
- Converts templates to Terraform configurations
- Uses Terraform CLI for deployments
- Enables true multi-cloud deployment

#### 3. Provider Factory (`providers/factory.py`)

Implements the Factory design pattern for dynamic provider creation:

```python
provider = ProviderFactory.create_provider(
    provider_type="azure",  # or "terraform-aws", "terraform-gcp"
    subscription_id="...",
    region="eastus"
)
```

**Features:**
- Runtime provider selection
- Provider registration system
- Configuration management
- Error handling and validation

### Data Models

#### DeploymentResult
```python
@dataclass
class DeploymentResult:
    deployment_id: str
    status: DeploymentStatus
    resource_group: str
    resources_created: List[str]
    message: str
    outputs: Optional[Dict[str, Any]]
    timestamp: Optional[datetime]
    provider_metadata: Optional[Dict[str, Any]]
```

#### ResourceGroup
```python
@dataclass
class ResourceGroup:
    name: str
    location: str
    tags: Optional[Dict[str, str]]
    resource_count: int
    provider_id: Optional[str]
```

#### CloudResource
```python
@dataclass
class CloudResource:
    id: str
    name: str
    type: str
    location: str
    resource_group: str
    properties: Optional[Dict[str, Any]]
    tags: Optional[Dict[str, str]]
```

## API Architecture

### New Endpoints

#### GET `/providers`
List available cloud providers

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
      "id": "terraform-azure",
      "name": "Azure (Terraform)",
      "description": "Azure deployment using Terraform"
    },
    {
      "id": "terraform-aws",
      "name": "AWS (Terraform)",
      "description": "AWS deployment using Terraform"
    },
    {
      "id": "terraform-gcp",
      "name": "GCP (Terraform)",
      "description": "Google Cloud deployment using Terraform"
    }
  ]
}
```

#### POST `/deploy` (Enhanced)
Deploy with provider selection

Request:
```json
{
  "template_name": "storage-account",
  "parameters": {...},
  "subscription_id": "xxx",
  "resource_group": "my-rg",
  "location": "eastus",
  "provider_type": "azure"  // NEW: provider selection
}
```

### Modified Endpoints

All resource management endpoints now accept a `provider_type` query parameter:

- `GET /resource-groups?provider_type=azure`
- `POST /resource-groups` (with `provider_type` in body)
- `DELETE /resource-groups/{name}?provider_type=terraform-aws`
- `GET /resource-groups/{name}/resources?provider_type=azure`

## Configuration Management

### Environment Variables

The application uses environment variables for configuration:

```bash
# Azure Configuration
AZURE_ENABLED=true
AZURE_SUBSCRIPTION_ID=xxx
AZURE_DEFAULT_REGION=eastus

# Terraform Configuration
TERRAFORM_ENABLED=true
TERRAFORM_DEFAULT_REGION=us-east-1

# AWS (for Terraform)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# GCP (for Terraform)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_PROJECT_ID=xxx
```

### Configuration File (`backend/config.py`)

Centralized configuration management using Pydantic models:

```python
from backend.config import config

# Access configuration
if config.azure.enabled:
    provider = get_provider("azure")
```

## Deployment Flow

### 1. User Selects Provider

```javascript
// Frontend
const provider = "terraform-aws";
deployTemplate(template, parameters, provider);
```

### 2. API Receives Request

```python
# Backend main_v2.py
@app.post("/deploy")
async def deploy_template(request: DeploymentRequest):
    provider = get_provider(
        provider_type=request.provider_type,
        subscription_id=request.subscription_id,
        region=request.location
    )
```

### 3. Provider Executes Deployment

```python
# Provider implementation
result = await provider.deploy(
    template_path=template_path,
    parameters=parameters,
    resource_group=resource_group,
    location=location
)
```

### 4. Standardized Response

```python
return {
    "status": "success",
    "deployment_id": result.deployment_id,
    "message": result.message,
    "provider": request.provider_type
}
```

## Error Handling

### Custom Exceptions

**DeploymentError**
- Raised when deployment operations fail
- Includes provider context and error details

**ProviderConfigurationError**
- Raised when provider configuration is invalid
- Helps debug setup issues

### Error Flow

```python
try:
    result = await provider.deploy(...)
except ProviderConfigurationError as e:
    # Configuration issue (400)
    raise HTTPException(status_code=400, detail=str(e))
except DeploymentError as e:
    # Deployment failure (500)
    raise HTTPException(status_code=500, detail=str(e))
```

## Security Considerations

### 1. Credential Management

**Development:**
- Environment variables via `.env` file
- DefaultAzureCredential for Azure
- AWS credentials file for AWS
- Service account JSON for GCP

**Production:**
- Azure Key Vault
- AWS Secrets Manager
- GCP Secret Manager
- Managed Identities where possible

### 2. Input Validation

All requests validated using Pydantic models:

```python
class DeploymentRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=100)
    resource_group: str = Field(..., min_length=1, max_length=90)
    provider_type: str = Field(default="azure")
```

### 3. CORS Configuration

Configurable via environment:

```python
CORS_ORIGINS=https://yourdomain.com,https://staging.yourdomain.com
```

## Testing Strategy

### Unit Tests

Test individual provider implementations:

```python
def test_azure_provider_deployment():
    provider = AzureNativeProvider(subscription_id="test")
    result = await provider.deploy(...)
    assert result.status == DeploymentStatus.SUCCEEDED
```

### Integration Tests

Test end-to-end deployment flows:

```python
def test_multi_cloud_deployment():
    for provider_type in ["azure", "terraform-aws"]:
        result = deploy_via_api(provider_type, template, params)
        assert result["status"] == "success"
```

### Provider Tests

Each provider has its own test suite:
- `tests/test_azure_provider.py`
- `tests/test_terraform_provider.py`

## Migration Guide

### From v1 to v2

#### Old Code (v1):
```python
# Directly using Azure SDK
resource_client = ResourceManagementClient(credential, subscription_id)
deployment = resource_client.deployments.begin_create_or_update(...)
```

#### New Code (v2):
```python
# Using provider abstraction
provider = get_provider("azure", subscription_id=subscription_id)
result = await provider.deploy(template_path, parameters, rg, location)
```

### Backend Files

- **Keep:** `backend/main.py` (rename to `main_legacy.py` for backup)
- **Use:** `backend/main_v2.py` (rename to `main.py` for production)
- **New:** `backend/providers/` directory

### Frontend Changes

Minimal frontend changes required:
1. Add provider selection dropdown
2. Include `provider_type` in API requests
3. Update UI to show provider-specific information

## Performance Considerations

### Async Operations

All provider methods are async, enabling:
- Non-blocking I/O
- Concurrent deployments
- Better scalability

### Caching

Future enhancement: Cache provider instances and metadata

```python
@lru_cache(maxsize=10)
def get_cached_provider(provider_type, subscription_id):
    return ProviderFactory.create_provider(provider_type, subscription_id)
```

## Future Enhancements

### 1. Additional Providers
- AWS CloudFormation (native)
- GCP Deployment Manager (native)
- Pulumi provider
- Ansible provider

### 2. Template Conversion
- Bicep → Terraform converter
- ARM → CloudFormation converter
- Universal template format

### 3. Multi-Cloud Orchestration
- Deploy to multiple clouds simultaneously
- Cross-cloud resource dependencies
- Unified monitoring and management

### 4. Cost Optimization
- Cost estimation before deployment
- Multi-cloud cost comparison
- Resource optimization suggestions

## Troubleshooting

### Provider Not Found

```
ProviderConfigurationError: Unsupported provider type: 'xxx'
```

**Solution:** Check available providers with `ProviderFactory.get_available_providers()`

### Azure CLI Not Found

```
ProviderConfigurationError: Azure CLI not found
```

**Solution:** Install Azure CLI or add to PATH

### Terraform Not Found

```
ProviderConfigurationError: Terraform is not installed
```

**Solution:** Install Terraform from https://www.terraform.io/downloads

## References

- [Provider Abstraction Pattern](https://refactoring.guru/design-patterns/abstract-factory)
- [Azure SDK Documentation](https://docs.microsoft.com/python/api/overview/azure)
- [Terraform Documentation](https://www.terraform.io/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

## Contributors

Created as part of the multi-cloud refactoring initiative to eliminate vendor lock-in and enable true cloud portability.

---

**Version:** 2.0.0
**Last Updated:** 2025
**Status:** Production Ready
