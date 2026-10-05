# Token maliyet hesaplayıcı

Agentic AI Developer Programı · Aşama 1 (LLM okuryazarlığı) · Bireysel proje

Çağrı öncesi çalışan bir CLI ile metnin token sayısını, model bazında maliyetini ve context window doluluğunu hesapla; Türkçe ile İngilizce'nin token verimliliğini karşılaştır.

> **Projeye nereden başlamalı?** Kurulumu aşağıdaki "Hızlı başlangıç" bölümüne göre yap, ardından **[Step-by-Step-GUIDE.md](Step-by-Step-GUIDE.md)** dosyasını aç. Rehber, aracı yedi adımda sıfırdan yazman için gereken kodu, komutları, beklenen çıktıları ve kontrol noktalarını içerir.

Projenin amacı, isterleri ve pratik edeceğin kavramlar platformdaki proje sayfasındadır. Bu klasör projenin başlangıç dosyalarını, adım adım rehberini ve referans çözümünü içerir.

## Klasör yapısı

| Yol | İçerik |
|-----|--------|
| `pricing.yaml` | Dört modelin fiyat, context window ve max output değerleri (tarih damgalı) |
| `ornekler/` | Üç Türkçe/İngilizce paralel metin çifti ve uzun log üretici |
| `Step-by-Step-GUIDE.md` | Yedi adımlık rehber: kod, komutlar, beklenen çıktılar ve kontrol noktaları |
| `calisma/` | Kendi `tokenhesap.py` dosyanı yazacağın klasör |
| `cozum/adim_1.py` … `adim_6.py` | Her adımın sonunda dosyanın ulaşması gereken hâl |
| `cozum/tokenhesap.py` | Tam çözüm (Adım 7'nin sonu) — önce kendin yaz, takıldığında bak |
| `kod-rehberi.html` | Referans çözümün çalışma akışını adım adım anlatan etkileşimli rehber; tarayıcıda aç |
| `kod-rehberi-yan-yana.html` | Referans çözümün tamamı solda, her parçanın açıklaması sağda; tarayıcıda aç |
| `demo.html` | Bitmiş aracın örnek komutlarını, çıktılarını ve parametrelerini gösteren demo kartı; tarayıcıda aç |
| `tests/` | Gerçek API çağrısı yapmayan testler (sahte client) |

## Hızlı başlangıç

```bash
cd token-maliyet-hesaplayici
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."

python cozum/tokenhesap.py count ornekler/2_eposta_tr.txt
python cozum/tokenhesap.py compare ornekler/2_eposta_tr.txt ornekler/2_eposta_en.txt
```

## Testler

```bash
python -m unittest discover -s tests -v
```

## Üretilen dosyalar hakkında

`Step-by-Step-GUIDE.md`, `kod-rehberi.html`, `kod-rehberi-yan-yana.html` ve `demo.html` dosyaları elle düzenlenmez; repo kökündeki `_pipeline/` aracıyla çözüm kodundan ve gerçek ölçüm çıktısından üretilir. Bu dosyalarda bir hata görürsen kaynağını `_pipeline/projeler/token-maliyet-hesaplayici/` altında düzelt ve yeniden üret.

## Fiyatlar hakkında

`pricing.yaml` içindeki fiyatlar dosyadaki `updated` tarihine aittir. API fiyatları değişebilir; üretimde kullanmadan önce [Anthropic pricing sayfasını](https://platform.claude.com/docs/en/about-claude/pricing) kontrol et.
