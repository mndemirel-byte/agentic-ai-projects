"""Kod rehberi (yan yana): çözüm dosyası solda, her parçanın açıklaması sağda.

Girdi: _pipeline/projeler/{slug}/kod_rehberi.yaml
  bolumler: renk gruplarının sırası; her biri {anahtar, ad, aciklama}
  parcalar: her biri {capa, fark (ops.), bolum, baslik, aciklama}
Çapa, parçanın başladığı satırın (baştaki boşluklar atılmış) başladığı metindir; dosyada yukarıdan
aşağıya sırayla aranır. fark: -1 parçayı çapanın bir satır üstünden başlatır.
"""

import html

import yaml
from pygments.lexers import PythonLexer
from pygments.token import Token

from ortak import PIPELINE, PipelineHatasi, Proje

PALET = 7  # şablondaki renk grubu sayısı


def _sinif(tt) -> str:
    if tt in Token.Literal.String.Doc: return "sd"
    if tt in Token.Comment: return "c"
    if tt in Token.Literal.String: return "s"
    if tt in Token.Literal.Number: return "m"
    if tt in Token.Keyword or tt in Token.Operator.Word: return "k"
    if tt in Token.Name.Function: return "nf"
    if tt in Token.Name.Builtin: return "nb"
    return ""


def renklendir(kaynak: str) -> list[str]:
    satirlar, simdiki = [], []
    for tt, deger in PythonLexer().get_tokens(kaynak):
        for i, parca in enumerate(deger.split("\n")):
            if i > 0:
                satirlar.append("".join(simdiki)); simdiki = []
            if parca:
                s = _sinif(tt); e = html.escape(parca, quote=False)
                simdiki.append(f'<span class="{s}">{e}</span>' if s else e)
    if simdiki:
        satirlar.append("".join(simdiki))
    return satirlar


def uret(proje: Proje) -> None:
    ayar = yaml.safe_load((proje.girdi / "kod_rehberi.yaml").read_text(encoding="utf-8"))
    dosya = proje.ayar["cozum"]
    kaynak = proje.kaynak(dosya)
    ham = kaynak.split("\n")
    if ham and ham[-1] == "":
        ham.pop()
    renkli = renklendir(kaynak)[: len(ham)]

    bolum_sira = {b["anahtar"]: i for i, b in enumerate(ayar["bolumler"])}
    if len(bolum_sira) > PALET:
        raise PipelineHatasi(f"En fazla {PALET} bölüm desteklenir.")
    bolum = {b["anahtar"]: b for b in ayar["bolumler"]}

    baslar, ara = [], 0
    for parca in ayar["parcalar"]:
        for i in range(ara, len(ham)):
            if ham[i].strip().startswith(parca["capa"]):
                baslar.append(i + 1 + parca.get("fark", 0)); ara = i + 1
                break
        else:
            raise PipelineHatasi(f"Kod rehberi: '{parca['baslik']}' parçasının çapası bulunamadı: {parca['capa']!r}")
    if baslar[0] != 1:
        raise PipelineHatasi("Kod rehberi: ilk parça 1. satırdan başlamalı.")
    baslar.append(len(ham) + 1)

    satirlar, onceki, ton = [], None, {}
    for k, parca in enumerate(ayar["parcalar"]):
        no = list(range(baslar[k], baslar[k + 1]))
        while no and not ham[no[-1] - 1].strip():
            no.pop()
        anahtar = parca["bolum"]
        renk = bolum_sira[anahtar]
        if anahtar != onceki:
            satirlar.append(f'<div class="sec-head t-{renk}" id="b-{anahtar}"><h2>{html.escape(bolum[anahtar]["ad"])}</h2>'
                            f'<p>{bolum[anahtar]["aciklama"]}</p></div>')
            ton[anahtar] = 0; onceki = anahtar
        harf = "a" if ton[anahtar] % 2 == 0 else "b"; ton[anahtar] += 1
        kod = "\n".join(f'<span class="ln">{n}</span>{renkli[n - 1]}' for n in no)
        aralik = f"satır {no[0]}–{no[-1]}" if no[-1] != no[0] else f"satır {no[0]}"
        satirlar.append(f'<div class="seg t-{renk} {harf}"><div class="code"><pre><code>{kod}</code></pre></div>'
                        f'<div class="note"><div class="rng">{aralik}</div><h3>{html.escape(parca["baslik"])}</h3>'
                        f'<p>{parca["aciklama"].strip()}</p></div></div>')

    gosterge = "".join(f'<a class="chip t-{bolum_sira[b["anahtar"]]}" href="#b-{b["anahtar"]}">{html.escape(b["ad"])}</a>'
                       for b in ayar["bolumler"])
    sayfa = ((PIPELINE / "arac" / "sablonlar" / "yan_yana.html").read_text(encoding="utf-8")
             .replace("{{DOSYA}}", html.escape(dosya.split("/")[-1]))
             .replace("{{LEGEND}}", gosterge)
             .replace("{{ROWS}}", "\n".join(satirlar))
             .replace("{{TOTAL}}", str(len(ham)))
             .replace("{{DIPNOT}}", ayar.get("dipnot", "")))
    hedef = proje.yol("kod-rehberi-yan-yana.html")
    hedef.write_text(sayfa, encoding="utf-8", newline="\n")
    print(f"Yazıldı: {hedef.name} ({len(ayar['parcalar'])} parça)")
