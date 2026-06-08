import sqlite3

con = sqlite3.connect("meta.db")
cur = con.cursor()

cur.execute("DELETE FROM trades")
cur.execute("DELETE FROM portfolio")

con.commit()
con.close()

print("Clean reset done")