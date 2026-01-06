# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow responsible disclosure practices.

### How to Report

1. **Do NOT create a public GitHub issue** for security vulnerabilities
2. Email security concerns to: [Create a private security advisory](../../security/advisories/new)
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Within 5 business days
- **Resolution Timeline**: Depends on severity
  - Critical: 24-72 hours
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next release cycle

### Disclosure Policy

- We will acknowledge receipt of your report
- We will confirm the vulnerability and determine its impact
- We will release a fix and publicly disclose the issue
- We will credit you in the release notes (unless you prefer anonymity)

## Security Measures

### Authentication & Authorization

- **JWT-based authentication** with configurable expiration
- **Role-Based Access Control (RBAC)** with three tiers:
  - Admin: Full access
  - User: Deploy and manage resources
  - Viewer: Read-only access
- **Password hashing** using bcrypt with proper salting
- **Rate limiting** on authentication endpoints (10 requests/minute for login, 5 for registration)

### API Security

- **Rate Limiting**: Configurable per-endpoint rate limits
  - General API: 100 requests/minute
  - Authentication: 10 requests/minute
  - Deployments: 20 requests/minute
- **CSRF Protection**: Double-submit cookie pattern for browser-based requests
- **Security Headers**:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security (HSTS) in production
  - Content-Security-Policy
  - Referrer-Policy

### Input Validation

- Comprehensive parameter validation with regex patterns
- Protection against:
  - Command injection
  - Path traversal
  - XSS attacks
  - SQL injection patterns
- Maximum parameter size constraints

### Sensitive Data Handling

- **Credentials**: Never stored in code; use environment variables
- **Logging**: Automatic masking of sensitive fields (password, token, secret, api_key, etc.)
- **Production Mode**: Default users disabled; random passwords in development
- **Git Ignored**: `.env`, `*.pem`, `credentials.json`, service account files

### Infrastructure Security

- **Docker**: Non-root user, health checks, resource limits
- **Network**: Internal Docker network isolation
- **Database**: PostgreSQL with proper authentication
- **Redis**: Used for task queue (not exposed externally)

## Security Configuration

### Environment Variables

```bash
# Required in Production
ENVIRONMENT=production
JWT_SECRET_KEY=<strong-random-key>

# Optional Security Settings
RATE_LIMIT_ENABLED=true
CSRF_PROTECTION_ENABLED=true
CORS_ORIGINS=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com

# Authentication
API_AUTH_ENABLED=true
API_KEY=<your-api-key>
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure strong `JWT_SECRET_KEY` (32+ characters)
- [ ] Enable `API_AUTH_ENABLED=true`
- [ ] Restrict `CORS_ORIGINS` to your domains
- [ ] Set `TRUSTED_HOSTS` to your domain(s)
- [ ] Use HTTPS (configure reverse proxy)
- [ ] Review and rotate API keys regularly
- [ ] Enable database encryption at rest
- [ ] Configure backup procedures
- [ ] Set up monitoring and alerting

## Known Security Limitations

1. **In-Memory Rate Limiting**: For single-instance deployments only. Multi-instance deployments should use Redis-backed rate limiting.

2. **Database Encryption**: Not enabled by default. Configure PostgreSQL with encryption at rest for production.

3. **Secrets Management**: Currently uses environment variables. Consider integrating with a secrets manager (Azure Key Vault, GCP Secret Manager) for production.

## Security Best Practices for Users

### Cloud Credentials

1. **Use Service Principals/Service Accounts** with minimal required permissions
2. **Never commit credentials** to version control
3. **Rotate credentials** regularly
4. **Use separate credentials** for development and production

### Deployment Security

1. **Review templates** before deploying
2. **Use parameter validation** in your templates
3. **Tag resources** for tracking and compliance
4. **Enable cloud provider audit logging**

### Network Security

1. **Use private endpoints** where possible
2. **Configure firewall rules** to restrict access
3. **Enable VPC/VNet** for resource isolation
4. **Use TLS** for all connections

## Compliance

This application is designed with security best practices but is not certified for specific compliance frameworks. Users are responsible for ensuring their deployments meet their compliance requirements (SOC 2, HIPAA, GDPR, etc.).

## Contact

For non-security related questions, please use [GitHub Issues](../../issues).

For security concerns, please use [GitHub Security Advisories](../../security/advisories/new).
