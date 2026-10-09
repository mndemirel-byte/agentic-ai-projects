# Model karşılaştırma lab'ı

Agentic AI Developer Programı · Aşama 1 (LLM okuryazarlığı) · Bireysel proje

Aynı görev setini dört Claude modelinde çalıştırıp ilk token süresini, toplam gecikmeyi, maliyeti ve kaliteyi tek tabloda karşılaştıran bir CLI yaz; etiketsiz puanlamayla model kararını gerekçelendir.

> **Projeye nereden başlamalı?** Kurulumu aşağıdaki "Hızlı başlangıç" bölümüne göre yap, ardından **[Step-by-Step-GUIDE.md](Step-by-Step-GUIDE.md)** dosyasını aç. Rehber, aracı sekiz adımda sıfırdan yazman için gereken kodu, komutları, beklenen çıktıları ve kontrol noktalarını içerir.

Projenin amacı, isterleri ve pratik edeceğin kavramlar platformdaki proje sayfasındadır. Bu klasör projenin başlangıç dosyalarını, adım adım rehberini ve referans çözümünü içerir.

## Klasör yapısı

| Yol | İçerik |
|-----|--------|
| `pricing.yaml` | Dört modelin kimlik, fiyat, context window ve max output değerleri (tarih damgalı) |
| `gorevler/` | Tek görevlik deneme dosyası ve beş görevlik Türkçe görev seti (otomatik kontrolleriyle) |
| `sonuclar/` | `run` komutunun yazdığı JSONL sonuçları; `2_gorev_seti.jsonl` gerçek bir ölçüm örneğidir |
| `Step-by-Step-GUIDE.md` | Sekiz adımlık rehber: kod, komutlar, beklenen çıktılar ve kontrol noktaları |
| `calisma/` | Kendi `modellab.py` dosyanı yazacağın klasör |
| `cozum/adim_1.py` … `adim_7.py` | Her adımın sonunda dosyanın ulaşması gereken hâl |
| `cozum/modellab.py` | Tam çözüm (Adım 8'in sonu) — önce kendin yaz, takıldığında bak |
| `kod-rehberi.html` | Referans çözümün `run`, `report` ve `rate` akışlarını adım adım anlatan etkileşimli rehber; tarayıcıda aç |
| `kod-rehberi-yan-yana.html` | Referans çözümün tamamı solda, her parçanın açıklaması sağda; tarayıcıda aç |
| `demo.html` | Bitmiş aracın örnek komutlarını, çıktılarını ve parametrelerini gösteren demo kartı; tarayıcıda aç |
| `tests/` | Gerçek API çağrısı yapmayan testler (sahte streaming client ve sahte saat) |

## Hızlı başlangıç

```bash
cd model-karsilastirma-labi
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."

python cozum/modellab.py run gorevler/2_gorev_seti.yaml
python cozum/modellab.py report sonuclar/2_gorev_seti.jsonl --monthly-calls 100000
python cozum/modellab.py show sonuclar/2_gorev_seti.jsonl ozet
python cozum/modellab.py rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,C=5,D=3
```

Yalnızca `run` komutu ücretli çağrı yapar; `report`, `show` ve `rate` kaydedilmiş sonuçlardan çalışır. Repodaki `sonuclar/2_gorev_seti.jsonl` dosyasıyla bu üç komutu API anahtarı tanımlamadan deneyebilirsin; kendi `run` komutun dosyanın üzerine yazar.

## Testler

```bash
python -m unittest discover -s tests -v
```

## Üretilen dosyalar hakkında

`Step-by-Step-GUIDE.md`, `kod-rehberi.html`, `kod-rehberi-yan-yana.html` ve `demo.html` dosyaları elle düzenlenmez; repo kökündeki `_pipeline/` aracıyla çözüm kodundan ve gerçek ölçüm çıktısından üretilir. Bu dosyalarda bir hata görürsen kaynağını `_pipeline/projeler/model-karsilastirma-labi/` altında düzelt ve yeniden üret.

## Fiyatlar hakkında

`pricing.yaml` içindeki fiyatlar dosyadaki `updated` tarihine aittir. API fiyatları değişebilir; üretimde kullanmadan önce [Anthropic pricing sayfasını](https://platform.claude.com/docs/en/about-claude/pricing) kontrol et. Gecikme ölçümleri ağ koşullarına, bölgeye ve API yüküne göre değişir; repodaki örnek sonuçlar tek bir ölçüm anına aittir.
