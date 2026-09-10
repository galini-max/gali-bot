import os
import time
from beem import Hive
from beem.market import Market
from beem.amount import Amount

# --- AGRESİF AYARLAR ---
HIVE_NODE = os.getenv("HIVE_NODE", "https://api.hive.blog")
ACTIVE_KEY = os.getenv("ACTIVE_KEY")
USERNAME = os.getenv("HIVE_USERNAME")

SYMBOL_BASE = "HIVE"
SYMBOL_QUOTE = "HBD"

# AGRESİF PARAMETRELER
SPREAD_PERCENT = 0.5          # %0.5 kar marjı (eski %1.5)
USE_BALANCE_PERCENT = 95      # Bakiyenin %95'ini kullan (eski %90)
MIN_ORDER_HBD = 0.5           # Min 0.5 HBD (eski 10)

# Fiyat değişim eşiği (%0.1'den fazla değişirse emir yenile)
PRICE_CHANGE_THRESHOLD = 0.1

def get_client():
    keys = [ACTIVE_KEY] if ACTIVE_KEY else []
    return Hive(node=HIVE_NODE, keys=keys, nobroadcast=False)

def get_market():
    hive = get_client()
    return Market(SYMBOL_BASE + ":" + SYMBOL_QUOTE, blockchain_instance=hive)

def get_balances():
    hive = get_client()
    try:
        acc_data = hive.rpc.get_accounts([USERNAME])[0]
        hive_bal = float(acc_data['balance'].split()[0])
        hbd_bal = float(acc_data['hbd_balance'].split()[0])
        return {"HIVE": hive_bal, "HBD": hbd_bal}
    except Exception as e:
        print("Bakiye hatasi: " + str(e))
        return {"HIVE": 0.0, "HBD": 0.0}

def get_open_orders():
    hive = get_client()
    try:
        orders = hive.rpc.get_open_orders(USERNAME)
        return orders if orders else []
    except Exception as e:
        return []

def cancel_all_orders():
    hive = get_client()
    orders = get_open_orders()
    if not orders:
        print("Iptal edilecek emir yok")
        return
    print(str(len(orders)) + " emir bulundu")
    for order in orders:
        try:
            order_id = order.get("orderid")
            hive.rpc.cancel_order(USERNAME, order_id)
            print("Iptal: " + str(order_id))
            time.sleep(2)
        except Exception as e:
            print("Iptal hatasi: " + str(e))

def place_orders():
    market = get_market()
    ticker = market.ticker()
    
    highest_bid = ticker.get("highest_bid") or ticker.get("highestBid")
    lowest_ask = ticker.get("lowest_ask") or ticker.get("lowestAsk")
    
    if highest_bid is None or lowest_ask is None:
        print("Piyasa verisi alinamadi")
        return
    
    highest_bid = float(highest_bid)
    lowest_ask = float(lowest_ask)
    
    # AGRESİF: Spread çok dar
    my_buy_price = round(highest_bid * (1 - SPREAD_PERCENT / 200), 6)
    my_sell_price = round(lowest_ask * (1 + SPREAD_PERCENT / 200), 6)
    
    balances = get_balances()
    print("Piyasa -> Bid: " + str(highest_bid) + " | Ask: " + str(lowest_ask))
    print("Benim fiyatlarim -> Alis: " + str(my_buy_price) + " | Satis: " + str(my_sell_price))
    print("Bakiye -> HIVE: " + str(balances['HIVE']) + " | HBD: " + str(balances['HBD']))
    
    # AGRESİF: Bakiyenin %95'ini kullan
    hbd_to_use = balances["HBD"] * (USE_BALANCE_PERCENT / 100)
    hive_to_use = balances["HIVE"] * (USE_BALANCE_PERCENT / 100)
    
    print("Kullanilacak -> HBD: " + str(round(hbd_to_use, 3)) + " | HIVE: " + str(round(hive_to_use, 3)))
    
    order_placed = False
    
    # ALIS emri
    if hbd_to_use >= MIN_ORDER_HBD:
        try:
            market.buy(my_buy_price, Amount(str(round(hbd_to_use, 3)) + " " + SYMBOL_QUOTE), account=USERNAME)
            print("ALIS: " + str(round(hbd_to_use, 3)) + " HBD @ " + str(my_buy_price))
            time.sleep(2)
            order_placed = True
        except Exception as e:
            print("Alis hatasi: " + str(e))
    else:
        print("Alis atlandi (HBD yetersiz: " + str(hbd_to_use) + ")")
    
    # SATIS emri
    if hive_to_use >= 0.01:
        try:
            market.sell(my_sell_price, Amount(str(round(hive_to_use, 3)) + " " + SYMBOL_BASE), account=USERNAME)
            print("SATIS: " + str(round(hive_to_use, 3)) + " HIVE @ " + str(my_sell_price))
            time.sleep(2)
            order_placed = True
        except Exception as e:
            print("Satis hatasi: " + str(e))
    else:
        print("Satis atlandi (HIVE yetersiz)")
    
    if not order_placed:
        print("Hic emir verilmedi")

def main():
    print("=" * 50)
    print("Hive Bot (AGRESİF MOD) - " + time.strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 50)
    
    if not ACTIVE_KEY or not USERNAME:
        print("HATA: ACTIVE_KEY veya USERNAME eksik!")
        return
    
    try:
        cancel_all_orders()
        time.sleep(3)
        place_orders()
        print("Bot dongusu tamamlandi")
    except Exception as e:
        print("Kritik hata: " + str(e))

if __name__ == "__main__":
    main()
