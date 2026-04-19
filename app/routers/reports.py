"""
Reports Router — Business intelligence and inventory analytics.

Endpoints:
  GET /api/reports/summary          — full KPI dashboard data
  GET /api/reports/categories       — stock breakdown by category
  GET /api/reports/top-products     — top products by value / movement
  GET /api/reports/stock-movement   — stock in/out movement per product
  GET /api/reports/transactions     — transaction trends over time
  GET /api/reports/valuation        — full valuation report
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database.connection import get_db

router = APIRouter()


@router.get("/summary")
async def get_summary(db=Depends(get_db)):
    """Complete KPI summary for the dashboard."""

    # ── Product KPIs ──────────────────────────────────────────────────────────
    prod_row = await db.execute("""
        SELECT
          COUNT(*)                                         AS total_products,
          SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END)    AS active_products,
          SUM(CASE WHEN is_active=1 THEN stock ELSE 0 END) AS total_units,
          ROUND(SUM(CASE WHEN is_active=1 THEN price*stock ELSE 0 END), 2) AS stock_value,
          ROUND(SUM(CASE WHEN is_active=1 THEN cost*stock  ELSE 0 END), 2) AS cost_value,
          SUM(CASE WHEN is_active=1 AND stock=0 THEN 1 ELSE 0 END)             AS out_of_stock,
          SUM(CASE WHEN is_active=1 AND stock>0 AND stock<=threshold THEN 1 ELSE 0 END) AS low_stock,
          COUNT(DISTINCT category)                         AS categories_count
        FROM products
    """)
    prod = dict(await prod_row.fetchone())

    # ── Transaction KPIs (last 30 days) ───────────────────────────────────────
    tx_row = await db.execute("""
        SELECT
          COUNT(*)                                               AS total_tx,
          SUM(CASE WHEN type='IN'  THEN quantity ELSE 0 END)    AS units_in,
          SUM(CASE WHEN type='OUT' THEN quantity ELSE 0 END)    AS units_out,
          ROUND(SUM(CASE WHEN type='IN'  THEN total_value ELSE 0 END), 2) AS value_in,
          ROUND(SUM(CASE WHEN type='OUT' THEN total_value ELSE 0 END), 2) AS value_out
        FROM transactions
        WHERE created_at >= datetime('now', '-30 days')
    """)
    tx = dict(await tx_row.fetchone())

    total_tx_row = await db.execute("SELECT COUNT(*) as c FROM transactions")
    total_tx     = (await total_tx_row.fetchone())["c"]

    return {
        "total_products":       prod["total_products"],
        "active_products":      prod["active_products"],
        "total_stock_units":    prod["total_units"] or 0,
        "total_stock_value":    prod["stock_value"] or 0.0,
        "total_cost_value":     prod["cost_value"]  or 0.0,
        "potential_profit":     round((prod["stock_value"] or 0) - (prod["cost_value"] or 0), 2),
        "out_of_stock_count":   prod["out_of_stock"],
        "low_stock_count":      prod["low_stock"],
        "categories_count":     prod["categories_count"],
        "total_transactions":   total_tx,
        "units_received_30d":   tx["units_in"]  or 0,
        "units_dispatched_30d": tx["units_out"] or 0,
        "value_received_30d":   tx["value_in"]  or 0.0,
        "value_dispatched_30d": tx["value_out"] or 0.0,
        "tx_count_30d":         tx["total_tx"],
    }


@router.get("/categories")
async def get_category_breakdown(db=Depends(get_db)):
    """Stock value and count broken down by category."""
    rows = await db.execute("""
        SELECT
          category,
          COUNT(*)                              AS product_count,
          SUM(stock)                            AS total_stock,
          ROUND(SUM(price * stock), 2)          AS stock_value,
          ROUND(SUM(cost  * stock), 2)          AS cost_value
        FROM products
        WHERE is_active = 1
        GROUP BY category
        ORDER BY stock_value DESC
    """)
    categories = [dict(r) for r in await rows.fetchall()]

    total_value = sum(c["stock_value"] for c in categories) or 1
    for c in categories:
        c["percentage"] = round(c["stock_value"] / total_value * 100, 1)

    return {"categories": categories}


@router.get("/top-products")
async def get_top_products(
    limit:  int = Query(10, ge=1, le=50),
    metric: str = Query("value", description="value | stock | movement"),
    db = Depends(get_db),
):
    """Top products by stock value, stock units, or total movement."""
    if metric == "value":
        rows = await db.execute(f"""
            SELECT id, name, sku, category, stock, price, cost,
                   ROUND(price*stock, 2) AS stock_value
            FROM products WHERE is_active=1
            ORDER BY price*stock DESC LIMIT ?
        """, (limit,))
    elif metric == "stock":
        rows = await db.execute(f"""
            SELECT id, name, sku, category, stock, price, cost,
                   ROUND(price*stock, 2) AS stock_value
            FROM products WHERE is_active=1
            ORDER BY stock DESC LIMIT ?
        """, (limit,))
    else:  # movement
        rows = await db.execute(f"""
            SELECT p.id, p.name, p.sku, p.category, p.stock, p.price, p.cost,
                   ROUND(p.price*p.stock, 2) AS stock_value,
                   COALESCE(SUM(t.quantity), 0) AS total_movement
            FROM products p
            LEFT JOIN transactions t ON t.product_id = p.id
            WHERE p.is_active=1
            GROUP BY p.id
            ORDER BY total_movement DESC LIMIT ?
        """, (limit,))

    return {"items": [dict(r) for r in await rows.fetchall()]}


@router.get("/stock-movement")
async def get_stock_movement(
    days:  int = Query(30, ge=1, le=365),
    limit: int = Query(15, ge=1, le=50),
    db = Depends(get_db),
):
    """Stock in vs stock out for each product in the given time window."""
    rows = await db.execute(f"""
        SELECT
          p.name AS product_name,
          p.sku,
          p.category,
          COALESCE(SUM(CASE WHEN t.type IN ('IN','RETURN') THEN t.quantity ELSE 0 END), 0) AS units_in,
          COALESCE(SUM(CASE WHEN t.type IN ('OUT','TRANSFER') THEN t.quantity ELSE 0 END), 0) AS units_out
        FROM products p
        LEFT JOIN transactions t
               ON t.product_id = p.id
              AND t.created_at >= datetime('now', ? || ' days')
        WHERE p.is_active = 1
        GROUP BY p.id
        HAVING units_in > 0 OR units_out > 0
        ORDER BY (units_in + units_out) DESC
        LIMIT ?
    """, (f"-{days}", limit))

    items = []
    for r in await rows.fetchall():
        d = dict(r)
        d["net_movement"] = d["units_in"] - d["units_out"]
        items.append(d)
    return {"items": items, "period_days": days}


@router.get("/transactions")
async def get_transaction_trends(
    days:    int = Query(30, ge=1, le=365),
    group_by: str = Query("day", description="day | week | month"),
    db = Depends(get_db),
):
    """Transaction counts and values over time for charts."""
    if group_by == "month":
        date_format = "%Y-%m"
    elif group_by == "week":
        date_format = "%Y-W%W"
    else:
        date_format = "%Y-%m-%d"

    rows = await db.execute(f"""
        SELECT
          strftime('{date_format}', created_at) AS period,
          type,
          COUNT(*)                              AS count,
          SUM(quantity)                         AS quantity,
          ROUND(SUM(total_value), 2)            AS value
        FROM transactions
        WHERE created_at >= datetime('now', ? || ' days')
        GROUP BY period, type
        ORDER BY period ASC
    """, (f"-{days}",))

    return {"items": [dict(r) for r in await rows.fetchall()], "period_days": days}


@router.get("/valuation")
async def get_valuation(db=Depends(get_db)):
    """Complete inventory valuation report."""
    rows = await db.execute("""
        SELECT
          id, name, sku, category, stock, price, cost, unit,
          supplier, location,
          ROUND(price * stock, 2)          AS sell_value,
          ROUND(cost  * stock, 2)          AS cost_value,
          ROUND((price - cost) * stock, 2) AS profit_value,
          CASE
            WHEN price > 0 THEN ROUND((price - cost) / price * 100, 1)
            ELSE 0
          END AS margin_pct
        FROM products
        WHERE is_active = 1
        ORDER BY sell_value DESC
    """)
    items = [dict(r) for r in await rows.fetchall()]

    total_sell   = sum(i["sell_value"]   for i in items)
    total_cost   = sum(i["cost_value"]   for i in items)
    total_profit = sum(i["profit_value"] for i in items)

    return {
        "items":         items,
        "total_sell_value":   round(total_sell,   2),
        "total_cost_value":   round(total_cost,   2),
        "total_profit_value": round(total_profit, 2),
        "overall_margin_pct": round(total_profit / total_sell * 100, 1) if total_sell > 0 else 0,
    }
