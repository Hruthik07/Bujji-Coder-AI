# GitHub Actions Workflows

This directory contains CI/CD workflows for Bujji-Coder-AI.

## Workflows

### 1. **test.yml** - Automated Testing
- Runs on: Push to main/develop, Pull Requests
- What it does:
  - Runs tests across Python 3.9, 3.10, 3.11
  - Checks code linting (flake8, black, isort)
  - Tests backend API endpoints
  - Builds and validates frontend
  - Generates coverage reports

### 2. **security.yml** - Security Scanning
- Runs on: Push to main/develop, Pull Requests, Weekly schedule
- What it does:
  - Scans Python dependencies for vulnerabilities (safety, pip-audit)
  - Scans code for security issues (bandit)
  - Scans for exposed secrets (gitleaks)
  - Scans Docker images for vulnerabilities (trivy)

### 3. **code-quality.yml** - Code Quality Checks
- Runs on: Push to main/develop, Pull Requests
- What it does:
  - Checks code formatting (black, isort)
  - Runs linters (flake8, pylint)
  - Type checking (mypy)
  - Frontend linting (ESLint)

### 4. **deploy.yml** - Deployment Automation
- Runs on: Push to main, Tags (v*), Manual trigger
- What it does:
  - Builds Docker images
  - Pushes to Docker Hub
  - Deploys to staging/production (configurable)

### 5. **docker-build.yml** - Docker Image Building
- Runs on: Push to main/develop, Pull Requests
- What it does:
  - Builds backend and frontend Docker images
  - Tests that images work correctly

### 6. **release.yml** - Release Management
- Runs on: Push tags (v*)
- What it does:
  - Creates GitHub releases
  - Generates changelogs

## Required Secrets

To use all workflows, you need to set up these GitHub Secrets:

### Required:
- `OPENAI_API_KEY` - For running tests that need OpenAI API

### Optional (for deployment):
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password or access token

## Status Badges

Add these to your README.md:

```markdown
![Tests](https://github.com/Hruthik07/Bujji-Coder-AI/workflows/Tests/badge.svg)
![Security](https://github.com/Hruthik07/Bujji-Coder-AI/workflows/Security/badge.svg)
![Code Quality](https://github.com/Hruthik07/Bujji-Coder-AI/workflows/Code%20Quality/badge.svg)
```

## Customization

### Modify Test Matrix
Edit `.github/workflows/test.yml` to change Python versions or add more test types.

### Add Deployment Steps
Edit `.github/workflows/deploy.yml` to add your actual deployment commands (SSH, kubectl, etc.).

### Adjust Security Thresholds
Edit `.github/workflows/security.yml` to change severity levels or add more scanners.

## Troubleshooting

### Tests Failing
- Check if all dependencies are in `requirements.txt`
- Verify test files are in `tests/` directory
- Check Python version compatibility

### Security Scans Failing
- Review the reports in the Actions tab
- Update vulnerable dependencies
- Fix security issues in code

### Docker Build Failing
- Check Dockerfile syntax
- Verify all files are present
- Check for missing dependencies
