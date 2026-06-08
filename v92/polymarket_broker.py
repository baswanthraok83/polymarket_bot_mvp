import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# =========================
# CONFIG
# =========================
HOST = "https://clob.polymarket.com"

# 🔴 FILL THESE
PRIVATE_KEY = "0x93a978e0c1566a5cb0b63acfc86fb8e631163d2d31a3776742f5ebb861245fa4"
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
PASSPHRASE = "YOUR_PASSPHRASE"

CHAIN_ID = 137

TEST_MODE = True


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
                side="BUY",
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
    # 🔥 FIXED ORDERBOOK
    # -------------------------
    def get_orderbook(self, token_id):
        try:
            return self.client.get_order_book(token_id)
        except Exception as e:
            print("Orderbook error:", e)
            return None

    # -------------------------
    # CANCEL
    # -------------------------
    def cancel_order(self, order_id):
        if TEST_MODE:
            print(f"⚠ TEST MODE - cancel skipped {order_id}")
            return True

        try:
            return self.client.cancel(order_id)
        except Exception as e:
            print("Cancel error:", e)
            return None

    # -------------------------
    # BALANCE
    # -------------------------
    def get_balance(self):
        try:
            return self.client.get_balance_allowance()
        except Exception as e:
            print("Balance error:", e)
            return None