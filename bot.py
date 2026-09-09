import os
import time
from beem import Hive
from beem.market import Market
from beem.account import Account
from beem.amount import Amount

# --- AYARLAR ---
HIVE_NODE = os.getenv("HIVE_NODE", "https://api.hive.blog")
ACTIVE_KEY  = os.getenv("ACTIVE_KEY")
USERNAME    = os.getenv("HIVE_USERNAME")

SYMBOL_BASE = "HIVE"
SYMBOL_QUOTE = "HBD"
SPREAD_PERCENT = 1.5
ORDER_AMOUNT_HBD = 10

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
    """Açık emirleri RPC ile al (en güvenilir yöntem)"""
    hive = get_client()
    try:
        orders = hive.rpc.get_open_orders(USERNAME)
        return orders if orders else []
    except Exception as e:
        print(f"⚠️ Open orders alınamadı: {e}")
        return []

def cancel_all_orders():
    """Tüm açık emirleri iptal et"""
    hive = get_client()
    orders = get_open_orders()
    
    if not orders:
        print("ℹ️ İptal edilecek açık emir yok")
        return
    
    print(f"📋 {len(orders)} açık emir bulundu")
    
    for order in orders:
        try:
            order_id = order.get("orderid")
            # RPC ile doğrudan iptal
            hive.rpc.cancel_order(USERNAME, order_id)
            print(f"✅ İptal edildi: orderid={order_id}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ İptal hatası: {e}")

def place_orders():
    """Alış ve satış emirleri ver"""
    market = get_market()
    ticker = market.ticker()
    
    # 🔍 DEBUG: Ticker çıktısını göster (sorun tespiti için)
    print(f"🔍 Ticker çıktısı: {ticker}")
    
    # Küçük harf anahtarlar (beem'in güncel versiyonu)
    # Fallback olarak büyük harfli olanları da dene
    highest_bid = ticker.get("highest_bid") or ticker.get("highestBid")
    lowest_ask  = ticker.get("lowest_ask")  or ticker.get("lowestAsk")
    
    if highest_bid is None or lowest_ask is None:
        print(f"❌ Piyasa verisi alınamadı! Ticker çıktısını kontrol et.")
        return
    
    highest_bid = float(highest_bid)
    lowest_ask  = float(lowest_ask)
    
    print(f"📊 Piyasa -> Bid: {highest_bid} | Ask: {lowest_ask}")
    
    # Benim fiyatlarım (spread ile)
    my_buy_price  = round(highest_bid * (1 - SPREAD_PERCENT/200), 3)
    my_sell_price = round(lowest_ask  * (1 + SPREAD_PERCENT/200), 3)
    
    balances = get_balances()
    print(f"💰 Bakiye -> HIVE: {balances['HIVE']} | HBD: {balances['HBD']}")
    
    # 🟢 ALIŞ emri (HBD ile HIVE al)
    if balances["HBD"] >= ORDER_AMOUNT_HBD:
        try:
            market.buy(my_buy_price, Amount(f"{ORDER_AMOUNT_HBD} {SYMBOL_QUOTE}"))
            print(f"🟢 ALIŞ emri: {ORDER_AMOUNT_HBD} HBD @ {my_buy_price}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Alış hatası: {e}")
    else:
        print(f"⚠️ Yetersiz HBD bakiyesi: {balances['HBD']} < {ORDER_AMOUNT_HBD}")
    
    # 🔴 SATIŞ emri (HIVE ile HBD al)
    hive_to_sell = ORDER_AMOUNT_HBD / my_sell_price
    if balances["HIVE"] >= hive_to_sell:
        try:
            market.sell(my_sell_price, Amount(f"{hive_to_sell:.3f} {SYMBOL_BASE}"))
            print(f"🔴 SATIŞ emri: {hive_to_sell:.3f} HIVE @ {my_sell_price}")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Satış hatası: {e}")
    else:
        print(f"⚠️ Yetersiz HIVE bakiyesi: {balances['HIVE']} < {hive_to_sell:.3f}")

def main():
    print(f"\n{'='*50
