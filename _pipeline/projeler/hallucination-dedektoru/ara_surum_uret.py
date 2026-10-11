"""Ara sürümleri tam çözümden türetir (yönerge §5.2: ara sürümler elle yazılmaz).

Kullanım (repo kökünden):  python _pipeline/projeler/hallucination-dedektoru/ara_surum_uret.py
Son adımdan geriye doğru gidilir: her adımda o adımın eklediği fonksiyonlar, sabitler ve parser
satırları çıkarılır; değişen fonksiyonlar (main, cmd_verify, print_verdicts) adıma özgü hâlleriyle
değiştirilir. Çıktı: cozum/adim_1.py … cozum/adim_6.py
"""

import ast
import re
from pathlib import Path

KLASOR = Path(__file__).resolve().parents[3] / "hallucination-dedektoru"
TAM = KLASOR / "cozum" / "dedektor.py"

DOCSTRINGS = {
    6: '''"""Hallucination dedektörü — Adım 6: zincir ve kayıt.

answer, extract ve verify adımları chain komutuyla uç uca bağlanır; her çalıştırma sonuclar/zincir.jsonl
dosyasına kaydedilir. --answer ile hazır (ör. tuzaklı) bir yanıt verilirse üretim atlanır.

Kullanım:
    python calisma/dedektor.py chain kaynaklar/03_webhook_ve_hatalar.md sorular/03_webhook_imza.txt
    python calisma/dedektor.py chain kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt --answer tuzaklar/01_iptal_tuzakli.md
"""''',
    5: '''"""Hallucination dedektörü — Adım 5: risk skoru ve yönlendirme.

verify komutu kararları bir risk skoruna çevirir ve yanıtı KABUL / İNCELE / RET olarak yönlendirir.

Kullanım:
    python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
    python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json --threshold 0.5
"""''',
    4: '''"""Hallucination dedektörü — Adım 4: kanıt denetimi.

verify komutu, modelin gösterdiği kanıt alıntısının kaynakta birebir geçip geçmediğini kontrol eder;
kanıtı kaynakta olmayan DESTEKLİ kararlar ŞÜPHELİ olur.

Kullanım:
    python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
"""''',
    3: '''"""Hallucination dedektörü — Adım 3: iddia doğrulama.

verify komutu iddia listesini kaynağa karşı değerlendirir: her iddia için karar, kanıt alıntısı ve gerekçe.

Kullanım:
    python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
"""''',
    2: '''"""Hallucination dedektörü — Adım 2: iddia çıkarma.

extract komutu bir yanıtı doğrulanabilir atomik iddialara ayırır ve JSON dosyasına yazar.

Kullanım:
    python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
    python calisma/dedektor.py extract sonuclar/01_iptal.md
"""''',
    1: '''"""Hallucination dedektörü — Adım 1: kaynağa dayalı yanıt.

answer komutu bir kaynak doküman ve bir soru alır, üretici modelden yanıtı ister, yanıtı dosyaya yazar
ve çağrının token sayılarıyla maliyetini gösterir.

Kullanım:
    python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
"""''',
}

# Her adımda çıkarılacak üst düzey tanımlar (fonksiyon ya da sabit adı). Adım N dosyası = adım N+1 dosyası − bunlar.
CIKAR = {
    6: ["TRAP_EXPECTATIONS", "load_traps", "load_records", "match_claims", "judge_trap", "cmd_score"],
    5: ["DEFAULT_CHAIN_PATH", "cmd_chain", "save_record"],
    4: ["RISK_WEIGHTS", "ROUTE_ACCEPT", "DEFAULT_THRESHOLD", "risk_score", "route", "fmt_score", "print_summary"],
    3: ["tr_lower", "normalize_text", "evidence_found", "apply_evidence_check"],
    2: ["VERDICT_LABELS", "VERIFY_PROMPT", "load_claims", "verify_claims", "shorten", "print_table", "print_verdicts", "cmd_verify"],
    1: ["EXTRACT_PROMPT", "extract_claims", "_parse_json", "claims_path", "cmd_extract"],
}

# Her adımda silinecek import satırları
IMPORT_CIKAR = {5: ["from datetime import datetime"], 1: ["import json", "import re"]}

# build_parser içinden çıkarılacak satırlar: (adım, satırın başlangıcı) — blok başlığı ise boş satıra kadar
PARSER_CIKAR = {
    6: ["p_score"],
    5: ["p_chain"],
    4: ['p_verify.add_argument("--threshold"'],
    2: ["p_verify"],
    1: ["p_extract", 'parser.add_argument("--verifier"'],
}

MAIN = {
    6: '''def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        commands = {"answer": cmd_answer, "extract": cmd_extract, "verify": cmd_verify, "chain": cmd_chain}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2''',
}
MAIN[5] = MAIN[6].replace(', "chain": cmd_chain', "")
MAIN[2] = MAIN[5].replace(', "verify": cmd_verify', "")
MAIN[1] = MAIN[2].replace(', "extract": cmd_extract', "").replace(", json.JSONDecodeError", "")

CMD_VERIFY = {
    4: '''def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    source = read_text(args.source)
    verdicts, result = verify_claims(client, model, source, load_claims(args.claims))
    apply_evidence_check(verdicts, source)
    print_verdicts(verdicts)
    print()
    print(fmt_usage(result, model))
    return 0''',
    3: '''def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    verdicts, result = verify_claims(client, model, read_text(args.source), load_claims(args.claims))
    print_verdicts(verdicts)
    print()
    print(fmt_usage(result, model))
    return 0''',
}

PRINT_VERDICTS_3 = '''def print_verdicts(verdicts: list[dict]) -> None:
    """Doğrulama tablosu: iddia, karar, kanıt alıntısı ve gerekçe."""
    rows = []
    for i, row in enumerate(verdicts, start=1):
        evidence = shorten(row["kanit"], 40) if row["kanit"] else "-"
        rows.append([str(i), shorten(row["iddia"], 56), VERDICT_LABELS[row["karar"]], evidence, shorten(row["not"], 44)])
    print_table(["#", "İddia", "Karar", "Kanıt", "Not"], rows, right_align={0})'''


def tanim_araliklari(kaynak: str) -> dict[str, tuple[int, int]]:
    """Üst düzey tanım adı → (ilk satır, son satır); sabitlerde üstteki yorum satırları dahil (1 tabanlı)."""
    satirlar = kaynak.split("\n")
    sonuc = {}
    for dugum in ast.parse(kaynak).body:
        if isinstance(dugum, ast.FunctionDef):
            sonuc[dugum.name] = (dugum.lineno, dugum.end_lineno)
        elif isinstance(dugum, ast.Assign):
            bas = dugum.lineno
            while bas > 1 and satirlar[bas - 2].startswith("#"):
                bas -= 1
            for hedef in dugum.targets:
                for ad in (getattr(hedef, "id", None),) if not isinstance(hedef, ast.Tuple) else (e.id for e in hedef.elts):
                    if ad:
                        sonuc[ad] = (bas, dugum.end_lineno)
    return sonuc


def sil(kaynak: str, adlar: list[str]) -> str:
    araliklar = tanim_araliklari(kaynak)
    satirlar = kaynak.split("\n")
    silinecek = set()
    for ad in adlar:
        a, b = araliklar[ad]
        silinecek.update(range(a - 1, b))
        # tanımdan sonraki boş satırları da sil (iki boş satır kuralı korunur)
        k = b
        while k < len(satirlar) and not satirlar[k].strip():
            silinecek.add(k)
            k += 1
    return "\n".join(s for i, s in enumerate(satirlar) if i not in silinecek)


def degistir(kaynak: str, ad: str, yeni: str) -> str:
    a, b = tanim_araliklari(kaynak)[ad]
    satirlar = kaynak.split("\n")
    return "\n".join(satirlar[: a - 1] + yeni.split("\n") + satirlar[b:])


def parser_sil(kaynak: str, baslangiclar: list[str]) -> str:
    a, b = tanim_araliklari(kaynak)["build_parser"]
    satirlar = kaynak.split("\n")
    govde = satirlar[a - 1: b]
    for bas in baslangiclar:
        if bas.startswith("p_") and "add_argument" not in bas:
            # blok: "p_x = sub.add_parser" ile başlayıp bir sonraki boş satıra kadar, önündeki boş satırla birlikte
            i = next(k for k, s in enumerate(govde) if s.strip().startswith(bas + " = "))
            j = i
            while j < len(govde) and govde[j].strip().startswith(bas):
                j += 1
            del govde[i - 1: j]
        else:
            govde = [s for s in govde if not s.strip().startswith(bas)]
    return "\n".join(satirlar[: a - 1] + govde + satirlar[b:])


def bos_bolumleri_temizle(kaynak: str) -> str:
    """İçi boşalan bölüm başlıklarını (# ---- / # Ad / # ----) kaldırır."""
    desen = re.compile(r"# -{10,}\n# [^\n]+\n# -{10,}\n\n+(?=# -{10,}\n# )")
    kaynak = desen.sub("", kaynak)
    kaynak = re.sub(r"\n+(# -{10,}\n# )", r"\n\n\n\1", kaynak)
    return re.sub(r"\n{4,}", "\n\n\n", kaynak)


def docstring_degistir(kaynak: str, yeni: str) -> str:
    agac = ast.parse(kaynak)
    son = agac.body[0].end_lineno
    return "\n".join([yeni] + kaynak.split("\n")[son:])


def main():
    kod = TAM.read_text(encoding="utf-8")
    for adim in range(6, 0, -1):
        kod = sil(kod, CIKAR[adim])
        for satir in IMPORT_CIKAR.get(adim, []):
            kod = kod.replace(satir + "\n", "")
        kod = parser_sil(kod, PARSER_CIKAR.get(adim, []))
        if adim in MAIN:
            kod = degistir(kod, "main", MAIN[adim])
        if adim in CMD_VERIFY:
            kod = degistir(kod, "cmd_verify", CMD_VERIFY[adim])
        if adim == 3:
            kod = degistir(kod, "print_verdicts", PRINT_VERDICTS_3)
        kod = bos_bolumleri_temizle(docstring_degistir(kod, DOCSTRINGS[adim]))
        hedef = KLASOR / "cozum" / f"adim_{adim}.py"
        hedef.write_text(kod.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
        print(f"Yazıldı: {hedef.relative_to(KLASOR)} ({len(kod.splitlines())} satır)")


if __name__ == "__main__":
    main()
