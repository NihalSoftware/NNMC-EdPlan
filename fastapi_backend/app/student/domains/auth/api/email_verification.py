from fastapi import APIRouter, HTTPException, status

from app.student.domains.auth.schemas.auth import EmailVerificationRequest

router = APIRouter(tags=["users"])


@router.post("/users/email-verification/request")
async def request_email_verification(data: EmailVerificationRequest):
    """Do not claim verification until a delivery and token flow exists."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email verification is not configured.",
    )


@router.get("/users/email-verification/status")
async def get_email_verification_status(email: str):
    """Return the current disabled email-verification status."""
    if not email:
        raise HTTPException(status_code=400, detail="email parameter is required")

    return {
        "success": True,
        "message": "Verification status retrieved",
        "data": {"verified": False, "email": email},
    }
