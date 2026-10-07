from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.medical_record_routers import medical_record_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(medical_record_router)
