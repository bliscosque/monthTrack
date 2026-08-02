from pydantic import BaseModel, Field, field_validator


class Expense(BaseModel):
    dia: int = Field(ge=0, le=31)
    description: str
    category: str
    amount: float = Field(ge=0)
    rollover: str = ""

    @field_validator("rollover", mode="before")
    @classmethod
    def coerce_rollover(cls, v):
        if isinstance(v, bool):
            return "x" if v else ""
        return v


class CaixaItem(BaseModel):
    data: int = Field(ge=0, le=31)
    tipo: str
    valor: float


class CaixaTipo(BaseModel):
    tipo: str
    nome: str = ""
    emoji: str | None = None


class Emprestimo(BaseModel):
    data: str
    pessoa: str
    description: str
    valor: float
    parcelas: int = Field(default=1, ge=1)
    parcela_atual: int = Field(default=1, ge=1)


class MonthData(BaseModel):
    year: int = Field(ge=1970)
    month: int = Field(ge=1, le=12)
    budget: float = Field(default=0, ge=0)
    notes: str = ""
    expenses: list[Expense] = []
    caixas: list[CaixaItem] = []
    emprestimos: list[Emprestimo] = []

    @property
    def total_spent(self) -> float:
        expenses_sum = sum(e.amount for e in self.expenses)
        caixas_pos = sum(c.valor for c in self.caixas if c.valor > 0)
        return expenses_sum + caixas_pos

    @property
    def remaining(self) -> float:
        return self.budget - self.total_spent


class Category(BaseModel):
    name: str
    emoji: str | None = None


class BudgetUpdate(BaseModel):
    budget: float = Field(ge=0)


class ExpenseCreate(BaseModel):
    dia: int = Field(ge=0, le=31)
    description: str
    category: str
    amount: float = Field(gt=0)
    rollover: bool = False


class ExpenseUpdate(BaseModel):
    dia: int | None = None
    description: str | None = None
    category: str | None = None
    amount: float | None = Field(default=None, gt=0)
    rollover: bool | None = None


class CategoryCreate(BaseModel):
    name: str
    emoji: str | None = None


class CategoryUpdate(BaseModel):
    emoji: str | None = None


class Pessoa(BaseModel):
    name: str
    emoji: str | None = None


class PessoaCreate(BaseModel):
    name: str
    emoji: str | None = None


class PessoaUpdate(BaseModel):
    emoji: str | None = None


class EmprestimoCreate(BaseModel):
    data: str
    pessoa: str
    description: str
    valor: float
    parcelas: int = Field(default=1, ge=1)


class EmprestimoUpdate(BaseModel):
    data: str | None = None
    pessoa: str | None = None
    description: str | None = None
    valor: float | None = None
    parcelas: int | None = Field(default=None, ge=1)
    parcela_atual: int | None = Field(default=None, ge=1)


class DashboardMonth(BaseModel):
    year: int
    month: int
    budget: float
    total_spent: float
    remaining: float
    expenses: list[Expense]


class HistoricalPoint(BaseModel):
    year: int
    month: int
    total_spent: float
    budget: float
