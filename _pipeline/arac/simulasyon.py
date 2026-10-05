"""Simülasyon aşaması: rehberin "şunu ekle, şunu değiştir" talimatlarını sırayla uygular ve
her adımın sonunda ortaya çıkan dosyanın ilgili ara sürümle (AST düzeyinde) aynı olduğunu doğrular.

Girdi: _pipeline/projeler/{slug}/adimlar.yaml
İşlemler:
  fn_degistir     {fn}               fonksiyonu içerikle değiştirir
  fn_sonrasi      {fn}               fonksiyondan sonra ekler
  fn_oncesi       {fn}               fonksiyondan önce ekler
  satir_sonrasi   {capa}             çapayla başlayan ilk satırdan sonra ekler
  fn_icinde_once  {fn, satir}        fonksiyon içindeki son eşleşen satırdan önce ekler
  bas_degistir    {}                 import ve sabit bloğunu değiştirir
İçerik: {fn: [yol, ad]} | {fnler: [yol, [ad, ...]]} | {sabit: [yol, ad]} | {bas: yol} | {metin: "...", girinti: n}
(YAML blok metinleri ortak girintiyi siler; fonksiyon içine eklenecek satırlar için girinti verilir.)
"""

import ast

import yaml

from ortak import PipelineHatasi, Proje, bas_blok, fonksiyon, fonksiyon_satirlari, sabit


def _icerik(proje: Proje, ic: dict) -> str:
    if "fn" in ic:
        return fonksiyon(proje.kaynak(ic["fn"][0]), ic["fn"][1])
    if "fnler" in ic:
        kaynak = proje.kaynak(ic["fnler"][0])
        return "\n\n\n".join(fonksiyon(kaynak, ad) for ad in ic["fnler"][1])
    if "sabit" in ic:
        return sabit(proje.kaynak(ic["sabit"][0]), ic["sabit"][1])
    if "bas" in ic:
        return bas_blok(proje.kaynak(ic["bas"]))
    girinti = " " * ic.get("girinti", 0)
    return "\n".join(girinti + satir if satir else satir for satir in ic["metin"].rstrip("\n").split("\n"))


def _uygula(kod: str, islem: dict, yeni: str) -> str:
    s = kod.split("\n")
    tur = islem["islem"]
    if tur in ("fn_degistir", "fn_sonrasi", "fn_oncesi"):
        a, b = fonksiyon_satirlari(kod, islem["fn"])
        if tur == "fn_degistir":
            return "\n".join(s[: a - 1] + yeni.split("\n") + s[b:])
        if tur == "fn_sonrasi":
            return "\n".join(s[:b] + ["", ""] + yeni.split("\n") + s[b:])
        return "\n".join(s[: a - 1] + yeni.split("\n") + ["", ""] + s[a - 1:])
    if tur == "satir_sonrasi":
        i = next((k for k, x in enumerate(s) if x.strip().startswith(islem["capa"])), None)
        if i is None:
            raise PipelineHatasi(f"Simülasyon: çapa bulunamadı: {islem['capa']!r}")
        ek = ([""] if islem.get("bosluk_once") else []) + yeni.split("\n")
        return "\n".join(s[: i + 1] + ek + s[i + 1:])
    if tur == "fn_icinde_once":
        a, b = fonksiyon_satirlari(kod, islem["fn"])
        i = max(k for k in range(a - 1, b) if s[k] == islem["satir"])
        return "\n".join(s[:i] + yeni.split("\n") + s[i:])
    if tur == "bas_degistir":
        agac = ast.parse(kod)
        bas = agac.body[1].lineno - 1 if isinstance(agac.body[0], ast.Expr) else 0
        son = next(k for k, x in enumerate(s) if k > bas and x.startswith("def "))
        return "\n".join(s[:bas] + yeni.split("\n") + ["", ""] + s[son:])
    raise PipelineHatasi(f"Bilinmeyen simülasyon işlemi: {tur}")


def _govde(kod: str) -> str:
    agac = ast.parse(kod)
    if agac.body and isinstance(agac.body[0], ast.Expr) and isinstance(agac.body[0].value, ast.Constant):
        agac.body = agac.body[1:]
    return ast.dump(agac)


def calistir(proje: Proje) -> None:
    ayar = yaml.safe_load((proje.girdi / "adimlar.yaml").read_text(encoding="utf-8"))
    kod = proje.kaynak(ayar["baslangic"])
    for adim in ayar["adimlar"]:
        for islem in adim["islemler"]:
            kod = _uygula(kod, islem, _icerik(proje, islem.get("icerik", {"metin": ""})))
        esit = _govde(kod) == _govde(proje.kaynak(adim["hedef"]))
        print(f"  {adim['ad']}: {'tamam' if esit else 'FARKLI'} ({adim['hedef']})")
        if not esit:
            raise PipelineHatasi(f"Simülasyon: '{adim['ad']}' talimatları {adim['hedef']} dosyasını üretmiyor.")
