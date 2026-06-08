import time, sqlite3, datetime
import pandas as pd
from modules.feed import fetch_real_markets

# =========================
# 🔴 LIVE SWITCH
# =========================
LIVE_MODE = False   # 🔥 flip to True ONLY when ready

# =========================
# CAPITAL & RISK
# =========================
TOTAL_CAPITAL = 700000
BASE_STAKE = 25000
MAX_OPEN_TRADES = 27
MAX_CAPITAL_IN_USE = 500000   # 🔥 do not deploy all capital
MAX_PER_TRADE = 60000         # 🔥 hard cap per trade
MIN_VOLUME = 50000
MIN_MOVE = 0.005

EARLY_TP = 2
SL_PCT = -3

# 🔥 Circuit breaker
DAILY_LOSS_LIMIT = -20000     # stop trading for the day

# =========================
# BROKER LAYER
# =========================
class PaperBroker:
    def place_order(self, market, side, price, stake):
        print(f"[PAPER] {side} {market} @ {price} stake={stake}")
        return True

    def close_order(self, trade_id):
        print(f"[PAPER] CLOSE trade {trade_id}")
        return True


class LiveBroker:
    def place_order(self, market, side, price, stake):
        # 🔥 TODO: integrate real API here
        print(f"[LIVE] {side} {market} @ {price} stake={stake}")
        return True

    def close_order(self, trade_id):
        # 🔥 TODO: integrate real API here
        print(f"[LIVE] CLOSE trade {trade_id}")
        return True


broker = LiveBroker() if LIVE_MODE else PaperBroker()

# =========================
# DB INIT
# =========================
def init_db():
    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                                                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                      strategy TEXT,
                                                      market TEXT,
                                                      side TEXT,
                                                      entry REAL,
                                                      current REAL,
                                                      pnl_pct REAL,
                                                      pnl_value REAL,
                                                      stake REAL,
                                                      max_price REAL,
                                                      min_price REAL,
                                                      open_time TEXT,
                                                      is_outlier INTEGER DEFAULT 0,
                                                      status TEXT,
                                                      ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

    con.commit()
    con.close()

# =========================
# HELPERS
# =========================
def clean_df(df):
    df = df.copy()
    df = df[(df["yes_price"] > 0) & (df["yes_price"] < 1)]
    df["yes_price"] = df["yes_price"].clip(0.01, 0.99)
    return df

def parse_time(t):
    try:
        return datetime.datetime.fromisoformat(t)
    except:
        return datetime.datetime.now()

# 🔥 Position sizing (same logic)
def get_position_size(cur):
    df = pd.read_sql("""
                     SELECT pnl_value
                     FROM trades
                     WHERE status='CLOSED' AND (is_outlier=0 OR is_outlier IS NULL)
                     ORDER BY id DESC
                         LIMIT 20
                     """, cur.connection)

    if len(df) < 10:
        return BASE_STAKE

    wins = df[df["pnl_value"] > 0]
    losses = df[df["pnl_value"] < 0]

    win_rate = len(wins) / len(df)

    avg_win = wins["pnl_value"].mean() if len(wins) else 0
    avg_loss = abs(losses["pnl_value"].mean()) if len(losses) else 1

    edge = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    if edge > 5000:
        return 60000
    elif edge > 2000:
        return 40000
    elif edge > 0:
        return 25000
    else:
        return 10000

# 🔥 AI + fallback
def fallback_side(price):
    if price < 0.2 or price > 0.8:
        return "BUY YES"
    return "BUY NO"

def choose_side(cur, price):
    df = pd.read_sql("""
                     SELECT entry, side, pnl_value
                     FROM trades
                     WHERE status='CLOSED' AND (is_outlier=0 OR is_outlier IS NULL)
                     """, cur.connection)

    if len(df) < 20:
        return fallback_side(price)

    bucket = df[(df["entry"] > price-0.2) & (df["entry"] < price+0.2)]

    if len(bucket) < 5:
        return fallback_side(price)

    yes_pnl = bucket[bucket["side"]=="BUY YES"]["pnl_value"].sum()
    no_pnl  = bucket[bucket["side"]=="BUY NO"]["pnl_value"].sum()

    return "BUY YES" if yes_pnl > no_pnl else "BUY NO"

# =========================
# START
# =========================
init_db()
print(f"V9.1 Live-Ready Engine started | LIVE_MODE={LIVE_MODE}")

last_prices = {}

while True:

    df = clean_df(fetch_real_markets())

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    # -------------------------------
    # Circuit breaker
    # -------------------------------
    today = datetime.date.today().isoformat()
    daily_pnl = cur.execute("""
                            SELECT IFNULL(SUM(pnl_value),0)
                            FROM trades
                            WHERE DATE(ts)=? AND (is_outlier=0 OR is_outlier IS NULL)
                            """, (today,)).fetchone()[0]

    if daily_pnl <= DAILY_LOSS_LIMIT:
        print("🚨 Daily loss limit hit. Trading paused.")
        time.sleep(60)
        continue

    # -------------------------------
    # Capital check
    # -------------------------------
    capital_used = cur.execute("""
                               SELECT IFNULL(SUM(stake),0)
                               FROM trades
                               WHERE status='OPEN'
                               """).fetchone()[0]

    total_open = cur.execute("""
                             SELECT COUNT(*) FROM trades WHERE status='OPEN'
                             """).fetchone()[0]

    stake = min(get_position_size(cur), MAX_PER_TRADE)

    print(f"Stake={stake} | Open={total_open} | Used={capital_used}")

    # -------------------------------
    # ENTRY
    # -------------------------------
    for _, r in df.iterrows():

        if total_open >= MAX_OPEN_TRADES:
            break

        if capital_used + stake > MAX_CAPITAL_IN_USE:
            break

        market = r["market"]
        price = float(r["yes_price"])
        volume = float(r.get("volume", 0))

        if volume < MIN_VOLUME:
            continue

        last = last_prices.get(market)
        if last:
            if abs(price - last) / last < MIN_MOVE:
                continue

        exists = cur.execute("""
                             SELECT COUNT(*) FROM trades
                             WHERE market=? AND status='OPEN'
                             """, (market,)).fetchone()[0]

        if exists > 0:
            continue

        side = choose_side(cur, price)

        # 🔥 place order (paper/live)
        ok = broker.place_order(market, side, price, stake)
        if not ok:
            continue

        cur.execute("""
                    INSERT INTO trades(strategy,market,side,entry,current,pnl_pct,pnl_value,stake,max_price,min_price,open_time,status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """, ("AI", market, side, price, price, 0, 0,
                          stake, price, price,
                          str(datetime.datetime.now()), "OPEN"))

        total_open += 1
        capital_used += stake

    # -------------------------------
    # UPDATE / EXIT
    # -------------------------------
    rows = cur.execute("""
                       SELECT id,market,side,entry,stake,max_price,min_price,open_time
                       FROM trades WHERE status='OPEN'
                       """).fetchall()

    for tid, market, side, entry, stake, max_p, min_p, open_time in rows:

        sub = df[df["market"] == market]
        if len(sub) == 0:
            continue

        price = float(sub.iloc[0]["yes_price"])
        last_prices[market] = price

        max_p = max(max_p or entry, price)
        min_p = min(min_p or entry, price)

        pnl_pct = ((price - entry)/entry)*100 if side=="BUY YES" else ((entry - price)/entry)*100
        pnl_val = stake * pnl_pct / 100

        cur.execute("""
                    UPDATE trades SET current=?, pnl_pct=?, pnl_value=?, max_price=?, min_price=?
                    WHERE id=?
                    """, (price, round(pnl_pct,2), round(pnl_val,2), max_p, min_p, tid))

        # exits
        if pnl_pct <= SL_PCT or pnl_pct >= EARLY_TP:
            broker.close_order(tid)
            cur.execute("UPDATE trades SET status='CLOSED' WHERE id=?", (tid,))
            continue

        open_dt = parse_time(open_time)
        if (datetime.datetime.now() - open_dt).total_seconds() > 480:
            broker.close_order(tid)
            cur.execute("UPDATE trades SET status='CLOSED' WHERE id=?", (tid,))
            continue

    con.commit()
    con.close()

    time.sleep(60)