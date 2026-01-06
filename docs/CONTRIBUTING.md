# Contributing to Multi-Cloud Infrastructure Hub

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include**:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, browser)
   - Screenshots if applicable

### Suggesting Features

1. **Check existing issues** for similar suggestions
2. **Use the feature request template**
3. **Explain**:
   - The problem you're trying to solve
   - Your proposed solution
   - Alternative approaches considered
   - Impact on existing functionality

### Submitting Pull Requests

1. **Fork the repository** and create a branch from `preprod`
2. **Follow the coding standards** (see below)
3. **Write tests** for new functionality
4. **Update documentation** if needed
5. **Ensure all tests pass** before submitting
6. **Reference related issues** in your PR description

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Azure CLI (for Azure templates)
- gcloud CLI (for GCP templates)

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/Multi-Cloud-Hub.git
cd Multi-Cloud-Hub

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r tests/requirements-test.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Start services
docker compose up -d redis postgres

# Run backend
cd backend
uvicorn api.routes:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run frontend
cd frontend-v3
npm install
npm run dev
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_auth_router.py -v

# Run tests matching a pattern
pytest -k "test_login" -v

# Run with verbose output
pytest -v --tb=short
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make typecheck

# Run all checks
make check-all
```

## Coding Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for formatting
- Use type hints for all functions
- Write docstrings for public functions and classes
- Maximum line length: 100 characters

```python
def process_deployment(
    template_name: str,
    parameters: dict[str, Any],
    *,
    dry_run: bool = False
) -> DeploymentResult:
    """
    Process a deployment request.

    Args:
        template_name: Name of the template to deploy
        parameters: Template parameters
        dry_run: If True, validate without deploying

    Returns:
        DeploymentResult with status and outputs

    Raises:
        ValidationError: If parameters are invalid
        DeploymentError: If deployment fails
    """
    ...
```

### JavaScript/React (Frontend)

- Use functional components with hooks
- Use meaningful variable names
- Avoid `console.log` in production code
- Use PropTypes or TypeScript for type checking
- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

```jsx
function DeploymentCard({ deployment, onSelect }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleClick = useCallback(() => {
    setIsExpanded(prev => !prev);
    onSelect?.(deployment.id);
  }, [deployment.id, onSelect]);

  return (
    <div className="deployment-card" onClick={handleClick}>
      {/* Component content */}
    </div>
  );
}
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(api): add rate limiting middleware
fix(auth): correct JWT expiration handling
docs(readme): update installation instructions
test(deployments): add integration tests for GCP
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Refactoring
- `test/description` - Test additions

## Project Structure

```
Multi-Cloud-Hub/
├── backend/
│   ├── api/              # FastAPI routers and schemas
│   ├── core/             # Core modules (auth, security, etc.)
│   ├── providers/        # Cloud provider implementations
│   ├── services/         # Business logic services
│   ├── tasks/            # Celery background tasks
│   └── utils/            # Utility functions
├── frontend-v3/          # React frontend
│   ├── src/
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Page components
│   │   ├── contexts/     # React contexts
│   │   ├── hooks/        # Custom hooks
│   │   └── api/          # API client
├── templates/            # Infrastructure templates
│   ├── azure/            # Azure (Bicep/Terraform)
│   └── gcp/              # GCP (Terraform)
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
└── docs/                 # Documentation
```

## Testing Guidelines

### Unit Tests

- Test one thing per test
- Use descriptive test names
- Mock external dependencies
- Aim for high code coverage

```python
class TestAuthRouter:
    """Tests for authentication endpoints."""

    def test_login_success(self, client, mock_user):
        """Test successful login returns token."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "validpassword"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials returns 401."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
```

### Integration Tests

- Test component interactions
- Use real database for data tests
- Clean up test data after tests

### End-to-End Tests

- Test complete user workflows
- Run against staging environment
- Include both happy path and error scenarios

## Documentation

- Update README.md for user-facing changes
- Update API_REFERENCE.md for API changes
- Add inline code comments for complex logic
- Keep CHANGELOG.md updated

## Release Process

1. Create release branch from `preprod`
2. Update version in appropriate files
3. Update CHANGELOG.md
4. Create PR to `main`
5. After merge, create GitHub release with tag
6. Deploy to production

## Getting Help

- **Questions**: Open a [Discussion](../../discussions)
- **Bugs**: Open an [Issue](../../issues)
- **Security**: See [SECURITY.md](SECURITY.md)

## Recognition

Contributors will be recognized in:
- Release notes
- CONTRIBUTORS.md (for significant contributions)

Thank you for contributing!
