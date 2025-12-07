# Credentials Setup Guide

## Azure Service Principal

### Step 1: Create Service Principal

```bash
az login
az ad sp create-for-rbac --name "multicloud-manager" --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
```

Output:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "multicloud-manager",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Step 2: Update .env File

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_CLIENT_ID=appId-from-above
AZURE_CLIENT_SECRET=password-from-above
AZURE_TENANT_ID=tenant-from-above
```

### Step 3: Verify

```bash
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID
```

---

## GCP Service Account

### Step 1: Create Service Account

1. Go to [GCP Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **Create Service Account**
3. Name: `multicloud-api`
4. Click **Create and Continue**

### Step 2: Assign Roles

Add these roles:
- **Editor** (for full access)
- Or specific roles:
  - Storage Admin
  - Compute Admin
  - etc.

### Step 3: Create Key

1. Click on the service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON**
5. Download the file

### Step 4: Add to Project

Save the JSON file as:
```
credentials/gcp-service-account.json
```

### Step 5: Update .env

```env
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-service-account.json
```

### Step 6: Enable APIs (if needed)

Enable these APIs in GCP Console:
- [Compute Engine API](https://console.cloud.google.com/apis/library/compute.googleapis.com)
- [Cloud Storage API](https://console.cloud.google.com/apis/library/storage.googleapis.com)

---

## Security Notes

- Never commit credentials to git
- Use `.gitignore` for credentials folder
- Rotate credentials regularly
- Use minimum required permissions
