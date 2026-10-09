"""modellab için testler. Gerçek API çağrısı yapmaz; sahte (fake) streaming client ve sahte saat kullanır.

Çalıştırma:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import anthropic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))

import modellab  # noqa: E402

TASKS = str(ROOT / "gorevler" / "2_gorev_seti.yaml")
SINGLE = str(ROOT / "gorevler" / "1_tek_prompt.yaml")


def _not_found_error():
    """SDK sürümünden bağımsız bir 404 hatası nesnesi üretir."""
    err = anthropic.NotFoundError.__new__(anthropic.NotFoundError)
    err.status_code = 404
    return err


class FakeClock:
    """time.perf_counter yerine geçer; sahte akış ilerledikçe zamanı elle ilerletir."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


# Model başına sahte profil: ilk token gecikmesi, parça başına gecikme (saniye)
PROFILES = {"claude-haiku": (0.05, 0.01), "claude-sonnet": (0.10, 0.02), "claude-opus": (0.20, 0.03), "claude-fable": (0.30, 0.04)}

# Görevin prompt'una göre dönen yanıt (model bağımsız); muhakeme görevinde Haiku yanlış cevap verir.
ANSWERS = {
    "kategori": "fatura",
    "JSON": '{"siparis_no": "TR-48213", "tutar": 2480.0, "teslim_tarihi": "2026-10-12"}',
    "özetle": "Kök neden süresi dolan TLS sertifikasıydı; sertifika yenilendi ve 30 gün önce uyaran bir izleme kuralı eklendi.",
    "medyan": "def medyan(s):\n    if not s:\n        raise ValueError('boş')\n    s = sorted(s)\n    return s[len(s) // 2]",
    "toplantı": "12:20",
    "Mikroservis": "1. Ağ gecikmesi.\n2. Veri tutarlılığı.\n3. Operasyon yükü.",
}


class FakeStream:
    def __init__(self, clock, model, messages, max_tokens):
        self.clock = clock
        self.model = model
        self.max_tokens = max_tokens
        prompt = "".join(m["content"] for m in messages)
        self.text = next((a for k, a in ANSWERS.items() if k in prompt), "yanıt")
        if "toplantı" in prompt and model.startswith("claude-haiku"):
            self.text = "12:00"
        self.ttft, self.gap = next(v for k, v in PROFILES.items() if model.startswith(k))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @property
    def text_stream(self):
        self.clock.now += self.ttft
        for word in self.text.split(" "):
            yield word + " "
            self.clock.now += self.gap

    def get_final_message(self):
        output = len(self.text.split())
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=50, output_tokens=output),
            stop_reason="max_tokens" if output >= self.max_tokens else "end_turn",
        )


class FakeMessages:
    def __init__(self, clock, unavailable=()):
        self.clock = clock
        self.unavailable = set(unavailable)
        self.calls = []
        self.extra = {}

    def stream(self, model, max_tokens, messages, system=None, **extra):
        if model in self.unavailable:
            raise _not_found_error()
        self.calls.append((model, system))
        self.extra[model] = extra
        return FakeStream(self.clock, model, messages, max_tokens)


class FakeClient:
    def __init__(self, unavailable=()):
        self.clock = FakeClock()
        self.messages = FakeMessages(self.clock, unavailable)


def run_cli(argv, client=None):
    client = client or FakeClient()
    buffer = io.StringIO()
    with mock.patch.object(time, "perf_counter", client.clock), contextlib.redirect_stdout(buffer):
        code = modellab.main(argv, client=client)
    return code, buffer.getvalue()


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.pricing = modellab.load_pricing(ROOT / "pricing.yaml")
        self.haiku = modellab.select_models(self.pricing, "haiku-4-5")[0]

    def test_estimate_cost(self):
        # Haiku: $1 girdi, $5 çıktı / MTok → 1000 girdi + 200 çıktı = $0,002
        self.assertAlmostEqual(modellab.estimate_cost(self.haiku, 1000, 200), 0.002)

    def test_tokens_per_second(self):
        self.assertAlmostEqual(modellab.tokens_per_second(100, 0.5, 2.5), 50.0)
        self.assertIsNone(modellab.tokens_per_second(5, 1.0, 1.02))
        self.assertEqual(modellab.fmt_speed(None), "-")
        self.assertEqual(modellab.fmt_speed(1234.4), "1.234")

    def test_select_models_unknown_key(self):
        with self.assertRaises(ValueError) as ctx:
            modellab.select_models(self.pricing, "gpt-5")
        self.assertIn("Geçerli anahtarlar", str(ctx.exception))

    def test_mean(self):
        self.assertEqual(modellab.mean([1, 2, 3]), 2)


class CheckTests(unittest.TestCase):
    def test_no_checks_returns_none(self):
        self.assertEqual(modellab.check_output("x", {}), (None, []))

    def test_all_pass(self):
        score, failed = modellab.check_output("Fatura", {"icermeli": ["fatura"], "max_kelime": 2})
        self.assertEqual((score, failed), (100.0, []))

    def test_partial_fail(self):
        score, failed = modellab.check_output("teknik sorun bu", {"icermeli": ["fatura"], "max_kelime": 5})
        self.assertEqual(score, 50.0)
        self.assertEqual(failed, ["icermeli: fatura"])

    def test_icermeli_biri_and_icermemeli(self):
        score, failed = modellab.check_output("Saat 12.20", {"icermeli_biri": ["12:20", "12.20"], "icermemeli": ["```"]})
        self.assertEqual(score, 100.0)
        score, failed = modellab.check_output("```json```", {"icermemeli": ["```"]})
        self.assertEqual(score, 0.0)

    def test_json_check(self):
        text = '```json\n{"siparis_no": "TR-1", "tutar": 5}\n```'
        score, failed = modellab.check_output(text, {"json": ["siparis_no", "tutar", "teslim_tarihi"]})
        self.assertEqual(score, 0.0)
        self.assertEqual(failed, ["json: eksik alan teslim_tarihi"])
        score, _ = modellab.check_output('{"a": 1}', {"json": ["a"]})
        self.assertEqual(score, 100.0)
        score, failed = modellab.check_output("bu json değil", {"json": ["a"]})
        self.assertEqual(failed, ["json: geçerli JSON nesnesi değil"])


class FormattingTests(unittest.TestCase):
    def test_fmt_int(self):
        self.assertEqual(modellab.fmt_int(1234567), "1.234.567")

    def test_fmt_usd(self):
        self.assertEqual(modellab.fmt_usd(0), "$0")
        self.assertEqual(modellab.fmt_usd(0.35), "$0,35")
        self.assertEqual(modellab.fmt_usd(0.0035), "$0,0035")
        self.assertEqual(modellab.fmt_usd(1234.5), "$1.234,50")

    def test_fmt_sec(self):
        self.assertEqual(modellab.fmt_sec(0.3204), "320 ms")
        self.assertEqual(modellab.fmt_sec(1.8367), "1,84 s")

    def test_fmt_score_and_rating(self):
        self.assertEqual(modellab.fmt_score(None), "-")
        self.assertEqual(modellab.fmt_score(87.5), "%88")
        self.assertEqual(modellab.fmt_rating(4.26), "4,3/5")

    def test_parse_scores(self):
        self.assertEqual(modellab.parse_scores("a=4, B=3", ["A", "B"]), {"A": 4, "B": 3})
        with self.assertRaises(ValueError):
            modellab.parse_scores("A=4", ["A", "B"])
        with self.assertRaises(ValueError):
            modellab.parse_scores("A=9,B=1", ["A", "B"])


class TaskLoadingTests(unittest.TestCase):
    def test_loads_task_set(self):
        tasks = modellab.load_tasks(TASKS)
        self.assertEqual(len(tasks["gorevler"]), 5)
        self.assertEqual([t["ad"] for t in tasks["gorevler"]][:2], ["siniflandirma", "veri_cikarma"])

    def test_unknown_check_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("ad: x\ngorevler:\n  - ad: a\n    prompt: b\n    kontroller: {regex: 'x'}\n")
        with self.assertRaises(ValueError) as ctx:
            modellab.load_tasks(f.name)
        self.assertIn("bilinmeyen kontrol", str(ctx.exception))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "sonuc.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_measures_and_saves(self):
        client = FakeClient()
        code, out = run_cli(["run", TASKS, "--out", str(self.out)], client)
        self.assertEqual(code, 0)
        self.assertIn("[siniflandirma] (tier 1)", out)
        self.assertIn("Claude Fable 5.1", out)
        records = [json.loads(line) for line in self.out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 20)
        haiku = [r for r in records if r["model"] == "haiku-4-5" and r["gorev"] == "siniflandirma"][0]
        self.assertAlmostEqual(haiku["ilk_token_sn"], 0.05)
        self.assertAlmostEqual(haiku["toplam_sn"], 0.06)
        self.assertEqual(haiku["puan"], 100.0)
        self.assertEqual(haiku["kesildi"], False)
        # system talimatı olan görevde system API'ye iletilmiş olmalı; cagri_ayarlari modele göre isteğe eklenmeli
        self.assertIn(("claude-haiku-4-5-20251001", "Sen bir müşteri destek yönlendirme asistanısın."), client.messages.calls)
        self.assertEqual(client.messages.extra["claude-haiku-4-5-20251001"], {"thinking": {"type": "disabled"}})
        self.assertEqual(client.messages.extra["claude-opus-5-5"]["output_config"], {"effort": "low"})

    def test_run_unavailable_model_does_not_stop(self):
        client = FakeClient(unavailable={"claude-opus-5-5"})
        code, out = run_cli(["run", SINGLE, "--out", str(self.out)], client)
        self.assertEqual(code, 0)
        self.assertIn("erişilemedi (HTTP 404)", out)
        self.assertIn("Uyarı: 1 çağrı başarısız oldu: mikroservis/opus-5-5", out)
        self.assertEqual(len(self.out.read_text(encoding="utf-8").splitlines()), 3)

    def test_run_repeat_and_max_tokens_cut(self):
        code, out = run_cli(["run", SINGLE, "--models", "haiku-4-5", "--repeat", "2", "--max-tokens", "3", "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertIn("Claude Haiku 4.5 #2", out)
        self.assertIn("(kesildi)", out)

    def test_report_show_rate_cycle(self):
        run_cli(["run", TASKS, "--out", str(self.out)])
        code, out = run_cli(["report", str(self.out), "--monthly-calls", "1000"])
        self.assertEqual(code, 0)
        self.assertIn("Aylık (1.000 çağrı)", out)
        self.assertIn("En hızlı ilk token: Claude Haiku 4.5 (50 ms)", out)
        self.assertIn("En ucuz: Claude Haiku 4.5", out)
        self.assertNotIn("Etiketsiz", out)
        self.assertNotIn("Toplam süre aralığı", out)
        # Haiku muhakeme görevinde yanlış cevap verdi: otomatik puanı %100'ün altında
        self.assertIn("En yüksek otomatik puan: Claude Sonnet 5.5 (%100)", out)

        code, shown = run_cli(["show", str(self.out), "muhakeme"])
        self.assertEqual(code, 0)
        self.assertNotIn("Claude", shown.split("Puanlamak için")[1])
        self.assertIn("--- A ---", shown)
        self.assertIn("--- D ---", shown)

        code, rated = run_cli(["rate", str(self.out), "muhakeme", "--scores", "A=5,B=4,C=3,D=2"])
        self.assertEqual(code, 0)
        self.assertIn("etiketler açılıyor", rated)
        self.assertIn("Claude Haiku 4.5", rated)
        self.assertEqual(len(self.out.read_text(encoding="utf-8").splitlines()), 24)

        # show ve rate aynı etiket eşlemesini kullanmalı: etiketsiz görünümde A hangi yanıtsa rate'te de o model
        first_answer = shown.split("--- A ---")[1].split("--- B ---")[0].strip()
        records = [json.loads(line) for line in self.out.read_text(encoding="utf-8").splitlines()]
        a_model = [r for r in records if r["tur"] == "puan"][0]["model"]
        self.assertEqual([r for r in records if r["tur"] == "calistirma" and r["gorev"] == "muhakeme" and r["model"] == a_model][0]["yanit"], first_answer)

        code, out = run_cli(["report", str(self.out), "--model-card", str(Path(self.tmp.name) / "kart.md")])
        self.assertIn("Etiketsiz", out)
        self.assertIn("En yüksek etiketsiz puan", out)
        card = (Path(self.tmp.name) / "kart.md").read_text(encoding="utf-8")
        self.assertIn("# Model kartı", card)
        self.assertIn("| Claude Haiku 4.5 |", card)
        self.assertIn("Seçilen model: _(yaz)_", card)

    def test_report_with_repeat_shows_range(self):
        run_cli(["run", SINGLE, "--repeat", "3", "--out", str(self.out)])
        code, out = run_cli(["report", str(self.out)])
        self.assertIn("görev başına 3 tekrar", out)
        self.assertIn("Toplam süre aralığı (min–maks)", out)

    def test_rate_rejects_bad_scores(self):
        run_cli(["run", SINGLE, "--out", str(self.out)])
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = modellab.main(["rate", str(self.out), "mikroservis", "--scores", "A=4"], client=FakeClient())
        self.assertEqual(code, 2)
        self.assertIn("Hata: Eksik puan", buffer.getvalue())

    def test_show_unknown_task(self):
        run_cli(["run", SINGLE, "--out", str(self.out)])
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = modellab.main(["show", str(self.out), "yok"], client=FakeClient())
        self.assertEqual(code, 2)
        self.assertIn("Görevler: mikroservis", buffer.getvalue())

    def test_missing_api_key_message(self):
        buffer = io.StringIO()
        with mock.patch.dict("os.environ", {}, clear=True), contextlib.redirect_stderr(buffer):
            code = modellab.main(["run", SINGLE])
        self.assertEqual(code, 2)
        self.assertIn("ANTHROPIC_API_KEY", buffer.getvalue())

    def test_report_needs_run_records(self):
        self.out.write_text("", encoding="utf-8")
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = modellab.main(["report", str(self.out)], client=FakeClient())
        self.assertEqual(code, 2)
        self.assertIn("Önce 'run'", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
