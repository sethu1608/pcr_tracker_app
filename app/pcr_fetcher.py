# pcr_fetcher.py
import time
from datetime import datetime
from dhan_api import get_option_chain, get_expiry_list
from db import insert_pcr
from config import SYMBOL_MAP
import json

EXPIRY_LIMIT = {
    "NSE_EQ_NIFTY": 4,
    "NSE_EQ_BANKNIFTY": 2,
    "BSE_EQ_SENSEX": 4
}

def calculate_pcr(ce_oi, pe_oi):
    try:
        if ce_oi is None or pe_oi is None or ce_oi == 0:
            return 0
        return round(pe_oi / ce_oi, 2)
    except Exception as e:
        print(f"❌ PCR Calculation error: {e}")
        return 0

def fetch_and_store():
    ist_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for symbol, info in SYMBOL_MAP.items():
        expiries = get_expiry_list(info["id"], info["segment"])
        if not expiries:
            print(f"❌ No expiries found for {symbol}")
            continue

        limit = EXPIRY_LIMIT.get(symbol, 2)
        for expiry in expiries[:limit]:
            print(f"\n🔍 {symbol} | Expiry: {expiry}")
            try:
                option_chain = get_option_chain(info["id"], info["segment"], expiry)
                data = option_chain.get('data', {}).get('data', {})
                oc_data = data.get('oc', {})

                if not oc_data:
                    raise ValueError("Missing 'oc' in option chain response")

                strike_prices = sorted([float(k) for k in oc_data.keys() if k.replace('.', '', 1).isdigit()])
                strike_map = {float(k): v for k, v in oc_data.items() if k.replace('.', '', 1).isdigit()}

                if not strike_prices:
                    raise ValueError("No valid strike prices")

                # Determine ATM
                underlying_value_raw = data.get('underlyingValue')
                try:
                    underlying_value = float(underlying_value_raw)
                    atm_strike = min(strike_prices, key=lambda x: abs(x - underlying_value))
                except Exception:
                    def total_oi(s): return s.get('ce', {}).get('oi', 0) + s.get('pe', {}).get('oi', 0)
                    atm_strike = max(strike_map.items(), key=lambda item: total_oi(item[1]))[0]

                atm_index = strike_prices.index(atm_strike)
                selected_strikes = strike_prices[max(0, atm_index - 5): atm_index + 6]
                print(f"🎯 ATM: {atm_strike} | Selected strikes: {selected_strikes}")

                for strike in selected_strikes:
                    oi_data = strike_map.get(strike, {})
                    ce_oi = oi_data.get("ce", {}).get("oi", 0)
                    pe_oi = oi_data.get("pe", {}).get("oi", 0)
                    pcr = calculate_pcr(ce_oi, pe_oi)

                    insert_pcr(symbol, expiry, strike, pcr, ist_now)
                    print(f"🟢 {symbol} | {expiry} | {strike} | PCR: {pcr}")

                time.sleep(1.5)  # delay to avoid rate-limit

            except Exception as e:
                print(f"❌ Error for {symbol} {expiry}: {e}")
                with open(f"{symbol}_{expiry}_error.json", "w") as f:
                    json.dump(option_chain, f, indent=2)

if __name__ == "__main__":
    while True:
        fetch_and_store()
        print("⏳ Waiting 3 minutes before next run...")
        time.sleep(180)
