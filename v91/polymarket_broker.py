import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# =========================
# CONFIG
# =========================
HOST = "https://clob.polymarket.com"

# 🔴 FILL THESE
PRIVATE_KEY = "YOUR_PRIVATE_KEY"
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
PASSPHRASE = "YOUR_PASSPHRASE"

CHAIN_ID = 137  # Polygon

TEST_MODE = True  # 🔥 keep TRUE initially


# =========================
# BROKER
# =========================
class PolymarketBroker:

    def __init__(self):
        self.client = ClobClient(
            HOST,
            key=PRIVATE_KEY,
            chain_id=CHAIN_ID
        )

        self.client.set_api_creds({
            "key": API_KEY,
            "secret": API_SECRET,
            "passphrase": PASSPHRASE
        })

    # -------------------------
    # PLACE ORDER
    # -------------------------
    def place_order(self, market, side, price, stake, token_id):

        size = round(stake / price, 4)

        print(f"[ORDER] {side} {market} price={price} size={size}")

        if TEST_MODE:
            print("⚠ TEST MODE - no real order placed")
            return {"status": "simulated"}

        try:
            order = OrderArgs(
                price=price,
                size=size,
                side="BUY" if side in ["BUY YES", "BUY NO"] else side,
                token_id=token_id
            )

            signed = self.client.create_order(order)

            resp = self.client.post_order(signed, OrderType.GTC)

            print("Order placed:", resp)
            return resp

        except Exception as e:
            print("Order error:", e)
            return None

    # -------------------------
    # CANCEL ORDER
    # -------------------------
    def cancel_order(self, order_id):

        if TEST_MODE:
            print(f"⚠ TEST MODE - cancel skipped {order_id}")
            return True

        try:
            resp = self.client.cancel(order_id)
            print("Cancel:", resp)
            return resp
        except Exception as e:
            print("Cancel error:", e)
            return None

    # -------------------------
    # GET ORDERBOOK
    # -------------------------
    def get_orderbook(self, token_id):
        try:
            return self.client.get_book(token_id)
        except Exception as e:
            print("Orderbook error:", e)
            return None

    # -------------------------
    # GET BALANCE
    # -------------------------
    def get_balance(self):
        try:
            return self.client.get_balance_allowance()
        except Exception as e:
            print("Balance error:", e)
            return None