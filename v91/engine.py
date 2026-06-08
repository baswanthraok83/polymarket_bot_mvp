import sqlite3
import time
import datetime
import random

# =========================
# CONFIG
# =========================
DB = "trades.db"

SCAN_INTERVAL = 15  # seconds
MAX_OPEN_TRADES = 27
MAX_PER_STRATEGY = 7

TOTAL_CAPITAL = 700000
STAKE_PER_TRADE = 25000


# =========================
# DB INIT
# =========================
con = sqlite3.connect(DB, check_same_thread=False)
cur = con.cursor()

cur.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                                                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                  strategy TEXT,
                                                  market TEXT,
                                                  token_id TEXT,
                                                  side TEXT,
                                                  entry REAL,
                                                  current REAL,
                                                  pnl_pct REAL,
                                                  pnl_value REAL,
                                                  stake REAL,
                                                  status TEXT,
                                                  ts TEXT
            )
            """)

con.commit()


# =========================
# MOCK MARKET FETCH (replace later with real API)
# =========================
def fetch_markets():
    """
    Simulates fresh markets every call
    Replace this with real Polymarket API later
    """
    base_markets = [
        "Will Bitcoin hit $100k?",
        "Will ETH flip BTC?",
        "Will Trump win 2028?",
        "Will recession happen in 2026?",
        "Will AI replace jobs?"
    ]

    markets = []
    for m in base_markets:
        markets.append({
            "market": m,
            "token_id": str(hash(m))[-6:],
            "price": round(random.uniform(0.1, 0.9), 3)
        })

    return markets


# =========================
# SIGNAL GENERATION
# =========================
def generate_signals(markets):
    signals = []

    for m in markets:
        if random.random() > 0.7:
            signals.append({
                "strategy": random.choice(["Contrarian", "Breakout"]),
                "market": m["market"],
                "token_id": m["token_id"],
                "side": "BUY YES",
                "price": m["price"]
            })

    return signals


# =========================
# CHECK LIMITS
# =========================
def can_enter(strategy):
    open_total = cur.execute(
        "SELECT COUNT(*) FROM trades WHERE status='OPEN'"
    ).fetchone()[0]

    open_strategy = cur.execute(
        "SELECT COUNT(*) FROM trades WHERE status='OPEN' AND strategy=?",
        (strategy,)
    ).fetchone()[0]

    return (
            open_total < MAX_OPEN_TRADES and
            open_strategy < MAX_PER_STRATEGY
    )


# =========================
# AVOID DUPLICATE TRADES
# =========================
def already_open(market):
    r = cur.execute(
        "SELECT COUNT(*) FROM trades WHERE market=? AND status='OPEN'",
        (market,)
    ).fetchone()[0]

    return r > 0


# =========================
# ENTER TRADE
# =========================
def enter_trade(signal):
    cur.execute("""
                INSERT INTO trades (strategy, market, token_id, side, entry, current,
                                    pnl_pct, pnl_value, stake, status, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (
                    signal["strategy"],
                    signal["market"],
                    signal["token_id"],
                    signal["side"],
                    signal["price"],
                    signal["price"],
                    0,
                    0,
                    STAKE_PER_TRADE,
                    datetime.datetime.now().isoformat()
                ))

    print(f"🟢 ENTER {signal['market']} @ {signal['price']} [{signal['strategy']}]")

    con.commit()


# =========================
# UPDATE OPEN TRADES
# =========================
def update_trades():
    rows = cur.execute(
        "SELECT id, entry, stake FROM trades WHERE status='OPEN'"
    ).fetchall()

    for r in rows:
        trade_id, entry, stake = r

        # simulate price movement
        price = round(entry * random.uniform(0.9, 1.1), 3)

        pnl_pct = ((price - entry) / entry) * 100
        pnl_value = (pnl_pct / 100) * stake

        cur.execute("""
                    UPDATE trades
                    SET current=?, pnl_pct=?, pnl_value=?
                    WHERE id=?
                    """, (price, pnl_pct, pnl_value, trade_id))

    con.commit()


# =========================
# EXIT LOGIC
# =========================
def manage_exits():
    rows = cur.execute("""
                       SELECT id, entry, current, stake, ts
                       FROM trades
                       WHERE status='OPEN'
                       """).fetchall()

    for r in rows:
        trade_id, entry, current, stake, ts = r

        # 🔥 recompute PnL (IMPORTANT FIX)
        pnl_pct = ((current - entry) / entry) * 100
        pnl_value = (pnl_pct / 100) * stake

        open_dt = datetime.datetime.fromisoformat(ts)
        age = (datetime.datetime.now() - open_dt).total_seconds()

        if pnl_pct > 20 or pnl_pct < -10 or age > 600:

            cur.execute("""
                        UPDATE trades
                        SET status='CLOSED',
                            pnl_pct=?,
                            pnl_value=?
                        WHERE id=?
                        """, (pnl_pct, pnl_value, trade_id))

            print(f"🔴 EXIT {trade_id} pnl={round(pnl_pct,2)}%")

# =========================
# DASHBOARD STATS
# =========================
def print_stats():
    open_trades = cur.execute(
        "SELECT COUNT(*) FROM trades WHERE status='OPEN'"
    ).fetchone()[0]

    closed_trades = cur.execute(
        "SELECT COUNT(*) FROM trades WHERE status='CLOSED'"
    ).fetchone()[0]

    pnl = cur.execute(
        "SELECT IFNULL(SUM(pnl_value),0) FROM trades WHERE status='CLOSED'"
    ).fetchone()[0]

    print(f"📊 Open: {open_trades} | Closed: {closed_trades} | PnL: {round(pnl,2)}")


# =========================
# MAIN LOOP
# =========================
print("🚀 V9.1 Engine started (LIVE SCANNING FIXED)")

while True:

    # 🔥 THIS IS THE FIX
    markets = fetch_markets()

    print(f"\n🔄 New scan @ {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"Markets fetched: {len(markets)}")

    signals = generate_signals(markets)

    print(f"Signals found: {len(signals)}")

    for s in signals:
        if can_enter(s["strategy"]) and not already_open(s["market"]):
            enter_trade(s)

    update_trades()
    manage_exits()
    print_stats()

    time.sleep(SCAN_INTERVAL)