
import sqlite3
def conn(): return sqlite3.connect("portfolio.db")
def init_db():
    c=conn(); cur=c.cursor()
    cur.execute("create table if not exists trades(id integer primary key, ts datetime default current_timestamp, market text, side text, qty real, entry real, current real, pnl real, status text)")
    # migrations
    cols=[r[1] for r in cur.execute("pragma table_info(trades)").fetchall()]
    for col,typ in [("status","TEXT"),("pnl","REAL"),("current","REAL")]:
        if col not in cols:
            cur.execute(f"alter table trades add column {col} {typ}")
    c.commit(); c.close()
def open_trade(market,side,qty,price):
    c=conn(); cur=c.cursor()
    ex=cur.execute("select count(*) from trades where market=? and status='OPEN'",(market,)).fetchone()[0]
    if ex==0:
        cur.execute("insert into trades(market,side,qty,entry,current,pnl,status) values(?,?,?,?,?,?,?)",(market,side,qty,price,price,0,"OPEN"))
    c.commit(); c.close()
def summary():
    c=conn(); cur=c.cursor()
    t=cur.execute("select count(*) from trades").fetchone()[0]
    p=cur.execute("select ifnull(sum(pnl),0) from trades").fetchone()[0]
    c.close()
    return f"Trades:{t} PnL:{round(p,2)}"
