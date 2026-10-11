"""cozum/adim_N.py ara sürümlerinin çalıştığını doğrular (gerçek API çağrısı yapmaz)."""

import contextlib
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))
sys.path.insert(0, str(ROOT / "tests"))

from test_dedektor import ANSWER, CLAIMS, FakeClient  # noqa: E402

SOURCE = str(ROOT / "kaynaklar" / "02_gonderi_uc_noktalari.md")
QUESTION = str(ROOT / "sorular" / "01_iptal.txt")
TRAP_ANSWER = str(ROOT / "tuzaklar" / "01_iptal_tuzakli.md")

# Her adım için çalıştırılacak komutlar ve çıktıda beklenen metin. {tmp} geçici klasörle değiştirilir.
PLAN = {
    1: [(["answer", SOURCE, QUESTION, "--out", "{tmp}/yanit.md"], "Yanıt kaydedildi")],
    2: [(["answer", SOURCE, QUESTION, "--out", "{tmp}/yanit.md"], "Yanıt kaydedildi"),
        (["extract", "{tmp}/yanit.md", "--out", "{tmp}/iddialar.json"], f"{len(CLAIMS)} iddia çıkarıldı")],
    3: [(["extract", TRAP_ANSWER, "--out", "{tmp}/iddialar.json"], "İddialar kaydedildi"),
        (["verify", SOURCE, "{tmp}/iddialar.json"], "DESTEKLİ")],
    4: [(["extract", TRAP_ANSWER, "--out", "{tmp}/iddialar.json"], "İddialar kaydedildi"),
        (["verify", SOURCE, "{tmp}/iddialar.json"], "kaynakta")],
    5: [(["extract", TRAP_ANSWER, "--out", "{tmp}/iddialar.json"], "İddialar kaydedildi"),
        (["verify", SOURCE, "{tmp}/iddialar.json", "--threshold", "0.5"], "Risk skoru")],
    6: [(["chain", SOURCE, QUESTION, "--answer", TRAP_ANSWER, "--out", "{tmp}/zincir.jsonl"], "Kaydedildi")],
}


class StepSnapshotTests(unittest.TestCase):
    def test_each_step_runs(self):
        for n, commands in PLAN.items():
            with self.subTest(adim=n), tempfile.TemporaryDirectory() as tmp:
                module = importlib.import_module(f"adim_{n}")
                client = FakeClient(answer=ANSWER)
                for argv, expected in commands:
                    argv = [a.replace("{tmp}", tmp) for a in argv]
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                        code = module.main(argv, client=client)
                    self.assertEqual(code, 0, buffer.getvalue())
                    self.assertIn(expected, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
