from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.products import ProductRepository
from app.schemas.shopping import (
    ParseQueryRequest,
    ParseQueryResponse,
    SearchRequest,
    SearchResponse,
    SmartSearchRequest,
)
from app.services.query_parser import QueryParser
from app.services.search import ShoppingSearchService

router = APIRouter(prefix="/shopping", tags=["shopping"])


@router.post("/parse-query", response_model=ParseQueryResponse)
async def parse_query(request: ParseQueryRequest) -> ParseQueryResponse:
    parsed, source = await QueryParser().parse(request.query)
    return ParseQueryResponse(parsed=parsed, source=source)


@router.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SearchResponse:
    return ShoppingSearchService(ProductRepository(db)).search(request)


@router.post("/smart-search", response_model=SearchResponse)
async def smart_search(
    request: SmartSearchRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SearchResponse:
    return await ShoppingSearchService(ProductRepository(db)).smart_search(request)
