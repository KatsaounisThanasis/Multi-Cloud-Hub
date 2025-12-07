# Quick Start Guide

Get the Multi-Cloud Infrastructure Manager running in 5 minutes.

## Prerequisites

- Docker & Docker Compose
- Azure credentials (Service Principal)
- GCP credentials (Service Account) - optional

## Step 1: Clone the Repository

```bash
git clone https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal.git
cd Azure-Resource-Manager-Portal
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Azure (required)
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# GCP (optional)
GOOGLE_PROJECT_ID=your-project-id
```

## Step 3: Add GCP Credentials (Optional)

Place your GCP service account JSON file at:
```
credentials/gcp-service-account.json
```

## Step 4: Start the Application

```bash
docker compose up -d
```

## Step 5: Access the Application

- **Frontend:** http://localhost:5174
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Verify Installation

Check that all services are running:

```bash
docker compose ps
```

You should see: `api`, `worker`, `frontend`, `db`, `redis`

## Next Steps

- [Credentials Setup](CREDENTIALS_SETUP.md) - Detailed credentials guide
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - How to deploy resources
- [API Reference](API_REFERENCE.md) - Full API documentation
