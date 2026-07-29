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
    assert data["expenses"] == [
        {"dia": 5, "description": "Almoço no centro", "category": "Restaurante",
         "amount": 35.0, "rollover": ""},
        {"dia": 10, "description": "Inscrição anual", "category": "Saúde",
         "amount": 400.0, "rollover": "x"},
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

    resp = client.post("/api/months/2026/1/expenses/20/rollover")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    original, overflow = results
    assert original["dia"] == 20
    assert original["amount"] == 50.0
    assert original["rollover"] == "200.0"
    assert original["description"] == "Compra grande"

    assert overflow["dia"] == 0
    assert overflow["amount"] == 150.0
    assert overflow["rollover"] == "x"
    assert overflow["description"] == "Compra grande"


def test_rollover_manual_remaining_zero(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 35})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })

    resp = client.post("/api/months/2026/1/expenses/20/rollover")
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
    resp = client.post("/api/months/2026/1/expenses/20/rollover")
    assert resp.status_code == 400


def test_rollover_manual_already_rolled_returns_400(client, data_dir):
    client.put("/api/months/2026/1/budget", json={"budget": 50})
    client.post("/api/months/2026/1/expenses", json={
        "dia": 20, "description": "Compra grande", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })
    client.post("/api/months/2026/1/expenses/20/rollover")
    resp = client.post("/api/months/2026/1/expenses/20/rollover")
    assert resp.status_code == 400


def test_rollover_manual_wraps_year(client, data_dir):
    client.put("/api/months/2026/12/budget", json={"budget": 50})
    client.post("/api/months/2026/12/expenses", json={
        "dia": 31, "description": "Fim de ano", "category": "Casa",
        "amount": 200.0, "rollover": True,
    })
    resp = client.post("/api/months/2026/12/expenses/31/rollover")
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
        f"/api/months/2026/1/expenses/{expense['dia']}",
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
    edit_resp = client.put("/api/months/2026/1/expenses/1", json={"rollover": True})
    assert edit_resp.status_code == 200
    assert edit_resp.json()["rollover"] == "x"

    edit_resp = client.put("/api/months/2026/1/expenses/1", json={"rollover": False})
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
    assert d["total_spent"] == 435.0
    assert d["remaining"] == 2565.0


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
