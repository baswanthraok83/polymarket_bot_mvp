import sqlite3

def save_snapshots(df):
 con=sqlite3.connect('portfolio.db'); cur=con.cursor()
 for _,r in df.iterrows():
  cur.execute('insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)',(r['market'],r['yes_price'],r['no_price'],r['volume'],r['source']))
 con.commit(); con.close()
