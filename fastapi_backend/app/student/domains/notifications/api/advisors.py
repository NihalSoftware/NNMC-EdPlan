from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings
from app.models.user import User
from app.security.auth import get_current_user
from app.student.domains.notifications.services import notification_service

router = APIRouter(tags=["users"])


class AdvisorNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    email: EmailStr | None = None
    advisor_email: EmailStr = Field(validation_alias="advisorEmail")
    body: str = Field(default="", max_length=20_000)


@router.post("/users/email-advisor")
async def email_advisor(
    data: AdvisorNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if data.email and str(data.email).lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The sender email does not match the authenticated user.",
        )
    _require_allowed_advisor_recipient(str(data.advisor_email))
    await run_in_threadpool(
        notification_service.notify_advisor,
        email=current_user.email,
        advisor_email=str(data.advisor_email),
        body=data.body,
    )
    return {"success": True, "message": "Advisor notified", "data": None}


def _require_allowed_advisor_recipient(email: str) -> None:
    domain = email.rsplit("@", maxsplit=1)[-1].lower()
    if not any(
        domain == allowed or domain.endswith(f".{allowed}")
        for allowed in settings.advisor_email_domains
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Advisor email must use an approved institutional domain.",
        )
