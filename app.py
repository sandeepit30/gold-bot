from flask import Flask, request, jsonify
import requests, hashlib, hmac, time, json, os

app = Flask(__name__)

API_KEY    = os.environ.get("DELTA_API_KEY", "")
API_SECRET = os.environ.get("DELTA_API_SECRET", "")
BASE_URL   = "https://api.india.delta.exchange"
SYMBOL     = "XAUUSD"  # Gold futures
SIZE       = 1          # Lot size — shuruaat mein 1 rakhna

position = {"side": None}

def sign(method, path, payload=""):
    ts  = str(int(time.time()))
    msg = method + ts + path + payload
    sig = hmac.new(API_SECRET.encode(),
                   msg.encode(), hashlib.sha256).hexdigest()
    return ts, sig

def order(side):
    path    = "/v2/orders"
    body    = json.dumps({"product_symbol": SYMBOL,
                          "size": SIZE, "side": side,
                          "order_type": "market_order"})
    ts, sig = sign("POST", path, body)
    headers = {"api-key": API_KEY, "timestamp": ts,
               "signature": sig, "Content-Type": "application/json"}
    r = requests.post(BASE_URL + path, headers=headers, data=body)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data     = request.get_json()
    new_side = data.get("side")          # "buy" ya "sell"
    print(f"Signal aaya: {new_side}")

    if position["side"] and position["side"] != new_side:
        close_side = "sell" if position["side"] == "buy" else "buy"
        print(f"Purani position band ho rahi hai: {close_side}")
        order(close_side)

    result = order(new_side)
    position["side"] = new_side
    print(f"Naya order: {result}")
    return jsonify({"status": "ok"})

@app.route("/status")
def status():
    return jsonify(position)

if __name__ == "__main__":
    app.run(port=5000)
