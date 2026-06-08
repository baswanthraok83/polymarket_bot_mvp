import requests
import sqlite3
import time
import json
import random
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
SCAN_INTERVAL = 30
MAX_OPEN_TRADES = 30
MAX_PER_STRATEGY = 7
STAKE_PER_TRADE = 10000

TP_PCT = 2.0
SL_PCT = -1.2
MAX_DURATION_MIN = 180

# =========================
# DB
# =========================
con = sqlite3.connect("trades.db", check_same_thread=False)
cur = con.cursor()

# =========================
# FETCH MARKETS
# =========================
def fetch_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=200"
        data = requests.get(url, timeout=5).json()

        markets = []

        for m in data:
            try:
                q = m.get("question")
                raw_ids = m.get("clobTokenIds")
                price_data = m.get("outcomePrices")
                end_date = m.get("endDate")

                if not q or not raw_ids or not price_data or not end_date:
                    continue

                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)

                hours_left = (end - now).total_seconds() / 3600
                if hours_left > 168:
                    continue

                token_ids = json.loads(raw_ids)
                prices = json.loads(price_data)

                if not token_ids or not prices:
                    continue

                price = float(prices[0])
                token_id = token_ids[0]

                if price < 0.03 or price > 0.97:
                    continue

                prev_price = m.get("lastTradePrice")
                if prev_price:
                    prev_price = float(prev_price)
                else:
                    prev_price = price

                momentum = price - prev_price

                markets.append({
                    "market": q,
                    "token_id": token_id,
                    "price": price,
                    "momentum": momentum
                })

            except:
                continue

        print(f"DEBUG: usable markets={len(markets)}")
        return markets[:60]

    except Exception as e:
        print("Market fetch error:", e)
        return []

# =========================
# STRATEGIES
# =========================
def contrarian_strategy(markets):
    signals = []
    for m in markets:
        p = m["price"]
        mom = m["momentum"]

        if 0.10 <= p <= 0.25 and mom >= -0.002:
            signals.append(m | {"strategy": "Contrarian", "side": "BUY YES"})

        if 0.75 <= p <= 0.90 and mom <= 0.002:
            signals.append(m | {"strategy": "Contrarian", "side": "BUY NO"})
    return signals


def breakout_strategy(markets):
    signals = []
    for m in markets:
        p = m["price"]
        mom = m["momentum"]

        if p > 0.60 and mom >= -0.001:
            signals.append(m | {"strategy": "Breakout", "side": "BUY YES"})

        if p < 0.40 and mom <= 0.001:
            signals.append(m | {"strategy": "Breakout", "side": "BUY NO"})
    return signals


def ai_strategy(markets):
    signals = []
    for m in markets:
        p = m["price"]

        if 0.30 <= p <= 0.70:
            side = random.choice(["BUY YES", "BUY NO"])
            signals.append(m | {"strategy": "AI", "side": side})
    return signals

# =========================
# ENTRY
# =========================
def enter_trade(s):
    cur.execute("""
                INSERT INTO trades(strategy, market, token_id, side, entry, current, pnl_pct, pnl_value, stake, status, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (
                    s["strategy"],
                    s["market"],
                    s["token_id"],
                    s["side"],
                    s["price"],
                    s["price"],
                    0,
                    0,
                    STAKE_PER_TRADE,
                    datetime.now(timezone.utc).isoformat()
                ))
    con.commit()

    print(f"🟢 ENTER: [{s['strategy']}] {s['side']} {s['market']} @ {s['price']}")

# =========================
# UPDATE PRICES
# =========================
def update_trades():
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=200"
        data = requests.get(url, timeout=5).json()

        token_price_map = {}

        for m in data:
            raw_ids = m.get("clobTokenIds")
            price_data = m.get("outcomePrices")

            if not raw_ids or not price_data:
                continue

            token_ids = json.loads(raw_ids)
            prices = json.loads(price_data)

            if token_ids and prices:
                token_price_map[token_ids[0]] = float(prices[0])

        rows = cur.execute(
            "SELECT id, entry, stake, token_id, current FROM trades WHERE status='OPEN'"
        ).fetchall()

        for tid, entry, stake, token_id, current in rows:
            new_price = token_price_map.get(token_id)

            print(f"[PRICE CHECK] {token_id} → {new_price}")

            if new_price is None:
                continue

            if current is not None and abs(new_price - current) < 1e-6:
                continue

            pnl_pct = ((new_price - entry) / entry) * 100
            pnl_val = (pnl_pct / 100) * stake

            cur.execute("""
                        UPDATE trades
                        SET current=?, pnl_pct=?, pnl_value=?
                        WHERE id=?
                        """, (new_price, pnl_pct, pnl_val, tid))

        con.commit()

    except Exception as e:
        print("UPDATE ERROR:", e)

# =========================
# EXIT LOGIC
# =========================
def check_exit():
    rows = cur.execute(
        "SELECT id, pnl_pct, ts FROM trades WHERE status='OPEN'"
    ).fetchall()

    now = datetime.now(timezone.utc)

    for tid, pnl_pct, ts in rows:
        entry_time = datetime.fromisoformat(ts)
        duration = (now - entry_time).total_seconds() / 60

        if pnl_pct >= TP_PCT or pnl_pct <= SL_PCT:
            cur.execute("UPDATE trades SET status='CLOSED' WHERE id=?", (tid,))
            print(f"🔴 EXIT {tid} pnl={round(pnl_pct,2)}%")
            continue

        if duration > MAX_DURATION_MIN:
            cur.execute("UPDATE trades SET status='CLOSED' WHERE id=?", (tid,))
            print(f"⏱️ TIME EXIT {tid}")

    con.commit()

# =========================
# MAIN LOOP
# =========================
def run():
    print("🚀 V13 Engine started (No Duplicate Trades)")

    while True:
        markets = fetch_markets()

        signals = []
        signals += breakout_strategy(markets)
        signals += ai_strategy(markets)
        signals += contrarian_strategy(markets)

        random.shuffle(signals)

        print(f"\n🔄 Markets: {len(markets)} | Signals: {len(signals)}")

        open_rows = cur.execute(
            "SELECT market, side, strategy FROM trades WHERE status='OPEN'"
        ).fetchall()

        market_count = {}
        market_side_map = {}
        strategy_count = {}

        for m, side, strat in open_rows:
            key = m.lower()

            market_count[key] = market_count.get(key, 0) + 1

            if key not in market_side_map:
                market_side_map[key] = set()
            market_side_map[key].add(side)

            strategy_count[strat] = strategy_count.get(strat, 0) + 1

        open_count = len(open_rows)

        for s in signals:
            if open_count >= MAX_OPEN_TRADES:
                break

            key = s["market"].lower()
            side = s["side"]
            strat = s["strategy"]

            if market_count.get(key, 0) >= 2:
                continue

            if side in market_side_map.get(key, set()):
                continue

            if strategy_count.get(strat, 0) >= MAX_PER_STRATEGY:
                continue

            enter_trade(s)

            open_count += 1
            market_count[key] = market_count.get(key, 0) + 1

            if key not in market_side_map:
                market_side_map[key] = set()
            market_side_map[key].add(side)

            strategy_count[strat] = strategy_count.get(strat, 0) + 1

        update_trades()
        check_exit()

        stats = cur.execute(
            "SELECT COUNT(*), SUM(pnl_value) FROM trades WHERE status='OPEN'"
        ).fetchone()

        print(f"📊 Open={stats[0]} | PnL={round(stats[1] or 0,2)}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    run()