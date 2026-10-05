"""cozum/adim_N.py ara sürümlerinin çalıştığını doğrular (gerçek API çağrısı yapmaz)."""

import contextlib
import importlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cozum"))
sys.path.insert(0, str(ROOT / "tests"))

from test_tokenhesap import FakeClient  # noqa: E402

PLAN = {
    1: ["count", "ornekler/1_kisa_tr.txt"],
    2: ["count", "ornekler/1_kisa_tr.txt", "--baseline"],
    3: ["count", "ornekler/2_eposta_tr.txt", "--models", "haiku-4-5", "--baseline", "--monthly-calls", "1000"],
    4: ["count", "ornekler/2_eposta_tr.txt"],
    5: ["count", "ornekler/2_eposta_tr.txt", "--output-tokens", "4000"],
    6: ["compare", "ornekler/2_eposta_tr.txt", "ornekler/2_eposta_en.txt"],
}
EXPECT = {
    1: "girdi token:",
    2: "Taban (mesaj iskeleti):",
    3: "Aylık (1.000 çağrı)",
    4: "Claude Fable 5.1",
    5: "Context doluluğu",
    6: "TR/EN",
}


class StepSnapshotTests(unittest.TestCase):
    def test_each_step_runs(self):
        for n, argv in PLAN.items():
            with self.subTest(adim=n):
                module = importlib.import_module(f"adim_{n}")
                argv = [str(ROOT / a) if a.startswith("ornekler/") else a for a in argv]
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = module.main(argv, client=FakeClient())
                self.assertEqual(code, 0)
                self.assertIn(EXPECT[n], buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
