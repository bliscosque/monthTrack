# monthTrack

A simple, self-hosted app to track monthly expenses against a monthly budget.

Data is stored as plain **markdown files** — you can edit expenses directly in any text editor or via the web UI.

## Quick start

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn monthtrack.app:app --reload
```

Open `http://localhost:8000`.

## Storage format

All data lives in `backend/data/` as markdown files.

```
data/
├── cat.md              ← categories (one per line)
└── 2026/
    ├── jan.md          ← budget + expenses for January
    ├── fev.md
    └── ...
```

**Month file example:**

```markdown
Budget: 3000

| Dia | Description | Category | Amount | Rollover |
|-----|-------------|----------|--------|----------|
| 5   | Almoço      | Comida   | 35.00  |          |
| 10  | Plano       | Saúde    | 150.00 | x        |
```

Set `Rollover` to `x` for expenses that should carry excess to the next month.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/months` | List available months |
| GET | `/api/months/{year}/{month}` | Get month data (budget + expenses) |
| PUT | `/api/months/{year}/{month}/budget` | Set budget |
| POST | `/api/months/{year}/{month}/expenses` | Add expense |
| PUT | `/api/months/{year}/{month}/expenses/{dia}` | Edit expense |
| DELETE | `/api/months/{year}/{month}/expenses/{dia}` | Delete expense |
| GET | `/api/months/{year}/{month}/dashboard` | Dashboard summary |
| GET | `/api/history?categories=` | Historical spending |
| GET/POST/PUT/DELETE | `/api/categories` | Category CRUD |

## Project structure

```
backend/
├── src/monthtrack/     ← Python backend (FastAPI)
│   ├── app.py          ← API routes
│   ├── models.py       ← Pydantic models
│   └── storage.py      ← Markdown file parser/writer
├── frontend/           ← Single-page web UI
│   └── index.html      ← HTML + CSS + JS (no build step)
├── data/               ← Your data files (git-ignored)
├── tests/              ← Integration tests (pytest)
└── pyproject.toml
```

## Tests

```bash
cd backend
.venv/bin/pytest -v
```

## Domain model

See [`CONTEXT.md`](CONTEXT.md) for the glossary and [`docs/adr/`](docs/adr/) for architectural decisions.
