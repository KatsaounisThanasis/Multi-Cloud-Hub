

# REST API Guide - Multi-Cloud Infrastructure Management

## Overview

Production-ready REST API for deploying and managing cloud infrastructure across **Azure**, **AWS**, and **Google Cloud Platform** with a unified interface.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Client Libraries](#client-libraries)

## Quick Start

### 1. Start the API Server

```bash
cd backend
uvicorn api_rest:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verify API is Running

```bash
curl http://localhost:8000/health
```

### 3. Explore Interactive Documentation

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

Currently uses **cloud provider credentials**:

- **Azure**: Requires `az login`
- **AWS**: Requires AWS credentials (`~/.aws/credentials` or environment variables)
- **GCP**: Requires gcloud auth or service account JSON

### Future: API Key Authentication

```bash
# Coming soon
curl -H "X-API-Key: your-api-key" http://localhost:8000/deploy
```

## Base URL

```
http://localhost:8000
```

For production, use your deployed API URL.

## Response Format

All responses follow a standardized format:

### Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  },
  "error": null,
  "timestamp": "2025-01-06T12:34:56.789Z"
}
```

### Error Response

```json
{
  "success": false,
  "message": "Operation failed",
  "data": null,
  "error": {
    "details": "Error description",
    "status_code": 400
  },
  "timestamp": "2025-01-06T12:34:56.789Z"
}
```

## API Endpoints

### Health & Info

#### GET `/` - API Info
Returns API information and health status.

**Response:**
```json
{
  "success": true,
  "message": "Multi-Cloud Infrastructure Management API is running",
  "data": {
    "version": "2.0.0",
    "status": "healthy",
    "available_providers": ["azure", "terraform", "terraform-azure", ...]
  }
}
```

#### GET `/health` - Detailed Health Check
Returns detailed health information including provider and template counts.

---

### Providers

#### GET `/providers` - List Cloud Providers
Returns information about available cloud providers.

**Response:**
```json
{
  "success": true,
  "message": "Found 4 providers",
  "data": {
    "providers": [
      {
        "id": "azure",
        "name": "Azure (Bicep)",
        "format": "bicep",
        "cloud": "azure",
        "template_count": 15
      },
      {
        "id": "terraform-aws",
        "name": "AWS (Terraform)",
        "format": "terraform",
        "cloud": "aws",
        "template_count": 3
      }
    ],
    "total_templates": 21
  }
}
```

---

### Templates

#### GET `/templates` - List Templates
List available deployment templates.

**Query Parameters:**
- `provider_type` (optional): Filter by provider (e.g., `terraform-aws`)
- `cloud` (optional): Filter by cloud (e.g., `aws`)

**Examples:**
```bash
# All templates
curl http://localhost:8000/templates

# AWS templates only
curl http://localhost:8000/templates?cloud=aws

# Terraform AWS templates
curl http://localhost:8000/templates?provider_type=terraform-aws
```

**Response:**
```json
{
  "success": true,
  "message": "Found 3 templates",
  "data": {
    "templates": [
      {
        "name": "storage-bucket",
        "display_name": "Storage Bucket",
        "format": "terraform",
        "cloud_provider": "aws",
        "path": "/path/to/template.tf",
        "description": "AWS S3 Bucket",
        "icon": "hdd-stack"
      }
    ],
    "count": 3
  }
}
```

#### GET `/templates/{provider_type}/{template_name}` - Get Template Details
Get detailed information about a specific template.

**Example:**
```bash
curl http://localhost:8000/templates/terraform-aws/storage-bucket
```

#### GET `/templates/{provider_type}/{template_name}/content` - Get Template Content
Get the raw content of a template file.

**Example:**
```bash
curl http://localhost:8000/templates/terraform-aws/storage-bucket/content
```

---

### Deployments

#### POST `/deploy` - Deploy Infrastructure
Deploy infrastructure using the specified template.

**Request Body:**
```json
{
  "template_name": "storage-bucket",
  "provider_type": "terraform-aws",
  "subscription_id": "123456789012",
  "resource_group": "my-resources",
  "location": "us-east-1",
  "parameters": {
    "bucket_name": "my-unique-bucket-name",
    "enable_versioning": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Deployment initiated successfully",
  "data": {
    "deployment_id": "terraform-my-resources-20250106123456",
    "status": "succeeded",
    "resource_group": "my-resources",
    "provider": "terraform-aws",
    "message": "Terraform deployment completed successfully",
    "outputs": {
      "bucket_arn": "arn:aws:s3:::my-unique-bucket-name"
    }
  }
}
```

**Examples:**

**Deploy to AWS:**
```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "storage-bucket",
    "provider_type": "terraform-aws",
    "subscription_id": "123456789012",
    "resource_group": "my-app",
    "location": "us-east-1",
    "parameters": {
      "bucket_name": "my-test-bucket-xyz"
    }
  }'
```

**Deploy to GCP:**
```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "storage-bucket",
    "provider_type": "terraform-gcp",
    "subscription_id": "my-gcp-project",
    "resource_group": "my-resources",
    "location": "us-central1",
    "parameters": {
      "bucket_name": "my-gcp-bucket"
    }
  }'
```

**Deploy to Azure:**
```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Storage Account",
    "provider_type": "azure",
    "subscription_id": "azure-sub-id",
    "resource_group": "my-rg",
    "location": "eastus",
    "parameters": {
      "storageAccountName": "mystorageacct123"
    }
  }'
```

#### GET `/deployments/{deployment_id}/status` - Get Deployment Status
Check the status of a deployment.

**Query Parameters:**
- `provider_type`: Provider type
- `subscription_id`: Subscription/account ID
- `resource_group`: Resource group name

**Example:**
```bash
curl "http://localhost:8000/deployments/deployment-123/status?provider_type=azure&subscription_id=sub-123&resource_group=my-rg"
```

---

### Resource Groups

#### GET `/resource-groups` - List Resource Groups
List all resource groups/stacks.

**Query Parameters:**
- `provider_type`: Provider type (default: `azure`)
- `subscription_id`: Subscription/account ID (required)

**Example:**
```bash
curl "http://localhost:8000/resource-groups?provider_type=azure&subscription_id=your-sub-id"
```

**Response:**
```json
{
  "success": true,
  "message": "Found 5 resource groups",
  "data": {
    "resource_groups": [
      {
        "name": "my-app-rg",
        "location": "eastus",
        "resource_count": 10,
        "tags": {
          "Environment": "Production"
        }
      }
    ],
    "count": 5
  }
}
```

#### POST `/resource-groups` - Create Resource Group
Create a new resource group/stack.

**Request Body:**
```json
{
  "name": "my-new-rg",
  "location": "eastus",
  "subscription_id": "your-subscription-id",
  "provider_type": "azure",
  "tags": {
    "Environment": "Development",
    "Project": "MyApp"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/resource-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-rg",
    "location": "eastus",
    "subscription_id": "sub-123",
    "provider_type": "azure"
  }'
```

#### DELETE `/resource-groups/{resource_group_name}` - Delete Resource Group
Delete a resource group and all its resources.

**⚠️ Warning**: This is a destructive operation!

**Query Parameters:**
- `provider_type`: Provider type
- `subscription_id`: Subscription/account ID

**Example:**
```bash
curl -X DELETE "http://localhost:8000/resource-groups/test-rg?provider_type=azure&subscription_id=sub-123"
```

#### GET `/resource-groups/{resource_group_name}/resources` - List Resources
List all resources within a resource group.

**Example:**
```bash
curl "http://localhost:8000/resource-groups/my-rg/resources?provider_type=azure&subscription_id=sub-123"
```

---

## Usage Examples

### Python Client

See [examples/api_client_python.py](examples/api_client_python.py)

```python
from api_client_python import MultiCloudClient

client = MultiCloudClient()

# List providers
providers = client.list_providers()

# Deploy to AWS
result = client.deploy(
    template_name="storage-bucket",
    provider_type="terraform-aws",
    subscription_id="123456789012",
    resource_group="my-resources",
    location="us-east-1",
    parameters={"bucket_name": "my-bucket"}
)

print(f"Deployment ID: {result['data']['deployment_id']}")
```

### cURL Examples

See [examples/api_examples_curl.sh](examples/api_examples_curl.sh)

```bash
chmod +x examples/api_examples_curl.sh
./examples/api_examples_curl.sh
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_BASE = 'http://localhost:8000';

async function listProviders() {
  const response = await axios.get(`${API_BASE}/providers`);
  console.log(response.data);
}

async function deploy() {
  const response = await axios.post(`${API_BASE}/deploy`, {
    template_name: 'storage-bucket',
    provider_type: 'terraform-aws',
    subscription_id: '123456789012',
    resource_group: 'my-resources',
    location: 'us-east-1',
    parameters: {
      bucket_name: 'my-unique-bucket'
    }
  });

  console.log('Deployment ID:', response.data.data.deployment_id);
}

listProviders();
```

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation initiated) |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (template/resource not found) |
| 500 | Internal Server Error |

### Error Response Example

```json
{
  "success": false,
  "message": "Deployment failed",
  "error": {
    "details": "Template 'invalid-template' not found for provider 'terraform-aws'",
    "status_code": 404
  },
  "timestamp": "2025-01-06T12:34:56.789Z"
}
```

### Common Errors

**Template Not Found:**
```json
{
  "success": false,
  "message": "Template 'storage' not found for provider 'terraform-aws'",
  "error": {
    "status_code": 404
  }
}
```

**Provider Configuration Error:**
```json
{
  "success": false,
  "message": "Provider configuration error",
  "error": {
    "details": "Terraform is not installed",
    "status_code": 400
  }
}
```

**Deployment Error:**
```json
{
  "success": false,
  "message": "Deployment failed",
  "error": {
    "details": "Bucket name already exists",
    "status_code": 500
  }
}
```

---

## Rate Limiting

Currently **no rate limiting** is enforced.

For production deployment, consider adding:
- **Rate limiting** (e.g., 100 requests/minute per IP)
- **API keys** for authentication
- **Request throttling** for expensive operations

---

## Client Libraries

### Python

```bash
pip install requests

# Use the provided client
python examples/api_client_python.py
```

### JavaScript/TypeScript

```bash
npm install axios

# Use axios or fetch API
```

### Go

```go
import "net/http"

resp, err := http.Get("http://localhost:8000/providers")
```

---

## Interactive Documentation

### Swagger UI

Visit http://localhost:8000/docs for interactive API exploration:
- Test endpoints directly from browser
- See request/response schemas
- Try different parameters

### ReDoc

Visit http://localhost:8000/redoc for beautiful API documentation:
- Organized by tags
- Clear descriptions
- Code examples

---

## Multi-Cloud Workflow

### Typical Workflow

```
1. List providers
   GET /providers

2. Choose cloud (e.g., AWS)
   Filter: provider_type=terraform-aws

3. List available templates
   GET /templates?provider_type=terraform-aws

4. Get template details
   GET /templates/terraform-aws/storage-bucket

5. Deploy infrastructure
   POST /deploy
   {
     "template_name": "storage-bucket",
     "provider_type": "terraform-aws",
     ...
   }

6. Check deployment status
   GET /deployments/{id}/status

7. List created resources
   GET /resource-groups/{name}/resources
```

---

## Production Deployment

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Cloud Credentials
AZURE_SUBSCRIPTION_ID=xxx
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY templates/ ./templates/

CMD ["uvicorn", "backend.api_rest:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multi-cloud-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: multi-cloud-api:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_SUBSCRIPTION_ID
          valueFrom:
            secretKeyRef:
              name: cloud-credentials
              key: azure-subscription-id
```

---

## Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal/issues)
- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Examples**: See [examples/](examples/) directory

---

## What's Next

### Upcoming Features

- [ ] API Key Authentication
- [ ] Rate Limiting
- [ ] Webhook Support for deployment events
- [ ] Cost Estimation API
- [ ] Template Validation API
- [ ] Bulk Operations

### Contributing

Contributions welcome! See the main [README.md](README.md) for guidelines.

---

**API Version**: 2.0.0
**Last Updated**: 2025
**Status**: Production Ready
