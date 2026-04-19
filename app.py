import requests, hashlib, hmac, time, json, os
from datetime import datetime

API_KEY    = os.environ.get("DELTA_API_KEY", "")
API_SECRET = os.environ.get("DELTA_API_SECRET", "")
BASE_URL   = "https://api.india.delta.exchange"
SYMBOL     = "XAUUSD"
SIZE       = 1

position = {"side": None}

def sign(method, path, payload=""):
    ts  = str(int(time.time()))
    msg = method + ts + path + payload
    sig = hmac.new(API_SECRET.encode(),
                   msg.encode(), hashlib.sha256).hexdigest()
    return ts, sig

def get_candles():
    """Last 2 candles ka data lo"""
    ts = int(time.time())
    path = f"/v2/history/candles?symbol={SYMBOL}&resolution=5&start={ts-600}&end={ts}"
    r = requests.get(BASE_URL + path)
    return r.json().get("result", [])

def calculate_ema(prices, period):
    """EMA calculate karo"""
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def get_rsi(prices, period=14):
    """RSI calculate karo"""
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def place_order(side):
    path = "/v2/orders"
    body = json.dumps({"product_symbol": SYMBOL,
                       "size": SIZE, "side": side,
                       "order_type": "market_order"})
    ts, sig = sign("POST", path, body)
    headers = {"api-key": API_KEY, "timestamp": ts,
               "signature": sig,
               "Content-Type": "application/json"}
    r = requests.post(BASE_URL + path,
                      headers=headers, data=body)
    print(f"Order placed: {side} → {r.json()}")
    return r.json()

def check_signal():
    candles = get_candles()
    if len(candles) < 30:
        print("Data kam hai, wait karo...")
        return

    closes = [c["close"] for c in candles]

    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    rsi   = get_rsi(closes)

    prev_ema12 = calculate_ema(closes[:-1], 12)
    prev_ema26 = calculate_ema(closes[:-1], 26)

    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] EMA12={ema12:.2f} EMA26={ema26:.2f} RSI={rsi:.1f} | Position={position['side']}")

    # BUY Signal
    buy = prev_ema12 < prev_ema26 and ema12 > ema26 and rsi > 50
    # SELL Signal  
    sell = prev_ema12 > prev_ema26 and ema12 < ema26 and rsi < 50

    if buy and position["side"] != "buy":
        print("🟢 BUY SIGNAL!")
        if position["side"] == "sell":
            place_order("buy")   # purana sell band karo
        place_order("buy")
        position["side"] = "buy"

    elif sell and position["side"] != "sell":
        print("🔴 SELL SIGNAL!")
        if position["side"] == "buy":
            place_order("sell")  # purana buy band karo
        place_order("sell")
        position["side"] = "sell"

# Main loop — har 5 minute mein check karo
print("Bot shuru ho gaya! Har 5 min mein signal check hoga...")
while True:
    try:
        check_signal()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)  # 5 minute wait
