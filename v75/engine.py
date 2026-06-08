
import time, random, sqlite3

markets=["BTC > 100k","Election X","Fed cuts","Team A wins","Oil > 90"]

print("V7.5 Engine started")
while True:
    con=sqlite3.connect("portfolio.db")
    cur=con.cursor()
    for m in markets:
        y=round(random.uniform(0.2,0.8),4)
        cur.execute("insert into snapshots(market,yes_price,no_price,volume,source) values(?,?,?,?,?)",
                    (m,y,round(1-y,4),random.randint(100000,700000),"engine"))
    con.commit(); con.close()
    print("Inserted snapshot batch")
    time.sleep(60)
