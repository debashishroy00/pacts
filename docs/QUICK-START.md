# PACTS v3.0 - Quick Start Guide

## Prerequisites

✅ Docker Desktop running
✅ Docker Compose available
✅ Port 5432 (Postgres) and 6379 (Redis) available

## Quick Start (3 Commands)

### 1. Start Infrastructure
```bash
docker-compose up -d postgres redis
```

**Wait 10 seconds** for database initialization, then verify:
```bash
docker-compose ps
```

Should show:
- `pacts-postgres` - healthy
- `pacts-redis` - healthy

### 2. Run a Test
```bash
# Simple test
docker-compose run --rm pacts-runner python -m backend.cli.main test --req wikipedia_search

# With caching (5 loops for validation)
docker-compose run --rm pacts-runner python -m backend.cli.main test --loops 5 --req wikipedia_search
```

### 3. Check Logs
```bash
# Postgres logs
docker-compose logs postgres

# Redis logs
docker-compose logs redis

# Application logs (if running detached)
docker-compose logs pacts-runner
```

## Cache Validation Test (Target: 80% Hit Rate)

### Run 5-Loop Test
```bash
docker-compose run --rm pacts-runner python -m backend.cli.main test --loops 5 --req wikipedia_search
```

**What to Look For:**
- Loop 1: All cache misses (building cache)
- Loops 2-5: High cache hit rates (target 80%+)
- Drift detection: Monitors for selector changes
- Auto-healing: Falls back to discovery on cache misses

## Troubleshooting

### Database Connection Failed
```bash
# Check if Postgres is healthy
docker-compose ps postgres

# View Postgres logs
docker-compose logs postgres

# Restart Postgres
docker-compose restart postgres
```

### Redis Connection Failed
```bash
# Check if Redis is healthy
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Container Build Issues
```bash
# Clean rebuild
docker-compose build --no-cache pacts-runner

# Check disk space
docker system df

# Clean up old images
docker system prune -a
```

## Advanced Usage

### Run Specific Test
```bash
# Replace 'wikipedia_search' with your requirement name
docker-compose run --rm pacts-runner python -m backend.cli.main test --req <your_requirement>
```

### Run with Debug Logging
```bash
docker-compose run --rm pacts-runner env CACHE_DEBUG=true python -m backend.cli.main test --req wikipedia_search
```

### Interactive Shell in Container
```bash
# Bash shell
docker-compose run --rm pacts-runner bash

# Python REPL with imports
docker-compose run --rm pacts-runner python
```

### Database Management Tools

#### pgAdmin (Web UI)
```bash
# Start with tools profile
docker-compose --profile tools up -d pgadmin

# Access at: http://localhost:5050
# Email: admin@pacts.local
# Password: admin
```

#### RedisInsight (Web UI)
```bash
# Start with tools profile
docker-compose --profile tools up -d redis-insight

# Access at: http://localhost:8001
```

## Cleanup

### Stop Services
```bash
docker-compose down
```

### Remove Volumes (WARNING: Deletes all data!)
```bash
docker-compose down -v
```

### Full Cleanup
```bash
# Stop everything and remove volumes
docker-compose down -v

# Remove images
docker rmi pacts-pacts-runner postgres:15 redis:7-alpine
```

## Status Check

### Quick Health Check
```bash
# Check all services
docker-compose ps

# Test database from container
docker-compose run --rm pacts-runner python -c "import asyncpg, asyncio; asyncio.run(asyncpg.connect('postgresql://pacts:pacts@postgres:5432/pacts')); print('OK!')"

# Test Redis from container
docker-compose run --rm pacts-runner python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping(); print('OK!')"
```

## Next Steps

1. ✅ **Infrastructure Running** - Postgres + Redis
2. ⏳ **Run Cache Validation** - 5-loop test
3. ⏳ **Integrate HealHistory** - Connect with OracleHealer
4. ⏳ **Integrate RunStorage** - Connect with pipeline
5. ⏳ **Production Testing** - Real-world requirements

---

**Pro Tips:**
- Always wait 10s after `docker-compose up` for database initialization
- Use `--rm` flag to auto-remove containers after they exit
- Check logs with `docker-compose logs -f <service>` for real-time output
- Use `docker-compose run` for one-off commands, `up` for services
