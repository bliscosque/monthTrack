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
