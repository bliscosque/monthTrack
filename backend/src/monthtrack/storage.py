from pathlib import Path

from monthtrack.models import (
    MonthData, Expense, Category, CaixaItem, CaixaTipo, Emprestimo, Pessoa,
)


MONTH_NAMES = ["jan", "fev", "mar", "abr", "mai", "jun",
               "jul", "ago", "set", "out", "nov", "dez"]


def _month_path(data_dir: str, year: int, month: int) -> Path:
    name = MONTH_NAMES[month - 1]
    return Path(data_dir) / str(year) / f"{name}.md"


def _advance_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def parse_month(data_dir: str, year: int, month: int) -> MonthData | None:
    path = _month_path(data_dir, year, month)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return _parse_month_text(text, year, month)


def write_month(data_dir: str, data: MonthData) -> None:
    path = _month_path(data_dir, data.year, data.month)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_format_month(data), encoding="utf-8")


def _format_month(data: MonthData) -> str:
    lines = [f"Budget: {data.budget}"]
    if data.notes:
        lines.append(f"Notas: {data.notes}")
    lines.extend(["",
                  "| Dia | Description | Category | Amount | Rollover |",
                  "|-----|-------------|----------|--------|----------|"])
    for e in data.expenses:
        roll = f" {e.rollover}" if e.rollover else ""
        lines.append(f"| {e.dia} | {e.description} | {e.category} | {e.amount:.2f} |{roll} |")
    if data.caixas:
        lines.extend(["",
                      "## Caixas",
                      "| Data | Tipo | Valor |",
                      "|------|------|-------|"])
        for c in data.caixas:
            lines.append(f"| {c.data} | {c.tipo} | {c.valor:.2f} |")
    if data.emprestimos:
        lines.extend(["",
                      "## Emprestimos",
                      "| Data | Pessoa | Description | Valor | Parcelas | ParcelaAtual |",
                      "|------|--------|-------------|-------|----------|--------------|"])
        for e in data.emprestimos:
            lines.append(
                f"| {e.data} | {e.pessoa} | {e.description} | {e.valor:.2f} "
                f"| {e.parcelas} | {e.parcela_atual} |"
            )
    return "\n".join(lines) + "\n"


def _parse_month_text(text: str, year: int, month: int) -> MonthData:
    lines = text.strip().splitlines()
    budget = 0.0
    notes = ""
    expenses: list[Expense] = []
    caixas: list[CaixaItem] = []
    emprestimos: list[Emprestimo] = []
    section: str | None = None
    in_caixas = False
    in_emprestimos = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("Budget:"):
            budget = float(stripped.removeprefix("Budget:").strip())
            continue

        if stripped.startswith("Notas:"):
            notes = stripped.removeprefix("Notas:").strip()
            continue

        if stripped.startswith("## Emprestimos"):
            in_emprestimos = True
            in_caixas = False
            section = None
            continue

        if stripped.startswith("## Caixas"):
            in_caixas = True
            in_emprestimos = False
            section = None
            continue

        if stripped.replace(" ", "").startswith("|---"):
            if in_emprestimos:
                section = "emprestimo"
            elif in_caixas:
                section = "caixa"
            else:
                section = "expense"
            continue

        if stripped.startswith("|") and section == "expense":
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            if len(parts) >= 4:
                dia = int(parts[0])
                description = parts[1]
                category = parts[2]
                amount = float(parts[3])
                rollover = parts[4].strip() if len(parts) > 4 else ""
                expenses.append(Expense(
                    dia=dia, description=description, category=category,
                    amount=amount, rollover=rollover,
                ))

        if stripped.startswith("|") and section == "caixa":
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            if len(parts) >= 3:
                caixas.append(CaixaItem(
                    data=int(parts[0]),
                    tipo=parts[1],
                    valor=float(parts[2]),
                ))

        if stripped.startswith("|") and section == "emprestimo":
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            if len(parts) >= 6:
                emprestimos.append(Emprestimo(
                    data=parts[0],
                    pessoa=parts[1],
                    description=parts[2],
                    valor=float(parts[3]),
                    parcelas=int(parts[4]),
                    parcela_atual=int(parts[5]),
                ))

    return MonthData(
        year=year, month=month, budget=budget, notes=notes,
        expenses=expenses, caixas=caixas, emprestimos=emprestimos,
    )


def add_expense(data_dir: str, year: int, month: int, expense: Expense) -> Expense:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")
    data.expenses.append(expense)
    write_month(data_dir, data)
    return expense


def execute_rollover(data_dir: str, year: int, month: int, idx: int) -> list[Expense]:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")

    if idx < 0 or idx >= len(data.expenses):
        raise FileNotFoundError(f"Expense at index {idx} not found")

    expense = data.expenses[idx]
    if expense.rollover != "x":
        raise ValueError(f"Expense at index {idx} is not eligible for rollover")

    original_amount = expense.amount
    room = max(0, data.remaining + original_amount)
    capped_amount = min(original_amount, room)
    overflow_amount = original_amount - capped_amount

    data.expenses[idx] = expense.model_copy(update={
        "amount": capped_amount,
        "rollover": str(original_amount),
    })
    write_month(data_dir, data)

    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    next_data = parse_month(data_dir, next_year, next_month)
    if next_data is None:
        next_data = MonthData(year=next_year, month=next_month, budget=0)

    overflow_expense = Expense(
        dia=0, description=expense.description, category=expense.category,
        amount=overflow_amount, rollover="x",
    )
    next_data.expenses.append(overflow_expense)
    write_month(data_dir, next_data)

    return [data.expenses[idx], overflow_expense]


def update_expense(data_dir: str, year: int, month: int, idx: int,
                   updates: dict) -> Expense | None:
    data = parse_month(data_dir, year, month)
    if data is None:
        return None
    if idx < 0 or idx >= len(data.expenses):
        return None

    current = data.expenses[idx]
    clean = {}
    for k, v in updates.items():
        if v is None:
            continue
        if k == "rollover" and isinstance(v, bool):
            clean[k] = "x" if v else ""
        else:
            clean[k] = v
    updated = current.model_copy(update=clean)
    data.expenses[idx] = updated
    write_month(data_dir, data)
    return updated


def delete_expense(data_dir: str, year: int, month: int, idx: int) -> bool:
    data = parse_month(data_dir, year, month)
    if data is None:
        return False
    if idx < 0 or idx >= len(data.expenses):
        return False
    data.expenses.pop(idx)
    write_month(data_dir, data)
    return True


# --- Caixa Items ---

def add_caixa_item(data_dir: str, year: int, month: int, item: CaixaItem) -> CaixaItem:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")
    data.caixas.append(item)
    write_month(data_dir, data)
    return item


def update_caixa_item(data_dir: str, year: int, month: int, idx: int,
                      updates: dict) -> CaixaItem | None:
    data = parse_month(data_dir, year, month)
    if data is None:
        return None
    if idx < 0 or idx >= len(data.caixas):
        return None
    current = data.caixas[idx]
    clean = {k: v for k, v in updates.items() if v is not None}
    updated = current.model_copy(update=clean)
    data.caixas[idx] = updated
    write_month(data_dir, data)
    return updated


def delete_caixa_item(data_dir: str, year: int, month: int, idx: int) -> bool:
    data = parse_month(data_dir, year, month)
    if data is None:
        return False
    if idx < 0 or idx >= len(data.caixas):
        return False
    data.caixas.pop(idx)
    write_month(data_dir, data)
    return True


# --- Emprestimo Items ---

def add_emprestimo(data_dir: str, year: int, month: int, item: Emprestimo) -> list[Emprestimo]:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")

    first = item.model_copy(update={"parcela_atual": 1})
    data.emprestimos.append(first)
    write_month(data_dir, data)
    created = [first]

    cur_year, cur_month = year, month
    for parcela_atual in range(2, item.parcelas + 1):
        cur_year, cur_month = _advance_month(cur_year, cur_month)
        next_data = parse_month(data_dir, cur_year, cur_month)
        if next_data is None:
            next_data = MonthData(year=cur_year, month=cur_month)
        row = item.model_copy(update={"parcela_atual": parcela_atual})
        next_data.emprestimos.append(row)
        write_month(data_dir, next_data)
        created.append(row)

    return created


def update_emprestimo_item(data_dir: str, year: int, month: int, idx: int,
                           updates: dict) -> Emprestimo | None:
    data = parse_month(data_dir, year, month)
    if data is None:
        return None
    if idx < 0 or idx >= len(data.emprestimos):
        return None
    current = data.emprestimos[idx]
    clean = {k: v for k, v in updates.items() if v is not None}
    updated = current.model_copy(update=clean)
    data.emprestimos[idx] = updated
    write_month(data_dir, data)
    return updated


def delete_emprestimo_item(data_dir: str, year: int, month: int, idx: int) -> bool:
    data = parse_month(data_dir, year, month)
    if data is None:
        return False
    if idx < 0 or idx >= len(data.emprestimos):
        return False
    data.emprestimos.pop(idx)
    write_month(data_dir, data)
    return True


def quitar_emprestimo(data_dir: str, year: int, month: int, idx: int) -> list[Emprestimo]:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")
    if idx < 0 or idx >= len(data.emprestimos):
        raise FileNotFoundError(f"Emprestimo at index {idx} not found")

    item = data.emprestimos[idx]
    remaining = item.parcelas - item.parcela_atual
    if remaining <= 0:
        raise ValueError(f"Emprestimo at index {idx} has no future installments")

    total = 0.0
    cur_year, cur_month = year, month
    for _ in range(remaining):
        cur_year, cur_month = _advance_month(cur_year, cur_month)
        future_data = parse_month(data_dir, cur_year, cur_month)
        if future_data is None:
            continue
        match_idxs = [
            i for i, e in enumerate(future_data.emprestimos)
            if e.pessoa == item.pessoa and e.description == item.description
            and e.data == item.data and e.parcelas == item.parcelas
        ]
        if not match_idxs:
            continue
        total += sum(future_data.emprestimos[i].valor for i in match_idxs)
        future_data.emprestimos = [
            e for i, e in enumerate(future_data.emprestimos) if i not in match_idxs
        ]
        write_month(data_dir, future_data)

    loan_row = Emprestimo(data=item.data, pessoa=item.pessoa, description=item.description,
                          valor=total, parcelas=1, parcela_atual=1)
    payment_row = Emprestimo(data=item.data, pessoa=item.pessoa, description=item.description,
                             valor=-total, parcelas=1, parcela_atual=1)
    data.emprestimos.append(loan_row)
    data.emprestimos.append(payment_row)
    write_month(data_dir, data)
    return [loan_row, payment_row]


def get_caixa_agregado(data_dir: str, year: int, month: int) -> list[dict]:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")
    tipos = set(c.tipo for c in data.caixas)
    result = []
    for tipo in sorted(tipos):
        total_pos = sum(c.valor for c in data.caixas if c.tipo == tipo and c.valor > 0)
        result.append({"tipo": tipo, "total_positivos": total_pos})
    return result


def get_caixa_saldos(data_dir: str, tipo: str | None = None) -> list[dict]:
    meses = list_months(data_dir)
    saldos: dict[str, float] = {}
    for m in meses:
        data = parse_month(data_dir, m["year"], m["month"])
        if data is None:
            continue
        for c in data.caixas:
            if tipo is None or c.tipo == tipo:
                key = f"{m['year']}-{m['month']:02d}"
                if key not in saldos:
                    saldos[key] = 0.0
                saldos[key] += c.valor

    if tipo:
        result = [{"mes": k, "saldo": v} for k, v in sorted(saldos.items())]
    else:
        totals: dict[str, float] = {}
        for t in parse_caixas_tipos(data_dir):
            totals[t.tipo] = 0.0
        for m in meses:
            data = parse_month(data_dir, m["year"], m["month"])
            if data is None:
                continue
            for c in data.caixas:
                totals[c.tipo] = totals.get(c.tipo, 0.0) + c.valor
        result = [{"tipo": k, "saldo": v} for k, v in sorted(totals.items())]
    return result


# --- Notes ---

def update_notes(data_dir: str, year: int, month: int, notes: str) -> MonthData:
    data = parse_month(data_dir, year, month)
    if data is None:
        data = MonthData(year=year, month=month)
    data.notes = notes
    write_month(data_dir, data)
    return data


# --- Categories ---

def _cat_path(data_dir: str) -> Path:
    return Path(data_dir) / "cat.md"


def parse_categories(data_dir: str) -> list[Category]:
    path = _cat_path(data_dir)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_categories_text(text)


def _parse_categories_text(text: str) -> list[Category]:
    categories: list[Category] = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            parts = stripped[2:].strip().split(maxsplit=1)
            if len(parts) == 1:
                categories.append(Category(name=parts[0], emoji=None))
            elif len(parts) == 2:
                name = parts[0]
                emoji = parts[1] if len(parts[1]) <= 2 else None
                categories.append(Category(name=name, emoji=emoji if emoji else None))
    return categories


def write_categories(data_dir: str, categories: list[Category]) -> None:
    lines = []
    for c in categories:
        line = f"- {c.name}"
        if c.emoji:
            line += f" {c.emoji}"
        lines.append(line)
    _cat_path(data_dir).write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_category(data_dir: str, category: Category) -> list[Category]:
    cats = parse_categories(data_dir)
    cats.append(category)
    write_categories(data_dir, cats)
    return cats


def update_category(data_dir: str, name: str, updates: dict) -> Category | None:
    cats = parse_categories(data_dir)
    for c in cats:
        if c.name == name:
            updated = c.model_copy(update={k: v for k, v in updates.items() if v is not None})
            cats[cats.index(c)] = updated
            write_categories(data_dir, cats)
            return updated
    return None


def delete_category(data_dir: str, name: str) -> bool:
    cats = parse_categories(data_dir)
    filtered = [c for c in cats if c.name != name]
    if len(filtered) == len(cats):
        return False
    write_categories(data_dir, filtered)
    return True


# --- Pessoas ---

def _pessoas_path(data_dir: str) -> Path:
    return Path(data_dir) / "pessoas.md"


def parse_pessoas(data_dir: str) -> list[Pessoa]:
    path = _pessoas_path(data_dir)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_pessoas_text(text)


def _parse_pessoas_text(text: str) -> list[Pessoa]:
    pessoas: list[Pessoa] = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            parts = stripped[2:].strip().split(maxsplit=1)
            if len(parts) == 1:
                pessoas.append(Pessoa(name=parts[0], emoji=None))
            elif len(parts) == 2:
                name = parts[0]
                emoji = parts[1] if len(parts[1]) <= 2 else None
                pessoas.append(Pessoa(name=name, emoji=emoji if emoji else None))
    return pessoas


def write_pessoas(data_dir: str, pessoas: list[Pessoa]) -> None:
    lines = []
    for p in pessoas:
        line = f"- {p.name}"
        if p.emoji:
            line += f" {p.emoji}"
        lines.append(line)
    _pessoas_path(data_dir).write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_pessoa(data_dir: str, pessoa: Pessoa) -> list[Pessoa]:
    pessoas = parse_pessoas(data_dir)
    pessoas.append(pessoa)
    write_pessoas(data_dir, pessoas)
    return pessoas


def update_pessoa(data_dir: str, name: str, updates: dict) -> Pessoa | None:
    pessoas = parse_pessoas(data_dir)
    for p in pessoas:
        if p.name == name:
            updated = p.model_copy(update={k: v for k, v in updates.items() if v is not None})
            pessoas[pessoas.index(p)] = updated
            write_pessoas(data_dir, pessoas)
            return updated
    return None


def delete_pessoa(data_dir: str, name: str) -> bool:
    pessoas = parse_pessoas(data_dir)
    filtered = [p for p in pessoas if p.name != name]
    if len(filtered) == len(pessoas):
        return False
    write_pessoas(data_dir, filtered)
    return True


# --- Caixa Tipos ---

def _caixas_tipos_path(data_dir: str) -> Path:
    return Path(data_dir) / "caixas.md"


def parse_caixas_tipos(data_dir: str) -> list[CaixaTipo]:
    path = _caixas_tipos_path(data_dir)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_caixas_tipos_text(text)


def _parse_caixas_tipos_text(text: str) -> list[CaixaTipo]:
    tipos: list[CaixaTipo] = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            parts = stripped[2:].strip().split(maxsplit=1)
            tipo = parts[0]
            emoji = parts[1] if len(parts) > 1 and len(parts[1]) <= 2 else None
            tipos.append(CaixaTipo(tipo=tipo, nome="", emoji=emoji))
    return tipos


def write_caixas_tipos(data_dir: str, tipos: list[CaixaTipo]) -> None:
    lines = []
    for t in tipos:
        line = f"- {t.tipo}"
        if t.emoji:
            line += f" {t.emoji}"
        lines.append(line)
    _caixas_tipos_path(data_dir).write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_caixa_tipo(data_dir: str, tipo: str, updates: dict) -> CaixaTipo | None:
    tipos = parse_caixas_tipos(data_dir)
    for t in tipos:
        if t.tipo == tipo:
            clean = {k: v for k, v in updates.items() if v is not None}
            updated = t.model_copy(update=clean)
            tipos[tipos.index(t)] = updated
            write_caixas_tipos(data_dir, tipos)
            return updated
    return None


# --- Month listing ---

def _month_from_name(name: str) -> int | None:
    try:
        return MONTH_NAMES.index(name.lower()) + 1
    except ValueError:
        return None


def list_months(data_dir: str) -> list[dict]:
    months: list[dict] = []
    base = Path(data_dir)
    if not base.exists():
        return months
    for year_dir in sorted(base.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for month in range(1, 13):
            path = _month_path(data_dir, year, month)
            if path.exists():
                data = parse_month(data_dir, year, month)
                if data:
                    months.append({"year": year, "month": month})
    return months
