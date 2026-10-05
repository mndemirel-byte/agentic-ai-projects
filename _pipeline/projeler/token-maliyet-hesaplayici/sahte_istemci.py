"""Önizleme ölçümü için sahte Anthropic istemcisi.

Gerçek API'ye gitmeden düzeni ve akışı görmek için kullanılır. Ürettiği sayılar
temsilidir; önizleme çıktıları "temsili" etiketi taşır ve teslim edilmez.
"""

from types import SimpleNamespace

TURKCE = set("çğıöşüÇĞİÖŞÜ")


class _Mesajlar:
    def _say(self, model, messages):
        metin = "".join(m["content"] for m in messages)
        tr_kelime = sum(1 for k in metin.split() if any(c in TURKCE for c in k))
        taban = len(metin) / 4.1 + tr_kelime * 0.9 + 8
        return int(taban * (1.0 if "haiku" in model else 1.22))

    def count_tokens(self, model, messages):
        return SimpleNamespace(input_tokens=self._say(model, messages))

    def create(self, model, max_tokens, messages):
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=self._say(model, messages) + 2, output_tokens=min(58, max_tokens)),
            content=[SimpleNamespace(type="text", text="Temsili yanıt: metnin tek cümlelik özeti burada yer alır.")],
        )


class SahteIstemci:
    def __init__(self):
        self.messages = _Mesajlar()
