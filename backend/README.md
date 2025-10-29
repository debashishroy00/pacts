# PACTS Backend

Python backend for PACTS (Production-Ready Autonomous Context Testing System).

## Architecture

6-agent system orchestrated by LangGraph 1.0:
1. **Planner** - Parse Excel requirements → intents
2. **POMBuilder** - Find-First discovery with multi-strategy approach
3. **Generator** - Create test.py files from verified selectors
4. **Executor** - Execute tests with 5-point actionability gate
5. **OracleHealer** - Autonomous test repair
6. **VerdictRCA** - Reporting and root cause analysis

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for Postgres + Redis)
- Git

## Quick Start

### 1. Set up Python environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Start databases

```bash
# From project root
cd ../docker
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

### 3. Configure environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# At minimum, set:
# - LANGSMITH_API_KEY (from https://smith.langchain.com/)
# - AWS credentials (for Bedrock Claude models)
```

### 4. Run database migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Run migrations
alembic upgrade head
```

### 5. Run the API server (when ready)

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Access:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Project Structure

```
backend/
├── graph/          # LangGraph orchestration
├── agents/         # 6 agents
├── runtime/        # Playwright browser automation
├── memory/         # Postgres + Redis persistence
├── telemetry/      # LangSmith observability
├── api/            # FastAPI REST endpoints
├── cli/            # Command-line interface
├── tests/          # Unit, integration, e2e tests
└── alembic/        # Database migrations
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_planner.py

# Run integration tests
pytest tests/integration/

# Run e2e tests
pytest tests/e2e/
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8 .

# Type check
mypy .
```

### CLI Usage (when implemented)

```bash
# Run test from Excel requirement
python -m cli.main test --req REQ-001

# With options
python -m cli.main test --req REQ-001 --headless true

# Show help
python -m cli.main --help
```

## API Endpoints (Planned)

### Requirements
- `GET /api/requirements` - List all requirements
- `POST /api/requirements/upload` - Upload Excel file
- `GET /api/requirements/{req_id}` - Get requirement details
- `PUT /api/requirements/{req_id}` - Update requirement
- `DELETE /api/requirements/{req_id}` - Delete requirement

### Test Execution
- `POST /api/runs/trigger` - Trigger test run
- `GET /api/runs` - List test runs
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/status` - Get run status
- `WS /ws/runs/{run_id}` - WebSocket for real-time updates

### Verdicts
- `GET /api/verdicts/{req_id}` - Get verdict for requirement
- `GET /api/verdicts/{req_id}/metrics` - Get metrics
- `GET /api/verdicts/{req_id}/rca` - Get RCA report

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/dashboard/trends` - Historical trends

### Health
- `GET /api/health` - Service health check

## Environment Variables

See [.env.example](.env.example) for full list of configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `LANGSMITH_API_KEY` - LangSmith observability API key
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS Bedrock credentials
- `HEADLESS` - Run browser in headless mode (true/false)

## Troubleshooting

### Playwright installation issues

```bash
# If Playwright browsers fail to install
playwright install --force

# Install system dependencies (Linux)
playwright install-deps
```

### Database connection errors

```bash
# Check if Postgres is running
docker-compose ps postgres

# View Postgres logs
docker-compose logs postgres

# Restart Postgres
docker-compose restart postgres
```

### Redis connection errors

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping  # Should return PONG
```

### Module import errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

## Documentation

- [Architecture Blueprint](../PACTS-Build-Blueprint-v3.4.md)
- [API Documentation](../docs/api/)
- [Feasibility Analysis](../docs/FEASIBILITY-ANALYSIS.md)

## License

MIT License - see [LICENSE](../LICENSE) for details
