from fastapi import APIRouter, Depends

from app.api.v1 import conversations, products, shopping, system
from app.core.security import require_api_key

api_router = APIRouter(dependencies=[Depends(require_api_key)])
api_router.include_router(system.router)
api_router.include_router(products.router)
api_router.include_router(shopping.router)
api_router.include_router(conversations.router)