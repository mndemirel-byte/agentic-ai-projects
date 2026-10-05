"""Proje hazırlama pipeline'ı.

Kullanım (repo kökünde):
    python _pipeline/arac/pipeline.py <slug> <aşama> [--onizleme]

Aşamalar:
    iskelet     Yeni proje için repo klasörü ve pipeline girdi dosyaları
    olcum       Gerçek API ile ölçüm (yazar çalıştırır). --onizleme: sahte istemciyle temsili ölçüm
    simulasyon  Rehber talimatlarının ara sürümleri ürettiğini doğrular
    rehberler   kod-rehberi.html ve kod-rehberi-yan-yana.html
    demo        demo.json (platform) ve demo.html (repo)
    icerik      project.mdx (platform) ve Step-by-Step-GUIDE.md (repo)
    dogrula     Kontrol paketi
    ekran       Ekran görüntüleri ve taşma kontrolü
    uret        simulasyon + rehberler + demo + icerik + dogrula (ölçüm hariç)

--onizleme: Gerçek ölçüm yokken düzeni görmek içindir. Demo temsili sayılarla üretilir ve
"temsili" etiketi taşır; içerikteki ölçüm blokları boş bırakılır. Önizleme çıktıları teslim edilmez.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import akis  # noqa: E402
import demo  # noqa: E402
import dogrula  # noqa: E402
import ekran  # noqa: E402
import icerik  # noqa: E402
import iskelet  # noqa: E402
import olcum  # noqa: E402
import simulasyon  # noqa: E402
import yan_yana  # noqa: E402
from ortak import PipelineHatasi, proje_yukle  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline", description="Proje hazırlama pipeline'ı")
    parser.add_argument("slug")
    parser.add_argument("asama", choices=["iskelet", "olcum", "simulasyon", "rehberler", "demo", "icerik", "dogrula", "ekran", "uret"])
    parser.add_argument("--onizleme", action="store_true", help="Temsili sayılarla önizleme (teslim edilmez)")
    args = parser.parse_args(argv)

    try:
        if args.asama == "iskelet":
            iskelet.calistir(args.slug)
            return 0
        proje = proje_yukle(args.slug)
        a, o = args.asama, args.onizleme
        if a == "olcum":
            olcum.calistir(proje, o)
        if a in ("simulasyon", "uret"):
            print("== simülasyon"); simulasyon.calistir(proje)
        if a in ("rehberler", "uret"):
            print("== rehberler"); akis.uret(proje); yan_yana.uret(proje)
        if a in ("demo", "uret"):
            print("== demo"); demo.uret(proje, o)
        if a in ("icerik", "uret"):
            print("== içerik"); icerik.uret(proje, o)
        if a in ("dogrula", "uret"):
            print("== doğrulama"); dogrula.calistir(proje, o)
        if a == "ekran":
            ekran.calistir(proje, o)
    except PipelineHatasi as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
