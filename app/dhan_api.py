# app/dhan_api.py
from dhanhq import dhanhq
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN

client = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

def get_expiry_list(underlying_id=13, segment="IDX_I"):
    try:
        response = client.expiry_list(under_security_id=underlying_id, under_exchange_segment=segment)
        if response.get("status", "").lower() == "success":
            return response.get("data", {}).get("data", [])
    except Exception as e:
        print("❌ Error getting expiry list:", e)
    return []

def get_option_chain(underlying_id, segment, expiry):
    try:
        return client.option_chain(
            under_security_id=underlying_id,
            under_exchange_segment=segment,
            expiry=expiry
        )
    except Exception as e:
        print("❌ Error getting option chain:", e)
        return None