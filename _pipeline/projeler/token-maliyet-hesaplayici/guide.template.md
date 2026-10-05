# Token maliyet hesaplayıcı: adım adım rehber

Bu rehber, projeyi yedi adımda sıfırdan yazman için hazırlandı. Kodun tamamını `calisma/tokenhesap.py` dosyasında, her adımda bir öncekinin üzerine ekleyerek büyüteceksin. Projenin amacı, isterleri ve pratik edeceğin kavramlar platformdaki proje sayfasında; bu rehber yalnızca "nasıl" sorusuna odaklanıyor.

Her adım aynı yapıyı izler: **ne yapacaksın**, **neden** (ilgili dersle bağlantısı), eklenecek ya da değiştirilecek **kod**, **çalıştırma** komutu, **beklenen çıktı**, **kontrol noktası** ve varsa **yaygın hatalar**. Bir adımın kontrol noktasını geçmeden bir sonrakine geçme.

## İçindekiler

- [Başlamadan önce](#baslamadan-once)
- [Adım 1 — İlk sayım](#adim-1)
- [Adım 2 — Taban ölçümü](#adim-2)
- [Adım 3 — Fiyatlar, maliyet ve tablo](#adim-3)
- [Adım 4 — Dört model](#adim-4)
- [Adım 5 — Context doluluğu](#adim-5)
- [Adım 6 — Türkçe ile İngilizce](#adim-6)
- [Adım 7 — Tahmin ile gerçeği karşılaştır](#adim-7)
- [Takıldığında](#takildiginda)

<a id="baslamadan-once"></a>

## Başlamadan önce

Kurulumu [README.md](README.md) dosyasındaki "Hızlı başlangıç" bölümüne göre yaptığından emin ol: sanal ortam etkin, bağımlılıklar kurulu ve `ANTHROPIC_API_KEY` tanımlı olmalı. Şu komut `Kurulum tamam` yazdırmalı:

```bash
python -c "import anthropic, yaml; print('Kurulum tamam')"
```

Tüm komutları proje klasöründe (`token-maliyet-hesaplayici`) çalıştır. Bitmiş aracın neye benzediğini görmek için başlamadan önce platformdaki proje sayfasının başındaki demoyu ya da bu klasördeki [`demo.html`](demo.html) dosyasını açabilirsin.

<a id="adim-1"></a>

## Adım 1 — İlk sayım

**Ne yapacaksın:** Tek bir metin dosyasının Claude Haiku 4.5'te kaç girdi token'ı tuttuğunu ölçen en küçük çalışan aracı yazacaksın. Bu adımda fiyat, tablo ya da birden fazla model yok; yalnızca bir API çağrısı ve sonucu.

**Neden:** Ders 1.4'te `count_tokens` ile çağrı öncesi ölçümü gördün. Bu adımda o çağrıyı kendi aracının çekirdeğine yerleştiriyorsun. Sonraki her adım bu çekirdeğin etrafına bir katman ekleyecek. Programı en baştan `argparse` ile alt komut (`count`) alacak şekilde kuruyoruz; Adım 6'da ikinci komutu eklerken yapıyı değiştirmek zorunda kalmayacaksın.

`calisma/tokenhesap.py` adında bir dosya oluştur ve içine şunu yaz:

```python
{{DOSYA:cozum/adim_1.py}}
```

Kodda dikkat etmen gereken üç nokta var. `build_messages`, metni API'nin beklediği rol-içerik yapısına sokar; token sayımı bu yapı üzerinden yapıldığı için sonuç metnin kendisinden biraz fazla çıkacak. `count_input_tokens` projenin kalbidir: API'ye mesajı gönderir ama model çalışmaz, yalnızca token sayısı döner. `main` fonksiyonundaki `client=None` parametresi ise testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt
```

**Beklenen çıktı:** İlk satırda dosya adı ve `86 karakter, 10 kelime` bilgisi, ikinci satırda `Claude Haiku 4.5 girdi token:` ifadesi ve ardından iki basamaklı bir sayı görmelisin.

{{OLCUM:rehber-1}}

**Kontrol noktası:** Sayı, 10 kelimelik bir cümle için makul mü? Kelime sayısından birkaç kat fazlaysa ya da birkaç token'dan ibaretse bir şeyler yanlıştır. Komutu iki kez çalıştır; aynı metin her seferinde aynı sayıyı vermeli.

**Yaygın hatalar:**

- `Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.` mesajı, anahtarı tanımladığın terminalden farklı bir terminalde çalıştığını gösterir. `export` komutunu bu terminalde tekrarla.
- `ModuleNotFoundError: No module named 'anthropic'` hatası, sanal ortamın etkin olmadığını gösterir. `source .venv/bin/activate` komutunu çalıştır.
- `anthropic.AuthenticationError` hatası, anahtarın yanlış kopyalandığını gösterir. Başta ve sonda boşluk kalıp kalmadığına bak.

<a id="adim-2"></a>

## Adım 2 — Taban ölçümü

**Ne yapacaksın:** `--baseline` seçeneği ekleyecek, neredeyse boş bir mesajı ayrıca sayarak mesaj iskeletinin token payını bulacak ve bunu toplamdan çıkararak metnin kendi payını hesaplayacaksın.

**Neden:** Ders 1.3'te özel token'ları gördün: model metni çıplak olarak değil, konuşmanın yapısını belirten işaretlerle birlikte okur. Adım 1'deki sayı bu işaretleri de içeriyor. Kısa bir metinde bu iskeletin payı büyüktür; uzun bir metinde önemsizleşir. Bunu kendi gözünle görmek, "bu prompt kaç token" sorusuna verdiğin cevabı daha kesin kılar.

`MODEL_NAME` satırının altına taban ölçümü için kullanılacak sabiti ekle:

```python
{{SABIT:cozum/adim_2.py:BASELINE_TEXT}}
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
{{FN:cozum/adim_2.py:cmd_count}}
```

`build_parser` içinde `p_count.add_argument("file", ...)` satırının altına yeni seçeneği ekle:

```python
    p_count.add_argument("--baseline", action="store_true", help="Mesaj iskeletinin taban token'ını ve net metin token'ını göster")
```

Taban ölçümünde boş metin yerine tek bir nokta kullanıyoruz, çünkü API içeriği boş bir mesajı kabul etmez. Bu yüzden Net değeri, noktanın kendi token'ı kadar yaklaşık bir değerdir; çıktıda da bunu belirtiyoruz.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt --baseline
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --baseline
```

**Beklenen çıktı:** Her iki komutta da Adım 1'deki iki satırın altına `Taban (mesaj iskeleti):` ve `Net (metnin kendi payı, yaklaşık):` satırları gelir. Taban değeri iki dosyada aynıdır, çünkü iskelet metinden bağımsızdır.

{{OLCUM:rehber-2a,rehber-2b}}

**Kontrol noktası:** Kısa cümlede tabanın toplam içindeki payını e-postadakiyle karşılaştır. Kısa metinde bu pay belirgin biçimde büyük olmalı. Taban değeri iki dosyada farklı çıkıyorsa iki çağrıda da `BASELINE_TEXT` kullandığından emin ol.

**Bitirdiğinde:** Dosyan [`cozum/adim_2.py`](cozum/adim_2.py) ile aynı işi yapıyor olmalı.

<a id="adim-3"></a>

## Adım 3 — Fiyatlar, maliyet ve tablo

**Ne yapacaksın:** Fiyatları `pricing.yaml` dosyasından okuyacak, her çağrının ve aylık hacmin maliyetini hesaplayacak, sonuçları hizalı bir tabloda göstereceksin. Bu, projenin en büyük adımı: dosyan tek modelli bir betikten, model listesi üzerinde dönen bir araca dönüşüyor.

**Neden:** Ders 1.4 §6.2'de maliyet formülünü elle hesapladın. Burada aynı formülü koda dökerken iki tasarım kararı veriyorsun. Birincisi, fiyatlar koda yazılmaz; ayrı bir dosyada durur. Fiyatlar değiştiğinde (ve değişirler) kodu değil yalnızca dosyayı güncellersin. İkincisi, hesap ile görünüm ayrılır: maliyet fonksiyonu ham sayı döndürür, biçimlendirme fonksiyonları onu Türkçe yazıma çevirir. Böylece hesabı test etmek kolaylaşır ve görünümü değiştirmek hesabı bozmaz.

Önce `pricing.yaml` dosyasını aç ve yapısını incele: her model için bir anahtar (`key`), görünen ad (`name`), API kimliği (`id`), milyon token başına girdi ve çıktı fiyatı, context window ve max output değerleri var.

Dosyanın başındaki docstring'den sonraki kısmı (import satırları ve sabitler) şu hâliyle değiştir. `MODEL_ID` ve `MODEL_NAME` sabitleri artık yok; model bilgisi `pricing.yaml` dosyasından gelecek.

```python
{{BAS:cozum/adim_3.py}}
```

`read_text` fonksiyonunun üstüne fiyat dosyasını okuyan ve model listesini süzen iki fonksiyon ekle:

```python
{{FN:cozum/adim_3.py:load_pricing}}


{{FN:cozum/adim_3.py:select_models}}
```

`count_input_tokens` fonksiyonunun altına maliyet hesabını ekle:

```python
{{FN:cozum/adim_3.py:estimate_cost}}
```

Hemen altına sayıları Türkçe yazıma çeviren ve tablo basan yardımcıları ekle:

```python
{{FN:cozum/adim_3.py:_tr_number}}


{{FN:cozum/adim_3.py:fmt_int}}


{{FN:cozum/adim_3.py:fmt_usd}}


{{FN:cozum/adim_3.py:print_table}}
```

`cmd_count` fonksiyonunu şu hâliyle değiştir. Fonksiyon artık üçüncü bir parametre (`pricing`) alıyor:

```python
{{FN:cozum/adim_3.py:cmd_count}}
```

`build_parser` ve `main` fonksiyonlarını da şu hâlleriyle değiştir:

```python
{{FN:cozum/adim_3.py:build_parser}}


{{FN:cozum/adim_3.py:main}}
```

`fmt_usd` fonksiyonuna özellikle bak. Maliyetler çok küçük olabildiği için sabit iki ondalık yetmez: $0,00025 gibi bir tutar iki ondalıkla $0,00 görünürdü. `math.log10` sayının büyüklük basamağını bulur ve ondalık sayısı buna göre ayarlanır.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5 --output-tokens 500 --monthly-calls 100000
```

**Beklenen çıktı:** Üstte dosya bilgisi ve `Çıktı tahmini: 500 token` satırı, ardından tek satırlık bir tablo gelir. Tabloda `Model`, `Girdi token`, `Maliyet/çağrı` ve `Aylık (100.000 çağrı)` sütunları bulunur. En altta `Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)` satırı yer alır.

{{OLCUM:rehber-3}}

**Kontrol noktası:** Maliyeti elle doğrula. Tablodaki girdi token sayısını 1 ile, 500'ü 5 ile çarp, ikisini topla ve 1.000.000'a böl; sonuç tablodaki çağrı başına maliyetle aynı olmalı. Aylık değer de bunun 100.000 katı olmalı. Haiku 4.5'in fiyatı milyon token başına girdi için $1, çıktı için $5'tır.

**Yaygın hatalar:**

- `FileNotFoundError` ya da `pricing.yaml` bulunamadı hatası, dosyanı `calisma/` dışında bir yere koyduğunu gösterir. `DEFAULT_PRICING_PATH`, dosyanın iki üst klasöründe `pricing.yaml` arar; dosyanın `calisma/tokenhesap.py` yolunda olmalı.
- Maliyet beklenenden bin kat büyükse ya da küçükse 1.000.000'a bölmeyi unutmuş ya da iki kez bölmüş olabilirsin.
- `--monthly-calls` seçeneğinin değeri kodda `args.monthly_calls` adıyla okunur; `argparse` seçenek adlarındaki tireleri alt çizgiye çevirir.

**Bitirdiğinde:** Dosyan [`cozum/adim_3.py`](cozum/adim_3.py) ile aynı işi yapıyor olmalı.

<a id="adim-4"></a>

## Adım 4 — Dört model

**Ne yapacaksın:** Aracı dört modelin tamamında çalıştıracak, bir modele erişim olmadığında programın çökmemesini sağlayacak ve modeller aynı metin için farklı sayı verdiğinde bunu not olarak yazdıracaksın.

**Neden:** Ders 1.7'de model seçiminin yalnızca kaliteyle değil, maliyet ve kapasiteyle de ilgili olduğunu gördün. Dört modeli aynı tabloda görmek, bu farkı rakama döker. Bu adımın ikinci dersi daha az belirgindir: tokenizer modele özgüdür. Aynı metin farklı modellerde farklı token sayısı verebilir; bu yüzden token'ı her model için ayrı saymak gerekir. Ayrıca gerçek bir sistemde bazı çağrılar başarısız olur. Hesabının bir modele erişimi olmayabilir ya da ağ bağlantısı kopabilir. Bir aracın tek bir hatada tamamen durması yerine hatayı raporlayıp devam etmesi (Ders 1.4 §5) üretim kodunun temel özelliğidir.

`count_input_tokens` fonksiyonunun altına hatayı yakalayan sarmalayıcı fonksiyonu ekle:

```python
{{FN:cozum/adim_4.py:try_count}}
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
{{FN:cozum/adim_4.py:cmd_count}}
```

`main` fonksiyonunu da geçersiz API anahtarını yakalayacak şekilde değiştir:

```python
{{FN:cozum/adim_4.py:main}}
```

`try_count` içindeki sıralamaya dikkat et. `AuthenticationError` yakalanıp yeniden fırlatılıyor (`raise`), çünkü geçersiz bir anahtar tek bir modeli değil hepsini etkiler; her satıra "erişilemedi" yazmak yerine programı tek bir anlaşılır mesajla durdurmak daha doğrudur. Diğer API hataları ise yalnızca o modelin satırını etkiler.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --output-tokens 500 --monthly-calls 100000
python calisma/tokenhesap.py count ornekler/3_teknik_tr.txt --output-tokens 500
```

**Beklenen çıktı:** Tabloda dört satır görmelisin: Haiku 4.5, Sonnet 5.5, Opus 5.5 ve Fable 5.1. Modellerin girdi token sayıları birbirinden farklıysa tablonun altında `Not: Aynı metin modele göre farklı token sayısı verdi` ile başlayan bir satır çıkar. Hesabının bir modele erişimi yoksa o satırda `erişilemedi` yazar ve diğer satırlar normal görünür.

{{OLCUM:rehber-4a,rehber-4b}}

**Kontrol noktası:** Aylık maliyet sütununda en ucuz ve en pahalı modeli karşılaştır. Aradaki fark kaç kat? Bu farkın ne kadarı fiyattan, ne kadarı token sayısındaki farktan geliyor? Bu soruyu cevaplayabiliyorsan adımın asıl amacına ulaştın.

**Bitirdiğinde:** Dosyan [`cozum/adim_4.py`](cozum/adim_4.py) ile aynı işi yapıyor olmalı.

<a id="adim-5"></a>

## Adım 5 — Context doluluğu

**Ne yapacaksın:** Girdi ile beklenen çıktının modelin context window'unun ne kadarını kapladığını hesaplayacak, bunu bir metin çubuğu ve uyarı etiketiyle tabloya ekleyeceksin. Sonra uzun bir log dosyasıyla sınırları zorlayacaksın.

**Neden:** Ders 1.3 §3'te context window'un sınırlı bir çalışma belleği olduğunu ve taşmanın sessiz kesilmeye ya da hataya yol açtığını gördün. Burada iki pratik nokta öğreniyorsun. Birincisi, pencere yalnızca girdiyle dolmaz; model cevabını da aynı pencerenin içinde üretir. Girdi tek başına sığsa bile cevaba yer kalmayabilir. İkincisi, 200K ile 1M token'lık pencereler arasındaki fark soyut bir sayı değildir: aynı dosya bir modelde pencereyi aşarken diğerinde rahatça sığar.

`estimate_cost` fonksiyonunun altına üç hesaplama fonksiyonu ekle:

```python
{{FN:cozum/adim_5.py:context_ratio}}


{{FN:cozum/adim_5.py:usage_label}}


{{FN:cozum/adim_5.py:render_bar}}
```

`fmt_usd` fonksiyonunun altına yüzde biçimlendirmesini ekle:

```python
{{FN:cozum/adim_5.py:fmt_pct}}
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
{{FN:cozum/adim_5.py:cmd_count}}
```

`usage_label` fonksiyonundaki `if` sıralaması önemlidir. Koşullar yukarıdan aşağıya denenir ve ilk doğru olan fonksiyondan çıkar. En büyük eşiği önce kontrol etmezsen, %120'lik bir oran `DİKKAT` olarak etiketlenir.

**Çalıştır:** Önce uzun log dosyasını üret, sonra ölç:

```bash
python ornekler/uzun_log_uret.py
python calisma/tokenhesap.py count ornekler/uzun_log.txt --output-tokens 4000
```

**Beklenen çıktı:** Tabloya `Context doluluğu` sütunu eklenir. Haiku 4.5 satırında çubuk tamamen dolar ve etiket `TAŞMA` olur: dosya, bu modelin 200K token'lık penceresinin neredeyse iki katı. 1M token'lık pencereye sahip diğer üç modelde çubuk yarıya ulaşmaz ve etiket `OK` olur. Aynı dosyanın Haiku'da diğer modellerden daha az token tuttuğuna da dikkat et; tokenizer farkı burada da görünüyor.

{{OLCUM:rehber-5}}

**Kontrol noktası:** Haiku satırındaki yüzdeyi elle doğrula: girdi token sayısına 4.000'i ekle ve 200.000'e böl. Ardından dosyayı yarı uzunlukta yeniden üret (`python ornekler/uzun_log_uret.py --satir 3000`), ölçümü tekrarla ve Haiku'nun etiketinin nereye indiğine bak. Son olarak aynı dosyayla `--output-tokens 30000` ver: girdi hiç değişmediği hâlde yalnızca cevaba ayrılan yer büyüdüğünde etiketin ne olduğunu gözle. Bitirdiğinde varsayılan dosyaya dönmek için üreticiyi parametresiz çalıştır.

**Bitirdiğinde:** Dosyan [`cozum/adim_5.py`](cozum/adim_5.py) ile aynı işi yapıyor olmalı.

> [!CAUTION]
> Büyük context window, modelin o pencereyi eşit dikkatle kullanacağı anlamına gelmez. Ders 1.3'teki "lost in the middle" etkisini hatırla: uzun bir girdinin ortasındaki bilgi, başındaki ve sonundakinden daha zor kullanılır. Bu aracın gösterdiği doluluk bir kapasite ölçüsüdür, kavrayış garantisi değildir.

<a id="adim-6"></a>

## Adım 6 — Türkçe ile İngilizce

**Ne yapacaksın:** İkinci bir komut (`compare`) ekleyeceksin. Bu komut aynı içeriğin Türkçe ve İngilizce hâlini alır, her model için iki metnin token sayısını karşılaştırır ve dil farkının maliyete etkisini hesaplar.

**Neden:** Ders 1.3 §1.3'te Türkçenin eklemeli yapısı nedeniyle aynı anlamı taşımak için genellikle daha fazla token kullandığını okudun. Derste bu farkın kaba bir sezgi olduğu ve gerçek oranın kendi verinle ölçülmesi gerektiği vurgulanıyordu. Bu adımda tam olarak bunu yapıyorsun. Karşılaştırmanın anlamlı olması için iki metnin aynı şeyi söylemesi gerekir; `ornekler/` klasöründeki çiftler bu yüzden birbirinin çevirisidir.

`cmd_count` fonksiyonundan sonra, `build_parser` fonksiyonundan önce yeni komutu ekle:

```python
{{FN:cozum/adim_6.py:cmd_compare}}
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştir. `main` artık hangi komutun çağrıldığına bakıp işi doğru fonksiyona yolluyor:

```python
{{FN:cozum/adim_6.py:build_parser}}


{{FN:cozum/adim_6.py:main}}
```

**Çalıştır:**

```bash
python calisma/tokenhesap.py compare ornekler/1_kisa_tr.txt ornekler/1_kisa_en.txt
python calisma/tokenhesap.py compare ornekler/2_eposta_tr.txt ornekler/2_eposta_en.txt
python calisma/tokenhesap.py compare ornekler/3_teknik_tr.txt ornekler/3_teknik_en.txt
```

**Beklenen çıktı:** Her komut iki dosyanın karakter ve kelime sayısını, ardından dört satırlık bir tablo basar. Tabloda `TR token`, `EN token`, `TR/EN`, `TR fazlası` ve `1.000 çağrıda ek girdi maliyeti` sütunları bulunur. En altta tüm modellerin ortalama oranını veren bir cümle yer alır.

{{OLCUM:rehber-6a,rehber-6b,rehber-6c}}

**Kontrol noktası:** Üç metin türündeki oranları karşılaştır. Kısa cümle, e-posta ve teknik olay raporu aynı oranı mı veriyor? Türkçe metinlerin kelime sayısının İngilizce karşılıklarından az, token sayısının ise fazla olması ne anlama geliyor? Sonuçlarını Ders 1.3'teki kaba tabloyla karşılaştır.

**Bitirdiğinde:** Dosyan [`cozum/adim_6.py`](cozum/adim_6.py) ile aynı işi yapıyor olmalı.

<a id="adim-7"></a>

## Adım 7 — Tahmin ile gerçeği karşılaştır

**Ne yapacaksın:** `--verify` seçeneği ekleyeceksin. Bu seçenek verildiğinde araç, aynı mesajı önce `count_tokens` ile sayacak, sonra gerçekten modele gönderecek ve iki ölçümü yan yana gösterecek.

**Neden:** Ders 1.4 §6.1'de `count_tokens` ile `usage` arasındaki farkı okudun: biri çağrı öncesi bir tahmin, diğeri faturada esas alınan kesin ölçüm. Bu adım iki ölçümü aynı ekranda gösteriyor ve sana hangisini ne zaman kullanacağını kalıcı olarak öğretiyor. Ayrıca çıktı token'ı hakkında önemli bir gerçekle yüzleşiyorsun: çağrıdan önce cevabın kaç token olacağını bilemezsin. Bu yüzden tahmin satırında çıktı için `max_tokens` üst sınırı, yani en kötü durum kullanılıyor.

Sabitlerin arasına, `BASELINE_TEXT` satırının altına doğrulama talimatını ekle:

```python
{{SABIT:cozum/tokenhesap.py:VERIFY_INSTRUCTION}}
```

`cmd_count` fonksiyonundan sonra doğrulama fonksiyonunu ekle:

```python
{{FN:cozum/tokenhesap.py:run_verify}}
```

`cmd_count` fonksiyonunun sonundaki `return 0` satırının hemen üstüne doğrulama çağrısını ekle:

```python
    if args.verify:
        print()
        verify_model = select_models(pricing, args.verify_model)[0]
        run_verify(client, verify_model, text, args.verify_max_tokens)
```

`build_parser` içinde `p_count.add_argument("--baseline", ...)` satırının altına üç seçenek ekle:

```python
    p_count.add_argument("--verify", action="store_true", help="Tek gerçek çağrı yapıp tahmini usage ile karşılaştır (ücretli)")
    p_count.add_argument("--verify-model", default="haiku-4-5", help="Doğrulama modeli (varsayılan: haiku-4-5)")
    p_count.add_argument("--verify-max-tokens", type=int, default=300, help="Doğrulama çağrısının max_tokens değeri")
```

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5 --verify
```

**Beklenen çıktı:** Normal tablonun altında `Doğrulama (Claude Haiku 4.5, gerçek çağrı, max_tokens=300)` başlıklı iki satırlık bir tablo gelir: `Tahmin (count_tokens + max_tokens)` ve `Gerçek (usage)`. Altında girdi farkını işaretiyle gösteren bir satır ve modelin e-postayı tek cümleyle özetleyen yanıtı yer alır.

{{OLCUM:rehber-7}}

**Kontrol noktası:** Tahmin ile gerçek arasındaki girdi farkı birkaç token'ı geçmemeli. Gerçek çıktı token sayısı ise tahmindeki 300'ün altında kalmalı; bu fark, çağrı öncesi maliyet tahmininin neden bir üst sınır olduğunu gösterir.

> [!WARNING]
> `--verify` gerçek bir çağrı yapar ve ücretlendirilir. Bu seçeneği büyük dosyalarla ya da pahalı modellerle (`--verify-model fable-5-1` gibi) kullanırken dikkatli ol. Uzun log dosyasıyla Fable 5.1 üzerinde yapılacak tek bir doğrulama, projenin geri kalanının toplam maliyetinden fazlasına mal olabilir.

**Bitirdiğinde:** Dosyan [`cozum/tokenhesap.py`](cozum/tokenhesap.py) ile aynı işi yapıyor olmalı. Bunu doğrulamanın en hızlı yolu iki dosyayı karşılaştırmaktır:

```bash
diff calisma/tokenhesap.py cozum/tokenhesap.py
```

Fark yalnızca yorum satırlarında ya da docstring'deyse projeyi tamamladın.

<a id="takildiginda"></a>

## Takıldığında

- **Ara sürümle karşılaştır.** Her adımın sonunda dosyanın ulaşması gereken hâl `cozum/adim_N.py` dosyasında. Farkı görmek için: `diff calisma/tokenhesap.py cozum/adim_3.py`
- **Ara sürümden devam et.** Dosyan bozulduysa o adımın ara sürümünü kopyalayıp oradan ilerleyebilirsin: `cp cozum/adim_3.py calisma/tokenhesap.py`
- **Satırın nedenini oku.** [`kod-rehberi-yan-yana.html`](kod-rehberi-yan-yana.html) tam çözümün her parçasının karşısında açıklamasını gösterir; [`kod-rehberi.html`](kod-rehberi.html) fonksiyonların hangi sırayla çağrıldığını adım adım izletir.
- **Parametreleri hatırla.** [`demo.html`](demo.html) sayfasının altındaki "Komut parametreleri" bölümü tüm seçenekleri örnekleriyle açıklar; aynı listeyi `python calisma/tokenhesap.py count --help` ile terminalde de görebilirsin.

Projeyi bitirdiğinde platformdaki proje sayfasının "Kontrol noktaları" listesini gözden geçir; listedeki her madde projenin bir isterine karşılık gelir.
