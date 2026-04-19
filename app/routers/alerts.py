"""
Alerts Router — Real-time low-stock and out-of-stock alerts.

Endpoints:
  GET /api/alerts                  — summary of all active alerts
  GET /api/alerts/out-of-stock     — only out-of-stock products
  GET /api/alerts/low-stock        — only low-stock products (stock > 0 but <= threshold)
  GET /api/alerts/count            — just the count (for badge updates)
"""

from fastapi import APIRouter, Depends
from app.database.connection import get_db
from app.schemas.reports import AlertItem, AlertSummary

router = APIRouter()


async def _build_alert_item(p: dict, db) -> dict:
    """Compute days-to-empty from recent OUT transaction rate."""
    # Get units dispatched in last 30 days for this product
    rate_row = await db.execute("""
        SELECT COALESCE(SUM(quantity), 0) as total_out
        FROM transactions
        WHERE product_id = ? AND type = 'OUT'
          AND created_at >= datetime('now', '-30 days')
    """, (p["id"],))
    rate_data   = await rate_row.fetchone()
    monthly_out = rate_data["total_out"] if rate_data else 0
    daily_rate  = monthly_out / 30 if monthly_out > 0 else 0
    days_to_empty = int(p["stock"] / daily_rate) if daily_rate > 0 and p["stock"] > 0 else None

    alert_type = "out_of_stock" if p["stock"] == 0 else "low_stock"
    severity   = "critical"     if p["stock"] == 0 else "warning"

    return {
        "id":            p["id"],
        "name":          p["name"],
        "sku":           p["sku"],
        "category":      p["category"],
        "stock":         p["stock"],
        "threshold":     p["threshold"],
        "supplier":      p.get("supplier"),
        "location":      p.get("location"),
        "price":         p["price"],
        "stock_value":   round(p["price"] * p["stock"], 2),
        "alert_type":    alert_type,
        "severity":      severity,
        "days_to_empty": days_to_empty,
    }


@router.get("/", response_model=AlertSummary)
async def get_all_alerts(db=Depends(get_db)):
    rows = await db.execute("""
        SELECT * FROM products
        WHERE is_active = 1 AND stock <= threshold
        ORDER BY stock ASC, name ASC
    """)
    products = [dict(r) for r in await rows.fetchall()]

    items           = [await _build_alert_item(p, db) for p in products]
    out_of_stock    = [i for i in items if i["alert_type"] == "out_of_stock"]
    low_stock       = [i for i in items if i["alert_type"] == "low_stock"]
    critical_value  = sum(
        p["price"] * p["threshold"]
        for p in products
    )

    return {
        "total_alerts":   len(items),
        "out_of_stock":   len(out_of_stock),
        "low_stock":      len(low_stock),
        "critical_value": round(critical_value, 2),
        "items":          items,
    }


@router.get("/out-of-stock")
async def get_out_of_stock(db=Depends(get_db)):
    rows = await db.execute("""
        SELECT * FROM products WHERE is_active=1 AND stock=0 ORDER BY name
    """)
    products = [dict(r) for r in await rows.fetchall()]
    items    = [await _build_alert_item(p, db) for p in products]
    return {"count": len(items), "items": items}


@router.get("/low-stock")
async def get_low_stock(db=Depends(get_db)):
    rows = await db.execute("""
        SELECT * FROM products
        WHERE is_active=1 AND stock > 0 AND stock <= threshold
        ORDER BY stock ASC
    """)
    products = [dict(r) for r in await rows.fetchall()]
    items    = [await _build_alert_item(p, db) for p in products]
    return {"count": len(items), "items": items}


@router.get("/count")
async def get_alert_count(db=Depends(get_db)):
    row = await db.execute("""
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS out_of_stock,
          SUM(CASE WHEN stock > 0 AND stock <= threshold THEN 1 ELSE 0 END) AS low_stock
        FROM products WHERE is_active=1 AND stock <= threshold
    """)
    data = dict(await row.fetchone())
    return data
