
import time, sqlite3
from modules.feed import fetch_real_markets

print("V7.7 Auto Paper Trader started")

def run_cycle():
    df = fetch_real_markets()
    con=sqlite3.connect("portfolio.db")
    cur=con.cursor()

    # save snapshots
    for _,r in df.iterrows():
        cur.execute("insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)",
                    (r["market"],r["yes_price"],r["no_price"],r["volume"],r["source"]))

    # signals + entries
    for _,r in df.iterrows():
        price=float(r["yes_price"])
        side=None
        if price > 0.60:
            side="BUY YES"
        elif price < 0.40:
            side="BUY NO"

        if side:
            ex=cur.execute("select count(*) from paper_trades where market=? and status='OPEN'",(r["market"],)).fetchone()[0]
            if ex==0:
                cur.execute("insert into paper_trades(market,side,entry,current,pnl_pct,status,reason) values(?,?,?,?,?,?,?)",
                            (r["market"],side,price,price,0,"OPEN","Signal"))

    # update open trades
    rows=cur.execute("select id,market,side,entry from paper_trades where status='OPEN'").fetchall()
    for t in rows:
        tid,market,side,entry=t
        sub=df[df["market"]==market]
        if len(sub)>0:
            price=float(sub.iloc[0]["yes_price"])
            pnl=((price-entry)/entry)*100 if side=="BUY YES" else ((entry-price)/entry)*100
            cur.execute("update paper_trades set current=?, pnl_pct=? where id=?",(price,round(pnl,2),tid))

            # exits
            reason=None
            if pnl >= 5:
                reason="TP"
            elif pnl <= -3:
                reason="SL"

            if reason:
                cur.execute("update paper_trades set status='CLOSED', reason=? where id=?",(reason,tid))

    con.commit(); con.close()

while True:
    run_cycle()
    print("Cycle complete")
    time.sleep(60)
