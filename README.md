# Multi-Cloud Infrastructure Management API

![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Azure](https://img.shields.io/badge/Azure-✓-0078D4.svg)
![AWS](https://img.shields.io/badge/AWS-✓-FF9900.svg)
![GCP](https://img.shields.io/badge/GCP-✓-4285F4.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![Tests](https://img.shields.io/badge/tests-70%25+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Breaking free from vendor lock-in** - A production-ready REST API for managing infrastructure across Azure, AWS, and Google Cloud from a single unified interface.

> **Latest Release:** v3.0 - Multi-Cloud Support | [v2.0](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal/releases/tag/v2.0.0) - Azure Only

---

## 🌟 What's New in v3.0

Transform your infrastructure management with true multi-cloud capabilities:

- 🌐 **Multi-Cloud Support** - Deploy to Azure, AWS, or GCP from one API
- 🏗️ **Provider Abstraction** - Cloud-agnostic architecture eliminates vendor lock-in
- 🔧 **Terraform Integration** - Support for both Bicep and Terraform templates
- 🐳 **Docker Ready** - Production containers with docker-compose
- 🧪 **Enterprise Testing** - 50+ tests with 70%+ coverage
- 🔄 **CI/CD Pipeline** - Automated testing with GitHub Actions
- 📚 **Rich Documentation** - 9 comprehensive guides

[View Full Changelog](CHANGELOG.md) | [Migration Guide](releases/MIGRATION_v2_to_v3.md) | [Release Notes](releases/v3.0-RELEASE-NOTES.md)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal.git
cd Azure-Resource-Manager-Portal

# Configure environment
cp .env.example .env
# Edit .env with your cloud credentials

# Start with Docker
docker-compose up -d

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn backend.api_rest:app --reload

# Or use Makefile
make dev
```

### First API Call

```bash
# Check health
curl http://localhost:8000/health

# List available cloud providers
curl http://localhost:8000/api/v1/providers

# List templates
curl http://localhost:8000/api/v1/templates
```

---

## 🌐 Multi-Cloud Deployments

Deploy the same resource to any cloud provider:

### Deploy to Azure
```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "azure",
    "template_name": "storage-account",
    "subscription_id": "your-sub-id",
    "resource_group": "my-rg",
    "location": "eastus",
    "parameters": {
      "storageAccountName": "mystorageacct123"
    }
  }'
```

### Deploy to AWS
```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "terraform-aws",
    "template_name": "storage-bucket",
    "resource_group": "my-project",
    "location": "us-east-1",
    "parameters": {
      "bucket_name": "my-bucket-123"
    }
  }'
```

### Deploy to GCP
```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "terraform-gcp",
    "template_name": "storage-bucket",
    "project_id": "my-gcp-project",
    "resource_group": "my-project",
    "location": "us-central1",
    "parameters": {
      "bucket_name": "my-gcs-bucket"
    }
  }'
```

---

## 📦 Features

### Core Capabilities

| Feature | v2.0 | v3.0 |
|---------|------|------|
| **Cloud Providers** | Azure only | Azure + AWS + GCP |
| **IaC Tools** | Bicep | Bicep + Terraform |
| **Templates** | 15 Azure | 22 multi-cloud |
| **API Architecture** | REST | Enhanced REST |
| **Deployment** | Manual | Docker + K8s ready |
| **Testing** | 11 tests | 50+ tests |
| **CI/CD** | None | GitHub Actions |
| **Documentation** | Basic | 9 comprehensive guides |

### Multi-Cloud Support

- ☁️ **Microsoft Azure**
  - Native Bicep support
  - ARM templates
  - Terraform alternative
  - Azure CLI integration

- 🟠 **Amazon Web Services**
  - Terraform automation
  - S3, EC2, Lambda
  - IAM management
  - Multiple regions

- 🔵 **Google Cloud Platform**
  - Terraform automation
  - Cloud Storage, Compute, Functions
  - IAM integration
  - Multi-region support

### Architecture

```
┌─────────────────────────────────────┐
│         REST API Layer              │
│    (FastAPI + OpenAPI/Swagger)      │
├─────────────────────────────────────┤
│      Provider Abstraction           │
│     (Factory + Strategy Pattern)    │
├──────────┬──────────┬───────────────┤
│  Azure   │   AWS    │     GCP       │
│ Provider │ Provider │   Provider    │
│  Bicep   │Terraform │  Terraform    │
└──────────┴──────────┴───────────────┘
```

### Template Library

**Azure (15 Bicep + 1 Terraform):**
- Storage Accounts, Virtual Machines, App Services
- Function Apps, Virtual Networks, SQL Databases
- Container Instances, Key Vaults, and more

**AWS (3 Terraform):**
- S3 Buckets, EC2 Instances, Lambda Functions

**GCP (3 Terraform):**
- Cloud Storage, Compute Engine, Cloud Functions

[Browse all templates →](templates/)

---

## 🛠️ Development

### Project Structure

```
.
├── backend/                 # API backend
│   ├── api_rest.py         # REST API endpoints
│   ├── providers/          # Cloud provider implementations
│   │   ├── base.py         # Abstract base classes
│   │   ├── azure_native.py # Azure implementation
│   │   ├── terraform_provider.py # Terraform implementation
│   │   └── factory.py      # Provider factory
│   └── template_manager.py # Template discovery
├── templates/              # IaC templates
│   ├── *.bicep            # Azure Bicep templates
│   └── terraform/         # Terraform templates
│       ├── aws/           # AWS resources
│       ├── gcp/           # GCP resources
│       └── azure/         # Azure via Terraform
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── examples/               # Usage examples
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-coverage

# Fast tests (skip slow)
make test-fast

# Using test script
./scripts/run_tests.sh unit
./scripts/run_tests.sh coverage
```

### Code Quality

```bash
# Linting
make lint

# Type checking
make type-check

# Code formatting
make format

# All quality checks
make quality
```

---

## 🐳 Docker Deployment

### Quick Start

```bash
# Production
docker-compose up -d

# Development (with hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Minimal (Azure only)
docker build -f Dockerfile.minimal -t multicloud-api:minimal .
```

### Environment Variables

Create `.env` file:

```bash
# Azure
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# GCP
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# API
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Cloud Deployment

Deploy containers to:
- **Azure Container Apps**
- **AWS ECS/Fargate**
- **GCP Cloud Run**
- **Kubernetes** (manifests ready)

---

## 📖 Documentation

Comprehensive guides in the [`docs/`](docs/) folder:

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and patterns
- [API Reference](docs/API_GUIDE.md) - Complete endpoint documentation
- [Testing Guide](docs/TESTING_GUIDE.md) - Testing best practices
- [Multi-Cloud Guide](docs/MULTI_CLOUD_GUIDE.md) - Multi-cloud deployments
- [Quick Start](docs/QUICK_START_GUIDE.md) - Get started in 5 minutes
- [Migration Guide](releases/MIGRATION_v2_to_v3.md) - Upgrade from v2.0

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testing

Enterprise-grade test infrastructure:

```bash
# Test statistics
- Unit Tests: 25+ tests
- Integration Tests: 15+ tests
- E2E Tests: 10+ tests
- Coverage: 70%+
- CI/CD: GitHub Actions
```

Test categories:
- ✅ Provider factory and abstraction
- ✅ Azure native implementation
- ✅ Terraform provider
- ✅ Template discovery and management
- ✅ REST API endpoints
- ✅ Docker container builds
- ✅ Configuration validation

---

## 🔒 Security

- **Container Security**: Non-root user, minimal base image
- **Secrets Management**: Environment-based configuration
- **Input Validation**: Pydantic models with type checking
- **Security Scanning**: Automated with Bandit and Safety
- **CI/CD Integration**: Security checks on every commit

**Production Recommendations:**
- Use cloud-native secret managers (Azure Key Vault, AWS Secrets Manager, GCP Secret Manager)
- Enable cloud provider firewalls
- Use managed identities/service accounts
- Implement API authentication
- Enable audit logging

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📊 Project Metrics

| Metric | Value |
|--------|-------|
| Lines of Code | ~3,000+ |
| Python Files | 25+ |
| Test Files | 4 |
| Templates | 22 |
| Documentation | 9 guides |
| Docker Images | 2 |
| CI/CD Jobs | 7 |
| Cloud Providers | 3 |

---

## 🗺️ Roadmap

### v3.1 (Planned)
- [ ] API authentication (API keys, OAuth)
- [ ] Rate limiting
- [ ] Deployment history database
- [ ] Cost estimation before deployment
- [ ] Webhook notifications

### v4.0 (Future)
- [ ] Web-based UI dashboard
- [ ] CLI tool
- [ ] Kubernetes Operator
- [ ] Multi-region deployments
- [ ] Infrastructure cost analytics

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Azure SDK](https://azure.microsoft.com/en-us/downloads/) - Azure integration
- [Terraform](https://www.terraform.io/) - Multi-cloud IaC
- [Docker](https://www.docker.com/) - Containerization
- [pytest](https://pytest.org/) - Testing framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal/discussions)
- **Documentation**: [docs/](docs/) folder
- **Email**: Contact repository owner

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

## 🚀 Version History

- **v3.0.0** (2025-11-06) - Multi-cloud support with AWS and GCP
- **v2.0.0** (2024-06-09) - Complete refactor with FastAPI and Bootstrap 5
- **v1.0.0** - Initial Azure-only release

[View all releases →](https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal/releases)

---

**Transform your infrastructure management today!** 🌟

Deploy anywhere, manage everywhere, locked into nowhere.
