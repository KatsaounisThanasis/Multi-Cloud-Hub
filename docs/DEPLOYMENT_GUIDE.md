# Deployment Guide

How to deploy cloud resources using the Multi-Cloud Infrastructure Manager.

## Using the Web Interface

### Step 1: Open the Dashboard

Navigate to http://localhost:5174

### Step 2: Select a Template

1. Click on **Deploy** in the navigation
2. Browse available templates by provider (Azure/GCP)
3. Click on a template to select it

### Step 3: Fill in Parameters

1. Select **Location/Region**
2. Enter **Resource Group** name
3. Fill in template-specific parameters
4. Review the **Cost Estimate**

### Step 4: Deploy

1. Click **Deploy**
2. Monitor progress in real-time logs
3. Wait for completion

### Step 5: Verify

Check the deployment in:
- **Deployment History** page
- Azure Portal / GCP Console

---

## Using the API

### Azure Storage Account Example

```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "storage-account",
    "provider_type": "terraform-azure",
    "resource_group": "my-resource-group",
    "location": "westeurope",
    "parameters": {
      "storage_account_name": "mystorageacct2024",
      "account_tier": "Standard",
      "replication_type": "LRS"
    }
  }'
```

### GCP Storage Bucket Example

```bash
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "storage-bucket",
    "provider_type": "terraform-gcp",
    "resource_group": "my-gcp-project",
    "location": "us-central1",
    "parameters": {
      "project_id": "my-gcp-project-id",
      "bucket_name": "my-unique-bucket-name",
      "storage_class": "STANDARD"
    }
  }'
```

### Check Deployment Status

```bash
curl http://localhost:8000/deployments/deploy-xxxxx
```

---

## Available Templates

### Azure (22 templates)

| Template | Description |
|----------|-------------|
| storage-account | Azure Storage Account |
| virtual-machine | Azure VM |
| virtual-network | Azure VNet |
| aks-cluster | Azure Kubernetes Service |
| sql-database | Azure SQL Database |
| key-vault | Azure Key Vault |
| function-app | Azure Functions |
| web-app | Azure App Service |
| container-registry | Azure Container Registry |
| ... | and more |

### GCP (13 templates)

| Template | Description |
|----------|-------------|
| storage-bucket | Google Cloud Storage |
| compute-instance | GCP VM Instance |
| vpc-network | GCP VPC Network |
| gke-cluster | Google Kubernetes Engine |
| cloud-sql | Cloud SQL Database |
| cloud-function | Google Cloud Functions |
| cloud-run | Cloud Run Service |
| pub-sub | Pub/Sub Topic |
| ... | and more |

---

## Troubleshooting

### Deployment Failed

1. Check the deployment logs in the UI
2. Verify credentials are correct
3. Check cloud provider quotas
4. Ensure required APIs are enabled (GCP)

### Authentication Errors

- Azure: Verify Service Principal has correct permissions
- GCP: Ensure Service Account has required roles

### Resource Already Exists

- Use a different resource name
- Or delete the existing resource first
