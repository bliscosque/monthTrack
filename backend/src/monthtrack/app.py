import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from monthtrack.models import (
    MonthData, BudgetUpdate, ExpenseCreate, ExpenseUpdate,
    CategoryCreate, CategoryUpdate, DashboardMonth, HistoricalPoint,
    Expense, Category, CaixaItem, CaixaTipo,
)
from monthtrack.security import create_access_token, get_password_hash, require_auth, verify_password
from monthtrack.storage import (
    parse_month, write_month, add_expense, update_expense, delete_expense,
    parse_categories, add_category, update_category, delete_category,
    list_months, execute_rollover, update_notes,
    add_caixa_item, update_caixa_item, delete_caixa_item,
    get_caixa_agregado, get_caixa_saldos,
    parse_caixas_tipos, update_caixa_tipo,
)


class LoginRequest(BaseModel):
    password: str


class NotesBody(BaseModel):
    notes: str


class CaixaItemCreate(BaseModel):
    data: int
    tipo: str
    valor: float


class CaixaItemUpdate(BaseModel):
    data: int | None = None
    tipo: str | None = None
    valor: float | None = None


class CaixaTipoUpdate(BaseModel):
    nome: str | None = None
    emoji: str | None = None


def _init_password() -> str:
    pw = os.getenv("APP_PASSWORD")
    if pw:
        h = get_password_hash(pw)
        print(f"[monthTrack] Senha configurada via APP_PASSWORD")
        return h
    import secrets
    default_pw = secrets.token_urlsafe(8)
    h = get_password_hash(default_pw)
    print(f"[monthTrack] ========================================")
    print(f"[monthTrack]  SENHA PADRÃO: {default_pw}")
    print(f"[monthTrack]  Defina APP_PASSWORD no .env para trocar")
    print(f"[monthTrack] ========================================")
    return h


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
        caixas_path = Path(data_dir) / "caixas.md"
        if not caixas_path.exists():
            caixas_path.write_text("- CP 🏦\n- CC 💳\n- CB 🎁\n", encoding="utf-8")
        yield

    app = FastAPI(title="monthTrack", lifespan=lifespan)
    app.state.data_dir = data_dir
    app.state.password_hash = _init_password()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=[],
        allow_headers=[],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.post("/api/auth/login")
    def login(body: LoginRequest):
        pw_hash = app.state.password_hash
        if not pw_hash or not verify_password(body.password, pw_hash):
            raise HTTPException(status_code=401, detail="Senha inválida")
        token = create_access_token()
        return {"access_token": token, "token_type": "bearer"}

    @app.get("/api/months")
    def get_months(_=Depends(require_auth)):
        return list_months(app.state.data_dir)

    @app.get("/api/months/{year}/{month}")
    def get_month(year: int, month: int, _=Depends(require_auth)):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            raise HTTPException(status_code=404, detail="Month not found")
        return data.model_dump()

    @app.put("/api/months/{year}/{month}/budget")
    def set_budget(year: int, month: int, body: BudgetUpdate, _=Depends(require_auth)):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            data = MonthData(year=year, month=month, budget=body.budget)
        else:
            data.budget = body.budget
        write_month(app.state.data_dir, data)
        return data.model_dump()

    @app.put("/api/months/{year}/{month}/notes")
    def set_notes(year: int, month: int, body: NotesBody, _=Depends(require_auth)):
        data = update_notes(app.state.data_dir, year, month, body.notes)
        return data.model_dump()

    @app.post("/api/months/{year}/{month}/expenses", status_code=201)
    def create_expense(year: int, month: int, body: ExpenseCreate, _=Depends(require_auth)):
        data = parse_month(app.state.data_dir, year, month)
        if data is None:
            raise HTTPException(status_code=404, detail="Month not found")
        try:
            expense = add_expense(app.state.data_dir, year, month,
                                  Expense(**body.model_dump()))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Month not found")
        return expense.model_dump()

    @app.put("/api/months/{year}/{month}/expenses/{dia}")
    def edit_expense(year: int, month: int, dia: int, body: ExpenseUpdate, _=Depends(require_auth)):
        result = update_expense(app.state.data_dir, year, month, dia, body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        return result.model_dump()

    @app.delete("/api/months/{year}/{month}/expenses/{dia}", status_code=204)
    def remove_expense(year: int, month: int, dia: int, _=Depends(require_auth)):
        ok = delete_expense(app.state.data_dir, year, month, dia)
        if not ok:
            raise HTTPException(status_code=404, detail="Expense not found")

    @app.post("/api/months/{year}/{month}/expenses/{dia}/rollover")
    def rollover_expense(year: int, month: int, dia: int, _=Depends(require_auth)):
        try:
            results = execute_rollover(app.state.data_dir, year, month, dia)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Expense not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Expense not eligible for rollover")
        return [r.model_dump() for r in results]

    @app.post("/api/months/{year}/{month}/caixas", status_code=201)
    def create_caixa_item(year: int, month: int, body: CaixaItemCreate, _=Depends(require_auth)):
        try:
            item = add_caixa_item(app.state.data_dir, year, month, CaixaItem(**body.model_dump()))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Month not found")
        return item.model_dump()

    @app.put("/api/months/{year}/{month}/caixas/{idx}")
    def edit_caixa_item(year: int, month: int, idx: int, body: CaixaItemUpdate, _=Depends(require_auth)):
        result = update_caixa_item(app.state.data_dir, year, month, idx,
                                   body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Caixa item not found")
        return result.model_dump()

    @app.delete("/api/months/{year}/{month}/caixas/{idx}", status_code=204)
    def remove_caixa_item(year: int, month: int, idx: int, _=Depends(require_auth)):
        ok = delete_caixa_item(app.state.data_dir, year, month, idx)
        if not ok:
            raise HTTPException(status_code=404, detail="Caixa item not found")

    @app.get("/api/months/{year}/{month}/caixas/agregado")
    def caixa_agregado(year: int, month: int, _=Depends(require_auth)):
        try:
            return get_caixa_agregado(app.state.data_dir, year, month)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Month not found")

    @app.get("/api/months/{year}/{month}/dashboard")
    def month_dashboard(year: int, month: int, _=Depends(require_auth)):
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
    def history(categories: str | None = None, _=Depends(require_auth)):
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
    def get_categories(_=Depends(require_auth)):
        cats = parse_categories(app.state.data_dir)
        return [c.model_dump() for c in cats]

    @app.post("/api/categories", status_code=201)
    def create_category(body: CategoryCreate, _=Depends(require_auth)):
        cat = Category(**body.model_dump())
        cats = add_category(app.state.data_dir, cat)
        return cat.model_dump()

    @app.put("/api/categories/{name}")
    def edit_category(name: str, body: CategoryUpdate, _=Depends(require_auth)):
        result = update_category(app.state.data_dir, name, body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return result.model_dump()

    @app.delete("/api/categories/{name}", status_code=204)
    def remove_category(name: str, _=Depends(require_auth)):
        ok = delete_category(app.state.data_dir, name)
        if not ok:
            raise HTTPException(status_code=404, detail="Category not found")

    @app.get("/api/caixas/tipos")
    def get_caixa_tipos(_=Depends(require_auth)):
        tipos = parse_caixas_tipos(app.state.data_dir)
        return [t.model_dump() for t in tipos]

    @app.put("/api/caixas/tipos/{tipo}")
    def edit_caixa_tipo(tipo: str, body: CaixaTipoUpdate, _=Depends(require_auth)):
        result = update_caixa_tipo(app.state.data_dir, tipo, body.model_dump(exclude_none=True))
        if result is None:
            raise HTTPException(status_code=404, detail="Caixa type not found")
        return result.model_dump()

    @app.get("/api/caixas/saldos")
    def caixa_saldos(tipo: str | None = None, _=Depends(require_auth)):
        return get_caixa_saldos(app.state.data_dir, tipo)

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


app = create_app(data_dir=os.getenv("DATA_DIR", "data"))
