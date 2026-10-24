from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.content_asset_routers import content_asset_router
from app.apis.v1.guide_routers import guide_router
from app.apis.v1.hospital_contact_routers import hospital_contact_router
from app.apis.v1.hospital_routers import hospital_router
from app.apis.v1.medical_record_routers import medical_record_router
from app.apis.v1.ocr_routers import ocr_router
from app.apis.v1.reminder_routers import reminder_router
from app.apis.v1.service_routers import service_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(reminder_router)
v1_routers.include_router(content_asset_router)
v1_routers.include_router(medical_record_router)
v1_routers.include_router(guide_router)
v1_routers.include_router(ocr_router)
v1_routers.include_router(hospital_router)
v1_routers.include_router(service_router)
v1_routers.include_router(hospital_contact_router)
