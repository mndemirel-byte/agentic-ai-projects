"""Ekran aşaması: üretilen sayfaların açık/koyu tema, masaüstü/mobil ekran görüntülerini alır.

Görüntüler _pipeline/cikti/{slug}/ekran/ altına yazılır ve gözle kontrol edilir. Sayfa yatay
taşıyorsa ya da konsolda hata varsa aşama başarısız olur. Playwright gerektirir.
"""

from ortak import PipelineHatasi, Proje

GORUNUMLER = [("masaustu", 1280, 900), ("mobil", 390, 844)]


def calistir(proje: Proje, onizleme: bool = False) -> None:
    from playwright.sync_api import sync_playwright

    sayfalar = [proje.yol(a) for a in ("kod-rehberi.html", "kod-rehberi-yan-yana.html", "demo.html")]
    if onizleme:
        sayfalar.append(proje.cikti / "demo-onizleme.html")
    sayfalar = [s for s in sayfalar if s.exists()]
    hedef = proje.cikti / "ekran"
    hedef.mkdir(exist_ok=True)
    sorunlar = []
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        for sayfa_yolu in sayfalar:
            for ad, gen, yuk in GORUNUMLER:
                for tema in ("light", "dark"):
                    sayfa = tarayici.new_page(viewport={"width": gen, "height": yuk}, color_scheme=tema,
                                              reduced_motion="reduce")
                    hatalar = []
                    sayfa.on("pageerror", lambda e: hatalar.append(str(e)))
                    sayfa.goto(sayfa_yolu.as_uri())
                    sayfa.wait_for_timeout(400)
                    genislik = sayfa.evaluate("document.documentElement.scrollWidth")
                    dosya = hedef / f"{sayfa_yolu.stem}-{ad}-{tema}.png"
                    sayfa.screenshot(path=str(dosya), full_page=ad == "masaustu")
                    if genislik > gen:
                        sorunlar.append(f"{dosya.name}: yatay taşma ({genislik}px)")
                    sorunlar += [f"{dosya.name}: {h}" for h in hatalar]
                    sayfa.close()
        tarayici.close()
    print(f"Ekran görüntüleri: {hedef}")
    if sorunlar:
        raise PipelineHatasi("; ".join(sorunlar))
