"""
Pydantic schemas for Reports and Alerts.
"""

from pydantic import BaseModel
from typing import Optional


# ── Alert Schemas ─────────────────────────────────────────────────────────────

class AlertItem(BaseModel):
    id:            int
    name:          str
    sku:           str
    category:      str
    stock:         int
    threshold:     int
    supplier:      Optional[str]
    location:      Optional[str]
    price:         float
    stock_value:   float
    alert_type:    str   # "out_of_stock" | "low_stock"
    severity:      str   # "critical" | "warning"
    days_to_empty: Optional[int]  # estimated days until out-of-stock

class AlertSummary(BaseModel):
    total_alerts:     int
    out_of_stock:     int
    low_stock:        int
    critical_value:   float   # total value at risk
    items:            list[AlertItem]


# ── Report Schemas ────────────────────────────────────────────────────────────

class KPISummary(BaseModel):
    total_products:      int
    active_products:     int
    total_stock_units:   int
    total_stock_value:   float
    total_cost_value:    float
    potential_profit:    float
    low_stock_count:     int
    out_of_stock_count:  int
    total_transactions:  int
    units_received_30d:  int
    units_dispatched_30d: int
    categories_count:    int


class CategoryBreakdown(BaseModel):
    category:      str
    product_count: int
    total_stock:   int
    stock_value:   float
    percentage:    float


class TopProduct(BaseModel):
    id:          int
    name:        str
    sku:         str
    category:    str
    stock:       int
    price:       float
    stock_value: float


class TransactionSummary(BaseModel):
    date:     str
    type:     str
    count:    int
    quantity: int
    value:    float


class StockMovement(BaseModel):
    product_name: str
    sku:          str
    units_in:     int
    units_out:    int
    net_movement: int


class FullReport(BaseModel):
    kpis:               KPISummary
    category_breakdown: list[CategoryBreakdown]
    top_by_value:       list[TopProduct]
    top_by_movement:    list[StockMovement]
    recent_activity:    list[TransactionSummary]
    low_stock_items:    list[AlertItem]
