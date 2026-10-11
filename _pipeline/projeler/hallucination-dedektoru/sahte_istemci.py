"""Önizleme ölçümü için sahte Anthropic istemcisi.

Gerçek API'ye gitmeden düzeni ve akışı görmek için kullanılır. Ürettiği yanıtlar, iddialar ve
kararlar temsilidir; önizleme çıktıları "temsili" etiketi taşır ve teslim edilmez.
Non-streaming arayüzü (messages.create → content, usage, stop_reason) taklit eder. Hangi aşamanın
çağrıldığını prompt'un başından anlar: DOKÜMAN (üretim), "<yanit>" (iddia çıkarma),
"Aşağıdaki iddiaların" (doğrulama).
"""

import json
import re
from types import SimpleNamespace

# Soru anahtar kelimesi → temsili yanıt
YANITLAR = {
    "iptal": "Bir gönderiyi iptal etmek için DELETE /v3/gonderiler/{takip_no} isteği gönderirsin. İptal yalnızca "
             "gönderi olusturuldu durumundayken mümkündür; kurye gönderiyi topladıktan sonra iptal isteği 409 Conflict "
             "döner ve iptal için müşteri hizmetleriyle iletişime geçmen gerekir.",
    "dakikada": "Standart planda bir anahtar dakikada en fazla 120 istek yapabilir. Limit aşıldığında API 429 Too Many "
                "Requests döner ve Retry-After başlığında kaç saniye bekleneceğini yazar. Toplu gönderi oluşturma uç "
                "noktası tek istekte en fazla 50 gönderi kabul eder ve hız limitinde tek istek sayılır.",
    "imza": "Her webhook isteği X-Kuzey-Imza başlığı taşır; imza, istek gövdesinin webhook gizli anahtarıyla "
            "HMAC-SHA256 ile hesaplanmış hex hâlidir ve ham bayt dizisi üzerinden hesaplanır. İmza 300 saniye "
            "geçerlidir ve zaman damgası imza hesabına dahildir.",
    "sandbox": "kz_test_ anahtarları yalnızca sandbox ortamında geçerlidir ve sandbox'ta oluşturulan gönderiler gerçek "
               "sevkiyata dönüşmez. Sandbox'ta da dakikada 120 istek yapılabilir; sandbox verileri 30 gün sonra silinir.",
}


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<=[.;])\s+", metin) if c.strip()]


def _kelimeler(metin: str) -> set[str]:
    return {k for k in re.findall(r"[0-9a-zçğıöşü_/-]+", metin.replace("I", "ı").replace("İ", "i").lower()) if len(k) > 2}


class _Mesajlar:
    def create(self, model, max_tokens, messages, system=None, **ayarlar):
        prompt = messages[0]["content"]
        if prompt.startswith("DOKÜMAN:"):
            soru = prompt.split("SORU:", 1)[-1].lower()
            metin = next((y for k, y in YANITLAR.items() if k in soru), "Temsili yanıt: sorunun cevabı burada yer alır.")
        elif prompt.startswith("<yanit>"):
            yanit = prompt.split("<yanit>\n", 1)[1].rsplit("\n</yanit>", 1)[0].strip()
            metin = json.dumps({"claims": _cumleler(yanit)[:10]}, ensure_ascii=False)
        else:
            kaynak = prompt.split('"""')[1]
            iddialar = re.findall(r"^\d+\. (.+)$", prompt.split("İDDİALAR:", 1)[-1], flags=re.M)
            kaynak_cumleleri = _cumleler(kaynak)
            sonuclar = []
            for i, iddia in enumerate(iddialar, start=1):
                kelimeler = _kelimeler(iddia)
                en_iyi = max(kaynak_cumleleri, key=lambda c: len(kelimeler & _kelimeler(c)))
                oran = len(kelimeler & _kelimeler(en_iyi)) / max(1, len(kelimeler))
                if oran >= 0.5:
                    sonuclar.append({"id": i, "verdict": "supported", "evidence": en_iyi, "note": "Kaynakta aynı bilgi var."})
                elif oran >= 0.3:
                    # Temsili "kaynak gösterir gibi" durumu: karar supported ama alıntı kaynakta birebir yok
                    sonuclar.append({"id": i, "verdict": "supported", "evidence": en_iyi.replace(" ", "  ", 1)[:40] + " (özet)",
                                     "note": "Kaynak bu bilgiyi dolaylı olarak içeriyor."})
                else:
                    sonuclar.append({"id": i, "verdict": "unsupported", "evidence": "", "note": "Kaynakta bu konuda bilgi yok."})
            metin = json.dumps({"results": sonuclar}, ensure_ascii=False)
        girdi = len(prompt) // 4 + (len(system) // 4 if system else 0)
        cikti = min(max_tokens, len(metin) // 3 + 3)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=metin)],
            usage=SimpleNamespace(input_tokens=girdi, output_tokens=cikti),
            stop_reason="max_tokens" if cikti >= max_tokens else "end_turn",
        )


class SahteIstemci:
    def __init__(self):
        self.messages = _Mesajlar()
