import time, sqlite3
import pandas as pd
from modules.feed import fetch_real_markets

strategies = ["Momentum","MeanReversion","Contrarian","Breakout","VolumeSurge"]

# -------------------------------
# REGIME DETECTION
# -------------------------------
def detect_regime(df, history):
    if history is None or len(history) == 0:
        return "UNKNOWN"

    moves = []
    direction = 0

    for m in df["market"]:
        prev = history[history["market"] == m].tail(1)
        curr = df[df["market"] == m]

        if len(prev) and len(curr):
            p1 = float(prev.iloc[0]["yes_price"])
            p2 = float(curr.iloc[0]["yes_price"])

            if p1 > 0:
                moves.append(abs((p2 - p1) / p1))

            if p2 > p1:
                direction += 1
            else:
                direction -= 1

    if not moves:
        return "UNKNOWN"

    avg_move = sum(moves) / len(moves)

    if avg_move > 0.05 and abs(direction) > len(moves) * 0.6:
        return "TRENDING"
    elif avg_move > 0.05:
        return "MEAN_REVERTING"
    else:
        return "FLAT"


# -------------------------------
# AI WEIGHT SCORING
# -------------------------------
def score_weights(cur):
    rows = cur.execute(
        "select strategy, ifnull(avg(pnl_pct),0) from trades group by strategy"
    ).fetchall()

    base = {s: 1.0 for s in strategies}

    for r in rows:
        strat = r[0]
        pnl = r[1]
        base[strat] = max(0.1, 1 + pnl/10)

    total = sum(base.values())
    return {k: round(v/total,4) for k,v in base.items()}


print("V8.1 Regime Engine started")

history_df = pd.DataFrame()

while True:

    df = fetch_real_markets()

    con = sqlite3.connect("meta.db")
    cur = con.cursor()

    # -------------------------------
    # SAVE SNAPSHOTS
    # -------------------------------
    for _, r in df.iterrows():
        cur.execute(
            "insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)",
            (r["market"], r["yes_price"], r["no_price"], r["volume"], r["source"])
        )

    # -------------------------------
    # DETECT REGIME
    # -------------------------------
    regime = detect_regime(df, history_df)
    print("Market Regime:", regime)

    # update history
    history_df = df.copy()

    # -------------------------------
    # AI ALLOCATION
    # -------------------------------
    weights = score_weights(cur)

    cur.execute("delete from allocations")
    for s, w in weights.items():
        cur.execute("insert into allocations(strategy,weight) values(?,?)", (s,w))

    # -------------------------------
    # STRATEGY EXECUTION (FILTERED)
    # -------------------------------
    for _, r in df.iterrows():
        price = float(r["yes_price"])

        for strat, w in weights.items():

            if w < 0.10:
                continue

            # -------- REGIME FILTER --------
            if regime == "TRENDING":
                if strat not in ["Momentum","Breakout"]:
                    continue

            elif regime == "MEAN_REVERTING":
                if strat not in ["Contrarian","MeanReversion"]:
                    continue

            elif regime == "FLAT":
                if strat != "VolumeSurge":
                    continue

            # -------- SIGNAL LOGIC --------
            side = None

            if strat == "Momentum" and price > 0.60:
                side = "BUY YES"

            elif strat == "MeanReversion" and price > 0.75:
                side = "BUY NO"

            elif strat == "Contrarian" and price < 0.20:
                side = "BUY YES"

            elif strat == "Breakout" and price > 0.80:
                side = "BUY YES"

            elif strat == "VolumeSurge" and float(r["volume"]) > 1000000:
                side = "BUY YES"

            if side:
                ex = cur.execute(
                    "select count(*) from trades where strategy=? and market=? and status='OPEN'",
                    (strat, r["market"])
                ).fetchone()[0]

                if ex == 0:
                    cur.execute(
                        "insert into trades(strategy,market,side,entry,current,pnl_pct,status) values(?,?,?,?,?,?,?)",
                        (strat, r["market"], side, price, price, 0, "OPEN")
                    )

    # -------------------------------
    # UPDATE TRADES
    # -------------------------------
    rows = cur.execute(
        "select id,market,side,entry from trades where status='OPEN'"
    ).fetchall()

    for t in rows:
        tid, market, side, entry = t

        sub = df[df["market"] == market]
        if len(sub) > 0:
            price = float(sub.iloc[0]["yes_price"])

            pnl = ((price-entry)/entry)*100 if side == "BUY YES" else ((entry-price)/entry)*100

            cur.execute(
                "update trades set current=?, pnl_pct=? where id=?",
                (price, round(pnl,2), tid)
            )

            if pnl >= 5 or pnl <= -3:
                cur.execute(
                    "update trades set status='CLOSED' where id=?",
                    (tid,)
                )

    con.commit()
    con.close()

    time.sleep(60)