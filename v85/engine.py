import time, sqlite3, datetime
import pandas as pd
from modules.feed import fetch_real_markets

TOTAL_CAPITAL = 700000
STAKE_PER_TRADE = 25000

MAX_OPEN_TRADES = 27
MAX_PER_STRATEGY = 7
MAX_DRAWDOWN = -20000

MAX_JUMP = 0.5
MAX_PNL_CAP = 200

EARLY_TP = 2        # 🔥 profit booking
RUNNER_TP = 5       # let winners run

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

init_db()
print("V8.6.4 Smart Exit Engine started")

last_prices = {}

while True:

    raw_df = fetch_real_markets()
    df = clean_df(raw_df)

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    total_pnl = cur.execute(
        "select ifnull(sum(pnl_value),0) from trades"
    ).fetchone()[0]

    if total_pnl < MAX_DRAWDOWN:
        print("⚠ Drawdown hit. Pausing")
        time.sleep(60)
        continue

    total_open = cur.execute(
        "select count(*) from trades where status='OPEN'"
    ).fetchone()[0]

    # ---------------- ENTRY ----------------
    for _, r in df.iterrows():

        if total_open >= MAX_OPEN_TRADES:
            break

        market = r["market"]
        price = float(r["yes_price"])
        volume = float(r.get("volume", 0))

        if price < 0.02 or price > 0.98:
            continue

        if volume < 100000:
            continue

        last = last_prices.get(market)
        if last:
            move = abs(price - last) / last
            if move < 0.02:
                continue

        exists = cur.execute(
            "select count(*) from trades where market=? and status='OPEN'",
            (market,)
        ).fetchone()[0]

        if exists > 0:
            continue

        strat = None
        side = None

        if price < 0.2:
            strat = "Contrarian"
            side = "BUY YES"
        elif price > 0.8:
            strat = "Breakout"
            side = "BUY YES"
        else:
            continue

        strat_count = cur.execute(
            "select count(*) from trades where strategy=? and status='OPEN'",
            (strat,)
        ).fetchone()[0]

        if strat_count >= MAX_PER_STRATEGY:
            continue

        cur.execute(
            """insert into trades(strategy,market,side,entry,current,pnl_pct,pnl_value,stake,max_price,min_price,open_time,status)
               values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (strat, market, side, price, price, 0, 0,
             STAKE_PER_TRADE, price, price,
             str(datetime.datetime.now()), "OPEN")
        )

        total_open += 1

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

        # 🔥 EARLY PROFIT BOOKING
        if pnl_pct >= EARLY_TP and pnl_pct < RUNNER_TP:
            cur.execute("update trades set status='CLOSED' where id=?", (tid,))
            continue

        # 🔥 BIG WINNER TRAILING
        if pnl_pct >= RUNNER_TP:
            trail = max_p * 0.98
            if price < trail:
                cur.execute("update trades set status='CLOSED' where id=?", (tid,))
                continue

        # TIME EXIT
        if isinstance(open_time, str):
            open_dt = datetime.datetime.fromisoformat(open_time)
        else:
            open_dt = datetime.datetime.now()

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