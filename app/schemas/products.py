"""
Pydantic schemas for Products — used for request validation and response serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Product display name")
    sku: str = Field(..., min_length=1, max_length=50, description="Unique stock-keeping unit")
    category: str = Field(default="General", max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    price: float = Field(default=0.0, ge=0, description="Selling price")
    cost: float = Field(default=0.0, ge=0, description="Purchase/cost price")
    stock: int = Field(default=0, ge=0, description="Current stock quantity")
    threshold: int = Field(default=10, ge=0, description="Low-stock alert threshold")
    unit: str = Field(default="pcs", max_length=20)
    supplier: Optional[str] = Field(default=None, max_length=200)
    location: Optional[str] = Field(default=None, max_length=100, description="Bin or shelf location")
    barcode: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("sku")
    @classmethod
    def sku_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name", "category", "supplier", "location", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product — all fields optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    cost: Optional[float] = Field(default=None, ge=0)
    threshold: Optional[int] = Field(default=None, ge=0)
    unit: Optional[str] = Field(default=None, max_length=20)
    supplier: Optional[str] = None
    location: Optional[str] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for reading a product from the database."""
    id: int
    created_at: str
    updated_at: str
    stock_value: float = 0.0
    profit_margin: float = 0.0
    status: str = "in_stock"

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Paginated list of products."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
