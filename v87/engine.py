import time, sqlite3, datetime
import pandas as pd
from modules.feed import fetch_real_markets

TOTAL_CAPITAL = 700000
STAKE_PER_TRADE = 25000

MAX_OPEN_TRADES = 27
BASE_MAX_PER_STRATEGY = 7
MAX_DRAWDOWN = -20000

EARLY_TP = 2
RUNNER_TP = 5

MIN_MOVE = 0.005
MIN_VOLUME = 50000

# 🔥 ADD THESE PARAMS AT TOP
LOCK_PROFIT = 3       # secure profit
TRAIL_TIGHT = 0.99    # tighter trailing (1%)
PANIC_DROP = 2        # if profit falls by 2% → exit

STRATEGIES = ["Contrarian","Breakout"]

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

    cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                         equity REAL,
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

def get_strategy_limits(cur):

    df = pd.read_sql("""
                     SELECT strategy, pnl_value
                     FROM trades
                     WHERE status='CLOSED' AND is_outlier=0
                     """, cur.connection)

    if len(df) == 0:
        return {s: BASE_MAX_PER_STRATEGY for s in STRATEGIES}

    summary = df.groupby("strategy")["pnl_value"].agg(["sum","count"]).reset_index()

    limits = {}

    for _, r in summary.iterrows():
        strat = r["strategy"]
        pnl = r["sum"]
        trades = r["count"]

        score = pnl / (trades + 1)

        if score > 1000:
            limits[strat] = 10
        elif score > 0:
            limits[strat] = 7
        elif score > -500:
            limits[strat] = 5
        else:
            limits[strat] = 3

    for s in STRATEGIES:
        if s not in limits:
            limits[s] = BASE_MAX_PER_STRATEGY

    return limits

# 🔥 SAFE TIME PARSER (NEW)
def parse_time(open_time):
    try:
        if isinstance(open_time, str):
            return datetime.datetime.fromisoformat(open_time)
        elif isinstance(open_time, datetime.datetime):
            return open_time
        else:
            return datetime.datetime.now()
    except:
        return datetime.datetime.now()

# ---------------- START ----------------
init_db()
print("V8.7.2 Strategy Allocator SAFE started")

last_prices = {}

while True:

    raw_df = fetch_real_markets()
    df = clean_df(raw_df)

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    strat_limits = get_strategy_limits(cur)
    print("Strategy Limits:", strat_limits)

    total_open = cur.execute(
        "select count(*) from trades where status='OPEN'"
    ).fetchone()[0]

    new_entries = 0

    # ---------------- ENTRY ----------------
    for _, r in df.iterrows():

        if total_open >= MAX_OPEN_TRADES:
            break

        market = r["market"]
        price = float(r["yes_price"])
        volume = float(r.get("volume", 0))

        if price < 0.02 or price > 0.98:
            continue

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

        if price < 0.2:
            strat = "Contrarian"
        elif price > 0.8:
            strat = "Breakout"
        else:
            continue

        strat_count = cur.execute(
            "select count(*) from trades where strategy=? and status='OPEN'",
            (strat,)
        ).fetchone()[0]

        if strat_count >= strat_limits.get(strat, BASE_MAX_PER_STRATEGY):
            continue

        cur.execute(
            """insert into trades(strategy,market,side,entry,current,pnl_pct,pnl_value,stake,max_price,min_price,open_time,status)
               values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (strat, market, "BUY YES", price, price, 0, 0,
             STAKE_PER_TRADE, price, price,
             str(datetime.datetime.now()), "OPEN")
        )

        total_open += 1
        new_entries += 1

    print("New trades added:", new_entries)

    # ---------------- UPDATE ----------------
    rows = cur.execute(
        "select id,market,entry,stake,max_price,min_price,open_time from trades where status='OPEN'"
    ).fetchall()

    for tid, market, entry, stake, max_p, min_p, open_time in rows:

        sub = df[df["market"] == market]
        if len(sub) == 0:
            continue

        price = float(sub.iloc[0]["yes_price"])
        last_prices[market] = price

        if max_p is None: max_p = entry
        if min_p is None: min_p = entry

        max_p = max(max_p, price)
        min_p = min(min_p, price)

        pnl_pct = ((price-entry)/entry)*100
        pnl_val = stake * pnl_pct / 100

        cur.execute(
            "update trades set current=?, pnl_pct=?, pnl_value=?, max_price=?, min_price=? where id=?",
            (price, round(pnl_pct,2), round(pnl_val,2), max_p, min_p, tid)
        )

        # ---------------- EXIT LOGIC ----------------

        # STOP LOSS
        if pnl_pct <= -3:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue

        # 🔥 PROFIT LOCK
        if pnl_pct >= LOCK_PROFIT:
            if price < max_p * 0.995:   # slight pullback
                cur.execute("update trades set status='CLOSED' where id=?", (tid,))
                continue

        # 🔥 TIGHT TRAILING (BIG WINNERS)
        if pnl_pct >= 5:
            trail = max_p * TRAIL_TIGHT
            if price < trail:
                cur.execute("update trades set status='CLOSED' where id=?", (tid,))
                continue

        # 🔥 PANIC EXIT (profit erosion)
        if max_p > entry:
            drop = ((max_p - price) / max_p) * 100
            if drop > PANIC_DROP:
                cur.execute("update trades set status='CLOSED' where id=?", (tid,))
                continue

        # TIME EXIT
        open_dt = parse_time(open_time)
        if (datetime.datetime.now() - open_dt).total_seconds() > 480:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue
    # ---------------- EQUITY ----------------
    total_pnl = cur.execute(
        "select ifnull(sum(pnl_value),0) from trades where is_outlier=0"
    ).fetchone()[0]

    equity = TOTAL_CAPITAL + total_pnl

    cur.execute("insert into portfolio(equity) values(?)", (equity,))
    print("Equity:", round(equity,2))

    con.commit()
    con.close()

    time.sleep(60)