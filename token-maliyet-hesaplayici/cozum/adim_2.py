"""Token maliyet hesaplayıcı — Adım 2: taban ölçümü.

Adım 1'e ek olarak --baseline ile mesaj iskeletinin token payını ayırır.

Kullanım:
    python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt --baseline
"""

import argparse
import os
import sys
from pathlib import Path

import anthropic

MODEL_ID = "claude-haiku-4-5-20251001"
MODEL_NAME = "Claude Haiku 4.5"

# Taban ölçümü için kullanılan en kısa anlamlı mesaj. API boş metin kabul etmez.
BASELINE_TEXT = "."


def read_text(path: str) -> str:
    """Dosyayı UTF-8 olarak okur; '-' verilirse standart girdiden okur."""
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def build_messages(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def count_input_tokens(client, model_id: str, messages: list[dict]) -> int:
    """Token Counting API ile girdi token sayısını döndürür. Model çalışmaz, ücret yazılmaz."""
    response = client.messages.count_tokens(model=model_id, messages=messages)
    return response.input_tokens


def cmd_count(args, client) -> int:
    text = read_text(args.file)
    tokens = count_input_tokens(client, MODEL_ID, build_messages(text))

    print(f"Dosya: {args.file}  |  {len(text)} karakter, {len(text.split())} kelime")
    print(f"{MODEL_NAME} girdi token: {tokens}")

    if args.baseline:
        base = count_input_tokens(client, MODEL_ID, build_messages(BASELINE_TEXT))
        print(f"Taban (mesaj iskeleti): {base}")
        print(f"Net (metnin kendi payı, yaklaşık): {tokens - base}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenhesap", description="Çağrı öncesi token, maliyet ve context hesaplayıcı.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_count = sub.add_parser("count", help="Bir metnin token sayısını hesapla")
    p_count.add_argument("file", help="Metin dosyası ('-' ile standart girdi)")
    p_count.add_argument("--baseline", action="store_true", help="Mesaj iskeletinin taban token'ını ve net metin token'ını göster")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
            return 2
        client = anthropic.Anthropic()

    try:
        return cmd_count(args, client)
    except FileNotFoundError as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
