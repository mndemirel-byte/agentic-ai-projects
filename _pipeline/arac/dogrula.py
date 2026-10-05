"""Doğrulama aşaması: teslimden önce çalıştırılan kontrol paketi.

Kontroller: testler, lint, simülasyon, UTF-8 ve Unicode kaçışı, Markdown bağlantıları,
MDX derlemesi, demo.json şeması, üretilen HTML'lerdeki JS sözdizimi.
Ekran görüntüsü kontrolü ayrı bir aşamadır (ekran).
"""

import json
import re
import subprocess
import sys

import simulasyon
from ortak import PIPELINE, PipelineHatasi, Proje

HTML_DOSYALARI = ["kod-rehberi.html", "kod-rehberi-yan-yana.html", "demo.html"]


def _adim(ad: str, fn) -> bool:
    try:
        fn()
        print(f"[tamam] {ad}")
        return True
    except (PipelineHatasi, subprocess.CalledProcessError, AssertionError) as e:
        print(f"[HATA]  {ad}: {e}")
        return False


def calistir(proje: Proje, onizleme: bool = False) -> None:
    k = proje.klasor
    sonuclar = []

    sonuclar.append(_adim("testler", lambda: subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=k, check=True, capture_output=True)))
    py = [proje.ayar["cozum"], *proje.ayar.get("ara_surumler", [])]
    sonuclar.append(_adim("lint (pyflakes)", lambda: subprocess.run(
        [sys.executable, "-m", "pyflakes", *py], cwd=k, check=True)))
    sonuclar.append(_adim("simülasyon", lambda: simulasyon.calistir(proje)))

    def kodlama():
        for yol in [*k.rglob("*.md"), *k.rglob("*.py"), *k.rglob("*.html"), *k.rglob("*.yaml"), *proje.cikti.glob("*")]:
            if ".venv" in yol.parts or yol.is_dir():
                continue
            metin = yol.read_text(encoding="utf-8")
            assert not re.search(r"\\u0[0-9a-fA-F]{3}", metin) or yol.suffix == ".html", f"Unicode kaçışı: {yol.name}"
    sonuclar.append(_adim("UTF-8 ve Unicode kaçışı", kodlama))

    def baglantilar():
        for md in k.rglob("*.md"):
            if ".venv" in md.parts:
                continue
            metin = md.read_text(encoding="utf-8")
            capalar = set(re.findall(r'<a id="([^"]+)"', metin))
            for hedef in re.findall(r"\]\(([^)\s]+)\)", metin):
                if hedef.startswith("http"):
                    continue
                if hedef.startswith("#"):
                    assert hedef[1:] in capalar, f"{md.name}: kırık çapa {hedef}"
                    continue
                yol = (md.parent / hedef.split("#")[0]).resolve()
                if yol.name == "demo.html" and onizleme:
                    continue
                assert yol.exists(), f"{md.name}: kırık bağlantı {hedef}"
    sonuclar.append(_adim("Markdown bağlantıları", baglantilar))

    oynatici = PIPELINE / "demo-player"
    for mdx in proje.cikti.glob("*.mdx"):
        sonuclar.append(_adim(f"MDX derlemesi ({mdx.name})", lambda m=mdx: subprocess.run(
            ["node", "mdx-kontrol.mjs", str(m)], cwd=oynatici, check=True, capture_output=True)))

    def demo_json():
        d = json.loads((proje.cikti / "demo.json").read_text(encoding="utf-8"))
        assert d["schema"] == 2 and d["scenes"] and d["parameters"], "demo.json eksik alan"
        assert ("representative" in d) == onizleme, "demo.json önizleme etiketi tutarsız"
    sonuclar.append(_adim("demo.json şeması", demo_json))

    html = [str(k / h) for h in HTML_DOSYALARI if (k / h).exists()]
    if onizleme and (proje.cikti / "demo-onizleme.html").exists():
        html.append(str(proje.cikti / "demo-onizleme.html"))
    sonuclar.append(_adim("HTML içi JS sözdizimi", lambda: subprocess.run(
        ["node", "js-kontrol.mjs", *html], cwd=oynatici, check=True, capture_output=True)))

    if not all(sonuclar):
        raise PipelineHatasi(f"{sonuclar.count(False)} kontrol başarısız.")
    print("Tüm kontroller geçti.")
