import os
import json
import time
from beem import Hive
from beem.market import Market
from beem.account import Account
from beem.price import Price
from beem.amount import Amount

# --- AYARLAR ---
HIVE_NODE = os.getenv("HIVE_NODE", "https://api.hive.blog")
POSTING_KEY = os.getenv("POSTING_KEY")
ACTIVE_KEY  = os.getenv("ACTIVE_KEY")
USERNAME    = os.getenv("HIVE_USERNAME")

SYMBOL_BASE = "HIVE"
SYMBOL_QUOTE = "HBD"
SPREAD_PERCENT = 1.5
ORDER_AMOUNT_HBD = 10
MAX_OPEN_ORDERS = 3

def get_client():
    keys = [ACTIVE_KEY] if ACTIVE_KEY else []
    return Hive(node=HIVE_NODE, keys=keys, nobroadcast=False)

def get_market():
    hive = get_client()
    return Market(f"{SYMBOL_BASE}:{SYMBOL_QUOTE}", blockchain_instance=hive)

def get_balances():
    hive = get_client()
    acc = Account(USERNAME, blockchain_instance=hive)
    return {
        "HIVE": float(acc.balances["available"][SYMBOL_BASE]),
        "HBD":  float(acc.balances["available"][SYMBOL_QUOTE]),
    }

def get_open_orders():
    hive = get_client()
    acc = Account(USERNAME, blockchain_instance=hive)
    return acc.open_orders

def cancel_all_orders():
    hive = get_client()
    acc = Account(USERNAME, blockchain_instance=hive)
    for order in acc.open_orders:
        try:
            acc.cancel(order["id"])
            print(f"✅ İptal: {order['id']}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ İptal hatası: {e}")

def place_orders():
    market = get_market()
    ticker = market.ticker()
    
    highest_bid = float(ticker["highestBid"])
    lowest_ask  = float(ticker["lowestAsk"])
    
    print(f"📊 Piyasa -> Bid: {highest_bid} | Ask: {lowest_ask}")
    
    my_buy_price  = round(highest_bid * (1 - SPREAD_PERCENT/200), 3)
    my_sell_price = round(lowest_ask  * (1 + SPREAD_PERCENT/200), 3)
    
    balances = get_balances()
    print(f"💰 Bakiye -> HIVE: {balances['HIVE']} | HBD: {balances['HBD']}")
    
    if balances["HBD"] >= ORDER_AMOUNT_HBD:
        try:
            market.buy(my_buy_price, Amount(f"{ORDER_AMOUNT_HBD} {SYMBOL_QUOTE}"))
            print(f"🟢 ALIŞ emri: {ORDER_AMOUNT_HBD} HBD @ {my_buy_price}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Alış hatası: {e}")
    
    hive_to_sell = ORDER_AMOUNT_HBD / my_sell_price
    if balances["HIVE"] >= hive_to_sell:
        try:
            market.sell(my_sell_price, Amount(f"{hive_to_sell:.3f} {SYMBOL_BASE}"))
            print(f"🔴 SATIŞ emri: {hive_to_sell:.3f} HIVE @ {my_sell_price}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Satış hatası: {e}")

def main():
    print(f"\n{'='*50}")
    print(f"🤖 Hive Bot çalıştı - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    if not ACTIVE_KEY or not USERNAME:
        print("❌ ACTIVE_KEY veya HIVE_USERNAME eksik!")
        return
    
    try:
        cancel_all_orders()
        time.sleep(5)
        place_orders()
    except Exception as e:
        print(f"💥 Kritik hata: {e}")

if __name__ == "__main__":
    main()
