"""tokenhesap için testler. Gerçek API çağrısı yapmaz; sahte (fake) client kullanır.

Çalıştırma:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import anthropic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))

import tokenhesap  # noqa: E402


def _not_found_error():
    """SDK sürümünden bağımsız bir 404 hatası nesnesi üretir."""
    err = anthropic.NotFoundError.__new__(anthropic.NotFoundError)
    err.status_code = 404
    return err


class FakeMessages:
    """count_tokens ve create çağrılarını taklit eder.

    Haiku ile diğer modeller arasında tokenizer farkını simüle etmek için
    farklı karakter/token oranları kullanır.
    """

    def __init__(self, unavailable=()):
        self.unavailable = set(unavailable)
        self.count_calls = []

    def _tokens(self, model, messages):
        text = "".join(m["content"] for m in messages)
        if model.startswith("claude-haiku"):
            return len(text) // 4 + 7
        return int(len(text) / 3.2) + 9

    def count_tokens(self, model, messages):
        if model in self.unavailable:
            raise _not_found_error()
        self.count_calls.append(model)
        return SimpleNamespace(input_tokens=self._tokens(model, messages))

    def create(self, model, max_tokens, messages):
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=self._tokens(model, messages) + 1, output_tokens=42),
            content=[SimpleNamespace(type="text", text="Test özeti.")],
        )


class FakeClient:
    def __init__(self, unavailable=()):
        self.messages = FakeMessages(unavailable)


def run_cli(argv, client):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = tokenhesap.main(argv, client=client)
    return code, buffer.getvalue()


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.pricing = tokenhesap.load_pricing(ROOT / "pricing.yaml")
        self.haiku = tokenhesap.select_models(self.pricing, "haiku-4-5")[0]

    def test_pricing_has_four_models(self):
        keys = [m["key"] for m in self.pricing["models"]]
        self.assertEqual(keys, ["haiku-4-5", "sonnet-5-5", "opus-5-5", "fable-5-1"])

    def test_estimate_cost(self):
        # 1.000 girdi × $1 + 500 çıktı × $5 = $0,0035
        self.assertAlmostEqual(tokenhesap.estimate_cost(self.haiku, 1000, 500), 0.0035)

    def test_context_ratio_and_labels(self):
        self.assertAlmostEqual(tokenhesap.context_ratio(self.haiku, 150_000, 10_000), 0.8)
        self.assertEqual(tokenhesap.usage_label(0.3), "OK")
        self.assertEqual(tokenhesap.usage_label(0.5), "DİKKAT")
        self.assertEqual(tokenhesap.usage_label(0.8), "YÜKSEK")
        self.assertEqual(tokenhesap.usage_label(1.01), "TAŞMA")

    def test_render_bar(self):
        self.assertEqual(tokenhesap.render_bar(0.5, width=10), "█████░░░░░")
        self.assertEqual(tokenhesap.render_bar(1.7, width=10), "██████████")

    def test_turkish_number_format(self):
        self.assertEqual(tokenhesap.fmt_int(1234567), "1.234.567")
        self.assertEqual(tokenhesap.fmt_usd(0.0014), "$0,0014")
        self.assertEqual(tokenhesap.fmt_usd(0.35), "$0,35")
        self.assertEqual(tokenhesap.fmt_usd(0.00012), "$0,00012")
        self.assertEqual(tokenhesap.fmt_usd(1234.5), "$1.234,50")
        self.assertEqual(tokenhesap.fmt_pct(0.125), "%12,5")
        self.assertEqual(tokenhesap.fmt_pct(-0.04, 0), "-%4")

    def test_unknown_model_key(self):
        with self.assertRaises(ValueError):
            tokenhesap.select_models(self.pricing, "gpt-5")


class CliTests(unittest.TestCase):
    def test_count_all_models(self):
        code, out = run_cli(["count", str(ROOT / "ornekler/2_eposta_tr.txt")], FakeClient())
        self.assertEqual(code, 0)
        for name in ("Claude Haiku 4.5", "Claude Sonnet 5.5", "Claude Opus 5.5", "Claude Fable 5.1"):
            self.assertIn(name, out)
        self.assertIn("farklı token sayısı", out)

    def test_count_with_baseline_and_monthly(self):
        code, out = run_cli(
            ["count", str(ROOT / "ornekler/1_kisa_tr.txt"), "--models", "haiku-4-5",
             "--baseline", "--monthly-calls", "100000"],
            FakeClient(),
        )
        self.assertEqual(code, 0)
        self.assertIn("Taban", out)
        self.assertIn("Aylık (100.000 çağrı)", out)

    def test_unavailable_model_does_not_crash(self):
        code, out = run_cli(["count", str(ROOT / "ornekler/1_kisa_tr.txt")],
                            FakeClient(unavailable={"claude-fable-5-1"}))
        self.assertEqual(code, 0)
        self.assertIn("erişilemedi (HTTP 404)", out)

    def test_output_tokens_above_max_output_warns(self):
        code, out = run_cli(["count", str(ROOT / "ornekler/1_kisa_tr.txt"), "--models", "haiku-4-5",
                             "--output-tokens", "70000"], FakeClient())
        self.assertIn("max output sınırını", out)

    def test_overflow_label_for_long_text(self):
        long_path = ROOT / "tests" / "_gecici_uzun.txt"
        long_path.write_text("a" * 900_000, encoding="utf-8")
        try:
            _, out = run_cli(["count", str(long_path), "--models", "haiku-4-5,sonnet-5-5"], FakeClient())
        finally:
            long_path.unlink()
        self.assertIn("TAŞMA", out)

    def test_verify(self):
        code, out = run_cli(["count", str(ROOT / "ornekler/1_kisa_tr.txt"), "--models", "haiku-4-5",
                             "--verify"], FakeClient())
        self.assertEqual(code, 0)
        self.assertIn("Gerçek (usage)", out)
        self.assertIn("Girdi farkı: +1 token", out)

    def test_compare(self):
        code, out = run_cli(["compare", str(ROOT / "ornekler/3_teknik_tr.txt"),
                             str(ROOT / "ornekler/3_teknik_en.txt")], FakeClient())
        self.assertEqual(code, 0)
        self.assertIn("TR/EN", out)
        self.assertIn("Ortalama: Türkçe metin", out)

    def test_missing_file(self):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code, _ = run_cli(["count", "yok.txt"], FakeClient())
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
