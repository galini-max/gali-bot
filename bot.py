import os
import time
from beem import Hive
from beem.market import Market
from beem.amount import Amount

# --- AGRESIF + AKILLI AYARLAR ---
HIVE_NODE = os.getenv("HIVE_NODE", "https://api.hive.blog")
ACTIVE_KEY = os.getenv("ACTIVE_KEY")
USERNAME = os.getenv("HIVE_USERNAME")

SYMBOL_BASE = "HIVE"
SYMBOL_QUOTE = "HBD"

SPREAD_PERCENT = 0.5
USE_BALANCE_PERCENT = 95
MIN_ORDER_HBD = 0.5

# Akıllı güncelleme eşiği: Emir piyasa fiyatından bu kadar uzaksa güncelle
UPDATE_THRESHOLD_PERCENT = 0.5

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
    print(str(len(orders)) + " emir bulundu, iptal ediliyor...")
    for order in orders:
        try:
            order_id = order.get("orderid")
            hive.rpc.cancel_order(USERNAME, order_id)
            print("Iptal: " + str(order_id))
            time.sleep(2)
        except Exception as e:
            print("Iptal hatasi: " + str(e))

def check_existing_orders(current_bid, current_ask):
    """
    Açık emirleri kontrol et.
    Emirler piyasa fiyatına yakınsa True döndür (güncelleme yapma).
    """
    orders = get_open_orders()
    
    if not orders:
        print("Acik emir yok, yeni emir verilecek")
        return False
    
    buy_orders = [o for o in orders if o.get("type") == "buy"]
    sell_orders = [o for o in orders if o.get("type") == "sell"]
    
    print("Mevcut emirler -> Alis: " + str(len(buy_orders)) + " | Satis: " + str(len(sell_orders)))
    
    # En iyi alış ve satış emirlerimizi bul
    best_buy = max([float(o.get("price", 0)) for o in buy_orders]) if buy_orders else 0
    best_sell = min([float(o.get("price", 999)) for o in sell_orders]) if sell_orders else 999
    
    print("En iyi emirlerim -> Alis: " + str(best_buy) + " | Satis: " + str(best_sell))
    print("Piyasa -> Bid: " + str(current_bid) + " | Ask: " + str(current_ask))
    
    # Emirlerin piyasa fiyatına yakınlığını hesapla
    if best_buy > 0:
        buy_diff = abs(current_bid - best_buy) / current_bid * 100
    else:
        buy_diff = 999
    
    if best_sell < 999:
        sell_diff = abs(current_ask - best_sell) / current_ask * 100
    else:
        sell_diff = 999
    
    print("Fiyat farki -> Alis: %" + str(round(buy_diff, 2)) + " | Satis: %" + str(round(sell_diff, 2)))
    print("Esik deger: %" + str(UPDATE_THRESHOLD_PERCENT))
    
    # Eğer her iki emir de piyasa fiyatına yakınsa, güncelleme yapma
    if buy_diff < UPDATE_THRESHOLD_PERCENT and sell_diff < UPDATE_THRESHOLD_PERCENT:
        print("AKILLI: Emirler piyasa fiyatina yakin, guncelleme yapilmiyor (API tasarrufu)")
        return True
    
    print("AKILLI: Emirler uzakta, guncelleme yapilacak")
    return False

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
    
    my_buy_price = round(highest_bid * (1 - SPREAD_PERCENT / 200), 6)
    my_sell_price = round(lowest_ask * (1 + SPREAD_PERCENT / 200), 6)
    
    balances = get_balances()
    print("Piyasa -> Bid: " + str(highest_bid) + " | Ask: " + str(lowest_ask))
    print("Benim fiyatlarim -> Alis: " + str(my_buy_price) + " | Satis: " + str(my_sell_price))
    print("Bakiye -> HIVE: " + str(balances['HIVE']) + " | HBD: " + str(balances['HBD']))
    
    hbd_to_use = balances["HBD"] * (USE_BALANCE_PERCENT / 100)
    hive_to_use = balances["HIVE"] * (USE_BALANCE_PERCENT / 100)
    
    print("Kullanilacak -> HBD: " + str(round(hbd_to_use, 3)) + " | HIVE: " + str(round(hive_to_use, 3)))
    
    order_placed = False
    
    if hbd_to_use >= MIN_ORDER_HBD:
        try:
            market.buy(my_buy_price, Amount(str(round(hbd_to_use, 3)) + " " + SYMBOL_QUOTE), account=USERNAME)
            print("ALIS: " + str(round(hbd_to_use, 3)) + " HBD @ " + str(my_buy_price))
            time.sleep(2)
            order_placed = True
        except Exception as e:
            print("Alis hatasi: " + str(e))
    else:
        print("Alis atlandi (HBD yetersiz: " + str(round(hbd_to_use, 3)) + ")")
    
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
    print("Hive Bot (AKILLI MOD) - " + time.strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 50)
    
    if not ACTIVE_KEY or not USERNAME:
        print("HATA: ACTIVE_KEY veya USERNAME eksik!")
        return
    
    try:
        # 1. Piyasa fiyatını al
        market = get_market()
        ticker = market.ticker()
        current_bid = float(ticker.get("highest_bid", 0))
        current_ask = float(ticker.get("lowest_ask", 0))
        
        print("Piyasa okundu -> Bid: " + str(current_bid) + " | Ask: " + str(current_ask))
        
        # 2. Akıllı kontrol: Mevcut emirler yeterli mi?
        orders_ok = check_existing_orders(current_bid, current_ask)
        
        if orders_ok:
            # Emirler iyi durumda, sadece bakiyeyi göster
            balances = get_balances()
            print("Bakiye -> HIVE: " + str(balances['HIVE']) + " | HBD: " + str(balances['HBD']))
        else:
            # Emirleri güncelle
            cancel_all_orders()
            time.sleep(3)
            place_orders()
        
        print("Bot dongusu tamamlandi")
    except Exception as e:
        print("Kritik hata: " + str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
