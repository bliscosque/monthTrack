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


class MonthData(BaseModel):
    year: int = Field(ge=1970)
    month: int = Field(ge=1, le=12)
    budget: float = Field(ge=0)
    expenses: list[Expense] = []

    @property
    def total_spent(self) -> float:
        return sum(e.amount for e in self.expenses)

    @property
    def remaining(self) -> float:
        return self.budget - self.total_spent


class Category(BaseModel):
    name: str
    emoji: str | None = None


class BudgetUpdate(BaseModel):
    budget: float = Field(ge=0)


class ExpenseCreate(BaseModel):
    dia: int = Field(ge=1, le=31)
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
