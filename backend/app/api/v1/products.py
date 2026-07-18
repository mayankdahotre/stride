from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.products import ProductRepository
from app.schemas.shopping import CategoriesResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=CategoriesResponse)
def categories(db: Annotated[Session, Depends(get_db)]) -> CategoriesResponse:
    values, _ = ProductRepository(db).categories()
    return CategoriesResponse(categories=values)
