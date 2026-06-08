import time, sqlite3
import pandas as pd
from modules.feed import fetch_real_markets

strategies = ["Momentum","MeanReversion","Contrarian","Breakout","VolumeSurge"]

# -------------------------------
# CAPITAL CONFIG (🔥 UPDATED)
# -------------------------------
TOTAL_CAPITAL = 700000
STAKE_PER_TRADE = 25000

MAX_OPEN_TRADES = 10
MAX_PER_STRATEGY = 7
MAX_DRAWDOWN = -20000   # ₹ loss protection

# -------------------------------
# DB INIT + MIGRATION
# -------------------------------
def init_db():
    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                         market TEXT,
                                                         yes_price REAL,
                                                         no_price REAL,
                                                         volume REAL,
                                                         source TEXT,
                                                         ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

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
                                                      status TEXT,
                                                      ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)

    cols = [c[1] for c in cur.execute("PRAGMA table_info(trades)").fetchall()]

    if "pnl_value" not in cols:
        cur.execute("ALTER TABLE trades ADD COLUMN pnl_value REAL DEFAULT 0")

    if "stake" not in cols:
        cur.execute("ALTER TABLE trades ADD COLUMN stake REAL DEFAULT 0")

    cur.execute("""
                CREATE TABLE IF NOT EXISTS allocations (
                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           strategy TEXT,
                                                           weight REAL,
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

# -------------------------------
# REGIME
# -------------------------------
def detect_regime(df, history):
    if history is None or len(history) == 0:
        return "UNKNOWN"

    moves, direction = [], 0

    for m in df["market"]:
        prev = history[history["market"] == m].tail(1)
        curr = df[df["market"] == m]

        if len(prev) and len(curr):
            p1 = float(prev.iloc[0]["yes_price"])
            p2 = float(curr.iloc[0]["yes_price"])

            if p1 > 0:
                moves.append(abs((p2 - p1)/p1))

            direction += 1 if p2 > p1 else -1

    if not moves:
        return "UNKNOWN"

    avg_move = sum(moves)/len(moves)

    if avg_move > 0.05 and abs(direction) > len(moves)*0.6:
        return "TRENDING"
    elif avg_move > 0.05:
        return "MEAN_REVERTING"
    else:
        return "FLAT"

# -------------------------------
# AI
# -------------------------------
def score_weights(cur):
    rows = cur.execute(
        "select strategy, ifnull(avg(pnl_pct),0) from trades group by strategy"
    ).fetchall()

    base = {s:1.0 for s in strategies}

    for strat, pnl in rows:
        base[strat] = max(0.1, 1 + pnl/10)

    return base

def regime_weights(base, regime):

    if regime == "TRENDING":
        allowed = ["Momentum","Breakout"]
    elif regime == "MEAN_REVERTING":
        allowed = ["Contrarian","MeanReversion"]
    elif regime == "FLAT":
        allowed = ["VolumeSurge"]
    else:
        allowed = strategies

    filtered = {k:v for k,v in base.items() if k in allowed}
    total = sum(filtered.values())

    return {k:v/total for k,v in filtered.items()} if total else {}

# -------------------------------
# START
# -------------------------------
init_db()
print("V8.4 Fixed Capital Engine started")

history_df = pd.DataFrame()

while True:

    df = fetch_real_markets()

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    # SNAPSHOT
    for _, r in df.iterrows():
        cur.execute(
            "insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)",
            (r["market"],r["yes_price"],r["no_price"],r["volume"],r["source"])
        )

    regime = detect_regime(df, history_df)
    print("Regime:", regime)

    history_df = pd.concat([history_df, df]).tail(200)

    base = score_weights(cur)
    weights = regime_weights(base, regime)

    cur.execute("delete from allocations")
    for s,w in weights.items():
        cur.execute("insert into allocations(strategy,weight) values(?,?)",(s,w))

    # -------------------------------
    # CAPITAL TRACKING
    # -------------------------------
    total_pnl = cur.execute("select ifnull(sum(pnl_value),0) from trades").fetchone()[0]
    equity = TOTAL_CAPITAL + total_pnl

    # drawdown protection
    if total_pnl < MAX_DRAWDOWN:
        print("⚠ Drawdown limit hit. Pausing trading.")
        con.commit(); con.close()
        time.sleep(60)
        continue

    # -------------------------------
    # EXECUTION
    # -------------------------------
    total_open = cur.execute(
        "select count(*) from trades where status='OPEN'"
    ).fetchone()[0]

    for _, r in df.iterrows():

        if total_open >= MAX_OPEN_TRADES:
            break

        market = r["market"]
        price = float(r["yes_price"])

        exists = cur.execute(
            "select count(*) from trades where market=? and status='OPEN'",
            (market,)
        ).fetchone()[0]

        if exists > 0:
            continue

        sorted_strats = sorted(weights.items(), key=lambda x:-x[1])

        for strat, w in sorted_strats:

            if w < 0.10:
                continue

            strat_open = cur.execute(
                "select count(*) from trades where strategy=? and status='OPEN'",
                (strat,)
            ).fetchone()[0]

            if strat_open >= MAX_PER_STRATEGY:
                continue

            side = None

            if strat=="Momentum" and price>0.60:
                side="BUY YES"
            elif strat=="MeanReversion" and price>0.75:
                side="BUY NO"
            elif strat=="Contrarian" and price<0.20:
                side="BUY YES"
            elif strat=="Breakout" and price>0.80:
                side="BUY YES"
            elif strat=="VolumeSurge" and float(r["volume"])>1000000:
                side="BUY YES"

            if side:
                cur.execute(
                    """insert into trades(strategy,market,side,entry,current,pnl_pct,pnl_value,stake,status)
                       values(?,?,?,?,?,?,?,?,?)""",
                    (strat,market,side,price,price,0,0,STAKE_PER_TRADE,"OPEN")
                )
                total_open += 1
                break

    # -------------------------------
    # UPDATE
    # -------------------------------
    rows = cur.execute(
        "select id,market,side,entry,stake from trades where status='OPEN'"
    ).fetchall()

    for tid, market, side, entry, stake in rows:

        sub = df[df["market"]==market]
        if len(sub)>0:

            price = float(sub.iloc[0]["yes_price"])

            pnl_pct = ((price-entry)/entry)*100 if side=="BUY YES" else ((entry-price)/entry)*100
            pnl_val = stake * pnl_pct/100

            cur.execute(
                "update trades set current=?, pnl_pct=?, pnl_value=? where id=?",
                (price,round(pnl_pct,2),round(pnl_val,2),tid)
            )

            if pnl_pct>=5 or pnl_pct<=-3:
                cur.execute(
                    "update trades set status='CLOSED' where id=?",
                    (tid,)
                )

    # -------------------------------
    # EQUITY
    # -------------------------------
    total_pnl = cur.execute("select ifnull(sum(pnl_value),0) from trades").fetchone()[0]
    equity = TOTAL_CAPITAL + total_pnl

    cur.execute("insert into portfolio(equity) values(?)",(equity,))

    print(f"Equity: {round(equity,2)} | PnL: {round(total_pnl,2)}")

    con.commit()
    con.close()

    time.sleep(60)