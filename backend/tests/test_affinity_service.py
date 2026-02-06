"""Tests for the affinity service - tier calculation."""

from app.services.affinity_service import affinity_service


def test_affinity_tiers():
    assert affinity_service.get_tier(0) == "陌生人"
    assert affinity_service.get_tier(10) == "陌生人"
    assert affinity_service.get_tier(20) == "认识"
    assert affinity_service.get_tier(50) == "朋友"
    assert affinity_service.get_tier(60) == "好友"
    assert affinity_service.get_tier(80) == "挚友"
    assert affinity_service.get_tier(100) == "羁绊"
    assert affinity_service.get_tier(999) == "羁绊"
