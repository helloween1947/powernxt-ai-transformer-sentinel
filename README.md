# Transformer Sentinel

An explainable digital twin and operational intelligence platform for electrical power transformers. Sentinel ingests high-frequency 3-phase electrical and physical sensor telemetry, monitors real-time operating conditions, predicts thermal dynamics, flags anomalies, and enables interactive "what-if" scenario evaluation.

---

## Implemented scope and integration status

Status reviewed against main `744c765` and candidate `4125237` on 10 October 2026. Source availability, passing tests, and running deployments are distinct facts. Consult exact commits and evidence files in `docs/`; laptop-local IDs are not shared deployment IDs.

- **Implemented on main:** registered assets and immutable configurations; transactional telemetry/deduplication and simulator; ordered durable analytics worker/result APIs; C's stored electrical/thermal dashboard; sample-backed maintenance tasks/history and separate sample maintenance screen.
- **Implemented on candidate branch (`feature/phase4-full-implementation`):** single migration head `d006_combined_integration` (19 tables); Model 1.0.2 worker adoption with epoch handover; immutable What-if scenario forecasting with automatic 1.0.1/1.0.2 dispatch; operator Bearer token authentication (`/api/v1/operators/me`); stream-aware incident triage console (`BackendIncidents`); What-if comparison cockpit (`BackendWhatIf`); dual-mode maintenance management (`BackendMaintenance`); and 10-step automated E2E integration probes.
- **Running in development stack:** development PostgreSQL on port 5433 (running `d004_worker_maintenance`, 10 tables, 25 readings, 25 Model 1.0.1 results); development backend on port 8000; Model 1.0.1 worker; demo frontend on port 3000. Upgraded stack is fully rehearsed on isolated ports (55435/8802) and documented in `docs/phase5-upgrade-plan.md` awaiting execution authorization.
- **Conservative adopted physical model:** magnitude electrical quantities and IEEE exponential top-oil evolution/residual. Default coefficients are assumed or nameplate; bootstrap/gap values remain unavailable. What-if forecasts are explicitly labeled *"Conditional healthy-model estimates under constant-load assumptions"*. No calibrated fault score, winding hotspot, health/confidence, RUL, PF/sequences, or physical cooling intervention is claimed.

Current guides and evidence:

| Area | Guide / Verification / Contract |
|---|---|
| **Phase 6 Acceptance Matrix** | [Final Acceptance & Status Matrix](docs/phase6-final-acceptance.md), [Evidence Manifest](docs/phase6-evidence.json) |
| **Mentor / Judge Demonstration** | [Mentor Demo Guide & Script](docs/mentor-demo-guide.md) |
| **Team Final Handoff** | [Team Final Handoff](docs/team-final-handoff.md) |
| **Development Upgrade Plan** | [Phase 5 Upgrade Plan](docs/phase5-upgrade-plan.md), [Rehearsal Record](docs/phase5-rehearsal-verification.md) |
| **Phase 4 Full Implementation** | [Implementation Report](docs/phase4-implementation-report.md), [Verification Record](docs/phase4-verification.md) |
| **Asset and Telemetry Contracts** | [Asset registry](backend/docs/asset-registry.md), [Telemetry contract](docs/contracts/telemetry-contract.md) |
| **Adopted Analytics & Models** | [Result API contract](docs/contracts/analytics-contract.md), [Worker policy](docs/analytics-worker.md) |
| **Main Sample Maintenance** | [Combined verification](docs/integration-verification.md), [Workflow](docs/persond-maintenance-workflow.md) |
| **Incident Design & Contracts** | [Genuine incident contract](analytics/docs/genuine-incident-integration-contract.md), [Incident test evidence](docs/incident-registry-evidence.json) |

Historical reports remain intact. Source review and passing CI are not evidence of teammate approval, trusted device identity, field calibration, or shared deployment.

---

## Team Ownership

| Teammate | Focus Area | Owned Directories |
| :--- | :--- | :--- |
| **Person A** | Backend, Ingestion, Database, Simulator, APIs | `backend/`, `data/sample/` |
| **Person B** | Digital Twin, Physical Models, Anomaly Detection, Forecasts | `analytics/` |
| **Person C** | Frontend, Monitoring Dashboard, Charts, What-If UI | `frontend/` |
| **Person D** | Integration, Testing, Deployment, Maintenance, Docs | `integration/`, `docs/`, `.github/` |

---

## Directory Guide

```text
powernxt-ai-transformer-sentinel/
├── .github/
│   └── workflows/
│       └── ci.yaml              # GitHub Actions CI workflow
├── analytics/                   # Person B: Electrical & thermal twin models
│   └── README.md
├── backend/                     # Person A: FastAPI application & database
│   ├── app/
│   │   ├── api/                 # Health, assets, telemetry, analytics, maintenance APIs
│   │   ├── db/                  # SQLAlchemy 2 engine, sessions, base model
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic (asset registry, ingestion)
│   │   ├── simulator/           # Sensor telemetry simulator
│   │   ├── workers/             # Background ingestion & streaming tasks
│   │   ├── config.py            # Pydantic settings & logging
│   │   └── main.py              # FastAPI application entrypoint
│   ├── migrations/              # Alembic database migration scripts
│   ├── tests/                   # Pytest test suite
│   ├── docs/                    # Backend notes and references
│   ├── alembic.ini              # Alembic database configuration
│   ├── Dockerfile               # Backend container definition
│   ├── .dockerignore            # Container build exclusions
│   ├── requirements.txt         # Production backend dependencies
│   └── requirements-dev.txt     # Test & development dependencies
├── data/
│   └── sample/                  # Sample telemetry files (no fault labels)
├── docs/
│   ├── contracts/               # Shared cross-team interface contracts
│   │   ├── telemetry-contract.md
│   │   ├── analytics-contract.md
│   │   └── event-contract.md
│   └── setup-verification.md    # Automated & manual setup validation audit
├── frontend/                    # Person C: Twin dashboard & visualizations
│   └── README.md
├── integration/                 # Person D: End-to-end integration & maintenance
│   └── README.md
├── compose.yaml                 # Docker Compose multi-service definition
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git exclusions (credentials, venv, caches)
├── pytest.ini                   # Pytest configuration
├── CONTRIBUTING.md              # Team workflow & collaboration guide
└── README.md                    # Project documentation
```

---

## Windows Prerequisites

Ensure the following tools are available on your Windows system:
1. **Git for Windows** (v2.40+)
2. **Python** (v3.11, 3.12, 3.13, or 3.14)
   - Verify via PowerShell: `py --version`
3. **Docker Desktop for Windows** (Optional for local Windows Python mode; required for Compose mode)
   - Ensure WSL 2 backend is enabled in Docker Desktop settings.
4. **PowerShell** (Default in Windows 10/11)

---

## Step-by-Step Setup Guide (Windows / PowerShell)

All commands below are designed to run in **PowerShell**. The working directory is stated before each group.

### 1. Clone the Repository
Open PowerShell and navigate to your desired parent workspace:
```powershell
# Directory: Workspace parent folder (e.g., C:\Projects)
git clone https://github.com/helloween1947/powernxt-ai-transformer-sentinel.git
cd powernxt-ai-transformer-sentinel
```

### 2. Prepare Environment Configuration
Copy the configuration template:
```powershell
# Directory: Repository root (powernxt-ai-transformer-sentinel)
Copy-Item .env.example .env
```

> **Note on Database Hostnames**:
> - **Local Windows Python**: Use `localhost` (pre-configured in `.env` default).
> - **Docker Compose**: Uses the internal service hostname `db`.

### 3. Create Virtual Environment & Install Dependencies
We use the virtual environment's Python directly without requiring shell script activation:
```powershell
# Directory: Repository root (powernxt-ai-transformer-sentinel)
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

### 4. Running the Test Suite
Verify your installation immediately:
```powershell
# Directory: Repository root (powernxt-ai-transformer-sentinel)
.\.venv\Scripts\pytest.exe backend/tests -v
```

---

## Running the Application

### Option A: Local Windows Python (Recommended for Backend Dev)

1. **Start PostgreSQL**:
   If Docker is installed:
   ```powershell
   # Directory: Repository root
   docker compose up -d db
   ```
   *(Or connect to any existing local PostgreSQL instance with credentials matching `.env`)*

2. **Start the FastAPI Backend**:
   ```powershell
   # Directory: Repository root
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Option B: Full Docker Compose Environment

If Docker Desktop is running, launch both PostgreSQL and Backend inside containers:
```powershell
# Directory: Repository root
docker compose up -d
```

---

## API Endpoints & Health Verification

Once the backend is running, verify via browser or `curl`:

| Resource | URL | Expected Response | Description |
| :--- | :--- | :--- | :--- |
| **Liveness Check** | [http://localhost:8000/health/live](http://localhost:8000/health/live) | `{"status":"live",...}` (HTTP 200) | Process running; no DB check |
| **Readiness Check** | [http://localhost:8000/health/ready](http://localhost:8000/health/ready) | `{"status":"ready",...}` (HTTP 200) | Probes PostgreSQL with `SELECT 1` |
| **Interactive Docs**| [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI | Live API explorer |
| **ReDoc UI** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc Documentation | Formatted API spec |

---

## Database Migrations (Alembic)

When Person A adds database models in `backend/app/db/`:

```powershell
# Directory: Repository root

# 1. Generate new migration script from SQLAlchemy metadata:
.\.venv\Scripts\alembic.exe -c backend/alembic.ini revision --autogenerate -m "describe_changes"

# 2. Apply pending migrations:
.\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head

# 3. Roll back one revision if needed:
.\.venv\Scripts\alembic.exe -c backend/alembic.ini downgrade -1
```

---

## Shutdown & Teardown

To cleanly stop the services:

- **Local Python Server**: Press `Ctrl + C` in the PowerShell window running Uvicorn.
- **Docker Compose**:
  ```powershell
  # Directory: Repository root
  docker compose down
  ```
  *(Note: This preserves database volumes. Do not add `-v` unless you intentionally want to delete stored database state).*

---

## Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Docker not recognized** (`docker: The term 'docker' is not recognized`) | Docker Desktop is not installed or not in Windows PATH | Install Docker Desktop for Windows or run backend locally using Windows Python and external PostgreSQL. |
| **Port 8000 or 5432 already in use** | Another service (e.g., local Postgres or old Python process) occupies port | Run `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess` in PowerShell to find and stop the process, or edit port mappings in `.env` and `compose.yaml`. |
| **Database Connection Refused** (`/health/ready` returns 503) | PostgreSQL container is stopped or still starting | Ensure container is up (`docker compose ps`). Wait 5 seconds for PostgreSQL healthcheck to become healthy. Verify `.env` credentials match. |
| **`ModuleNotFoundError: No module named 'backend'`** | Working directory or pythonpath not set | Always execute commands from repository root, or ensure `pytest.ini` is present in root. |
| **Git Authentication Prompt** | GitHub permissions or credentials not cached | Run `gh auth login` in terminal or authenticate via Git Credential Manager browser window. |

## Durable analytics worker (feature)

The opt-in PostgreSQL worker stores real electrical/top-oil results with lease recovery and transactional state updates. Apply the reviewed worker migration before starting the updated API and worker. See [startup, ordering and model limitations](docs/analytics-worker.md), [result APIs](docs/contracts/analytics-contract.md), and [isolated verification / Windows commands](docs/analytics-worker-windows.md). No analytics runs in API startup or requests.
