# ADR-0005: Empréstimos (loans to family/friends)

**Date**: 2026-08-02

**Status**: Accepted

## Context

The user occasionally lends money (or covers a card charge) for family and
friends and needs to track who owes what, per month, until it's paid back.
This is conceptually close to **Caixas** (ADR-0004) — a secondary table
appended to each month's `.md` file, backed by a simple pre-registered list
(like `cat.md`/`caixas.md`) — but with different lifecycle needs: loans can
be paid off in installments, spread automatically across future months, and
should not distort the monthly budget the way expenses do.

## Decision

### Pessoa (person)

A new pre-registered list, `backend/data/pessoas.md`, same format as
`cat.md` (`- Nome emoji`). Full CRUD (add/edit/remove), unlike Caixa types
which only support editing. Removing a person does **not** cascade — past
and already-generated future `Emprestimo` rows keep the person's name as a
plain (now orphaned) string, exactly like removing a `Category` does not
touch historical expenses.

### Emprestimo (loan/payment item)

- Each month's `.md` file gains an optional `## Emprestimos` section after
  `## Caixas`, containing a pipe table:
  `| Data | Pessoa | Description | Valor | Parcelas | ParcelaAtual |`.
- One table, signed value: `valor > 0` is money lent, `valor < 0` is a
  payment received. There is no separate "Pagamento" entity — a payment is
  just a row with `Parcelas=1`, `ParcelaAtual=1`.
- `Data` is the loan's **origination date** (`dd/mm/aa`), not a day-of-month
  like `Expense.dia`/`CaixaItem.data`. It is constant across every
  installment of a series, even the ones written into future months.
- **Installments are pre-generated at creation time.** Creating a loan with
  `parcelas=N` writes N rows in one operation: the current month gets
  `parcela_atual=1`, and N-1 more rows are written into the following months
  (creating those month files if they don't exist yet, same as
  `execute_rollover` does for its overflow row), incrementing
  `parcela_atual` each time. `Valor` is the **per-installment** amount the
  user enters directly (not a total split by the backend); the frontend may
  offer a total↔per-installment calculator as a pure UI convenience, but the
  stored value is always per-installment.
- **No series id column.** Sibling installments are identified by matching
  `Pessoa + Description + Data + Parcelas` (total count) across month files;
  `Valor` and `ParcelaAtual` are allowed to differ. Two genuinely distinct
  loans for the same person that happen to share description, origination
  date, and installment count would be misidentified as one series — accepted
  as a rare edge case in exchange for not adding a technical id column to a
  hand-editable file.
- **Early payoff ("quitar antecipado")**: sums the `valor` of every future
  (not-yet-current-month) installment in the matched series, deletes those
  rows from their respective month files, and writes two new rows into the
  **current** month: one loan row for the consolidated remaining total
  (positive) and one payment row for the same amount (negative). Net effect
  on the current month's balance is zero, but the history shows the debt was
  pulled forward and paid, rather than silently disappearing.
- **Emprestimos are outside the budget.** `total_spent`/`remaining`/the
  progress bar are unaffected, the same way Caixas already sit outside the
  budget — lending money isn't consumption, it's a temporary transfer.

### Frontend

- New **Empréstimos** tab, structured like the Caixas tab but scoped to the
  **current month only** (no cross-month aggregate balance — since
  installments are already pre-distributed across the right months at
  creation time, there's no hidden historical balance to surface). Lists
  people with their net current-month total; clicking a person opens the
  month's items with add-loan, add-payment, edit/delete, and (when
  applicable) quitar-antecipado actions.
- The **Categorias** tab is renamed **Configurações** and gains a second
  section for managing Pessoas (add/remove), alongside the existing
  Categorias section.

## Consequences

- `MonthData` gains an `emprestimos` field (list of loan/payment items).
- Parser/writer updated for the `## Emprestimos` table.
- New `backend/data/pessoas.md` file and CRUD endpoints, mirroring
  `Category`'s endpoints (not `CaixaTipo`'s, which lacks add/remove).
- Creating a multi-installment loan is the first place in the codebase that
  writes to more than one future month file in a single request path
  (`execute_rollover` only ever touches the *next* month).
- Early payoff needs to scan multiple month files to find sibling
  installments by field-matching rather than an id lookup.
