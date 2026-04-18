"""
Stripe Billing API endpoints for ModPorter AI (Issue #970)

Endpoints:
- POST /api/v1/billing/checkout - Create Stripe Checkout session
- POST /api/v1/billing/portal - Create Stripe Customer Portal session
- POST /api/v1/billing/webhook - Handle Stripe webhook events
- GET /api/v1/billing/subscription - Get current user's subscription status
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Billing"])

security = HTTPBearer()

STRIPE_SECRET_KEY = ""  # Loaded from env
STRIPE_PUBLISHABLE_KEY = ""  # Loaded from env
STRIPE_WEBHOOK_SECRET = ""  # Loaded from env

TIER_PRICE_IDS = {
    "pro": "prod_ULsnGiOD4DbTer",
    "studio": "prod_ULso0In8XJcHQv",
    "enterprise": None,  # Enterprise uses custom pricing, no subscription
}

FREE_TRIAL_DAYS = 14


def get_stripe():
    """Get configured Stripe instance"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    secret_key = os.getenv("STRIPE_SECRET_KEY", STRIPE_SECRET_KEY)
    if not secret_key:
        logger.warning("Stripe secret key not configured - billing endpoints will fail")
    stripe.api_key = secret_key
    return stripe


def init_stripe():
    """Initialize Stripe settings from environment"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    global STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", STRIPE_SECRET_KEY)
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", STRIPE_PUBLISHABLE_KEY)
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", STRIPE_WEBHOOK_SECRET)


init_stripe()


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session"""

    tier: str = "pro"  # "pro" or "studio"
    trial: bool = True  # Whether to include free trial
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout session URL"""

    checkout_url: str
    session_id: str


class PortalRequest(BaseModel):
    """Request to create a Stripe Customer Portal session"""

    return_url: Optional[str] = None


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL"""

    portal_url: str


class SubscriptionStatus(BaseModel):
    """Current subscription status for a user"""

    tier: str
    status: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    current_period_end: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user"""
    from uuid import UUID

    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscription.

    Flow:
    1. User clicks CTA on PricingPage (e.g., "Start Free Trial" for Pro)
    2. Frontend calls this endpoint with tier and trial flag
    3. Backend creates Stripe Checkout session with optional trial
    4. Returns checkout_url for frontend redirect
    """
    from services.feature_flags import is_feature_enabled

    if not is_feature_enabled("premium_features"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium features are currently disabled. Please contact support if you believe this is an error.",
        )
    if request.tier not in TIER_PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    if request.tier == "enterprise":
        raise HTTPException(
            status_code=400, detail="Enterprise tier uses custom pricing - contact sales"
        )

    price_id = TIER_PRICE_IDS.get(request.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Price not configured for this tier")

    stripe_instance = get_stripe()
    import os
    from dotenv import load_dotenv

    load_dotenv()
    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")

    success_url = request.success_url or f"{base_url}/dashboard?billing=success"
    cancel_url = request.cancel_url or f"{base_url}/pricing?billing=cancelled"

    try:
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe_instance.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)},
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            db.add(user)
            await db.commit()

        session_params = {
            "customer": customer_id,
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "user_id": str(user.id),
                "tier": request.tier,
            },
        }

        if request.trial and request.tier in ("pro", "studio"):
            session_params["subscription_data"] = {
                "trial_period_days": FREE_TRIAL_DAYS,
            }

        session = stripe_instance.checkout.sessions.create(**session_params)

        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a Stripe Customer Portal session for self-service billing management.

    Allows users to:
    - View and update payment methods
    - Upgrade/downgrade subscriptions
    - Cancel subscriptions
    - Download invoices
    """
    from services.feature_flags import is_feature_enabled

    if not is_feature_enabled("premium_features"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium features are currently disabled. Please contact support if you believe this is an error.",
        )
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account found. Please subscribe first."
        )

    stripe_instance = get_stripe()
    import os
    from dotenv import load_dotenv

    load_dotenv()
    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")

    return_url = request.return_url or f"{base_url}/dashboard?billing=portal"

    try:
        session = stripe_instance.billing_portal.sessions.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )

        return PortalResponse(portal_url=session.url)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.post("/webhook")
async def handle_stripe_webhook(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events.

    Webhook events handled:
    - checkout.session.completed - Subscription created
    - customer.subscription.updated - Subscription updated (tier change)
    - customer.subscription.deleted - Subscription cancelled
    - invoice.payment_failed - Payment failed
    - invoice.paid - Payment successful (for recording)
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    stripe_instance = get_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", STRIPE_WEBHOOK_SECRET)

    body = await request.body()

    try:
        event = stripe_instance.webhook.construct_event(
            body, request.headers.get("stripe-signature", ""), webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await handle_checkout_completed(session, db)

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription, db)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_deleted(subscription, db)

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            await handle_payment_failed(invoice, db)

        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            await handle_invoice_paid(invoice, db)

        else:
            logger.info(f"Unhandled webhook event type: {event['type']}")

    except Exception as e:
        logger.error(f"Webhook handler error for {event.get('type')}: {e}")
        return Response(status_code=500, content="Webhook handler failed")

    return Response(status_code=200, content="OK")


async def handle_checkout_completed(session: dict, db: AsyncSession):
    """Handle checkout.session.completed - subscription created"""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier")
    subscription_id = session.get("subscription")

    if not user_id or not tier:
        logger.warning(f"Checkout completed missing metadata: user_id={user_id}, tier={tier}")
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found for checkout: {user_id}")
        return

    user.subscription_tier = tier
    user.stripe_subscription_id = subscription_id
    user.subscription_status = "active"

    stripe_instance = get_stripe()
    if subscription_id:
        try:
            subscription = stripe_instance.subscriptions.retrieve(subscription_id)
            if subscription.get("trial_end"):
                user.trial_ends_at = datetime.fromtimestamp(
                    subscription["trial_end"], tz=timezone.utc
                )
        except stripe.error.StripeError as e:
            logger.warning(f"Could not fetch subscription for trial end: {e}")

    db.add(user)
    await db.commit()
    logger.info(f"User {user_id} subscribed to {tier} (checkout.completed)")


async def handle_subscription_updated(subscription: dict, db: AsyncSession):
    """Handle customer.subscription.updated"""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    tier = "pro"  # Would need to derive from price lookup

    if subscription.get("items", {}).get("data"):
        price_id = subscription["items"]["data"][0].get("price", {}).get("id")
        if price_id == TIER_PRICE_IDS.get("studio"):
            tier = "studio"

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found for subscription update: {customer_id}")
        return

    user.subscription_status = status
    user.subscription_tier = tier

    if subscription.get("cancel_at_period_end"):
        user.subscription_status = "canceling"

    if subscription.get("trial_end"):
        user.trial_ends_at = datetime.fromtimestamp(subscription["trial_end"], tz=timezone.utc)

    db.add(user)
    await db.commit()
    logger.info(f"User {user.id} subscription updated: {tier} ({status})")


async def handle_subscription_deleted(subscription: dict, db: AsyncSession):
    """Handle customer.subscription.deleted - subscription cancelled"""
    customer_id = subscription.get("customer")

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found for subscription deletion: {customer_id}")
        return

    user.subscription_tier = "free"
    user.subscription_status = "canceled"
    user.stripe_subscription_id = None

    db.add(user)
    await db.commit()
    logger.info(f"User {user.id} subscription cancelled")


async def handle_payment_failed(invoice: dict, db: AsyncSession):
    """Handle invoice.payment_failed"""
    customer_id = invoice.get("customer")
    attempt_count = invoice.get("attempt_count", 1)

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.subscription_status = f"payment_failed (attempt {attempt_count})"
    db.add(user)
    await db.commit()
    logger.warning(f"User {user.id} payment failed (attempt {attempt_count})")


async def handle_invoice_paid(invoice: dict, db: AsyncSession):
    """Handle invoice.paid - successful payment"""
    customer_id = invoice.get("customer")

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    if user.subscription_status and user.subscription_status.startswith("payment_failed"):
        user.subscription_status = "active"
        db.add(user)
        await db.commit()


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    user: User = Depends(get_current_user),
):
    """Get current user's subscription status"""
    from services.feature_flags import is_feature_enabled

    if not is_feature_enabled("premium_features"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium features are currently disabled. Please contact support if you believe this is an error.",
        )
    return SubscriptionStatus(
        tier=user.subscription_tier or "free",
        status=user.subscription_status,
        trial_ends_at=user.trial_ends_at,
        stripe_customer_id=user.stripe_customer_id,
    )


@router.get("/publishable-key")
async def get_publishable_key():
    """Get Stripe publishable key for frontend"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    return {"publishable_key": publishable_key}
