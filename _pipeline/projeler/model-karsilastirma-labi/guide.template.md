# Model karşılaştırma lab'ı: adım adım rehber

Bu rehber, projeyi sekiz adımda sıfırdan yazman için hazırlandı. Kodun tamamını `calisma/modellab.py` dosyasında, her adımda bir öncekinin üzerine ekleyerek büyüteceksin. Projenin amacı, isterleri ve pratik edeceğin kavramlar platformdaki proje sayfasında; bu rehber yalnızca "nasıl" sorusuna odaklanıyor.

Her adım aynı yapıyı izler: **ne yapacaksın**, **neden** (ilgili dersle bağlantısı), eklenecek ya da değiştirilecek **kod**, **çalıştırma** komutu, **beklenen çıktı**, **kontrol noktası** ve varsa **yaygın hatalar**. Bir adımın kontrol noktasını geçmeden bir sonrakine geçme.

## İçindekiler

- [Başlamadan önce](#baslamadan-once)
- [Adım 1 — İlk ölçüm](#adim-1)
- [Adım 2 — Dört model ve maliyet](#adim-2)
- [Adım 3 — Görev seti ve kayıt](#adim-3)
- [Adım 4 — Otomatik kalite kontrolleri](#adim-4)
- [Adım 5 — Rapor](#adim-5)
- [Adım 6 — Etiketsiz puanlama](#adim-6)
- [Adım 7 — Tekrar ve varyans](#adim-7)
- [Adım 8 — Model kartı](#adim-8)
- [Takıldığında](#takildiginda)

<a id="baslamadan-once"></a>

## Başlamadan önce

Kurulumu [README.md](README.md) dosyasındaki "Hızlı başlangıç" bölümüne göre yaptığından emin ol: sanal ortam etkin, bağımlılıklar kurulu ve `ANTHROPIC_API_KEY` tanımlı olmalı. Şu komut `Kurulum tamam` yazdırmalı:

```bash
python -c "import anthropic, yaml; print('Kurulum tamam')"
```

Tüm komutları proje klasöründe (`model-karsilastirma-labi`) çalıştır. Bitmiş aracın neye benzediğini görmek için başlamadan önce platformdaki proje sayfasının başındaki demoyu ya da bu klasördeki [`demo.html`](demo.html) dosyasını açabilirsin.

> [!WARNING]
> Bu projede `run` komutunun her çalıştırması gerçek API çağrısı yapar ve ücretlendirilir. Görevler kısa ve `max_tokens` varsayılanı 300 olduğu için rehberin tamamı, dört modelle birlikte, bir doların altında kalır. Yine de `--repeat` değerini ve görev sayısını artırırken maliyetin aynı oranda arttığını unutma. `report`, `show` ve `rate` komutları çağrı yapmaz.

<a id="adim-1"></a>

## Adım 1 — İlk ölçüm

**Ne yapacaksın:** Bir görev dosyasındaki prompt'u Claude Haiku 4.5'e streaming ile gönderen, ilk token süresini ve toplam süreyi ölçen en küçük çalışan aracı yazacaksın. Bu adımda fiyat, tablo ya da birden fazla model yok; tek bir çağrı ve iki kronometre.

**Neden:** Ders 1.4 §4.1'de streaming çağrıyı, §4.3'te ilk token süresinin (TTFT) kullanıcı deneyimi için neden kritik olduğunu okudun. Bu adımda o ölçümü kendi aracının çekirdeğine yerleştiriyorsun: streaming olmadan ilk token süresi ölçülemez, çünkü yanıt tek parça hâlinde en sonda gelir. Programı en baştan `argparse` ile alt komut (`run`) alacak şekilde kuruyoruz; Adım 5'te `report` komutunu eklerken yapıyı değiştirmek zorunda kalmayacaksın.

Önce `gorevler/1_tek_prompt.yaml` dosyasını aç ve yapısını incele: bir `ad`, bir `gorevler` listesi ve listedeki tek görevde `ad`, `tier`, `prompt` ile `kontroller` alanları var. Kontrolleri Adım 4'e kadar kullanmayacağız.

`calisma/modellab.py` adında bir dosya oluştur ve içine şunu yaz:

```python
{{DOSYA:cozum/adim_1.py}}
```

Kodda dikkat etmen gereken üç nokta var. `stream_call` projenin kalbidir: `time.perf_counter()` isteğin hemen öncesinde başlar, ilk metin parçası geldiğinde `first` işaretlenir, akış bitince `end` alınır; `get_final_message()` ise akış bittikten sonra `usage` ve `stop_reason` alanlarını verir. `kwargs` sözlüğü `system` talimatını yalnızca görevde varsa, `extra` sözlüğündeki ek ayarları da varsa isteğe ekler; bu adımda ikisi de boş. `main` fonksiyonundaki `client=None` parametresi testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/1_tek_prompt.yaml
```

**Beklenen çıktı:** İlk satırda görev setinin adı ve model, ardından `[mikroservis]` başlığı altında modelin üç maddelik yanıtı, en altta `İlk token:`, `Toplam:`, `Girdi:`, `Çıktı:` ve `Durma nedeni: end_turn` bilgilerini taşıyan tek bir satır görmelisin.

{{OLCUM:rehber-1}}

**Kontrol noktası:** Komutu üç kez çalıştır ve ilk token sürelerini karşılaştır. Aynı mı? Aynı değilse fark ne kadar? Bu sayı sabit bir özellik değil, bir ölçümdür; Adım 7'de bu varyansı sistematik olarak göreceksin. Ayrıca toplam sürenin ilk token süresinden belirgin biçimde büyük olduğuna dikkat et: aradaki fark modelin üretim süresidir.

**Yaygın hatalar:**

- `Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.` mesajı, anahtarı tanımladığın terminalden farklı bir terminalde çalıştığını gösterir. `export` komutunu bu terminalde tekrarla.
- `ModuleNotFoundError: No module named 'anthropic'` hatası, sanal ortamın etkin olmadığını gösterir. `source .venv/bin/activate` komutunu çalıştır.
- `anthropic.AuthenticationError` hatası, anahtarın yanlış kopyalandığını gösterir. Başta ve sonda boşluk kalıp kalmadığına bak.

<a id="adim-2"></a>

## Adım 2 — Dört model ve maliyet

**Ne yapacaksın:** Model bilgilerini `pricing.yaml` dosyasından okuyacak, aynı görevi dört modelde çalıştıracak, her çağrının maliyetini `usage` değerlerinden hesaplayacak ve sonuçları hizalı bir tabloda göstereceksin. Bir modele erişim olmadığında program çökmeyecek. Bu, projenin en büyük adımı.

**Neden:** Ders 1.7 §4'teki beş eksenli karar çerçevesinin iki ekseni (latency ve maliyet) burada tek tabloda yan yana geliyor. Maliyeti Ders 1.4 §6.2'deki formülle hesaplıyorsun; ama token maliyet hesaplayıcı projesinden farklı olarak sayılar tahmin değil, yanıtın `usage` alanından gelen kesin değerler. İki tasarım kararı da oradan tanıdık: fiyatlar koda yazılmaz, ayrı dosyada durur; hesap ile görünüm ayrılır. Üçüncü karar Ders 1.4 §5'ten: gerçek bir sistemde bazı çağrılar başarısız olur; araç tek hatada durmak yerine hatayı raporlayıp devam eder.

Önce `pricing.yaml` dosyasını aç ve yapısını incele: her model için bir anahtar (`key`), görünen ad (`name`), API kimliği (`id`), milyon token başına girdi ve çıktı fiyatı, context window ve max output değerleri var. Bir de `cagri_ayarlari` alanı var: modele özgü ek istek parametreleri. Bu projede her model için düşünmeyi (thinking) en aza indiren ayar seçilmiş. Bazı modeller düşünmeyi varsayılan olarak açar; düşünme token'ları metin akışında görünmez ama çıktı olarak faturalanır ve `max_tokens` bütçesini tüketir (Ders 1.4 §6.2). Düşünmeyi kısmadan dört modeli karşılaştırmak, modelleri değil düşünme varsayılanlarını karşılaştırmak olurdu. Modeller aynı parametreyi kabul etmediği için (biri `disabled`, biri `between_tools`, diğerleri `adaptive` + `effort`) bu ayar koda değil veri dosyasına yazılır; API değişirse yalnızca YAML güncellenir.

Dosyanın başındaki docstring'den sonraki kısmı (import satırları ve sabitler) şu hâliyle değiştir. `MODEL_ID` ve `MODEL_NAME` sabitleri artık yok; model bilgisi `pricing.yaml` dosyasından gelecek.

```python
{{BAS:cozum/adim_2.py}}
```

`load_tasks` fonksiyonunun üstüne fiyat dosyasını okuyan ve model listesini süzen iki fonksiyon ekle:

```python
{{FN:cozum/adim_2.py:load_pricing}}


{{FN:cozum/adim_2.py:select_models}}
```

`stream_call` fonksiyonunun altına hatayı yakalayan sarmalayıcıyı ve ardından iki hesap fonksiyonunu ekle:

```python
{{FN:cozum/adim_2.py:try_call}}


{{FN:cozum/adim_2.py:estimate_cost}}


{{FN:cozum/adim_2.py:tokens_per_second}}
```

`_tr_number` fonksiyonunun altına sayı biçimlendiricileri ekle:

```python
{{FN:cozum/adim_2.py:fmt_int}}


{{FN:cozum/adim_2.py:fmt_usd}}
```

`fmt_sec` fonksiyonunun altına hız biçimlendiricisini ve tablo basan yardımcıyı ekle:

```python
{{FN:cozum/adim_2.py:fmt_speed}}


{{FN:cozum/adim_2.py:print_table}}
```

`cmd_run` fonksiyonunu şu hâliyle değiştir. Fonksiyon artık üçüncü bir parametre (`pricing`) alıyor ve yanıt metnini yalnızca `--show-output` verildiğinde yazıyor:

```python
{{FN:cozum/adim_2.py:cmd_run}}
```

`build_parser` ve `main` fonksiyonlarını da şu hâlleriyle değiştir:

```python
{{FN:cozum/adim_2.py:build_parser}}


{{FN:cozum/adim_2.py:main}}
```

`try_call` içindeki sıralamaya dikkat et. `AuthenticationError` yakalanıp yeniden fırlatılıyor (`raise`), çünkü geçersiz bir anahtar tek bir modeli değil hepsini etkiler; her satıra "erişilemedi" yazmak yerine programı tek bir anlaşılır mesajla durdurmak daha doğrudur. `try_call` ayrıca modelin `cagri_ayarlari` sözlüğünü `stream_call`'a iletir; `kwargs.update(extra or {})` satırı bu ayarları isteğe ekler. Kod ayarların içeriğini bilmez; bir model yeni bir parametre isterse yalnızca `pricing.yaml` değişir. `tokens_per_second` ise üretim süresi 50 ms'nin altındaysa `None` döndürür: birkaç token'lık bir yanıtta hız ölçülemez ve ölçülemeyen değer uydurulmaz, tabloda "-" olarak kalır.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/1_tek_prompt.yaml --show-output
python calisma/modellab.py run gorevler/1_tek_prompt.yaml --models haiku-4-5,fable-5-1 --max-tokens 40 --show-output
```

**Beklenen çıktı:** İlk komutta dört modelin yanıtı ve ardından dört satırlık bir tablo gelir: `İlk token`, `Toplam`, `token/sn`, `Çıktı token` ve `Maliyet` sütunları. Maliyet modelden modele kat kat değişir; ilk token süresi de değişir ama fiyat sırasını izlemez, en pahalı model ilk token'ı en hızlı verebilir. İkinci komutta yalnızca iki satır vardır; `Çıktı token` sütunu 40'ta kalır ve yanıtlar yarım biter.

{{OLCUM:rehber-2a,rehber-2b}}

**Kontrol noktası:** Bir satırın maliyetini elle doğrula: girdi token sayısını modelin girdi fiyatıyla, çıktı token sayısını çıktı fiyatıyla çarp, topla ve 1.000.000'a böl. İkinci komutta yanıtın kesildiğini gördün ama tablo bunu henüz söylemiyor; Adım 4'te `stop_reason` değerinden "kesildi" işaretini ekleyeceksin. Yanlış bir anahtar dene (`--models gpt-5`): geçerli anahtarları listeleyen tek satırlık bir hata almalısın.

**Yaygın hatalar:**

- `FileNotFoundError` ya da `pricing.yaml` bulunamadı hatası, dosyanı `calisma/` dışında bir yere koyduğunu gösterir. `PROJECT_DIR`, dosyanın iki üst klasörünü proje klasörü sayar; dosyan `calisma/modellab.py` yolunda olmalı.
- Maliyet beklenenden bin kat büyükse ya da küçükse 1.000.000'a bölmeyi unutmuş ya da iki kez bölmüş olabilirsin.
- `--show-output` seçeneğinin değeri kodda `args.show_output` adıyla okunur; `argparse` seçenek adlarındaki tireleri alt çizgiye çevirir.

**Bitirdiğinde:** Dosyan [`cozum/adim_2.py`](cozum/adim_2.py) ile aynı işi yapıyor olmalı.

<a id="adim-3"></a>

## Adım 3 — Görev seti ve kayıt

**Ne yapacaksın:** Beş görevlik bir seti dört modelde çalıştıracak ve her çalıştırmanın tüm verilerini (süreler, token'lar, maliyet, yanıtın kendisi) bir JSONL dosyasına kaydedeceksin. Bundan sonraki adımlar bu dosyadan çalışacak; ücretli çağrı yalnızca `run` komutunda kalacak.

**Neden:** Ders 1.5 §8'in ilkesi: bir LLM'in tek bir çıktısı, bir dağılımın tek bir örneklemidir; tek örnekle karar verilmez. Ders 1.7 §7'deki eval-driven model seçim akışının ilk adımı da temsili görev örnekleri toplamaktır. Bu yüzden tek prompt'tan göreve setine geçiyorsun. İkinci karar daha pratik: ölçüm ile inceleme ayrılır. Ücretli veri bir kez toplanır ve dosyada kalır; rapor, etiketsiz görünüm ve puanlama bu dosyadan çalışır. Her soru için yeniden çağrı yapmak hem pahalı olurdu hem de gecikme ölçümlerini her seferinde değiştirirdi.

Önce `gorevler/2_gorev_seti.yaml` dosyasını aç. Beş görev, Ders 1.7 §3'teki üç kapasite katmanına yayılmış: sınıflandırma ve veri çıkarma (tier 1), özet ve kod (tier 2), küçük bir muhakeme sorusu (tier 3). Her görevin `kontroller` alanını şimdilik okuyup geç; Adım 4'te kullanacaksın.

Dosyanın başındaki import ve sabit bloğunu şu hâliyle değiştir (`json`, `datetime` ve `DEFAULT_RESULTS_DIR` eklendi):

```python
{{BAS:cozum/adim_3.py}}
```

`print_table` fonksiyonunun altına kayıt fonksiyonlarını ekle:

```python
{{FN:cozum/adim_3.py:default_results_path}}


{{FN:cozum/adim_3.py:save_results}}
```

`cmd_run` fonksiyonunu şu hâliyle değiştir. Her başarılı çağrı için bir kayıt sözlüğü oluşturuluyor ve döngü bitince dosyaya yazılıyor:

```python
{{FN:cozum/adim_3.py:cmd_run}}
```

`build_parser` içinde `p_run.add_argument("--max-tokens", ...)` satırının altına yeni seçeneği ekle:

```python
    p_run.add_argument("--out", help="Sonuç dosyası (varsayılan: sonuclar/<görev dosyası adı>.jsonl)")
```

JSONL, her satırı bağımsız bir JSON nesnesi olan metin dosyasıdır. Tek bir büyük JSON dizisine göre iki avantajı var: dosyanın sonuna satır eklemek kolaydır (Adım 6'da puan kayıtlarını böyle ekleyeceksin) ve dosya yarım kalsa bile önceki satırlar okunabilir. `ensure_ascii=False` Türkçe karakterlerin kaçış dizilerine çevrilmeden yazılmasını sağlar.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/2_gorev_seti.yaml
```

**Beklenen çıktı:** Beş görev başlığı, her birinin altında dört satırlık bir tablo ve en altta `Kaydedildi: sonuclar/2_gorev_seti.jsonl (20 kayıt)` satırı. Sınıflandırma ve muhakeme gibi birkaç token'lık yanıtlarda `token/sn` sütunu çoğunlukla "-" gösterir. Bir satırda birkaç kelimelik cevap için onlarca token görürsen şaşırma: `adaptive` ayarıyla düşünme tamamen kapanmaz, kalan düşünme token'ları metinde görünmez ama `usage` sayımına ve faturaya girer.

{{OLCUM:rehber-3}}

**Kontrol noktası:** `sonuclar/2_gorev_seti.jsonl` dosyasını bir editörde aç. Yirmi satır olmalı; bir satırı seç ve `gorev`, `model`, `ilk_token_sn`, `maliyet` ve `yanit` alanlarını tablodaki değerlerle karşılaştır. Ardından `--out sonuclar/deneme.jsonl` ile tekrar çalıştır ve iki dosyanın aynı görevde farklı süreler verdiğini gör.

**Yaygın hatalar:**

- `Hata: gorevler/... : 'gorevler' listesi boş ya da yok.` mesajı YAML girintisinin bozuk olduğunu gösterir; görev listesi `gorevler:` anahtarının altında iki boşluk içeride olmalı.
- `TypeError: Object of type ... is not JSON serializable` hatası, kayda JSON'a çevrilemeyen bir nesne koyduğunu gösterir; `datetime` değerini `isoformat()` ile metne çevirdiğinden emin ol.

**Bitirdiğinde:** Dosyan [`cozum/adim_3.py`](cozum/adim_3.py) ile aynı işi yapıyor olmalı.

<a id="adim-4"></a>

## Adım 4 — Otomatik kalite kontrolleri

**Ne yapacaksın:** Görev dosyasındaki `kontroller` kurallarını uygulayan bir puanlayıcı yazacaksın. Her çıktı 0–100 arası bir puan alacak, başarısız kontroller kaydedilecek ve `max_tokens` sınırına takılan yanıtlar tabloda işaretlenecek.

**Neden:** Ders 1.7 §7'deki akışın ikinci adımı başarı kriterini tanımlamaktır: doğruluk, format uyumu, uzunluk. Bu adımda kriterleri kasıtlı olarak basit tutuyorsun: belirli bir ifade geçiyor mu, çıktı geçerli JSON mu, kelime sınırı aşıldı mı. Bu kontroller kaliteyi tam ölçmez; ama "yanıt kurallara uydu mu?" sorusunu tutarlı, tekrarlanabilir ve ücretsiz biçimde cevaplar. Bir modelin başka bir modelle puanlanması (LLM-as-judge) Aşama 2'nin konusu. İkinci nokta Ders 1.4 §5.3'ten: `stop_reason` değeri `max_tokens` ise yanıt eksiktir ve bunu sessizce geçmek yarım veriyle çalışmak demektir.

Dosyanın başındaki import ve sabit bloğunu şu hâliyle değiştir (`CHECK_KINDS` eklendi):

```python
{{BAS:cozum/adim_4.py}}
```

`load_tasks` fonksiyonunu, görev dosyasını yüklerken doğrulayan şu hâliyle değiştir:

```python
{{FN:cozum/adim_4.py:load_tasks}}
```

`tokens_per_second` fonksiyonunun altına JSON çözücüyü ve kontrol fonksiyonunu ekle:

```python
{{FN:cozum/adim_4.py:_parse_json}}


{{FN:cozum/adim_4.py:check_output}}
```

`fmt_sec` fonksiyonunun altına yüzde biçimlendiricisini, `fmt_speed` fonksiyonunun altına puan biçimlendiricisini ekle:

```python
{{FN:cozum/adim_4.py:fmt_pct}}
```

```python
{{FN:cozum/adim_4.py:fmt_score}}
```

`cmd_run` fonksiyonunu şu hâliyle değiştir. Tabloya `Puan` sütunu, kayda `kesildi`, `puan` ve `basarisiz` alanları eklendi:

```python
{{FN:cozum/adim_4.py:cmd_run}}
```

`check_output` içinde kontrol yoksa puanın `None` olduğuna dikkat et: "0 puan" ile "puanlanmadı" farklı şeylerdir ve `fmt_score` ikincisini "-" olarak yazar. Metin küçük harfe çevrilerek karşılaştırılır; böylece "Fatura" ile "fatura" aynı sayılır.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/2_gorev_seti.yaml
```

**Beklenen çıktı:** Adım 3'teki tabloların sonuna `Puan` sütunu eklenir. Çoğu satırda `%100` görürsün; bir model bir görevde kuralı kaçırdıysa `%50` ya da `%67` gibi bir değer çıkar. Bir yanıt 300 token'a takılırsa `Çıktı token` sütununda `(kesildi)` yazar.

{{OLCUM:rehber-4}}

**Kontrol noktası:** Puanı %100'ün altında kalan bir satır varsa `sonuclar/2_gorev_seti.jsonl` dosyasında o kaydın `basarisiz` alanına bak: hangi kontrol, neden geçilmedi? Satır yoksa bir kontrolü kasten sıkılaştır (ör. `ozet` görevinde `max_kelime: 20`) ve yeniden çalıştır; puanların nasıl düştüğünü gözle. Bitirdiğinde dosyayı eski hâline getir.

**Yaygın hatalar:**

- `Hata: ... bilinmeyen kontrol: ...` mesajı görev dosyasında yazım hatalı bir kontrol türü olduğunu gösterir. Geçerli türler `CHECK_KINDS` sabitinde listelenir.
- JSON görevinde puan beklenmedik biçimde düşükse `basarisiz` alanına bak: model yanıtı kod bloğuna sarmış olabilir; `icermemeli: ["```"]` kontrolü tam olarak bunu yakalar.

**Bitirdiğinde:** Dosyan [`cozum/adim_4.py`](cozum/adim_4.py) ile aynı işi yapıyor olmalı.

<a id="adim-5"></a>

## Adım 5 — Rapor

**Ne yapacaksın:** `report` komutunu ekleyeceksin. Komut, kaydedilmiş sonuç dosyasını okuyup model başına tek satırlık bir özet tablo basacak: ortalama ilk token süresi, toplam süre, üretim hızı, çıktı uzunluğu, görev başına maliyet, isteğe bağlı aylık maliyet ve otomatik puan. Tablonun altında karar satırları yer alacak.

**Neden:** Ders 1.7 §4'ün ana mesajı: model seçimi tek eksenli bir karar değildir; kalite, latency ve maliyet birlikte tartılır. Adım 4'e kadar her görevi ayrı ayrı gördün; şimdi görevler üzerinden ortalama alıp modelleri karşılaştırıyorsun. `--monthly-calls` seçeneği Ders 1.7 §6.3'teki hesabı yapar: görev başına kuruşun altındaki farklar, aylık hacimde onlarca kat farka dönüşür. Karar satırlarındaki "puan farkı" ise Ders 1.7 §3'teki trap'in karşılığıdır: puanlar yakınsa kararı kalite değil hız ve maliyet verdirir.

`check_output` fonksiyonunun altına ortalama yardımcısını ekle:

```python
{{FN:cozum/adim_5.py:mean}}
```

`save_results` fonksiyonunun altına okuma fonksiyonunu ekle:

```python
{{FN:cozum/adim_5.py:load_results}}
```

`cmd_run` fonksiyonundan sonra üç fonksiyon ekle: özetleyici, karar satırları ve rapor komutu:

```python
{{FN:cozum/adim_5.py:summarize}}


{{FN:cozum/adim_5.py:decision_lines}}


{{FN:cozum/adim_5.py:cmd_report}}
```

`build_parser` içinde `return parser` satırının hemen üstüne yeni komutu ekle:

```python

    p_report = sub.add_parser("report", help="Kaydedilmiş sonuçlardan karşılaştırma raporu üret (çağrı yapmaz)")
    p_report.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_report.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet sütunu eklenir")
```

`main` fonksiyonunu şu hâliyle değiştir. `report` komutu API istemcisi gerektirmediği için anahtar kontrolünden önce yönlendiriliyor:

```python
{{FN:cozum/adim_5.py:main}}
```

`summarize` içindeki `dict.fromkeys(...)` kalıbı model anahtarlarını ilk görüldükleri sırayla ve tekrarsız listeler. Puanlanmamış görevler (`puan` değeri `None`) ortalamaya girmez; sıfır gibi sayılsalardı ortalamayı haksız yere düşürürlerdi.

**Çalıştır:**

```bash
python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl --monthly-calls 100000
```

**Beklenen çıktı:** Dört satırlık bir tablo: `İlk token`, `Toplam`, `token/sn`, `Çıktı token`, `Maliyet/görev`, `Aylık (100.000 çağrı)` ve `Oto puan` sütunları. Altında dört karar satırı: en hızlı ilk token, en ucuz model, en yüksek otomatik puan ve puan farkı.

{{OLCUM:rehber-5}}

**Kontrol noktası:** Aylık sütununda en ucuz ve en pahalı modeli karşılaştır: fark kaç kat? Şimdi `Oto puan` sütununa bak: bu kat farkının karşılığında puan farkı ne kadar? Bu iki soruyu birlikte cevaplayabiliyorsan adımın asıl amacına ulaştın. Çağrı yapılmadığını doğrulamak için komutu üç kez çalıştır; sayılar değişmemeli.

**Bitirdiğinde:** Dosyan [`cozum/adim_5.py`](cozum/adim_5.py) ile aynı işi yapıyor olmalı.

<a id="adim-6"></a>

## Adım 6 — Etiketsiz puanlama

**Ne yapacaksın:** İki komut ekleyeceksin. `show` bir görevin dört çıktısını model adları gizlenmiş ve sırası karıştırılmış olarak A, B, C, D etiketleriyle gösterir. `rate` senin 1–5 puanlarını kaydeder, etiketleri açar ve rapora "Etiketsiz" sütununu ekler.

**Neden:** Ders 1.7 §7'deki akışın altıncı adımı insan değerlendirmesidir; §3'teki trap ise "benchmark sıralaması senin görevin için en iyi model değildir" der. Otomatik kontroller kuralları ölçer, kaliteyi değil: iki özet de "sertifika" kelimesini içerebilir ama biri çok daha iyi yazılmış olabilir. Burada okuyucu sensin. Model adını görmeden puanlamanın nedeni basit: en pahalı modelin çıktısını, pahalı olduğunu bildiğin için daha yüksek puanlamaya eğilimlisin. Etiket gizlenince bu eğilim devreden çıkar.

Dosyanın başındaki import ve sabit bloğunu şu hâliyle değiştir (`random` ve `LABELS` eklendi):

```python
{{BAS:cozum/adim_6.py}}
```

`load_results` fonksiyonunun altına süzme ve karıştırma fonksiyonlarını ekle:

```python
{{FN:cozum/adim_6.py:runs_for_task}}


{{FN:cozum/adim_6.py:anonymize}}
```

`fmt_score` fonksiyonunun altına etiketsiz puan biçimlendiricisini ekle:

```python
{{FN:cozum/adim_6.py:fmt_rating}}
```

`summarize`, `decision_lines` ve `cmd_report` fonksiyonlarını etiketsiz puanı da hesaba katan şu hâlleriyle değiştir:

```python
{{FN:cozum/adim_6.py:summarize}}


{{FN:cozum/adim_6.py:decision_lines}}


{{FN:cozum/adim_6.py:cmd_report}}
```

`cmd_report` fonksiyonundan sonra üç fonksiyon ekle: etiketsiz görünüm, puan ayrıştırıcı ve puanlama komutu:

```python
{{FN:cozum/adim_6.py:cmd_show}}


{{FN:cozum/adim_6.py:parse_scores}}


{{FN:cozum/adim_6.py:cmd_rate}}
```

`build_parser` içinde `return parser` satırının hemen üstüne iki komutu ekle:

```python

    p_show = sub.add_parser("show", help="Bir görevin çıktılarını model adları gizli olarak göster")
    p_show.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_show.add_argument("task", help="Görev adı (görev dosyasındaki 'ad')")

    p_rate = sub.add_parser("rate", help="Etiketsiz puanları kaydet ve etiketleri aç")
    p_rate.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_rate.add_argument("task", help="Görev adı (görev dosyasındaki 'ad')")
    p_rate.add_argument("--scores", help="Puanlar, ör. A=4,B=3,C=5,D=3 (verilmezse terminalden sorulur)")
```

`main` fonksiyonunu şu hâliyle değiştir:

```python
{{FN:cozum/adim_6.py:main}}
```

`anonymize` içindeki `random.Random(seed)` tohumlu bir üreteçtir: aynı tohum her seferinde aynı karışıklığı verir. Tohum dosya adı ile görev adından türetildiği için `show` ve `rate` ayrı çalıştırılsa da aynı eşlemeyi kullanır; A harfi iki komutta da aynı modeli gösterir.

**Çalıştır:** Önce çıktıları etiketsiz gör, puanlarını ver, sonra raporu yenile. Aşağıdaki puanlar örnektir; kendi puanlarını yaz.

```bash
python calisma/modellab.py show sonuclar/2_gorev_seti.jsonl ozet
python calisma/modellab.py rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,C=5,D=3
python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl
```

**Beklenen çıktı:** `show` dört yanıtı `--- A ---` … `--- D ---` başlıklarıyla, model adı olmadan basar. `rate` etiketleri açar: her harfin hangi model olduğu, senin puanın, otomatik puan ve maliyet yan yana; en altta `+4 puan kaydı` notu. `report` tabloya `Etiketsiz` sütununu ve karar satırlarına "En yüksek etiketsiz puan" satırını ekler.

{{OLCUM:rehber-6a,rehber-6b,rehber-6c}}

**Kontrol noktası:** Etiketler açıldığında puanın fiyat sırasını izliyor mu? En yüksek puanı en pahalı modele mi verdin? Aynı işlemi `kod` ve `muhakeme` görevleri için tekrarla (`show` ve `rate` komutlarında görev adını değiştir). Üç görevin etiketsiz ortalaması raporda görünür. Puanlarken yanıtın bir çalışma arkadaşından gelmiş olsa onu kabul edip etmeyeceğini düşün.

**Yaygın hatalar:**

- `Hata: Eksik puan: D.` mesajı, dört çıktı varken üç puan verdiğini gösterir; her harfe puan vermeden kayıt yazılmaz.
- `Hata: 'ozet' adında görev yok. Görevler: ...` mesajı görev adını yanlış yazdığını gösterir; adlar görev dosyasındaki `ad` alanıyla birebir aynıdır.

**Bitirdiğinde:** Dosyan [`cozum/adim_6.py`](cozum/adim_6.py) ile aynı işi yapıyor olmalı.

<a id="adim-7"></a>

## Adım 7 — Tekrar ve varyans

**Ne yapacaksın:** `--repeat` seçeneğini ekleyeceksin. Her görev-model çifti N kez çalıştırılacak ve rapor, toplam sürenin en küçük ve en büyük değerini de gösterecek.

**Neden:** Ders 1.5 §5'te non-determinism'in üç katmanını okudun: sampling, altyapı varyansı ve sağlayıcı güncellemeleri. Gecikme de aynı şekilde dalgalanır; aynı çağrı bir sonraki saniyede daha yavaş ya da daha hızlı dönebilir. Adım 1'in kontrol noktasında bunu elle gördün. Ders 1.5 §6'nın önerisi, çıktıyı tek bir değerle değil kabul edilebilir bir varyans bandıyla düşünmektir. Bu adımda tek ölçümün ne kadar güvenilir olduğunu sayıyla görüyorsun: min–maks aralığı dar ise tek ölçüm yeter, genişse ortalama almadan karar vermemelisin.

`cmd_run` fonksiyonunu şu hâliyle değiştir. Model döngüsünün içine tekrar döngüsü eklendi ve kayda `tekrar` alanı girdi:

```python
{{FN:cozum/adim_7.py:cmd_run}}
```

`summarize` ve `cmd_report` fonksiyonlarını şu hâlleriyle değiştir:

```python
{{FN:cozum/adim_7.py:summarize}}


{{FN:cozum/adim_7.py:cmd_report}}
```

`build_parser` içinde `p_run.add_argument("--max-tokens", ...)` satırının altına yeni seçeneği ekle:

```python
    p_run.add_argument("--repeat", type=int, default=1, help="Her görev-model çiftini kaç kez çalıştırmalı (varsayılan: 1)")
```

`runs_for_task` fonksiyonunun yalnızca ilk tekrarı (`tekrar == 1`) aldığına dikkat et; böylece tekrarlı dosyalarda etiketsiz görünüm her modeli bir kez gösterir.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/1_tek_prompt.yaml --repeat 3 --out sonuclar/tekrar.jsonl
python calisma/modellab.py report sonuclar/tekrar.jsonl
```

**Beklenen çıktı:** `run` tablosunda her model üç satır olarak görünür (`#1`, `#2`, `#3`). `report` başlığında `görev başına 3 tekrar` yazar ve tablonun altında `Toplam süre aralığı (min–maks)` satırı gelir.

{{OLCUM:rehber-7a,rehber-7b}}

**Kontrol noktası:** Her model için aralığın genişliğini ortalamayla karşılaştır: en yavaş tekrar en hızlısının kaç katı? Bu oran modeller arasındaki farktan büyük mü, küçük mü? Büyükse tek ölçümle "X modeli daha hızlı" demek yanıltıcıdır. Üç tekrar küçük bir örneklemdir; ama Ders 1.5 §8'in dediği gibi küçük deneylerde bile sinyal verir.

> [!WARNING]
> `--repeat` çağrı sayısını ve maliyeti aynı oranda artırır. Beş görevlik seti dört modelle üç kez tekrarlamak 60 çağrı demektir. Deneme için tek görevlik dosyayı kullan.

**Bitirdiğinde:** Dosyan [`cozum/adim_7.py`](cozum/adim_7.py) ile aynı işi yapıyor olmalı.

<a id="adim-8"></a>

## Adım 8 — Model kartı

**Ne yapacaksın:** `report` komutuna `--model-card` seçeneğini ekleyeceksin. Özet tablo ve karar satırları bir Markdown dosyasına yazılacak; seçilen model, gerekçe, yedek model ve yeniden değerlendirme tarihi satırlarını sen dolduracaksın.

**Neden:** Ders 1.7 §7'deki akışın yedinci adımı kararı ve gerekçeyi model kartına kaydetmek, sekizinci adımı üç ayda bir ya da yeni model çıktığında tekrarlamaktır. Ders 1.7 §4'ün pratik notu da aynı yöne işaret eder: "Claude kullanıyoruz" yeterli değildir; model sürümü, fiyat varsayımı ve fallback modeli karar kaydına yazılır. Araç kararı vermez; kararın dayanacağı sayıları hazırlar ve gerekçeyi senden ister.

`cmd_report` fonksiyonundan sonra kart yazıcısını ekle:

```python
{{FN:cozum/modellab.py:write_model_card}}
```

`cmd_report` fonksiyonunu, seçenek verildiğinde kartı yazan şu hâliyle değiştir:

```python
{{FN:cozum/modellab.py:cmd_report}}
```

`build_parser` içinde `p_report.add_argument("--monthly-calls", ...)` satırının altına yeni seçeneği ekle:

```python
    p_report.add_argument("--model-card", help="Karar kaydını bu Markdown dosyasına yaz")
```

**Çalıştır:**

```bash
python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl --model-card sonuclar/model-karti.md
```

**Beklenen çıktı:** Adım 6'daki rapor ve en altta `Model kartı yazıldı: sonuclar/model-karti.md` satırı. Dosyayı açtığında tarih, sonuç dosyası, özet tablo, "Ölçümün söyledikleri" listesi ve doldurman için boş bırakılmış "Karar" bölümünü görmelisin.

{{OLCUM:rehber-8}}

**Kontrol noktası:** Kartın "Karar" bölümünü doldur. Seçtiğin model en hızlı, en ucuz ya da en yüksek puanlı olmak zorunda değil; önemli olan gerekçenin üç ekseni birlikte tartması. Yedek model sorusunu atlama: Ders 1.7 §5'teki erişilebilirlik riskleri (fiyat değişimi, deprecation, rate limit) her sağlayıcıda geçerlidir.

**Bitirdiğinde:** Dosyan [`cozum/modellab.py`](cozum/modellab.py) ile aynı işi yapıyor olmalı. Bunu doğrulamanın en hızlı yolu iki dosyayı karşılaştırmaktır:

```bash
diff calisma/modellab.py cozum/modellab.py
```

Fark yalnızca yorum satırlarında ya da docstring'deyse projeyi tamamladın.

<a id="takildiginda"></a>

## Takıldığında

- **Ara sürümle karşılaştır.** Her adımın sonunda dosyanın ulaşması gereken hâl `cozum/adim_N.py` dosyasında. Farkı görmek için: `diff calisma/modellab.py cozum/adim_4.py`
- **Ara sürümden devam et.** Dosyan bozulduysa o adımın ara sürümünü kopyalayıp oradan ilerleyebilirsin: `cp cozum/adim_4.py calisma/modellab.py`
- **Satırın nedenini oku.** [`kod-rehberi-yan-yana.html`](kod-rehberi-yan-yana.html) tam çözümün her parçasının karşısında açıklamasını gösterir; [`kod-rehberi.html`](kod-rehberi.html) `run`, `report` ve `rate` komutlarının kodda hangi fonksiyonlardan geçtiğini adım adım izletir.
- **Parametreleri hatırla.** [`demo.html`](demo.html) sayfasının "Parametreler" sekmesi tüm komutları ve seçenekleri örnekleriyle açıklar; aynı listeyi `python calisma/modellab.py run --help` ile terminalde de görebilirsin.
- **Çağrı yapmadan dene.** `sonuclar/2_gorev_seti.jsonl` dosyası repoda gerçek bir ölçümle gelir; `report`, `show` ve `rate` komutlarını API anahtarı olmadan bu dosyayla deneyebilirsin. Kendi `run` komutun dosyanın üzerine yazar.

Projeyi bitirdiğinde platformdaki proje sayfasının "Kontrol noktaları" listesini gözden geçir; listedeki her madde projenin bir isterine karşılık gelir.
