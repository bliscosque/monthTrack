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
A type of expense that, when it exceeds the remaining budget for the month, is split: the portion within budget stays, and the remainder is automatically carried over as a new rollover expense in the following month (same category, same description). Recurse as needed.
_Avoid_: Despesa parcelada, conta rotativa
