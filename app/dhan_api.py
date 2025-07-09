# app/dhan_api.py
import time
from dhanhq import dhanhq
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN

client = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

# --------- Expiry Caching ---------
_expiry_cache = {}
_expiry_cache_time = {}

EXPIRY_LIMIT = {
    13: 4,   # NIFTY
    25: 2    # BANKNIFTY
}

def get_expiry_list(underlying_id=13, segment="IDX_I"):
    key = f"{underlying_id}_{segment}"
    now = time.time()

    if key in _expiry_cache and (now - _expiry_cache_time.get(key, 0) < 3600):
        print(f"⚡ [Cache] Expiry list for {key}")
        return _expiry_cache[key]

    try:
        print(f"📦 [API] Fetching expiry list for {key}")
        response = client.expiry_list(under_security_id=underlying_id, under_exchange_segment=segment)
        if response.get("status", "").lower() == "success":
            expiries = response.get("data", {}).get("data", [])
            limit = EXPIRY_LIMIT.get(underlying_id, 2)
            _expiry_cache[key] = expiries[:limit]
            _expiry_cache_time[key] = now
            return _expiry_cache[key]
    except Exception as e:
        print("❌ Error getting expiry list:", e)

    return _expiry_cache.get(key, [])

# --------- Option Chain Caching ---------
_option_chain_cache = {}
_option_chain_time = {}
OPTION_CHAIN_TTL = 30  # seconds

def get_option_chain(underlying_id, segment, expiry):
    key = f"{underlying_id}_{segment}_{expiry}"
    now = time.time()

    if key in _option_chain_cache and (now - _option_chain_time.get(key, 0) < OPTION_CHAIN_TTL):
        print(f"⚡ [Cache] Option chain for {key}")
        return _option_chain_cache[key]

    try:
        print(f"📦 [API] Fetching option chain for {key}")
        response = client.option_chain(
            under_security_id=underlying_id,
            under_exchange_segment=segment,
            expiry=expiry
        )
        _option_chain_cache[key] = response
        _option_chain_time[key] = now
        return response
    except Exception as e:
        print(f"❌ Error getting option chain for {key}: {e}")
        return _option_chain_cache.get(key)
