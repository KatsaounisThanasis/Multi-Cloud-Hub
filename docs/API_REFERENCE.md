# API Reference

Base URL: `http://localhost:8000`

## Health & Status

### GET /health
Check system health status.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "success": true,
  "message": "System healthy",
  "data": {
    "api_version": "3.0.0",
    "status": "healthy",
    "providers": {...},
    "database": {"status": "connected"},
    "celery": {"status": "connected", "workers": 1}
  }
}
```

## Templates

### GET /templates
List all available templates.

```bash
curl http://localhost:8000/templates
```

### GET /templates/{provider}/{template_name}
Get template details.

```bash
curl http://localhost:8000/templates/terraform-azure/storage-account
curl http://localhost:8000/templates/terraform-gcp/storage-bucket
```

## Deployments

### POST /deploy
Create a new deployment.

```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "storage-account",
    "provider_type": "terraform-azure",
    "resource_group": "my-resources",
    "location": "westeurope",
    "parameters": {
      "storage_account_name": "mystorageaccount"
    }
  }'
```

### GET /deployments
List all deployments.

```bash
curl http://localhost:8000/deployments
```

### GET /deployments/{deployment_id}
Get deployment status and details.

```bash
curl http://localhost:8000/deployments/deploy-abc123
```

## Cloud Resources

### Azure

#### GET /azure/locations
Get available Azure locations.

```bash
curl http://localhost:8000/azure/locations
```

#### GET /azure/skus
Get available VM SKUs for a location.

```bash
curl "http://localhost:8000/azure/skus?location=westeurope"
```

### GCP

#### GET /gcp/regions
Get available GCP regions.

```bash
curl http://localhost:8000/gcp/regions
```

#### GET /gcp/zones
Get available GCP zones.

```bash
curl "http://localhost:8000/gcp/zones?region=us-central1"
```

#### GET /gcp/machine-types
Get available machine types.

```bash
curl "http://localhost:8000/gcp/machine-types?zone=us-central1-a"
```

## Cost Estimation

### POST /templates/{provider}/{template}/estimate-cost
Get cost estimate before deployment.

```bash
curl -X POST http://localhost:8000/templates/terraform-azure/storage-account/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{
    "location": "westeurope",
    "parameters": {
      "storage_account_name": "test",
      "account_tier": "Standard"
    }
  }'
```

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "message": "Error description",
  "error": {
    "code": "ERROR_CODE",
    "details": "Detailed error message"
  }
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
