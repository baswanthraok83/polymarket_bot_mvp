
import sqlite3
TP=0.10; SL=0.07
def c(): return sqlite3.connect("portfolio.db")
def open_trade(market,side,stake,price):
    con=c(); cur=con.cursor()
    ex=cur.execute("select count(*) from trades where market=? and status='OPEN'",(market,)).fetchone()[0]
    if ex==0:
        cur.execute("insert into trades(market,side,stake,entry,current,pnl,status) values(?,?,?,?,?,?,?)",(market,side,stake,price,price,0,"OPEN"))
    con.commit(); con.close()
def update_open_prices(df):
    con=c(); cur=con.cursor()
    for _,r in df.iterrows():
        cur.execute("update trades set current=?, pnl=(?-entry)*stake where market=? and status='OPEN'",(r["price"],r["price"],r["market"]))
    con.commit(); con.close()
def close_tp_sl():
    con=c(); cur=con.cursor()
    cur.execute("update trades set status='CLOSED' where status='OPEN' and (pnl>=stake*? or pnl<=-stake*?)",(TP,SL))
    con.commit(); con.close()
def stats():
    con=c(); cur=con.cursor()
    o=cur.execute("select count(*) from trades where status='OPEN'").fetchone()[0]
    cl=cur.execute("select count(*) from trades where status='CLOSED'").fetchone()[0]
    pnl=cur.execute("select ifnull(sum(pnl),0) from trades").fetchone()[0]
    con.close()
    return {"open":o,"closed":cl,"pnl":pnl}
