import os

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from monthtrack.app import create_app
from monthtrack.security import require_auth


@pytest.fixture(autouse=True)
def _set_test_password():
    os.environ.setdefault("APP_PASSWORD", "test-pw-123")


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    (d / "2026").mkdir()
    (d / "2026" / "jan.md").write_text(
        "Budget: 3000\n"
        "Notas: Meu mês de janeiro\n\n"
        "| Dia | Description | Category | Amount | Rollover |\n"
        "|-----|-------------|----------|--------|----------|\n"
        "| 5 | Almoço no centro | Restaurante | 35.00 | |\n"
        "| 10 | Inscrição anual | Saúde | 400.00 | x |\n"
        "\n"
        "## Caixas\n"
        "| Data | Tipo | Valor |\n"
        "|------|------|-------|\n"
        "| 10 | CP | 1000.00 |\n"
        "| 15 | CC | -50.00 |\n"
    )
    (d / "caixas.md").write_text("- CP 🏦\n- CC 💳\n- CB 🎁\n")
    return d


async def _noop_auth():
    return True


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    app = create_app(data_dir=str(data_dir))
    app.dependency_overrides[require_auth] = _noop_auth
    return TestClient(app)
