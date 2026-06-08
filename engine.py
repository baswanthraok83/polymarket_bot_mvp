
import time, datetime
from modules.feed import fetch_markets
from modules.ai_ranker import rank_markets
from modules.portfolio import open_trade, update_prices, summary
print("V6 Engine started")
while True:
    ts=datetime.datetime.now().strftime("%H:%M:%S")
    mkts=fetch_markets()
    ranked=rank_markets(mkts)
    top=ranked.head(1)
    for _,r in top.iterrows():
        open_trade(r["market"], "YES" if r["price"]<0.5 else "NO", 1, r["price"])
    update_prices(ranked)
    print(f"[{ts}] {summary()}")
    time.sleep(60)
