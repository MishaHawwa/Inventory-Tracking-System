"""
Transactions Router — Records every stock movement and updates product stock.

Endpoints:
  GET  /api/transactions          — list all transactions (paginated, filterable)
  POST /api/transactions          — create a transaction (updates product stock)
  GET  /api/transactions/{id}     — get a single transaction
  GET  /api/transactions/product/{product_id} — all transactions for one product
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.database.connection import get_db
from app.schemas.transactions import (
    TransactionCreate, TransactionResponse, TransactionListResponse, TransactionType
)

router = APIRouter()


def _row_to_tx(row, product_name: str = "", sku: str = "") -> dict:
    d = dict(row)
    d["product_name"] = product_name or d.get("product_name", "")
    d["sku"]          = sku          or d.get("sku", "")
    return d


# ── LIST ALL ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page:       int           = Query(1, ge=1),
    page_size:  int           = Query(30, ge=1, le=200),
    product_id: Optional[int] = Query(None),
    type:       Optional[str] = Query(None, description="IN | OUT | ADJ | TRANSFER | RETURN"),
    search:     Optional[str] = Query(None, description="Search reference or note"),
    db = Depends(get_db),
):
    conditions = []
    params     = []

    if product_id:
        conditions.append("t.product_id = ?")
        params.append(product_id)
    if type:
        conditions.append("t.type = ?")
        params.append(type.upper())
    if search:
        conditions.append("(t.reference LIKE ? OR t.note LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_q = await db.execute(
        f"SELECT COUNT(*) FROM transactions t {where}", params
    )
    total = (await count_q.fetchone())[0]

    offset = (page - 1) * page_size
    rows   = await db.execute(f"""
        SELECT t.*, p.name AS product_name, p.sku
        FROM transactions t
        JOIN products p ON p.id = t.product_id
        {where}
        ORDER BY t.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])

    items = [dict(r) for r in await rows.fetchall()]

    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── GET ONE ───────────────────────────────────────────────────────────────────

@router.get("/{tx_id}", response_model=TransactionResponse)
async def get_transaction(tx_id: int, db=Depends(get_db)):
    row = await db.execute("""
        SELECT t.*, p.name AS product_name, p.sku
        FROM transactions t
        JOIN products p ON p.id = t.product_id
        WHERE t.id = ?
    """, (tx_id,))
    tx = await row.fetchone()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return dict(tx)


# ── GET BY PRODUCT ─────────────────────────────────────────────────────────────

@router.get("/product/{product_id}", response_model=TransactionListResponse)
async def get_product_transactions(
    product_id: int,
    page:      int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    db = Depends(get_db),
):
    # Verify product exists
    check = await db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if not await check.fetchone():
        raise HTTPException(status_code=404, detail="Product not found")

    count_q = await db.execute(
        "SELECT COUNT(*) FROM transactions WHERE product_id = ?", (product_id,)
    )
    total  = (await count_q.fetchone())[0]
    offset = (page - 1) * page_size

    rows = await db.execute("""
        SELECT t.*, p.name AS product_name, p.sku
        FROM transactions t
        JOIN products p ON p.id = t.product_id
        WHERE t.product_id = ?
        ORDER BY t.created_at DESC
        LIMIT ? OFFSET ?
    """, (product_id, page_size, offset))

    items = [dict(r) for r in await rows.fetchall()]
    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── CREATE TRANSACTION ────────────────────────────────────────────────────────

@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(payload: TransactionCreate, db=Depends(get_db)):
    # Fetch current product
    row = await db.execute("SELECT * FROM products WHERE id = ?", (payload.product_id,))
    product = await row.fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product["is_active"]:
        raise HTTPException(status_code=400, detail="Cannot transact on an inactive product")

    product        = dict(product)
    stock_before   = product["stock"]
    tx_type        = payload.type

    # ── Calculate new stock ────────────────────────────────────────────────────
    if tx_type == TransactionType.IN:
        stock_after = stock_before + payload.quantity
    elif tx_type == TransactionType.OUT:
        if payload.quantity > stock_before:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available: {stock_before}, Requested: {payload.quantity}",
            )
        stock_after = stock_before - payload.quantity
    elif tx_type == TransactionType.ADJ:
        stock_after = payload.quantity   # ADJ sets stock to the given value
    elif tx_type == TransactionType.RETURN:
        stock_after = stock_before + payload.quantity
    elif tx_type == TransactionType.TRANSFER:
        if payload.quantity > stock_before:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for transfer. Available: {stock_before}",
            )
        stock_after = stock_before - payload.quantity
    else:
        raise HTTPException(status_code=400, detail="Unknown transaction type")

    # ── Compute value ──────────────────────────────────────────────────────────
    unit_price  = payload.unit_price if payload.unit_price is not None else product["cost"]
    total_value = round(unit_price * payload.quantity, 2)

    # ── Update product stock ───────────────────────────────────────────────────
    await db.execute(
        "UPDATE products SET stock=?, updated_at=datetime('now') WHERE id=?",
        (stock_after, payload.product_id),
    )

    # ── Insert transaction record ──────────────────────────────────────────────
    cursor = await db.execute("""
        INSERT INTO transactions
          (product_id, type, quantity, stock_before, stock_after,
           unit_price, total_value, reference, note, performed_by)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        payload.product_id, tx_type.value, payload.quantity,
        stock_before, stock_after,
        unit_price, total_value,
        payload.reference, payload.note, payload.performed_by or "admin",
    ))
    await db.commit()

    # ── Return the new transaction ─────────────────────────────────────────────
    tx_row = await db.execute("""
        SELECT t.*, p.name AS product_name, p.sku
        FROM transactions t JOIN products p ON p.id = t.product_id
        WHERE t.id = ?
    """, (cursor.lastrowid,))
    return dict(await tx_row.fetchone())
