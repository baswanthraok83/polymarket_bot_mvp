import time, sqlite3, datetime
import pandas as pd
from modules.feed import fetch_real_markets

TOTAL_CAPITAL = 700000
BASE_STAKE = 25000

MAX_OPEN_TRADES = 27
MIN_VOLUME = 50000
MIN_MOVE = 0.005

EARLY_TP = 2

# ---------------- INIT ----------------
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

# 🔥 POSITION SIZING ENGINE
def get_position_size(cur):

    df = pd.read_sql("""
                     SELECT pnl_value
                     FROM trades
                     WHERE status='CLOSED' AND is_outlier=0
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

    # 🔥 sizing logic
    if edge > 5000:
        return 60000
    elif edge > 2000:
        return 40000
    elif edge > 0:
        return 25000
    else:
        return 10000

# 🔥 AI SIDE SELECTOR (same as V8.9)
def choose_side(cur, price):

    df = pd.read_sql("""
                     SELECT entry, side, pnl_value
                     FROM trades
                     WHERE status='CLOSED' AND is_outlier=0
                     """, cur.connection)

    # 🔥 Not enough data → fallback
    if len(df) < 20:
        return fallback_side(price)

    bucket = df[(df["entry"] > price-0.2) & (df["entry"] < price+0.2)]

    # 🔥 bucket too small → fallback
    if len(bucket) < 5:
        return fallback_side(price)

    yes_pnl = bucket[bucket["side"]=="BUY YES"]["pnl_value"].sum()
    no_pnl  = bucket[bucket["side"]=="BUY NO"]["pnl_value"].sum()

    return "BUY YES" if yes_pnl > no_pnl else "BUY NO"
def fallback_side(price):

    if price < 0.2:
        return "BUY YES"
    elif price > 0.8:
        return "BUY YES"
    else:
        return "BUY NO"
# ---------------- START ----------------
init_db()
print("V9.0 Position Sizing Engine started")

last_prices = {}

while True:

    df = clean_df(fetch_real_markets())

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    total_open = cur.execute(
        "select count(*) from trades where status='OPEN'"
    ).fetchone()[0]

    # 🔥 dynamic stake
    stake = get_position_size(cur)
    print("Current stake:", stake)

    new_entries = 0

    # ---------------- ENTRY ----------------
    for _, r in df.iterrows():

        if total_open >= MAX_OPEN_TRADES:
            break

        market = r["market"]
        price = float(r["yes_price"])
        volume = float(r.get("volume", 0))

        if volume < MIN_VOLUME:
            continue

        last = last_prices.get(market)
        if last:
            move = abs(price - last) / last
            if move < MIN_MOVE:
                continue

        exists = cur.execute(
            "select count(*) from trades where market=? and status='OPEN'",
            (market,)
        ).fetchone()[0]

        if exists > 0:
            continue

        side = choose_side(cur, price)
        if side is None:
            continue

        cur.execute(
            """insert into trades(strategy,market,side,entry,current,pnl_pct,pnl_value,stake,max_price,min_price,open_time,status)
               values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("AI", market, side, price, price, 0, 0,
             stake, price, price,
             str(datetime.datetime.now()), "OPEN")
        )

        total_open += 1
        new_entries += 1

    print("New trades:", new_entries)

    # ---------------- UPDATE ----------------
    rows = cur.execute(
        "select id,market,side,entry,stake,max_price,min_price,open_time from trades where status='OPEN'"
    ).fetchall()

    for tid, market, side, entry, stake, max_p, min_p, open_time in rows:

        sub = df[df["market"] == market]
        if len(sub) == 0:
            continue

        price = float(sub.iloc[0]["yes_price"])
        last_prices[market] = price

        if max_p is None: max_p = entry
        if min_p is None: min_p = entry

        max_p = max(max_p, price)
        min_p = min(min_p, price)

        if side == "BUY YES":
            pnl_pct = ((price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - price) / entry) * 100

        pnl_val = stake * pnl_pct / 100

        cur.execute(
            "update trades set current=?, pnl_pct=?, pnl_value=?, max_price=?, min_price=? where id=?",
            (price, round(pnl_pct,2), round(pnl_val,2), max_p, min_p, tid)
        )

        # exits
        if pnl_pct <= -3:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue

        if pnl_pct >= EARLY_TP:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue

        open_dt = parse_time(open_time)
        if (datetime.datetime.now() - open_dt).total_seconds() > 480:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue

    con.commit()
    con.close()

    time.sleep(60)