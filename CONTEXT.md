# monthTrack

An app to track monthly expenses against a monthly budget.

## Language

**Expense (Despesa)**:
Any outgoing monetary transaction recorded during the month. Has a date, description, category, and amount.
The date (`dia`) may be `0`, meaning the expense applies to the whole month
rather than a specific day (e.g. rollover carryover, or any charge the user
doesn't want tied to a single day).
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
The remaining budget accounts for both expenses and positive caixa values
(`remaining = budget − expenses − positive_caixas`).
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

**Pessoa (Person)**:
A family member or friend the user lends money to. Defined in
`backend/data/pessoas.md` (same format as `cat.md`): name plus optional
emoji. Full CRUD (add/edit/remove) via Configurações, unlike Caixa types.
Removing a Pessoa does not delete their historical Emprestimo entries.
_Avoid_: Contact, cliente, devedor

**Emprestimo (Loan)**:
A signed monetary entry tracked per month via a secondary table
(`## Emprestimos`) in the same `.md` file, linked to a Pessoa. Positive
`valor` = money lent; negative `valor` = a payment received (a "Pagamento"
is not a separate entity, just an Emprestimo row with a negative value and
`Parcelas=1`). Unlike Expense/CaixaItem, its date field is the loan's full
origination date (`dd/mm/aa`), constant across every installment of the
series — not a day-of-month within the file it lives in.
Emprestimos sit **outside the budget**: they never affect `total_spent`,
`remaining`, or the progress bar.
The **Empréstimos** tab shows only the current month's net balance per
Pessoa (no cross-month aggregate, unlike Caixas) — click a Pessoa to see
that month's items.
_Avoid_: Dívida, conta a receber, IOU

**Parcela (Installment)**:
One row of an Emprestimo whose `Parcelas` (total count) is greater than 1.
Creating a multi-parcela loan pre-generates every installment across the
following months in one operation (creating those month files if needed),
each with the per-installment `Valor` the user entered and an incrementing
`ParcelaAtual`. Sibling installments are identified by matching
Pessoa + Description + Data + Parcelas across month files — there is no
series id field. "Quitar antecipado" (early payoff) sums the remaining
future installments, deletes them from their month files, and writes the
consolidated total plus a matching payment into the current month.
_Avoid_: Series id, loan id
