## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles mapped to label strings in this repo. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.

## Language

All documentation must be written in **English**. Domain terms (Caixa, Notas, Dia, etc.) keep their original Portuguese names as they are part of the data format.

## Git rules

**NEVER `git push` without the user asking or explicitly confirming.** Commits may be made without asking, but push requires authorization.

## Session state (Jul 2026)

Backend (FastAPI) and frontend (SPA) implemented. 34 tests pass.
Data stored as `.md` files in `backend/data/`. Run with:
```
cd backend && .venv/bin/uvicorn monthtrack.app:app --reload
```
Set `APP_PASSWORD` in `.env` for auth.
See `.scratch/monthTrack/spec.md` and `.scratch/monthTrack/notas-e-caixas/spec.md` for specs.
