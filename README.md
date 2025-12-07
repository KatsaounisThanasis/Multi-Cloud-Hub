# Multi-Cloud Infrastructure Manager

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18-61DAFB.svg)
![Terraform](https://img.shields.io/badge/terraform-1.5+-purple.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)
![Azure](https://img.shields.io/badge/cloud-Azure-0078D4.svg)
![GCP](https://img.shields.io/badge/cloud-GCP-4285F4.svg)

A unified platform for deploying and managing cloud infrastructure
across Azure and Google Cloud Platform using Terraform.

## Features

- **Multi-Cloud Support** - Deploy to Azure and GCP from one interface
- **Terraform Backend** - Infrastructure as Code for all deployments
- **Real-time Logs** - Live deployment progress and status
- **Cost Estimation** - Preview costs before deploying
- **Template Library** - 35+ pre-built templates (22 Azure, 13 GCP)
- **REST API** - Full API access for automation
- **Authentication** - JWT-based user authentication

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and add your credentials
3. Run:
   ```bash
   docker compose up -d
   ```
4. Open http://localhost:5174

## Tech Stack

- **Backend:** Python, FastAPI, Celery
- **Frontend:** React, Vite, Tailwind CSS
- **Infrastructure:** Terraform, Docker
- **Database:** PostgreSQL, Redis

## Documentation

See [docs/](docs/) for detailed guides:

- [Quick Start](docs/QUICK_START.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Credentials Setup](docs/CREDENTIALS_SETUP.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
