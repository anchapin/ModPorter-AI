"""
Email Verification API Endpoints

Handles user email verification flow.
"""

import logging
from datetime import datetime, timedelta
<<<<<<< HEAD
=======
from typing import Optional
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from db.base import get_db
from db.models import User
from services.email_service import get_email_service, EmailMessage
<<<<<<< HEAD
from security.auth import generate_verification_token
=======
from security.auth import generate_verification_token, hash_password
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterWithVerificationRequest(BaseModel):
    """User registration with email verification."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    email: EmailStr
    password: str


class RegisterWithVerificationResponse(BaseModel):
    """Registration response."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    message: str
    user_id: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """Resend verification response."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    message: str


@router.post("/register-verify", response_model=RegisterWithVerificationResponse)
async def register_with_verification(
    request: RegisterWithVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user with email verification.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    - Creates user account (unverified)
    - Sends verification email
    - User must verify before logging in
    """
    from security.auth import hash_password
<<<<<<< HEAD

    # Check if user already exists
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

=======
    
    # Check if user already exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered and verified",
            )
        else:
            # Delete unverified user to allow re-registration
            await db.delete(existing_user)
            await db.commit()
<<<<<<< HEAD

    # Generate verification token
    verification_token = generate_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)

=======
    
    # Generate verification token
    verification_token = generate_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        verification_token=verification_token,
        verification_token_expires=verification_expires,
        is_verified=False,
    )
<<<<<<< HEAD

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification email
    email_service = get_email_service()
    verification_url = f"https://modporter.ai/verify-email/{verification_token}"

=======
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Send verification email
    email_service = get_email_service()
    verification_url = f"https://modporter.ai/verify-email/{verification_token}"
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    message = EmailMessage(
        to=request.email,
        subject="Verify your ModPorter AI account",
        template="email_verification",
        context={
            "verification_url": verification_url,
            "expiry_hours": 24,
        },
    )
<<<<<<< HEAD

    await email_service.send(message)

    logger.info(f"Verification email sent to {request.email}")

=======
    
    await email_service.send(message)
    
    logger.info(f"Verification email sent to {request.email}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return RegisterWithVerificationResponse(
        message="Registration successful. Please check your email to verify your account.",
        user_id=str(user.id),
    )


@router.get("/verify-email/{token}", response_model=dict)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email address using verification token.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    - Validates token
    - Marks user as verified
    - Clears verification token
    """
    from sqlalchemy import select
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Find user with valid token
    result = await db.execute(
        select(User).where(
            User.verification_token == token,
            User.verification_token_expires > datetime.utcnow(),
        )
    )
    user = result.scalar_one_or_none()
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
<<<<<<< HEAD

    await db.commit()

    logger.info(f"Email verified for user {user.email}")

=======
    
    await db.commit()
    
    logger.info(f"Email verified for user {user.email}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return {
        "message": "Email verified successfully",
        "email": user.email,
    }


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend verification email.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    - Finds unverified user
    - Generates new token
    - Sends new verification email
    """
    from sqlalchemy import select
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Find unverified user
    result = await db.execute(
        select(User).where(
            User.email == request.email,
<<<<<<< HEAD
            not User.is_verified,
        )
    )
    user = result.scalar_one_or_none()

=======
            User.is_verified == False,
        )
    )
    user = result.scalar_one_or_none()
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    if not user:
        # Don't reveal if email exists
        return ResendVerificationResponse(
            message="If the email is registered, a new verification link has been sent.",
        )
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Check if token is still valid (prevent spam)
    if user.verification_token_expires and user.verification_token_expires > datetime.utcnow():
        # Token still valid, don't resend
        return ResendVerificationResponse(
            message="Verification email already sent. Please check your inbox.",
        )
<<<<<<< HEAD

    # Generate new token
    verification_token = generate_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)

    user.verification_token = verification_token
    user.verification_token_expires = verification_expires

    await db.commit()

    # Send verification email
    email_service = get_email_service()
    verification_url = f"https://modporter.ai/verify-email/{verification_token}"

=======
    
    # Generate new token
    verification_token = generate_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)
    
    user.verification_token = verification_token
    user.verification_token_expires = verification_expires
    
    await db.commit()
    
    # Send verification email
    email_service = get_email_service()
    verification_url = f"https://modporter.ai/verify-email/{verification_token}"
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    message = EmailMessage(
        to=request.email,
        subject="Verify your ModPorter AI account",
        template="email_verification",
        context={
            "verification_url": verification_url,
            "expiry_hours": 24,
        },
    )
<<<<<<< HEAD

    await email_service.send(message)

    logger.info(f"Verification email resent to {request.email}")

=======
    
    await email_service.send(message)
    
    logger.info(f"Verification email resent to {request.email}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return ResendVerificationResponse(
        message="If the email is registered, a new verification link has been sent.",
    )
