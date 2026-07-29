Status: ready-for-agent

# Rollover Manual — Especificação

## Problem Statement

O rollover automático atual divide a despesa no momento da criação, o que é
surpreendente e remove o controle do usuário sobre quando e como o carry-over
acontece. O campo `rollover` é booleano e não preserva o valor histórico da
despesa original.

## Solution

O rollover passa a ser um **acionamento manual**: o usuário marca uma despesa
como "elegível para rollover" (`x`) no momento da criação, e depois clica num
botão na interface para executar o rollover. O campo `rollover` deixa de ser
booleano e vira texto, assumindo três estados:

| Estado | Significado | Botão de rollover |
|--------|-------------|-------------------|
| `""` (vazio) | Despesa normal | Não |
| `"x"` | Elegível para rollover, ainda não executado | Sim |
| `"200.00"` | Rollover já executado, guarda o valor original | Não |

## User Stories

1. As a user, I want to mark an expense as "eligible for rollover" when creating
   it, so that I can decide upfront which expenses may be carried over.
2. As a user, I want creating an expense with `rollover=true` to do nothing
   special (no auto-split), so that the expense stays intact in the current
   month until I decide to roll it over.
3. As a user, I want a visible "rollover" button on eligible expenses, so that I
   can trigger the rollover manually when I choose.
4. As a user, when I click the rollover button, I want the expense amount to be
   reduced to what fits in the remaining budget, and the excess to be carried
   over as a new expense in the next month, so that the current month stays
   within budget.
5. As a user, after clicking rollover, I want the original expense to show the
   original total value in the rollover field (e.g. `"200.00"`), so that I can
   see the historical total even though the amount was reduced.
6. As a user, I want the overflow expense in the next month to have `dia=0`,
   indicating it was not originated in that month.
7. As a user, I want the overflow expense in the next month to be marked with
   `rollover="x"`, so that I can roll it over again recursively if needed.
8. As a user, I want the rollover button to disappear after execution, so that I
   don't accidentally roll over the same expense twice.
9. As a user, I want overflow expenses to be generated even when the remaining
   budget is already zero or negative (capped amount = 0), so that the full
   expense can be carried forward.

## Implementation Decisions

### Schema changes (`models.py`)

- `Expense.rollover`: `bool` → `str` (default `""`)
- `Expense.dia`: validation relaxado de `ge=1` para `ge=0` (permite `dia=0` para
  overflow expenses)
- `ExpenseCreate.rollover`: mantido como `bool` — traduzido para `"x"` (se True)
  ou `""` (se False) na camada de storage
- `ExpenseUpdate.rollover`: mantido como `bool | None` — mesma tradução
- `MonthData.remaining`: continua `budget - total_spent` (pode ser negativo)

### Storage changes (`storage.py`)

- `add_expense()`: remove toda a lógica de split automático (linhas 87-108).
  Apenas adiciona a despesa ao mês. Traduz `rollover: True` → `"x"`,
  `rollover: False` → `""`.
- Nova função `execute_rollover(data_dir, year, month, expense_id) → list[Expense]`:
  1. Parseia o mês, encontra a despesa pelo `dia`
  2. Verifica se `rollover == "x"` (se não, erro — não elegível)
  3. Calcula: `room = max(0, data.remaining)`,
     `capped = min(expense.amount, room)`,
     `overflow = expense.amount - capped`
  4. Atualiza a despesa original: `amount = capped`, `rollover = str(original_amount)`
  5. Cria nova despesa no mês seguinte: `amount = overflow`, `rollover = "x"`,
     `dia = 0`, mesma `description` e `category`
  6. Retorna `[expense_atualizado, overflow_expense]`
- `_format_month()`: atualizado para escrever `rollover` como string no lugar
  do booleano
- `_parse_month_text()`: atualizado para parsear `rollover` como string:
  - Se vazio → `""`
  - Se `"x"` → `"x"`
  - Caso contrário → mantém o texto como está (ex: `"200.00"`)

### API changes (`app.py`)

- `POST /api/months/{year}/{month}/expenses`: mantido igual, mas sem split
  automático. Cria uma despesa normal. Retorna apenas um expense.
- Novo endpoint `POST /api/months/{year}/{month}/expenses/{dia}/rollover`:
  aciona `execute_rollover()`. Retorna `[expense_alterado, overflow_expense]`.

### Frontend changes (`index.html`)

- Criar despesa: checkbox "Despesa especial (rollover)" continua igual, envia
  `rollover: true/false`
- Renderizar despesa: mostrar badge "rollover" para despesas com
  `rollover` não vazio. Exibir o valor do rollover quando for numérico (ex:
  `"orig: R$200,00"`).
- Adicionar botão "Rollover" (seta para frente) em despesas com `rollover == "x"`
- Botão chama `POST /.../{dia}/rollover`, recarrega o mês
- Editar despesa: ler `rollover` como string, converter para booleano
  (`!!e.rollover`) para preencher o checkbox. Despesas já roladas
  (`rollover` numérico) podem não ter o checkbox marcado.
- Cálculo de categoria (`loadDashboard`): excluir despesas com `rollover` não
  vazio da soma (já rolam ou são elegíveis — por design, a despesa elegível
  ainda não foi rolada, mas o usuário quer manter o valor cheio fora do
  orçamento até decidir)

## Testing Decisions

### What makes a good test

- Testar comportamento externo via API (seam mais alto)
- Usar fixtures de arquivos markdown reais em temp directory
- Verificar responses HTTP e estado dos arquivos em disco

### Test seam

**API seam** — testes de integração com `TestClient`, igual aos existentes em
`test_api.py`.

### Testes existentes que mudam

- `test_post_rollover_expense_carries_excess`: desativado ou rewrite —
  rollover não é mais automático no POST. Em vez disso, testar o novo endpoint
  de rollover manual.
- `test_get_month_returns_budget_and_expenses`: atualizar asserção de
  `"rollover": True` para `"rollover": "x"`.

### Testes novos

- Criar despesa com `rollover=true`, verificar que NÃO foi splitada (mês
  seguinte não tem nada)
- Criar despesa com `rollover=true`, chamar endpoint de rollover, verificar:
  - Despesa original com amount reduzido e rollover = string numérica
  - Mês seguinte com overflow, dia=0, rollover="x"
- Criar despesa com `rollover=false`, verificar que botão não funciona (404 ou
  400)
- Testar rollover com remaining = 0: capped = 0, overflow = total
- Testar rollover com remaining negativo: capped = 0, overflow = total
- Testar rollover de despesa já rolada (rollover numérico): retorna erro
- Testar rollover do último mês do ano (dez → jan do ano seguinte)

### Fixtures

- `conftest.py`: alterar fixture `jan.md` para usar `"x"` em vez de booleano.
  Ex: `| 10 | Inscrição anual | Saúde | 400.00 | x |`

## Out of Scope

- Rollover automático no momento da criação (removido)
- Rollover recursivo automático (o overflow é criado com `"x"`, mas o usuário
  precisa clicar manualmente no mês seguinte para rolá-lo de novo)

## Further Notes

- Contradiz parcialmente a User Story #11 e #12 do spec original (rollover
  automático e recursivo), que são substituídas por esta spec.
- ADR-0003 registra a decisão de migrar para rollover manual.
