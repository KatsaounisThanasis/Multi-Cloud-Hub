# Cloud Credentials Setup Guide

This guide will help you configure credentials for Azure, AWS, and GCP.

## Quick Start

Run the interactive setup script:

```bash
cd ~/Desktop/Azure-Resource-Manager-Portal-main
./scripts/setup-cloud-credentials.sh
```

Or manually configure credentials following the steps below.

---

## Azure Setup

### Option 1: Service Principal (Recommended for Production)

1. **Login to Azure CLI:**
   ```bash
   az login
   ```

2. **Create a Service Principal:**
   ```bash
   az ad sp create-for-rbac \
     --name "multicloud-api-sp" \
     --role contributor \
     --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
     --sdk-auth
   ```

3. **Copy the output and add to `.env`:**
   ```bash
   AZURE_SUBSCRIPTION_ID=your_subscription_id
   AZURE_TENANT_ID=your_tenant_id
   AZURE_CLIENT_ID=your_client_id
   AZURE_CLIENT_SECRET=your_client_secret
   ```

### Option 2: Azure CLI Authentication

1. **Login to Azure CLI:**
   ```bash
   az login
   ```

2. **No need to update `.env`** - the containers will use your `~/.azure` credentials (already mounted in docker-compose.yml)

---

## GCP Setup

### Step 1: Create Service Account

1. **Set your project:**
   ```bash
   export PROJECT_ID="your-gcp-project-id"
   gcloud config set project $PROJECT_ID
   ```

2. **Create service account:**
   ```bash
   gcloud iam service-accounts create multicloud-api \
       --description="Service account for Multi-Cloud API" \
       --display-name="Multi-Cloud API"
   ```

3. **Grant permissions:**
   ```bash
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:multicloud-api@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/editor"
   ```

4. **Create and download key:**
   ```bash
   gcloud iam service-accounts keys create ~/gcp-service-account.json \
       --iam-account=multicloud-api@${PROJECT_ID}.iam.gserviceaccount.com
   ```

### Step 2: Move Key to Project

```bash
# Create credentials directory
mkdir -p ~/Desktop/Azure-Resource-Manager-Portal-main/credentials

# Move the key file
mv ~/gcp-service-account.json ~/Desktop/Azure-Resource-Manager-Portal-main/credentials/

# Set permissions
chmod 600 ~/Desktop/Azure-Resource-Manager-Portal-main/credentials/gcp-service-account.json
```

### Step 3: Update .env

```bash
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-service-account.json
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_REGION=us-central1
```

---

## AWS Setup

### Option 1: Environment Variables

1. **Create IAM user with programmatic access** in AWS Console

2. **Add to `.env`:**
   ```bash
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_DEFAULT_REGION=us-east-1
   ```

### Option 2: AWS CLI Credentials

1. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

2. **Mount credentials in docker-compose.yml** (already configured):
   ```yaml
   volumes:
     - ~/.aws:/root/.aws:ro
   ```

---

## Verification

After setting up credentials, verify they work:

### 1. Start the services:
```bash
docker compose up -d
```

### 2. Check the logs:
```bash
docker compose logs -f api
```

### 3. Test the API:

**Health check:**
```bash
curl http://localhost:8000/health
```

**List providers:**
```bash
curl http://localhost:8000/providers
```

**Test Azure (Bicep):**
```bash
curl http://localhost:8000/templates/bicep
```

**Test GCP (Terraform):**
```bash
curl http://localhost:8000/templates/terraform-gcp
```

**Test AWS (Terraform):**
```bash
curl http://localhost:8000/templates/terraform-aws
```

---

## Troubleshooting

### Azure: "Subscription not found"
- Make sure you've run `az login` or set up Service Principal correctly
- Verify `AZURE_SUBSCRIPTION_ID` in `.env`

### GCP: "Permission denied"
- Check that `credentials/gcp-service-account.json` exists
- Verify file permissions: `chmod 600 credentials/gcp-service-account.json`
- Check that `GOOGLE_PROJECT_ID` in `.env` matches your GCP project

### AWS: "Invalid credentials"
- Verify your access keys in `.env`
- Check that IAM user has appropriate permissions

### General: "Unable to authenticate"
- Restart containers after updating credentials:
  ```bash
  docker compose down
  docker compose up -d
  ```
- Check logs for specific errors:
  ```bash
  docker compose logs api
  docker compose logs celery-worker
  ```

---

## Security Best Practices

1. **Never commit credentials to git:**
   - `.env` is in `.gitignore`
   - `credentials/` directory is in `.gitignore`

2. **Use different credentials for each environment:**
   - Development: Limited scope service accounts
   - Production: Managed identities or Key Vault

3. **Rotate credentials regularly:**
   - Service Principal secrets
   - Service Account keys
   - Access keys

4. **Use minimal permissions:**
   - Only grant roles needed for your deployments
   - Consider using custom roles with specific permissions

5. **Enable API authentication in production:**
   ```bash
   API_AUTH_ENABLED=true
   API_KEY=your_secure_random_key
   ```

---

## Next Steps

After setting up credentials:

1. ✅ Test basic deployments
2. ✅ Configure Terraform remote state backends
3. ✅ Set up monitoring and logging
4. ✅ Review security settings
5. ✅ Deploy to production environment

See [README.md](../README.md) for usage examples.
