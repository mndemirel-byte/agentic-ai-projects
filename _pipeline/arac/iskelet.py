"""İskelet aşaması: yeni bir proje için repo klasörünü ve pipeline girdi dosyalarını oluşturur.

Var olan dosyaların üzerine yazmaz. Doldurulacak yerler, referans projeye
(_pipeline/projeler/token-maliyet-hesaplayici/) bakılarak yazılır.
"""

from ortak import PIPELINE, REPO

REFERANS = "_pipeline/projeler/token-maliyet-hesaplayici/"

DOSYALAR = {
    "repo": {
        "calisma/README.md": "# Çalışma klasörü\n\nKendi kodunu bu klasörde, [Step-by-Step-GUIDE.md](../Step-by-Step-GUIDE.md) rehberini takip ederek yazacaksın.\n",
        "cozum/.gitkeep": "",
        "tests/.gitkeep": "",
        "ornekler/.gitkeep": "",
        ".gitignore": ".venv/\n__pycache__/\n*.pyc\n.env\n",
    },
    "girdi": {
        "proje.yaml": f"# Doldurma rehberi: {REFERANS}proje.yaml\nslug: {{slug}}\nbaslik: \nyazim_modu: manuel\ndemo_kind: terminal\ncozum: cozum/\nara_surumler: []\nolcum:\n  hazirlik: []\n  calistirmalar: []\n  gosterim: {{}}\n  sahte_istemci: sahte_istemci.py\nicerik:\n  - {{sablon: project.template.mdx, hedef: project.mdx, yer: platform}}\n  - {{sablon: guide.template.md, hedef: Step-by-Step-GUIDE.md, yer: repo}}\ndemo:\n  baslik: \n  parser_fonksiyonu: build_parser\n  dosya_alanlari: []\n  varsayilan_etiketleri: {{}}\n  sahneler: []\n  parametreler: {{}}\n",
        "adimlar.yaml": f"# Doldurma rehberi: {REFERANS}adimlar.yaml\nbaslangic: cozum/adim_1.py\nadimlar: []\n",
        "kod_rehberi.yaml": f"# Doldurma rehberi: {REFERANS}kod_rehberi.yaml\ndipnot: \nbolumler: []\nparcalar: []\n",
        "akis_rehberi.yaml": f"# Doldurma rehberi: {REFERANS}akis_rehberi.yaml\nbaslik: \ngiris: \nbloklar: []\nortak_adimlar: []\nakislar: []\n",
        "project.template.mdx": f"{{/* Doldurma rehberi: {REFERANS}project.template.mdx ve yönerge §3 */}}\n",
        "guide.template.md": f"<!-- Doldurma rehberi: {REFERANS}guide.template.md ve yönerge §4 -->\n",
        "sahte_istemci.py": f'"""Önizleme ölçümü için sahte istemci. Örnek: {REFERANS}sahte_istemci.py"""\n',
    },
}


def calistir(slug: str) -> None:
    hedefler = {"repo": REPO / slug, "girdi": PIPELINE / "projeler" / slug}
    for alan, dosyalar in DOSYALAR.items():
        for goreli, icerik in dosyalar.items():
            yol = hedefler[alan] / goreli
            if yol.exists():
                print(f"[var]  {yol.relative_to(REPO)}")
                continue
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(icerik.replace("{slug}", slug), encoding="utf-8", newline="\n")
            print(f"[yeni] {yol.relative_to(REPO)}")
