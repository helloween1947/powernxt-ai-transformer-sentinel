# Frontend Monitoring & Twin Visualization Dashboard

**Owner**: Person C (Frontend Engineer)

## Scope & Responsibilities
- Real-time transformer telemetry monitoring dashboard.
- 3-Phase electrical waveform & load balance visual charts.
- Thermal behavior and anomaly indicator views.
- "What-If" scenario simulator interface (load manipulation, ambient stress testing).
- Alerting & maintenance notification views.

## Backend Integration
- **API Base URL**: `http://localhost:8000`
- **Interactive Documentation**: `http://localhost:8000/docs`
- **Health Verification**:
  - `GET /health/live`: Server process check.
  - `GET /health/ready`: Database connectivity check.
- **CORS Configuration**:
  - Development ports `http://localhost:3000` (React/Next) and `http://localhost:5173` (Vite) are pre-configured in `backend/app/config.py`.
