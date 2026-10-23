# Mangadvisor — Instructions for coding agents

This file applies to the whole repository. Read the relevant code and documentation before changing behavior; avoid unnecessary scaffolding or duplicated planning files.

## Product and architecture
- Mangadvisor is a local-first Windows 10/11 manga catalogue, recommendation and physical-library application.
- User entry point: `mangadvisor.cmd`; orchestration: `cmd/control-center.ps1`.
- Frontend: `apps/web/` (HTML/CSS/JavaScript); API: `apps/api/` (FastAPI).
- Acquisition and enrichment: `pipelines/engine/`; schema and migrations: `sql/schema/`.
- Runtime: PostgreSQL (source of truth), Meilisearch (public search), Docker Compose (`infra/compose/`).
- See `README.md` and `docs/03_technical/project_structure.md` for current behavior. Treat older design documents as proposals, not proof of implemented functionality.

## Engineering approach
- Investigate and fix root causes; make the smallest coherent change that solves the problem.
- Check call sites, scripts, dependencies and tests before removing or renaming code. Do not silently drop existing features.
- Extend existing tests with a regression case for each bug. A passing mocked test does not prove Windows/Docker behavior.
- When working on a complex task, make a short plan and then implement, test and iterate without asking for approval on routine engineering choices.
- Keep the repository lean: no duplicate launchers, generated reports, speculative documentation, unnecessary dependencies or copied implementations.
- Do not declare a feature functional unless it was exercised, and never claim a check passed unless it actually ran.

## Non-negotiable data safety
- NEVER delete, recreate, overwrite or reset real PostgreSQL/Meilisearch volumes, `.env`, `private-data/`, `backups/` or `data/raw/` to fix application code.
- NEVER run `docker compose down -v`, `docker volume prune`, `git reset --hard` or `git clean -fdx` against a user checkout. Ask for explicit approval before any destructive operation, production migration or restore.
- Keep secrets and personal library exports out of commits, logs and PR descriptions. Respect `.gitignore`.
- Test database migrations, backups, imports and restores in isolated disposable environments; verify recovery before risky updates.
- Never infer owned volumes, exact editions or ISBNs from fuzzy title matches. Distinguish work, edition, volume and ISBN; preserve unresolved ambiguity and source provenance.
- Keep personal reading status, ratings, inventory and quantities separate from public catalogue/search indexes.

## Windows and Git safety
- The canonical user workflow starts from `mangadvisor.cmd`. Preserve support for Windows PowerShell 5.1, quoting/encoding and Docker Desktop.
- For Windows-native subprocess or quoting issues, use a real Windows runner or a local Windows test; Linux-only or mocked checks are insufficient.
- Keep the stable clone and sandbox/test clone separate, with isolated Docker project names and data.
- Use a short feature/fix branch based on `main`; make scoped commits and open a PR. Do not force-push, rewrite shared history or merge into `main` without approval.
- A GitHub commit/CI run does not update a user's local Windows checkout. Do not claim local deployment or verification unless performed with access to that machine.

## Verification (choose the checks relevant to the change)
- Repository contracts: `python tools/audit_repository.py --strict`.
- Python syntax: `python -m compileall -q apps/api pipelines/engine tests tools`.
- Python tests: `python -m unittest discover -s tests -p "test_*.py" -v`.
- Frontend tests: `node --test tests/web/*.test.mjs`.
- Windows menu/backup/Git tests: inspect and run the matching `tests/windows/*.ps1` on Windows PowerShell 5.1.
- Docker, integration and browser tests: use applicable workflows under `.github/workflows/`, and disposable test databases only.
- Do not silently skip failed tests; report exact commands, outcomes and environmental blockers.

## Delivery report
Summarize: root cause / change / observed tests and results / risks or untested areas / branch, commit and PR link. Make one clear recommendation for the next step.