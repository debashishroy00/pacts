# PACTS v3.0 Docker Setup Guide

## Overview

PACTS v3.0 uses Docker Compose to run Postgres + Redis for memory & persistence. Due to Windows Docker Desktop networking limitations, we provide two execution modes:

1. **Containerized Runner** (Recommended for Windows) - Runs PACTS inside Docker
2. **Host Execution** (Works on Linux/WSL2) - Runs PACTS from host machine

---

## Option 1: Containerized Runner (Recommended for Windows)

### Why Use This?

- ✅ Bypasses Windows Docker networking issues entirely
- ✅ Consistent execution environment across all platforms
- ✅ Production-ready deployment pattern
- ✅ Direct service-to-service communication (no localhost)

### Quick Start

```bash
# 1. Ensure ANTHROPIC_API_KEY is in .env
cat .env | grep ANTHROPIC_API_KEY

# 2. Start infrastructure + runner
docker-compose --profile runner up --build

# 3. Watch logs
docker-compose logs -f pacts-runner

# 4. Run specific test (edit docker-compose.yml)
# Uncomment and modify the command line:
# command: python -m backend.cli.main test --req salesforce_opportunity_postlogin --headed=false
```

### Configuration

The `pacts-runner` service automatically connects to:
- **Database**: `postgres:5432` (service name, not localhost)
- **Redis**: `redis:6379`
- **Memory**: Enabled by default
- **Model**: Haiku 3.5 (cost-effective)

### Custom Test Execution

```bash
# Run specific requirement
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req wikipedia_search

# Run with headed browser (requires X11 forwarding on Linux)
docker-compose run --rm pacts-runner \
  python -m backend.cli.main test --req github_search --headed

# Run 5-loop cache validation
for i in {1..5}; do
  echo "=== Loop $i ==="
  docker-compose run --rm pacts-runner \
    python -m backend.cli.main test --req wikipedia_search
done
```

### View Results

```bash
# Check cache metrics
docker exec pacts-redis redis-cli KEYS "metrics:*"
docker exec pacts-redis redis-cli GET "metrics:selector_cache:cache_hit_redis"

# Query database
docker exec pacts-postgres psql -U pacts -d pacts -c \
  "SELECT * FROM run_summary ORDER BY start_time DESC LIMIT 5;"

# View artifacts (mounted to host)
ls -la ./artifacts/
ls -la ./generated_tests/
```

---

## Option 2: Host Execution (Linux/WSL2/Mac)

### Prerequisites

This mode requires working localhost↔Docker connectivity. **Does NOT work on Windows Docker Desktop due to port forwarding issues.**

### Setup

```bash
# 1. Start infrastructure only
docker-compose up -d postgres redis

# 2. Verify connectivity
python test_db_connection.py

# 3. Run tests from host
python -m backend.cli.main test --req wikipedia_search --headed
```

### Environment Configuration

Ensure `.env` has:
```bash
POSTGRES_HOST=127.0.0.1  # or localhost
POSTGRES_PORT=5432
POSTGRES_USER=pacts
POSTGRES_PASSWORD=pacts
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
ENABLE_MEMORY=true
```

---

## Troubleshooting

### Windows Docker Desktop: "password authentication failed"

**Symptom**: asyncpg/psycopg2 connections fail with password auth error, but no connection appears in Postgres logs.

**Root Cause**: Windows Docker Desktop port forwarding doesn't properly relay SCRAM-SHA-256 authentication packets.

**Solution**: Use containerized runner (Option 1).

**Diagnosis**:
```powershell
# Verify port is open
Test-NetConnection 127.0.0.1 -Port 5432
# Should show TcpTestSucceeded: True

# But connection still fails - this confirms Windows networking issue
python test_db_connection.py
```

### Container Build Fails

```bash
# Clear cache and rebuild
docker-compose build --no-cache pacts-runner

# Check Dockerfile syntax
docker build -f Dockerfile.runner -t pacts-runner-test .
```

### Database Connection Refused

```bash
# Check containers are healthy
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs redis

# Manual connection test
docker exec pacts-postgres psql -U pacts -d pacts -c "SELECT 1"
```

### Cache Not Working

```bash
# Verify memory is enabled
docker-compose run --rm pacts-runner env | grep ENABLE_MEMORY
# Should show: ENABLE_MEMORY=true

# Check Redis connection
docker exec pacts-redis redis-cli PING
# Should show: PONG

# Check database schema
docker exec pacts-postgres psql -U pacts -d pacts -c "\dt"
# Should show: runs, run_steps, artifacts, selector_cache, heal_history, metrics
```

---

## Architecture

### Network Flow (Containerized)

```
┌─────────────────┐
│  pacts-runner   │
│  (Python app)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌────────┐
│postgres │ │ redis  │
│  :5432  │ │ :6379  │
└─────────┘ └────────┘
    │         │
    └─────┬───┘
          │
  pacts-network (bridge)
```

All communication stays inside Docker network - no localhost involved!

### Network Flow (Host Execution)

```
┌──────────────────┐
│  Host Machine    │
│  (Windows/WSL2)  │
│                  │
│  Python app      │
│  ↓               │
│  127.0.0.1:5432 ─┼──→ Port Forwarding → postgres:5432
│  127.0.0.1:6379 ─┼──→ Port Forwarding → redis:6379
└──────────────────┘
```

Requires working Docker Desktop port forwarding (broken on Windows for SCRAM-SHA-256).

---

## Database Schema

Tables created automatically on first startup:

- **runs**: Test execution metadata
- **run_steps**: Step-level execution details
- **artifacts**: Screenshots, HTML snapshots
- **selector_cache**: Persistent POM cache (7-day retention)
- **heal_history**: Healing strategy success tracking
- **metrics**: Aggregated analytics

Views:
- **run_summary**: Quick test run overview
- **selector_cache_stats**: Cache hit rate analysis
- **healing_success_rate**: Best healing strategies

---

## Production Deployment

For production, use containerized runner with:

1. **Environment secrets**: Use Docker secrets instead of .env
2. **Health checks**: Already configured in docker-compose.yml
3. **Resource limits**: Add memory/CPU limits
4. **Persistent volumes**: Mounted to host filesystem
5. **Logging**: Use Docker logging drivers (json-file, syslog, etc.)

Example production compose snippet:
```yaml
pacts-runner:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
    restart_policy:
      condition: on-failure
      max_attempts: 3
```

---

## Next Steps

1. ✅ Start infrastructure: `docker-compose up -d`
2. ✅ Run first test: `docker-compose --profile runner up --build`
3. ⏳ Run 5-loop cache validation
4. ⏳ Integrate HealHistory with OracleHealer
5. ⏳ Integrate RunStorage with pipeline
6. ⏳ Add LangSmith telemetry (Phase 4)

---

## Support

**Issue**: Connection failures on Windows
**Fix**: Use containerized runner (Option 1)

**Issue**: Playwright browser not found
**Fix**: `docker-compose build --no-cache pacts-runner`

**Issue**: Out of memory
**Fix**: Increase Docker Desktop memory (Settings → Resources → 8GB+)
