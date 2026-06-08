import sqlite3

con = sqlite3.connect("meta.db")
cur = con.cursor()

cur.execute("""
            UPDATE trades
            SET is_outlier = 0
            WHERE is_outlier IS NULL
            """)

con.commit()
con.close()