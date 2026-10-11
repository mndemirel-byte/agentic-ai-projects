"""İçerik aşaması: şablonlara çözüm kodunu ve ölçüm çıktılarını yerleştirir.

Şablon işaretleri:
  {{DOSYA:yol}}            dosyanın tamamı               (yol proje klasörüne göredir)
  {{BAS:yol}}              docstring sonrası import ve sabit bloğu
  {{FN:yol:ad}}            bir fonksiyonun tamamı
  {{SABIT:yol:ad}}         bir sabit, üstündeki yorumlarla
  {{OLCUM:ad[,ad...]}}     ölçüm çıktıları, kısa bir girişle ve komutlarıyla birlikte ```text blokları olarak
                           (önizlemede boş kalır; rehberde yapay sayı bulunmaz). proje.yaml > olcum > gosterim
                           eşlemesi hem komuta hem çıktıya uygulanır (ör. cozum/adim_3.py → calisma/arac.py).
Kod parçaları elle kopyalanmaz; her üretimde kaynaktan çekilir.
"""

import re

import olcum
from ortak import PIPELINE, PipelineHatasi, Proje, bas_blok, fonksiyon, sabit


def _olcum_blok(proje: Proje, olcumler: dict, ad: str, onizleme: bool) -> str:
    if ad not in olcumler:
        if onizleme:
            return ""
        raise PipelineHatasi(f"Şablondaki ölçüm yok: {ad}")
    komut, cikti = olcumler[ad]
    gosterim = proje.ayar["olcum"].get("gosterim", {})
    for eski, yeni in gosterim.items():
        komut = komut.replace(eski, yeni)
        cikti = cikti.replace(eski, yeni)
    return f"```text\n$ {komut}\n{cikti}\n```"


def isle(proje: Proje, metin: str, onizleme: bool) -> str:
    try:
        olcumler = olcum.oku(proje, onizleme=False)
    except PipelineHatasi:
        if not onizleme:
            raise
        olcumler = {}

    def degistir(m):
        tur, arg = m.group(1), m.group(2)
        parca = arg.split(":")
        if tur == "OLCUM":
            bloklar = [_olcum_blok(proje, olcumler, ad.strip(), onizleme) for ad in arg.split(",")]
            bloklar = [b for b in bloklar if b]
            if not bloklar:
                return "\x00BOS\x00"
            giris = ("Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre "
                     "küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):")
            return giris + "\n\n" + "\n\n".join(bloklar)
        kaynak = proje.kaynak(parca[0])
        if tur == "DOSYA":
            return kaynak.rstrip("\n")
        if tur == "BAS":
            return bas_blok(kaynak)
        if tur == "FN":
            return fonksiyon(kaynak, parca[1])
        if tur == "SABIT":
            return sabit(kaynak, parca[1])
        raise PipelineHatasi(f"Bilinmeyen işaret: {tur}")

    sonuc = re.sub(r"\{\{(DOSYA|BAS|FN|SABIT|OLCUM):([^}]+)\}\}", degistir, metin)
    sonuc = sonuc.replace("\n\x00BOS\x00\n", "").replace("\x00BOS\x00", "")
    kalan = re.findall(r"\{\{[A-Z]+:[^}]*\}\}", sonuc)
    if kalan:
        raise PipelineHatasi(f"İşlenmemiş şablon işaretleri: {kalan[:3]}")
    return sonuc


def uret(proje: Proje, onizleme: bool = False) -> None:
    for kayit in proje.ayar["icerik"]:
        sablon = (proje.girdi / kayit["sablon"]).read_text(encoding="utf-8")
        hedef = proje.cikti / kayit["hedef"] if kayit["yer"] == "platform" else proje.yol(kayit["hedef"])
        hedef.write_text(isle(proje, sablon, onizleme), encoding="utf-8", newline="\n")
        print(f"Yazıldı: {hedef.relative_to(PIPELINE.parent)}" + ("  (önizleme: ölçüm blokları boş)" if onizleme else ""))
