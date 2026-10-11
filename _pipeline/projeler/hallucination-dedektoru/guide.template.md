# Hallucination dedektörü: adım adım rehber

Bu rehber, projeyi yedi adımda, iki kişi birlikte sıfırdan yazmanız için hazırlandı. Kodun tamamını `calisma/dedektor.py` dosyasında, her adımda bir öncekinin üzerine ekleyerek büyüteceksiniz. Projenin amacı, isterleri ve pratik edeceğiniz kavramlar platformdaki proje sayfasında; bu rehber yalnızca "nasıl" sorusuna odaklanıyor.

Her adım aynı yapıyı izler: **kim sürüyor**, **ne yapacaksınız**, **neden** (ilgili dersle bağlantısı), eklenecek ya da değiştirilecek **kod**, **çalıştırma** komutu, **beklenen çıktı**, iki rol için **kontrol noktası** ve varsa **yaygın hatalar**. Bir adımın kontrol noktasını geçmeden bir sonrakine geçmeyin.

**İkili çalışma biçimi.** İlk altı adımda pair programming yaparsınız: biri **sürücü** (klavyede, kodu yazar), diğeri **navigatör** (rehberi okur, satırı yazılırken sorgular, kontrol noktasını yürütür). Rol her adımda değişir; adım başlığının altında kimin sürdüğü yazar. Yedinci adımda roller ayrışır: biriniz **dedektör**, diğeriniz **tuzakçı** olur, sonra takas edersiniz. Tek dosya üzerinde çalışmanın en kolay yolu aynı bilgisayarı kullanmaktır; ayrı bilgisayarlarda çalışıyorsanız her adımın sonunda dosyayı paylaşın.

## İçindekiler

- [Başlamadan önce](#baslamadan-once)
- [Adım 1 — Kaynağa dayalı yanıt](#adim-1)
- [Adım 2 — İddia çıkarma](#adim-2)
- [Adım 3 — İddia doğrulama](#adim-3)
- [Adım 4 — Kanıt denetimi](#adim-4)
- [Adım 5 — Risk skoru ve yönlendirme](#adim-5)
- [Adım 6 — Zincir ve kayıt](#adim-6)
- [Adım 7 — Tuzak seti ve dedektör karnesi](#adim-7)
- [Takıldığında](#takildiginda)

<a id="baslamadan-once"></a>

## Başlamadan önce

Kurulumu [README.md](README.md) dosyasındaki "Hızlı başlangıç" bölümüne göre yaptığınızdan emin olun: sanal ortam etkin, bağımlılıklar kurulu ve `ANTHROPIC_API_KEY` tanımlı olmalı. Şu komut `Kurulum tamam` yazdırmalı:

```bash
python -c "import anthropic, yaml; print('Kurulum tamam')"
```

Tüm komutları proje klasöründe (`hallucination-dedektoru`) çalıştırın. Bitmiş aracın neye benzediğini görmek için başlamadan önce platformdaki proje sayfasının başındaki demoyu ya da bu klasördeki [`demo.html`](demo.html) dosyasını açabilirsiniz.

Sonra `kaynaklar/` klasöründeki üç dokümanı birlikte okuyun. Kurgusal bir şirketin kargo API'si anlatılıyor; şirket de API de gerçekte yok. Bu bilerek seçildi: model bu API'yi eğitim verisinden bilemez, dolayısıyla yanıtta dokümanda geçmeyen her ayrıntı kaynak dışıdır (Ders 1.6 §4.1). Dokümanları tanımadan dedektörün kararlarını değerlendiremezsiniz.

> [!WARNING]
> Bu projede `answer`, `extract`, `verify` ve `chain` komutları gerçek API çağrısı yapar ve ücretlendirilir. Dokümanlar birkaç bin token, yanıtlar bir paragraf ve doğrulayıcı model ucuz olduğu için rehberin tamamı birkaç sentte kalır. `score` komutu çağrı yapmaz. Yine de bir komutu döngüye sokmadan önce çağrı sayısını düşünün: `chain` tek başına üç çağrıdır.

> [!NOTE]
> Ders 1.5 §7'deki "JSON için `temperature: 0`" reçetesi bu projede uygulanmaz: Ekim 2026 itibarıyla 5.x Claude modelleri varsayılan dışı `temperature`, `top_p` ve `top_k` değerlerini reddeder (400 hatası). Çıktı biçimini prompt'taki açık JSON şablonu ve `_parse_json` fonksiyonundaki ayrıştırma belirler; düşünme ayarları `pricing.yaml > cagri_ayarlari` alanından gelir.

<a id="adim-1"></a>

## Adım 1 — Kaynağa dayalı yanıt

**Sürücü:** Partner A · **Navigatör:** Partner B

**Ne yapacaksınız:** Bir kaynak doküman ve bir soru alan, üretici modelden dokümana dayalı bir yanıt isteyen, yanıtı dosyaya yazan ve çağrının token sayılarıyla maliyetini gösteren en küçük çalışan aracı yazacaksınız. Bu adımda doğrulama yok; zincirin girdisi olan yanıtı üretiyorsunuz.

**Neden:** Ders 1.6 §5.2'deki pipeline'ın ilk iki adımı "retrieve" ve "generate"tir: önce ilgili context sağlanır, sonra model bu context'le yanıt üretir. Burada retrieval'ı en basit hâliyle yapıyorsunuz, dokümanın tamamını prompt'a koyarak; Aşama 3'te bunun yerini RAG alacak. Çağrı Ders 1.4 §3.1'deki SDK kullanımıdır ve streaming değildir: yanıtı bütün olarak işleyeceğiniz için akışın faydası yok (Ders 1.4 §4.4). `stop_reason` kontrolü Ders 1.4 §5.3'ten: kesik bir yanıtı iddialara ayırmak yarım veriyle çalışmaktır. Programı en baştan alt komutlu `argparse` ile kuruyorsunuz; sonraki adımlarda komut eklerken iskelet değişmeyecek.

Önce `pricing.yaml` dosyasını açın. Model karşılaştırma lab'ından tanıdık yapıya iki ekleme var: `roller` alanı hangi modelin üretici, hangisinin doğrulayıcı olduğunu söyler; `cagri_ayarlari` her modelde düşünmeyi en düşük ayara çeker. Kod rolleri bilmez, yalnızca dosyadan okur.

`calisma/dedektor.py` adında bir dosya oluşturun ve içine şunu yazın:

```python
{{DOSYA:cozum/adim_1.py}}
```

Kodda dikkat etmeniz gereken üç nokta var. `call_model` programın API ile konuşan tek fonksiyonudur: `kwargs` sözlüğünü kurar, modelin `cagri_ayarlari` sözlüğünü `update` ile ekler ve yanıtın `content` dizisindeki `text` bloklarını birleştirir; `usage` ve `stop_reason` alanlarını da döndürür. `generate_answer` dokümanı ve soruyu tek bir kullanıcı mesajında birleştirir; davranış çerçevesi `GENERATE_SYSTEM` ile `system` alanından gider (Ders 1.4 §1). `main` fonksiyonundaki `client=None` parametresi testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştırın:**

```bash
python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
```

**Beklenen çıktı:** İlk satırda soru, ardından modelin bir paragraflık yanıtı, altında model adı, girdi ve çıktı token sayıları ile maliyeti taşıyan tek bir satır ve `Yanıt kaydedildi: sonuclar/01_iptal.md` satırı. Girdi token sayısı dokümanın uzunluğunu yansıtır; çıktı birkaç yüz token'ı geçmez.

{{OLCUM:rehber-1}}

**Kontrol noktası (navigatör):** Yanıtı `kaynaklar/02_gonderi_uc_noktalari.md` ile karşılaştırın: her cümlenin dokümanda bir karşılığı var mı? Varsa bile bunu "göz kararı" yaptığınızı not edin; projenin geri kalanı tam olarak bu göz kararını sistematik hâle getiriyor. **Kontrol noktası (sürücü):** Maliyeti elle doğrulayın: girdi token sayısını üreticinin girdi fiyatıyla, çıktı token sayısını çıktı fiyatıyla çarpıp toplayın ve 1.000.000'a bölün. Sonra `--max-tokens` olmadığına dikkat edin: sınır `MAX_TOKENS` sözlüğünde; `answer` değerini 40'a indirip komutu tekrarlayın, çıktı satırında `UYARI: yanıt max_tokens sınırında kesildi` görmelisiniz. Bitirdiğinizde değeri geri alın.

**Yaygın hatalar:**

- `Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.` mesajı, anahtarı tanımladığınız terminalden farklı bir terminalde çalıştığınızı gösterir. `export` komutunu bu terminalde tekrarlayın.
- `ModuleNotFoundError: No module named 'anthropic'` hatası, sanal ortamın etkin olmadığını gösterir. `source .venv/bin/activate` komutunu çalıştırın.
- `Hata: pricing.yaml: 'roller' altında 'uretici' tanımlı değil.` mesajı, `pricing.yaml` dosyasını düzenlerken `roller` alanını bozduğunuzu gösterir.

<a id="adim-2"></a>

## Adım 2 — İddia çıkarma

**Sürücü:** Partner B · **Navigatör:** Partner A

**Ne yapacaksınız:** `extract` komutunu ekleyeceksiniz. Komut bir yanıt dosyasını doğrulayıcı modele gönderir, yanıtı tek tek doğrulanabilir atomik iddialara ayırmasını ister, dönen JSON'u çözer ve iddiaları hem ekrana hem bir dosyaya yazar. Bu, zincirin birinci aşamasıdır.

**Neden:** Ders 1.6 §5.2 adım 3: bir yanıt içindeki beş iddiadan dördü doğru, biri yanlış olabilir; bütüncül bir "doğru/yanlış" kararı bu ayrımı kaçırır. İddialara ayırmak, doğrulamayı yanıt düzeyinden iddia düzeyine indirir. Modelden JSON istemek ve dönen metni ayrıştırmak Ders 1.6 §5.1'deki syntactic verification'ın kendisidir: JSON çözülemezse ya da `claims` listesi boşsa program tek satırlık bir hatayla durur; bozuk çıktıyı sessizce "sıfır iddia" saymaz. `_parse_json` kod bloğu çitlerini temizler, çünkü modeller JSON'u ara sıra ```` ```json ```` içine sarar.

Dosyanın başındaki `import argparse` satırının altına `import json`, `import os` satırının altına `import re` ekleyin.

`GENERATE_SYSTEM` tanımının altına, Prompt'lar bölümünün sonuna iddia çıkarma prompt'unu ekleyin:

```python
{{SABIT:cozum/adim_2.py:EXTRACT_PROMPT}}
```

`generate_answer` fonksiyonunun altına iddia çıkarıcıyı ekleyin:

```python
{{FN:cozum/adim_2.py:extract_claims}}
```

`estimate_cost` fonksiyonunun altına JSON çözücüyü ekleyin:

```python
{{FN:cozum/adim_2.py:_parse_json}}
```

`answer_path` fonksiyonunun altına iddia dosyasının yolunu üreten yardımcıyı ekleyin:

```python
{{FN:cozum/adim_2.py:claims_path}}
```

`cmd_answer` fonksiyonunun altına yeni komutu ekleyin:

```python
{{FN:cozum/adim_2.py:cmd_extract}}
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştirin. Parser'a `--verifier` seçeneği ve `extract` komutu eklendi; `main` komutları bir sözlükten seçiyor:

```python
{{FN:cozum/adim_2.py:build_parser}}


{{FN:cozum/adim_2.py:main}}
```

`EXTRACT_PROMPT` içindeki kuralları okuyun: her iddia tek olgu, zamir yerine ad, en fazla on iddia. Yanıt `<yanit>` etiketleri arasına konur ve prompt yanıtın ne olduğunu açıkça söyler; bu ayrıntı deneyimden geliyor: yanıt "dokümanda belirtilmiyor" gibi bir cümle içerdiğinde, ne olduğu söylenmemiş bir metni alan doğrulayıcı onu iddialara bölmek yerine yorumlamaya kalkabiliyor ve JSON yerine açıklama döndürüyor. "Yorumlama, değerlendirme, düzeltme" kuralı da aynı nedenle var. Bu kurallar doğrulamanın kalitesini belirler; "bu" ya da "o" ile başlayan bir iddia kaynağa karşı tek başına kontrol edilemez. Prompt'taki `{answer}` yer tutucusu `str.replace` ile dolduruluyor, f-string ile değil; çünkü prompt'un kendisi küme parantezi içeren JSON örneği taşıyor.

**Çalıştırın:**

```bash
python calisma/dedektor.py extract sonuclar/01_iptal.md
```

**Beklenen çıktı:** `N iddia çıkarıldı:` başlığı altında numaralı iddialar, altında doğrulayıcı modelin token ve maliyet satırı ve `İddialar kaydedildi: sonuclar/01_iptal.iddialar.json` satırı. İddia sayısı yanıttaki olgu sayısına yakındır; her iddia yanıttaki bir cümleyi ya da cümle parçasını kendi başına anlaşılır hâle getirmiştir.

{{OLCUM:rehber-2}}

**Kontrol noktası (navigatör):** İddiaları yanıtla yan yana koyun. Yanıttaki bir olgu iddialarda eksik mi? Bir iddia iki olguyu birden mi taşıyor? Bu, çıkarıcının kaçırdığı bir iddianın asla doğrulanamayacağı anlamına gelir; Adım 7'de bu durumu "iddia çıkarılmadı" olarak sayacaksınız. **Kontrol noktası (sürücü):** `sonuclar/01_iptal.iddialar.json` dosyasını açıp JSON'un geçerli olduğunu görün. Sonra bir deney: yanıt dosyasının bir kopyasına "Umarım yardımcı olabilmişimdir." gibi bir nezaket cümlesi ekleyip `extract` komutunu o dosyayla çalıştırın; cümlenin iddiaya dönüşmediğini doğrulayın.

**Yaygın hatalar:**

- `Hata: İddia çıkarma: model geçerli bir {"claims": [...]} JSON'u döndürmedi.` mesajı, modelin JSON yerine açıklama yazdığını gösterir; mesajın devamında yanıtın ilk 120 karakteri vardır. Prompt'u değiştirdiyseniz JSON şablonunun ve "başka hiçbir şey yazma" talimatının yerinde olduğunu kontrol edin.
- `KeyError: 'answer'` hatası, `EXTRACT_PROMPT` içindeki yer tutucuyu f-string ile doldurmaya çalıştığınızı gösterir; `replace` kullanın.

**Bitirdiğinizde:** Dosyanız [`cozum/adim_2.py`](cozum/adim_2.py) ile aynı işi yapıyor olmalı.

<a id="adim-3"></a>

## Adım 3 — İddia doğrulama

**Sürücü:** Partner A · **Navigatör:** Partner B

**Ne yapacaksınız:** `verify` komutunu ekleyeceksiniz. Komut iddia dosyasını ve kaynağı doğrulayıcı modele tek çağrıda gönderir; her iddia için bir karar (`DESTEKLİ`, `DESTEKSİZ`, `ÇELİŞİYOR`), kaynaktan birebir bir kanıt alıntısı ve tek cümlelik gerekçe alır; sonucu hizalı bir tabloda gösterir. Bu, zincirin ikinci aşamasının LLM yarısıdır.

**Neden:** Ders 1.6 §5.1'deki grounding verification: cevap verilen kaynağa sadık mı, her iddia context'te var mı? Ders bu katmanın tam otomasyonu en zor olan katman olduğunu ve genellikle ikinci bir LLM çağrısı gerektirdiğini söylüyor; o ikinci çağrı budur. Prompt'ta iki kritik talimat var. "Kendi bilgini kullanma; kaynakta olmayan bir bilgi doğru görünse bile `unsupported` say" talimatı, doğrulayıcının parametrik bilgisini devre dışı bırakmaya çalışır (Ders 1.6 §4.1). "Kanıtı KAYNAKTAN BİREBİR kopyala" talimatı ise bir sonraki adımın hazırlığıdır: alıntı birebirse makineyle denetlenebilir. Tüm iddiaların tek çağrıda gitmesi maliyet kararıdır; iddia başına ayrı çağrı daha bağımsız kararlar verir ama N kat pahalıdır.

`MAX_TOKENS` tanımının altına karar etiketlerini ekleyin. `suspect` anahtarı bu adımda kullanılmaz; Adım 4'teki kanıt denetimi için şimdiden yerinde:

```python
{{SABIT:cozum/adim_3.py:VERDICT_LABELS}}
```

`EXTRACT_PROMPT` tanımının altına doğrulama prompt'unu ekleyin:

```python
{{SABIT:cozum/adim_3.py:VERIFY_PROMPT}}
```

`read_question` fonksiyonunun altına iddia dosyasını okuyan fonksiyonu ekleyin:

```python
{{FN:cozum/adim_3.py:load_claims}}
```

`extract_claims` fonksiyonunun altına doğrulayıcıyı ekleyin:

```python
{{FN:cozum/adim_3.py:verify_claims}}
```

`wrap_text` fonksiyonunun altına üç biçimlendirme yardımcısı ekleyin: metin kısaltıcı, hizalı tablo ve karar tablosu:

```python
{{FN:cozum/adim_3.py:shorten}}


{{FN:cozum/adim_3.py:print_table}}


{{FN:cozum/adim_3.py:print_verdicts}}
```

`cmd_extract` fonksiyonunun altına yeni komutu ekleyin:

```python
{{FN:cozum/adim_3.py:cmd_verify}}
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştirin:

```python
{{FN:cozum/adim_3.py:build_parser}}


{{FN:cozum/adim_3.py:main}}
```

`verify_claims` üç şeyi doğrular: dönen `results` listesinin uzunluğu iddia sayısına eşit mi, her kararın değeri tanınan üç değerden biri mi, `evidence` ve `note` metin mi. Model bir iddiayı atlar ya da yeni bir karar adı uydurursa program sessizce devam etmek yerine durur. Ders 1.6'nın mesajını kendi aracınıza uyguluyorsunuz: doğrulayıcı da bir LLM'dir ve onun çıktısı da doğrulanır.

**Çalıştırın:**

```bash
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
```

**Beklenen çıktı:** İddia başına bir satırlık tablo: `#`, `İddia`, `Karar`, `Kanıt` (alıntının başı) ve `Not` sütunları. Kaynağın tamamen cevapladığı bu soruda kararların tamamı ya da tamamına yakını `DESTEKLİ`dir. Referans ölçümde altı iddiadan biri (müşteri hizmetleriyle iletişim) `DESTEKSİZ` çıktı, oysa kaynak bunu açıkça söylüyor: doğrulayıcı da bir modeldir ve yanlış alarm verebilir; bunu Adım 7'de sayacaksınız. Altta doğrulayıcının token ve maliyet satırı vardır; girdi token sayısı dokümanın tamamı gittiği için `extract` adımından belirgin biçimde yüksektir.

{{OLCUM:rehber-3}}

**Kontrol noktası (navigatör):** Tablodaki bir kanıt alıntısını seçin ve kaynak dosyada arayın (`Ctrl+F`). Birebir geçiyor mu, yoksa model alıntıyı "düzelterek" mi yazmış? Bu soruyu her satır için elle sormak, bir sonraki adımın kodunu neden yazacağınızı anlatır. **Kontrol noktası (sürücü):** `sonuclar/01_iptal.iddialar.json` dosyasına, kaynakta olmayan bir iddia ekleyin (ör. "İptal edilen gönderiler için ücret iadesi 3 iş günü sürer.") ve `verify` komutunu tekrarlayın; yeni satırın `DESTEKSİZ` olduğunu görün. Bitirdiğinizde eklediğiniz satırı silin.

**Yaygın hatalar:**

- `Hata: Doğrulama: model 6 iddia için 5 sonuç döndürdü` mesajı, modelin bir iddiayı atladığını gösterir. Komutu tekrarlayın; sorun sürüyorsa `MAX_TOKENS["verify"]` değerini artırın, yanıt kesilmiş olabilir.
- `Hata: ... 'claims' listesi boş ya da hatalı. Önce 'extract' komutunu çalıştır.` mesajı, `verify` komutuna iddia dosyası yerine yanıt dosyasını verdiğinizi gösterir.

**Bitirdiğinizde:** Dosyanız [`cozum/adim_3.py`](cozum/adim_3.py) ile aynı işi yapıyor olmalı.

<a id="adim-4"></a>

## Adım 4 — Kanıt denetimi

**Sürücü:** Partner B · **Navigatör:** Partner A

**Ne yapacaksınız:** Doğrulayıcının gösterdiği her kanıt alıntısının kaynakta gerçekten geçip geçmediğini kodla kontrol edeceksiniz. Alıntı kaynakta yoksa `DESTEKLİ` karar `ŞÜPHELİ`ye düşer; tablonun `Kanıt` sütunu alıntı yerine denetim sonucunu gösterir. Bu, zincirin ikinci aşamasının deterministik yarısıdır ve projeye adını veren "iki aşamalı" yapının ikinci aşamasını tamamlar.

**Neden:** Ders 1.6 §3.4'teki uyarı: "Kaynak göstermek yeterli değildir. Model bazen citation varmış gibi davranır; source-looking bir cevap ile source-grounded bir cevap arasındaki fark hayati bir ayrımdır." Doğrulayıcı da bir modeldir ve aynı tuzağa düşebilir: bir iddiayı `DESTEKLİ` ilan edip kaynakta olmayan, kaynağa benzeyen bir "alıntı" yazabilir. LLM kararının arkasına deterministik bir kontrol koymak, Ders 1.6 §5.1'deki "self-consistency doğruluğu değil kararsızlığı ölçer" uyarısının pratik karşılığıdır: aynı modele ikinci kez sormak yerine, modelin dışında bir kaynağa, metnin kendisine bakıyorsunuz. Karşılaştırma noktalama, boşluk ve büyük-küçük harf farklarını yok sayar; Türkçe'de `I` ile `İ` ayrımı Python'un `lower()` fonksiyonunda doğru çalışmadığı için küçük bir yardımcı yazıyorsunuz.

`_parse_json` fonksiyonunun altına dört fonksiyon ekleyin: Türkçe küçük harf, metin sadeleştirme, kanıt arama ve denetimi uygulayan fonksiyon:

```python
{{FN:cozum/adim_4.py:tr_lower}}


{{FN:cozum/adim_4.py:normalize_text}}


{{FN:cozum/adim_4.py:evidence_found}}


{{FN:cozum/adim_4.py:apply_evidence_check}}
```

`print_verdicts` fonksiyonunu, `Kanıt` sütununda denetim sonucunu gösteren şu hâliyle değiştirin:

```python
{{FN:cozum/adim_4.py:print_verdicts}}
```

`cmd_verify` fonksiyonunu, doğrulamadan sonra denetimi uygulayan şu hâliyle değiştirin:

```python
{{FN:cozum/adim_4.py:cmd_verify}}
```

`normalize_text` yalnızca harf ve rakamları tutar: "`409 Conflict` döner." metni `409conflictdöner` olur. Bu sayede modelin alıntıda ters tırnağı atması ya da bir virgülü değiştirmesi eşleşmeyi bozmaz; ama bir kelimeyi değiştirmesi bozar. Denetim kasıtlı olarak katıdır: bulanık eşleme yok. Katı bir denetim bazen doğru alıntıyı da reddeder; bu yanlış alarmları Adım 7'de sayacaksınız.

**Çalıştırın:** Bu kez tuzaklı bir yanıtla çalışın. `tuzaklar/01_iptal_tuzakli.md` dosyası, aynı soruya verilmiş bir yanıtın içine kaynakta olmayan üç cümle yerleştirilmiş hâlidir (Adım 7'de kendi setinizi yapacaksınız).

```bash
python calisma/dedektor.py extract tuzaklar/01_iptal_tuzakli.md --out sonuclar/01_iptal_tuzakli.iddialar.json
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal_tuzakli.iddialar.json
```

**Beklenen çıktı:** `extract` tuzaklı yanıttan daha uzun bir iddia listesi çıkarır. `verify` tablosunda `Kanıt` sütunu artık üç değerden birini gösterir: `kaynakta` (alıntı bulundu), `kaynakta YOK` (model alıntı verdi ama kaynakta geçmiyor; karar `ŞÜPHELİ`ye düştü) ya da `yok` (model alıntı vermedi; `DESTEKSİZ` kararlarda beklenen durum). Yerleştirilen cümlelere karşılık gelen iddialar `DESTEKSİZ` ya da `ŞÜPHELİ` olmalıdır; hangisinin hangisi olduğu çalıştırmaya göre değişir. Referans ölçümde doğrulayıcının verdiği her alıntı kaynakta bulundu, dolayısıyla `ŞÜPHELİ` görünmedi; üç tuzak da `DESTEKSİZ`. Dördüncü bir `DESTEKSİZ` daha var: `iptal_edilemez` hata kodu. Bu bilgi `kaynaklar/03_webhook_ve_hatalar.md` dokümanında doğru, ama zincire verilen kaynak `02_gonderi_uc_noktalari.md`; doğrulayıcı "kendi bilgini kullanma" talimatına uyup yalnızca verilen kaynağa baktı. Doğru bir bilginin bu kaynağa göre desteksiz olması hata değil, grounding'in tanımıdır.

{{OLCUM:rehber-4a,rehber-4b}}

**Kontrol noktası (navigatör):** `tuzaklar/01_iptal_tuzaklar.yaml` dosyasını açmadan, tabloya bakarak yerleştirilen üç cümleyi bulmaya çalışın; sonra dosyayı açıp kendinizi puanlayın. **Kontrol noktası (sürücü):** `evidence_found` fonksiyonunu kasıtlı bir hatayla deneyin: `normalize_text` içindeki `tr_lower` çağrısını `lower()` ile değiştirip komutu tekrarlayın. `İ` harfi içeren bir alıntı (`İptal`, `İmza`) artık bulunamaz ve `kaynakta YOK` olur. Bitirdiğinizde geri alın.

**Yaygın hatalar:**

- Tüm `DESTEKLİ` kararlar `ŞÜPHELİ`ye düşüyorsa `evidence_found` içinde kaynağı değil kanıtı sadeleştirip kanıtı değil kaynağı aramış olabilirsiniz; `normalized in normalize_text(source)` sırasına bakın.
- `KeyError: 'kanit_bulundu'` hatası, `print_verdicts` fonksiyonunu `apply_evidence_check` çağrılmadan kullandığınızı gösterir; `cmd_verify` içindeki sıraya bakın.

**Bitirdiğinizde:** Dosyanız [`cozum/adim_4.py`](cozum/adim_4.py) ile aynı işi yapıyor olmalı.

<a id="adim-5"></a>

## Adım 5 — Risk skoru ve yönlendirme

**Sürücü:** Partner A · **Navigatör:** Partner B

**Ne yapacaksınız:** Kararları tek bir risk skoruna çevirecek ve skora göre yanıtı `KABUL`, `İNCELE` ya da `RET` olarak yönlendireceksiniz. `verify` komutu `--threshold` seçeneği alacak ve tablonun altında karar dağılımı, skor ve yönlendirme satırları basacak.

**Neden:** Ders 1.6 §5.2'nin son iki adımı: doğrulama sonuçlarını risk skoruna dönüştür, skora göre yönlendir (otomatik kabul, insan onayı, ret). Skor ağırlıklı bir ortalamadır: `DESTEKSİZ` ve `ÇELİŞİYOR` tam puan, `ŞÜPHELİ` yarım puan, `DESTEKLİ` sıfır. Eşik ise Ders 1.6 §5.3'teki risk matrisinin tek sayıya indirilmiş hâlidir: hatanın geri dönüş maliyeti yüksekse eşik düşer, daha çok yanıt insana gider. `ÇELİŞİYOR` kararının eşikten bağımsız `RET` vermesi bilinçli bir kuraldır; kaynağın aksini söyleyen bir yanıt skoru ne olursa olsun kullanıcıya gitmemelidir.

`VERDICT_LABELS` tanımının altına ağırlıkları, yönlendirme etiketlerini ve varsayılan eşiği ekleyin:

```python
{{SABIT:cozum/adim_5.py:RISK_WEIGHTS}}

{{SABIT:cozum/adim_5.py:ROUTE_ACCEPT}}
{{SABIT:cozum/adim_5.py:DEFAULT_THRESHOLD}}
```

`apply_evidence_check` fonksiyonunun altına skor ve yönlendirme fonksiyonlarını ekleyin:

```python
{{FN:cozum/adim_5.py:risk_score}}


{{FN:cozum/adim_5.py:route}}
```

`fmt_usd` fonksiyonunun altına skor biçimlendiricisini, `print_verdicts` fonksiyonunun altına özet satırlarını basan fonksiyonu ekleyin:

```python
{{FN:cozum/adim_5.py:fmt_score}}
```

```python
{{FN:cozum/adim_5.py:print_summary}}
```

`cmd_verify` fonksiyonunu şu hâliyle değiştirin:

```python
{{FN:cozum/adim_5.py:cmd_verify}}
```

`build_parser` içinde `p_verify.add_argument("claims", ...)` satırının altına yeni seçeneği ekleyin:

```python
    p_verify.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="İNCELE için en yüksek risk skoru (varsayılan: 0.25)")
```

`route` içindeki sıraya dikkat edin: önce çelişki, sonra sıfır skor, sonra eşik. Sıra değişirse çelişen bir iddia eşiğin altında kalıp `İNCELE` ile geçebilir.

**Çalıştırın:** Önce tuzaklı iddialarla, sonra temiz iddialarla ve gevşetilmiş bir eşikle:

```bash
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal_tuzakli.iddialar.json
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json --threshold 0.5
```

**Beklenen çıktı:** Tablonun altında iki yeni satır: karar dağılımı (`N iddia: a destekli, b desteksiz, ...`) ve `Risk skoru: X (eşik Y)  →  YÖNLENDİRME`. Tuzaklı iddialarda skor sıfırdan belirgin biçimde büyüktür ve yönlendirme `RET`tir (referans ölçümde 8 iddianın 4'ü desteksiz, skor 0,50). Temiz iddialarda skor sıfır ya da sıfıra yakındır ve yönlendirme `KABUL` ya da `İNCELE` olur; referans ölçümde iki iddia `DESTEKSİZ` çıktı ve skor 0,33 ile gevşetilmiş eşiğin altında `İNCELE` verdi. Bu iki iddiaya bakın: çıkarıcı "kurye topladıktan sonra" bağlamını "iptal edilemediğinde" diye genelleştirmiş, doğrulayıcı da genelleşmiş ifadeyi kaynakta bulamamış. Yanlış alarmın kaynağı bazen doğrulayıcı değil, çıkarıcıdır.

{{OLCUM:rehber-5a,rehber-5b}}

**Kontrol noktası (navigatör):** Tuzaklı tablodaki skoru elle hesaplayın: kararların ağırlıklarını toplayıp iddia sayısına bölün; ekrandaki değerle tutmalı. **Kontrol noktası (sürücü):** Tuzaklı iddiaları `--threshold 1.0` ile çalıştırın; yönlendirme `İNCELE`ye döner (çelişki yoksa). Şimdi Ders 1.6 §5.3'teki matrisi düşünün: bu araç bir "kod açıklaması" için mi, bir "database migration" için mi çalışıyor olsaydı eşiği nereye koyardınız?

**Bitirdiğinizde:** Dosyanız [`cozum/adim_5.py`](cozum/adim_5.py) ile aynı işi yapıyor olmalı.

<a id="adim-6"></a>

## Adım 6 — Zincir ve kayıt

**Sürücü:** Partner B · **Navigatör:** Partner A

**Ne yapacaksınız:** `chain` komutunu ekleyeceksiniz: üret, iddialara ayır, doğrula ve yönlendir; çağrı sayısını ve toplam maliyeti göster; sonucu bir JSONL dosyasının sonuna ekle. `--answer` ile hazır bir yanıt dosyası verildiğinde üretim atlanır; tuzaklı yanıtlar böyle zincire girer.

**Neden:** Ders 1.6 §5.2'deki pipeline'ı artık tek komutla çalıştırıyorsunuz. Maliyet satırı Ders 1.4 §6.3'ün dersidir: tek bir zincir üç çağrıdır ve doğrulayıcı, dokümanın tamamını her seferinde okur; üretim ucuz görünse de doğrulama katmanı toplam maliyetin büyük kısmı olabilir. Ders 1.7'nin TCO mantığı buradan okunur: ucuz bir doğrulayıcı (Haiku) pahalı bir üreticinin (Sonnet) yanıtını denetliyor; `--verifier` ile tersini de deneyebilirsiniz. Kaydın JSONL olması model karşılaştırma lab'ından tanıdık: her zincir bir satır, dosyanın sonuna eklenir, sonraki komut bu dosyadan okur.

Dosyanın başındaki `import textwrap` satırının altına `from datetime import datetime` satırını ekleyin.

`DEFAULT_RESULTS_DIR` tanımının altına varsayılan kayıt dosyasını ekleyin:

```python
{{SABIT:cozum/adim_6.py:DEFAULT_CHAIN_PATH}}
```

`write_text` fonksiyonunun altına kayıt fonksiyonunu ekleyin:

```python
{{FN:cozum/adim_6.py:save_record}}
```

`cmd_verify` fonksiyonunun altına zincir komutunu ekleyin:

```python
{{FN:cozum/adim_6.py:cmd_chain}}
```

`build_parser` içinde `return parser` satırının hemen üstüne yeni komutu ekleyin:

```python

    p_chain = sub.add_parser("chain", help="Üç adımı uç uca çalıştır ve sonucu kaydet (ücretli)")
    p_chain.add_argument("source", help="Kaynak doküman")
    p_chain.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_chain.add_argument("--answer", help="Hazır yanıt dosyası; verilirse üretim atlanır (tuzaklı yanıt için)")
    p_chain.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="İNCELE için en yüksek risk skoru (varsayılan: 0.25)")
    p_chain.add_argument("--out", help="Kayıt dosyası (varsayılan: sonuclar/zincir.jsonl)")
```

`main` fonksiyonunu şu hâliyle değiştirin:

```python
{{FN:cozum/adim_6.py:main}}
```

`cmd_chain` içindeki kayıt sözlüğüne bakın: iddialar kararlarıyla birlikte, skor, eşik, yönlendirme, çağrı sayısı ve maliyet. `uretici` alanı `--answer` verildiğinde `None` olur; kaydı okuyan biri yanıtın modelden mi dosyadan mı geldiğini görür.

**Çalıştırın:** Önce kaynağın kısmen cevapladığı bir soruyla, sonra tuzaklı yanıtla:

```bash
python calisma/dedektor.py chain kaynaklar/03_webhook_ve_hatalar.md sorular/03_webhook_imza.txt
python calisma/dedektor.py chain kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt --answer tuzaklar/01_iptal_tuzakli.md
```

**Beklenen çıktı:** İlk komutta soru, üreticinin yanıtı, `Aşama 1` ve `Aşama 2` satırları, karar tablosu, özet, `3 çağrı, toplam $...` ve `Kaydedildi: sonuclar/zincir.jsonl`. Webhook sorusunun iki ayrıntısı (imzanın geçerlilik süresi, zaman damgası) dokümanda yoktur; modelin bu boşluğu nasıl geçtiği tabloda görünür. Referans ölçümde Sonnet boşluğu doldurmadı, "dokümanda belirtilmiyor" dedi; çıkarıcı bu cümleleri de iddia yaptı ("Doküman imzanın kaç saniye geçerli olduğunu belirtmez.") ve doğrulayıcı kaynakta böyle bir bilgi olmadığı için onları `DESTEKSİZ` saydı: 10 iddianın 3'ü desteksiz, skor 0,30, yönlendirme `RET`. Model dürüst davrandı, dedektör yine de yanıtı reddetti; bunu kontrol noktasında tartışacaksınız. Aynı soru referans demoda 9 iddia üretip 0,22 ile `İNCELE` aldı: iddia sayısı çalıştırmadan çalıştırmaya değişir ve eşiğe yakın skorlarda yönlendirmeyi değiştirir (Ders 1.5 §5). İkinci komutta `Yanıt dosyadan okundu ... (üretim atlandı)` satırı ve `2 çağrı` görürsünüz.

{{OLCUM:rehber-6a,rehber-6b}}

**Kontrol noktası (navigatör):** İlk zincirde modelin boşluğu nasıl geçtiğini Ders 1.6 §3'teki taksonomiyle adlandırın: boşluğu kabul etmek mi, confabulation mı? Sonra dedektörün kararını tartışın: "doküman X'i belirtmez" iddiası kaynağa göre desteksizdir, ama kullanıcıya zararlı mı? Bir yanıtın reddedilmesi için kaynak dışı olması yeterli mi, yoksa kaynak dışı *olgu* mu gerekir? Bu, `VERIFY_PROMPT`'a ya da risk ağırlıklarına yapacağınız ilk değişikliğin konusudur. **Kontrol noktası (sürücü):** `sonuclar/zincir.jsonl` dosyasını açın; iki satır olmalı. İkinci satırın `uretici` alanı `null`, `cagri` alanı 2 olmalı. Sonra `--verifier sonnet-5-5` ile tuzaklı zinciri tekrarlayıp maliyeti ve kararları karşılaştırın; pahalı doğrulayıcı daha çok tuzak mı yakalıyor?

**Yaygın hatalar:**

- `Hata: tuzaklar/...: dosya boş.` mesajı, `--answer` ile yanlış dosyayı (ör. YAML tuzak setini) verdiğinizi gösterir; `--answer` yanıt metnini alır.
- Kayıt dosyası her çalıştırmada büyür; bu beklenen davranıştır. Temiz başlamak için dosyayı silin ya da `--out` ile başka dosya verin.

**Bitirdiğinizde:** Dosyanız [`cozum/adim_6.py`](cozum/adim_6.py) ile aynı işi yapıyor olmalı.

<a id="adim-7"></a>

## Adım 7 — Tuzak seti ve dedektör karnesi

**Dedektör:** Partner A · **Tuzakçı:** Partner B (sonra takas)

**Ne yapacaksınız:** `score` komutunu ekleyeceksiniz: bir tuzak setindeki her tuzak için ilgili iddiayı bulur, dedektörün kararını beklentiyle karşılaştırır ve yakalama oranı ile yanlış alarm sayısını basar. Sonra kendi tuzak setinizi kuracaksınız.

**Neden:** Ders 1.6 §4.3: model ne kadar iyi yazarsa hallucination o kadar zor tespit edilir ve tespit mekanizmasına yatırım model kalitesiyle birlikte artmalıdır. Bir dedektörün iyi olup olmadığını bilmenin tek yolu, cevabını bildiğiniz hatalarla sınamaktır; bu Ders 1.5 §6'daki eval refleksinin bu projeye uygulanmış hâlidir ve Aşama 8'deki red team / blue team tatbikatının ilk provasıdır. Kontrol cümlesi (kaynaktaki doğru bilginin farklı ifadesi) en az tuzaklar kadar önemlidir: her şeyi işaretleyen bir dedektör tüm tuzakları yakalar ama işe yaramaz.

Kodu hangi rol yazarsa yazsın, bu adımda ikiniz de aynı dosyada çalışıyorsunuz; aşağıdaki ekleri birlikte yapın.

`DEFAULT_THRESHOLD` tanımının altına geçerli beklenti değerlerini ekleyin:

```python
{{SABIT:cozum/dedektor.py:TRAP_EXPECTATIONS}}
```

`load_claims` fonksiyonunun altına tuzak setini okuyan fonksiyonu ekleyin:

```python
{{FN:cozum/dedektor.py:load_traps}}
```

`route` fonksiyonunun altına eşleştirme ve değerlendirme fonksiyonlarını ekleyin:

```python
{{FN:cozum/dedektor.py:match_claims}}


{{FN:cozum/dedektor.py:judge_trap}}
```

`save_record` fonksiyonunun altına kayıt okuyucuyu ekleyin:

```python
{{FN:cozum/dedektor.py:load_records}}
```

`cmd_chain` fonksiyonunun altına karne komutunu ekleyin:

```python
{{FN:cozum/dedektor.py:cmd_score}}
```

`build_parser` içinde `return parser` satırının hemen üstüne yeni komutu ekleyin:

```python

    p_score = sub.add_parser("score", help="Tuzak setini zincir kaydıyla karşılaştır (çağrı yapmaz)")
    p_score.add_argument("results", help="chain komutunun yazdığı JSONL dosyası")
    p_score.add_argument("traps", help="Tuzak seti (YAML)")
```

`main` fonksiyonunu şu hâliyle değiştirin. `score` komutu API istemcisi gerektirmediği için anahtar kontrolünden önce yönlendiriliyor:

```python
{{FN:cozum/dedektor.py:main}}
```

`match_claims` tuzağı iddiaya metinle bağlar: tuzak dosyasındaki `anahtar` parçalarının hepsi iddiada geçmeli, `|` ile alternatif yazılabilir (`"2 saat|iki saat"`). Çıkarıcı iddiayı yeniden ifade ettiği için cümlenin tamamı değil, ayırt edici parçası aranır. `judge_trap` beş sonuç üretir: `yakalandı` ve `kaçtı` yerleştirilen hatalar için, `doğru geçti` ve `yanlış alarm` kontrol cümleleri için, `iddia çıkarılmadı` ise cümlenin hiçbir iddiaya dönüşmediği durum için. Son durum dedektörün değil çıkarıcının hatasıdır ve ayrı sayılır.

**Çalıştırın:**

```bash
python calisma/dedektor.py score sonuclar/zincir.jsonl tuzaklar/01_iptal_tuzaklar.yaml
```

**Beklenen çıktı:** Kullanılan zincir kaydının zamanı ve yönlendirmesi, ardından tuzak başına bir satır: tür, anahtar, eşleşen iddia sayısı, karar ve sonuç. Altta `Yakalama: k/3 tuzak yakalandı` ve `Yanlış alarm: m/1 kontrol cümlesi haksız yere işaretlendi` satırları.

{{OLCUM:rehber-7}}

**Şimdi kendi setiniz.** Tuzakçı, dedektörün görmediği bir yerde çalışır:

1. `answer` ile yeni bir soruya yanıt alın (`sorular/02_hiz_limiti.txt` iyi bir başlangıç) ve `sonuclar/` altındaki yanıtı `tuzaklar/` altına kopyalayın.
2. Kopyaya üç cümle ekleyin: kaynakta hiç olmayan bir nesne (fabrication: var olmayan bir uç nokta, başlık ya da parametre), kaynaktaki gerçek bir nesnenin uydurma bir ayrıntısı (confabulation: bir limit, süre ya da varsayılan değer) ve kaynaktaki iki doğru bilginin yanlış birleşimi (conflation). Bir de kontrol cümlesi seçin: kaynaktaki bir bilgiyi yanıttakinden farklı sözcüklerle yazın.
3. `tuzaklar/01_iptal_tuzaklar.yaml` yapısında bir YAML yazın; her tuzağa ayırt edici bir `anahtar` verin.

Dedektör ise yalnızca tuzaklı yanıt dosyasını alır, `chain --answer` ile zinciri çalıştırır ve tabloya bakarak hangi cümlelerin yerleştirilmiş olduğunu tahmin eder. Sonra tuzakçı YAML dosyasını açıklar ve `score` birlikte çalıştırılır. Ardından roller takas edilir.

**Kontrol noktası (dedektör):** Kaçan bir tuzak varsa nedenini sınıflandırın: iddia hiç çıkarılmadı mı (çıkarıcı sorunu), iddia `DESTEKLİ` sayıldı ve kanıt kaynakta bulundu mu (doğrulayıcı sorunu), yoksa anahtar iddiayı yakalamadı mı (tuzak dosyası sorunu)? Her biri farklı yerde düzeltilir. **Kontrol noktası (tuzakçı):** Kontrol cümleniz yanlış alarm verdiyse, kanıt denetiminin mi yoksa doğrulayıcının mı işaretlediğine bakın; `Kanıt` sütunu söyler. Denetim fazla katıysa bu bir tasarım kararıdır: kaç yanlış alarmı kaç kaçan tuzağa değişirsiniz?

**Bitirdiğinizde:** Dosyanız [`cozum/dedektor.py`](cozum/dedektor.py) ile aynı işi yapıyor olmalı. Bunu doğrulamanın en hızlı yolu iki dosyayı karşılaştırmaktır:

```bash
diff calisma/dedektor.py cozum/dedektor.py
```

Fark yalnızca yorum satırlarında ya da docstring'deyse projeyi tamamladınız.

<a id="takildiginda"></a>

## Takıldığında

- **Ara sürümle karşılaştırın.** Her adımın sonunda dosyanın ulaşması gereken hâl `cozum/adim_N.py` dosyasında. Farkı görmek için: `diff calisma/dedektor.py cozum/adim_4.py`
- **Ara sürümden devam edin.** Dosyanız bozulduysa o adımın ara sürümünü kopyalayıp oradan ilerleyebilirsiniz: `cp cozum/adim_4.py calisma/dedektor.py`
- **Satırın nedenini okuyun.** [`kod-rehberi-yan-yana.html`](kod-rehberi-yan-yana.html) tam çözümün her parçasının karşısında açıklamasını gösterir; [`kod-rehberi.html`](kod-rehberi.html) `chain` ve `score` komutlarının kodda hangi fonksiyonlardan geçtiğini adım adım izletir.
- **Parametreleri hatırlayın.** [`demo.html`](demo.html) sayfasının "Parametreler" sekmesi tüm komutları ve seçenekleri örnekleriyle açıklar; aynı listeyi `python calisma/dedektor.py chain --help` ile terminalde de görebilirsiniz.
- **Çağrı yapmadan deneyin.** `sonuclar/zincir.jsonl` dosyası repoda gerçek bir ölçümle gelir; `score` komutunu API anahtarı olmadan bu dosyayla deneyebilirsiniz. Kendi `chain` komutunuz dosyanın sonuna ekler.

Projeyi bitirdiğinizde platformdaki proje sayfasının "Kontrol noktaları" listesini gözden geçirin; listedeki her madde projenin bir isterine karşılık gelir.
