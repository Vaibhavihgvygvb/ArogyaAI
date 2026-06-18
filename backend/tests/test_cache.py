import pytest
from app.cache.base import CacheStats, TTL
from app.cache.deps import get_cache_provider, set_cache_provider, reset_cache_provider
from app.cache.feature_flags import FeatureFlags
from app.cache.providers.memory import MemoryCacheProvider
from app.cache.service import CacheService


@pytest.fixture(autouse=True)
def memory_cache():
    provider = MemoryCacheProvider()
    set_cache_provider(provider)
    yield provider
    provider.clear()
    reset_cache_provider()


# ------------------------------------------------------------------
#  CacheProvider — Memory
# ------------------------------------------------------------------


class TestMemoryCacheProvider:
    def test_set_and_get(self):
        provider = get_cache_provider()
        provider.set("key1", "value1", ttl=TTL.DAY)
        assert provider.get("key1") == "value1"

    def test_get_missing_key(self):
        provider = get_cache_provider()
        assert provider.get("nonexistent") is None

    def test_delete_existing(self):
        provider = get_cache_provider()
        provider.set("key1", "value1")
        assert provider.delete("key1") is True
        assert provider.get("key1") is None

    def test_delete_missing(self):
        provider = get_cache_provider()
        assert provider.delete("nonexistent") is False

    def test_exists(self):
        provider = get_cache_provider()
        provider.set("key1", "value1")
        assert provider.exists("key1") is True
        assert provider.exists("nonexistent") is False

    def test_clear_all(self):
        provider = get_cache_provider()
        provider.set("a", 1)
        provider.set("b", 2)
        provider.set("c", 3)
        assert provider.clear() == 3
        assert provider.get("a") is None

    def test_clear_pattern(self):
        provider = get_cache_provider()
        provider.set("user:1", "alice")
        provider.set("user:2", "bob")
        provider.set("admin:1", "carol")
        assert provider.clear("user:*") == 2
        assert provider.get("user:1") is None
        assert provider.get("admin:1") == "carol"

    def test_ttl_expiry(self, monkeypatch):
        provider = get_cache_provider()
        provider.set("key1", "value1", ttl=1)
        assert provider.get("key1") == "value1"

        import time
        time.sleep(1.1)
        assert provider.get("key1") is None

    def test_get_many(self):
        provider = get_cache_provider()
        provider.set("a", 1)
        provider.set("b", 2)
        results = provider.get_many(["a", "b", "c"])
        assert results == {"a": 1, "b": 2, "c": None}

    def test_set_many(self):
        provider = get_cache_provider()
        provider.set_many({"x": 10, "y": 20}, ttl=TTL.LONG)
        assert provider.get("x") == 10
        assert provider.get("y") == 20

    def test_get_stats(self):
        provider = get_cache_provider()
        provider.set("a", 1)
        provider.set("b", 2)
        stats = provider.get_stats()
        assert stats.size == 2
        assert stats.memory_estimate_bytes > 0

    def test_cache_entry_expiry(self):
        from app.cache.base import CacheEntry
        from datetime import datetime, timedelta, timezone

        entry = CacheEntry(key="k", value="v", ttl=1)
        assert not entry.is_expired
        entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        assert entry.is_expired

    def test_concurrent_access(self):
        import threading

        provider = get_cache_provider()
        errors = []

        def worker(n):
            try:
                for i in range(100):
                    provider.set(f"k{n}_{i}", i)
                    val = provider.get(f"k{n}_{i}")
                    assert val == i
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ------------------------------------------------------------------
#  CacheService
# ------------------------------------------------------------------


class TestCacheService:
    def test_build_key(self):
        key = CacheService.build_key("test", "a", "b")
        assert "test" in key
        assert "a" in key
        assert "b" in key
        assert key.startswith("arogyaai:v1:test:")

    def test_build_namespace_pattern(self):
        pattern = CacheService.build_namespace_pattern("dashboard")
        assert pattern == "arogyaai:v1:dashboard:*"

    def test_set_and_get(self):
        CacheService.set("test:key", {"hello": "world"}, ttl=TTL.SHORT)
        result = CacheService.get("test:key")
        assert result is not None
        assert "hello" in result

    def test_get_or_set(self):
        computed = []

        def expensive():
            computed.append(1)
            return {"result": 42}

        key = "get_or_set:test"
        result1 = CacheService.get_or_set(key, TTL.SHORT, expensive)
        assert result1["result"] == 42
        assert len(computed) == 1

        result2 = CacheService.get_or_set(key, TTL.SHORT, expensive)
        assert result2["result"] == 42
        assert len(computed) == 1

    def test_invalidate_key(self):
        CacheService.set("test:inv", "value")
        assert CacheService.get("test:inv") is not None
        CacheService.invalidate_key("test:inv")
        assert CacheService.get("test:inv") is None

    def test_invalidate_namespace(self):
        CacheService.set("arogyaai:v1:dashboard:a", 1)
        CacheService.set("arogyaai:v1:dashboard:b", 2)
        CacheService.set("arogyaai:v1:other:c", 3)

        count = CacheService.invalidate_namespace("dashboard")
        assert count == 2
        assert CacheService.get("arogyaai:v1:dashboard:a") is None
        assert CacheService.get("arogyaai:v1:other:c") == 3

    def test_clear_all(self):
        CacheService.set("a", 1)
        CacheService.set("b", 2)
        assert CacheService.clear_all() == 2
        assert CacheService.get("a") is None

    def test_get_stats(self):
        CacheService.set("a", 1)
        stats = CacheService.get_stats()
        assert isinstance(stats, CacheStats)
        assert stats.size >= 1

    def test_get_many(self):
        CacheService.set("m1", 1)
        CacheService.set("m2", 2)
        results = CacheService.get_many(["m1", "m2", "m3"])
        assert results["m1"] == 1
        assert results["m2"] == 2
        assert results["m3"] is None

    def test_exists(self):
        CacheService.set("ex", "val")
        assert CacheService.exists("ex") is True
        assert CacheService.exists("nonexistent") is False

    def test_serialize_pydantic(self):
        from pydantic import BaseModel

        class DummyModel(BaseModel):
            name: str
            value: int

        obj = DummyModel(name="test", value=42)
        serialized = CacheService._serialize(obj)
        assert isinstance(serialized, str)
        assert "test" in serialized
        assert "42" in serialized

    def test_deserialize(self):
        data = '{"name": "test", "value": 42}'
        result = CacheService._deserialize(data)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_serialize_plain_dict(self):
        serialized = CacheService._serialize({"a": 1, "b": "hello"})
        assert isinstance(serialized, str)
        deserialized = CacheService._deserialize(serialized)
        assert deserialized["a"] == 1


# ------------------------------------------------------------------
#  FeatureFlags
# ------------------------------------------------------------------


class TestFeatureFlags:
    def test_flag_disabled_by_default(self):
        assert FeatureFlags.is_enabled("test_flag") is False

    def test_enable_and_check(self):
        FeatureFlags.enable("test_flag")
        assert FeatureFlags.is_enabled("test_flag") is True

    def test_disable(self):
        FeatureFlags.enable("test_flag")
        FeatureFlags.disable("test_flag")
        assert FeatureFlags.is_enabled("test_flag") is False

    def test_enable_with_custom_ttl(self):
        FeatureFlags.enable("short_flag", ttl=1)
        assert FeatureFlags.is_enabled("short_flag") is True

        import time
        time.sleep(1.1)
        assert FeatureFlags.is_enabled("short_flag") is False

    def test_clear_all_flags(self):
        FeatureFlags.enable("flag_a")
        FeatureFlags.enable("flag_b")
        assert FeatureFlags.clear_all_flags() >= 2
        assert FeatureFlags.is_enabled("flag_a") is False


# ------------------------------------------------------------------
#  Cache Integration — DashboardService
# ------------------------------------------------------------------


class TestDashboardCacheIntegration:
    def test_doctor_dashboard_cached(self, db, doctor_with_profile):
        from app.models.user import User
        from app.services.dashboard_service import DashboardService
        from app.core.security import decode_access_token

        payload = decode_access_token(doctor_with_profile)
        user = db.get(User, int(payload["sub"]))

        result1 = DashboardService.get_doctor_dashboard(db, user)
        assert result1 is not None

        key = CacheService.build_key("dashboard", "doctor", str(user.id))
        cached = CacheService.get(key)
        assert cached is not None
        assert "profile" in cached

    def test_patient_dashboard_cached(self, db, patient_with_profile):
        from app.models.user import User
        from app.services.dashboard_service import DashboardService
        from app.core.security import decode_access_token

        payload = decode_access_token(patient_with_profile)
        user = db.get(User, int(payload["sub"]))

        result1 = DashboardService.get_patient_dashboard(db, user)
        assert result1 is not None

        key = CacheService.build_key("dashboard", "patient", str(user.id))
        cached = CacheService.get(key)
        assert cached is not None

    def test_admin_dashboard_cached(self, db, admin_token):
        from app.models.user import User
        from app.services.dashboard_service import DashboardService
        from app.core.security import decode_access_token

        payload = decode_access_token(admin_token)
        user = db.get(User, int(payload["sub"]))

        result1 = DashboardService.get_admin_dashboard(db, user)
        assert result1 is not None

        key = CacheService.build_key("dashboard", "admin")
        cached = CacheService.get(key)
        assert cached is not None


# ------------------------------------------------------------------
#  Cache Integration — AnalyticsService
# ------------------------------------------------------------------


class TestAnalyticsCacheIntegration:
    def test_platform_analytics_cached(self, db, admin_token):
        from app.models.user import User
        from app.services.analytics_service import AnalyticsService
        from app.core.security import decode_access_token

        payload = decode_access_token(admin_token)
        user = db.get(User, int(payload["sub"]))

        result1 = AnalyticsService.get_platform_analytics(db)
        assert result1 is not None

        key = CacheService.build_key("analytics", "platform", "", "")
        cached = CacheService.get(key)
        assert cached is not None

    def test_analytics_summary_cached(self, db, admin_token):
        from app.services.analytics_service import AnalyticsService

        result1 = AnalyticsService.get_analytics_summary(db)
        assert result1 is not None

        key = CacheService.build_key("analytics", "summary")
        cached = CacheService.get(key)
        assert cached is not None


# ------------------------------------------------------------------
#  Cache Integration — NotificationService
# ------------------------------------------------------------------


class TestNotificationCacheIntegration:
    def test_unread_count_cached(self, db, patient_token):
        from app.models.user import User
        from app.services.notification_service import NotificationService
        from app.core.security import decode_access_token

        payload = decode_access_token(patient_token)
        user = db.get(User, int(payload["sub"]))

        count1 = NotificationService.get_unread_count(db, user.id)
        assert count1 == 0

        key = CacheService.build_key("notification", "unread", str(user.id))
        cached = CacheService.get(key)
        assert cached == 0

    def test_unread_cache_invalidated_on_create(self, db, patient_token):
        from app.models.user import User
        from app.schemas.notification import NotificationCreate
        from app.models.enums import NotificationType, NotificationPriority
        from app.services.notification_service import NotificationService
        from app.core.security import decode_access_token

        payload = decode_access_token(patient_token)
        user = db.get(User, int(payload["sub"]))

        key = CacheService.build_key("notification", "unread", str(user.id))
        NotificationService.get_unread_count(db, user.id)
        assert CacheService.get(key) == 0

        NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user.id,
                title="Test",
                message="Test message",
                notification_type=NotificationType.INFO,
                priority=NotificationPriority.LOW,
            ),
        )
        assert CacheService.get(key) is None

    def test_unread_cache_invalidated_on_mark_read(self, db, patient_token):
        from app.models.user import User
        from app.schemas.notification import NotificationCreate
        from app.models.enums import NotificationType, NotificationPriority
        from app.services.notification_service import NotificationService
        from app.core.security import decode_access_token

        payload = decode_access_token(patient_token)
        user = db.get(User, int(payload["sub"]))

        notif = NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=user.id,
                title="Test",
                message="Test msg",
                notification_type=NotificationType.INFO,
                priority=NotificationPriority.LOW,
            ),
        )

        key = CacheService.build_key("notification", "unread", str(user.id))
        NotificationService.get_unread_count(db, user.id)
        assert CacheService.get(key) is not None

        NotificationService.mark_as_read(db, notif.id)
        assert CacheService.get(key) is None

    def test_cache_namespace_notification(self):
        key = CacheService.build_key("notification", "unread", "42")
        assert "notification" in key
        assert "unread" in key
        assert "42" in key


# ------------------------------------------------------------------
#  Cache Integration — MedicineService
# ------------------------------------------------------------------


class TestMedicineCacheIntegration:
    def test_get_medicine_cached(self, db, admin_token):
        from app.services.medicine_service import MedicineService
        from app.schemas.medicine import MedicineCreate

        med = MedicineService.create_medicine(
            db,
            MedicineCreate(
                generic_name="TestMed",
                brand_name="TestMedBrand",
                strength="10mg",
                dosage_form="Tablet",
                route="Oral",
            ),
        )

        key = CacheService.build_key("medicine", "item", str(med.id))
        cached_after_create = CacheService.get(key)
        assert cached_after_create is None

        result = MedicineService.get_medicine(db, med.id)
        assert result is not None
        cached = CacheService.get(key)
        assert cached is not None

    def test_medicine_cache_invalidated_on_create(self, db, admin_token):
        from app.services.medicine_service import MedicineService
        from app.schemas.medicine import MedicineCreate

        stale_key = CacheService.build_key(CacheService.NAMESPACE_MEDICINE, "list", "0", "100")
        CacheService.set(stale_key, "stale")
        MedicineService.create_medicine(
            db,
            MedicineCreate(
                generic_name="NewMed",
                brand_name="NewMedBrand",
                strength="20mg",
                dosage_form="Capsule",
                route="Oral",
            ),
        )
        assert CacheService.get(stale_key) is None

    def test_medicine_cache_invalidated_on_delete(self, db, admin_token):
        from app.services.medicine_service import MedicineService
        from app.schemas.medicine import MedicineCreate

        med = MedicineService.create_medicine(
            db,
            MedicineCreate(
                generic_name="DelMed",
                brand_name="DelMedBrand",
                strength="5mg",
                dosage_form="Tablet",
                route="Oral",
            ),
        )

        stale_key = CacheService.build_key(CacheService.NAMESPACE_MEDICINE, "list", "0", "100")
        CacheService.set(stale_key, "stale")
        MedicineService.delete_medicine(db, med.id)
        assert CacheService.get(stale_key) is None

    def test_search_medicines_cached(self, db, admin_token):
        from app.services.medicine_service import MedicineService
        from app.schemas.medicine import MedicineCreate

        MedicineService.create_medicine(
            db,
            MedicineCreate(
                generic_name="Searchable",
                brand_name="SearchableBrand",
                strength="10mg",
                dosage_form="Tablet",
                route="Oral",
            ),
        )

        results = MedicineService.search_medicines(db, "Searchable", 0, 10)
        assert len(results) >= 1

        key = CacheService.build_key("medicine", "search", "Searchable", "0", "10")
        cached = CacheService.get(key)
        assert cached is not None


# ------------------------------------------------------------------
#  CacheService — TTL and Eviction Edge Cases
# ------------------------------------------------------------------


class TestTTLEdgeCases:
    def test_zero_ttl_expires_immediately(self, monkeypatch):
        provider = get_cache_provider()
        provider.set("zero", "val", ttl=0)
        import time
        time.sleep(0.01)
        assert provider.get("zero") is None

    def test_negative_ttl_expires_immediately(self):
        provider = get_cache_provider()
        provider.set("neg", "val", ttl=-1)
        assert provider.get("neg") is None

    def test_ttl_default_is_medium(self):
        provider = get_cache_provider()
        provider.set("default", "val")
        key = list(provider._store.keys())[0]
        entry = provider._store[key]
        assert entry.ttl == TTL.MEDIUM

    def test_large_ttl(self):
        provider = get_cache_provider()
        provider.set("large", "val", ttl=TTL.WEEK)
        assert provider.get("large") == "val"

    def test_overwrite_existing_key(self):
        provider = get_cache_provider()
        provider.set("k", "old")
        provider.set("k", "new")
        assert provider.get("k") == "new"

    def test_clear_empty_cache(self):
        provider = get_cache_provider()
        assert provider.clear() == 0
        assert provider.clear("nonexistent:*") == 0


# ------------------------------------------------------------------
#  CacheService — Performance Benchmarks
# ------------------------------------------------------------------


class TestCacheBenchmarks:
    def test_set_and_get_1000_items(self):
        provider = get_cache_provider()
        for i in range(1000):
            provider.set(f"bench:{i}", {"id": i, "data": "x" * 100})
        assert provider.exists("bench:999")
        stats = provider.get_stats()
        assert stats.size == 1000

    def test_cache_hit_returns_fast(self):
        provider = get_cache_provider()
        provider.set("fast", "value")
        for _ in range(1000):
            val = provider.get("fast")
            assert val == "value"

    def test_clear_pattern_on_empty(self):
        provider = get_cache_provider()
        count = provider.clear("no_match:*")
        assert count == 0
