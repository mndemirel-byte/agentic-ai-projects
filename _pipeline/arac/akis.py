"""Kod rehberi (akış): bir komutun kodda hangi fonksiyonlardan geçtiğini adım adım gösteren sayfa.

Girdi: _pipeline/projeler/{slug}/akis_rehberi.yaml (+ isteğe bağlı ekstra HTML bölümü)
Satır aralıkları ve blok aralıkları her üretimde çözüm dosyasından yeniden hesaplanır.
Ekstra bölümdeki {{VERI:dosya.yaml}} işaretleri, proje klasöründeki YAML dosyasının JSON hâliyle değiştirilir.
"""

import html
import json
import re

import yaml

from ortak import PIPELINE, PipelineHatasi, Proje, bolumler, fonksiyon_satirlari


def _konum(kaynak: str, konum: dict) -> str:
    if "fn" in konum:
        bas, son = fonksiyon_satirlari(kaynak, konum["fn"])
    else:
        satirlar = kaynak.split("\n")
        bas = next((i + 1 for i, s in enumerate(satirlar) if s.strip().startswith(konum["capa"])), None)
        if bas is None:
            raise PipelineHatasi(f"Akış rehberi: çapa bulunamadı: {konum['capa']!r}")
        son = bas + konum.get("uzunluk", 1) - 1
    return f"satır {bas}–{son}" if son != bas else f"satır {bas}"


def _adim(kaynak: str, a: dict) -> dict:
    return {"b": a["blok"], "fn": a["etiket"], "where": _konum(kaynak, a["konum"]), "title": a["baslik"],
            "what": a["ne"].strip(), "code": a["kod"].rstrip("\n"), "why": a["neden"].strip()}


def uret(proje: Proje) -> None:
    ayar = yaml.safe_load((proje.girdi / "akis_rehberi.yaml").read_text(encoding="utf-8"))
    dosya = proje.ayar["cozum"]
    kaynak = proje.kaynak(dosya)

    araliklar = bolumler(kaynak)
    bloklar = []
    for b in ayar["bloklar"]:
        eslesen = [(bas, son) for ad, bas, son in araliklar if ad.startswith(b["bolum"])]
        if not eslesen:
            raise PipelineHatasi(f"Akış rehberi: '{b['bolum']}' ile başlayan bölüm başlığı çözüm dosyasında yok.")
        bas, son = eslesen[0]
        bloklar.append({"id": b["anahtar"], "name": b["bolum"], "lines": f"satır {bas}–{son}", "desc": b["aciklama"]})

    veri = {"bloklar": bloklar,
            "ortak_adimlar": [_adim(kaynak, a) for a in ayar.get("ortak_adimlar", [])],
            "akislar": [{"ad": ak["ad"], "adimlar": [_adim(kaynak, a) for a in ak["adimlar"]]} for ak in ayar["akislar"]]}

    ekstra_html = ekstra_js = ""
    if ayar.get("ekstra"):
        metin = (proje.girdi / ayar["ekstra"]).read_text(encoding="utf-8")
        metin = re.sub(r"\{\{VERI:([^}]+)\}\}",
                       lambda m: json.dumps(yaml.safe_load(proje.kaynak(m.group(1))), ensure_ascii=False), metin)
        metin = re.sub(r"^<!--.*?-->\n", "", metin, flags=re.S)
        m = re.search(r"<script>\n?(.*?)</script>", metin, flags=re.S)
        ekstra_js = m.group(1) if m else ""
        ekstra_html = metin[: m.start()].strip() if m else metin.strip()

    baslik = ayar["baslik"]
    dosya_adi = dosya.split("/")[-1]
    baslik_html = html.escape(baslik).replace(html.escape(dosya_adi), f"<code>{html.escape(dosya_adi)}</code>", 1)
    sayfa = ((PIPELINE / "arac" / "sablonlar" / "akis.html").read_text(encoding="utf-8")
             .replace("{{BASLIK_DUZ}}", html.escape(baslik))
             .replace("{{BASLIK}}", baslik_html)
             .replace("{{GIRIS}}", html.escape(ayar["giris"]))
             .replace("{{DOSYA}}", html.escape(dosya_adi))
             .replace("{{EKSTRA_HTML}}", ekstra_html)
             .replace("{{EKSTRA_JS}}", ekstra_js)
             .replace("{{DIPNOT}}", html.escape(ayar.get("dipnot", "")))
             .replace("{{AKIS}}", json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")))
    hedef = proje.yol("kod-rehberi.html")
    hedef.write_text(sayfa, encoding="utf-8", newline="\n")
    print(f"Yazıldı: {hedef.name} ({sum(len(a['adimlar']) for a in veri['akislar']) + len(veri['ortak_adimlar'])} adım)")
