"""
User Preferences Service for v2.5 Milestone

Stores and retrieves user preferences with learning from conversion history.
Simple in-memory store that can be enhanced with Redis later.

See: docs/GAP-ANALYSIS-v2.5.md
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import threading


logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class UserPreferenceProfile(BaseModel):
    """User's preference profile for conversions."""

    user_id: str
    preferred_detail_level: str = "standard"
    preferred_validation_level: str = "standard"
    preferred_timeout_seconds: int = 300
    enable_auto_fix: bool = True
    enable_ai_assistance: bool = True
    parallel_processing: bool = True
    quality_threshold: float = 0.8

    # Learning data
    total_conversions: int = 0
    successful_conversions: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Mode-specific preferences
    mode_preferences: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_conversions == 0:
            return 0.0
        return self.successful_conversions / self.total_conversions


class ConversionHistoryEntry(BaseModel):
    """Single conversion history entry."""

    conversion_id: str
    user_id: str
    mode: str
    settings_used: Dict[str, Any]
    success: bool
    duration_seconds: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# In-Memory Store
# =============================================================================

class InMemoryPreferenceStore:
    """
    Thread-safe in-memory store for user preferences.

    This is a simple implementation that can be enhanced with Redis later.
    Data is stored in memory and will be lost on restart.
    """

    def __init__(self):
        self._preferences: Dict[str, UserPreferenceProfile] = {}
        self._history: Dict[str, List[ConversionHistoryEntry]] = {}  # user_id -> history
        self._lock = threading.RLock()

    def get_preferences(self, user_id: str) -> Optional[UserPreferenceProfile]:
        """Get user preferences by user_id."""
        with self._lock:
            return self._preferences.get(user_id)

    def save_preferences(self, profile: UserPreferenceProfile) -> None:
        """Save user preferences."""
        with self._lock:
            profile.last_updated = datetime.utcnow()
            self._preferences[profile.user_id] = profile
            logger.debug(f"Saved preferences for user {profile.user_id}")

    def add_history(self, entry: ConversionHistoryEntry) -> None:
        """Add a conversion history entry."""
        with self._lock:
            if entry.user_id not in self._history:
                self._history[entry.user_id] = []

            self._history[entry.user_id].append(entry)

            # Keep only last 100 entries per user
            if len(self._history[entry.user_id]) > 100:
                self._history[entry.user_id] = self._history[entry.user_id][-100:]

    def get_history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[ConversionHistoryEntry]:
        """Get conversion history for a user."""
        with self._lock:
            history = self._history.get(user_id, [])
            return history[-limit:]

    def get_successful_history(
        self,
        user_id: str,
        mode: Optional[str] = None,
        limit: int = 20,
    ) -> List[ConversionHistoryEntry]:
        """Get successful conversion history, optionally filtered by mode."""
        with self._lock:
            history = self._history.get(user_id, [])
            successful = [h for h in history if h.success]

            if mode:
                successful = [h for h in successful if h.mode == mode]

            return successful[-limit:]


# =============================================================================
# User Preferences Service
# =============================================================================

class UserPreferencesService:
    """
    Service for managing user preferences with learning capabilities.

    Features:
    - Store and retrieve user preferences
    - Learn from conversion history
    - Provide personalized defaults based on user history
    """

    def __init__(self, store: Optional[InMemoryPreferenceStore] = None):
        self._store = store or InMemoryPreferenceStore()

    async def get_preferences(self, user_id: str) -> Optional[UserPreferenceProfile]:
        """Get user preferences."""
        return self._store.get_preferences(user_id)

    async def save_preferences(self, profile: UserPreferenceProfile) -> None:
        """Save user preferences."""
        self._store.save_preferences(profile)

    async def update_preferences(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> UserPreferenceProfile:
        """
        Update user preferences with new values.

        Args:
            user_id: User ID
            updates: Dictionary of preference values to update

        Returns:
            Updated preference profile
        """
        profile = self._store.get_preferences(user_id)

        if profile is None:
            # Create new profile
            profile = UserPreferenceProfile(user_id=user_id)

        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow()
        self._store.save_preferences(profile)

        return profile

    async def learn_from_conversion(
        self,
        conversion_id: str,
        user_id: str,
        mode: str,
        settings_used: Dict[str, Any],
        success: bool,
        duration_seconds: int,
    ) -> None:
        """
        Learn from a conversion to improve future defaults.

        This is called after a conversion completes to update the user's
        preference profile based on what worked.
        """
        # Add history entry
        entry = ConversionHistoryEntry(
            conversion_id=conversion_id,
            user_id=user_id,
            mode=mode,
            settings_used=settings_used,
            success=success,
            duration_seconds=duration_seconds,
        )
        self._store.add_history(entry)

        # Update profile statistics
        profile = self._store.get_preferences(user_id)

        if profile is None:
            profile = UserPreferenceProfile(user_id=user_id)

        profile.total_conversions += 1
        if success:
            profile.successful_conversions += 1

        # Learn mode-specific preferences from successful conversions
        if success:
            await self._learn_mode_preferences(profile, mode, settings_used)

        profile.last_updated = datetime.utcnow()
        self._store.save_preferences(profile)

        logger.info(
            f"Learned from conversion {conversion_id}: "
            f"user={user_id}, mode={mode}, success={success}"
        )

    async def _learn_mode_preferences(
        self,
        profile: UserPreferenceProfile,
        mode: str,
        settings: Dict[str, Any],
    ) -> None:
        """Learn mode-specific preferences from successful conversions."""
        if mode not in profile.mode_preferences:
            profile.mode_preferences[mode] = {}

        mode_prefs = profile.mode_preferences[mode]

        # Learn from successful settings
        for key, value in settings.items():
            if key in ("detail_level", "validation_level", "enable_auto_fix",
                       "enable_ai_assistance", "parallel_processing"):
                mode_prefs[key] = value
            elif key in ("timeout_seconds", "max_retries", "quality_threshold"):
                # Average numeric values over time
                if key in mode_prefs:
                    current = mode_prefs[key]
                    if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                        mode_prefs[key] = (current + value) / 2
                else:
                    mode_prefs[key] = value

    async def get_personalized_defaults(
        self,
        user_id: str,
        mode: str,
    ) -> Dict[str, Any]:
        """
        Get personalized default settings for a user based on their history.

        Args:
            user_id: User ID
            mode: Conversion mode (simple, standard, complex, expert)

        Returns:
            Dictionary of personalized default settings
        """
        profile = self._store.get_preferences(user_id)

        if profile is None:
            return {}

        # Check for mode-specific preferences first
        if mode in profile.mode_preferences:
            return profile.mode_preferences[mode].copy()

        # Fall back to general preferences
        defaults = {}

        if profile.preferred_detail_level:
            defaults["detail_level"] = profile.preferred_detail_level
        if profile.preferred_validation_level:
            defaults["validation_level"] = profile.preferred_validation_level
        if profile.preferred_timeout_seconds:
            defaults["timeout_seconds"] = profile.preferred_timeout_seconds

        defaults["enable_auto_fix"] = profile.enable_auto_fix
        defaults["enable_ai_assistance"] = profile.enable_ai_assistance
        defaults["parallel_processing"] = profile.parallel_processing
        defaults["quality_threshold"] = profile.quality_threshold

        return defaults

    async def get_conversion_history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[ConversionHistoryEntry]:
        """Get conversion history for a user."""
        return self._store.get_history(user_id, limit)

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's conversions."""
        profile = self._store.get_preferences(user_id)

        if profile is None:
            return {
                "total_conversions": 0,
                "successful_conversions": 0,
                "success_rate": 0.0,
            }

        return {
            "total_conversions": profile.total_conversions,
            "successful_conversions": profile.successful_conversions,
            "success_rate": profile.success_rate,
            "mode_preferences": list(profile.mode_preferences.keys()),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_user_preferences_service: Optional[UserPreferencesService] = None


def get_user_preferences_service() -> UserPreferencesService:
    """Get singleton UserPreferencesService instance."""
    global _user_preferences_service
    if _user_preferences_service is None:
        _user_preferences_service = UserPreferencesService()
    return _user_preferences_service
