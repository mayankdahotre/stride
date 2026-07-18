from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Keyword = Annotated[str, Field(min_length=1, max_length=80)]


class ParsedQuery(BaseModel):
    keywords: list[Keyword] = Field(default_factory=list, max_length=20)
    category: str | None = Field(default=None, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def prices_are_ordered(self) -> "ParsedQuery":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot exceed max_price")
        return self


class ParseQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class ParseQueryResponse(BaseModel):
    parsed: ParsedQuery
    source: str


class SearchRequest(BaseModel):
    query: str | None = Field(default=None, max_length=500)
    keywords: list[Keyword] = Field(default_factory=list, max_length=20)
    category: str | None = Field(default=None, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def prices_are_ordered(self) -> "SearchRequest":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot exceed max_price")
        return self


class SmartSearchRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    category: str | None = Field(default=None, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def prices_are_ordered(self) -> "SmartSearchRequest":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot exceed max_price")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str
    category: str
    sport: str
    brand: str
    specifications: dict[str, object]
    in_stock: bool
    price: Decimal
    currency: str
    retailer: str
    image_url: str | None = None
    rating: Decimal | None = None


class SearchResponse(BaseModel):
    products: list[ProductResponse]
    total: int
    source: str
    parsed_query: ParsedQuery | None = None


class CategoriesResponse(BaseModel):
    categories: list[str]
