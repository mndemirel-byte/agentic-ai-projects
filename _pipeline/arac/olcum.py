"""Ölçüm aşaması: proje.yaml'daki komutları gerçek API ile çalıştırır ve çıktıyı kaydeder.

Çıktı dosyası (_pipeline/projeler/{slug}/olcum_cikti.txt) repoya eklenir; rehberdeki
beklenen çıktılar ve demo bu dosyadan üretilir. Pipeline'da yapay sayı kullanılmaz.
"""

import contextlib
import io
import os
import re
import shlex
import subprocess
from datetime import date
from pathlib import Path

from ortak import PipelineHatasi, Proje, modul_yukle

AYIRICI = "=" * 66


def _env_yukle() -> None:
    """Depo kökündeki .env dosyasını okur; terminalde zaten tanımlı değişkenlerin üzerine yazmaz."""
    dosya = Path(__file__).resolve().parents[2] / ".env"
    if not dosya.exists():
        return
    for satir in dosya.read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        ad, _, deger = satir.partition("=")
        ad = ad.removeprefix("export ").strip()
        os.environ.setdefault(ad, deger.strip().strip("\"'"))


_env_yukle()

# Windows'ta alt süreç çıktısı sistemin kodlamasıyla (cp1254/cp1252) okunursa Türkçe karakterler bozulur.
# Alt süreçler UTF-8 modunda çalıştırılır, çıktı açıkça UTF-8 olarak okunur, satır sonları LF'e sabitlenir.
UTF8_ORTAM = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
BOZUK_KODLAMA = ("Ã", "Ä±", "ÅŸ", "â–", "â€")


def olcum_dosyasi(proje: Proje, onizleme: bool = False):
    ad = "olcum_onizleme.txt" if onizleme else "olcum_cikti.txt"
    return proje.girdi / ad


def _sahte_calistir(proje: Proje, komut: str) -> tuple[str, int]:
    """'python dosya.py argümanlar' komutunu sahte istemciyle süreç içinde çalıştırır."""
    parca = shlex.split(komut)
    if parca[0] != "python":
        raise PipelineHatasi(f"Önizleme yalnızca 'python ...' komutlarını çalıştırabilir: {komut}")
    istemci = modul_yukle(proje.girdi / proje.ayar["olcum"]["sahte_istemci"]).SahteIstemci()
    modul = modul_yukle(proje.yol(parca[1]))
    tampon = io.StringIO()
    eski = os.getcwd()
    os.chdir(proje.klasor)
    try:
        with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
            kod = modul.main(parca[2:], client=istemci)
    finally:
        os.chdir(eski)
    return tampon.getvalue(), kod


def calistir(proje: Proje, onizleme: bool = False) -> None:
    ayar = proje.ayar["olcum"]
    if not onizleme and not os.environ.get("ANTHROPIC_API_KEY"):
        raise PipelineHatasi("ANTHROPIC_API_KEY tanımlı değil; ölçüm gerçek API ile yapılır.")

    for komut in ayar.get("hazirlik", []):
        print(f"[hazırlık] {komut}")
        subprocess.run(komut, shell=True, cwd=proje.klasor, check=True, env=UTF8_ORTAM)

    etiket = "Önizleme (sahte istemci, temsili sayılar)" if onizleme else "Ölçüm"
    parcalar = [f"# {etiket} tarihi: {date.today().isoformat()}", ""]
    hatali = []
    for kayit in ayar["calistirmalar"]:
        print(f"[ölçüm] {kayit['ad']}")
        if onizleme:
            cikti, kod = _sahte_calistir(proje, kayit["komut"])
        else:
            sonuc = subprocess.run(kayit["komut"], shell=True, cwd=proje.klasor, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", env=UTF8_ORTAM)
            cikti, kod = sonuc.stdout + sonuc.stderr, sonuc.returncode
        cikti = cikti.replace("\r\n", "\n").rstrip("\n")
        if kod != 0:
            hatali.append(kayit["ad"])
        parcalar += [AYIRICI, f"## {kayit['ad']}", f"$ {kayit['komut']}", "-" * 66, cikti, ""]

    hedef = olcum_dosyasi(proje, onizleme)
    hedef.write_text("\n".join(parcalar) + "\n", encoding="utf-8", newline="\n")
    print(f"Yazıldı: {hedef}")
    if hatali:
        raise PipelineHatasi("Hata ile biten ölçümler: " + ", ".join(hatali))


def oku(proje: Proje, onizleme: bool = False) -> dict[str, tuple[str, str]]:
    """Ölçüm dosyasını {ad: (komut, çıktı)} sözlüğüne çevirir."""
    dosya = olcum_dosyasi(proje, onizleme)
    if not dosya.exists():
        raise PipelineHatasi(
            f"{dosya.name} yok. Gerçek ölçüm için: python _pipeline/arac/pipeline.py {proje.slug} olcum"
        )
    metin = dosya.read_text(encoding="utf-8").replace("\r\n", "\n")
    bozuk = [m for m in BOZUK_KODLAMA if m in metin]
    if bozuk:
        raise PipelineHatasi(f"{dosya.name} bozuk karakter kodlaması içeriyor ({', '.join(bozuk)}). Ölçümü yeniden çalıştır.")
    sonuc = {}
    for blok in re.split(r"^=+\s*$", metin, flags=re.M):
        m = re.match(r"\s*## (?P<ad>.+?)\n\$ (?P<komut>.+?)\n-+\n(?P<cikti>.*)", blok, flags=re.S)
        if m:
            sonuc[m["ad"].strip()] = (m["komut"].strip(), m["cikti"].rstrip())
    return sonuc
