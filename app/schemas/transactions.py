"""
Pydantic schemas for Transactions.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    IN       = "IN"       # Receive stock
    OUT      = "OUT"      # Dispatch / sell stock
    ADJ      = "ADJ"      # Manual adjustment (sets absolute value)
    TRANSFER = "TRANSFER" # Internal transfer between locations
    RETURN   = "RETURN"   # Customer return (adds back to stock)


class TransactionCreate(BaseModel):
    product_id:   int             = Field(..., description="ID of the product")
    type:         TransactionType = Field(..., description="Transaction type")
    quantity:     int             = Field(..., gt=0, description="Quantity (must be > 0)")
    unit_price:   Optional[float] = Field(default=None, ge=0)
    reference:    Optional[str]   = Field(default=None, max_length=100, description="PO/SO reference number")
    note:         Optional[str]   = Field(default=None, max_length=500)
    performed_by: Optional[str]   = Field(default="admin", max_length=100)

    @field_validator("reference", "note", "performed_by", mode="before")
    @classmethod
    def strip_str(cls, v):
        return v.strip() if isinstance(v, str) else v


class TransactionResponse(BaseModel):
    id:           int
    product_id:   int
    product_name: str
    sku:          str
    type:         str
    quantity:     int
    stock_before: int
    stock_after:  int
    unit_price:   Optional[float]
    total_value:  Optional[float]
    reference:    Optional[str]
    note:         Optional[str]
    performed_by: str
    created_at:   str

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items:       list[TransactionResponse]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
