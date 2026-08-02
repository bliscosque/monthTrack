# monthTrack

A simple, self-hosted app to track monthly expenses against a monthly budget.

Data is stored as plain **markdown files** — you can edit expenses directly in any text editor or via the web UI.

A password is required to access the app (set via `APP_PASSWORD` env var or `password` in `.env`).

## Quick start

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
echo 'APP_PASSWORD=mysecret' > .env
.venv/bin/uvicorn monthtrack.app:app --reload
```

Open `http://localhost:8000` and enter the password.

## Storage format

All data lives in `backend/data/` as markdown files.

```
data/
├── cat.md              ← categories (one per line)
├── caixas.md           ← caixa types (CP, CC, CB)
├── pessoas.md          ← people you lend money to (one per line)
└── 2026/
    ├── jan.md          ← budget + notes + expenses + caixas + emprestimos
    ├── fev.md
    └── ...
```

**Month file example:**

```markdown
Budget: 3000
Notas: My notes for the month

| Dia | Description | Category | Amount | Rollover |
|-----|-------------|----------|--------|----------|
| 5   | Lunch       | Food     | 35.00  |          |
| 10  | Insurance   | Health   | 150.00 | x        |

## Caixas
| Data | Tipo | Valor |
|------|------|-------|
| 1    | CP   | 500.0 |
| 15   | CC   | -200.0 |

## Emprestimos
| Data | Pessoa | Description | Valor | Parcelas | ParcelaAtual |
|------|--------|-------------|-------|----------|--------------|
| 01/01/26 | Mom | Fridge | 300.00 | 3 | 1 |
```

`Emprestimos` tracks money lent to family/friends — positive `Valor` is a loan, negative is a payment received. It sits outside the budget (doesn't affect `total_spent`/`remaining`). See [ADR-0005](docs/adr/0005-emprestimos.md) for the full model.

Set `Rollover` to `x` for expenses eligible for manual carry-over. Click the
rollover button in the UI to split the expense when ready.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/months` | List available months |
| GET | `/api/months/{year}/{month}` | Get month data |
| PUT | `/api/months/{year}/{month}/budget` | Set budget |
| PUT | `/api/months/{year}/{month}/notes` | Set notes |
| POST | `/api/months/{year}/{month}/expenses` | Add expense |
| PUT | `/api/months/{year}/{month}/expenses/{idx}` | Edit expense |
| DELETE | `/api/months/{year}/{month}/expenses/{idx}` | Delete expense |
| POST | `/api/months/{year}/{month}/expenses/{idx}/rollover` | Execute rollover |
| GET | `/api/months/{year}/{month}/dashboard` | Dashboard summary |
| GET | `/api/history?categories=` | Historical spending |
| GET/POST/PUT/DELETE | `/api/categories` | Category CRUD |
| POST/PUT/DELETE | `/api/months/{year}/{month}/caixas[/{idx}]` | Caixa item CRUD |
| GET/PUT | `/api/caixas/tipos[/{tipo}]` | Caixa type list/edit |
| GET | `/api/caixas/saldos[?tipo=]` | Consolidated balances |
| GET/POST/PUT/DELETE | `/api/pessoas[/{name}]` | Pessoa CRUD |
| POST/PUT/DELETE | `/api/months/{year}/{month}/emprestimos[/{idx}]` | Emprestimo item CRUD (POST spreads installments across future months) |
| POST | `/api/months/{year}/{month}/emprestimos/{idx}/quitar` | Early payoff (consolidates remaining installments into the current month) |

## Project structure

```
backend/
├── src/monthtrack/     ← Python backend (FastAPI)
│   ├── app.py          ← API routes
│   ├── models.py       ← Pydantic models
│   ├── storage.py      ← Markdown file parser/writer
│   └── security.py     ← JWT auth helpers
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

49 integration tests cover expenses, rollover, categories, notes, caixas, pessoas, and emprestimos.

## Domain model

See [`CONTEXT.md`](CONTEXT.md) for the glossary and [`docs/adr/`](docs/adr/) for architectural decisions.
