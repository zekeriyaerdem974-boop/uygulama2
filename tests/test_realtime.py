import json

from bullwatch_unified.realtime import cache_get, cache_set


def test_cache_set_and_get():
    cache_set("rt_price_TESTUSDT", 123.45)
    cache_set("rt_change_TESTUSDT", 1.23)
    cache_set("rt_vol_TESTUSDT", 9876.0)

    assert cache_get("rt_price_TESTUSDT") == 123.45
    assert cache_get("rt_change_TESTUSDT") == 1.23
    assert cache_get("rt_vol_TESTUSDT") == 9876.0
    assert cache_get("nonexistent_key") is None
