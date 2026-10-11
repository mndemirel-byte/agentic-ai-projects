"""Hallucination dedektörü — Adım 1: kaynağa dayalı yanıt.

answer komutu bir kaynak doküman ve bir soru alır, üretici modelden yanıtı ister, yanıtı dosyaya yazar
ve çağrının token sayılarıyla maliyetini gösterir.

Kullanım:
    python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
"""

import argparse
import math
import os
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


# ---------------------------------------------------------------------------
# Prompt'lar
# ---------------------------------------------------------------------------

GENERATE_SYSTEM = (
    "Sen bir teknik destek asistanısın. Kullanıcının sorusunu, sana verilen dokümana dayanarak Türkçe "
    "cevapla. Cevabın kısa ve net olsun; en fazla bir paragraf yaz, liste kullanma."
)


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


# ---------------------------------------------------------------------------
# Hesaplamalar
# ---------------------------------------------------------------------------

def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına (Ders 1.4 §6.2)."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000


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


# ---------------------------------------------------------------------------
# Kayıt (JSONL: her satır bir zincir çalıştırması)
# ---------------------------------------------------------------------------

def answer_path(question_path: str) -> Path:
    stem = Path(question_path).stem if Path(question_path).is_file() else "yanit"
    return DEFAULT_RESULTS_DIR / f"{stem}.md"


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


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedektor", description="LLM yanıtını iddialara ayır, kaynağa karşı doğrula, risk skoruna göre yönlendir.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat ve model dosyası (varsayılan: pricing.yaml)")
    parser.add_argument("--generator", help="Üretici model anahtarı (varsayılan: pricing.yaml > roller > uretici)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_answer = sub.add_parser("answer", help="Kaynağa dayalı yanıt üret ve dosyaya yaz (ücretli)")
    p_answer.add_argument("source", help="Kaynak doküman (Markdown ya da düz metin)")
    p_answer.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_answer.add_argument("--out", help="Yanıt dosyası (varsayılan: sonuclar/<soru dosyası adı>.md)")
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
        commands = {"answer": cmd_answer}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
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
