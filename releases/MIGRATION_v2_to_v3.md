# Migration Guide: v2.0 → v3.0

Quick reference guide for upgrading from v2.0 to v3.0

---

## ⚡ Quick Summary

**Time Required**: 15-30 minutes
**Difficulty**: Moderate
**Breaking Changes**: Yes
**Rollback**: Possible (keep v2.0 backup)

---

## 🎯 What Changed

| Aspect | v2.0 | v3.0 |
|--------|------|------|
| **Clouds** | Azure only | Azure + AWS + GCP |
| **API Endpoint** | `/deploy` | `/api/v1/deploy` |
| **Provider Field** | Not required | **Required** |
| **Template Names** | `storage-account` | Organized by cloud |
| **Environment** | Azure only | Multi-cloud config |

---

## 📋 Pre-Migration Checklist

- [ ] Backup current v2.0 deployment
- [ ] Review API calls in your code
- [ ] Check custom templates
- [ ] Test in development first
- [ ] Update documentation
- [ ] Notify team members

---

## 🔧 Step-by-Step Migration

### Step 1: Backup (5 min)

```bash
# Backup your current v2.0
cd /path/to/project
cp -r . ../project-v2-backup
cd ../project-v2-backup
git tag v2.0-backup
```

### Step 2: Pull v3.0 (2 min)

```bash
cd /path/to/project
git pull origin main
git checkout v3.0  # When released
```

### Step 3: Update Dependencies (5 min)

```bash
# Create new virtual environment (recommended)
python3 -m venv venv-v3
source venv-v3/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Step 4: Update Configuration (5 min)

```bash
# Backup old .env
cp .env .env.v2

# Copy new template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required Changes in .env:**

```bash
# Azure (same as v2.0)
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# NEW: AWS (if using AWS)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# NEW: GCP (if using GCP)
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
```

### Step 5: Update API Calls (10 min)

**Change 1: Endpoint URLs**

```python
# OLD (v2.0)
url = "http://localhost:8000/deploy"

# NEW (v3.0)
url = "http://localhost:8000/api/v1/deploy"
```

**Change 2: Add provider_type**

```python
# OLD (v2.0)
payload = {
    "template": "storage-account",
    "resource_group": "my-rg",
    "location": "eastus",
    "parameters": {...}
}

# NEW (v3.0)
payload = {
    "provider_type": "azure",        # NEW: Required!
    "template_name": "storage-account",  # Renamed
    "subscription_id": "xxx",        # NEW: Required
    "resource_group": "my-rg",
    "location": "eastus",
    "parameters": {...}
}
```

**Change 3: Response Format**

```python
# OLD (v2.0) - Direct response
response = requests.post(url, json=payload)
deployment_id = response.json()["deployment_id"]

# NEW (v3.0) - Standardized format
response = requests.post(url, json=payload)
result = response.json()

if result["success"]:
    deployment_id = result["data"]["deployment_id"]
else:
    error = result["error"]
```

### Step 6: Test (5 min)

```bash
# Run tests
make test

# Test health endpoint
curl http://localhost:8000/health

# Test providers endpoint
curl http://localhost:8000/api/v1/providers

# Test templates endpoint
curl http://localhost:8000/api/v1/templates
```

### Step 7: Deploy (Variable)

```bash
# Option 1: Docker
docker-compose up -d

# Option 2: Local
uvicorn backend.api_rest:app --host 0.0.0.0 --port 8000

# Option 3: Make
make dev
```

---

## 💻 Code Examples

### Example 1: Simple Migration

**Before (v2.0):**
```python
import requests

response = requests.post('http://localhost:8000/deploy', json={
    'template': 'storage-account',
    'resource_group': 'my-rg',
    'location': 'eastus',
    'parameters': {
        'storageAccountName': 'mystorageacct123'
    }
})

if response.status_code == 200:
    print(f"Deployed: {response.json()['deployment_id']}")
```

**After (v3.0):**
```python
import requests

response = requests.post('http://localhost:8000/api/v1/deploy', json={
    'provider_type': 'azure',
    'template_name': 'storage-account',
    'subscription_id': 'your-sub-id',
    'resource_group': 'my-rg',
    'location': 'eastus',
    'parameters': {
        'storageAccountName': 'mystorageacct123'
    }
})

result = response.json()
if result['success']:
    print(f"Deployed: {result['data']['deployment_id']}")
else:
    print(f"Error: {result['error']['message']}")
```

### Example 2: Multi-Cloud Deployments (NEW in v3.0)

```python
# Deploy to AWS
response = requests.post('http://localhost:8000/api/v1/deploy', json={
    'provider_type': 'terraform-aws',
    'template_name': 'storage-bucket',
    'resource_group': 'my-project',
    'location': 'us-east-1',
    'parameters': {
        'bucket_name': 'my-bucket-123'
    }
})

# Deploy to GCP
response = requests.post('http://localhost:8000/api/v1/deploy', json={
    'provider_type': 'terraform-gcp',
    'template_name': 'storage-bucket',
    'project_id': 'my-gcp-project',
    'resource_group': 'my-project',
    'location': 'us-central1',
    'parameters': {
        'bucket_name': 'my-gcs-bucket-123'
    }
})
```

---

## ⚠️ Common Issues

### Issue 1: Missing provider_type

**Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "provider_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Solution:** Add `provider_type` field to all deploy requests.

### Issue 2: 404 on old endpoints

**Error:** `404 Not Found`

**Solution:** Update URLs from `/deploy` to `/api/v1/deploy`.

### Issue 3: Template not found

**Error:**
```json
{
  "success": false,
  "error": {"message": "Template not found"}
}
```

**Solution:**
- Check template name (may have changed)
- Use `/api/v1/templates` to list available templates
- Ensure `provider_type` matches template

### Issue 4: Missing environment variables

**Error:** `Provider configuration error`

**Solution:** Ensure all required environment variables are set:
```bash
# Check current environment
printenv | grep AZURE
printenv | grep AWS
printenv | grep GOOGLE
```

---

## 🔄 Rollback Plan

If you need to rollback to v2.0:

```bash
# Stop v3.0
docker-compose down  # or kill process

# Switch back
git checkout v2.0
source venv/bin/activate  # old venv
pip install -r requirements.txt

# Restore old config
cp .env.v2 .env

# Start v2.0
uvicorn backend.api_rest:app --reload
```

---

## ✅ Verification Checklist

After migration, verify:

- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] Providers list works: `curl http://localhost:8000/api/v1/providers`
- [ ] Templates list works: `curl http://localhost:8000/api/v1/templates`
- [ ] Can deploy Azure resources (existing functionality)
- [ ] All tests pass: `make test`
- [ ] Documentation accessible: `http://localhost:8000/docs`
- [ ] Your application code works with new API
- [ ] No errors in logs

---

## 📞 Getting Help

If you encounter issues:

1. **Check Documentation**: `docs/` folder
2. **Review Examples**: `examples/` folder
3. **Run Tests**: `make test` to verify setup
4. **Check Logs**: Enable DEBUG logging
5. **GitHub Issues**: Report bugs with details
6. **TESTING_GUIDE.md**: Troubleshooting section

---

## 🎓 What to Learn

New features in v3.0 to explore:

1. **Multi-Cloud Deployments**: Try AWS and GCP
2. **Provider Abstraction**: Understand the architecture
3. **Docker Deployment**: Use containers
4. **Testing**: Run comprehensive test suite
5. **CI/CD**: Set up GitHub Actions
6. **Makefile Commands**: Use convenient shortcuts

---

## 📚 Further Reading

- `releases/v3.0-RELEASE-NOTES.md` - Complete release notes
- `docs/ARCHITECTURE.md` - New architecture details
- `docs/API_GUIDE.md` - Full API reference
- `docs/MULTI_CLOUD_GUIDE.md` - Multi-cloud usage
- `docs/TESTING_GUIDE.md` - Testing your setup

---

## ⏱️ Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Backup | 5 min | ✅ |
| Update Code | 2 min | ✅ |
| Dependencies | 5 min | ✅ |
| Configuration | 5 min | ✅ |
| API Updates | 10 min | ⏳ |
| Testing | 5 min | ⏳ |
| Deployment | Variable | ⏳ |

**Total**: ~30 minutes for basic migration

---

**Good luck with your migration!** 🚀

Questions? Open an issue on GitHub.
