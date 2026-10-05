"""Context window doluluk testi için gerçekçi bir uygulama log dosyası üretir.

Kullanım:
    python ornekler/uzun_log_uret.py                  # varsayılan 6000 satır
    python ornekler/uzun_log_uret.py --satir 9000     # daha uzun dosya

Çıktı: ornekler/uzun_log.txt
Aynı tohum (seed) kullanıldığı için her çalıştırmada aynı dosya üretilir.
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

SERVICES = ["order-service", "stock-service", "payment-gateway", "invoice-worker", "auth-service"]

MESSAGES = {
    "INFO": [
        "Sipariş oluşturuldu: order={order} müşteri={customer} tutar={amount} TL",
        "Fatura kuyruğa alındı: invoice={invoice} kalem={items}",
        "Kullanıcı oturum açtı: user={customer} kanal=web",
        "Stok güncellendi: sku={sku} yeni_miktar={qty}",
        "Ödeme onaylandı: order={order} sağlayıcı=banka-{bank} süre={ms}ms",
    ],
    "WARN": [
        "Stok sorgusu yavaş yanıt verdi: sku={sku} süre={ms}ms havuz={pool}/5",
        "Yeniden deneme başlatıldı: order={order} deneme={attempt}/3",
        "Fatura alanı eksik: invoice={invoice} alan=vergi_no",
        "Tarih formatı dönüştürüldü: invoice={invoice} kaynak=GG.AA.YYYY",
    ],
    "ERROR": [
        "Veritabanı bağlantısı alınamadı: havuz tükendi ({pool}/5) bekleme={ms}ms",
        "İstek zaman aşımına uğradı: endpoint=/api/orders süre={ms}ms",
        "Ödeme sağlayıcısı hata döndü: order={order} kod=HTTP_503",
    ],
}

LEVEL_WEIGHTS = [("INFO", 70), ("WARN", 20), ("ERROR", 10)]


def make_line(rng: random.Random, ts: datetime) -> str:
    level = rng.choices([lvl for lvl, _ in LEVEL_WEIGHTS], weights=[w for _, w in LEVEL_WEIGHTS])[0]
    template = rng.choice(MESSAGES[level])
    message = template.format(
        order=f"ORD-{rng.randint(100000, 999999)}",
        customer=f"C{rng.randint(1000, 9999)}",
        amount=f"{rng.randint(50, 25000)},{rng.randint(0, 99):02d}",
        invoice=f"INV-2026-{rng.randint(10000, 99999)}",
        items=rng.randint(1, 40),
        sku=f"TR-{rng.randint(10000, 99999)}",
        qty=rng.randint(0, 500),
        bank=rng.randint(1, 9),
        ms=rng.randint(40, 31000),
        pool=rng.randint(3, 5),
        attempt=rng.randint(1, 3),
    )
    request_id = f"{rng.getrandbits(32):08x}"
    service = rng.choice(SERVICES)
    return f"{ts:%Y-%m-%d %H:%M:%S}.{ts.microsecond // 1000:03d} {level:<5} [{service}] [req={request_id}] {message}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Uzun log dosyası üretir.")
    parser.add_argument("--satir", type=int, default=6000, help="Üretilecek satır sayısı (varsayılan: 6000)")
    args = parser.parse_args()

    rng = random.Random(42)
    ts = datetime(2026, 9, 14, 8, 0, 0)
    lines = []
    for _ in range(args.satir):
        ts += timedelta(milliseconds=rng.randint(5, 900))
        lines.append(make_line(rng, ts))

    out_path = Path(__file__).parent / "uzun_log.txt"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{args.satir} satır yazıldı: {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
