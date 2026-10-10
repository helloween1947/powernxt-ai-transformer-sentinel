Phase 4 full implementation: incident triage, What-if forecasting, and genuine maintenance

This pull request completes Phase 4 technical implementation across Roles A, B, C, and D for PowerNXT Transformer Sentinel.

Target branch: feature/persona-phase3-combined-integration
Branch: feature/phase4-full-implementation
Base commit: a0689417efd0b674b93198eb537d940cb3547285

Scope of Changes:
- Person A (Backend & Integration): Verified PostgreSQL schema (19 tables, d006_combined_integration), authenticated operator session (/api/v1/operators/me), telemetry-to-incident worker processing loop, and maintenance task creation with strict foreign key linkage to incidents.
- Person B (Twin & Analytics): Validated Model 1.0.2 / 1.0.1 thermal differential calculation under constant-load assumptions, deterministic What-if scenario forecasting with zero worker state/job mutation, distinct analytic crossing statuses, and honest labeling of uncalibrated parameters as "Conditional healthy-model estimates".
- Person C (Frontend): Created OperatorAuthBar for Bearer token session management, BackendIncidents for stream-aware incident triage (event timeline, raw evidence inspector, versioned acknowledgement with UUIDv4 idempotency, and one-click task creation), BackendWhatIf for dual-scenario comparison with TrendChart visualization, and enhanced BackendMaintenance with dual-mode support for genuine incident-linked tasks. Updated main App navigation.
- Person D (Testing & Verification): Verified 351 backend tests (0 failures), 55 frontend tests (0 failures), clean ESLint (0 errors, 0 warnings), clean Vite build (121ms), executed 10-step automated E2E live integration probe (integration/verify_phase4_e2e.py), and captured headless Chrome browser render (docs/evidence/phase4-browser-ui.png).

Preservation & Safety:
- Zero disruption to long-running development stack (PostgreSQL on port 5433, FastAPI backend on 8000, Vite demo frontend on 3000).
- Historical Model 1.0.1 data, demo sample task workflows, and existing contracts remain completely intact.
- Machine-readable evidence: docs/evidence/phase4-evidence.json.
- Full reports: docs/phase4-implementation-report.md and docs/phase4-verification.md.

Human review and CI remain required. This PR is submitted for team review and must not be merged without teammate sign-offs.
