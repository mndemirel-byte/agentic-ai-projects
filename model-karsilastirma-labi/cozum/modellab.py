"""Model karşılaştırma lab'ı.

Aynı görev setini birden fazla Claude modelinde çalıştırır ve şu soruları cevaplar:
  - Hangi model ilk token'ı ne kadar sürede veriyor, cevabı ne kadar sürede bitiriyor?
  - Her görev her modelde kaça mal oluyor?
  - Çıktılar görevin kurallarına ne ölçüde uyuyor (otomatik puan)?
  - Model adını görmeden puanladığında hangisini daha iyi buluyorsun (etiketsiz puan)?

Kullanım:
    python cozum/modellab.py run gorevler/1_tek_prompt.yaml --models haiku-4-5
    python cozum/modellab.py run gorevler/2_gorev_seti.yaml
    python cozum/modellab.py run gorevler/2_gorev_seti.yaml --repeat 3 --out sonuclar/tekrar.jsonl
    python cozum/modellab.py report sonuclar/2_gorev_seti.jsonl --monthly-calls 100000
    python cozum/modellab.py show sonuclar/2_gorev_seti.jsonl ozet
    python cozum/modellab.py rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,C=5,D=3
    python cozum/modellab.py report sonuclar/2_gorev_seti.jsonl --model-card sonuclar/model-karti.md
"""

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")

# Görev dosyasında tanınan kontrol türleri. Bilinmeyen bir tür dosya yüklenirken hata verir.
CHECK_KINDS = ("icermeli", "icermeli_biri", "icermemeli", "max_kelime", "json")

# Etiketsiz görünümde model adlarının yerine geçen harfler.
LABELS = "ABCDEFGH"


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


def load_tasks(path: str) -> dict:
    """Görev dosyasını okur; her görevde ad ve prompt olduğunu, kontrol türlerinin tanındığını doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or not data.get("gorevler"):
        raise ValueError(f"{path}: 'gorevler' listesi boş ya da yok.")
    for task in data["gorevler"]:
        if "ad" not in task or "prompt" not in task:
            raise ValueError(f"{path}: her görevde 'ad' ve 'prompt' alanları olmalı.")
        unknown = [k for k in task.get("kontroller", {}) if k not in CHECK_KINDS]
        if unknown:
            raise ValueError(f"{path}: '{task['ad']}' görevinde bilinmeyen kontrol: {', '.join(unknown)}")
    return data


# ---------------------------------------------------------------------------
# API çağrıları
# ---------------------------------------------------------------------------

def build_messages(prompt: str) -> list[dict]:
    return [{"role": "user", "content": prompt}]


def stream_call(client, model_id: str, messages: list[dict], max_tokens: int, system: str | None = None,
                extra: dict | None = None) -> dict:
    """Streaming ile tek çağrı yapar; ilk token süresini, toplam süreyi ve usage değerlerini ölçer.

    Süreler saniye cinsindendir. İlk token süresi, isteğin gönderilmesinden ilk metin
    parçasının gelmesine kadar geçen süredir (Ders 1.4 §4.3). `extra`, modele özgü ek
    istek ayarlarıdır (pricing.yaml > cagri_ayarlari); olduğu gibi isteğe eklenir.
    """
    kwargs = {"model": model_id, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    kwargs.update(extra or {})
    start = time.perf_counter()
    first = None
    chunks = []
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if first is None:
                first = time.perf_counter()
            chunks.append(text)
        final = stream.get_final_message()
    end = time.perf_counter()
    return {
        "text": "".join(chunks).strip(),
        "ttft": (first or end) - start,
        "total": end - start,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "stop_reason": final.stop_reason,
    }


def try_call(client, model: dict, messages: list[dict], max_tokens: int, system: str | None) -> tuple[dict | None, str | None]:
    """Bir model için çağrı yapar; o modele erişim yoksa hatayı tabloya yansıtmak üzere döndürür."""
    try:
        return stream_call(client, model["id"], messages, max_tokens, system, model.get("cagri_ayarlari")), None
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


def tokens_per_second(output_tokens: int, ttft: float, total: float) -> float | None:
    """Üretim hızı: ilk token geldikten sonra saniyede kaç çıktı token'ı üretildi.

    Üretim süresi 50 ms'nin altındaysa (birkaç token'lık yanıt) hız güvenilir ölçülemez; None döner.
    """
    generation = total - ttft
    if generation < 0.05:
        return None
    return output_tokens / generation


def _parse_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned[cleaned.find("{"):] if "{" in cleaned else cleaned
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def check_output(text: str, checks: dict) -> tuple[float | None, list[str]]:
    """Çıktıyı görevin kontrollerine göre puanlar: (0–100 puan, başarısız kontrollerin listesi).

    Kontrol yoksa puan None döner. Her kontrol eşit ağırlıktadır.
    """
    if not checks:
        return None, []
    lowered = text.lower()
    failed = []
    for kind, rule in checks.items():
        if kind == "icermeli":
            missing = [s for s in rule if s.lower() not in lowered]
            if missing:
                failed.append(f"icermeli: {', '.join(missing)}")
        elif kind == "icermeli_biri":
            if not any(s.lower() in lowered for s in rule):
                failed.append(f"icermeli_biri: {' | '.join(rule)}")
        elif kind == "icermemeli":
            present = [s for s in rule if s.lower() in lowered]
            if present:
                failed.append(f"icermemeli: {', '.join(present)}")
        elif kind == "max_kelime":
            words = len(text.split())
            if words > rule:
                failed.append(f"max_kelime: {words} > {rule}")
        elif kind == "json":
            parsed = _parse_json(text)
            if not isinstance(parsed, dict):
                failed.append("json: geçerli JSON nesnesi değil")
            else:
                missing = [k for k in rule if k not in parsed]
                if missing:
                    failed.append(f"json: eksik alan {', '.join(missing)}")
    score = (len(checks) - len(failed)) / len(checks) * 100
    return score, failed


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


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


def fmt_sec(seconds: float) -> str:
    """Süreyi okunur yazar: 1 saniyenin altı milisaniye, üstü saniye."""
    if seconds < 1:
        return f"{round(seconds * 1000)} ms"
    return _tr_number(f"{seconds:.2f}") + " s"


def fmt_pct(ratio: float, decimals: int = 0) -> str:
    return "%" + _tr_number(f"{ratio * 100:.{decimals}f}")


def fmt_speed(speed: float | None) -> str:
    """Üretim hızı; ölçülemediyse '-'."""
    return "-" if speed is None else fmt_int(round(speed))


def fmt_score(score: float | None) -> str:
    return "-" if score is None else fmt_pct(score / 100)


def fmt_rating(rating: float | None) -> str:
    """Etiketsiz puan: 1–5 ölçeğinde ortalama, ör. 4,3/5."""
    return "-" if rating is None else _tr_number(f"{rating:.1f}") + "/5"


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
# Kayıt (JSONL: her satır bir JSON nesnesi)
# ---------------------------------------------------------------------------

def default_results_path(tasks_path: str) -> Path:
    return DEFAULT_RESULTS_DIR / (Path(tasks_path).stem + ".jsonl")


def save_results(path: Path, records: list[dict], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_results(path: str) -> list[dict]:
    """JSONL dosyasını okur. 'calistirma' kayıtları ölçümleri, 'puan' kayıtları etiketsiz puanları taşır."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    if not any(r.get("tur") == "calistirma" for r in records):
        raise ValueError(f"{path}: çalıştırma kaydı yok. Önce 'run' komutunu çalıştır.")
    return records


def runs_for_task(records: list[dict], task_name: str) -> list[dict]:
    """Bir görevin başarılı çalıştırma kayıtlarını, model başına ilk tekrarla sınırlı olarak döndürür."""
    runs = [r for r in records if r.get("tur") == "calistirma" and r["gorev"] == task_name and r.get("tekrar", 1) == 1]
    if not runs:
        known = sorted({r["gorev"] for r in records if r.get("tur") == "calistirma"})
        raise ValueError(f"'{task_name}' adında görev yok. Görevler: {', '.join(known)}")
    return runs


def anonymize(runs: list[dict], seed: str) -> list[tuple[str, dict]]:
    """Çalıştırmaları karıştırıp A, B, C... etiketleriyle eşler. Aynı tohum aynı sırayı verir."""
    shuffled = list(runs)
    random.Random(seed).shuffle(shuffled)
    return list(zip(LABELS, shuffled))


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_run(args, client, pricing: dict) -> int:
    tasks = load_tasks(args.tasks)
    models = select_models(pricing, args.models)
    out_path = Path(args.out) if args.out else default_results_path(args.tasks)

    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  {len(models)} model  |  "
          f"max_tokens={fmt_int(args.max_tokens)}  |  tekrar={args.repeat}")
    print()

    records, failures = [], []
    for task in tasks["gorevler"]:
        print(f"[{task['ad']}]" + (f" (tier {task['tier']})" if task.get("tier") else ""))
        messages = build_messages(task["prompt"])
        headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet", "Puan"]
        rows = []
        for model in models:
            for repeat in range(1, args.repeat + 1):
                result, error = try_call(client, model, messages, args.max_tokens, task.get("system"))
                if error:
                    rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
                    failures.append(f"{task['ad']}/{model['key']}")
                    continue
                cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
                score, failed = check_output(result["text"], task.get("kontroller", {}))
                cut = result["stop_reason"] == "max_tokens"
                records.append({
                    "tur": "calistirma", "zaman": datetime.now().isoformat(timespec="seconds"),
                    "gorev": task["ad"], "tier": task.get("tier"), "model": model["key"], "model_adi": model["name"],
                    "tekrar": repeat, "ilk_token_sn": round(result["ttft"], 3), "toplam_sn": round(result["total"], 3),
                    "girdi_token": result["input_tokens"], "cikti_token": result["output_tokens"],
                    "kesildi": cut, "maliyet": cost, "puan": score, "basarisiz": failed, "yanit": result["text"],
                })
                name = model["name"] if args.repeat == 1 else f"{model['name']} #{repeat}"
                rows.append([
                    name, fmt_sec(result["ttft"]), fmt_sec(result["total"]),
                    fmt_speed(tokens_per_second(result["output_tokens"], result["ttft"], result["total"])),
                    fmt_int(result["output_tokens"]) + (" (kesildi)" if cut else ""), fmt_usd(cost), fmt_score(score),
                ])
                if args.show_output:
                    print(f"  {model['name']}:\n" + "\n".join("    " + line for line in result["text"].splitlines()))
        print_table(headers, rows, right_align=set(range(1, len(headers))))
        print()

    save_results(out_path, records)
    shown = out_path.relative_to(PROJECT_DIR) if out_path.is_relative_to(PROJECT_DIR) else out_path
    print(f"Kaydedildi: {shown.as_posix()} ({len(records)} kayıt)")
    if failures:
        print(f"Uyarı: {len(failures)} çağrı başarısız oldu: {', '.join(failures)}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0


def summarize(records: list[dict]) -> list[dict]:
    """Çalıştırma kayıtlarını model başına özetler; etiketsiz puanlar varsa ortalamasını ekler."""
    runs = [r for r in records if r.get("tur") == "calistirma"]
    ratings = [r for r in records if r.get("tur") == "puan"]
    summaries = []
    for key in dict.fromkeys(r["model"] for r in runs):
        mine = [r for r in runs if r["model"] == key]
        scored = [r["puan"] for r in mine if r["puan"] is not None]
        rated = [r["puan"] for r in ratings if r["model"] == key]
        totals = [r["toplam_sn"] for r in mine]
        speeds = [v for v in (tokens_per_second(r["cikti_token"], r["ilk_token_sn"], r["toplam_sn"]) for r in mine) if v is not None]
        summaries.append({
            "model": key, "model_adi": mine[0]["model_adi"], "calistirma": len(mine),
            "tekrar": max(r.get("tekrar", 1) for r in mine),
            "ilk_token_sn": mean([r["ilk_token_sn"] for r in mine]),
            "toplam_sn": mean(totals), "toplam_min_sn": min(totals), "toplam_max_sn": max(totals),
            "token_sn": mean(speeds) if speeds else None,
            "cikti_token": mean([r["cikti_token"] for r in mine]),
            "maliyet": mean([r["maliyet"] for r in mine]),
            "kesilen": sum(1 for r in mine if r["kesildi"]),
            "puan": mean(scored) if scored else None,
            "etiketsiz_puan": mean(rated) if rated else None,
        })
    return summaries


def decision_lines(summaries: list[dict]) -> list[str]:
    """Özet tablodan karar cümleleri üretir: en hızlı, en ucuz, en yüksek puan ve puan başına maliyet."""
    fastest = min(summaries, key=lambda s: s["ilk_token_sn"])
    cheapest = min(summaries, key=lambda s: s["maliyet"])
    lines = [
        f"En hızlı ilk token: {fastest['model_adi']} ({fmt_sec(fastest['ilk_token_sn'])})",
        f"En ucuz: {cheapest['model_adi']} ({fmt_usd(cheapest['maliyet'])}/görev)",
    ]
    scored = [s for s in summaries if s["puan"] is not None]
    if scored:
        best = max(scored, key=lambda s: s["puan"])
        lines.append(f"En yüksek otomatik puan: {best['model_adi']} ({fmt_score(best['puan'])})")
        spread = max(s["puan"] for s in scored) - min(s["puan"] for s in scored)
        lines.append(f"Otomatik puan farkı (en yüksek − en düşük): {fmt_int(round(spread))} puan "
                     f"(fark küçükse kararı kalite değil, hız ve maliyet verdirir)")
    rated = [s for s in summaries if s["etiketsiz_puan"] is not None]
    if rated:
        best = max(rated, key=lambda s: s["etiketsiz_puan"])
        lines.append(f"En yüksek etiketsiz puan: {best['model_adi']} ({fmt_rating(best['etiketsiz_puan'])})")
    return lines


def cmd_report(args, pricing: dict) -> int:
    records = load_results(args.results)
    summaries = summarize(records)
    repeated = any(s["tekrar"] > 1 for s in summaries)
    rated = any(s["etiketsiz_puan"] is not None for s in summaries)

    task_count = len({r["gorev"] for r in records if r.get("tur") == "calistirma"})
    print(f"Sonuç dosyası: {args.results}  |  {task_count} görev, {len(summaries)} model"
          + (f", görev başına {summaries[0]['tekrar']} tekrar" if repeated else ""))
    print()

    headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet/görev"]
    if args.monthly_calls:
        headers.append(f"Aylık ({fmt_int(args.monthly_calls)} çağrı)")
    headers.append("Oto puan")
    if rated:
        headers.append("Etiketsiz")
    rows = []
    for s in summaries:
        row = [s["model_adi"], fmt_sec(s["ilk_token_sn"]), fmt_sec(s["toplam_sn"]), fmt_speed(s["token_sn"]),
               fmt_int(round(s["cikti_token"])) + (f" ({s['kesilen']} kesildi)" if s["kesilen"] else ""),
               fmt_usd(s["maliyet"])]
        if args.monthly_calls:
            row.append(fmt_usd(s["maliyet"] * args.monthly_calls))
        row.append(fmt_score(s["puan"]))
        if rated:
            row.append(fmt_rating(s["etiketsiz_puan"]))
        rows.append(row)
    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    if repeated:
        print("Toplam süre aralığı (min–maks): " + "  |  ".join(
            f"{s['model_adi']} {fmt_sec(s['toplam_min_sn'])}–{fmt_sec(s['toplam_max_sn'])}" for s in summaries))
        print()
    for line in decision_lines(summaries):
        print(line)
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")

    if args.model_card:
        write_model_card(Path(args.model_card), args.results, summaries)
        print(f"Model kartı yazıldı: {args.model_card}")
    return 0


def write_model_card(path: Path, results_path: str, summaries: list[dict]) -> None:
    """Karar kaydını Markdown olarak yazar (Ders 1.7 §7, adım 7). Gerekçe satırlarını öğrenci doldurur."""
    lines = [
        "# Model kartı",
        "",
        f"- Tarih: {datetime.now().date().isoformat()}",
        f"- Sonuç dosyası: `{results_path}`",
        "",
        "| Model | İlk token | Toplam | Maliyet/görev | Oto puan | Etiketsiz |",
        "|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(f"| {s['model_adi']} | {fmt_sec(s['ilk_token_sn'])} | {fmt_sec(s['toplam_sn'])} | "
                     f"{fmt_usd(s['maliyet'])} | {fmt_score(s['puan'])} | {fmt_rating(s['etiketsiz_puan'])} |")
    lines += ["", "## Ölçümün söyledikleri", ""]
    lines += [f"- {line}" for line in decision_lines(summaries)]
    lines += [
        "",
        "## Karar",
        "",
        "- Seçilen model: _(yaz)_",
        "- Gerekçe (kalite, gecikme, maliyet ekseninde): _(yaz)_",
        "- Yedek (fallback) model: _(yaz)_",
        "- Yeniden değerlendirme tarihi: _(yaz)_",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def cmd_show(args) -> int:
    records = load_results(args.results)
    runs = runs_for_task(records, args.task)
    print(f"Görev: {args.task}  |  {len(runs)} çıktı, model adları gizli. "
          f"Puanlamak için: rate {args.results} {args.task} --scores A=4,B=3,...")
    for label, run in anonymize(runs, f"{args.results}:{args.task}"):
        print()
        print(f"--- {label} ---")
        print(run["yanit"])
    return 0


def parse_scores(scores_csv: str, labels: list[str]) -> dict[str, int]:
    """'A=4,B=3' biçimindeki metni {etiket: puan} sözlüğüne çevirir; eksik ya da geçersiz girdiyi reddeder."""
    scores = {}
    for part in (p.strip() for p in scores_csv.split(",") if p.strip()):
        label, _, value = part.partition("=")
        label = label.strip().upper()
        if label not in labels or not value.strip().isdigit() or not 1 <= int(value) <= 5:
            raise ValueError(f"Geçersiz puan girdisi: '{part}'. Biçim: A=4 (1–5 arası).")
        scores[label] = int(value)
    missing = [label for label in labels if label not in scores]
    if missing:
        raise ValueError(f"Eksik puan: {', '.join(missing)}. Her çıktıya puan ver.")
    return scores


def cmd_rate(args) -> int:
    records = load_results(args.results)
    runs = runs_for_task(records, args.task)
    labeled = anonymize(runs, f"{args.results}:{args.task}")
    labels = [label for label, _ in labeled]

    if args.scores:
        scores = parse_scores(args.scores, labels)
    else:
        answers = []
        for label in labels:
            answers.append(f"{label}={input(f'{label} için puan (1–5): ').strip()}")
        scores = parse_scores(",".join(answers), labels)

    ratings = []
    print(f"Görev: {args.task}  |  etiketler açılıyor")
    print()
    rows = []
    for label, run in labeled:
        rows.append([label, run["model_adi"], f"{scores[label]}/5", fmt_score(run["puan"]), fmt_usd(run["maliyet"])])
        ratings.append({"tur": "puan", "zaman": datetime.now().isoformat(timespec="seconds"),
                        "gorev": args.task, "model": run["model"], "model_adi": run["model_adi"], "puan": scores[label]})
    print_table(["Etiket", "Model", "Etiketsiz puan", "Oto puan", "Maliyet"], rows, right_align={2, 3, 4})
    print()
    save_results(Path(args.results), ratings, append=True)
    print(f"Kaydedildi: {args.results} (+{len(ratings)} puan kaydı). Rapora yansıtmak için: report {args.results}")
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modellab", description="Aynı görev setini modellerde çalıştırıp gecikme, maliyet ve kaliteyi karşılaştır.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat dosyası (varsayılan: pricing.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Görev setini modellerde çalıştır ve sonuçları kaydet (ücretli)")
    p_run.add_argument("tasks", help="Görev dosyası (YAML)")
    p_run.add_argument("--models", help=MODELS_HELP)
    p_run.add_argument("--max-tokens", type=int, default=300, help="Her çağrı için max_tokens (varsayılan: 300)")
    p_run.add_argument("--repeat", type=int, default=1, help="Her görev-model çiftini kaç kez çalıştırmalı (varsayılan: 1)")
    p_run.add_argument("--out", help="Sonuç dosyası (varsayılan: sonuclar/<görev dosyası adı>.jsonl)")
    p_run.add_argument("--show-output", action="store_true", help="Model yanıtlarını da yazdır")

    p_report = sub.add_parser("report", help="Kaydedilmiş sonuçlardan karşılaştırma raporu üret (çağrı yapmaz)")
    p_report.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_report.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet sütunu eklenir")
    p_report.add_argument("--model-card", help="Karar kaydını bu Markdown dosyasına yaz")

    p_show = sub.add_parser("show", help="Bir görevin çıktılarını model adları gizli olarak göster")
    p_show.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_show.add_argument("task", help="Görev adı (görev dosyasındaki 'ad')")

    p_rate = sub.add_parser("rate", help="Etiketsiz puanları kaydet ve etiketleri aç")
    p_rate.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_rate.add_argument("task", help="Görev adı (görev dosyasındaki 'ad')")
    p_rate.add_argument("--scores", help="Puanlar, ör. A=4,B=3,C=5,D=3 (verilmezse terminalden sorulur)")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if args.command == "report":
            return cmd_report(args, pricing)
        if args.command == "show":
            return cmd_show(args)
        if args.command == "rate":
            return cmd_rate(args)

        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        return cmd_run(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
