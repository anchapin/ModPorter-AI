"""
Tests for user_preferences.py - InMemoryPreferenceStore and UserPreferencesService.
"""

import pytest

from services.user_preferences import (
    InMemoryPreferenceStore,
    UserPreferenceProfile,
    ConversionHistoryEntry,
    UserPreferencesService,
    get_user_preferences_service,
)


def _make_entry(user_id="u1", mode="simple", success=True, conversion_id="c1"):
    return ConversionHistoryEntry(
        conversion_id=conversion_id,
        user_id=user_id,
        mode=mode,
        settings_used={"detail_level": "standard"},
        success=success,
        duration_seconds=10,
    )


def _make_profile(user_id="u1", **overrides):
    defaults = {"user_id": user_id}
    defaults.update(overrides)
    return UserPreferenceProfile(**defaults)


class TestUserPreferenceProfile:
    def test_success_rate_zero_conversions(self):
        p = _make_profile()
        assert p.success_rate == 0.0

    def test_success_rate_calculation(self):
        p = _make_profile(total_conversions=10, successful_conversions=7)
        assert p.success_rate == 0.7

    def test_default_values(self):
        p = _make_profile()
        assert p.preferred_detail_level == "standard"
        assert p.preferred_validation_level == "standard"
        assert p.preferred_timeout_seconds == 300
        assert p.enable_auto_fix is True
        assert p.enable_ai_assistance is True
        assert p.parallel_processing is True
        assert p.quality_threshold == 0.8
        assert p.mode_preferences == {}


class TestConversionHistoryEntry:
    def test_entry_creation(self):
        e = _make_entry()
        assert e.conversion_id == "c1"
        assert e.user_id == "u1"
        assert e.mode == "simple"
        assert e.success is True
        assert e.duration_seconds == 10


class TestInMemoryPreferenceStore:
    def test_get_preferences_missing(self):
        store = InMemoryPreferenceStore()
        assert store.get_preferences("nonexistent") is None

    def test_save_and_get_preferences(self):
        store = InMemoryPreferenceStore()
        profile = _make_profile()
        store.save_preferences(profile)
        result = store.get_preferences("u1")
        assert result is not None
        assert result.user_id == "u1"

    def test_save_overwrites(self):
        store = InMemoryPreferenceStore()
        store.save_preferences(_make_profile(preferred_detail_level="basic"))
        store.save_preferences(_make_profile(preferred_detail_level="expert"))
        result = store.get_preferences("u1")
        assert result.preferred_detail_level == "expert"

    def test_add_history_new_user(self):
        store = InMemoryPreferenceStore()
        store.add_history(_make_entry())
        history = store.get_history("u1")
        assert len(history) == 1

    def test_add_history_appends(self):
        store = InMemoryPreferenceStore()
        store.add_history(_make_entry(conversion_id="c1"))
        store.add_history(_make_entry(conversion_id="c2"))
        history = store.get_history("u1")
        assert len(history) == 2

    def test_add_history_truncates_at_100(self):
        store = InMemoryPreferenceStore()
        for i in range(105):
            store.add_history(_make_entry(conversion_id=f"c{i}"))
        history = store.get_history("u1", limit=200)
        assert len(history) == 100
        assert history[0].conversion_id == "c5"

    def test_get_history_limit(self):
        store = InMemoryPreferenceStore()
        for i in range(5):
            store.add_history(_make_entry(conversion_id=f"c{i}"))
        history = store.get_history("u1", limit=3)
        assert len(history) == 3

    def test_get_history_empty(self):
        store = InMemoryPreferenceStore()
        assert store.get_history("nonexistent") == []

    def test_get_successful_history_no_filter(self):
        store = InMemoryPreferenceStore()
        store.add_history(_make_entry(success=True))
        store.add_history(_make_entry(success=False))
        result = store.get_successful_history("u1")
        assert len(result) == 1
        assert result[0].success is True

    def test_get_successful_history_with_mode_filter(self):
        store = InMemoryPreferenceStore()
        store.add_history(_make_entry(mode="simple", success=True))
        store.add_history(_make_entry(mode="complex", success=True))
        result = store.get_successful_history("u1", mode="simple")
        assert len(result) == 1
        assert result[0].mode == "simple"

    def test_get_successful_history_empty(self):
        store = InMemoryPreferenceStore()
        assert store.get_successful_history("nonexistent") == []


@pytest.fixture
def service():
    return UserPreferencesService()


class TestUserPreferencesService:
    @pytest.mark.asyncio
    async def test_get_preferences_missing(self, service):
        result = await service.get_preferences("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_get(self, service):
        profile = _make_profile()
        await service.save_preferences(profile)
        result = await service.get_preferences("u1")
        assert result is not None
        assert result.user_id == "u1"

    @pytest.mark.asyncio
    async def test_update_preferences_existing(self, service):
        await service.save_preferences(_make_profile())
        updated = await service.update_preferences("u1", {"preferred_detail_level": "expert"})
        assert updated.preferred_detail_level == "expert"

    @pytest.mark.asyncio
    async def test_update_preferences_creates_new(self, service):
        updated = await service.update_preferences("u2", {"preferred_detail_level": "basic"})
        assert updated.user_id == "u2"
        assert updated.preferred_detail_level == "basic"

    @pytest.mark.asyncio
    async def test_update_preferences_ignores_invalid_keys(self, service):
        await service.save_preferences(_make_profile())
        updated = await service.update_preferences("u1", {"nonexistent_field": "value"})
        assert not hasattr(updated, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_learn_from_conversion_success(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="simple",
            settings_used={"detail_level": "high"},
            success=True,
            duration_seconds=10,
        )
        stats = await service.get_user_stats("u1")
        assert stats["total_conversions"] == 1
        assert stats["successful_conversions"] == 1
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_learn_from_conversion_failure(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="complex",
            settings_used={},
            success=False,
            duration_seconds=300,
        )
        stats = await service.get_user_stats("u1")
        assert stats["total_conversions"] == 1
        assert stats["successful_conversions"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_learn_mode_preferences_string_settings(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="simple",
            settings_used={
                "detail_level": "high",
                "validation_level": "strict",
                "enable_auto_fix": False,
                "enable_ai_assistance": True,
                "parallel_processing": True,
            },
            success=True,
            duration_seconds=10,
        )
        defaults = await service.get_personalized_defaults("u1", "simple")
        assert defaults["detail_level"] == "high"
        assert defaults["validation_level"] == "strict"

    @pytest.mark.asyncio
    async def test_learn_mode_preferences_numeric_averaging(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="standard",
            settings_used={"timeout_seconds": 200},
            success=True,
            duration_seconds=10,
        )
        await service.learn_from_conversion(
            conversion_id="c2",
            user_id="u1",
            mode="standard",
            settings_used={"timeout_seconds": 400},
            success=True,
            duration_seconds=20,
        )
        defaults = await service.get_personalized_defaults("u1", "standard")
        assert defaults["timeout_seconds"] == 300.0

    @pytest.mark.asyncio
    async def test_get_personalized_defaults_no_profile(self, service):
        result = await service.get_personalized_defaults("nonexistent", "simple")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_personalized_defaults_fallback_to_general(self, service):
        await service.save_preferences(_make_profile())
        defaults = await service.get_personalized_defaults("u1", "unknown_mode")
        assert defaults["detail_level"] == "standard"
        assert defaults["validation_level"] == "standard"
        assert defaults["timeout_seconds"] == 300
        assert defaults["enable_auto_fix"] is True

    @pytest.mark.asyncio
    async def test_get_conversion_history(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="simple",
            settings_used={},
            success=True,
            duration_seconds=10,
        )
        await service.learn_from_conversion(
            conversion_id="c2",
            user_id="u1",
            mode="complex",
            settings_used={},
            success=False,
            duration_seconds=20,
        )
        history = await service.get_conversion_history("u1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_user_stats_no_profile(self, service):
        stats = await service.get_user_stats("nonexistent")
        assert stats["total_conversions"] == 0
        assert stats["successful_conversions"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_user_stats_with_mode_preferences(self, service):
        await service.learn_from_conversion(
            conversion_id="c1",
            user_id="u1",
            mode="simple",
            settings_used={"detail_level": "high"},
            success=True,
            duration_seconds=10,
        )
        stats = await service.get_user_stats("u1")
        assert "simple" in stats["mode_preferences"]


class TestGetSingleton:
    def test_returns_instance(self):
        import services.user_preferences as mod

        mod._user_preferences_service = None
        svc = get_user_preferences_service()
        assert isinstance(svc, UserPreferencesService)

    def test_returns_same_instance(self):
        import services.user_preferences as mod

        mod._user_preferences_service = None
        svc1 = get_user_preferences_service()
        svc2 = get_user_preferences_service()
        assert svc1 is svc2
        mod._user_preferences_service = None
