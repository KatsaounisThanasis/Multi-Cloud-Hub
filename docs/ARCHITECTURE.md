# Architecture Overview

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   React + Vite + Tailwind                    │
│                      (Port 3000)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Server                              │
│                  FastAPI + Uvicorn                           │
│                      (Port 8000)                             │
└───────────┬─────────────────────────────────────┬───────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────┐       ┌───────────────────────────┐
│      PostgreSQL       │       │          Redis            │
│      (Database)       │       │     (Task Queue)          │
│      (Port 5432)      │       │      (Port 6379)          │
└───────────────────────┘       └─────────────┬─────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │      Celery Worker        │
                                │   (Background Tasks)      │
                                │      - Terraform          │
                                │      - Azure CLI          │
                                └─────────────┬─────────────┘
                                              │
                          ┌───────────────────┴───────────────┐
                          ▼                                   ▼
                 ┌─────────────────┐               ┌─────────────────┐
                 │     Azure       │               │      GCP        │
                 │  (Terraform)    │               │  (Terraform)    │
                 └─────────────────┘               └─────────────────┘
```

## Directory Structure

```
├── backend/
│   ├── api/              # REST API routes
│   ├── core/             # Auth, database, security
│   ├── providers/        # Cloud provider abstraction
│   ├── services/         # Business logic
│   ├── tasks/            # Celery background tasks
│   └── utils/            # Validators, helpers
├── frontend-v3/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── contexts/     # React contexts
│   │   └── api/          # API client
├── templates/
│   └── terraform/
│       ├── azure/        # 22 Azure templates
│       └── gcp/          # 13 GCP templates
├── credentials/          # Cloud credentials (gitignored)
└── docker-compose.yml    # Container orchestration
```

## Data Flow

1. **User Request** → Frontend sends request to API
2. **API Processing** → FastAPI validates and queues task
3. **Task Queue** → Redis stores task for Celery
4. **Worker Execution** → Celery worker runs Terraform
5. **Cloud Deployment** → Terraform deploys to Azure/GCP
6. **Status Updates** → Worker updates PostgreSQL
7. **Response** → Frontend polls for status updates

## Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 18, Vite, Tailwind | User interface |
| API | FastAPI, Pydantic | REST endpoints |
| Worker | Celery | Background processing |
| IaC | Terraform | Cloud deployments |
| Database | PostgreSQL | Persistent storage |
| Cache | Redis | Task queue, caching |
| Container | Docker | Containerization |
