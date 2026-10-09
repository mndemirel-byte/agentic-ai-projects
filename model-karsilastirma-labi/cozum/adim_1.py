"""Model karşılaştırma lab'ı — Adım 1: i̇lk ölçüm.

Bu dosya, Step-by-Step-GUIDE.md rehberindeki 1. adımın sonunda calisma/modellab.py
dosyasının ulaşması gereken hâldir. Kendi başına çalışır:

    python cozum/adim_1.py run gorevler/1_tek_prompt.yaml
"""

import argparse
import os
import sys
import time

import anthropic
import yaml

# İlk adımda tek model kullanılır; Adım 2'de model bilgisi pricing.yaml dosyasından gelecek.
MODEL_ID = "claude-haiku-4-5-20251001"
MODEL_NAME = "Claude Haiku 4.5"


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_tasks(path: str) -> dict:
    """Görev dosyasını (YAML) okur."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


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


# ---------------------------------------------------------------------------
# Biçimlendirme (Türkçe sayı yazımı: binlik ayırıcı nokta, ondalık virgül)
# ---------------------------------------------------------------------------

def _tr_number(formatted: str) -> str:
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_sec(seconds: float) -> str:
    """Süreyi okunur yazar: 1 saniyenin altı milisaniye, üstü saniye."""
    if seconds < 1:
        return f"{round(seconds * 1000)} ms"
    return _tr_number(f"{seconds:.2f}") + " s"


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_run(args, client) -> int:
    tasks = load_tasks(args.tasks)
    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  model: {MODEL_NAME}  |  max_tokens={args.max_tokens}")

    for task in tasks["gorevler"]:
        print()
        print(f"[{task['ad']}]")
        result = stream_call(client, MODEL_ID, build_messages(task["prompt"]), args.max_tokens, task.get("system"))
        print(result["text"])
        print()
        print(f"İlk token: {fmt_sec(result['ttft'])}  |  Toplam: {fmt_sec(result['total'])}  |  "
              f"Girdi: {result['input_tokens']} token  |  Çıktı: {result['output_tokens']} token  |  "
              f"Durma nedeni: {result['stop_reason']}")
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modellab", description="Aynı görev setini modellerde çalıştırıp gecikme, maliyet ve kaliteyi karşılaştır.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Görev setini modellerde çalıştır ve sonuçları kaydet (ücretli)")
    p_run.add_argument("tasks", help="Görev dosyası (YAML)")
    p_run.add_argument("--max-tokens", type=int, default=300, help="Her çağrı için max_tokens (varsayılan: 300)")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
            return 2
        client = anthropic.Anthropic()
    return cmd_run(args, client)


if __name__ == "__main__":
    sys.exit(main())
