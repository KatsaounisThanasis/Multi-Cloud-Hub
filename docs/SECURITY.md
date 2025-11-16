# Security Guide

This document describes the security features of the Multi-Cloud Infrastructure Management API and best practices for secure deployment.

## Table of Contents

1. [Security Features](#security-features)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [CORS Configuration](#cors-configuration)
5. [Security Headers](#security-headers)
6. [Input Validation](#input-validation)
7. [Logging and Monitoring](#logging-and-monitoring)
8. [Production Deployment](#production-deployment)
9. [Security Best Practices](#security-best-practices)

---

## Security Features

The API implements multiple layers of security:

- **API Key Authentication**: Protect endpoints with API keys
- **Rate Limiting**: Prevent abuse and DoS attacks
- **CORS Protection**: Control cross-origin requests
- **Security Headers**: HTTP security headers (CSP, X-Frame-Options, etc.)
- **Input Validation**: Sanitize and validate all user inputs
- **Request Logging**: Audit trail for all API requests
- **Sensitive Data Masking**: Automatic masking in logs

---

## Authentication

### Overview

API authentication is **optional** but **highly recommended** for production deployments.

### Configuration

**Development Mode** (Authentication Disabled):
```bash
# .env
API_AUTH_ENABLED=false
```

**Production Mode** (Authentication Enabled):
```bash
# .env
API_AUTH_ENABLED=true
API_KEY=your_secure_api_key_here
```

### Generating API Keys

Use the provided script to generate secure API keys:

```bash
python scripts/generate_api_key.py
```

This will output:
- A secure random API key (plaintext)
- The SHA-256 hash (for verification)

**Store the plaintext key securely** - you'll need it to make API requests.

### Using API Keys

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" \
     http://localhost:8000/health
```

**JavaScript/Fetch:**
```javascript
fetch('http://localhost:8000/deploy', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({...})
})
```

**Python requests:**
```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:8000/deploy',
    headers=headers,
    json={...}
)
```

### Authentication Responses

**Success (200/202):**
```json
{
  "success": true,
  "message": "Request processed",
  "data": {...}
}
```

**Missing API Key (401):**
```json
{
  "detail": "API key required. Provide X-API-Key header."
}
```

**Invalid API Key (401):**
```json
{
  "detail": "Invalid API key"
}
```

---

## Rate Limiting

### Overview

Rate limiting prevents abuse by limiting the number of requests per client per time window.

**Default Limit**: 60 requests per minute per client

### Configuration

```bash
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60  # Requests per minute
```

### Client Identification

Clients are identified by:
1. API Key (if provided) - more accurate tracking
2. IP Address (from `X-Forwarded-For` or `client.host`)

### Rate Limit Response

**Success (200):**
```json
{
  "success": true,
  "message": "Request processed"
}
```

**Rate Limit Exceeded (429):**
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds."
}
```

**Response Headers:**
- `Retry-After`: Seconds until rate limit resets

### Production Considerations

For distributed deployments, consider:
- Using Redis for shared rate limiting across instances
- Implementing different limits for different endpoint types
- Setting up monitoring for rate limit violations

**Example Redis-based rate limiter** (future enhancement):
```python
from redis import Redis
from fastapi_limiter import FastAPILimiter

@app.on_event("startup")
async def startup():
    redis = Redis(host='localhost', port=6379)
    await FastAPILimiter.init(redis)
```

---

## CORS Configuration

### Overview

Cross-Origin Resource Sharing (CORS) controls which domains can access the API from browsers.

### Configuration

**Development** (Allow All Origins):
```bash
# .env
CORS_ORIGINS=*
CORS_CREDENTIALS=true
```

**Production** (Restrict Origins):
```bash
# .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_CREDENTIALS=true
CORS_METHODS=GET,POST,PUT,DELETE
CORS_HEADERS=*
```

### Best Practices

1. **Never use `CORS_ORIGINS=*` in production**
2. List specific allowed domains
3. Use HTTPS for all production origins
4. Disable credentials if not needed: `CORS_CREDENTIALS=false`

---

## Security Headers

The API automatically adds security headers to all responses:

### Headers Applied

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter |
| `Strict-Transport-Security` | `max-age=31536000` | Force HTTPS (production only) |
| `Content-Security-Policy` | Custom CSP | Prevent XSS and injection attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer information |

### HSTS (Strict-Transport-Security)

Only applied in production (`ENVIRONMENT=production`).

Forces browsers to use HTTPS for 1 year (31536000 seconds).

---

## Input Validation

### Parameter Validation

All deployment parameters are validated for security issues:

**Checked Patterns:**
- Shell metacharacters: `;`, `&`, `|`, `` ` ``, `$`
- Path traversal: `../`, `..\`
- XSS attempts: `<script`
- SQL injection: `DROP TABLE`
- Code execution: `eval(`

**Size Limits:**
- Parameter name: 100 characters
- Parameter value: 10,000 characters
- Total parameters: 100 per request

**Example - Rejected Request:**
```json
{
  "template_name": "storage",
  "parameters": {
    "bucket_name": "test; rm -rf /"  // ❌ Contains shell metacharacters
  }
}
```

**Response (400):**
```json
{
  "success": false,
  "message": "Invalid deployment parameters",
  "error": {
    "details": "Potentially dangerous value in parameter 'bucket_name': contains '[;&|`$]'"
  }
}
```

### Filename Sanitization

Template and file names are sanitized to prevent path traversal:
- Path components removed
- Non-alphanumeric characters replaced with `_`
- Hidden files prevented (`.` prefix)

---

## Logging and Monitoring

### Request Logging

All requests are logged with:
- HTTP method and path
- Client IP address (from `X-Forwarded-For`)
- User agent
- Response status code
- Request duration

**Example Log:**
```
2025-01-09 10:30:45 - INFO - Request: POST /deploy from 192.168.1.100
2025-01-09 10:30:46 - INFO - Response: 202 for POST /deploy (1.234s)
```

### Sensitive Data Masking

Sensitive data is automatically masked in logs:

**Sensitive Keywords:**
- password, secret, token, api_key, private_key
- client_secret, access_token, refresh_token
- credentials, auth, authorization

**Example:**
```python
# Original data
{
  "username": "admin",
  "password": "SuperSecret123",
  "api_key": "sk-1234567890abcdef"
}

# Logged data (masked)
{
  "username": "admin",
  "password": "Su***23",
  "api_key": "sk***ef"
}
```

### Security Events

Critical security events are logged:
- Failed authentication attempts
- Rate limit violations
- Invalid parameter attempts
- Unusual request patterns

---

## Production Deployment

### Security Checklist

Before deploying to production:

- [ ] **Enable Authentication**
  ```bash
  API_AUTH_ENABLED=true
  API_KEY=<secure-random-key>
  ```

- [ ] **Configure CORS Properly**
  ```bash
  CORS_ORIGINS=https://yourdomain.com
  ```

- [ ] **Set Environment to Production**
  ```bash
  ENVIRONMENT=production
  DEBUG=false
  ```

- [ ] **Enable Rate Limiting**
  ```bash
  RATE_LIMIT_ENABLED=true
  ```

- [ ] **Use HTTPS**
  - Configure reverse proxy (nginx, Traefik)
  - Obtain SSL certificates (Let's Encrypt)

- [ ] **Secure Database**
  ```bash
  DATABASE_URL=postgresql://user:strong_password@localhost/db
  ```

- [ ] **Secure Redis**
  - Enable authentication: `REDIS_URL=redis://:password@localhost:6379`
  - Bind to localhost only
  - Use firewall rules

- [ ] **Set Up Monitoring**
  - Log aggregation (ELK, Splunk)
  - Metrics (Prometheus, Grafana)
  - Alerts for security events

- [ ] **Regular Updates**
  - Keep dependencies updated
  - Monitor security advisories
  - Apply patches promptly

### Environment Variables for Production

```bash
# Security
ENVIRONMENT=production
DEBUG=false
API_AUTH_ENABLED=true
API_KEY=<secure-key>
RATE_LIMIT_ENABLED=true

# CORS
CORS_ORIGINS=https://yourdomain.com
CORS_CREDENTIALS=true

# Database (use strong passwords)
DATABASE_URL=postgresql://apiuser:<strong-password>@postgres:5432/multicloud
DB_PASSWORD=<strong-password>

# Redis (with authentication)
REDIS_URL=redis://:<strong-password>@redis:6379/0

# Cloud Credentials (use Key Vault/Secrets Manager)
USE_KEY_VAULT=true
KEY_VAULT_URL=https://your-keyvault.vault.azure.net/
```

### Using Azure Key Vault (Recommended)

For production, store secrets in Azure Key Vault:

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = SecretClient(
    vault_url="https://your-keyvault.vault.azure.net/",
    credential=credential
)

api_key = client.get_secret("api-key").value
db_password = client.get_secret("db-password").value
```

---

## Security Best Practices

### 1. Principle of Least Privilege

- Use separate credentials for each cloud provider
- Grant only necessary permissions
- Use service principals/service accounts, not personal accounts

### 2. Network Security

- Deploy behind a firewall
- Use VPC/VNet isolation
- Restrict database access to API only
- Use private endpoints for Azure/AWS services

### 3. Secrets Management

**❌ Don't:**
- Commit secrets to Git
- Store secrets in plaintext files
- Share secrets via email/Slack

**✓ Do:**
- Use Azure Key Vault / AWS Secrets Manager / GCP Secret Manager
- Rotate secrets regularly
- Use environment variables
- Implement secrets rotation

### 4. Monitoring and Alerting

Set up alerts for:
- Failed authentication attempts (>10 per hour)
- Rate limit violations (>100 per hour)
- Unusual deployment patterns
- Database connection failures
- High error rates

### 5. Regular Security Audits

- Review access logs weekly
- Audit API key usage
- Check for unused/expired keys
- Review deployment history
- Update dependencies monthly

### 6. Backup and Disaster Recovery

- Regular database backups
- Terraform state backups
- Document recovery procedures
- Test recovery process

### 7. Compliance

Depending on your industry:
- **HIPAA**: Encrypt data at rest and in transit
- **PCI-DSS**: Secure cardholder data
- **GDPR**: Implement data protection measures
- **SOC 2**: Maintain audit logs

---

## Security Incident Response

If you suspect a security breach:

1. **Isolate**: Disable affected API keys immediately
2. **Investigate**: Check logs for unauthorized access
3. **Rotate**: Generate new API keys
4. **Notify**: Inform stakeholders
5. **Remediate**: Fix vulnerabilities
6. **Document**: Record incident details

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security concerns to: [your-security-email@domain.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We take security seriously and will respond within 48 hours.

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Azure Security Best Practices](https://docs.microsoft.com/en-us/azure/security/)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)

---

**Last Updated**: 2025-01-09
**Version**: 3.0.0
