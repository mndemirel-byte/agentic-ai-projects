"""Hallucination dedektörü — Adım 3: iddia doğrulama.

verify komutu iddia listesini kaynağa karşı değerlendirir: her iddia için karar, kanıt alıntısı ve gerekçe.

Kullanım:
    python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
"""

import argparse
import json
import math
import os
import re
import sys
import textwrap
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"
REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok")

# Her çağrı için çıktı sınırı. Yanıt kısa tutulur; iddia listesi ve doğrulama JSON'u daha uzun olabilir.
MAX_TOKENS = {"answer": 600, "extract": 800, "verify": 1500}

# Doğrulayıcının döndürdüğü karar anahtarları ve ekrandaki Türkçe etiketleri.
VERDICT_LABELS = {"supported": "DESTEKLİ", "unsupported": "DESTEKSİZ", "contradicted": "ÇELİŞİYOR", "suspect": "ŞÜPHELİ"}


# ---------------------------------------------------------------------------
# Prompt'lar
# ---------------------------------------------------------------------------

GENERATE_SYSTEM = (
    "Sen bir teknik destek asistanısın. Kullanıcının sorusunu, sana verilen dokümana dayanarak Türkçe "
    "cevapla. Cevabın kısa ve net olsun; en fazla bir paragraf yaz, liste kullanma."
)

EXTRACT_PROMPT = """<yanit> etiketleri arasındaki metin, bir teknik destek asistanının bir dokümana dayanarak \
verdiği yanıttır. Bu yanıtı doğrulanabilir atomik iddialara ayır.

Kurallar:
- Her iddia tek bir olgu içersin ve tek başına anlaşılsın (zamir yerine adı yaz).
- Yanıttaki her olgusal ifadeyi bir iddia yap; görüş, öneri ve nezaket cümlelerini atla.
- Yanıt "dokümanda belirtilmiyor" gibi bir boşluğu kabul eden cümleler içerebilir; bunları da iddia olarak yaz \
(ör. "Doküman imzanın geçerlilik süresini belirtmez.").
- Yanıtın içeriğini yorumlama, değerlendirme ya da düzeltme; görevin yalnızca onu iddialara bölmek.
- En fazla 10 iddia çıkar; iddiaları yanıttaki sırayla yaz.
- Yalnızca şu biçimde JSON döndür, başka hiçbir şey yazma:
{"claims": ["iddia 1", "iddia 2"]}

<yanit>
{answer}
</yanit>"""

VERIFY_PROMPT = """Aşağıdaki iddiaların her birini yalnızca KAYNAK dokümana göre değerlendir. Kendi bilgini kullanma; \
kaynakta olmayan bir bilgi doğru görünse bile "unsupported" say.

Her iddia için:
- verdict: "supported" (kaynak açıkça söylüyor ya da kaynaktaki bir ifadenin doğrudan sonucu), "contradicted" \
(kaynak aksini söylüyor) ya da "unsupported" (kaynakta bu konuda bilgi yok ya da yetersiz).
- evidence: kararı dayandırdığın cümle ya da cümle parçası, KAYNAKTAN BİREBİR kopyalanmış olarak. \
"unsupported" için boş bırak.
- note: tek cümlelik gerekçe.

Yalnızca şu biçimde JSON döndür, başka hiçbir şey yazma:
{"results": [{"id": 1, "verdict": "supported", "evidence": "...", "note": "..."}]}

KAYNAK:
\"\"\"
{source}
\"\"\"

İDDİALAR:
{claims}"""


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_pricing(path: Path) -> dict:
    """pricing.yaml dosyasını okur; zorunlu alanları ve rol atamalarını doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for model in data["models"]:
        missing = [field for field in REQUIRED_MODEL_FIELDS if field not in model]
        if missing:
            raise ValueError(f"pricing.yaml: '{model.get('key', '?')}' modelinde eksik alan: {', '.join(missing)}")
    for role in ("uretici", "dogrulayici"):
        if role not in data.get("roller", {}):
            raise ValueError(f"pricing.yaml: 'roller' altında '{role}' tanımlı değil.")
    return data


def select_model(pricing: dict, key: str | None, role: str) -> dict:
    """Komut satırında verilen anahtarı, verilmediyse pricing.yaml'daki rol atamasını kullanarak modeli seçer."""
    key = key or pricing["roller"][role]
    by_key = {m["key"]: m for m in pricing["models"]}
    if key not in by_key:
        raise ValueError(f"Bilinmeyen model anahtarı: '{key}'. Geçerli anahtarlar: {', '.join(by_key)}")
    return by_key[key]


def read_text(path: str) -> str:
    """Bir metin dosyasını UTF-8 olarak okur; boş dosyayı reddeder."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path}: dosya boş.")
    return text


def read_question(value: str) -> str:
    """Soru bir dosya yoluysa dosyadan okunur; değilse metnin kendisi sorudur."""
    if Path(value).is_file():
        return read_text(value)
    return value.strip()


def load_claims(path: str) -> list[str]:
    """extract komutunun yazdığı iddia dosyasını okur."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    claims = data.get("claims") if isinstance(data, dict) else None
    if not claims or not all(isinstance(c, str) and c.strip() for c in claims):
        raise ValueError(f"{path}: 'claims' listesi boş ya da hatalı. Önce 'extract' komutunu çalıştır.")
    return claims


# ---------------------------------------------------------------------------
# API çağrıları
# ---------------------------------------------------------------------------

def call_model(client, model: dict, prompt: str, max_tokens: int, system: str | None = None) -> dict:
    """Tek bir non-streaming çağrı yapar; metni, token sayılarını ve durma nedenini döndürür.

    Modelin `cagri_ayarlari` sözlüğü (pricing.yaml) isteğe olduğu gibi eklenir; kod ayarların
    içeriğini bilmez. Yanıt bütün olarak işleneceği için streaming gerekmez (Ders 1.4 §4.4).
    """
    kwargs = {"model": model["id"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    kwargs.update(model.get("cagri_ayarlari") or {})
    message = client.messages.create(**kwargs)
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    return {
        "text": text.strip(),
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "stop_reason": message.stop_reason,
    }


def generate_answer(client, model: dict, source: str, question: str) -> dict:
    """Üretici modelden kaynağa dayalı yanıt alır."""
    prompt = f"DOKÜMAN:\n\"\"\"\n{source}\n\"\"\"\n\nSORU: {question}"
    return call_model(client, model, prompt, MAX_TOKENS["answer"], GENERATE_SYSTEM)


def extract_claims(client, model: dict, answer: str) -> tuple[list[str], dict]:
    """Zincirin 1. aşaması: yanıtı atomik iddialara ayırır. JSON çözülemezse hata verir."""
    result = call_model(client, model, EXTRACT_PROMPT.replace("{answer}", answer), MAX_TOKENS["extract"])
    parsed = _parse_json(result["text"])
    claims = parsed.get("claims") if isinstance(parsed, dict) else None
    if not isinstance(claims, list) or not claims or not all(isinstance(c, str) and c.strip() for c in claims):
        raise ValueError("İddia çıkarma: model geçerli bir {\"claims\": [...]} JSON'u döndürmedi. Yanıt: "
                         + result["text"][:120].replace("\n", " "))
    return [c.strip() for c in claims], result


def verify_claims(client, model: dict, source: str, claims: list[str]) -> tuple[list[dict], dict]:
    """Zincirin 2. aşamasının LLM yarısı: her iddiayı kaynağa karşı değerlendirir."""
    numbered = "\n".join(f"{i}. {claim}" for i, claim in enumerate(claims, start=1))
    prompt = VERIFY_PROMPT.replace("{source}", source).replace("{claims}", numbered)
    result = call_model(client, model, prompt, MAX_TOKENS["verify"])
    parsed = _parse_json(result["text"])
    rows = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) != len(claims):
        raise ValueError(f"Doğrulama: model {len(claims)} iddia için {len(rows) if isinstance(rows, list) else 0} "
                         "sonuç döndürdü; geçerli JSON bekleniyordu.")
    verdicts = []
    for claim, row in zip(claims, rows):
        verdict = str(row.get("verdict", "")).strip().lower()
        if verdict not in ("supported", "unsupported", "contradicted"):
            raise ValueError(f"Doğrulama: bilinmeyen karar '{verdict}' (iddia: {claim[:60]})")
        verdicts.append({"iddia": claim, "karar": verdict, "kanit": str(row.get("evidence") or "").strip(),
                         "not": str(row.get("note") or "").strip()})
    return verdicts, result


# ---------------------------------------------------------------------------
# Hesaplamalar
# ---------------------------------------------------------------------------

def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına (Ders 1.4 §6.2)."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000


def _parse_json(text: str):
    """Model çıktısındaki JSON'u çözer; kod bloğu çitlerini (```json ... ```) ve JSON'un çevresindeki metni atar.

    Çözülemezse None döner. Önce metnin tamamı, sonra ilk '{' ile son '}' arasındaki parça denenir;
    böylece "İşte iddialar:" gibi bir giriş cümlesi ayrıştırmayı bozmaz.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned)
    candidates = [cleaned]
    if "{" in cleaned and "}" in cleaned:
        candidates.append(cleaned[cleaned.find("{"): cleaned.rfind("}") + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------------------
# Biçimlendirme (Türkçe sayı yazımı: binlik ayırıcı nokta, ondalık virgül)
# ---------------------------------------------------------------------------

def _tr_number(formatted: str) -> str:
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_int(n: int) -> str:
    return _tr_number(f"{n:,}")


def fmt_usd(x: float) -> str:
    if x == 0:
        return "$0"
    # 1 doların altındaki tutarlarda ilk anlamlı basamaktan sonra bir basamak daha göster: 0,0035 → $0,0035
    decimals = 2 if x >= 1 else min(8, -math.floor(math.log10(x)) + 1)
    return "$" + _tr_number(f"{x:,.{decimals}f}")


def fmt_usage(result: dict, model: dict) -> str:
    """Bir çağrının özet satırı: model, token sayıları, maliyet ve durma nedeni."""
    cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
    cut = "  |  UYARI: yanıt max_tokens sınırında kesildi" if result["stop_reason"] == "max_tokens" else ""
    return (f"{model['name']}  |  girdi {fmt_int(result['input_tokens'])} token, çıktı "
            f"{fmt_int(result['output_tokens'])} token  |  {fmt_usd(cost)}{cut}")


def wrap_text(text: str, width: int = 100) -> str:
    """Uzun bir paragrafı terminalde okunur satırlara böler; dosyaya yazılan metin değişmez."""
    return "\n".join(textwrap.fill(p, width) for p in text.splitlines() if p.strip())


def shorten(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def print_table(headers: list[str], rows: list[list[str]], right_align: set[int] = frozenset()) -> None:
    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]

    def line(cells):
        parts = []
        for i, cell in enumerate(cells):
            parts.append(str(cell).rjust(widths[i]) if i in right_align else str(cell).ljust(widths[i]))
        return "  ".join(parts).rstrip()

    print(line(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(line(row))


def print_verdicts(verdicts: list[dict]) -> None:
    """Doğrulama tablosu: iddia, karar, kanıt alıntısı ve gerekçe."""
    rows = []
    for i, row in enumerate(verdicts, start=1):
        evidence = shorten(row["kanit"], 40) if row["kanit"] else "-"
        rows.append([str(i), shorten(row["iddia"], 56), VERDICT_LABELS[row["karar"]], evidence, shorten(row["not"], 44)])
    print_table(["#", "İddia", "Karar", "Kanıt", "Not"], rows, right_align={0})


# ---------------------------------------------------------------------------
# Kayıt (JSONL: her satır bir zincir çalıştırması)
# ---------------------------------------------------------------------------

def answer_path(question_path: str) -> Path:
    stem = Path(question_path).stem if Path(question_path).is_file() else "yanit"
    return DEFAULT_RESULTS_DIR / f"{stem}.md"


def claims_path(answer_file: str) -> Path:
    return DEFAULT_RESULTS_DIR / f"{Path(answer_file).stem}.iddialar.json"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def shown(path: Path) -> str:
    """Yolu proje klasörüne göre, ters bölü kullanmadan yazar."""
    return (path.relative_to(PROJECT_DIR) if path.is_relative_to(PROJECT_DIR) else path).as_posix()


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_answer(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.generator, "uretici")
    source, question = read_text(args.source), read_question(args.question)
    result = generate_answer(client, model, source, question)
    out = Path(args.out) if args.out else answer_path(args.question)
    write_text(out, result["text"])
    print(f"Soru: {question}")
    print()
    print(wrap_text(result["text"]))
    print()
    print(fmt_usage(result, model))
    print(f"Yanıt kaydedildi: {shown(out)}")
    return 0


def cmd_extract(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    claims, result = extract_claims(client, model, read_text(args.answer))
    out = Path(args.out) if args.out else claims_path(args.answer)
    write_text(out, json.dumps({"claims": claims}, ensure_ascii=False, indent=2))
    print(f"{len(claims)} iddia çıkarıldı:")
    for i, claim in enumerate(claims, start=1):
        print(f"  {i}. {claim}")
    print()
    print(fmt_usage(result, model))
    print(f"İddialar kaydedildi: {shown(out)}")
    return 0


def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    verdicts, result = verify_claims(client, model, read_text(args.source), load_claims(args.claims))
    print_verdicts(verdicts)
    print()
    print(fmt_usage(result, model))
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedektor", description="LLM yanıtını iddialara ayır, kaynağa karşı doğrula, risk skoruna göre yönlendir.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat ve model dosyası (varsayılan: pricing.yaml)")
    parser.add_argument("--generator", help="Üretici model anahtarı (varsayılan: pricing.yaml > roller > uretici)")
    parser.add_argument("--verifier", help="Doğrulayıcı model anahtarı (varsayılan: pricing.yaml > roller > dogrulayici)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_answer = sub.add_parser("answer", help="Kaynağa dayalı yanıt üret ve dosyaya yaz (ücretli)")
    p_answer.add_argument("source", help="Kaynak doküman (Markdown ya da düz metin)")
    p_answer.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_answer.add_argument("--out", help="Yanıt dosyası (varsayılan: sonuclar/<soru dosyası adı>.md)")

    p_extract = sub.add_parser("extract", help="Yanıtı atomik iddialara ayır ve JSON'a yaz (ücretli)")
    p_extract.add_argument("answer", help="answer komutunun yazdığı yanıt dosyası")
    p_extract.add_argument("--out", help="İddia dosyası (varsayılan: sonuclar/<yanıt dosyası adı>.iddialar.json)")

    p_verify = sub.add_parser("verify", help="İddiaları kaynağa karşı doğrula, kanıtı denetle, risk skoru ver (ücretli)")
    p_verify.add_argument("source", help="Kaynak doküman")
    p_verify.add_argument("claims", help="extract komutunun yazdığı iddia dosyası")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        commands = {"answer": cmd_answer, "extract": cmd_extract, "verify": cmd_verify}
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
        return 2


if __name__ == "__main__":
    sys.exit(main())
