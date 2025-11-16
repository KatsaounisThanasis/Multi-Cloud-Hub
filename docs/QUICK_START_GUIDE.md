# Quick Start Guide - Multi-Cloud Setup

## 🚀 Get Started in 5 Minutes

This guide will help you quickly set up and test the new multi-cloud capabilities.

## Prerequisites Check

```bash
# Check Python version (need 3.8+)
python --version

# Check Azure CLI (for Azure provider)
az --version

# Check Terraform (for multi-cloud)
terraform --version
```

If anything is missing:
- **Python**: https://www.python.org/downloads/
- **Azure CLI**: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
- **Terraform**: https://www.terraform.io/downloads

## Step 1: Install Dependencies (2 minutes)

```bash
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment (1 minute)

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env  # or use any text editor
```

**Minimum configuration for Azure:**
```bash
AZURE_ENABLED=true
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_DEFAULT_REGION=eastus
```

**Optional - for AWS/GCP:**
```bash
TERRAFORM_ENABLED=true
AWS_ACCESS_KEY_ID=your-aws-key
GOOGLE_PROJECT_ID=your-gcp-project
```

## Step 3: Start the Application (30 seconds)

```bash
cd backend

# Use the new v2 API with provider abstraction
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
```

Or rename to use as default:
```bash
# Backup original
cp main.py main_legacy.py

# Use v2 as main
cp main_v2.py main.py

# Start
uvicorn main:app --reload
```

## Step 4: Test the API (1 minute)

Open another terminal and test:

```bash
# Check health
curl http://localhost:8000/health

# List available providers
curl http://localhost:8000/providers

# Expected response:
# {
#   "providers": [
#     {"id": "azure", "name": "Azure (Bicep)", ...},
#     {"id": "terraform-aws", "name": "AWS (Terraform)", ...},
#     ...
#   ]
# }
```

## Step 5: Test Provider System

### Test in Python

Create `test_multi_cloud.py`:

```python
import asyncio
from backend.providers import get_provider, ProviderFactory

async def test_providers():
    # List available providers
    providers = ProviderFactory.get_available_providers()
    print(f"Available providers: {providers}")

    # Test Azure provider
    try:
        azure = get_provider("azure", subscription_id="test")
        locations = azure.get_supported_locations()
        print(f"Azure locations: {locations[:5]}...")
    except Exception as e:
        print(f"Azure provider: {e}")

    # Test Terraform provider
    try:
        terraform = get_provider("terraform-aws", subscription_id="test")
        locations = terraform.get_supported_locations()
        print(f"AWS locations: {locations}")
    except Exception as e:
        print(f"Terraform provider: {e}")

if __name__ == "__main__":
    asyncio.run(test_providers())
```

Run it:
```bash
python test_multi_cloud.py
```

### Test via API

```bash
# Test deployment to Azure
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Storage Account",
    "parameters": {
      "storageAccountName": "teststorage123"
    },
    "subscription_id": "your-subscription-id",
    "resource_group": "test-rg",
    "location": "eastus",
    "provider_type": "azure"
  }'
```

## Step 6: Run Tests

```bash
# Run all tests
pytest

# Run provider tests specifically
pytest tests/test_providers.py -v

# Run with coverage
pytest --cov=backend --cov-report=html
```

## What You've Achieved

✅ **Installed** the multi-cloud application
✅ **Configured** Azure (and optionally AWS/GCP)
✅ **Started** the backend API
✅ **Tested** the provider system
✅ **Verified** multi-cloud capabilities

## Next Steps

### 1. Explore the Documentation

- **Architecture**: `ARCHITECTURE.md` - Understand the design
- **Multi-Cloud Guide**: `MULTI_CLOUD_GUIDE.md` - Learn advanced usage
- **Vendor Lock-In Solution**: `VENDOR_LOCK_IN_SOLUTION.md` - See how it works

### 2. Try Different Providers

```python
# Azure Native (Bicep)
provider = get_provider("azure")

# Azure via Terraform
provider = get_provider("terraform-azure", cloud_platform="azure")

# AWS via Terraform
provider = get_provider("terraform-aws", cloud_platform="aws")

# GCP via Terraform
provider = get_provider("terraform-gcp", cloud_platform="gcp")
```

### 3. Deploy Something Real

Use the web interface at `http://localhost:8000` or:

```bash
# Open frontend
open frontend/index.html  # Mac
xdg-open frontend/index.html  # Linux
start frontend/index.html  # Windows
```

## Troubleshooting

### Issue: Azure CLI not found

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login
```

### Issue: Terraform not found

```bash
# Download Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform version
```

### Issue: Module not found

```bash
# Make sure you're in venv
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# If still failing, try:
pip install azure-identity azure-mgmt-resource pydantic
```

### Issue: Permission denied

```bash
# Make sure you have the right permissions
chmod +x backend/main_v2.py

# Or run with python explicitly
python -m uvicorn backend.main_v2:app --reload
```

## Understanding What Changed

### Before (v1):
```
Your App → Hard-coded Azure SDK → Azure Only
```

### After (v2):
```
Your App → Provider Factory → [Azure | AWS | GCP]
```

### Key Files:

| File | Purpose |
|------|---------|
| `backend/providers/base.py` | Abstract interface for all providers |
| `backend/providers/azure_native.py` | Azure implementation |
| `backend/providers/terraform_provider.py` | Multi-cloud via Terraform |
| `backend/providers/factory.py` | Provider selection logic |
| `backend/main_v2.py` | New API using providers |
| `backend/config.py` | Configuration management |

## Code Examples

### Example 1: Switch Providers Dynamically

```python
async def deploy_to_best_cloud(template, params):
    # Try clouds in order of preference
    providers = [
        ("azure", "Azure sub"),
        ("terraform-aws", "AWS account"),
        ("terraform-gcp", "GCP project")
    ]

    for provider_type, subscription_id in providers:
        try:
            provider = get_provider(provider_type, subscription_id)
            result = await provider.deploy(template, params, "rg", "location")
            if result.status == DeploymentStatus.SUCCEEDED:
                return result
        except Exception as e:
            print(f"{provider_type} failed: {e}")
            continue

    raise Exception("All clouds failed!")
```

### Example 2: Multi-Cloud Comparison

```python
async def compare_clouds(template, params):
    clouds = ["azure", "terraform-aws", "terraform-gcp"]
    results = {}

    for cloud in clouds:
        provider = get_provider(cloud)

        # Validate template
        is_valid, error = await provider.validate_template(template, params)

        # Check supported locations
        locations = provider.get_supported_locations()

        results[cloud] = {
            "valid": is_valid,
            "locations": len(locations),
            "error": error
        }

    return results
```

## Final Check

Make sure everything works:

```bash
# 1. Backend is running
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}

# 2. Providers are available
curl http://localhost:8000/providers
# Should return list of providers

# 3. Tests pass
pytest tests/test_providers.py
# Should show all tests passing
```

## Success! 🎉

You now have a **multi-cloud, vendor-agnostic infrastructure management platform**!

You can:
- ✅ Deploy to Azure, AWS, or GCP
- ✅ Switch providers without code changes
- ✅ Compare clouds before deploying
- ✅ Avoid vendor lock-in completely

## Need Help?

- 📖 **Full Documentation**: See `ARCHITECTURE.md`
- 🌐 **API Docs**: Visit `http://localhost:8000/docs`
- 📚 **User Guide**: Read `MULTI_CLOUD_GUIDE.md`
- 🐛 **Issues**: Check logs in `logs/` directory

---

**You're ready to deploy to any cloud! 🚀**
