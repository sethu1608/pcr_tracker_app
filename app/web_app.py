# web_app.py
from flask import Flask, render_template, request, jsonify
from dhan_api import get_expiry_list as dhan_expiry_list, get_option_chain
from db import get_pcr_data, get_connection

app = Flask(__name__)

SYMBOL_MAP = {
    "NSE_EQ_NIFTY": {"id": 13, "segment": "IDX_I"},
    "NSE_EQ_BANKNIFTY": {"id": 25, "segment": "IDX_I"}
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_expiry_list")
def get_expiry_list():
    symbol = request.args.get("symbol")
    if symbol not in SYMBOL_MAP:
        return jsonify([])
    info = SYMBOL_MAP[symbol]
    expiry_list = dhan_expiry_list(info["id"], info["segment"])
    return jsonify(expiry_list)

def get_strikes(option_chain_response):
    try:
        oc_data = option_chain_response.get('data', {}).get('data', {}).get('oc', {})
        if not oc_data:
            raise ValueError("Option chain missing")

        strike_prices = sorted([float(k) for k in oc_data.keys() if k.replace('.', '', 1).isdigit()])
        strike_map = {float(k): v for k, v in oc_data.items() if k.replace('.', '', 1).isdigit()}

        def total_oi(d): return d.get('ce', {}).get('oi', 0) + d.get('pe', {}).get('oi', 0)
        atm_strike = max(strike_map.items(), key=lambda item: total_oi(item[1]))[0]

        atm_index = strike_prices.index(atm_strike)
        lower = strike_prices[max(0, atm_index - 5):atm_index]
        upper = strike_prices[atm_index + 1:atm_index + 6]

        return lower + [atm_strike] + upper
    except Exception as e:
        print(f"❌ Error in get_strikes(): {e}")
        return []

@app.route("/get_strikes")
def get_strikes_route():
    symbol = request.args.get("symbol")
    expiry = request.args.get("expiry")

    if symbol not in SYMBOL_MAP or not expiry:
        return jsonify({"strikes": []}), 400

    info = SYMBOL_MAP[symbol]
    try:
        option_chain = get_option_chain(info["id"], info["segment"], expiry)
        oc_data = option_chain.get('data', {}).get('data', {}).get('oc', {})
        if not oc_data:
            raise ValueError("Option chain missing")

        strike_prices = sorted([float(k) for k in oc_data.keys() if k.replace('.', '', 1).isdigit()])
        strike_map = {float(k): v for k, v in oc_data.items() if k.replace('.', '', 1).isdigit()}

        def total_oi(d): return d.get('ce', {}).get('oi', 0) + d.get('pe', {}).get('oi', 0)
        atm_strike = max(strike_map.items(), key=lambda item: total_oi(item[1]))[0]

        atm_index = strike_prices.index(atm_strike)

        # ✅ Pick 2 below + ATM + 2 above
        lower = strike_prices[max(0, atm_index - 2):atm_index]
        upper = strike_prices[atm_index + 1:atm_index + 3]
        strikes = lower + [atm_strike] + upper

        return jsonify({"strikes": strikes})
    except Exception as e:
        print(f"❌ Error in /get_strikes: {e}")
        return jsonify({"strikes": []}), 500

@app.route("/get_pcr_data")
def get_pcr_data_route():
    symbol = request.args.get("symbol")
    expiry = request.args.get("expiry")
    timeframe = request.args.get("timeframe", "3m")
    data = get_pcr_data(symbol, expiry, timeframe)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
