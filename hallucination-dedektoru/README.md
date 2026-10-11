# Hallucination dedektörü

Agentic AI Developer Programı · Aşama 1 (LLM okuryazarlığı) · İkili proje

Kaynak dokümana dayalı LLM yanıtını iddialara ayırıp her iddiayı kaynağa karşı doğrulayan iki aşamalı bir zincir kur; risk skoruna göre yönlendir ve partnerinin yerleştirdiği tuzak iddiaların kaçını yakaladığını ölç.

> **Projeye nereden başlamalı?** Kurulumu aşağıdaki "Hızlı başlangıç" bölümüne göre yapın, `kaynaklar/` klasöründeki üç dokümanı okuyun, ardından **[Step-by-Step-GUIDE.md](Step-by-Step-GUIDE.md)** dosyasını açın. Rehber, aracı yedi adımda iki kişi birlikte sıfırdan yazmanız için gereken rolleri, kodu, komutları, beklenen çıktıları ve kontrol noktalarını içerir.

Projenin amacı, isterleri, rolleri ve pratik edeceğiniz kavramlar platformdaki proje sayfasındadır. Bu klasör projenin başlangıç dosyalarını, adım adım rehberini ve referans çözümünü içerir.

## Klasör yapısı

| Yol | İçerik |
|-----|--------|
| `pricing.yaml` | İki modelin kimlik, fiyat, rol (üretici / doğrulayıcı) ve çağrı ayarları (tarih damgalı) |
| `kaynaklar/` | Kurgusal "Kuzey Lojistik Kargo Takip API'si" için üç Türkçe doküman |
| `sorular/` | Kaynağın tamamen ya da kısmen cevapladığı dört soru |
| `tuzaklar/` | Tuzak yerleştirilmiş örnek yanıt ve etiketleri; kendi setinizi buraya yazarsınız |
| `sonuclar/` | Yanıtlar, iddia dosyaları ve zincir kayıtları; `zincir.jsonl` gerçek bir ölçüm örneğidir |
| `Step-by-Step-GUIDE.md` | Yedi adımlık rehber: roller, kod, komutlar, beklenen çıktılar ve kontrol noktaları |
| `calisma/` | Kendi `dedektor.py` dosyanızı yazacağınız klasör |
| `cozum/adim_1.py` … `adim_6.py` | Her adımın sonunda dosyanın ulaşması gereken hâl |
| `cozum/dedektor.py` | Tam çözüm (Adım 7'nin sonu) — önce kendiniz yazın, takıldığınızda bakın |
| `kod-rehberi.html` | Referans çözümün `chain` ve `score` akışlarını adım adım anlatan etkileşimli rehber; risk skoru hesaplayıcısıyla; tarayıcıda açın |
| `kod-rehberi-yan-yana.html` | Referans çözümün tamamı solda, her parçanın açıklaması sağda; tarayıcıda açın |
| `demo.html` | Bitmiş aracın örnek komutlarını, çıktılarını ve parametrelerini gösteren demo kartı; tarayıcıda açın |
| `tests/` | Gerçek API çağrısı yapmayan testler (sahte istemci) |

## Hızlı başlangıç

```bash
cd hallucination-dedektoru
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."

python cozum/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
python cozum/dedektor.py extract sonuclar/01_iptal.md
python cozum/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
python cozum/dedektor.py chain kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt --answer tuzaklar/01_iptal_tuzakli.md
python cozum/dedektor.py score sonuclar/zincir.jsonl tuzaklar/01_iptal_tuzaklar.yaml
```

`answer`, `extract`, `verify` ve `chain` ücretli çağrı yapar (bir zincir üç çağrı); `score` kaydedilmiş sonuçlardan çalışır. Repodaki `sonuclar/zincir.jsonl` dosyasıyla `score` komutunu API anahtarı tanımlamadan deneyebilirsiniz; kendi `chain` komutunuz dosyanın sonuna ekler.

## Testler

```bash
python -m unittest discover -s tests -v
```

## Üretilen dosyalar hakkında

`Step-by-Step-GUIDE.md`, `kod-rehberi.html`, `kod-rehberi-yan-yana.html` ve `demo.html` dosyaları elle düzenlenmez; repo kökündeki `_pipeline/` aracıyla çözüm kodundan ve gerçek ölçüm çıktısından üretilir. `cozum/adim_N.py` ara sürümleri de tam çözümden türetilir (`_pipeline/projeler/hallucination-dedektoru/ara_surum_uret.py`). Bu dosyalarda bir hata görürseniz kaynağını `_pipeline/projeler/hallucination-dedektoru/` altında düzeltin ve yeniden üretin.

## Modeller ve fiyatlar hakkında

`pricing.yaml` içindeki fiyatlar ve çağrı ayarları dosyadaki `updated` tarihine aittir. API fiyatları ve kabul edilen parametreler değişebilir; üretimde kullanmadan önce [Anthropic pricing sayfasını](https://platform.claude.com/docs/en/about-claude/pricing) kontrol edin. Model kararları (hangi iddianın desteklendiği, kanıt alıntıları) çalıştırmadan çalıştırmaya değişebilir; repodaki örnek sonuçlar tek bir ölçüm anına aittir.
