"""Seed development products after running `alembic upgrade head`.

Run from the backend directory with: python -m scripts.seed
"""

import asyncio

from sqlalchemy import select

from app.data.seed_products import seeded_products
from app.db.session import SessionLocal
from app.models.product import Product
from app.services.embeddings import embedding_service


async def seed() -> None:
    with SessionLocal.begin() as session:
        products = seeded_products()
        changed = 0
        for product in products:
            product.embedding = await embedding_service.embed(
                f"{product.name}. {product.description}. Category: {product.category}"
            )
            existing = session.scalar(
                select(Product).where(
                    (Product.sku == product.sku) | (Product.id == product.id)
                )
            )
            if existing is None:
                session.add(product)
            else:
                for column in (
                    "sku", "name", "description", "category", "sport", "brand",
                    "specifications", "in_stock", "price", "currency", "retailer",
                    "image_url", "rating", "embedding",
                ):
                    setattr(existing, column, getattr(product, column))
            changed += 1
        print(f"Upserted {changed} products.")


if __name__ == "__main__":
    asyncio.run(seed())
