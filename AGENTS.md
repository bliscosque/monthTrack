## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles mapped to label strings in this repo. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.

## Git rules

**NUNCA fazer `git push` sem o usuário pedir ou confirmar explicitamente.** Commits podem ser feitos sem perguntar, mas push só sob autorização.

## Session state (Jul 2026)

Backend (FastAPI) and frontend (SPA) implemented. 34 tests pass.
Data stored as `.md` files in `backend/data/`. Run with:
```
cd backend && .venv/bin/uvicorn monthtrack.app:app --reload
```
Set `APP_PASSWORD` in `.env` for auth.
See `.scratch/monthTrack/spec.md` and `.scratch/monthTrack/notas-e-caixas/spec.md` for specs.
