# monthTrack

An app to track monthly expenses against a monthly budget.

## Language

**Expense (Despesa)**:
Any outgoing monetary transaction recorded during the month. Has a date, description, category, and amount.
_Avoid_: Gasto, purchase, transaction, outflow

**Budget**:
A single monthly spending cap defined by the user. Can be changed each month independently.
_Avoid_: Monthly limit, spending cap, allowance

**Category**:
A label that classifies expenses. Has a name and optionally an emoji icon.
_Avoid_: Tag, group, tipo

**Month**:
A monthly period that holds a budget and a collection of expenses. Has a year and month identifier.
_Avoid_: Period, mês fiscal, ciclo

**Rollover Expense (Despesa Especial)**:
An expense marked as eligible for manual rollover (field value `"x"`). When the
user triggers the rollover via the UI, the expense is split: the portion that
fits within the remaining budget stays, and the excess is carried over as a new
expense in the following month (same category, same description, `dia=0`).
After rollover, the field stores the original total amount (e.g. `"200.00"`)
for historical reference.
_Avoid_: Despesa parcelada, conta rotativa, auto-rollover

**Notes (Notas)**:
A single-line text field attached to each month, stored as `Notas: ...` below
the Budget line in the month's `.md` file. Editable inline from the dashboard
summary card.

**Caixa (Box)**:
A special-purpose account tracked per month via a secondary table
(`## Caixas`) in the same `.md` file. Each entry has a date, a type
(CP, CC, or CB), and a signed value (positive for deposits, negative for
withdrawals). The monthly dashboard shows each type in a compact row with
`dia=0` and the sum of positive entries. The dedicated **Caixas** tab shows
the real balance (all entries summed) per type, with drill-down by month.
Types are defined in `backend/data/caixas.md` (same format as `cat.md`).
_Avoid_: Account, wallet, envelope
