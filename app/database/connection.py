"""
Database connection setup using aiosqlite (async SQLite).
This module handles DB initialization, connection pooling, and table creation.
"""

import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "inventory.db")


async def get_db():
    """Dependency: yields a database connection for use in route handlers."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row  # Return rows as dict-like objects
        await db.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        await db.execute("PRAGMA foreign_keys=ON")   # Enforce FK constraints
        yield db


async def init_db():
    """Create all tables if they do not exist. Run on startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        # ── Products table ────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                sku         TEXT NOT NULL UNIQUE,
                category    TEXT NOT NULL DEFAULT 'General',
                description TEXT,
                price       REAL NOT NULL DEFAULT 0.0,
                cost        REAL NOT NULL DEFAULT 0.0,
                stock       INTEGER NOT NULL DEFAULT 0,
                threshold   INTEGER NOT NULL DEFAULT 10,
                unit        TEXT DEFAULT 'pcs',
                supplier    TEXT,
                location    TEXT,
                barcode     TEXT,
                image_url   TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # ── Transactions table ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                type            TEXT NOT NULL CHECK(type IN ('IN','OUT','ADJ','TRANSFER','RETURN')),
                quantity        INTEGER NOT NULL,
                stock_before    INTEGER NOT NULL,
                stock_after     INTEGER NOT NULL,
                unit_price      REAL,
                total_value     REAL,
                reference       TEXT,
                note            TEXT,
                performed_by    TEXT DEFAULT 'system',
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # ── Suppliers table ───────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                contact     TEXT,
                email       TEXT,
                phone       TEXT,
                address     TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # ── Categories table ──────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#1D9E75'
            )
        """)

        # ── Indexes for fast querying ─────────────────────────────────────────
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_sku      ON products(sku)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_stock    ON products(stock)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tx_product        ON transactions(product_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tx_type           ON transactions(type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tx_created        ON transactions(created_at)")

        await db.commit()

        # Seed default categories
        default_cats = [
            ("Electronics", "#185FA5"),
            ("Furniture", "#3B6D11"),
            ("Clothing", "#D4537E"),
            ("Food", "#BA7517"),
            ("Tools", "#534AB7"),
            ("General", "#5F5E5A"),
        ]
        for cat_name, cat_color in default_cats:
            await db.execute(
                "INSERT OR IGNORE INTO categories(name, color) VALUES (?, ?)",
                (cat_name, cat_color),
            )

        # Seed sample data only if products table is empty
        count = await db.execute("SELECT COUNT(*) FROM products")
        row = await count.fetchone()
        if row[0] == 0:
            await _seed_sample_data(db)

        await db.commit()
    print(f"[DB] Database initialized at: {DB_PATH}")


async def _seed_sample_data(db):
    """Insert realistic sample data for demo purposes."""
    products = [
        ("USB-C Cable 2m",       "EL-001", "Electronics", "High-speed USB-C charging cable", 12.99, 8.00,  145, 20, "pcs", "TechSupply Co",  "A1-S2"),
        ("Wireless Mouse",        "EL-002", "Electronics", "Ergonomic wireless mouse 2.4GHz",  34.50, 18.00,  8,  15, "pcs", "TechSupply Co",  "A1-S3"),
        ("HDMI Adapter 4K",       "EL-003", "Electronics", "4K HDMI to DisplayPort adapter",   19.00, 9.50,  52, 10, "pcs", "GadgetHub",      "A2-S1"),
        ("Mechanical Keyboard",   "EL-004", "Electronics", "Tenkeyless mechanical keyboard",   89.99, 45.00,  3,  5,  "pcs", "KeyCo",          "A2-S2"),
        ("24-inch Monitor",       "EL-005", "Electronics", "Full HD IPS 75Hz monitor",        199.00, 110.00, 14,  5, "pcs", "ScreenWorld",    "A3-S1"),
        ("Office Chair",          "FU-001", "Furniture",   "Ergonomic mesh office chair",     249.00, 130.00, 12,  3, "pcs", "FurnWorld",      "W1-S1"),
        ("Standing Desk",         "FU-002", "Furniture",   "Height-adjustable standing desk", 399.00, 210.00,  0,  2, "pcs", "FurnWorld",      "W1-S2"),
        ("Monitor Stand",         "FU-003", "Furniture",   "Dual monitor aluminium stand",     45.00, 20.00,  28,  5, "pcs", "DeskCo",         "W2-S1"),
        ("Cotton T-Shirt L",      "CL-001", "Clothing",    "100% cotton t-shirt size L",       15.00, 6.00,  200, 30, "pcs", "FashionBulk",    "C1-S1"),
        ("Denim Jeans 32",        "CL-002", "Clothing",    "Slim fit denim jeans waist 32",    45.00, 20.00,  4,  10, "pcs", "FashionBulk",    "C1-S2"),
        ("Winter Jacket M",       "CL-003", "Clothing",    "Padded winter jacket size M",      89.00, 40.00,  22,  8, "pcs", "FashionBulk",    "C2-S1"),
        ("Power Drill",           "TO-001", "Tools",       "18V cordless power drill",        120.00, 65.00,  18,  5, "pcs", "ToolMaster",     "T1-S1"),
        ("Screwdriver Set 12pc",  "TO-002", "Tools",       "Magnetic 12-piece screwdriver set",22.00, 10.00,  60, 10, "pcs", "ToolMaster",     "T1-S2"),
        ("Tape Measure 5m",       "TO-003", "Tools",       "Steel tape measure 5 metre",        8.50,  3.50,  45, 10, "pcs", "ToolMaster",     "T1-S3"),
        ("Instant Noodles (24pk)","FD-001", "Food",        "Chicken instant noodles 24-pack",  18.00, 10.00,  7,  20, "pcs", "FoodDist",       "F1-S1"),
        ("Green Tea (100 bags)",  "FD-002", "Food",        "Premium green tea 100 tea bags",   12.00, 5.50,  33, 15, "pcs", "FoodDist",       "F1-S2"),
    ]

    for p in products:
        await db.execute("""
            INSERT INTO products(name,sku,category,description,price,cost,stock,threshold,unit,supplier,location)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, p)

    # Seed a handful of transactions
    sample_tx = [
        (1, "IN",  50, 95,  145, 8.00,  400.0,  "PO-1001", "Initial stock received"),
        (2, "IN",  20, 0,   8,   18.00, 360.0,  "PO-1002", "Restock order"),
        (2, "OUT", 12, 20,  8,   34.50, 414.0,  "SO-2201", "Dispatched to client A"),
        (3, "IN",  52, 0,   52,  9.50,  494.0,  "PO-1003", "New stock"),
        (4, "OUT",  2, 5,   3,   89.99, 179.98, "SO-2202", "Sold to retail"),
        (6, "IN",  12, 0,   12,  130.0, 1560.0, "PO-1004", "Furniture order"),
        (7, "OUT",  1, 1,   0,   399.0, 399.0,  "SO-2203", "Last unit dispatched"),
        (9, "IN", 200, 0,  200,  6.00,  1200.0, "PO-1005", "Bulk clothing order"),
        (10,"OUT", 6, 10,  4,   20.00, 120.0,  "SO-2204", "Order fulfilled"),
        (15,"OUT", 3, 10,  7,   10.00, 30.0,   "SO-2205", "Weekly dispatch"),
    ]
    for tx in sample_tx:
        pid, ttype, qty, sb, sa, up, tv, ref, note = tx
        await db.execute("""
            INSERT INTO transactions(product_id,type,quantity,stock_before,stock_after,unit_price,total_value,reference,note,performed_by)
            VALUES (?,?,?,?,?,?,?,?,?,'admin')
        """, (pid, ttype, qty, sb, sa, up, tv, ref, note))
