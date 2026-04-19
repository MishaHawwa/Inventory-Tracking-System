# InvTrack — Inventory Tracking System

A production-grade inventory management system built with **Python + FastAPI + SQLite**.  
Includes a full REST API, a browser-based frontend, real-time stock alerts, CSV export, and a complete test suite.

---

## Project Structure

```
inventory-system/
│
├── main.py                      ← FastAPI app entry point
├── requirements.txt             ← Python dependencies
├── pytest.ini                   ← Test configuration
├── .env.example                 ← Copy to .env and edit
├── .gitignore
│
├── app/
│   ├── database/
│   │   └── connection.py        ← SQLite setup, table creation, seed data
│   ├── routers/
│   │   ├── products.py          ← CRUD for products + CSV export
│   │   ├── transactions.py      ← Stock movements (IN/OUT/ADJ/RETURN/TRANSFER)
│   │   ├── alerts.py            ← Low-stock & out-of-stock alerts
│   │   └── reports.py           ← KPIs, category breakdown, charts, valuation
│   └── schemas/
│       ├── products.py          ← Pydantic models for products
│       ├── transactions.py      ← Pydantic models for transactions
│       └── reports.py           ← Pydantic models for reports & alerts
│
├── static/
│   └── index.html               ← Full frontend (HTML + CSS + JS, no build step)
│
├── tests/
│   └── test_api.py              ← 25+ async API tests (pytest + httpx)
│
└── scripts/
    └── seed.py                  ← Reset & re-seed the database
```

---

## Features

| Area | What's included |
|---|---|
| **Products** | Full CRUD (create, read, update, patch, soft-delete, hard-delete), SKU uniqueness, search, filter by category/status, sort, pagination |
| **Transactions** | Stock In, Stock Out, Adjustment, Return, Transfer — each updates stock atomically |
| **Alerts** | Real-time low-stock and out-of-stock detection with estimated days-to-empty |
| **Reports** | KPI dashboard, top products by value/movement, category breakdown, stock valuation with profit margins |
| **Export** | One-click CSV download of entire inventory |
| **Frontend** | Zero-dependency single-file HTML UI — served by FastAPI at `/` |
| **API Docs** | Auto-generated Swagger UI at `/docs`, ReDoc at `/redoc` |
| **Database** | Async SQLite via `aiosqlite` — WAL mode, FK constraints, indexed columns |
| **Tests** | 25+ async tests covering all endpoints, edge cases, and validations |

---

## Quick Start

### Step 1 — Prerequisites

Make sure you have **Python 3.10 or newer** installed.

```bash
python --version
# Should print: Python 3.10.x or higher
```

If you don't have Python:
- **Windows**: Download from https://python.org/downloads — tick "Add to PATH"
- **macOS**: `brew install python` (or download from python.org)
- **Linux/Ubuntu**: `sudo apt install python3 python3-pip python3-venv`

---

### Step 2 — Download / Clone the project

If you have Git:
```bash
git clone <your-repo-url>
cd inventory-system
```

Or just unzip the downloaded folder and open a terminal inside it:
```bash
cd inventory-system
```

---

### Step 3 — Create a virtual environment

A virtual environment keeps project dependencies isolated from your system Python.

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt.

---

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fastapi` — web framework
- `uvicorn` — ASGI server (runs FastAPI)
- `aiosqlite` — async SQLite driver
- `pydantic` — data validation
- `python-multipart` — form support

---

### Step 5 — (Optional) Configure environment

```bash
cp .env.example .env
```

The defaults work out of the box. Edit `.env` only if you need a different DB path or port.

---

### Step 6 — Run the server

```bash
uvicorn main:app --reload
```

The `--reload` flag restarts the server automatically when you save changes to code.

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
[DB] Database initialized at: inventory.db
```

The SQLite database `inventory.db` is created automatically on first run, with 16 sample products and sample transactions already loaded.

---

### Step 7 — Open the app

| URL | What it is |
|---|---|
| http://127.0.0.1:8000 | Full inventory management UI |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger UI) |
| http://127.0.0.1:8000/redoc | Alternative API docs (ReDoc) |
| http://127.0.0.1:8000/health | Health check endpoint |

---

## Running the Tests

Make sure the virtual environment is active, then:

```bash
pip install pytest pytest-asyncio httpx
pytest tests/test_api.py -v
```

Tests use an **in-memory SQLite database** — they are completely isolated from your real data and run in seconds.

Expected output:
```
tests/test_api.py::test_health PASSED
tests/test_api.py::test_list_products PASSED
tests/test_api.py::test_create_product PASSED
tests/test_api.py::test_create_duplicate_sku PASSED
...
25 passed in 2.41s
```

---

## Resetting / Re-seeding the Database

To wipe and recreate the database with fresh demo data:

```bash
# Reset and re-seed (keeps the file)
python scripts/seed.py

# Drop the DB file completely, then seed fresh
python scripts/seed.py --drop
```

---

## API Reference

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/` | List products (search, filter, sort, paginate) |
| POST | `/api/products/` | Create a new product |
| GET | `/api/products/{id}` | Get one product |
| PUT | `/api/products/{id}` | Full update |
| PATCH | `/api/products/{id}` | Partial update |
| DELETE | `/api/products/{id}` | Soft delete (hides product) |
| DELETE | `/api/products/{id}/hard` | Hard delete (permanent) |
| GET | `/api/products/export/csv` | Download CSV of all products |

**Query params for list:** `search`, `category`, `status` (in_stock/low_stock/out_of_stock), `sort_by`, `sort_dir`, `page`, `page_size`, `is_active`

### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/` | List transactions (filter by product, type) |
| POST | `/api/transactions/` | Record a stock movement |
| GET | `/api/transactions/{id}` | Get one transaction |
| GET | `/api/transactions/product/{id}` | All transactions for a product |

**Transaction types:** `IN` (receive), `OUT` (dispatch/sell), `ADJ` (set absolute stock), `RETURN` (customer return), `TRANSFER` (internal move)

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts/` | All active alerts with details |
| GET | `/api/alerts/count` | Just the count (for polling) |
| GET | `/api/alerts/low-stock` | Only low-stock items |
| GET | `/api/alerts/out-of-stock` | Only out-of-stock items |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/summary` | Full KPI dashboard data |
| GET | `/api/reports/categories` | Breakdown by category |
| GET | `/api/reports/top-products` | Top by value/stock/movement |
| GET | `/api/reports/stock-movement` | In vs out per product |
| GET | `/api/reports/transactions` | Transaction trends over time |
| GET | `/api/reports/valuation` | Full valuation with margins |

---

## Example API Calls

```bash
# List all products
curl http://localhost:8000/api/products/

# Search for a product
curl "http://localhost:8000/api/products/?search=keyboard"

# Filter low stock items
curl "http://localhost:8000/api/products/?status=low_stock"

# Create a product
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop Stand","sku":"LS-001","category":"Electronics","price":49.99,"cost":22.00,"stock":30,"threshold":5,"is_active":true}'

# Record stock in
curl -X POST http://localhost:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"type":"IN","quantity":50,"reference":"PO-5001"}'

# Get all alerts
curl http://localhost:8000/api/alerts/

# Get dashboard report
curl http://localhost:8000/api/reports/summary

# Export CSV
curl http://localhost:8000/api/products/export/csv -o inventory.csv
```

---

## Common Errors & Fixes

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -r requirements.txt` with venv active |
| `Address already in use` | Another process is on port 8000. Use `uvicorn main:app --port 8001` |
| `python: command not found` | Use `python3` instead of `python` on Linux/macOS |
| PowerShell script execution disabled | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `Permission denied` on venv activate | Run `chmod +x venv/bin/activate` then `source venv/bin/activate` |

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Database**: SQLite (async via aiosqlite), WAL mode, foreign key constraints
- **Validation**: Pydantic v2
- **Frontend**: Vanilla HTML/CSS/JS (no npm, no build tools, zero dependencies)
- **Testing**: pytest, pytest-asyncio, httpx

---

## Upgrading to PostgreSQL (Optional)

To switch from SQLite to PostgreSQL in production:

1. `pip install asyncpg databases[postgresql]`
2. Replace `aiosqlite.connect(DB_PATH)` with an `asyncpg` connection pool
3. Change `datetime('now')` SQL expressions to `NOW()`
4. Everything else (routers, schemas, tests) stays the same

---

## License

MIT — free for personal and commercial use.
