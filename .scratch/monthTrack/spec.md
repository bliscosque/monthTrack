Status: ready-for-agent

# monthTrack Spec

## Problem Statement

The user needs a simple way to track monthly expenses against a monthly budget, with historical visibility across months. Data must be stored in plain markdown files so it can be inspected and edited directly, and a web UI plus a bot must be able to read and write the same files through a backend API.

## Solution

A web application split into a Python backend API and a separate frontend. The backend reads and writes markdown files organized by year/month, plus a categories file. It exposes a REST API that the frontend (and later a bot) consumes. The frontend provides a dashboard with budget vs. spent, per-category breakdown, and historical charts.

## User Stories

1. As a user, I want to set a monthly budget, so that I know my spending cap for the month.
2. As a user, I want the budget to default to the previous month's value, so that I don't have to redefine it every month.
3. As a user, I want to record an expense with a date, description, category, and amount, so that I can track what I spent.
4. As a user, I want to view all expenses for the current month, so that I can see where my money went.
5. As a user, I want to see how much I've spent so far vs. my budget, so that I know if I'm on track.
6. As a user, I want to see how much budget remains for the month, so that I can plan remaining spending.
7. As a user, I want to see a breakdown of expenses by category, so that I know which categories consume the most budget.
8. As a user, I want to edit an existing expense, so that I can correct mistakes.
9. As a user, I want to delete an expense, so that I can remove entries that should not count.
10. As a user, I want to mark an expense as a rollover expense, so that if it exceeds the remaining budget, the excess carries to next month.
11. As a user, I want rollover expenses to automatically create a new expense in the following month (same category, same description), so that the carry-over happens without manual work.
12. As a user, I want rollover expenses to keep rolling forward recursively if the next month also lacks sufficient budget, so that large expenses are spread properly.
13. As a user, I want to view a chart of monthly spending over time, so that I can spot trends.
14. As a user, I want to filter the historical chart by one or more categories, so that I can track specific expense types over time.
15. As a user, I want to manage categories (name + optional emoji), so that expenses are meaningfully classified.
16. As a user, I want to edit the markdown files directly and see those changes reflected in the app, so that I can work offline or via my editor.
17. As a user, I want to navigate between months, so that I can view past months' data.

## Implementation Decisions

### Storage format

All data lives in markdown files. No database. The Python backend parses and writes these files.

```
ano/
├── jan.md
├── feb.md
├── mar.md
├── ...
└── dec.md
cat.md
```

Each month file contains the budget for that month and a list of expenses. `cat.md` contains the list of categories.

Expenses are identified for edit/delete by date + description + amount (or by line number in the file). An expense contains: date, description, category, amount, and an optional `rollover` flag.

### Backend

- Python (the user's preferred language)
- REST API (framework TBD — could be Flask, FastAPI, or similar)
- Reads/writes the markdown files directly
- Serves as the single source of truth for both the frontend and the bot

### Frontend

- Web application (framework TBD)
- Dashboard views:
  1. Current month: budget vs. total spent, remaining balance
  2. Category breakdown for current month
  3. Historical bar/line chart of monthly spending
  4. Historical chart filtered by selected categories
- Navigation between months
- CRUD for expenses, budget, and categories

### API endpoints (expected)

- `GET /api/months` — list available months
- `GET /api/months/<year>/<month>` — get month (budget + expenses)
- `PUT /api/months/<year>/<month>/budget` — set budget
- `POST /api/months/<year>/<month>/expenses` — add expense
- `PUT /api/months/<year>/<month>/expenses/<id>` — edit expense
- `DELETE /api/months/<year>/<month>/expenses/<id>` — delete expense
- `GET /api/categories` — list categories
- `POST /api/categories` — add category
- `PUT /api/categories/<name>` — edit category
- `DELETE /api/categories/<name>` — delete category

### Rollover expense behavior (algorithm)

1. User creates an expense with `rollover: true`
2. On write, check if the expense amount exceeds remaining budget
3. If it fits entirely within remaining budget, store as a normal expense
4. If it exceeds remaining budget:
   - Store a partial expense equal to remaining budget
   - Create a new rollover expense in the next month with the excess amount (same category, same description)
   - If the next month also overflows, recurse

### Initial categories

Gym, Lazer, Presentes, Restaurante, Mercado, Casa, Pessoal, Saúde

### Currency

Single currency (R$).

### Over-budget alert

Informative only — no blocking behavior.

## Testing Decisions

### What makes a good test

- Test external behavior, not implementation details
- Use real markdown file fixtures in a temporary directory
- Test through the API (highest seam) to maximize confidence

### Test seam

**API seam** — integration tests that:
1. Spin up the backend with a temp directory containing known `.md` fixtures
2. Call HTTP endpoints via a test client
3. Assert on the response body and status codes
4. Optionally verify the resulting `.md` files on disk after mutations

No lower-level unit tests for now. Add them only if parsing logic grows complex enough to warrant isolated coverage.

### What will be tested

- Budget CRUD
- Expense CRUD (including edit/delete)
- Rollover expense creation and carry-over logic (multi-month scenarios)
- Category CRUD
- Dashboard aggregation endpoints (spent vs. budget, category breakdown)
- Historical data aggregation

## Out of Scope

- Authentication / user accounts (single-user app)
- Multi-currency support
- Mobile app (responsive web only)
- Recurring / subscription auto-import
- Export to CSV or PDF

## Further Notes

- The frontend framework decision is left open for the implementation phase.
- The backend framework decision (Flask vs FastAPI vs others) is left open for the implementation phase.
- ADR-0001 (markdown files as primary store) records the rationale behind the storage choice.
