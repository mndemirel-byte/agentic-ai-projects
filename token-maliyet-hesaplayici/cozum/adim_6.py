"""Token maliyet hesaplayıcı — Adım 6: Türkçe/İngilizce karşılaştırması.

Bir metni modele göndermeden ÖNCE şu sorulara cevap verir:
  - Bu metin her modelde kaç girdi token'ı tutuyor?
  - Tek çağrı ve aylık hacimde maliyeti ne olur?
  - Modelin context window'unun ne kadarını dolduruyor?
  - Aynı içeriğin Türkçe ve İngilizce hâli arasında token farkı ne?

Kullanım:
    python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt
    python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5,sonnet-5-5 --output-tokens 800
    python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --monthly-calls 100000 --baseline
    python calisma/tokenhesap.py compare ornekler/2_eposta_tr.txt ornekler/2_eposta_en.txt
"""

import argparse
import math
import os
import sys
from pathlib import Path

import anthropic
import yaml

DEFAULT_PRICING_PATH = Path(__file__).resolve().parent.parent / "pricing.yaml"

# Taban ölçümü için kullanılan en kısa anlamlı mesaj. API boş metin kabul etmez.
BASELINE_TEXT = "."

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_pricing(path: Path) -> dict:
    """pricing.yaml dosyasını okur ve zorunlu alanları doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for model in data["models"]:
        missing = [field for field in REQUIRED_MODEL_FIELDS if field not in model]
        if missing:
            raise ValueError(f"pricing.yaml: '{model.get('key', '?')}' modelinde eksik alan: {', '.join(missing)}")
    return data


def select_models(pricing: dict, keys_csv: str | None) -> list[dict]:
    """--models parametresine göre model listesini döndürür (boşsa hepsi)."""
    models = pricing["models"]
    if not keys_csv:
        return models
    by_key = {m["key"]: m for m in models}
    selected = []
    for key in (k.strip() for k in keys_csv.split(",") if k.strip()):
        if key not in by_key:
            valid = ", ".join(by_key)
            raise ValueError(f"Bilinmeyen model anahtarı: '{key}'. Geçerli anahtarlar: {valid}")
        selected.append(by_key[key])
    return selected


def read_text(path: str) -> str:
    """Dosyayı UTF-8 olarak okur; '-' verilirse standart girdiden okur."""
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# API çağrıları
# ---------------------------------------------------------------------------

def build_messages(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def count_input_tokens(client, model_id: str, messages: list[dict]) -> int:
    """Token Counting API ile girdi token sayısını döndürür. Model çalışmaz, ücret yazılmaz."""
    response = client.messages.count_tokens(model=model_id, messages=messages)
    return response.input_tokens


def try_count(client, model: dict, messages: list[dict]) -> tuple[int | None, str | None]:
    """Bir model için sayım yapar; o modele erişim yoksa hatayı tabloya yansıtmak üzere döndürür."""
    try:
        return count_input_tokens(client, model["id"], messages), None
    except anthropic.AuthenticationError:
        raise  # API anahtarı sorunu tüm modelleri etkiler; yukarıda ele alınır
    except anthropic.APIStatusError as e:
        return None, f"HTTP {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "bağlantı hatası"


# ---------------------------------------------------------------------------
# Hesaplamalar
# ---------------------------------------------------------------------------

def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000


def context_ratio(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Girdi + çıktı rezervinin context window'a oranı."""
    return (input_tokens + output_tokens) / model["context_window"]


def usage_label(ratio: float) -> str:
    if ratio > 1:
        return "TAŞMA"
    if ratio >= 0.8:
        return "YÜKSEK"
    if ratio >= 0.5:
        return "DİKKAT"
    return "OK"


def render_bar(ratio: float, width: int = 20) -> str:
    filled = min(width, round(min(ratio, 1.0) * width))
    return "█" * filled + "░" * (width - filled)


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
    if x < 0:
        return "-" + fmt_usd(-x)
    # 1 doların altındaki tutarlarda ilk anlamlı basamaktan sonra bir basamak daha göster:
    # 0,35 → $0,35  |  0,0035 → $0,0035  |  0,00012 → $0,00012
    decimals = 2 if x >= 1 else min(8, -math.floor(math.log10(x)) + 1)
    return "$" + _tr_number(f"{x:,.{decimals}f}")


def fmt_pct(ratio: float, decimals: int = 1) -> str:
    sign = "-" if ratio < 0 else ""
    return sign + "%" + _tr_number(f"{abs(ratio) * 100:.{decimals}f}")


def print_table(headers: list[str], rows: list[list[str]], right_align: set[int]) -> None:
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


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_count(args, client, pricing: dict) -> int:
    text = read_text(args.file)
    models = select_models(pricing, args.models)
    messages = build_messages(text)

    print(f"Dosya: {args.file}  |  {fmt_int(len(text))} karakter, {fmt_int(len(text.split()))} kelime")
    print(f"Çıktı tahmini: {fmt_int(args.output_tokens)} token (cevap + varsa thinking)")
    print()

    headers = ["Model", "Girdi token"]
    if args.baseline:
        headers += ["Taban", "Net"]
    headers += ["Maliyet/çağrı"]
    if args.monthly_calls:
        headers += [f"Aylık ({fmt_int(args.monthly_calls)} çağrı)"]
    headers += ["Context doluluğu"]

    rows, counts, warnings = [], [], []
    for model in models:
        tokens, error = try_count(client, model, messages)
        if error:
            rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
            continue

        counts.append(tokens)
        row = [model["name"], fmt_int(tokens)]
        if args.baseline:
            base, _ = try_count(client, model, build_messages(BASELINE_TEXT))
            row += [fmt_int(base) if base is not None else "-",
                    fmt_int(tokens - base) if base is not None else "-"]

        cost = estimate_cost(model, tokens, args.output_tokens)
        row.append(fmt_usd(cost))
        if args.monthly_calls:
            row.append(fmt_usd(cost * args.monthly_calls))

        ratio = context_ratio(model, tokens, args.output_tokens)
        row.append(f"{render_bar(ratio)} {fmt_pct(ratio)} {usage_label(ratio)}")
        rows.append(row)

        if args.output_tokens > model["max_output"]:
            warnings.append(f"{model['name']}: çıktı tahmini, modelin max output sınırını "
                            f"({fmt_int(model['max_output'])}) aşıyor.")

    print_table(headers, rows, right_align=set(range(1, len(headers) - 1)))
    print()

    if len(set(counts)) > 1:
        low, high = min(counts), max(counts)
        print(f"Not: Aynı metin modele göre farklı token sayısı verdi "
              f"({fmt_int(low)} – {fmt_int(high)}, fark {fmt_pct(high / low - 1)}). "
              f"Tokenizer modele özgüdür; her model için ayrı say.")
    for warning in warnings:
        print(f"Uyarı: {warning}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0


def cmd_compare(args, client, pricing: dict) -> int:
    tr_text, en_text = read_text(args.tr_file), read_text(args.en_file)
    models = select_models(pricing, args.models)

    print(f"Türkçe:   {args.tr_file}  |  {fmt_int(len(tr_text))} karakter, {fmt_int(len(tr_text.split()))} kelime")
    print(f"İngilizce: {args.en_file}  |  {fmt_int(len(en_text))} karakter, {fmt_int(len(en_text.split()))} kelime")
    print()

    headers = ["Model", "TR token", "EN token", "TR/EN", "TR fazlası", "1.000 çağrıda ek girdi maliyeti"]
    rows, ratios = [], []
    for model in models:
        tr_tokens, tr_err = try_count(client, model, build_messages(tr_text))
        en_tokens, en_err = try_count(client, model, build_messages(en_text))
        if tr_err or en_err:
            rows.append([model["name"], "-", "-", "-", "-", f"erişilemedi ({tr_err or en_err})"])
            continue
        ratio = tr_tokens / en_tokens
        ratios.append(ratio)
        extra_cost = (tr_tokens - en_tokens) * model["input_per_mtok"] / 1_000_000 * 1000
        rows.append([
            model["name"], fmt_int(tr_tokens), fmt_int(en_tokens),
            _tr_number(f"{ratio:.2f}"), fmt_pct(ratio - 1, 0), fmt_usd(extra_cost),
        ])

    print_table(headers, rows, right_align={1, 2, 3, 4, 5})
    print()
    if ratios:
        avg = sum(ratios) / len(ratios)
        direction = "daha fazla" if avg >= 1 else "daha az"
        print(f"Ortalama: Türkçe metin aynı içerik için {fmt_pct(abs(avg - 1), 0)} {direction} girdi token'ı kullandı.")
        print("Bu oran metin türüne ve modele göre değişir; kendi verinle ölç.")
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenhesap", description="Çağrı öncesi token, maliyet ve context hesaplayıcı.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat dosyası (varsayılan: pricing.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_count = sub.add_parser("count", help="Bir metnin token, maliyet ve context doluluğunu hesapla")
    p_count.add_argument("file", help="Metin dosyası ('-' ile standart girdi)")
    p_count.add_argument("--models", help=MODELS_HELP)
    p_count.add_argument("--output-tokens", type=int, default=1000, help="Beklenen çıktı token'ı (varsayılan: 1000)")
    p_count.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet gösterilir")
    p_count.add_argument("--baseline", action="store_true", help="Mesaj iskeletinin taban token'ını ve net metin token'ını göster")

    p_compare = sub.add_parser("compare", help="Aynı içeriğin Türkçe ve İngilizce token sayılarını karşılaştır")
    p_compare.add_argument("tr_file", help="Türkçe metin dosyası")
    p_compare.add_argument("en_file", help="İngilizce metin dosyası")
    p_compare.add_argument("--models", help=MODELS_HELP)
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

        if args.command == "count":
            return cmd_count(args, client, pricing)
        return cmd_compare(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
