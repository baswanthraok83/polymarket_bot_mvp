
import time, sqlite3
from modules.feed import fetch_real_markets

strategies = ["Momentum","MeanReversion","Contrarian","Breakout","VolumeSurge"]

base = {s: 1.0 for s in strategies}
base["Contrarian"] = 0.1

def score_weights(cur):
    rows=cur.execute("select strategy, ifnull(avg(pnl_pct),0) from trades group by strategy").fetchall()
    base={s:1.0 for s in strategies}
    for r in rows:
        base[r[0]]=max(0.1,1+r[1]/10)
    total=sum(base.values())
    return {k:round(v/total,4) for k,v in base.items()}

print("V7.9 AI Meta Trader started")

while True:
    df=fetch_real_markets()
    con=sqlite3.connect("meta.db")
    cur=con.cursor()

    for _,r in df.iterrows():
        cur.execute("insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)",
                    (r["market"],r["yes_price"],r["no_price"],r["volume"],r["source"]))

    weights=score_weights(cur)
    cur.execute("delete from allocations")
    for s,w in weights.items():
        cur.execute("insert into allocations(strategy,weight) values(?,?)",(s,w))

    for _,r in df.iterrows():
        price=float(r["yes_price"])
        for strat,w in weights.items():
            if w < 0.10:
                continue
            side=None
            if strat=="Momentum" and price>0.60: side="BUY YES"
            elif strat=="MeanReversion" and price>0.75: side="BUY NO"
            elif strat=="Contrarian" and price<0.20: side="BUY YES"
            elif strat=="Breakout" and price>0.80: side="BUY YES"
            elif strat=="VolumeSurge" and float(r["volume"])>1000000: side="BUY YES"

            if side:
                ex=cur.execute("select count(*) from trades where strategy=? and market=? and status='OPEN'",
                               (strat,r["market"])).fetchone()[0]
                if ex==0:
                    cur.execute("insert into trades(strategy,market,side,entry,current,pnl_pct,status) values(?,?,?,?,?,?,?)",
                                (strat,r["market"],side,price,price,0,"OPEN"))

    rows=cur.execute("select id,market,side,entry from trades where status='OPEN'").fetchall()
    for t in rows:
        tid,market,side,entry=t
        sub=df[df["market"]==market]
        if len(sub)>0:
            price=float(sub.iloc[0]["yes_price"])
            pnl=((price-entry)/entry)*100 if side=="BUY YES" else ((entry-price)/entry)*100
            cur.execute("update trades set current=?, pnl_pct=? where id=?",(price,round(pnl,2),tid))
            if pnl>=5 or pnl<=-3:
                cur.execute("update trades set status='CLOSED' where id=?",(tid,))

    con.commit(); con.close()
    print("Cycle complete")
    time.sleep(60)
