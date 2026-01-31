# Production Deployment Script for Bujji-Coder-AI (PowerShell)
# Usage: .\deploy.ps1 [environment]
# Environments: development, staging, production

param(
    [string]$Environment = "production"
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Bujji-Coder-AI Deployment Script" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker Compose is not installed" -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env.$Environment") -and $Environment -ne "development") {
    Write-Host "Warning: .env.$Environment not found" -ForegroundColor Yellow
    Write-Host "Creating from example..." -ForegroundColor Yellow
    if (Test-Path ".env.production.example") {
        Copy-Item ".env.production.example" ".env.$Environment"
        Write-Host "Please edit .env.$Environment and set your configuration" -ForegroundColor Yellow
        exit 1
    }
}

# Load environment variables
if (Test-Path ".env.$Environment") {
    Get-Content ".env.$Environment" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Validate required variables
if ($Environment -eq "production") {
    $jwtSecret = [Environment]::GetEnvironmentVariable("JWT_SECRET_KEY", "Process")
    if ([string]::IsNullOrEmpty($jwtSecret) -or $jwtSecret -eq "your-super-secret-jwt-key-change-this-in-production") {
        Write-Host "Error: JWT_SECRET_KEY must be set in .env.production" -ForegroundColor Red
        exit 1
    }
    
    $corsOrigins = [Environment]::GetEnvironmentVariable("CORS_ORIGINS", "Process")
    if ([string]::IsNullOrEmpty($corsOrigins)) {
        Write-Host "Error: CORS_ORIGINS must be set in .env.production" -ForegroundColor Red
        exit 1
    }
}

# Build images
Write-Host "Building Docker images..." -ForegroundColor Green
docker-compose build

# Start services
if ($Environment -eq "production") {
    Write-Host "Starting production services..." -ForegroundColor Green
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
} else {
    Write-Host "Starting development services..." -ForegroundColor Green
    docker-compose up -d
}

# Wait for services to be ready
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Health check
Write-Host "Performing health check..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$healthCheckPassed = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8010/api/health" -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Health check passed!" -ForegroundColor Green
            $healthCheckPassed = $true
            break
        }
    } catch {
        # Continue retrying
    }
    
    $retryCount++
    Write-Host "Waiting for backend... ($retryCount/$maxRetries)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

if (-not $healthCheckPassed) {
    Write-Host "Error: Health check failed after $maxRetries retries" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs backend" -ForegroundColor Yellow
    exit 1
}

# Display status
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8010" -ForegroundColor White
Write-Host "Frontend: http://localhost:80" -ForegroundColor White
Write-Host ""
Write-Host "Health Check:" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8010/api/health"
    $health | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Could not fetch health status" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "View logs: docker-compose logs -f" -ForegroundColor White
Write-Host "Stop services: docker-compose down" -ForegroundColor White
Write-Host ""
