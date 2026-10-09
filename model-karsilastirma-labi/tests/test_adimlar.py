"""cozum/adim_N.py ara sürümlerinin çalıştığını doğrular (gerçek API çağrısı yapmaz)."""

import contextlib
import importlib
import io
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))
sys.path.insert(0, str(ROOT / "tests"))

from test_modellab import FakeClient  # noqa: E402

SINGLE = str(ROOT / "gorevler" / "1_tek_prompt.yaml")
TASKS = str(ROOT / "gorevler" / "2_gorev_seti.yaml")

# Her adım için çalıştırılacak komutlar ve çıktıda beklenen metin. {out} sonuç dosyasıyla değiştirilir.
PLAN = {
    1: [(["run", SINGLE], "Durma nedeni: end_turn")],
    2: [(["run", SINGLE, "--show-output"], "Claude Fable 5.1")],
    3: [(["run", TASKS, "--out", "{out}"], "(20 kayıt)")],
    4: [(["run", TASKS, "--out", "{out}"], "Puan")],
    5: [(["run", TASKS, "--out", "{out}"], "Kaydedildi"),
        (["report", "{out}", "--monthly-calls", "1000"], "En hızlı ilk token")],
    6: [(["run", TASKS, "--out", "{out}"], "Kaydedildi"),
        (["show", "{out}", "ozet"], "--- D ---"),
        (["rate", "{out}", "ozet", "--scores", "A=4,B=3,C=5,D=3"], "etiketler açılıyor"),
        (["report", "{out}"], "Etiketsiz")],
    7: [(["run", SINGLE, "--repeat", "2", "--out", "{out}"], "Claude Haiku 4.5 #2"),
        (["report", "{out}"], "Toplam süre aralığı")],
}


class StepSnapshotTests(unittest.TestCase):
    def test_each_step_runs(self):
        for n, commands in PLAN.items():
            with self.subTest(adim=n), tempfile.TemporaryDirectory() as tmp:
                module = importlib.import_module(f"adim_{n}")
                out = str(Path(tmp) / "sonuc.jsonl")
                client = FakeClient()
                for argv, expected in commands:
                    argv = [a.replace("{out}", out) for a in argv]
                    buffer = io.StringIO()
                    with mock.patch.object(time, "perf_counter", client.clock), contextlib.redirect_stdout(buffer):
                        code = module.main(argv, client=client)
                    self.assertEqual(code, 0, buffer.getvalue())
                    self.assertIn(expected, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
