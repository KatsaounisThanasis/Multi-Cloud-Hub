# Multi-Cloud Infrastructure Manager

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
4. Open http://localhost:3000

## Tech Stack

- **Backend:** Python, FastAPI, Celery
- **Frontend:** React, Vite, Tailwind CSS
- **Infrastructure:** Terraform, Docker
- **Database:** PostgreSQL, Redis

## Documentation

See [docs/](docs/) for detailed guides.

## License

MIT
