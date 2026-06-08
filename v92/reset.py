import sqlite3
from datetime import datetime, timezone

con = sqlite3.connect("trades.db")
cur = con.cursor()

# today's UTC date
today = datetime.now(timezone.utc).date().isoformat()

# delete all CLOSED trades created today
cur.execute("""
            DELETE FROM trades
            WHERE status='CLOSED'
              AND date(ts) = ?
            """, (today,))

deleted = cur.rowcount

con.commit()

print(f"✅ Deleted {deleted} closed trades from today")