"""Demo aşaması: ölçüm çıktısından demo.json (platform) ve demo.html (repo) üretir.

demo.json schema 2:
  scenes      — demo kartının sahneleri (başlık, açıklama, komut, çıktı)
  parameters  — CLI parametre başvurusu; parser fonksiyonundan okunur, açıklamalar proje.yaml'dan gelir
  steps       — eski terminal oynatıcıları için command/output dizisi (geriye uyumluluk)
demo.html, _pipeline/demo-player/ProjectDemo.tsx bileşeninin bağımsız derlemesidir; platform aynı
bileşeni MDX içinde <ProjectDemo /> olarak gösterir.
"""

import argparse
import json
import subprocess

import olcum
from ortak import PIPELINE, PipelineHatasi, Proje, modul_yukle


def _tur(eylem) -> str:
    if not eylem.option_strings:
        return "konumsal"
    return "bayrak" if eylem.nargs == 0 else "seçenek"


def _deger(eylem, dosya_alanlari: set) -> str:
    if eylem.nargs == 0:
        return ""
    if eylem.type is int:
        return "sayı"
    if eylem.type is float:
        return "ondalık sayı"
    return "dosya yolu" if eylem.dest in dosya_alanlari else "metin"


def parametreler(proje: Proje) -> list[dict]:
    """Parametreleri çözümün parser fonksiyonundan okur ve proje.yaml açıklamalarıyla birleştirir."""
    ayar = proje.ayar["demo"]
    modul = modul_yukle(proje.yol(proje.ayar["cozum"]))
    parser = getattr(modul, ayar.get("parser_fonksiyonu", "build_parser"))()
    aciklamalar = ayar["parametreler"]
    varsayilan_etiket = ayar.get("varsayilan_etiketleri", {})
    dosya_alanlari = set(ayar.get("dosya_alanlari", []))
    eksik = []

    def kayit(komut, eylem):
        ad = eylem.option_strings[0] if eylem.option_strings else eylem.dest
        anahtar = f"{komut} {ad}"
        if anahtar not in aciklamalar:
            eksik.append(anahtar)
            return None
        bilgi = aciklamalar[anahtar]
        if eylem.dest in varsayilan_etiket:
            vars_ = varsayilan_etiket[eylem.dest]
        elif eylem.nargs == 0 or eylem.default is None:
            vars_ = ""
        else:
            vars_ = str(eylem.default)
        return {"name": ad, "kind": _tur(eylem), "value": _deger(eylem, dosya_alanlari), "default": vars_,
                "short": eylem.help or "", "detail": bilgi["aciklama"].strip(), "example": bilgi["ornek"],
                "positional": not eylem.option_strings}

    gruplar = []
    genel = [kayit("genel", e) for e in parser._actions if e.option_strings and e.dest != "help"]
    if genel:
        gruplar.append({"command": "genel", "title": "Genel seçenek", "summary": "Alt komuttan önce yazılır.",
                        "params": [g for g in genel if g]})
    alt = next((e for e in parser._actions if isinstance(e, argparse._SubParsersAction)), None)
    for komut, altparser in (alt.choices.items() if alt else []):
        bilgi = aciklamalar.get(f"{komut} {komut}")
        if not bilgi:
            eksik.append(f"{komut} {komut}")
            continue
        gruplar.append({"command": komut, "title": f"{komut} komutu", "summary": bilgi["aciklama"].strip(),
                        "example": bilgi["ornek"],
                        "params": [k for k in (kayit(komut, e) for e in altparser._actions if e.dest != "help") if k]})
    if eksik:
        raise PipelineHatasi("Açıklaması olmayan parametreler (proje.yaml > demo > parametreler): " + ", ".join(eksik))
    return gruplar


def uret(proje: Proje, onizleme: bool = False) -> None:
    ayar = proje.ayar["demo"]
    olcumler = olcum.oku(proje, onizleme)
    sahneler, adimlar = [], []
    for sahne in ayar["sahneler"]:
        if sahne["olcum"] not in olcumler:
            raise PipelineHatasi(f"Demo sahnesinin ölçümü yok: {sahne['olcum']}")
        komut, cikti = olcumler[sahne["olcum"]]
        if cikti.startswith("Hata:") or "Traceback" in cikti:
            raise PipelineHatasi(f"'{sahne['olcum']}' ölçümü hata ile bitmiş.")
        sahneler.append({"title": sahne["baslik"], "caption": sahne["aciklama"].strip(), "command": komut, "output": cikti})
        adimlar += [{"role": "command", "content": komut}, {"role": "output", "content": cikti}]

    demo = {"schema": 2, "demo_kind": "terminal", "title": ayar["baslik"], "representative": onizleme,
            "scenes": sahneler, "parameters": parametreler(proje), "steps": adimlar}
    if not onizleme:
        demo.pop("representative")

    json_yolu = proje.cikti / "demo.json"
    json_yolu.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Yazıldı: {json_yolu.relative_to(PIPELINE.parent)} ({len(sahneler)} sahne)")

    html_yolu = (proje.cikti / "demo-onizleme.html") if onizleme else proje.yol("demo.html")
    oynatici = PIPELINE / "demo-player"
    subprocess.run(["node", str(oynatici / "build.mjs"), str(json_yolu), str(html_yolu)], check=True, cwd=oynatici)
