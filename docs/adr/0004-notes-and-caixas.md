# ADR-0004: Notes and Caixas (special-purpose boxes)

**Date**: 2026-07-29

**Status**: Accepted

## Context

The user needs two additions to the monthly tracking model:

1. A **notes** field per month for free-form observations.
2. **Caixas** — special-purpose accounts (CP, CC, CB) that track deposits and
   withdrawals independently of the expense budget, stored alongside expenses
   in the same monthly `.md` file.

## Decision

### Notes

A `Notas:` line is added to each month's `.md` file, after the `Budget:` line.
It is a single-line text field. The backend parses and writes it as part of
`MonthData`. The frontend displays it in the summary card and allows inline
editing.

### Caixas

- Each month's `.md` file gains an optional `## Caixas` section after the
  expenses table, containing a pipe table with columns `| Data | Tipo | Valor |`.
- Types are stored in `backend/data/caixas.md` (same format as `cat.md`).
  Initially: CP, CC, CB. The user can edit names/emojis but cannot add or
  remove types.
- The backend model adds `CaixaItem` (data, tipo, valor) and `CaixaTipo`
  (tipo, nome, emoji).
- **Monthly view** (frontend): shows one compact row per type with `dia=0`
  and the sum of **positive** values only. Clicking a type opens a modal
  with the individual items (all values, signed), plus Add/Remove buttons.
- **Caixas tab**: shows the **real balance** (sum of all values, positive and
  negative) per type across all months. Clicking a type shows a monthly
  breakdown.
- CRUD for individual CaixaItem entries follows the same pattern as expenses
  (add, edit, delete).

## Consequences

- `MonthData.notes` field added (string).
- `MonthData.caixas` field added (list of CaixaItem).
- Parser/writer updated for the new `Notas:` line and `## Caixas` table.
- New API endpoints for caixa item CRUD, caixa type editing, and consolidated
  queries.
- Frontend gains inline notes editing and a new Caixas tab.
- The expense CRUD patterns serve as prior art for caixa item CRUD.
