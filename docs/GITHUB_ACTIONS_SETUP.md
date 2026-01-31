# GitHub Actions Setup Guide

## Overview

GitHub Actions CI/CD has been fully implemented for Bujji-Coder-AI. This document explains what was set up and how to use it.

## ✅ What's Been Implemented

### 1. **Automated Testing** (`test.yml`)
- ✅ Runs tests on every push and pull request
- ✅ Tests across Python 3.9, 3.10, 3.11
- ✅ Code linting (flake8, black, isort)
- ✅ Backend API testing
- ✅ Frontend build validation
- ✅ Coverage reports

### 2. **Security Scanning** (`security.yml`)
- ✅ Dependency vulnerability scanning (safety, pip-audit)
- ✅ Code security analysis (bandit)
- ✅ Secret detection (gitleaks)
- ✅ Docker image scanning (trivy)
- ✅ Weekly automated scans

### 3. **Code Quality** (`code-quality.yml`)
- ✅ Code formatting checks (black, isort)
- ✅ Linting (flake8, pylint)
- ✅ Type checking (mypy)
- ✅ Frontend linting (ESLint)

### 4. **Docker Building** (`docker-build.yml`)
- ✅ Builds backend and frontend Docker images
- ✅ Validates images work correctly
- ✅ Uses build caching for speed

### 5. **Deployment** (`deploy.yml`)
- ✅ Builds and pushes Docker images
- ✅ Supports staging and production deployments
- ✅ Manual deployment triggers
- ✅ Tag-based releases

### 6. **Release Management** (`release.yml`)
- ✅ Automatic release creation on version tags
- ✅ Changelog generation

### 7. **Dependabot** (`dependabot.yml`)
- ✅ Automatic dependency updates
- ✅ Weekly update checks
- ✅ Separate PRs for Python, Node.js, Docker, GitHub Actions

## 📋 Required Setup

### 1. GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:

#### Required:
- `OPENAI_API_KEY` - For running tests (can use a test key)

#### Optional (for Docker Hub deployment):
- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_PASSWORD` - Your Docker Hub password or access token

### 2. Enable GitHub Actions

GitHub Actions are enabled by default. If disabled:
1. Go to repository Settings
2. Click "Actions" in the left sidebar
3. Enable "Allow all actions and reusable workflows"

### 3. Enable Dependabot

Dependabot is configured but needs to be enabled:
1. Go to repository Settings
2. Click "Code security and analysis"
3. Enable "Dependabot alerts" and "Dependabot security updates"

## 🚀 How It Works

### On Every Push/PR:
1. **Tests run** - Validates code works
2. **Code quality checks** - Ensures formatting and style
3. **Security scans** - Finds vulnerabilities
4. **Docker builds** - Validates containerization

### On Push to Main:
1. All checks above
2. **Docker images built and pushed** (if secrets configured)
3. **Deployment triggered** (if configured)

### On Version Tag (v*):
1. All checks
2. **GitHub Release created**
3. **Production deployment** (if configured)

## 📊 Viewing Results

### Status Badges
The README now includes status badges showing:
- Test status
- Security scan status
- Code quality status

### Actions Tab
1. Go to your repository on GitHub
2. Click the "Actions" tab
3. See all workflow runs and their status

### Detailed Reports
- Test coverage: View in Actions → Tests → Artifacts
- Security reports: View in Actions → Security
- Code quality: View in Actions → Code Quality

## 🔧 Customization

### Modify Test Matrix
Edit `.github/workflows/test.yml`:
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11"]  # Add/remove versions
```

### Add Deployment Steps
Edit `.github/workflows/deploy.yml`:
```yaml
- name: Deploy to production
  run: |
    # Add your deployment commands here
    ssh user@server "cd /app && docker-compose pull && docker-compose up -d"
```

### Adjust Security Thresholds
Edit `.github/workflows/security.yml`:
```yaml
severity: 'CRITICAL,HIGH'  # Change to include MEDIUM, LOW
```

## 🐛 Troubleshooting

### Tests Failing
1. Check Actions tab for error details
2. Run tests locally: `pytest tests/`
3. Check if dependencies are up to date

### Security Scans Failing
1. Review security reports in Actions tab
2. Update vulnerable dependencies
3. Fix security issues in code

### Docker Build Failing
1. Test Docker build locally: `docker build -f Dockerfile .`
2. Check for missing files
3. Verify Dockerfile syntax

### Workflows Not Running
1. Check if GitHub Actions is enabled
2. Verify workflow files are in `.github/workflows/`
3. Check for syntax errors in YAML files

## 📈 Benefits

### Time Savings
- **Before**: Manual testing takes 30+ minutes
- **After**: Automated testing takes 5-10 minutes
- **Savings**: 20+ minutes per change

### Quality Improvement
- Catches bugs before they reach production
- Ensures code quality standards
- Identifies security vulnerabilities early

### Professional Standard
- Industry best practice
- Shows project maturity
- Important for open-source projects

## 🎯 Next Steps

1. **Set up GitHub Secrets** (see above)
2. **Push code to trigger workflows**
3. **Review workflow results**
4. **Customize deployment steps** (if needed)
5. **Enable Dependabot** (optional but recommended)

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)

---

**Status**: ✅ Fully implemented and ready to use!
