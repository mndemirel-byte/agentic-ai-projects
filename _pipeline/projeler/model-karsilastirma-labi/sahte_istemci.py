"""Önizleme ölçümü için sahte Anthropic istemcisi.

Gerçek API'ye gitmeden düzeni ve akışı görmek için kullanılır. Ürettiği süreler, token
sayıları ve yanıtlar temsilidir; önizleme çıktıları "temsili" etiketi taşır ve teslim edilmez.
Streaming arayüzünü (messages.stream → text_stream, get_final_message) taklit eder.
"""

import time
from types import SimpleNamespace

# Model başına temsili profil: ilk token gecikmesi (sn), parça başına gecikme (sn), kalite eğilimi
PROFIL = {
    "haiku": (0.05, 0.004, 0),
    "sonnet": (0.09, 0.006, 1),
    "opus": (0.14, 0.009, 1),
    "fable": (0.22, 0.012, 2),
}

YANITLAR = {
    "kategori": ["fatura", "fatura", "fatura", "fatura"],
    "JSON": ['{"siparis_no": "TR-48213", "tutar": 2480.0, "teslim_tarihi": "2026-10-12"}'] * 4,
    "özetle": [
        "Ödeme servisindeki zaman aşımlarının kök nedeni, banka entegrasyonunda kullanılan TLS sertifikasının süresinin dolmasıydı. Sertifika yenilendi ve süresi dolmadan 30 gün önce uyaran bir izleme kuralı eklendi.",
        "Ödeme servisinde 65 dakika süren kesintinin kök nedeni süresi dolmuş TLS sertifikasıydı; sertifika yenilendi. Önlem olarak sertifika süresi dolmadan 30 gün önce uyaran bir izleme kuralı tanımlandı.",
        "9 Ekim'de ödeme servisinin banka entegrasyonunda süresi dolan TLS sertifikası isteklerin %38'inin zaman aşımına uğramasına yol açtı; sertifika yenilenerek sorun giderildi. Tekrarı önlemek için sertifika bitişinden 30 gün önce uyarı veren bir izleme kuralı eklendi.",
        "Kök neden, ödeme servisinin banka entegrasyonunda kullandığı TLS sertifikasının süresinin dolmasıydı; yenilenmesiyle 65 dakikalık kesinti sona erdi. Önlem olarak sertifika bitiminden 30 gün önce uyaran bir izleme kuralı devreye alındı.",
    ],
    "medyan": [
        "def medyan(sayilar):\n    if not sayilar:\n        raise ValueError(\"Liste boş\")\n    s = sorted(sayilar)\n    n = len(s)\n    orta = n // 2\n    if n % 2:\n        return s[orta]\n    return (s[orta - 1] + s[orta]) / 2",
    ] * 4,
    "toplantı": ["12:00", "12:20", "12:20", "12:20"],
    "Mikroservis": [
        "1. Servisler arası ağ iletişimi gecikme ve hata kaynağı yaratır.\n2. Dağıtık veri yönetimi tutarlılığı zorlaştırır.\n3. Operasyon ve izleme karmaşıklığı belirgin biçimde artar.",
    ] * 4,
}


class _Akis:
    def __init__(self, model, messages, max_tokens):
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens
        self._metin = self._yanit()[: max_tokens * 3]  # temsili kesme: ~3 karakter/token

    def _yanit(self):
        prompt = "".join(m["content"] for m in self.messages)
        sira = next((i for i, k in enumerate(PROFIL) if k in self.model), 1)
        for anahtar, secenekler in YANITLAR.items():
            if anahtar in prompt:
                return secenekler[sira]
        return "Temsili yanıt: görevin cevabı burada yer alır."

    def _profil(self):
        for anahtar, degerler in PROFIL.items():
            if anahtar in self.model:
                return degerler
        return PROFIL["sonnet"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @property
    def text_stream(self):
        ttft, parca_gecikme, _ = self._profil()
        time.sleep(ttft)
        kelimeler = self._metin.split(" ")
        for i, kelime in enumerate(kelimeler):
            time.sleep(parca_gecikme)
            yield kelime + (" " if i < len(kelimeler) - 1 else "")

    def get_final_message(self):
        girdi = len("".join(m["content"] for m in self.messages)) // 4 + 12
        cikti = min(self.max_tokens, len(self._metin) // 3 + 3)
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=girdi, output_tokens=cikti),
            stop_reason="max_tokens" if cikti >= self.max_tokens else "end_turn",
        )


class _Mesajlar:
    def stream(self, model, max_tokens, messages, system=None, **ayarlar):
        return _Akis(model, messages, max_tokens)


class SahteIstemci:
    def __init__(self):
        self.messages = _Mesajlar()
