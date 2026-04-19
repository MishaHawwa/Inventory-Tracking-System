"""
Test suite for InvTrack API.
Run with:  pytest tests/test_api.py -v
"""

import pytest
import asyncio
import os
os.environ["DB_PATH"] = ":memory:"   # Use in-memory SQLite for tests

from httpx import AsyncClient, ASGITransport
from main import app
from app.database.connection import init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    await init_db()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Products ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_products(client):
    res = await client.get("/api/products/")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_product(client):
    payload = {
        "name": "Test Widget",
        "sku": "TW-001",
        "category": "Electronics",
        "price": 29.99,
        "cost": 15.00,
        "stock": 50,
        "threshold": 10,
        "unit": "pcs",
        "supplier": "Test Supplier",
        "location": "A1-S1",
        "is_active": True,
    }
    res = await client.post("/api/products/", json=payload)
    assert res.status_code == 201
    p = res.json()
    assert p["sku"] == "TW-001"
    assert p["stock"] == 50
    assert p["status"] == "in_stock"
    return p["id"]


@pytest.mark.asyncio
async def test_create_duplicate_sku(client):
    payload = {"name": "Dupe", "sku": "TW-001", "price": 1.0, "cost": 0.5, "stock": 1, "threshold": 1, "is_active": True}
    res = await client.post("/api/products/", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_get_product(client):
    res = await client.get("/api/products/1")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_product_not_found(client):
    res = await client.get("/api/products/99999")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_patch_product(client):
    res = await client.patch("/api/products/1", json={"threshold": 25})
    assert res.status_code == 200
    assert res.json()["threshold"] == 25


@pytest.mark.asyncio
async def test_search_products(client):
    res = await client.get("/api/products/?search=cable")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_filter_by_category(client):
    res = await client.get("/api/products/?category=Electronics")
    assert res.status_code == 200
    for p in res.json()["items"]:
        assert p["category"] == "Electronics"


@pytest.mark.asyncio
async def test_export_csv(client):
    res = await client.get("/api/products/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "SKU" in res.text


# ── Transactions ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_stock_in(client):
    res = await client.post("/api/transactions/", json={
        "product_id": 1,
        "type": "IN",
        "quantity": 20,
        "reference": "PO-TEST-01",
        "performed_by": "test_user",
    })
    assert res.status_code == 201
    tx = res.json()
    assert tx["type"] == "IN"
    assert tx["quantity"] == 20


@pytest.mark.asyncio
async def test_create_stock_out(client):
    # First check current stock
    prod = (await client.get("/api/products/1")).json()
    initial_stock = prod["stock"]

    res = await client.post("/api/transactions/", json={
        "product_id": 1,
        "type": "OUT",
        "quantity": 5,
        "reference": "SO-TEST-01",
    })
    assert res.status_code == 201
    tx = res.json()
    assert tx["stock_after"] == initial_stock - 5


@pytest.mark.asyncio
async def test_insufficient_stock(client):
    res = await client.post("/api/transactions/", json={
        "product_id": 1,
        "type": "OUT",
        "quantity": 9999999,
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_adjustment(client):
    res = await client.post("/api/transactions/", json={
        "product_id": 1,
        "type": "ADJ",
        "quantity": 100,
        "note": "Physical count correction",
    })
    assert res.status_code == 201
    assert res.json()["stock_after"] == 100


@pytest.mark.asyncio
async def test_list_transactions(client):
    res = await client.get("/api/transactions/")
    assert res.status_code == 200
    assert "items" in res.json()


@pytest.mark.asyncio
async def test_filter_tx_by_type(client):
    res = await client.get("/api/transactions/?type=IN")
    assert res.status_code == 200
    for tx in res.json()["items"]:
        assert tx["type"] == "IN"


@pytest.mark.asyncio
async def test_product_transactions(client):
    res = await client.get("/api/transactions/product/1")
    assert res.status_code == 200


# ── Alerts ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_summary(client):
    res = await client.get("/api/alerts/")
    assert res.status_code == 200
    data = res.json()
    assert "total_alerts" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_alert_count(client):
    res = await client.get("/api/alerts/count")
    assert res.status_code == 200
    assert "total" in res.json()


@pytest.mark.asyncio
async def test_low_stock_alerts(client):
    res = await client.get("/api/alerts/low-stock")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_out_of_stock_alerts(client):
    res = await client.get("/api/alerts/out-of-stock")
    assert res.status_code == 200


# ── Reports ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_summary(client):
    res = await client.get("/api/reports/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_products" in data
    assert "total_stock_value" in data


@pytest.mark.asyncio
async def test_reports_categories(client):
    res = await client.get("/api/reports/categories")
    assert res.status_code == 200
    assert "categories" in res.json()


@pytest.mark.asyncio
async def test_reports_top_products(client):
    res = await client.get("/api/reports/top-products?metric=value&limit=5")
    assert res.status_code == 200
    assert "items" in res.json()


@pytest.mark.asyncio
async def test_reports_stock_movement(client):
    res = await client.get("/api/reports/stock-movement?days=30")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_reports_valuation(client):
    res = await client.get("/api/reports/valuation")
    assert res.status_code == 200
    data = res.json()
    assert "total_sell_value" in data
    assert "overall_margin_pct" in data


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete(client):
    # Create a product, then delete it
    p = (await client.post("/api/products/", json={
        "name": "To Delete", "sku": "DEL-001", "price": 1.0,
        "cost": 0.5, "stock": 5, "threshold": 1, "is_active": True,
    })).json()
    res = await client.delete(f"/api/products/{p['id']}")
    assert res.status_code == 204
    # Should not appear in default (is_active=True) listing
    listing = (await client.get("/api/products/?is_active=true")).json()
    assert all(x["id"] != p["id"] for x in listing["items"])
