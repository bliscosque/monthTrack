from pathlib import Path

from monthtrack.models import MonthData, Expense, Category


def _month_path(data_dir: str, year: int, month: int) -> Path:
    return Path(data_dir) / str(year) / f"{month}.md"


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
    lines = [f"Budget: {data.budget}", "",
             "| Dia | Description | Category | Amount | Rollover |",
             "|-----|-------------|----------|--------|----------|"]
    for e in data.expenses:
        roll = " x" if e.rollover else ""
        lines.append(f"| {e.dia} | {e.description} | {e.category} | {e.amount:.2f} |{roll} |")
    return "\n".join(lines) + "\n"


def _parse_month_text(text: str, year: int, month: int) -> MonthData:
    lines = text.strip().splitlines()
    budget = 0.0
    expenses: list[Expense] = []
    header_found = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Budget:"):
            budget = float(stripped.removeprefix("Budget:").strip())
            continue

        if stripped.startswith("|---"):
            header_found = True
            continue

        if header_found and stripped.startswith("|"):
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            if len(parts) >= 4:
                dia = int(parts[0])
                description = parts[1]
                category = parts[2]
                amount = float(parts[3])
                rollover = len(parts) > 4 and parts[4].strip().lower() in ("x", "yes", "true")
                expenses.append(Expense(
                    dia=dia,
                    description=description,
                    category=category,
                    amount=amount,
                    rollover=rollover,
                ))

    return MonthData(year=year, month=month, budget=budget, expenses=expenses)


def _find_expense_index(expenses: list[Expense], dia: int) -> int | None:
    for i, e in enumerate(expenses):
        if e.dia == dia:
            return i
    return None


def add_expense(data_dir: str, year: int, month: int, expense: Expense) -> list[Expense]:
    data = parse_month(data_dir, year, month)
    if data is None:
        raise FileNotFoundError(f"Month {year}/{month} not found")

    if expense.rollover and data.remaining < expense.amount:
        room = max(0, data.remaining)
        capped_amount = min(expense.amount, room)
        overflow_amount = expense.amount - capped_amount

        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

        results = []
        if capped_amount > 0:
            capped = expense.model_copy(update={"amount": capped_amount, "rollover": False})
            data.expenses.append(capped)
            write_month(data_dir, data)
            results.append(capped)

        next_data = parse_month(data_dir, next_year, next_month)
        if next_data is None:
            next_data = MonthData(year=next_year, month=next_month, budget=0)
        overflow_expense = expense.model_copy(update={"amount": overflow_amount})
        next_data.expenses.append(overflow_expense)
        write_month(data_dir, next_data)
        results.append(overflow_expense)
        return results
    else:
        data.expenses.append(expense)
        write_month(data_dir, data)
        return [expense]


def update_expense(data_dir: str, year: int, month: int, dia: int,
                   updates: dict) -> Expense | None:
    data = parse_month(data_dir, year, month)
    if data is None:
        return None
    idx = _find_expense_index(data.expenses, dia)
    if idx is None:
        return None

    current = data.expenses[idx]
    updated = current.model_copy(update={k: v for k, v in updates.items() if v is not None})
    data.expenses[idx] = updated
    write_month(data_dir, data)
    return updated


def delete_expense(data_dir: str, year: int, month: int, dia: int) -> bool:
    data = parse_month(data_dir, year, month)
    if data is None:
        return False
    idx = _find_expense_index(data.expenses, dia)
    if idx is None:
        return False
    data.expenses.pop(idx)
    write_month(data_dir, data)
    return True


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


def list_months(data_dir: str) -> list[dict]:
    months: list[dict] = []
    base = Path(data_dir)
    if not base.exists():
        return months
    for year_dir in sorted(base.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for f in sorted(year_dir.glob("*.md")):
            month = int(f.stem)
            data = parse_month(data_dir, year, month)
            if data:
                months.append({"year": year, "month": month})
    return months
