from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.reminders import ReminderCreateRequest, ReminderResponse, ReminderUpdateRequest
from app.models.users import User
from app.services.reminders import ReminderService

reminder_router = APIRouter(prefix="/reminders", tags=["reminders"])


@reminder_router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    create_data: ReminderCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    reminder_service: Annotated[ReminderService, Depends(ReminderService)],
) -> Response:
    reminder = await reminder_service.create_reminder(user=user, data=create_data)
    return Response(ReminderResponse.model_validate(reminder).model_dump(), status_code=status.HTTP_201_CREATED)


@reminder_router.get("", response_model=list[ReminderResponse], status_code=status.HTTP_200_OK)
async def get_reminders(
    user: Annotated[User, Depends(get_request_user)],
    reminder_service: Annotated[ReminderService, Depends(ReminderService)],
) -> Response:
    reminders = await reminder_service.get_user_reminders(user=user)
    data = [ReminderResponse.model_validate(reminder).model_dump() for reminder in reminders]
    return Response(data, status_code=status.HTTP_200_OK)


@reminder_router.patch("/{reminder_id}", response_model=ReminderResponse, status_code=status.HTTP_200_OK)
async def update_reminder(
    reminder_id: int,
    update_data: ReminderUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    reminder_service: Annotated[ReminderService, Depends(ReminderService)],
) -> Response:
    reminder = await reminder_service.update_reminder(reminder_id=reminder_id, user=user, data=update_data)
    return Response(ReminderResponse.model_validate(reminder).model_dump(), status_code=status.HTTP_200_OK)


@reminder_router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    user: Annotated[User, Depends(get_request_user)],
    reminder_service: Annotated[ReminderService, Depends(ReminderService)],
) -> Response:
    await reminder_service.delete_reminder(reminder_id=reminder_id, user=user)
    return Response(None, status_code=status.HTTP_204_NO_CONTENT)
