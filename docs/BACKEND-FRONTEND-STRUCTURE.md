# Backend/Frontend Architecture Decision

**Date**: October 28, 2025
**Status**: ✅ APPROVED
**Decision**: Separate backend/ and frontend/ folders for full-stack application

---

## Rationale

### User Requirement
**"In future phases, we are planning to build a UI in Angular 18 where users can interact. So won't it make sense to create folder structure as backend and frontend?"**

**Answer**: Absolutely YES! ✅

---

## Architecture Benefits

### 1. Clear Separation of Concerns
- **Backend** (`backend/`): Python/FastAPI microservices, agents, orchestration
- **Frontend** (`frontend/`): Angular 18 UI, user interactions

### 2. Independent Development
- Backend team can work in `backend/` without affecting frontend
- Frontend team can work in `frontend/` without affecting backend
- Clear API contract between layers

### 3. Independent Deployment
- Deploy backend separately (Docker, Kubernetes, etc.)
- Deploy frontend separately (Nginx, CDN, etc.)
- Scale independently based on load

### 4. Technology Isolation
- **Backend**: Python 3.11+, FastAPI, Playwright, LangGraph
- **Frontend**: Angular 18, TypeScript, Angular Material
- No technology mixing or conflicts

### 5. Easier Onboarding
- Backend developers focus on `backend/`
- Frontend developers focus on `frontend/`
- Clear project boundaries

---

## Folder Structure

### Root Level
```
pacts/
├── backend/          # Python backend
├── frontend/         # Angular 18 frontend
├── docker/           # Docker configurations
├── generated_tests/  # Output from Generator agent
├── docs/             # Documentation
└── README.md
```

### Backend Structure
```
backend/
├── graph/            # LangGraph orchestration
├── agents/           # 6 agents (Planner, POMBuilder, Generator, Executor, OracleHealer, VerdictRCA)
├── runtime/          # Playwright browser automation
├── memory/           # Postgres + Redis persistence
├── telemetry/        # LangSmith observability
├── api/              # FastAPI REST endpoints
│   ├── routes/       # API routes
│   └── models/       # Pydantic models
├── cli/              # Command-line interface
├── tests/            # Unit, integration, e2e tests
├── alembic/          # Database migrations
├── requirements.txt
├── pyproject.toml
└── .env.example
```

### Frontend Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── features/
│   │   │   ├── dashboard/       # Main dashboard
│   │   │   ├── requirements/    # Requirements CRUD
│   │   │   ├── test-runs/       # Test execution UI
│   │   │   ├── verdicts/        # Verdict viewing
│   │   │   └── settings/        # App settings
│   │   ├── core/
│   │   │   ├── services/        # API services
│   │   │   ├── guards/          # Route guards
│   │   │   └── interceptors/    # HTTP interceptors
│   │   └── shared/
│   │       ├── components/      # Reusable UI components
│   │       └── models/          # TypeScript interfaces
│   ├── assets/
│   └── environments/
├── angular.json
├── package.json
└── tsconfig.json
```

---

## Communication Layer

### REST APIs (Backend → Frontend)

**Backend exposes FastAPI REST endpoints:**

```python
# backend/api/routes/requirements.py
@router.get("/api/requirements")
async def list_requirements():
    ...

@router.post("/api/requirements/upload")
async def upload_requirement(file: UploadFile):
    ...

@router.post("/api/runs/trigger")
async def trigger_test_run(req_id: str):
    ...

@router.get("/api/verdicts/{req_id}")
async def get_verdict(req_id: str):
    ...
```

**Frontend consumes via Angular services:**

```typescript
// frontend/src/app/core/services/api.service.ts
@Injectable({providedIn: 'root'})
export class ApiService {
  constructor(private http: HttpClient) {}

  listRequirements() {
    return this.http.get<Requirement[]>('/api/requirements');
  }

  uploadRequirement(file: File) {
    return this.http.post('/api/requirements/upload', formData);
  }

  triggerTestRun(reqId: string) {
    return this.http.post(`/api/runs/trigger`, { req_id: reqId });
  }

  getVerdict(reqId: string) {
    return this.http.get<Verdict>(`/api/verdicts/${reqId}`);
  }
}
```

### WebSocket (Real-time Updates)

**Backend WebSocket endpoint:**
```python
# backend/api/main.py
from fastapi import WebSocket

@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    # Send real-time updates during test execution
    while execution_running:
        status = get_execution_status(run_id)
        await websocket.send_json(status)
        await asyncio.sleep(1)
```

**Frontend WebSocket service:**
```typescript
// frontend/src/app/core/services/websocket.service.ts
@Injectable({providedIn: 'root'})
export class WebSocketService {
  private socket: WebSocket;

  connectToRun(runId: string): Observable<RunStatus> {
    this.socket = new WebSocket(`ws://localhost:8000/ws/runs/${runId}`);
    return new Observable(observer => {
      this.socket.onmessage = (event) => {
        observer.next(JSON.parse(event.data));
      };
    });
  }
}
```

---

## Development Workflow

### Phase 1 (Weeks 1-2): Backend Only
```bash
cd backend/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Access: http://localhost:8000/docs (FastAPI Swagger UI)

### Phase 3 (Weeks 5-8): Add Frontend
```bash
# Terminal 1: Backend
cd backend/
uvicorn api.main:app --reload

# Terminal 2: Frontend
cd frontend/
npm install
ng serve
```

Access:
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Deployment
```bash
docker-compose up -d
```

Access: http://localhost (Nginx reverse proxy)

---

## Docker Configuration

### docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: pacts
      POSTGRES_USER: pacts
      POSTGRES_PASSWORD: pacts

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://pacts:pacts@postgres:5432/pacts
      REDIS_URL: redis://redis:6379

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend.Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
```

### backend.Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### frontend.Dockerfile
```dockerfile
FROM node:20 AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build --prod

FROM nginx:alpine
COPY --from=builder /app/dist/pacts-ui /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## API Contract (OpenAPI/Swagger)

### Backend Auto-Generated Docs
FastAPI automatically generates OpenAPI schema at:
- JSON: http://localhost:8000/openapi.json
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend Type Generation
Generate TypeScript interfaces from OpenAPI schema:

```bash
# Install OpenAPI generator
npm install -g @openapitools/openapi-generator-cli

# Generate TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-angular \
  -o frontend/src/app/generated-api
```

---

## Phase Roadmap

### Phase 1 (Weeks 1-2): Backend MVP
- ✅ `backend/` folder structure
- ✅ 6 agents implemented
- ✅ FastAPI REST APIs
- ✅ CLI interface
- ✅ Postgres + Redis
- ✅ LangSmith telemetry

**Access**: CLI + API (Swagger UI)

### Phase 2 (Weeks 3-4): Enhanced Backend
- Advanced healing strategies
- Confidence scoring improvements
- Performance optimizations

**Access**: CLI + API (Swagger UI)

### Phase 3 (Weeks 5-8): Angular Frontend
- ✅ `frontend/` folder structure
- Dashboard, requirements, test runs, verdicts
- Real-time WebSocket updates
- Angular Material UI

**Access**: Full web UI + CLI

### Phase 4 (Weeks 9-12): Enterprise
- Multi-tenant support
- User authentication/authorization
- Advanced analytics
- Integration marketplace

**Access**: Full enterprise platform

---

## Technology Stack Summary

### Backend (`backend/`)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11+ | Core runtime |
| API Framework | FastAPI | REST APIs |
| Orchestration | LangGraph 1.0 | Agent workflow |
| Browser Automation | Playwright | Test execution |
| Database | PostgreSQL 15+ | State persistence |
| Cache | Redis 7+ | Working memory |
| Observability | LangSmith | Traces & telemetry |

### Frontend (`frontend/`)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Angular 18 | UI framework |
| Language | TypeScript 5+ | Type-safe development |
| UI Library | Angular Material | Component library |
| State | NgRx Signals | Reactive state |
| Charts | ngx-charts | Data visualization |
| Real-time | WebSocket | Live updates |

### Infrastructure (`docker/`)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containers | Docker | Service isolation |
| Orchestration | Docker Compose | Local dev environment |
| Database | PostgreSQL | Relational data |
| Cache | Redis | In-memory cache |
| Reverse Proxy | Nginx | Frontend serving |

---

## Benefits Summary

### ✅ For Development
- Clear project boundaries
- Independent team workflows
- Technology isolation
- Easier onboarding

### ✅ For Deployment
- Independent scaling
- Backend: Scale for agent workloads
- Frontend: Scale for user traffic
- Separate release cycles

### ✅ For Maintenance
- Backend changes don't affect frontend
- Frontend changes don't affect backend
- API versioning for compatibility
- Clear upgrade paths

### ✅ For Testing
- Backend: Unit, integration, e2e tests
- Frontend: Component, service, e2e tests
- API contract testing
- Independent CI/CD pipelines

---

## Files Updated

1. ✅ **PACTS-Build-Blueprint-v3.4.md**
   - Section 3: Updated repository layout
   - Section 14: Added Phase 3 (Angular frontend)
   - Section 14.1: New section for Angular frontend details

2. ✅ **README.md**
   - Project Structure: Updated to show backend/frontend separation
   - Roadmap: Added Phase 3 (Angular 18 Frontend) and Phase 4 (Enterprise)

3. ✅ **This Document**
   - Comprehensive backend/frontend architecture guide

---

## Next Steps

1. ✅ Architecture finalized
2. ✅ Documentation updated
3. ⏭️ Create `backend/` folder structure
4. ⏭️ Create `frontend/` folder structure (Phase 3)
5. ⏭️ Set up Docker configuration
6. ⏭️ Begin Phase 1 backend implementation

---

**Status**: ✅ Backend/Frontend architecture approved and documented.

**Ready to build**: Phase 1 backend with future-proof structure for Angular frontend.
