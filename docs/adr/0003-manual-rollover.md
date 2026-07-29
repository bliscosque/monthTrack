# ADR-0003: Manual rollover instead of automatic

**Date**: 2026-07-29

**Status**: Accepted

## Context

The original implementation split a rollover expense automatically at creation
time when it exceeded the remaining budget. This was surprising — the user lost
control over *when* the carry-over happened. Additionally, the boolean
`rollover` field discarded the original expense total, making it impossible to
see the historical full amount after the split.

## Decision

Replace automatic rollover with a **manual two-step flow**:

1. **Create**: the user marks an expense as eligible (`rollover=true` →
   stored as `"x"`). No split happens.
2. **Trigger**: the user clicks a "rollover" button in the UI, which calls a
   new endpoint that executes the split at that moment.

The `rollover` field becomes a **string** with three states:
- `""` — normal expense, not eligible
- `"x"` — eligible, not yet rolled over
- `"200.00"` — rolled over, stores the original total for reference

Overflow expenses in the following month get `dia=0` (not an expense originated
in that month) and `rollover="x"` (eligible for further manual rollover).

### Why not alternatives

| Option | Rejected because |
|--------|------------------|
| Keep auto-rollover | Surprising; removes user control; loses historical amount. |
| Separate `original_amount` field | Adds schema complexity; the rollover field can carry both roles (flag + history). |
| Amount = 0 for fully-rolled expenses | Confusing in the UI; field should not be zero. |

## Consequences

- `Expense.rollover` changes from `bool` to `str`.
- `Expense.dia` validation relaxes to allow `0`.
- `POST /api/months/{y}/{m}/expenses` no longer splits automatically.
- New endpoint `POST /api/months/{y}/{m}/expenses/{idx}/rollover` (expenses identified by array index, not `dia`, to avoid ambiguity when multiple expenses share the same day).
- `MonthData.total_spent` includes positive caixa values, so `remaining` (budget − total_spent) reflects the full monthly outlay and the rollover cap accounts for caixa spending.
- Frontend gains a rollover button; rollover badge shows the original amount
  when present.
- Existing tests for auto-rollover need to be rewritten.
- Contradicts User Stories #11 and #12 from the original spec (automatic +
  recursive rollover), which are superseded.
