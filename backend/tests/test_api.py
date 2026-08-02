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


def test_post_expense_with_dia_zero_is_allowed(client, data_dir):
    resp = client.post("/api/months/2026/1/expenses", json={
        "dia": 0, "description": "Assinatura mensal", "category": "Casa", "amount": 30.0,
    })
    assert resp.status_code == 201
    assert resp.json()["dia"] == 0


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


# --- Pessoas CRUD ---

def test_pessoas_crud(client, data_dir):
    resp = client.get("/api/pessoas")
    assert resp.status_code == 200
    assert resp.json() == []

    client.post("/api/pessoas", json={"name": "Heber", "emoji": "🧑"})
    client.post("/api/pessoas", json={"name": "Elaine", "emoji": "👩"})

    resp = client.get("/api/pessoas")
    assert len(resp.json()) == 2

    client.put("/api/pessoas/Heber", json={"emoji": "🧔"})
    resp = client.get("/api/pessoas")
    heber = next(p for p in resp.json() if p["name"] == "Heber")
    assert heber["emoji"] == "🧔"

    client.delete("/api/pessoas/Elaine")
    resp = client.get("/api/pessoas")
    assert len(resp.json()) == 1


def test_delete_pessoa_does_not_affect_existing_emprestimos(client, data_dir):
    client.post("/api/pessoas", json={"name": "Heber"})
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "05/01/26", "pessoa": "Heber", "description": "Remédio",
        "valor": 50.0, "parcelas": 1,
    })

    client.delete("/api/pessoas/Heber")

    resp = client.get("/api/months/2026/1")
    assert resp.json()["emprestimos"] == [
        {"data": "05/01/26", "pessoa": "Heber", "description": "Remédio",
         "valor": 50.0, "parcelas": 1, "parcela_atual": 1},
    ]


# --- Emprestimos CRUD ---

def test_add_single_installment_loan(client, data_dir):
    resp = client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Uber",
        "valor": 40.0,
    })
    assert resp.status_code == 201
    item = resp.json()
    assert item["parcelas"] == 1
    assert item["parcela_atual"] == 1

    resp = client.get("/api/months/2026/1")
    assert len(resp.json()["emprestimos"]) == 1


def test_emprestimo_does_not_affect_budget(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Empréstimo grande",
        "valor": 1000.0,
    })

    resp = client.get("/api/months/2026/1/dashboard")
    d = resp.json()
    assert d["total_spent"] == 1435.0  # unchanged from fixture (expenses + caixas positivos)
    assert d["remaining"] == 1565.0


def test_payment_is_a_negative_value_emprestimo(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Uber", "valor": 40.0,
    })
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "12/01/26", "pessoa": "Heber", "description": "Pagamento", "valor": -40.0,
    })

    resp = client.get("/api/months/2026/1")
    heber_items = [e for e in resp.json()["emprestimos"] if e["pessoa"] == "Heber"]
    assert sum(e["valor"] for e in heber_items) == 0.0


def test_edit_emprestimo_item(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Uber", "valor": 40.0,
    })
    resp = client.put("/api/months/2026/1/emprestimos/0", json={"valor": 45.0})
    assert resp.status_code == 200
    assert resp.json()["valor"] == 45.0


def test_delete_emprestimo_item(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Uber", "valor": 40.0,
    })
    resp = client.delete("/api/months/2026/1/emprestimos/0")
    assert resp.status_code == 204

    resp = client.get("/api/months/2026/1")
    assert resp.json()["emprestimos"] == []


def test_emprestimo_item_out_of_range_returns_404(client, data_dir):
    resp = client.put("/api/months/2026/1/emprestimos/0", json={"valor": 10.0})
    assert resp.status_code == 404
    resp = client.delete("/api/months/2026/1/emprestimos/0")
    assert resp.status_code == 404


# --- Emprestimos: installment spread ---

def test_multi_installment_loan_spreads_across_future_months(client, data_dir):
    resp = client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Geladeira",
        "valor": 300.0, "parcelas": 3,
    })
    assert resp.status_code == 201
    first = resp.json()
    assert first["parcela_atual"] == 1
    assert first["valor"] == 300.0

    jan = client.get("/api/months/2026/1").json()["emprestimos"]
    fev = client.get("/api/months/2026/2").json()["emprestimos"]
    mar = client.get("/api/months/2026/3").json()["emprestimos"]

    assert [e["parcela_atual"] for e in jan] == [1]
    assert [e["parcela_atual"] for e in fev] == [2]
    assert [e["parcela_atual"] for e in mar] == [3]
    assert all(e["valor"] == 300.0 for e in jan + fev + mar)
    assert all(e["data"] == "10/01/26" for e in jan + fev + mar)
    assert all(e["description"] == "Geladeira" for e in jan + fev + mar)


def test_multi_installment_loan_creates_missing_future_month_file(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Geladeira",
        "valor": 300.0, "parcelas": 2,
    })

    text = (data_dir / "2026" / "fev.md").read_text(encoding="utf-8")
    assert "## Emprestimos" in text
    assert "Geladeira" in text
    assert "| 10/01/26 | Heber | Geladeira | 300.00 | 2 | 2 |" in text


def test_multi_installment_loan_wraps_year(client, data_dir):
    client.put("/api/months/2026/12/budget", json={"budget": 1000})
    client.post("/api/months/2026/12/emprestimos", json={
        "data": "10/12/26", "pessoa": "Heber", "description": "Viagem",
        "valor": 100.0, "parcelas": 2,
    })

    resp = client.get("/api/months/2027/1")
    assert resp.status_code == 200
    assert len(resp.json()["emprestimos"]) == 1
    assert resp.json()["emprestimos"][0]["parcela_atual"] == 2


# --- Emprestimos: quitar antecipado ---

def test_quitar_antecipado_consolidates_remaining_into_current_month(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Geladeira",
        "valor": 300.0, "parcelas": 3,
    })

    resp = client.post("/api/months/2026/1/emprestimos/0/quitar")
    assert resp.status_code == 200
    new_rows = resp.json()
    assert len(new_rows) == 2
    assert sorted(r["valor"] for r in new_rows) == [-600.0, 600.0]

    jan = client.get("/api/months/2026/1").json()["emprestimos"]
    assert len(jan) == 3  # original parcela 1/3 + consolidated loan + payment
    assert sum(e["valor"] for e in jan if e["parcelas"] == 1) == 0.0

    fev = client.get("/api/months/2026/2").json()["emprestimos"]
    mar = client.get("/api/months/2026/3").json()["emprestimos"]
    assert fev == []
    assert mar == []


def test_quitar_antecipado_without_future_installments_returns_400(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Uber", "valor": 40.0,
    })
    resp = client.post("/api/months/2026/1/emprestimos/0/quitar")
    assert resp.status_code == 400


def test_quitar_antecipado_matches_series_ignoring_valor_and_parcela_atual(client, data_dir):
    client.post("/api/months/2026/1/emprestimos", json={
        "data": "10/01/26", "pessoa": "Heber", "description": "Geladeira",
        "valor": 300.0, "parcelas": 3,
    })
    # Renegotiate the 2nd installment's value before paying off early.
    fev_items = client.get("/api/months/2026/2").json()["emprestimos"]
    fev_idx = 0
    assert fev_items[fev_idx]["parcela_atual"] == 2
    client.put(f"/api/months/2026/2/emprestimos/{fev_idx}", json={"valor": 250.0})

    resp = client.post("/api/months/2026/1/emprestimos/0/quitar")
    assert resp.status_code == 200
    new_rows = resp.json()
    assert sorted(r["valor"] for r in new_rows) == [-550.0, 550.0]  # 250 + 300
