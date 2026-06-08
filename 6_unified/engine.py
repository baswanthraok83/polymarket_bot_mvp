import time, datetime, random
from modules.db import init_db, summary, open_trade

init_db()
print("V6.6 Turbo Signals Engine started")

market_pool = [
    ("BTC > 100k", "YES"),
    ("Election X", "NO"),
    ("Fed cuts", "YES"),
    ("Team A wins", "YES"),
    ("Oil > 90", "NO"),
    ("Rate Cut July", "YES"),
    ("Gold > 2500", "YES"),
    ("Recession 2026", "NO"),
    ("ETH > 8k", "YES"),
    ("Inflation Falls", "YES")
]

while True:
    ts = datetime.datetime.now().strftime("%H:%M:%S")

    # choose fresh opportunities each cycle
    signals = random.sample(market_pool, 3)

    print(f"[{ts}] Scanning markets...")

    for s in signals:
        price = round(random.uniform(0.35, 0.70), 2)
        qty = random.choice([1, 1, 1, 2])

        open_trade(s[0], s[1], qty, price)
        print(f"[{ts}] Signal -> {s[0]} {s[1]} @ {price}")

    print(f"[{ts}] {summary()}")
    print(f"[{ts}] Sleeping 20 sec...\n")

    time.sleep(20)