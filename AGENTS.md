## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles mapped to label strings in this repo. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.

## Session state (Jul 2026)

Backend (FastAPI) and frontend (SPA) implemented. 15 tests pass.
Data stored as `.md` files in `backend/data/`. Run with:
```
cd backend && .venv/bin/uvicorn monthtrack.app:app --reload
```
See `.scratch/monthTrack/spec.md` for the full spec.
