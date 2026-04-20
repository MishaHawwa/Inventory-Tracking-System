Inventory Tracking System

InvTrack is a simple but complete inventory management system built with Python and FastAPI.

I built this to understand how real-world inventory systems handle stock updates, transactions, alerts, and reporting—all in one place.

It includes a REST API, a basic frontend, and a test suite, so you can interact with it both programmatically and through the browser.

What it can do

At its core, InvTrack lets you:

Manage products (add, update, delete, search)
Track stock changes through transactions (in, out, adjustments, returns)
Get alerts when stock is running low or out
View basic reports like total value, category breakdown, etc.
Export your inventory data as CSV
Use a simple UI without needing any frontend build tools
Features
Product Management

You can create and manage products with:

Unique SKU enforcement
Search and filtering
Sorting and pagination
Soft delete vs permanent delete
Transactions

Every stock change goes through a transaction:

IN → adding stock
OUT → removing stock (sales, usage)
ADJ → correcting stock manually
RETURN → returned items
TRANSFER → internal movement

Stock updates are handled safely so values stay consistent.

Alerts

The system automatically flags:

Low stock items
Out of stock items

This makes it easier to see what needs attention without manually checking everything.

Reports

Basic reporting endpoints include:

Inventory summary (KPIs)
Category-wise breakdown
Top products
Stock movement overview

Nothing too fancy, but enough to understand how reporting APIs are structured.

Frontend

There’s a simple HTML-based UI served directly by FastAPI:

No React, no build tools
Just open the browser and use it
API & Testing
FastAPI provides auto docs at /docs
Around 25+ test cases using pytest
Tests run on an isolated in-memory database
Project Structure
inventory-system/
├── main.py
├── app/
│   ├── database/
│   ├── routers/
│   └── schemas/
├── static/
└── tests/
Getting Started
1. Create virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows (Git Bash)
2. Install dependencies
pip install -r requirements.txt
3. Run the app
uvicorn main:app --reload

Open:

http://127.0.0.1:8000
http://127.0.0.1:8000/docs
Running Tests
pytest tests/test_api.py -v
Notes on Design
SQLite is used for simplicity (no setup required)
Async database access using aiosqlite
API-first design — frontend just consumes the API
Focus was more on backend logic than UI
Why I built this

I wanted to go beyond basic CRUD apps and build something closer to a real system—where data changes over time (transactions), not just static records.

This project helped me understand:

how inventory flows work
how to structure APIs cleanly
how to test backend systems properly
Tech Stack
Python, FastAPI
SQLite (aiosqlite)
Pydantic
Pytest
License

MIT
