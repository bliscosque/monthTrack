Status: ready-for-agent

# Notes and Caixas — Especificação

## Problem Statement

The user needs to attach free-form observations to each month and track
special-purpose accounts (caixas) independently of the expense budget. Caixas
handle deposits and withdrawals per month per type (CP, CC, CB) without
affecting the budget calculation.

## Solution

### Notes

A single-line text field attached to each month, stored in the same `.md`
file as the budget and expenses. Editable inline from the dashboard summary
card.

### Caixas

A secondary table in each month's `.md` file recording deposits (positive
values) and withdrawals (negative values) by type. Three fixed types
(CP, CC, CB). Monthly view shows a compact aggregation of positive values
per type. A dedicated tab shows the real balance (all values summed) with
drill-down by month. Types are editable (name, emoji) but not creatable or
deletable.

## User Stories

1. As a user, I want to write a note for each month, so that I can record
   observations about my spending that month.
2. As a user, I want to see the note in the dashboard summary card and edit
   it inline, so that I don't have to navigate to a separate form.
3. As a user, I want to record deposits and withdrawals for special-purpose
   accounts (CP, CC, CB) per month, so that I can track money outside the
   expense budget.
4. As a user, I want the monthly view to show one compact row per caixa type
   with the sum of positive entries for the month, so that I can see deposits
   at a glance.
5. As a user, when I click a caixa type in the monthly view, I want to see
   all individual items (both positive and negative) for that type in that
   month, so that I can inspect details.
6. As a user, I want to add a deposit (positive value) to a caixa from the
   detail modal, so that I can record incoming money.
7. As a user, I want to add a withdrawal (negative value) to a caixa from the
   detail modal, so that I can record outgoing money.
8. As a user, I want to edit or delete any individual caixa item, so that I
   can correct mistakes.
9. As a user, I want a dedicated Caixas tab in the main navigation, showing
   the real balance (sum of all values, positive and negative) per type across
   all months.
10. As a user, when I click a type in the Caixas tab, I want to see a monthly
    breakdown of that type's balance, so that I can track it over time.
11. As a user, I want to edit the name and emoji of each caixa type (CP, CC,
    CB), so that I can personalise them.

## Implementation Decisions

### Storage format

Month `.md` files gain two additions:
- A `Notas:` line right after the `Budget:` line.
- A `## Caixas` section after the expenses table, with a pipe table:
  `| Data | Tipo | Valor |`.

Caixa types are stored in `caixas.md` in the same directory as `cat.md`,
using the same line format (`- Tipo emoji`).

### Domain model

`MonthData` gains `notes` (string) and `caixas` (list of caixa items) fields.
A caixa item has: date, tipo (string), valor (signed float).
A caixa tipo has: tipo (short code), nome, emoji (optional).

### Caixa type lifecycle

Only three types exist: CP, CC, CB. The user can edit their display name and
emoji but cannot create or delete types. Editing is done by writing to
`caixas.md`.

### Caixa item identification

Items are identified by their 0-based index in the month's `caixas` list.
The frontend passes this index for edit/delete operations. This avoids a
separate ID field and matches the simplicity of the flat-file storage.

### Monthly aggregation logic

The monthly view shows one row per type with:
- `dia` displayed as 0 (virtual)
- `valor` = sum of entries where `valor > 0` for that type

The Caixas tab shows real balance = sum of ALL entries (positive + negative).
When drilling down by type, the balance is broken down month by month.

### API endpoints

- `GET /api/months/{y}/{m}` — extended to include `notes` and `caixas`
- `PUT /api/months/{y}/{m}/notes` — update notes (body: `{"notes": "..."}`)
- `POST /api/months/{y}/{m}/caixas` — add caixa item
- `PUT /api/months/{y}/{m}/caixas/{idx}` — edit caixa item by index
- `DELETE /api/months/{y}/{m}/caixas/{idx}` — delete caixa item by index
- `GET /api/caixas/tipos` — list caixa types
- `PUT /api/caixas/tipos/{tipo}` — update caixa type name/emoji
- `GET /api/caixas/saldos` — consolidated balances per type (all months)
- `GET /api/caixas/saldos?tipo=CP` — monthly breakdown for one type

### Frontend

**Notes**: A new row in the summary card below budget/spent/remaining. Shows
the note text; clicking turns it into an inline input. Saves on Enter/blur.

**Monthly caixas**: Below the expense list, render a mini-table with one row
per caixa type at `dia=0`. Clicking a row opens a modal showing all
individual items (with edit/delete). The modal has "Adicionar valor" and
"Remover valor" buttons that add a positive or negative entry respectively.

**Caixas tab**: A new tab button in the main navigation. Shows the real
balance per type. Clicking a type expands to show a monthly breakdown.

### Caixa operations don't affect budget

Caixa entries are independent of the expense budget. They do not change
`total_spent`, `remaining`, or the progress bar. They are not eligible for
rollover.

## Testing Decisions

### What makes a good test

- Test external behavior via HTTP API (highest seam).
- Use real markdown file fixtures in a temporary directory.
- Assert on response bodies and optionally verify the `.md` files on disk.

### Test seam

**API seam** — integration tests using FastAPI's `TestClient`, exactly like
the existing test suite in `test_api.py`. The same fixture pattern
(`data_dir` + `client`) applies.

### Prior art

- Expense CRUD (`test_post_expense_adds_to_month`,
  `test_put_expense_updates_expense`, `test_delete_expense_removes_expense`)
- Category CRUD (`test_categories_crud`)

### Tests to add

- Set notes on a month, read back; verify the `.md` file contains the notes.
- Add caixa items (positive and negative) to a month, verify they appear in
  the month data.
- Verify monthly aggregation: only positive values are returned per type.
- Add, edit, delete caixa items by index.
- Verify consolidated balance endpoint returns correct totals across months.
- Verify filtered balance endpoint returns monthly breakdown for a type.
- List and edit caixa types.

## Out of Scope

- Creating or deleting caixa types (only CP, CC, CB).
- Transfers between caixa types in a single operation.
- Caixa items affecting the expense budget, rollover, or category breakdown.
- Multi-line notes.

## Further Notes

- ADR-0004 records the architectural decision.
- Caixa items use index-based addressing, matching the simplicity of the
  flat-file storage (same spirit as dia-based expense identification).
