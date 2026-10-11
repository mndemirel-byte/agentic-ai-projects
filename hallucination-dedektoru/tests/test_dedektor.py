"""dedektor için testler. Gerçek API çağrısı yapmaz; sahte (fake) istemci kullanır.

Çalıştırma:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))

import dedektor  # noqa: E402

SOURCE = str(ROOT / "kaynaklar" / "02_gonderi_uc_noktalari.md")
QUESTION = str(ROOT / "sorular" / "01_iptal.txt")
TRAP_ANSWER = str(ROOT / "tuzaklar" / "01_iptal_tuzakli.md")
TRAPS = str(ROOT / "tuzaklar" / "01_iptal_tuzaklar.yaml")

ANSWER = ("Bir gönderiyi iptal etmek için DELETE /v3/gonderiler/{takip_no} isteği gönderirsin. "
          "Kurye gönderiyi topladıktan sonra iptal isteği 409 Conflict döner.")
CLAIMS = ["Gönderi DELETE /v3/gonderiler/{takip_no} isteğiyle iptal edilir.",
          "Kurye gönderiyi topladıktan sonra iptal isteği 409 Conflict döner."]
RESULTS = [
    {"id": 1, "verdict": "supported", "evidence": "`DELETE /v3/gonderiler/{takip_no}` gönderiyi iptal eder.", "note": "Açıkça yazıyor."},
    {"id": 2, "verdict": "supported", "evidence": "kurye gönderiyi topladıktan sonra iptal isteği `409 Conflict` döner", "note": "Açıkça yazıyor."},
]


class FakeClient:
    """Prompt'un başına göre üretim, iddia çıkarma ya da doğrulama yanıtı döndürür; her çağrıyı sayar."""

    def __init__(self, answer=ANSWER, extract_text=None, verify_text=None, stop_reason="end_turn"):
        self.answer = answer
        self.extract_text = extract_text if extract_text is not None else json.dumps({"claims": CLAIMS}, ensure_ascii=False)
        self.verify_text = verify_text if verify_text is not None else json.dumps({"results": RESULTS}, ensure_ascii=False)
        self.stop_reason = stop_reason
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, model, max_tokens, messages, system=None, **extra):
        prompt = messages[0]["content"]
        self.calls.append({"model": model, "max_tokens": max_tokens, "system": system, "extra": extra, "prompt": prompt})
        if prompt.startswith("DOKÜMAN:"):
            text = self.answer
        elif prompt.startswith("<yanit>"):
            text = self.extract_text
        else:
            text = self.verify_text
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=500, output_tokens=80), stop_reason=self.stop_reason)


def run(argv, client=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = dedektor.main(argv, client=client)
    return code, out.getvalue(), err.getvalue()


class TextTests(unittest.TestCase):
    def test_tr_lower_handles_dotted_and_dotless_i(self):
        self.assertEqual(dedektor.tr_lower("İPTAL ISTEK"), "iptal ıstek")

    def test_normalize_strips_punctuation_and_spaces(self):
        self.assertEqual(dedektor.normalize_text("`409 Conflict` döner!"), "409conflictdöner")

    def test_evidence_found_ignores_formatting(self):
        source = "İptal yalnızca `olusturuldu` durumundaki gönderiler için mümkündür."
        self.assertTrue(dedektor.evidence_found("iptal yalnızca olusturuldu durumundaki", source))
        self.assertFalse(dedektor.evidence_found("iptal 2 saat içinde", source))
        self.assertFalse(dedektor.evidence_found("", source))

    def test_parse_json_strips_code_fences(self):
        self.assertEqual(dedektor._parse_json('```json\n{"claims": ["a"]}\n```'), {"claims": ["a"]})
        self.assertIsNone(dedektor._parse_json("bu JSON değil"))


class ScoringTests(unittest.TestCase):
    def rows(self, *verdicts):
        return [{"iddia": f"iddia {i}", "karar": v, "kanit": "", "not": ""} for i, v in enumerate(verdicts)]

    def test_evidence_check_downgrades_supported_without_evidence(self):
        source = "Takip numarası KZ ön eki ve 10 rakamdan oluşur."
        rows = [{"iddia": "a", "karar": "supported", "kanit": "KZ ön eki ve 10 rakamdan", "not": ""},
                {"iddia": "b", "karar": "supported", "kanit": "takip numarası 12 haneli", "not": ""},
                {"iddia": "c", "karar": "unsupported", "kanit": "", "not": ""}]
        dedektor.apply_evidence_check(rows, source)
        self.assertEqual([r["karar"] for r in rows], ["supported", "suspect", "unsupported"])
        self.assertEqual([r["kanit_bulundu"] for r in rows], [True, False, False])

    def test_risk_score_weights(self):
        self.assertEqual(dedektor.risk_score(self.rows("supported", "supported")), 0)
        self.assertAlmostEqual(dedektor.risk_score(self.rows("supported", "suspect", "unsupported", "supported")), 0.375)

    def test_route_thresholds(self):
        self.assertEqual(dedektor.route(self.rows("supported"), 0, 0.25), "KABUL")
        self.assertEqual(dedektor.route(self.rows("supported", "supported", "supported", "suspect"), 0.125, 0.25), "İNCELE")
        self.assertEqual(dedektor.route(self.rows("supported", "unsupported"), 0.5, 0.25), "RET")
        self.assertEqual(dedektor.route(self.rows("supported", "unsupported"), 0.5, 0.6), "İNCELE")

    def test_contradiction_always_rejects(self):
        rows = self.rows(*(["supported"] * 9 + ["contradicted"]))
        self.assertEqual(dedektor.route(rows, dedektor.risk_score(rows), 0.25), "RET")

    def test_cost_formula(self):
        model = {"input_per_mtok": 0.10, "output_per_mtok": 0.50}
        self.assertAlmostEqual(dedektor.estimate_cost(model, 1_000_000, 2_000_000), 1.10)

    def test_fmt_usd_turkish(self):
        self.assertEqual(dedektor.fmt_usd(0.00039), "$0,00039")
        self.assertEqual(dedektor.fmt_usd(1234.5), "$1.234,50")
        self.assertEqual(dedektor.fmt_usd(0), "$0")


class TrapTests(unittest.TestCase):
    def test_match_claims_requires_every_part_with_alternatives(self):
        rows = [{"iddia": "İptal isteği iki saat içinde yapılmalıdır.", "karar": "unsupported"},
                {"iddia": "Toplu iptal için POST /v3/gonderiler/toplu-iptal kullanılır.", "karar": "unsupported"}]
        self.assertEqual(len(dedektor.match_claims({"anahtar": ["2 saat|iki saat"]}, rows)), 1)
        self.assertEqual(len(dedektor.match_claims({"anahtar": ["toplu-iptal", "POST"]}, rows)), 1)
        self.assertEqual(dedektor.match_claims({"anahtar": ["toplu-iptal", "DELETE"]}, rows), [])

    def test_judge_trap_outcomes(self):
        flagged, clean = [{"karar": "unsupported"}], [{"karar": "supported"}]
        self.assertEqual(dedektor.judge_trap({"beklenen": "yakalanmali"}, flagged), "yakalandı")
        self.assertEqual(dedektor.judge_trap({"beklenen": "yakalanmali"}, clean), "kaçtı")
        self.assertEqual(dedektor.judge_trap({"beklenen": "gecmeli"}, clean), "doğru geçti")
        self.assertEqual(dedektor.judge_trap({"beklenen": "gecmeli"}, flagged), "yanlış alarm")
        self.assertEqual(dedektor.judge_trap({"beklenen": "gecmeli"}, []), "iddia çıkarılmadı")

    def test_load_traps_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text("tuzaklar:\n  - id: T1\n    tur: x\n    anahtar: [a]\n    beklenen: belki\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                dedektor.load_traps(str(bad))
            self.assertEqual(len(dedektor.load_traps(TRAPS)["tuzaklar"]), 4)


class DataTests(unittest.TestCase):
    def test_pricing_loads_with_roles(self):
        pricing = dedektor.load_pricing(dedektor.DEFAULT_PRICING_PATH)
        self.assertEqual(dedektor.select_model(pricing, None, "uretici")["key"], pricing["roller"]["uretici"])
        self.assertEqual(dedektor.select_model(pricing, "haiku-5-5", "uretici")["key"], "haiku-5-5")
        with self.assertRaises(ValueError):
            dedektor.select_model(pricing, "gpt-5", "uretici")

    def test_pricing_missing_role_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.yaml"
            path.write_text("roller: {uretici: a}\nmodels:\n  - {key: a, name: A, id: a, input_per_mtok: 1, output_per_mtok: 1}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                dedektor.load_pricing(path)

    def test_read_question_accepts_file_or_text(self):
        self.assertTrue(dedektor.read_question(QUESTION).startswith("Oluşturduğum"))
        self.assertEqual(dedektor.read_question("  Soru metni  "), "Soru metni")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_answer_writes_file_and_uses_generator_settings(self):
        client = FakeClient()
        out = str(self.dir / "yanit.md")
        code, text, _ = run(["answer", SOURCE, QUESTION, "--out", out], client)
        self.assertEqual(code, 0, text)
        self.assertEqual(Path(out).read_text(encoding="utf-8").strip(), ANSWER)
        self.assertIn("Claude Sonnet 5.5", text)
        self.assertEqual(client.calls[0]["system"], dedektor.GENERATE_SYSTEM)
        self.assertIn("thinking", client.calls[0]["extra"])

    def test_extract_then_verify(self):
        client = FakeClient()
        answer = self.dir / "yanit.md"
        answer.write_text(ANSWER, encoding="utf-8")
        claims = str(self.dir / "iddialar.json")
        code, text, _ = run(["extract", str(answer), "--out", claims], client)
        self.assertEqual(code, 0, text)
        self.assertIn("2 iddia çıkarıldı", text)
        self.assertEqual(json.loads(Path(claims).read_text(encoding="utf-8"))["claims"], CLAIMS)
        code, text, _ = run(["verify", SOURCE, claims], client)
        self.assertEqual(code, 0, text)
        self.assertIn("DESTEKLİ", text)
        self.assertIn("→  KABUL", text)
        self.assertEqual(client.calls[-1]["model"], "claude-haiku-5-5")

    def test_chain_records_and_reports_calls(self):
        client = FakeClient()
        out = str(self.dir / "zincir.jsonl")
        with mock.patch.object(dedektor, "DEFAULT_RESULTS_DIR", self.dir):
            code, text, _ = run(["chain", SOURCE, QUESTION, "--out", out], client)
        self.assertEqual(code, 0, text)
        self.assertIn("3 çağrı", text)
        record = json.loads(Path(out).read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(record["yonlendirme"], "KABUL")
        self.assertEqual(record["cagri"], 3)
        self.assertEqual(len(record["iddialar"]), 2)

    def test_chain_with_ready_answer_skips_generation(self):
        client = FakeClient()
        out = str(self.dir / "zincir.jsonl")
        code, text, _ = run(["chain", SOURCE, QUESTION, "--answer", TRAP_ANSWER, "--out", out], client)
        self.assertEqual(code, 0, text)
        self.assertIn("üretim atlandı", text)
        self.assertIn("2 çağrı", text)
        self.assertEqual(json.loads(Path(out).read_text(encoding="utf-8"))["uretici"], None)

    def test_evidence_check_and_threshold_in_verify(self):
        rows = [dict(RESULTS[0]), {"id": 2, "verdict": "supported", "evidence": "iptal 2 saat içinde yapılır", "note": ""}]
        client = FakeClient(verify_text=json.dumps({"results": rows}, ensure_ascii=False))
        claims = self.dir / "iddialar.json"
        claims.write_text(json.dumps({"claims": CLAIMS}), encoding="utf-8")
        code, text, _ = run(["verify", SOURCE, str(claims)], client)
        self.assertEqual(code, 0, text)
        self.assertIn("ŞÜPHELİ", text)
        self.assertIn("kaynakta YOK", text)
        self.assertIn("→  İNCELE", text)
        code, text, _ = run(["verify", SOURCE, str(claims), "--threshold", "0.1"], client)
        self.assertIn("→  RET", text)

    def test_score_matches_traps(self):
        verdicts = [
            {"iddia": "Toplu iptal için POST /v3/gonderiler/toplu-iptal kullanılır.", "karar": "unsupported", "kanit": "", "not": "", "kanit_bulundu": False},
            {"iddia": "İptal isteği 2 saat içinde yapılmalıdır.", "karar": "suspect", "kanit": "x", "not": "", "kanit_bulundu": False},
            {"iddia": "İptal edilen gönderinin durumu iade olur.", "karar": "supported", "kanit": "iade", "not": "", "kanit_bulundu": True},
            {"iddia": "Toplanmış gönderide iptal 409 döner.", "karar": "supported", "kanit": "409 Conflict", "not": "", "kanit_bulundu": True},
        ]
        results = self.dir / "zincir.jsonl"
        results.write_text(json.dumps({"zaman": "t", "yanit_dosyasi": "tuzaklar/01_iptal_tuzakli.md", "yonlendirme": "RET",
                                       "iddialar": verdicts}, ensure_ascii=False) + "\n", encoding="utf-8")
        code, text, _ = run(["score", str(results), TRAPS])
        self.assertEqual(code, 0, text)
        self.assertIn("Yakalama: 2/3", text)
        self.assertIn("Yanlış alarm: 0/1", text)
        self.assertIn("kaçtı", text)

    def test_score_without_matching_record_is_one_line_error(self):
        results = self.dir / "zincir.jsonl"
        results.write_text(json.dumps({"zaman": "t", "yanit_dosyasi": "baska.md", "yonlendirme": "KABUL", "iddialar": []}) + "\n", encoding="utf-8")
        code, _, err = run(["score", str(results), TRAPS])
        self.assertEqual(code, 2)
        self.assertIn("Hata:", err)
        self.assertNotIn("Traceback", err)

    def test_bad_model_json_is_one_line_error(self):
        client = FakeClient(extract_text="Elbette! İşte iddialar: ...")
        answer = self.dir / "yanit.md"
        answer.write_text(ANSWER, encoding="utf-8")
        code, _, err = run(["extract", str(answer), "--out", str(self.dir / "i.json")], client)
        self.assertEqual(code, 2)
        self.assertIn("Hata: İddia çıkarma", err)
        self.assertNotIn("Traceback", err)

    def test_verify_result_count_mismatch_is_error(self):
        client = FakeClient(verify_text=json.dumps({"results": RESULTS[:1]}))
        claims = self.dir / "iddialar.json"
        claims.write_text(json.dumps({"claims": CLAIMS}), encoding="utf-8")
        code, _, err = run(["verify", SOURCE, str(claims)], client)
        self.assertEqual(code, 2)
        self.assertIn("2 iddia için 1 sonuç", err)

    def test_cut_answer_is_flagged(self):
        client = FakeClient(stop_reason="max_tokens")
        code, text, _ = run(["answer", SOURCE, "Kısa soru", "--out", str(self.dir / "y.md")], client)
        self.assertEqual(code, 0)
        self.assertIn("kesildi", text)

    def test_missing_api_key_stops_before_call(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _, err = run(["answer", SOURCE, QUESTION])
        self.assertEqual(code, 2)
        self.assertIn("ANTHROPIC_API_KEY", err)

    def test_unknown_model_key_is_one_line_error(self):
        code, _, err = run(["--verifier", "gpt-5", "extract", TRAP_ANSWER], FakeClient())
        self.assertEqual(code, 2)
        self.assertIn("Geçerli anahtarlar", err)


if __name__ == "__main__":
    unittest.main()
