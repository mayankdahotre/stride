from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), index=True)
    sport: Mapped[str] = mapped_column(String(80), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    specifications: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    retailer: Mapped[str] = mapped_column(String(120), default="Stride Market")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
