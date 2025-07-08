# web_app.py
from flask import Flask, render_template, request, jsonify
from dhan_api import get_expiry_list as dhan_expiry_list, get_option_chain
from db import get_connection, get_pcr_data

app = Flask(__name__)

# Symbol mapping
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
    """
    Returns 5 strikes above and 5 below the ATM based on max OI (fallback if underlyingValue not provided).
    """
    try:
        oc_data = option_chain_response.get('data', {}).get('data', {}).get('oc', {})
        if not oc_data:
            raise ValueError("Option chain data missing")

        strike_prices = sorted([float(strike) for strike in oc_data.keys()])
        strike_map = {float(k): v for k, v in oc_data.items()}

        # Fallback logic: choose ATM by highest CE/PE OI
        def get_total_oi(data):
            return data.get('ce', {}).get('oi', 0) + data.get('pe', {}).get('oi', 0)

        atm_strike = max(strike_map.items(), key=lambda item: get_total_oi(item[1]))[0]

        atm_index = strike_prices.index(atm_strike)
        lower = strike_prices[max(atm_index - 5, 0):atm_index]
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
        option_chain_response = get_option_chain(info["id"], info["segment"], expiry)
        # print("🔍 Option Chain Response:", option_chain_response)  # Debug line
        strikes = get_strikes(option_chain_response)
        return jsonify({"strikes": strikes})
    except Exception as e:
        print(f"Error in /get_strikes: {e}")
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
