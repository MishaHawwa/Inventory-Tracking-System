"""
Products Router — Full CRUD operations for inventory products.

Endpoints:
  GET    /api/products            — list with search, filter, sort, pagination
  POST   /api/products            — create new product
  GET    /api/products/{id}       — get single product
  PUT    /api/products/{id}       — full update
  PATCH  /api/products/{id}       — partial update
  DELETE /api/products/{id}       — soft delete (sets is_active=0)
  DELETE /api/products/{id}/hard  — hard delete (removes from DB)
  GET    /api/products/export/csv — export all products as CSV
"""

import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from app.database.connection import get_db
from app.schemas.products import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
)

router = APIRouter()


def _row_to_product(row) -> dict:
    """Convert a DB row to a product dict with computed fields."""
    p = dict(row)
    stock_value    = round(p["price"] * p["stock"], 2)
    cost_value     = round(p["cost"]  * p["stock"], 2)
    profit_margin  = round(((p["price"] - p["cost"]) / p["price"] * 100), 1) if p["price"] > 0 else 0.0
    if p["stock"] == 0:
        status = "out_of_stock"
    elif p["stock"] <= p["threshold"]:
        status = "low_stock"
    else:
        status = "in_stock"
    return {**p, "stock_value": stock_value, "profit_margin": profit_margin, "status": status}


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=ProductListResponse)
async def list_products(
    page:      int            = Query(1, ge=1),
    page_size: int            = Query(20, ge=1, le=100),
    search:    Optional[str]  = Query(None, description="Search name, SKU, or supplier"),
    category:  Optional[str]  = Query(None),
    status:    Optional[str]  = Query(None, description="in_stock | low_stock | out_of_stock"),
    sort_by:   str            = Query("name", description="name | stock | price | value | created_at"),
    sort_dir:  str            = Query("asc",  description="asc | desc"),
    is_active: Optional[bool] = Query(True),
    db = Depends(get_db),
):
    allowed_sort = {"name", "stock", "price", "created_at", "category", "sku"}
    if sort_by not in allowed_sort:
        sort_by = "name"
    sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

    conditions = []
    params     = []

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(1 if is_active else 0)

    if search:
        conditions.append("(name LIKE ? OR sku LIKE ? OR supplier LIKE ? OR description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])

    if category:
        conditions.append("category = ?")
        params.append(category)

    if status == "out_of_stock":
        conditions.append("stock = 0")
    elif status == "low_stock":
        conditions.append("stock > 0 AND stock <= threshold")
    elif status == "in_stock":
        conditions.append("stock > threshold")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Special sort for computed value column
    order_expr = "price * stock" if sort_by == "value" else sort_by

    count_q = await db.execute(f"SELECT COUNT(*) FROM products {where_clause}", params)
    total   = (await count_q.fetchone())[0]

    offset = (page - 1) * page_size
    rows   = await db.execute(
        f"SELECT * FROM products {where_clause} ORDER BY {order_expr} {sort_dir} LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )
    items = [_row_to_product(r) for r in await rows.fetchall()]

    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── GET ONE ───────────────────────────────────────────────────────────────────

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db=Depends(get_db)):
    row = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = await row.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _row_to_product(product)


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(payload: ProductCreate, db=Depends(get_db)):
    # Check SKU uniqueness
    existing = await db.execute("SELECT id FROM products WHERE sku = ?", (payload.sku,))
    if await existing.fetchone():
        raise HTTPException(status_code=409, detail=f"SKU '{payload.sku}' already exists")

    cursor = await db.execute("""
        INSERT INTO products
          (name,sku,category,description,price,cost,stock,threshold,unit,supplier,location,barcode,image_url,is_active)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        payload.name, payload.sku, payload.category, payload.description,
        payload.price, payload.cost, payload.stock, payload.threshold,
        payload.unit, payload.supplier, payload.location,
        payload.barcode, payload.image_url, int(payload.is_active),
    ))
    await db.commit()

    row = await db.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,))
    return _row_to_product(await row.fetchone())


# ── FULL UPDATE ───────────────────────────────────────────────────────────────

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, payload: ProductCreate, db=Depends(get_db)):
    row = await db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Product not found")

    # SKU uniqueness check (exclude self)
    dup = await db.execute("SELECT id FROM products WHERE sku = ? AND id != ?", (payload.sku, product_id))
    if await dup.fetchone():
        raise HTTPException(status_code=409, detail=f"SKU '{payload.sku}' already used by another product")

    await db.execute("""
        UPDATE products SET
          name=?, sku=?, category=?, description=?, price=?, cost=?,
          stock=?, threshold=?, unit=?, supplier=?, location=?,
          barcode=?, image_url=?, is_active=?,
          updated_at=datetime('now')
        WHERE id=?
    """, (
        payload.name, payload.sku, payload.category, payload.description,
        payload.price, payload.cost, payload.stock, payload.threshold,
        payload.unit, payload.supplier, payload.location,
        payload.barcode, payload.image_url, int(payload.is_active),
        product_id,
    ))
    await db.commit()

    updated = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    return _row_to_product(await updated.fetchone())


# ── PARTIAL UPDATE ────────────────────────────────────────────────────────────

@router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(product_id: int, payload: ProductUpdate, db=Depends(get_db)):
    row = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = await row.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return _row_to_product(product)

    if "sku" in updates:
        dup = await db.execute("SELECT id FROM products WHERE sku = ? AND id != ?", (updates["sku"], product_id))
        if await dup.fetchone():
            raise HTTPException(status_code=409, detail=f"SKU '{updates['sku']}' already in use")
    if "is_active" in updates:
        updates["is_active"] = int(updates["is_active"])

    set_clause = ", ".join(f"{k}=?" for k in updates) + ", updated_at=datetime('now')"
    await db.execute(f"UPDATE products SET {set_clause} WHERE id=?", list(updates.values()) + [product_id])
    await db.commit()

    updated = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    return _row_to_product(await updated.fetchone())


# ── SOFT DELETE ───────────────────────────────────────────────────────────────

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, db=Depends(get_db)):
    row = await db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Product not found")
    await db.execute("UPDATE products SET is_active=0, updated_at=datetime('now') WHERE id=?", (product_id,))
    await db.commit()


# ── HARD DELETE ───────────────────────────────────────────────────────────────

@router.delete("/{product_id}/hard", status_code=204)
async def hard_delete_product(product_id: int, db=Depends(get_db)):
    row = await db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Product not found")
    await db.execute("DELETE FROM products WHERE id=?", (product_id,))
    await db.commit()


# ── CSV EXPORT ────────────────────────────────────────────────────────────────

@router.get("/export/csv")
async def export_csv(db=Depends(get_db)):
    rows = await db.execute("SELECT * FROM products WHERE is_active=1 ORDER BY category, name")
    products = await rows.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "SKU", "Name", "Category", "Description", "Price", "Cost",
        "Stock", "Threshold", "Unit", "Supplier", "Location",
        "Stock Value", "Status", "Created At",
    ])
    for p in products:
        p = dict(p)
        stock_value = round(p["price"] * p["stock"], 2)
        if p["stock"] == 0:
            status = "Out of Stock"
        elif p["stock"] <= p["threshold"]:
            status = "Low Stock"
        else:
            status = "OK"
        writer.writerow([
            p["id"], p["sku"], p["name"], p["category"], p.get("description", ""),
            p["price"], p["cost"], p["stock"], p["threshold"], p["unit"],
            p.get("supplier", ""), p.get("location", ""),
            stock_value, status, p["created_at"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_export.csv"},
    )
