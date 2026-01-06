# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Rate limiting middleware with configurable per-endpoint limits
- CSRF protection using double-submit cookie pattern
- SECURITY.md with vulnerability reporting guidelines
- CONTRIBUTING.md with development guidelines
- Prometheus metrics endpoint preparation

### Changed
- Removed all console.log statements from frontend for security
- Enhanced security headers middleware
- Improved error handling without exposing internals

### Security
- Fixed hardcoded default passwords - now generates random passwords in development
- Added rate limiting on authentication endpoints (anti-brute-force)
- Added CSRF validation for state-changing requests
- Removed sensitive data from client-side logging

## [1.0.0-rc1] - 2024-12-XX

### Added
- Multi-cloud infrastructure deployment support (Azure + GCP)
- Terraform-based deployment engine
- JWT authentication with Role-Based Access Control (RBAC)
- Real-time deployment log streaming via SSE
- Cost estimation for deployments
- Template management system with automatic discovery
- Dynamic parameter loading from cloud providers
- Cloud account management with user permissions
- React-based modern UI with deployment wizard
- Docker Compose setup for development and production
- Comprehensive API documentation (OpenAPI/Swagger)
- Health check endpoints with dependency status
- Background task processing with Celery

### Infrastructure Templates
- Azure: Storage Account, Virtual Network, Virtual Machine, Web App, SQL Database, AKS Cluster, Container Registry
- GCP: Cloud Storage, VPC Network, Compute Instance, Cloud Run, Cloud SQL

### Security
- Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
- Input validation and sanitization
- Sensitive data masking in logs
- Environment-based configuration
- Trusted hosts validation

## [0.9.0] - 2024-11-XX

### Added
- Initial project structure
- Basic Azure deployment support (Bicep)
- Simple REST API
- Basic frontend UI

### Changed
- Migrated from Bicep to Terraform for better multi-cloud support

## Version History Summary

| Version | Status | Notes |
|---------|--------|-------|
| 1.0.0   | In Development | First public release |
| 1.0.0-rc1 | Released | Release candidate |
| 0.9.0   | Deprecated | Pre-release internal version |

## Upgrade Notes

### From 0.9.x to 1.0.0

1. **Breaking Changes**:
   - API endpoints have changed from `/api/v2/*` to `/*`
   - Authentication is now required for most endpoints
   - Template format has changed (Bicep → Terraform)

2. **Migration Steps**:
   ```bash
   # Update environment variables
   cp .env.example .env
   # Edit .env with your credentials

   # Run database migrations (if applicable)
   alembic upgrade head

   # Rebuild containers
   docker compose down
   docker compose build
   docker compose up -d
   ```

3. **New Requirements**:
   - Python 3.11+
   - Node.js 18+
   - Terraform CLI
   - Updated cloud provider credentials

## Links

- [GitHub Releases](../../releases)
- [Migration Guides](docs/MIGRATION.md)
- [API Documentation](API_REFERENCE.md)
