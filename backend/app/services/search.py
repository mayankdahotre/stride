from app.repositories.products import ProductRepository
from app.schemas.shopping import (
    ParsedQuery,
    SearchRequest,
    SearchResponse,
    SmartSearchRequest,
)
from app.services.embeddings import embedding_service
from app.services.query_parser import QueryParser


class ShoppingSearchService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository
        self.parser = QueryParser()

    def search(self, request: SearchRequest) -> SearchResponse:
        keywords = request.keywords
        if request.query:
            query_terms = QueryParser.parse_deterministically(request.query).keywords
            keywords = list(dict.fromkeys([*keywords, *query_terms]))
        products, source = self.repository.search(
            keywords=keywords,
            category=request.category,
            min_price=request.min_price,
            max_price=request.max_price,
            limit=request.limit,
        )
        return SearchResponse(products=products, total=len(products), source=source)

    async def smart_search(self, request: SmartSearchRequest) -> SearchResponse:
        if request.query.strip():
            parsed, parser_source = await self.parser.parse(request.query)
            embedding = await embedding_service.embed(request.query)
        else:
            parsed, parser_source = ParsedQuery(), "filters"
            embedding = None

        category = request.category or parsed.category
        min_price = (
            request.min_price if request.min_price is not None else parsed.min_price
        )
        max_price = (
            request.max_price if request.max_price is not None else parsed.max_price
        )
        products, product_source = self.repository.search(
            keywords=parsed.keywords,
            category=category,
            min_price=min_price,
            max_price=max_price,
            limit=request.limit,
            embedding=embedding,
        )
        effective_query = parsed.model_copy(
            update={
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
            }
        )
        return SearchResponse(
            products=products,
            total=len(products),
            source=f"{product_source}:{parser_source}",
            parsed_query=effective_query,
        )
