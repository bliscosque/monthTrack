import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from monthtrack.app import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    (d / "2026").mkdir()
    (d / "2026" / "jan.md").write_text(
        "Budget: 3000\n\n"
        "| Dia | Description | Category | Amount | Rollover |\n"
        "|-----|-------------|----------|--------|----------|\n"
        "| 5 | Almoço no centro | Restaurante | 35.00 | |\n"
        "| 10 | Inscrição anual | Saúde | 400.00 | x |\n"
    )
    return d


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    app = create_app(data_dir=str(data_dir))
    return TestClient(app)
