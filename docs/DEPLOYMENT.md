# Production Deployment Guide

This guide covers deploying Bujji-Coder-AI to production environments.

## Prerequisites

- Docker and Docker Compose installed
- Domain name (for production)
- SSL certificate (for HTTPS)
- API keys for LLM providers (OpenAI, Anthropic, DeepSeek)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Hruthik07/Bujji-Coder-AI.git
cd Bujji-Coder-AI
```

### 2. Configure Environment

Copy the production environment example:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and set:
- `JWT_SECRET_KEY` - Generate a strong secret key
- `CORS_ORIGINS` - Your domain(s)
- API keys for LLM providers
- `ADMIN_PASSWORD` - Strong password for default admin user

### 3. Generate JWT Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Build and Start

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Verify Deployment

```bash
# Check health
curl http://localhost:8010/api/health

# Check status
curl http://localhost:8010/api/status
```

## Environment Variables

### Required Variables

- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `OPENAI_API_KEY` - OpenAI API key
- `CORS_ORIGINS` - Comma-separated list of allowed origins

### Optional Variables

- `ANTHROPIC_API_KEY` - Anthropic API key (for Claude)
- `DEEPSEEK_API_KEY` - DeepSeek API key (for DeepSeek Coder)
- `RATE_LIMIT_PER_MINUTE` - Rate limit per minute (default: 60)
- `RATE_LIMIT_PER_HOUR` - Rate limit per hour (default: 1000)
- `RATE_LIMIT_PER_DAY` - Rate limit per day (default: 10000)
- `ENVIRONMENT` - Environment name (development/staging/production)

## Docker Deployment

### Development

```bash
docker-compose up -d
```

### Production

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop Services

```bash
docker-compose down
```

### Update Services

```bash
git pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Authentication

### Default Admin User

On first startup, a default admin user is created:
- Username: `admin`
- Password: Set via `ADMIN_PASSWORD` environment variable

**Important**: Change the admin password immediately after first login!

### Register New User

```bash
curl -X POST http://localhost:8010/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### Login

```bash
curl -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Use Token

```bash
curl http://localhost:8010/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Rate Limiting

Rate limits are applied per IP address or per user (if authenticated). Limits can be configured via environment variables:

- `RATE_LIMIT_PER_MINUTE` - Requests per minute
- `RATE_LIMIT_PER_HOUR` - Requests per hour
- `RATE_LIMIT_PER_DAY` - Requests per day

Rate limit headers are included in all responses:
- `X-RateLimit-Limit-Minute` - Limit per minute
- `X-RateLimit-Remaining-Minute` - Remaining requests
- `X-RateLimit-Reset-Minute` - Reset timestamp

## Security Checklist

- [ ] JWT secret key is strong and unique
- [ ] CORS origins are restricted to your domain(s)
- [ ] Admin password is changed from default
- [ ] API keys are secure and not exposed
- [ ] HTTPS is enabled (via reverse proxy)
- [ ] Rate limits are configured appropriately
- [ ] Environment variables are not committed to git
- [ ] Database files are backed up regularly

## Reverse Proxy (Nginx)

For production, use Nginx as a reverse proxy with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

### Health Checks

The application provides health check endpoints:

- `GET /` - Basic health check
- `GET /api/health` - Detailed health check

### Logs

View application logs:

```bash
# Docker logs
docker-compose logs -f backend

# Application logs (if logging to file)
tail -f logs/app.log
```

## Backup

### Database Backup

```bash
# Backup SQLite databases
cp .auth.db backups/auth-$(date +%Y%m%d).db
cp .memory.db backups/memory-$(date +%Y%m%d).db

# Backup vector database
tar -czf backups/vector-db-$(date +%Y%m%d).tar.gz .vector_db/
```

### Automated Backup Script

Create a cron job for daily backups:

```bash
0 2 * * * /path/to/backup-script.sh
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8010
# or
netstat -tulpn | grep 8010

# Kill process
kill -9 <PID>
```

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker-compose ps

# Restart container
docker-compose restart backend
```

### Authentication Not Working

1. Check JWT_SECRET_KEY is set
2. Verify token is being sent in Authorization header
3. Check token expiration
4. Verify user exists in database

### Rate Limiting Issues

1. Check rate limit configuration
2. Verify Redis is running (if using Redis)
3. Check rate limit headers in response

## Support

For issues and questions:
- GitHub Issues: https://github.com/Hruthik07/Bujji-Coder-AI/issues
- Documentation: See `docs/` folder
