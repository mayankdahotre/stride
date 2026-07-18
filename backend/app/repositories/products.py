import logging
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.data.seed_products import seeded_products
from app.models.product import Product

logger = logging.getLogger(__name__)


class ProductRepository:
    def __init__(self, session: Session | None) -> None:
        self.session = session

    def categories(self) -> tuple[list[str], str]:
        if self.session is not None:
            try:
                rows = self.session.scalars(
                    select(Product.category).distinct().order_by(Product.category)
                ).all()
                return list(rows), "database"
            except SQLAlchemyError as exc:
                self._recover(exc)
        return sorted({product.category for product in seeded_products()}), "fallback"

    def get_by_ids(
        self, product_ids: list[int], *, candidate_ids: set[int] | None = None
    ) -> tuple[list[Product], str]:
        """Return products in request order, optionally constrained to retrieved IDs."""
        allowed = [
            value
            for value in dict.fromkeys(product_ids)
            if candidate_ids is None or value in candidate_ids
        ]
        if not allowed:
            return [], "database" if self.session is not None else "fallback"
        if self.session is not None:
            try:
                found = self.session.scalars(
                    select(Product).where(Product.id.in_(allowed))
                ).all()
                by_id = {product.id: product for product in found}
                return [by_id[value] for value in allowed if value in by_id], "database"
            except SQLAlchemyError as exc:
                self._recover(exc)
        by_id = {product.id: product for product in seeded_products()}
        return [by_id[value] for value in allowed if value in by_id], "fallback"

    def search_candidates(
        self, query: str, *, limit: int = 12
    ) -> tuple[list[Product], str]:
        ignored = {
            "compare", "versus", "recommend", "suggest", "search", "find",
            "show", "plan", "best", "product", "products", "under", "with",
            "for", "and", "the",
        }
        terms = [
            term
            for term in query.casefold().replace(",", " ").split()
            if len(term) > 2 and term not in ignored and not term.strip("$").isdigit()
        ]
        products, source = self.search(
            keywords=terms,
            category=None,
            min_price=None,
            max_price=None,
            limit=limit,
        )
        if products:
            return products, source
        return self.search(
            keywords=[],
            category=None,
            min_price=None,
            max_price=None,
            limit=limit,
        )

    def search(
        self,
        *,
        keywords: list[str],
        category: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        limit: int,
        embedding: list[float] | None = None,
    ) -> tuple[list[Product], str]:
        if self.session is not None:
            try:
                statement = select(Product)
                keyword_conditions = [
                    or_(
                        Product.name.ilike(f"%{term}%"),
                        Product.description.ilike(f"%{term}%"),
                        Product.sport.ilike(f"%{term}%"),
                        Product.brand.ilike(f"%{term}%"),
                    )
                    for term in keywords
                ]
                if keyword_conditions and embedding is None:
                    statement = statement.where(or_(*keyword_conditions))
                if category:
                    statement = statement.where(
                        func.lower(Product.category) == category.lower()
                    )
                if min_price is not None:
                    statement = statement.where(Product.price >= min_price)
                if max_price is not None:
                    statement = statement.where(Product.price <= max_price)
                if embedding is not None:
                    distance = Product.embedding.cosine_distance(embedding)
                    if keyword_conditions:
                        keyword_score = sum(
                            (
                                case((condition, 1.0), else_=0.0)
                                for condition in keyword_conditions
                            )
                        )
                        # Lower is better: semantic distance is the primary signal,
                        # with exact text matches receiving a small ranking boost.
                        rank = distance - (keyword_score * 0.15)
                    else:
                        rank = distance
                    statement = statement.order_by(rank.asc().nullslast())
                else:
                    statement = statement.order_by(Product.rating.desc().nullslast())
                products = list(self.session.scalars(statement.limit(limit * 3)).all())
                if embedding is None:
                    products = self._rank(products, keywords)
                products = products[:limit]
                return products, "database"
            except SQLAlchemyError as exc:
                self._recover(exc)
        return (
            self._fallback_search(keywords, category, min_price, max_price, limit),
            "fallback",
        )

    def _recover(self, exc: SQLAlchemyError) -> None:
        logger.warning("Database unavailable; using seeded products: %s", exc)
        if self.session is not None:
            self.session.rollback()

    @staticmethod
    def _fallback_search(
        keywords: list[str],
        category: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        limit: int,
    ) -> list[Product]:
        normalized = [term.casefold() for term in keywords if term.strip()]

        def matches(product: Product) -> bool:
            text = (
                f"{product.name} {product.description} {product.sport} "
                f"{product.brand} {product.specifications}"
            ).casefold()
            return (
                (not normalized or any(term in text for term in normalized))
                and (category is None or product.category.casefold() == category.casefold())
                and (min_price is None or product.price >= min_price)
                and (max_price is None or product.price <= max_price)
            )

        products = [product for product in seeded_products() if matches(product)]
        return ProductRepository._rank(products, normalized)[:limit]

    @staticmethod
    def _rank(products: list[Product], keywords: list[str]) -> list[Product]:
        terms = [term.casefold() for term in keywords if term.strip()]

        def score(product: Product) -> tuple[int, Decimal, Decimal, int]:
            name = product.name.casefold()
            details = (
                f"{product.description} {product.category} {product.sport} "
                f"{product.brand} {product.specifications}"
            ).casefold()
            relevance = sum(
                5 if term in name else 2 if term in details else 0 for term in terms
            )
            return (
                relevance,
                product.rating or Decimal("0"),
                -product.price,
                -product.id,
            )

        return sorted(products, key=score, reverse=True)
