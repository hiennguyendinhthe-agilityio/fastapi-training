"""
app/api/v1/api.py
Router aggregator — includes all v1 sub-routers under /api/v1.

Implemented in: Task 6.4

Aggregates:
- auth_router: /api/v1/auth
- users_router: /api/v1/users
- products_router: /api/v1/products
- orders_router: /api/v1/orders
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(products_router)
api_router.include_router(orders_router)
