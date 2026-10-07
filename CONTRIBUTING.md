# Contributing to PowerNXT Transformer Sentinel

Welcome to the team! This document outlines our collaborative workflow, branch strategies, code review standards, and repository safety policies.

---

## 1. Team Ownership & Responsibilities

| Role | Teammate | Focus Area | Primary Directories |
| :--- | :--- | :--- | :--- |
| **Person A** | Backend Lead | Backend architecture, asset registry, ingestion, database, simulator, live APIs | `backend/`, `data/sample/` |
| **Person B** | Twin & Analytics | Electrical & thermal physical models, anomaly detection, forecasts | `analytics/` |
| **Person C** | Frontend Lead | Twin monitoring dashboard, charts, what-if scenario UI | `frontend/` |
| **Person D** | Integration & QA | End-to-end integration, maintenance workflows, CI/CD, documentation, demo scripts | `integration/`, `docs/`, `.github/` |

### Coordination for Shared Files
Shared configuration files (`compose.yaml`, `.env.example`, `README.md`, `CONTRIBUTING.md`, and contracts in `docs/contracts/`) require cross-teammate awareness. Always discuss contract revisions with impacted owners before modifying shared interfaces.

---

## 2. Git Workflow & Branching Guidelines

1. **Keep Default Branch (`main`) Green & Protected**:
   - Never push directly to `main`.
   - All contributions must land on `main` via reviewed Pull Requests (PRs).

2. **Branch Naming Standard**:
   - Create focused feature branches named according to purpose and role:
     - `feature/<person>-<short-description>` (e.g., `feature/personb-thermal-model`)
     - `chore/<short-description>` (e.g., `chore/team-repository-setup`)
     - `fix/<short-description>` (e.g., `fix/cors-origin-header`)

3. **Updating the Default Branch Before New Work**:
   Before creating a new feature branch, ensure your local `main` is current:
   ```powershell
   git checkout main
   git pull origin main
   git checkout -b feature/my-new-task
   ```

4. **Small, Atomic Commits**:
   - Write clear, imperative commit messages (e.g., `Add top-oil thermal prediction function`).
   - Group related modifications together; avoid bundling disparate features in a single commit.

5. **Pull Requests & Peer Review**:
   - Target PRs into `main`.
   - Require **at least one teammate review** and approval before merging.
   - All automated CI checks in `.github/workflows/ci.yaml` must pass.

---

## 3. Security & Credential Hygiene

- **NEVER commit secrets, tokens, private keys, or `.env` files**:
  - The repository's `.gitignore` automatically excludes `.env`, `.env.*`, `.venv/`, and Python caches.
  - Only commit `.env.example` containing generic development placeholders.
- Always review `git status` and `git diff` before committing to verify no confidential files are staged.

---

## 4. Teammate Onboarding & Repository Invitations

To invite your teammates (**Person B**, **Person C**, and **Person D**) as collaborators:

1. Open your web browser and navigate to the repository on GitHub:
   `https://github.com/helloween1947/powernxt-ai-transformer-sentinel`
2. Click the **Settings** tab in the top navigation bar.
3. In the left-hand menu under **Access**, click **Collaborators**.
4. Click the green **Add people** button.
5. Enter each teammate's GitHub username or email address:
   - Search for **Person B** and click **Add <user> to this repository**.
   - Search for **Person C** and click **Add <user> to this repository**.
   - Search for **Person D** and click **Add <user> to this repository**.
6. Each teammate will receive an email invitation and a notification on GitHub to accept collaborator access.
