
import time, datetime
from modules.fetcher import fetch_markets
from modules.ai import rank_markets
from modules.db import open_trade, update_open_prices, close_tp_sl, stats

print("V5.1 started")
while True:
    ts=datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Fetching markets...")
    mkts=fetch_markets()
    ranked=rank_markets(mkts)
    print(f"[{ts}] Ranked {len(ranked)} markets")
    update_open_prices(ranked)
    close_tp_sl()
    top=ranked.head(1)
    for _,r in top.iterrows():
        open_trade(r["market"], "YES" if r["price"]<0.5 else "NO", 20, r["price"])
        print(f"[{ts}] New Trade: {r['market']}")
    s=stats()
    print(f"[{ts}] Open:{s['open']} Closed:{s['closed']} PnL:{round(s['pnl'],2)}")
    print(f"[{ts}] Sleeping 60 sec...")
    time.sleep(60)
