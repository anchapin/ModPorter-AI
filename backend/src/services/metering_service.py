"""
Metering Service for subscription tier usage limits (Issue #977, #1226)

Provides:
- Tier-based conversion limits (Free: 1/month, Creator/Pro: unlimited, Studio: unlimited + API)
- PAYG credit-based conversions (credits never expire)
- BYOK (Bring Your Own Key) tier variants
- Monthly usage tracking with automatic reset
- API usage tracking separate from web UI usage
- Usage queries for UI display
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, UsageRecord

logger = logging.getLogger(__name__)


TIER_LIMITS = {
    "free": {
        "monthly_conversions": 1,
        "monthly_api_calls": 0,
        "has_api_access": False,
        "max_jar_size_mb": 5,
    },
    "payg": {
        "monthly_conversions": -1,
        "monthly_api_calls": 0,
        "has_api_access": False,
        "max_jar_size_mb": 100,
    },
    "creator": {
        "monthly_conversions": -1,
        "monthly_api_calls": 0,
        "has_api_access": False,
        "max_jar_size_mb": 100,
    },
    "creator_byok": {
        "monthly_conversions": -1,
        "monthly_api_calls": 0,
        "has_api_access": False,
        "max_jar_size_mb": 100,
    },
    "pro": {
        "monthly_conversions": -1,
        "monthly_api_calls": 0,
        "has_api_access": False,
        "max_jar_size_mb": 100,
    },
    "studio": {
        "monthly_conversions": -1,
        "monthly_api_calls": 1000,
        "has_api_access": True,
        "max_jar_size_mb": 500,
    },
    "studio_byok": {
        "monthly_conversions": -1,
        "monthly_api_calls": 500,
        "has_api_access": True,
        "max_jar_size_mb": 500,
    },
    "enterprise": {
        "monthly_conversions": -1,
        "monthly_api_calls": -1,
        "has_api_access": True,
        "max_jar_size_mb": -1,
    },
}

UPGRADE_THRESHOLD = 0.8  # 80% of limit triggers upgrade prompt


@dataclass
class UsageInfo:
    """Current usage information for a user"""

    tier: str
    period_year: int
    period_month: int
    web_conversions: int
    api_conversions: int
    monthly_limit: int
    api_limit: int
    remaining: int
    api_remaining: int
    is_at_limit: bool
    is_api_at_limit: bool
    should_upgrade: bool
    upgrade_message: Optional[str] = None


@dataclass
class MeteringResult:
    """Result of a metering check"""

    allowed: bool
    usage_info: UsageInfo
    error_message: Optional[str] = None
    upgrade_cta: Optional[str] = None


class MeteringService:
    """Service for metering and enforcing subscription tier usage limits"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_current_period(self) -> tuple[int, int]:
        """Get current year and month for usage tracking"""
        now = datetime.now(timezone.utc)
        return now.year, now.month

    def _get_tier_limits(self, tier: str) -> dict:
        """Get limits for a subscription tier"""
        return TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    async def get_or_create_usage_record(self, user_id: UUID, year: int, month: int) -> UsageRecord:
        """Get or create a usage record for the given period"""
        result = await self.db.execute(
            select(UsageRecord).where(
                and_(
                    UsageRecord.user_id == user_id,
                    UsageRecord.period_year == year,
                    UsageRecord.period_month == month,
                )
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            record = UsageRecord(
                user_id=user_id,
                period_year=year,
                period_month=month,
                web_conversions=0,
                api_conversions=0,
            )
            self.db.add(record)
            await self.db.flush()

        return record

    async def get_usage_info(self, user: User) -> UsageInfo:
        """Get current usage information for a user"""
        year, month = self._get_current_period()
        limits = self._get_tier_limits(user.subscription_tier)

        record = await self.get_or_create_usage_record(user.id, year, month)

        monthly_limit = limits["monthly_conversions"]
        api_limit = limits["monthly_api_calls"]

        if monthly_limit == -1:
            remaining = float("inf")
            is_at_limit = False
        else:
            remaining = max(0, monthly_limit - record.web_conversions)
            is_at_limit = record.web_conversions >= monthly_limit

        if api_limit == -1:
            api_remaining = float("inf")
            is_api_at_limit = False
        else:
            api_remaining = max(0, api_limit - record.api_conversions)
            is_api_at_limit = record.api_conversions >= api_limit

        should_upgrade = (
            monthly_limit != -1 and record.web_conversions >= monthly_limit * UPGRADE_THRESHOLD
        ) or (api_limit != 0 and record.api_conversions >= api_limit * UPGRADE_THRESHOLD)

        upgrade_message = None
        if should_upgrade and user.subscription_tier == "free":
            upgrade_message = (
                f"You've used {record.web_conversions} of your {monthly_limit} free monthly conversions. "
                f"Upgrade to Pro for unlimited conversions!"
            )

        return UsageInfo(
            tier=user.subscription_tier,
            period_year=year,
            period_month=month,
            web_conversions=record.web_conversions,
            api_conversions=record.api_conversions,
            monthly_limit=monthly_limit,
            api_limit=api_limit,
            remaining=remaining if remaining != float("inf") else -1,
            api_remaining=api_remaining if api_remaining != float("inf") else -1,
            is_at_limit=is_at_limit,
            is_api_at_limit=is_api_at_limit,
            should_upgrade=should_upgrade,
            upgrade_message=upgrade_message,
        )

    async def check_and_increment_web_usage(self, user: User) -> MeteringResult:
        """
        Check if user can perform a web conversion and increment counter if allowed.
        Returns MeteringResult with allowed=True if conversion is allowed.
        """
        year, month = self._get_current_period()
        limits = self._get_tier_limits(user.subscription_tier)
        monthly_limit = limits["monthly_conversions"]

        if monthly_limit == -1:
            record = await self.get_or_create_usage_record(user.id, year, month)
            record.web_conversions += 1
            await self.db.commit()
            usage_info = await self.get_usage_info(user)
            return MeteringResult(allowed=True, usage_info=usage_info)

        record = await self.get_or_create_usage_record(user.id, year, month)

        if record.web_conversions >= monthly_limit:
            usage_info = await self.get_usage_info(user)
            return MeteringResult(
                allowed=False,
                usage_info=usage_info,
                error_message="Monthly conversion limit reached",
                upgrade_cta=f"/billing?upgrade=true&tier=pro",
            )

        record.web_conversions += 1
        await self.db.commit()

        usage_info = await self.get_usage_info(user)
        return MeteringResult(allowed=True, usage_info=usage_info)

    async def check_and_increment_api_usage(self, user: User) -> MeteringResult:
        """
        Check if user can perform an API conversion and increment counter if allowed.
        Only Studio and Enterprise tiers have API access.
        """
        year, month = self._get_current_period()
        limits = self._get_tier_limits(user.subscription_tier)

        if not limits["has_api_access"]:
            usage_info = await self.get_usage_info(user)
            return MeteringResult(
                allowed=False,
                usage_info=usage_info,
                error_message="API access requires Studio or Enterprise tier",
                upgrade_cta="/billing?upgrade=true&tier=studio",
            )

        api_limit = limits["monthly_api_calls"]

        if api_limit == -1:
            record = await self.get_or_create_usage_record(user.id, year, month)
            record.api_conversions += 1
            await self.db.commit()
            usage_info = await self.get_usage_info(user)
            return MeteringResult(allowed=True, usage_info=usage_info)

        record = await self.get_or_create_usage_record(user.id, year, month)

        if record.api_conversions >= api_limit:
            usage_info = await self.get_usage_info(user)
            return MeteringResult(
                allowed=False,
                usage_info=usage_info,
                error_message="Monthly API call limit reached",
                upgrade_cta="/billing?upgrade=true&tier=studio",
            )

        record.api_conversions += 1
        await self.db.commit()

        usage_info = await self.get_usage_info(user)
        return MeteringResult(allowed=True, usage_info=usage_info)

    async def get_usage_for_period(
        self, user_id: UUID, year: int, month: int
    ) -> Optional[UsageRecord]:
        """Get usage record for a specific period"""
        result = await self.db.execute(
            select(UsageRecord).where(
                and_(
                    UsageRecord.user_id == user_id,
                    UsageRecord.period_year == year,
                    UsageRecord.period_month == month,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_usage_history(self, user_id: UUID, months: int = 6) -> list[UsageRecord]:
        """Get usage records for the last N months"""
        now = datetime.now(timezone.utc)
        records = []

        for i in range(months):
            month_date = datetime(now.year, now.month, 1) - datetime.timedelta(days=30 * i)
            year, month = month_date.year, month_date.month
            record = await self.get_usage_for_period(user_id, year, month)
            if record:
                records.append(record)

        return records
