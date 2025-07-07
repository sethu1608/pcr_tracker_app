import time
from datetime import datetime
from app.dhan_api import get_option_chain, get_expiry_list
from app.db import insert_pcr
from app.config import SYMBOL_MAP
import json

def calculate_pcr(ce_oi, pe_oi):
    try:
        if ce_oi is None or pe_oi is None or ce_oi == 0:
            return 0
        return round(pe_oi / ce_oi, 2)
    except Exception as e:
        print(f"❌ PCR Calculation error: {e}")
        return 0

def fetch_and_store():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for symbol, info in SYMBOL_MAP.items():
        print(f"\n📌 Fetching expiry list for {symbol}")
        expiries = get_expiry_list(info["id"], info["segment"])
        if not expiries:
            print(f"❌ No expiries found for {symbol}")
            continue

        latest_expiry = expiries[0]
        print(f"✅ Using expiry: {latest_expiry}")

        print(f"📦 Fetching option chain for {symbol}")
        option_chain = get_option_chain(info["id"], info["segment"], latest_expiry)

        try:
            data = option_chain.get('data', {}).get('data', {})
            oc_data = data.get('oc', {})

            if not oc_data:
                raise ValueError("Missing 'oc' in option chain response")

            # Parse valid strike prices
            strike_prices = []
            strike_map = {}
            for k, v in oc_data.items():
                try:
                    strike = float(k)
                    strike_prices.append(strike)
                    strike_map[strike] = v
                except (ValueError, TypeError):
                    continue

            if not strike_prices:
                raise ValueError("No valid strike prices found")

            strike_prices.sort()

            # Try to use underlyingValue as ATM
            underlying_value_raw = data.get('underlyingValue')
            try:
                underlying_value = float(underlying_value_raw)
                atm_strike = min(strike_prices, key=lambda x: abs(x - underlying_value))
                print(f"🎯 ATM based on underlyingValue: {underlying_value}")
            except (TypeError, ValueError):
                print("⚠️ No valid underlyingValue found, falling back to max OI ATM")
                def total_oi(s):
                    return s.get('ce', {}).get('oi', 0) + s.get('pe', {}).get('oi', 0)
                atm_strike = max(strike_map.items(), key=lambda item: total_oi(item[1]))[0]

            atm_index = strike_prices.index(atm_strike)
            selected_strikes = strike_prices[max(0, atm_index - 5): atm_index + 6]

            print(f"🎯 Selected strikes: {selected_strikes}")

            for strike in selected_strikes:
                oi_data = strike_map.get(strike, {})
                ce_oi = oi_data.get("ce", {}).get("oi", 0)
                pe_oi = oi_data.get("pe", {}).get("oi", 0)

                pcr = calculate_pcr(ce_oi, pe_oi)
                insert_pcr(symbol, latest_expiry, strike, pcr, now)
                print(f"🟢 {symbol} | {strike} | CE OI: {ce_oi} | PE OI: {pe_oi} | PCR: {pcr}")

        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            with open(f"{symbol}_raw_response.json", "w") as f:
                json.dump(option_chain, f, indent=2)

if __name__ == "__main__":
    while True:
        fetch_and_store()
        print("⏳ Waiting 3 minutes before next run...")
        time.sleep(180)
