from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from monthtrack.models import (
    MonthData, BudgetUpdate, ExpenseCreate, ExpenseUpdate,
    CategoryCreate, CategoryUpdate, DashboardMonth, HistoricalPoint,
    Expense, Category,
)
from monthtrack.storage import (
    parse_month, write_month, add_expense, update_expense, delete_expense,
    parse_categories, add_category, update_category, delete_category,
    list_months,
)


def create_app(data_dir: str = "data") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        cat_path = Path(data_dir) / "cat.md"
        if not cat_path.exists():
            initial = [
                "Gym", "Lazer", "Presentes", "Restaurante",
                "Mercado", "Casa", "Pessoal", "Saúde",
            ]
            cat_path.write_text("\n".join(f"- {c}" for c in initial) + "\n", encoding="utf-8")
        yield

    app = FastAPI(title="monthTrack", lifespan=lifespan)
    app.state.data_dir = data_dir

    @app.get("/api/months")
    def get_months():
        return list_months(app.state.data_dir)

    @app.get("/api/months/{year}/{month}")
    def get_month(year: int, month: int):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            raise HTTPException(status_code=404, detail="Month not found")
        return data.model_dump()

    @app.put("/api/months/{year}/{month}/budget")
    def set_budget(year: int, month: int, body: BudgetUpdate):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            data = MonthData(year=year, month=month, budget=body.budget)
        else:
            data.budget = body.budget
        write_month(app.state.data_dir, data)
        return data.model_dump()

    @app.post("/api/months/{year}/{month}/expenses", status_code=201)
    def create_expense(year: int, month: int, body: ExpenseCreate):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            raise HTTPException(status_code=404, detail="Month not found")
        try:
            results = add_expense(app.state.data_dir, year, month,
                                  Expense(**body.model_dump()))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Month not found")
        return results[0].model_dump()

    @app.put("/api/months/{year}/{month}/expenses/{dia}")
    def edit_expense(year: int, month: int, dia: int, body: ExpenseUpdate):
        result = update_expense(app.state.data_dir, year, month, dia, body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        return result.model_dump()

    @app.delete("/api/months/{year}/{month}/expenses/{dia}", status_code=204)
    def remove_expense(year: int, month: int, dia: int):
        ok = delete_expense(app.state.data_dir, year, month, dia)
        if not ok:
            raise HTTPException(status_code=404, detail="Expense not found")

    @app.get("/api/months/{year}/{month}/dashboard")
    def month_dashboard(year: int, month: int):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            raise HTTPException(status_code=404, detail="Month not found")
        return DashboardMonth(
            year=data.year, month=data.month,
            budget=data.budget, total_spent=data.total_spent,
            remaining=data.remaining,
            expenses=data.expenses,
        ).model_dump()

    @app.get("/api/history")
    def history(categories: str | None = None):
        all_months = list_months(app.state.data_dir)
        points = []
        for m in all_months:
            data = parse_month(app.state.data_dir, m["year"], m["month"])
            if data is None:
                continue

            if categories:
                cat_list = [c.strip() for c in categories.split(",")]
                total = sum(e.amount for e in data.expenses if e.category in cat_list)
            else:
                total = data.total_spent

            points.append(HistoricalPoint(
                year=m["year"], month=m["month"],
                total_spent=total, budget=data.budget,
            ))
        return [p.model_dump() for p in points]

    @app.get("/api/categories")
    def get_categories():
        cats = parse_categories(app.state.data_dir)
        return [c.model_dump() for c in cats]

    @app.post("/api/categories", status_code=201)
    def create_category(body: CategoryCreate):
        cat = Category(**body.model_dump())
        cats = add_category(app.state.data_dir, cat)
        return cat.model_dump()

    @app.put("/api/categories/{name}")
    def edit_category(name: str, body: CategoryUpdate):
        result = update_category(app.state.data_dir, name, body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return result.model_dump()

    @app.delete("/api/categories/{name}", status_code=204)
    def remove_category(name: str):
        ok = delete_category(app.state.data_dir, name)
        if not ok:
            raise HTTPException(status_code=404, detail="Category not found")

    here = Path(__file__).resolve().parent.parent.parent
    frontend_dir = here / "frontend"

    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/")
        @app.get("/{path:path}")
        def serve_frontend(path: str = ""):
                if path.startswith("api/"):
                    return JSONResponse({"detail": "Not found"}, status_code=404)
                index = frontend_dir / "index.html"
                if not index.exists():
                    return JSONResponse({"detail": "Frontend not found"}, status_code=404)
                return FileResponse(str(index))

    return app


app = create_app()
