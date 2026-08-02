Status: ready-for-agent

# Empréstimos — Especificação

## Problem Statement

The user occasionally lends money (or covers a card charge) for family and
friends and has no way to track who owes what, per month, until it's paid
back. This needs the same markdown-backed backend as the rest of the app,
without distorting the monthly budget calculation the way an expense would.

## Solution

A new secondary table (`## Emprestimos`) appended to each month's `.md`
file, backed by a pre-registered `Pessoa` list (`pessoas.md`, same format
as `cat.md`). One signed-value table covers both loans (positive) and
payments received (negative) — no separate "Pagamento" entity. Multi
-installment loans pre-generate every future installment at creation time,
spread across the right month files. A new **Empréstimos** tab (current
month only, like the Caixas monthly card) lets the user manage this per
person. The **Categorias** tab is renamed **Configurações** and gains a
Pessoas management section.

## User Stories

1. As a user, I want to register people I lend money to (name + optional
   emoji), so that I can attribute loans to them.
2. As a user, I want to add/remove people from Configurações, so that I can
   keep the list current.
3. As a user, when I remove a person, I want their historical loan records
   to remain intact, so that past months stay accurate.
4. As a user, I want to record a loan with a description, origination date,
   value, and number of installments, so that I can track what I lent.
5. As a user, I want the number of installments to default to 1, so that a
   one-off loan doesn't require extra input.
6. As a user, when I create a loan with more than one installment, I want
   the system to automatically create the remaining installments in the
   following months' files, so that I don't have to revisit this every
   month.
7. As a user, I want to type either the total value or the per-installment
   value in the loan form and have the other calculated automatically, so
   that I don't need a separate calculator.
8. As a user, I want to record a payment received from a person in the
   current month, so that it reduces what they owe that month.
9. As a user, I want a new Empréstimos tab listing every registered person
   with their net balance for the current month, so that I can see who owes
   me money at a glance.
10. As a user, when I click a person in the Empréstimos tab, I want to see
    that month's loan and payment items for them, so that I can inspect and
    manage the details.
11. As a user, I want to edit or delete any individual loan/payment item, so
    that I can correct mistakes.
12. As a user, when a person pays off the remaining installments of a loan
    early, I want a "quitar antecipado" action that removes the future
    installments and records the payoff as a loan+payment pair in the
    current month, so that the history reflects the money actually came in
    early rather than the debt silently vanishing.
13. As a user, I want loans and payments to have no effect on my monthly
    budget/spent/remaining figures, so that lending money isn't confused
    with spending it.

## Implementation Decisions

### Storage format

Month `.md` files gain an optional `## Emprestimos` section after
`## Caixas`, with a pipe table:
`| Data | Pessoa | Description | Valor | Parcelas | ParcelaAtual |`.

`Data` is `dd/mm/aa` (loan origination date), not a day-of-month like
`Expense.dia`/`CaixaItem.data`. It stays constant across every installment
of a series, including rows written into future months.

People are stored in `backend/data/pessoas.md`, same line format as
`cat.md` (`- Nome emoji`).

### Domain model

`MonthData` gains an `emprestimos` field: a list of items with `data`
(string, `dd/mm/aa`), `pessoa`, `description`, `valor` (signed float),
`parcelas` (int, default 1), `parcela_atual` (int, default 1).

A `Pessoa` has: `name`, `emoji` (optional) — same shape as `Category`.

### One table, signed value

There is no separate "Pagamento" model. A payment is an `Emprestimo` row
with `valor < 0`, `parcelas=1`, `parcela_atual=1`. A loan is a row with
`valor > 0`.

### Installment pre-generation

Creating a loan with `parcelas=N` writes N rows in a single request: the
current month gets `parcela_atual=1` at the entered value; N-1 more rows
are written to the following months (creating those month files if they
don't exist, same as `execute_rollover`'s handling of the next month),
`parcela_atual` incrementing each time. `Valor` is the per-installment
amount the user enters directly — the backend never divides a total. The
frontend form may offer total↔per-installment calculation as a pure
convenience; only the per-installment number is sent to the API.

### Series identification (no id column)

Sibling installments are found by matching `pessoa + description + data +
parcelas` (total count) across month files — `valor` and `parcela_atual`
are allowed to differ between rows. Two distinct loans sharing all four of
those fields would be misidentified as one series; accepted as a rare edge
case in exchange for not adding a technical id column to a hand-editable
file.

### Early payoff ("quitar antecipado")

Given an installment row, find its series (see above), sum the `valor` of
every installment in a month **after** the current one, delete those rows
from their respective month files, and write two new rows into the
**current** month:
- a loan row for the consolidated remaining total (positive `valor`,
  `parcelas=1`, `parcela_atual=1`)
- a payment row for the same amount (negative `valor`, `parcelas=1`,
  `parcela_atual=1`)

Net effect on the current month's Emprestimos balance is zero; the pair
records that the debt was pulled forward and paid rather than vanishing.

### Outside the budget

`total_spent`, `remaining`, and the progress bar are computed exactly as
today (`expenses + positive caixas`) — Emprestimos are never included.

### API endpoints

- `GET /api/pessoas` — list people
- `POST /api/pessoas` — add a person
- `PUT /api/pessoas/{name}` — edit a person (emoji)
- `DELETE /api/pessoas/{name}` — remove a person (no cascade)
- `POST /api/months/{y}/{m}/emprestimos` — add a loan or payment item.
  When `parcelas > 1`, generates the remaining installments in future
  months as a side effect.
- `PUT /api/months/{y}/{m}/emprestimos/{idx}` — edit an item by index
- `DELETE /api/months/{y}/{m}/emprestimos/{idx}` — delete an item by index
- `POST /api/months/{y}/{m}/emprestimos/{idx}/quitar` — early payoff for
  the series that item belongs to
- `GET /api/months/{y}/{m}` — extended to include `emprestimos`

### Frontend

**Empréstimos tab**: new tab in the main navigation, positioned after
Caixas. Lists every registered Pessoa with the net sum of their current
month's Emprestimos items (0 if none). Clicking a person opens a view/modal
with that month's items (date, description, value, parcela label when
`parcelas > 1`), each with edit/delete, plus "+ Adicionar empréstimo" (full
form: description, date, value, parcelas with the total↔mensal calculator)
and "+ Registrar pagamento" (simple form: date, value — no parcelas field,
submits as a negative-value item). Items with `parcelas > 1` and a
not-yet-paid future installment show a "Quitar antecipado" action.

**Configurações tab**: rename of the current Categorias tab/label. Keeps
the existing Categorias section, adds a second Pessoas section (list with
inline add/remove), same interaction pattern as Categorias' existing
add-form.

## Testing Decisions

### What makes a good test

Test external behavior via the HTTP API (highest seam) — same as the rest
of the suite. Use real markdown file fixtures in a temporary directory;
assert on response bodies and, where the on-disk format itself is the
point (e.g. installment spread across month files, `dd/mm/aa` date
format), also read the `.md` file(s) directly.

### Test seam

**API seam** — integration tests using FastAPI's `TestClient`, in
`test_api.py`, matching the existing fixture pattern (`data_dir` + `client`).

### Prior art

- Caixa item CRUD (`add_caixa_item`/`update_caixa_item`/`delete_caixa_item`
  and their endpoints) — closest precedent for a signed-value secondary
  table with index-based addressing.
- Category CRUD (`test_categories_crud`) — precedent for Pessoa's full
  add/edit/remove lifecycle (unlike Caixa types, which only support edit).
- `execute_rollover` — precedent for writing into a month file that may not
  exist yet (`next_data is None` → construct a fresh `MonthData`).

### Tests to add

- Pessoa CRUD: add, edit (emoji), remove, remove doesn't affect existing
  Emprestimo rows referencing that name.
- Add a single-installment loan; verify it appears in the month and does
  not affect `total_spent`/`remaining`.
- Add a payment (negative value); verify it reduces the person's net
  balance for the month.
- Add a loan with `parcelas=3`; verify 3 rows exist across the current and
  next 2 months' files, each with the entered per-installment value and
  the correct `parcela_atual`.
- Creating a multi-installment loan when a future month file doesn't exist
  yet creates it.
- Edit and delete an Emprestimo item by index.
- Quitar antecipado: given a loan with future installments pending, verify
  the future rows are removed and the current month gains the consolidated
  loan+payment pair with matching totals.
- Quitar antecipado series matching ignores `valor`/`parcela_atual`
  differences but requires matching `pessoa`/`description`/`data`/`parcelas`.

## Out of Scope

- A cross-month aggregate balance view for Empréstimos (like the Caixas
  tab has) — current month only, per this ADR's decision.
- Blocking Pessoa removal when they have a non-zero balance.
- A series id field/column.
- Interest, due-date reminders, or notifications.

## Further Notes

- ADR-0005 records the architectural decision.
- Built on the same append-a-secondary-table pattern established by
  ADR-0004 (Caixas), but diverges deliberately on: signed single table
  covering both directions with no separate payment entity, a full date
  instead of a day-of-month, automatic multi-month installment generation,
  and current-month-only aggregation.
