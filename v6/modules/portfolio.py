
import sqlite3
def c(): return sqlite3.connect("portfolio.db")
def open_trade(market,side,qty,price):
    con=c(); cur=con.cursor()
    ex=cur.execute("select count(*) from trades where market=? and status='OPEN'",(market,)).fetchone()[0]
    if ex==0:
        cur.execute("insert into trades(market,side,qty,entry,current,reserved,pnl,status) values(?,?,?,?,?,?,?,?)",(market,side,qty,price,price,qty*price,0,"OPEN"))
    con.commit(); con.close()
def update_prices(df):
    con=c(); cur=con.cursor()
    for _,r in df.iterrows():
        cur.execute("update trades set current=?, pnl=(?-entry)*qty where market=? and status='OPEN'",(r["price"],r["price"],r["market"]))
    con.commit(); con.close()
def summary():
    con=c(); cur=con.cursor()
    t=cur.execute("select count(*) from trades").fetchone()[0]
    pnl=cur.execute("select ifnull(sum(pnl),0) from trades").fetchone()[0]
    con.close()
    return f"Trades:{t} PnL:{round(pnl,2)}"
