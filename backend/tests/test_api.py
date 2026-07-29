import json


def test_list_months(client):
    resp = client.get("/api/months")
    assert resp.status_code == 200
    assert resp.json() == [{"year": 2026, "month": 1}]


def test_get_month_returns_budget_and_expenses(client):
    resp = client.get("/api/months/2026/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2026
    assert data["month"] == 1
    assert data["budget"] == 3000.0
    assert data["notes"] == "Meu mês de janeiro"
    assert data["expenses"] == [
        {"dia": 5, "description": "Almoço no centro", "category": "Restaurante",
         "amount": 35.0, "rollover": ""},
        {"dia": 10, "description": "Inscrição anual", "category": "Saúde",
         "amount": 400.0, "rollover": "x"},
    ]
    assert data["caixas"] == [
        {"data": 10, "tipo": "CP", "valor": 1000.0},
        {"data": 15, "tipo": "CC", "valor": -50.0},
    ]


def test_put_budget_updates_month_file(client, data_dir):
    resp = client.put("/api/months/2026/1/budget", json={"budget": 5000})
    assert resp.status_code == 200
    assert resp.json()["budget"] == 5000.0

    get_resp = client.get("/api/months/2026/1")
    assert get_resp.json()["budget"] == 5000.0

    text = (data_dir / "2026" / "jan.md").read_text(encoding="utf-8")
    assert "Budget: 5000" in text


def test_put_budget_creates_month_if_not_exists(client, data_dir):
    resp = client.put("/api/months/2026/3/budget", json={"budget": 2000})
    assert resp.status_code == 200
    assert resp.json()["budget"] == 2000.0

    assert (data_dir / "2026" / "mar.md").exists()
    text = (data_dir / "2026" / "mar.md").read_text(encoding="utf-8")
    assert "Budget: 2000" in text


def test_post_expense_adds_to_month(client, data_dir):
    resp = client.post("/api/months/2026/1/expenses", json={
        "dia": 15, "description": "Gasolina", "category": "Transporte", "amount": 120.0,
    })
    assert resp.status_code == 201
    exp = resp.json()
    assert exp["dia"] == 15
    assert exp["description"] == "Gasolina"

    get_resp = client.get("/api/months/2026/1")
    assert len(get_resp.json()["expenses"]) == 3


def test_post_expense_with_rollover_does_not_split_automatically(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 50})
    resp = client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })
    assert resp.status_code == 201
    exp = resp.json()
    assert exp["amount"] == 200.0
    assert exp["rollover"] == "x"

    assert client.get("/api/months/2026/2").status_code == 404


def test_rollover_manual(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 485})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })

    resp = client.post("/api/months/2026/1/expenses/2/rollover")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    original, overflow = results
    assert original["dia"] == 20
    assert original["amount"] == 0.0
    assert original["rollover"] == "200.0"
    assert original["description"] == "Compra grande"

    assert overflow["dia"] == 0
    assert overflow["amount"] == 200.0
    assert overflow["rollover"] == "x"
    assert overflow["description"] == "Compra grande"


def test_rollover_manual_remaining_zero(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 35})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })

    resp = client.post("/api/months/2026/1/expenses/2/rollover")
    assert resp.status_code == 200
    original, overflow = resp.json()
    assert original["amount"] == 0.0
    assert original["rollover"] == "200.0"
    assert overflow["amount"] == 200.0


def test_rollover_manual_not_eligible_returns_400(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 5000})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Normal", "category": "Casa", "amount": 100.0,
    })
    resp = client.post("/api/months/2026/1/expenses/2/rollover")
    assert resp.status_code == 400


def test_rollover_manual_already_rolled_returns_400(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 50})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })
    client.post("/api/months/2026/1/expenses/2/rollover")
    resp = client.post("/api/months/2026/1/expenses/2/rollover")
    assert resp.status_code == 400


def test_rollover_manual_wraps_year(client, data_dir):
    client.put("/api/months/2026/12/budget", json={"budget": 50})
    client.post("/api/months/2026/12/expenses", json={
        "dia": 31, "description": "Fim de ano", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })
    resp = client.post("/api/months/2026/12/expenses/0/rollover")
    assert resp.status_code == 200
    _, overflow = resp.json()

    month1 = client.get("/api/months/2027/1").json()
    carry = [e for e in month1["expenses"] if e["description"] == "Fim de ano"]
    assert len(carry) == 1
    assert carry[0]["amount"] == 150.0
    assert carry[0]["dia"] == 0
    assert carry[0]["rollover"] == "x"


def test_post_expense_without_rollover_stays_in_month(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 50})
    resp = client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Excesso sem rollover", "category": "Casa",
        "amount": 200.0, "rollover": False,
    })
    assert resp.status_code == 201
    assert resp.json()["rollover"] == ""
    assert client.get("/api/months/2026/2").status_code == 404


def test_put_expense_updates_expense(data_dir, client):
    client.put("/api/months/2026/1/budget", json={"budget": 5000})
    resp = client.post("/api/months/2026/1/expenses", json={
        "dia": 1, "description": "Teste", "category": "Casa", "amount": 100,
    })
    expense = resp.json()
    edit_resp = client.put(
        f"/api/months/2026/1/expenses/2",
        json={"description": "Teste editado", "amount": 150},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["description"] == "Teste editado"
    assert edit_resp.json()["amount"] == 150.0


def test_put_expense_toggles_rollover(data_dir, client):
    client.put("/api/months/2026/1/budget", json={"budget": 5000})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 1, "description": "Teste", "category": "Casa", "amount": 100,
    })
    edit_resp = client.put("/api/months/2026/1/expenses/2", json={"rollover": True})
    assert edit_resp.status_code == 200
    assert edit_resp.json()["rollover"] == "x"

    edit_resp = client.put("/api/months/2026/1/expenses/2", json={"rollover": False})
    assert edit_resp.status_code == 200
    assert edit_resp.json()["rollover"] == ""


def test_delete_expense_removes_expense(data_dir, client):
    client.put("/api/months/2026/1/budget", json={"budget": 5000})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 2, "description": "Pra deletar", "category": "Casa", "amount": 50,
    })

    del_resp = client.delete("/api/months/2026/1/expenses/2")
    assert del_resp.status_code == 204

    get_resp = client.get("/api/months/2026/1")
    assert len(get_resp.json()["expenses"]) == 2


def test_delete_expense_returns_404_if_not_found(client):
    resp = client.delete("/api/months/2026/1/expenses/99")
    assert resp.status_code == 404


def test_get_month_returns_404_for_missing_month(client):
    resp = client.get("/api/months/2099/12")
    assert resp.status_code == 404


def test_categories_crud(client, data_dir):
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    assert resp.json() == []

    client.post("/api/categories", json={"name": "Alimentação", "emoji": "🍔"})
    client.post("/api/categories", json={"name": "Transporte", "emoji": "🚗"})

    resp = client.get("/api/categories")
    assert len(resp.json()) == 2

    client.put("/api/categories/Alimentação", json={"emoji": "🥗"})
    resp = client.get("/api/categories")
    cat = next(c for c in resp.json() if c["name"] == "Alimentação")
    assert cat["emoji"] == "🥗"

    client.delete("/api/categories/Transporte")
    resp = client.get("/api/categories")
    assert len(resp.json()) == 1


def test_dashboard_month(client):
    resp = client.get("/api/months/2026/1/dashboard")
    assert resp.status_code == 200
    d = resp.json()
    assert d["budget"] == 3000.0
    assert d["total_spent"] == 1435.0
    assert d["remaining"] == 1565.0


def test_history(client):
    client.put("/api/months/2025/12/budget", json={"budget": 2000})
    client.post("/api/months/2025/12/expenses", json={
        "dia": 1, "description": "Teste", "category": "Casa", "amount": 500,
    })

    resp = client.get("/api/history")
    assert resp.status_code == 200
    points = resp.json()
    assert len(points) >= 2
    dec = next(p for p in points if p["year"] == 2025 and p["month"] == 12)
    assert dec["total_spent"] == 500.0
    assert dec["budget"] == 2000.0


def test_history_filtered_by_category(client):
    resp = client.get("/api/history?categories=Restaurante")
    assert resp.status_code == 200
    jan = next(p for p in resp.json() if p["year"] == 2026 and p["month"] == 1)
    assert jan["total_spent"] == 35.0


# --- Notes ---

def test_get_month_returns_notes(client):
    resp = client.get("/api/months/2026/1")
    assert resp.json()["notes"] == "Meu mês de janeiro"


def test_put_notes_updates(client, data_dir):
    resp = client.put("/api/months/2026/1/notes", json={"notes": "Nota atualizada"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Nota atualizada"

    get_resp = client.get("/api/months/2026/1")
    assert get_resp.json()["notes"] == "Nota atualizada"

    text = (data_dir / "2026" / "jan.md").read_text(encoding="utf-8")
    assert "Notas: Nota atualizada" in text


def test_put_notes_creates_month_if_not_exists(client, data_dir):
    resp = client.put("/api/months/2026/4/notes", json={"notes": "Novo mês"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Novo mês"


# --- Caixa Types ---

def test_list_caixa_tipos(client):
    resp = client.get("/api/caixas/tipos")
    assert resp.status_code == 200
    tipos = resp.json()
    assert len(tipos) == 3
    cp = next(t for t in tipos if t["tipo"] == "CP")
    assert cp["emoji"] == "🏦"


def test_update_caixa_tipo(client, data_dir):
    resp = client.put("/api/caixas/tipos/CP", json={"nome": "Caixa Principal", "emoji": "💰"})
    assert resp.status_code == 200
    assert resp.json()["emoji"] == "💰"

    text = (data_dir / "caixas.md").read_text(encoding="utf-8")
    assert "💰" in text


# --- Caixa Items CRUD ---

def test_add_caixa_item(client, data_dir):
    resp = client.post("/api/months/2026/1/caixas", json={
        "data": 20, "tipo": "CP", "valor": 500.0,
    })
    assert resp.status_code == 201
    item = resp.json()
    assert item["data"] == 20
    assert item["tipo"] == "CP"
    assert item["valor"] == 500.0

    month = client.get("/api/months/2026/1").json()
    assert len(month["caixas"]) == 3


def test_add_negative_caixa_item(client):
    resp = client.post("/api/months/2026/1/caixas", json={
        "data": 25, "tipo": "CC", "valor": -100.0,
    })
    assert resp.status_code == 201


def test_edit_caixa_item(client):
    resp = client.put("/api/months/2026/1/caixas/0", json={"valor": 2000.0})
    assert resp.status_code == 200
    assert resp.json()["valor"] == 2000.0

    month = client.get("/api/months/2026/1").json()
    assert month["caixas"][0]["valor"] == 2000.0


def test_delete_caixa_item(client):
    resp = client.delete("/api/months/2026/1/caixas/1")
    assert resp.status_code == 204

    month = client.get("/api/months/2026/1").json()
    assert len(month["caixas"]) == 1


def test_caixa_item_out_of_range_returns_404(client):
    resp = client.put("/api/months/2026/1/caixas/99", json={"valor": 100})
    assert resp.status_code == 404

    resp = client.delete("/api/months/2026/1/caixas/99")
    assert resp.status_code == 404


# --- Caixa Saldos ---

def test_caixa_saldos_consolidado(client, data_dir):
    client.put("/api/months/2026/2/budget", json={"budget": 1000})
    client.post("/api/months/2026/2/caixas", json={
        "data": 1, "tipo": "CP", "valor": 200.0,
    })

    resp = client.get("/api/caixas/saldos")
    assert resp.status_code == 200
    saldos = resp.json()
    cp = next(s for s in saldos if s["tipo"] == "CP")
    assert cp["saldo"] == 1200.0  # 1000 (fixture) + 200

    cc = next(s for s in saldos if s["tipo"] == "CC")
    assert cc["saldo"] == -50.0

    cb = next(s for s in saldos if s["tipo"] == "CB")
    assert cb["saldo"] == 0.0


def test_caixa_saldos_por_mes(client, data_dir):
    client.put("/api/months/2026/2/budget", json={"budget": 1000})
    client.post("/api/months/2026/2/caixas", json={
        "data": 1, "tipo": "CP", "valor": 200.0,
    })

    resp = client.get("/api/caixas/saldos?tipo=CP")
    assert resp.status_code == 200
    breakdown = resp.json()
    jan = next(b for b in breakdown if b["mes"] == "2026-01")
    assert jan["saldo"] == 1000.0
    fev = next(b for b in breakdown if b["mes"] == "2026-02")
    assert fev["saldo"] == 200.0


# --- Caixa Monthly View (positive-only aggregation) ---

def test_caixa_agregacao_mensal_positivos(client):
    client.post("/api/months/2026/1/caixas", json={
        "data": 20, "tipo": "CP", "valor": 500.0,
    })
    client.post("/api/months/2026/1/caixas", json={
        "data": 25, "tipo": "CP", "valor": -30.0,
    })

    resp = client.get("/api/months/2026/1/caixas/agregado")
    assert resp.status_code == 200
    agg = resp.json()
    cp = next(a for a in agg if a["tipo"] == "CP")
    assert cp["total_positivos"] == 1500.0  # 1000 (fixture) + 500
