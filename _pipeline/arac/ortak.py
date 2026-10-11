"""Pipeline modüllerinin paylaştığı yardımcılar: yollar, proje yapılandırması, Python kaynak çözümleme."""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
REPO = PIPELINE.parent


class PipelineHatasi(Exception):
    """Kullanıcıya tek satırlık mesajla gösterilecek pipeline hatası."""


@dataclass
class Proje:
    slug: str
    ayar: dict

    @property
    def klasor(self) -> Path:
        """Öğrencinin gördüğü proje klasörü: agentic-ai-projects/{slug}/"""
        return REPO / self.slug

    @property
    def girdi(self) -> Path:
        """Projeye özgü pipeline girdileri: _pipeline/projeler/{slug}/"""
        return PIPELINE / "projeler" / self.slug

    @property
    def cikti(self) -> Path:
        """Platforma kopyalanacak çıktılar: _pipeline/cikti/{slug}/"""
        yol = PIPELINE / "cikti" / self.slug
        yol.mkdir(parents=True, exist_ok=True)
        return yol

    def yol(self, goreli: str) -> Path:
        return self.klasor / goreli

    def kaynak(self, goreli: str) -> str:
        return self.yol(goreli).read_text(encoding="utf-8")


def proje_yukle(slug: str) -> Proje:
    dosya = PIPELINE / "projeler" / slug / "proje.yaml"
    if not dosya.exists():
        raise PipelineHatasi(f"{dosya.relative_to(REPO)} bulunamadı.")
    ayar = yaml.safe_load(dosya.read_text(encoding="utf-8"))
    if ayar.get("slug") != slug:
        raise PipelineHatasi(f"proje.yaml içindeki slug ({ayar.get('slug')}) klasör adıyla ({slug}) eşleşmiyor.")
    return Proje(slug, ayar)


def modul_yukle(yol: Path):
    """Bir Python dosyasını modül olarak yükler (ör. build_parser'a erişmek için)."""
    import importlib.util

    sys.path.insert(0, str(yol.parent))
    spec = importlib.util.spec_from_file_location(yol.stem + "_pipeline", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# ---------------------------------------------------------------------------
# Python kaynak çözümleme: fonksiyon, sabit ve import bloğu çıkarma
# ---------------------------------------------------------------------------

def fonksiyon(kaynak: str, ad: str) -> str:
    for dugum in ast.parse(kaynak).body:
        if isinstance(dugum, ast.FunctionDef) and dugum.name == ad:
            return ast.get_source_segment(kaynak, dugum)
    raise PipelineHatasi(f"Fonksiyon bulunamadı: {ad}")


def fonksiyon_satirlari(kaynak: str, ad: str) -> tuple[int, int]:
    for dugum in ast.parse(kaynak).body:
        if isinstance(dugum, ast.FunctionDef) and dugum.name == ad:
            return dugum.lineno, dugum.end_lineno
    raise PipelineHatasi(f"Fonksiyon bulunamadı: {ad}")


def _hedef_adlari(dugum: ast.Assign) -> list[str]:
    """Bir atamanın hedef adları; 'A, B = ...' biçimindeki çoklu atamada tüm adlar."""
    adlar = []
    for hedef in dugum.targets:
        for parca in (hedef.elts if isinstance(hedef, ast.Tuple) else [hedef]):
            if getattr(parca, "id", None):
                adlar.append(parca.id)
    return adlar


def sabit(kaynak: str, ad: str) -> str:
    """Bir atamayı, hemen üstündeki yorum satırlarıyla birlikte döndürür."""
    satirlar = kaynak.split("\n")
    for dugum in ast.parse(kaynak).body:
        if isinstance(dugum, ast.Assign) and ad in _hedef_adlari(dugum):
            bas = dugum.lineno - 1
            while bas > 0 and satirlar[bas - 1].startswith("#"):
                bas -= 1
            return "\n".join(satirlar[bas:dugum.end_lineno])
    raise PipelineHatasi(f"Sabit bulunamadı: {ad}")


def bas_blok(kaynak: str) -> str:
    """Modül docstring'inden sonraki import ve sabit bloğu (ilk bölüm başlığına ya da fonksiyona kadar)."""
    satirlar = kaynak.split("\n")
    agac = ast.parse(kaynak)
    bas = agac.body[1].lineno - 1 if isinstance(agac.body[0], ast.Expr) else 0
    son = next(i for i, s in enumerate(satirlar) if i > bas and (s.startswith("# ----") or s.startswith("def ")))
    blok = satirlar[bas:son]
    while blok and not blok[-1].strip():
        blok.pop()
    return "\n".join(blok)


def bolumler(kaynak: str) -> list[tuple[str, int, int]]:
    """'# ----' / '# Ad' / '# ----' biçimli bölüm başlıklarını (ad, ilk satır, son satır) olarak döndürür."""
    satirlar = kaynak.rstrip("\n").split("\n")
    bulunan = []
    for i in range(len(satirlar) - 2):
        if satirlar[i].startswith("# ----") and satirlar[i + 2].startswith("# ----") and satirlar[i + 1].startswith("# "):
            bulunan.append((satirlar[i + 1][2:].strip(), i + 1))
    sonuc = []
    for k, (ad, bas) in enumerate(bulunan):
        son = bulunan[k + 1][1] - 1 if k + 1 < len(bulunan) else len(satirlar)
        while son > bas and not satirlar[son - 1].strip():
            son -= 1
        sonuc.append((ad, bas, son))
    return sonuc
