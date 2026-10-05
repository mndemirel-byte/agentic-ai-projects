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
"""Token maliyet hesaplayıcı — Adım 1: ilk sayım.

Bir metin dosyasının Claude Haiku 4.5'te kaç girdi token'ı tuttuğunu Token Counting API ile ölçer.

Kullanım:
    python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt
"""

import argparse
import os
import sys
from pathlib import Path

import anthropic

MODEL_ID = "claude-haiku-4-5-20251001"
MODEL_NAME = "Claude Haiku 4.5"


def read_text(path: str) -> str:
    """Dosyayı UTF-8 olarak okur; '-' verilirse standart girdiden okur."""
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def build_messages(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def count_input_tokens(client, model_id: str, messages: list[dict]) -> int:
    """Token Counting API ile girdi token sayısını döndürür. Model çalışmaz, ücret yazılmaz."""
    response = client.messages.count_tokens(model=model_id, messages=messages)
    return response.input_tokens


def cmd_count(args, client) -> int:
    text = read_text(args.file)
    tokens = count_input_tokens(client, MODEL_ID, build_messages(text))

    print(f"Dosya: {args.file}  |  {len(text)} karakter, {len(text.split())} kelime")
    print(f"{MODEL_NAME} girdi token: {tokens}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenhesap", description="Çağrı öncesi token, maliyet ve context hesaplayıcı.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_count = sub.add_parser("count", help="Bir metnin token sayısını hesapla")
    p_count.add_argument("file", help="Metin dosyası ('-' ile standart girdi)")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
            return 2
        client = anthropic.Anthropic()

    try:
        return cmd_count(args, client)
    except FileNotFoundError as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

Kodda dikkat etmen gereken üç nokta var. `build_messages`, metni API'nin beklediği rol-içerik yapısına sokar; token sayımı bu yapı üzerinden yapıldığı için sonuç metnin kendisinden biraz fazla çıkacak. `count_input_tokens` projenin kalbidir: API'ye mesajı gönderir ama model çalışmaz, yalnızca token sayısı döner. `main` fonksiyonundaki `client=None` parametresi ise testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt
```

**Beklenen çıktı:** İlk satırda dosya adı ve `86 karakter, 10 kelime` bilgisi, ikinci satırda `Claude Haiku 4.5 girdi token:` ifadesi ve ardından iki basamaklı bir sayı görmelisin.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt
Dosya: ornekler/1_kisa_tr.txt  |  86 karakter, 10 kelime
Claude Haiku 4.5 girdi token: 41
```

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
# Taban ölçümü için kullanılan en kısa anlamlı mesaj. API boş metin kabul etmez.
BASELINE_TEXT = "."
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
def cmd_count(args, client) -> int:
    text = read_text(args.file)
    tokens = count_input_tokens(client, MODEL_ID, build_messages(text))

    print(f"Dosya: {args.file}  |  {len(text)} karakter, {len(text.split())} kelime")
    print(f"{MODEL_NAME} girdi token: {tokens}")

    if args.baseline:
        base = count_input_tokens(client, MODEL_ID, build_messages(BASELINE_TEXT))
        print(f"Taban (mesaj iskeleti): {base}")
        print(f"Net (metnin kendi payı, yaklaşık): {tokens - base}")
    return 0
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/1_kisa_tr.txt --baseline
Dosya: ornekler/1_kisa_tr.txt  |  86 karakter, 10 kelime
Claude Haiku 4.5 girdi token: 41
Taban (mesaj iskeleti): 8
Net (metnin kendi payı, yaklaşık): 33
```

```text
$ python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --baseline
Dosya: ornekler/2_eposta_tr.txt  |  720 karakter, 93 kelime
Claude Haiku 4.5 girdi token: 306
Taban (mesaj iskeleti): 8
Net (metnin kendi payı, yaklaşık): 298
```

**Kontrol noktası:** Kısa cümlede tabanın toplam içindeki payını e-postadakiyle karşılaştır. Kısa metinde bu pay belirgin biçimde büyük olmalı. Taban değeri iki dosyada farklı çıkıyorsa iki çağrıda da `BASELINE_TEXT` kullandığından emin ol.

**Bitirdiğinde:** Dosyan [`cozum/adim_2.py`](cozum/adim_2.py) ile aynı işi yapıyor olmalı.

<a id="adim-3"></a>

## Adım 3 — Fiyatlar, maliyet ve tablo

**Ne yapacaksın:** Fiyatları `pricing.yaml` dosyasından okuyacak, her çağrının ve aylık hacmin maliyetini hesaplayacak, sonuçları hizalı bir tabloda göstereceksin. Bu, projenin en büyük adımı: dosyan tek modelli bir betikten, model listesi üzerinde dönen bir araca dönüşüyor.

**Neden:** Ders 1.4 §6.2'de maliyet formülünü elle hesapladın. Burada aynı formülü koda dökerken iki tasarım kararı veriyorsun. Birincisi, fiyatlar koda yazılmaz; ayrı bir dosyada durur. Fiyatlar değiştiğinde (ve değişirler) kodu değil yalnızca dosyayı güncellersin. İkincisi, hesap ile görünüm ayrılır: maliyet fonksiyonu ham sayı döndürür, biçimlendirme fonksiyonları onu Türkçe yazıma çevirir. Böylece hesabı test etmek kolaylaşır ve görünümü değiştirmek hesabı bozmaz.

Önce `pricing.yaml` dosyasını aç ve yapısını incele: her model için bir anahtar (`key`), görünen ad (`name`), API kimliği (`id`), milyon token başına girdi ve çıktı fiyatı, context window ve max output değerleri var.

Dosyanın başındaki docstring'den sonraki kısmı (import satırları ve sabitler) şu hâliyle değiştir. `MODEL_ID` ve `MODEL_NAME` sabitleri artık yok; model bilgisi `pricing.yaml` dosyasından gelecek.

```python
import argparse
import math
import os
import sys
from pathlib import Path

import anthropic
import yaml

DEFAULT_PRICING_PATH = Path(__file__).resolve().parent.parent / "pricing.yaml"

# Taban ölçümü için kullanılan en kısa anlamlı mesaj. API boş metin kabul etmez.
BASELINE_TEXT = "."

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")
```

`read_text` fonksiyonunun üstüne fiyat dosyasını okuyan ve model listesini süzen iki fonksiyon ekle:

```python
def load_pricing(path: Path) -> dict:
    """pricing.yaml dosyasını okur ve zorunlu alanları doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for model in data["models"]:
        missing = [field for field in REQUIRED_MODEL_FIELDS if field not in model]
        if missing:
            raise ValueError(f"pricing.yaml: '{model.get('key', '?')}' modelinde eksik alan: {', '.join(missing)}")
    return data


def select_models(pricing: dict, keys_csv: str | None) -> list[dict]:
    """--models parametresine göre model listesini döndürür (boşsa hepsi)."""
    models = pricing["models"]
    if not keys_csv:
        return models
    by_key = {m["key"]: m for m in models}
    selected = []
    for key in (k.strip() for k in keys_csv.split(",") if k.strip()):
        if key not in by_key:
            valid = ", ".join(by_key)
            raise ValueError(f"Bilinmeyen model anahtarı: '{key}'. Geçerli anahtarlar: {valid}")
        selected.append(by_key[key])
    return selected
```

`count_input_tokens` fonksiyonunun altına maliyet hesabını ekle:

```python
def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000
```

Hemen altına sayıları Türkçe yazıma çeviren ve tablo basan yardımcıları ekle:

```python
def _tr_number(formatted: str) -> str:
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_int(n: int) -> str:
    return _tr_number(f"{n:,}")


def fmt_usd(x: float) -> str:
    if x == 0:
        return "$0"
    if x < 0:
        return "-" + fmt_usd(-x)
    # 1 doların altındaki tutarlarda ilk anlamlı basamaktan sonra bir basamak daha göster:
    # 0,35 → $0,35  |  0,0035 → $0,0035  |  0,00012 → $0,00012
    decimals = 2 if x >= 1 else min(8, -math.floor(math.log10(x)) + 1)
    return "$" + _tr_number(f"{x:,.{decimals}f}")


def print_table(headers: list[str], rows: list[list[str]], right_align: set[int]) -> None:
    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]

    def line(cells):
        parts = []
        for i, cell in enumerate(cells):
            parts.append(str(cell).rjust(widths[i]) if i in right_align else str(cell).ljust(widths[i]))
        return "  ".join(parts).rstrip()

    print(line(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(line(row))
```

`cmd_count` fonksiyonunu şu hâliyle değiştir. Fonksiyon artık üçüncü bir parametre (`pricing`) alıyor:

```python
def cmd_count(args, client, pricing: dict) -> int:
    text = read_text(args.file)
    models = select_models(pricing, args.models)
    messages = build_messages(text)

    print(f"Dosya: {args.file}  |  {fmt_int(len(text))} karakter, {fmt_int(len(text.split()))} kelime")
    print(f"Çıktı tahmini: {fmt_int(args.output_tokens)} token (cevap + varsa thinking)")
    print()

    headers = ["Model", "Girdi token"]
    if args.baseline:
        headers += ["Taban", "Net"]
    headers += ["Maliyet/çağrı"]
    if args.monthly_calls:
        headers += [f"Aylık ({fmt_int(args.monthly_calls)} çağrı)"]

    rows = []
    for model in models:
        tokens = count_input_tokens(client, model["id"], messages)
        row = [model["name"], fmt_int(tokens)]
        if args.baseline:
            base = count_input_tokens(client, model["id"], build_messages(BASELINE_TEXT))
            row += [fmt_int(base), fmt_int(tokens - base)]

        cost = estimate_cost(model, tokens, args.output_tokens)
        row.append(fmt_usd(cost))
        if args.monthly_calls:
            row.append(fmt_usd(cost * args.monthly_calls))

        rows.append(row)

    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`build_parser` ve `main` fonksiyonlarını da şu hâlleriyle değiştir:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenhesap", description="Çağrı öncesi token, maliyet ve context hesaplayıcı.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat dosyası (varsayılan: pricing.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_count = sub.add_parser("count", help="Bir metnin token, maliyet ve context doluluğunu hesapla")
    p_count.add_argument("file", help="Metin dosyası ('-' ile standart girdi)")
    p_count.add_argument("--models", help=MODELS_HELP)
    p_count.add_argument("--output-tokens", type=int, default=1000, help="Beklenen çıktı token'ı (varsayılan: 1000)")
    p_count.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet gösterilir")
    p_count.add_argument("--baseline", action="store_true", help="Mesaj iskeletinin taban token'ını ve net metin token'ını göster")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()

        return cmd_count(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
```

`fmt_usd` fonksiyonuna özellikle bak. Maliyetler çok küçük olabildiği için sabit iki ondalık yetmez: $0,00025 gibi bir tutar iki ondalıkla $0,00 görünürdü. `math.log10` sayının büyüklük basamağını bulur ve ondalık sayısı buna göre ayarlanır.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5 --output-tokens 500 --monthly-calls 100000
```

**Beklenen çıktı:** Üstte dosya bilgisi ve `Çıktı tahmini: 500 token` satırı, ardından tek satırlık bir tablo gelir. Tabloda `Model`, `Girdi token`, `Maliyet/çağrı` ve `Aylık (100.000 çağrı)` sütunları bulunur. En altta `Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)` satırı yer alır.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5 --output-tokens 500 --monthly-calls 100000
Dosya: ornekler/2_eposta_tr.txt  |  720 karakter, 93 kelime
Çıktı tahmini: 500 token (cevap + varsa thinking)

Model             Girdi token  Maliyet/çağrı  Aylık (100.000 çağrı)
----------------  -----------  -------------  ---------------------
Claude Haiku 4.5          306        $0,0028                $280,60

Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
def try_count(client, model: dict, messages: list[dict]) -> tuple[int | None, str | None]:
    """Bir model için sayım yapar; o modele erişim yoksa hatayı tabloya yansıtmak üzere döndürür."""
    try:
        return count_input_tokens(client, model["id"], messages), None
    except anthropic.AuthenticationError:
        raise  # API anahtarı sorunu tüm modelleri etkiler; yukarıda ele alınır
    except anthropic.APIStatusError as e:
        return None, f"HTTP {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "bağlantı hatası"
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
def cmd_count(args, client, pricing: dict) -> int:
    text = read_text(args.file)
    models = select_models(pricing, args.models)
    messages = build_messages(text)

    print(f"Dosya: {args.file}  |  {fmt_int(len(text))} karakter, {fmt_int(len(text.split()))} kelime")
    print(f"Çıktı tahmini: {fmt_int(args.output_tokens)} token (cevap + varsa thinking)")
    print()

    headers = ["Model", "Girdi token"]
    if args.baseline:
        headers += ["Taban", "Net"]
    headers += ["Maliyet/çağrı"]
    if args.monthly_calls:
        headers += [f"Aylık ({fmt_int(args.monthly_calls)} çağrı)"]

    rows, counts, warnings = [], [], []
    for model in models:
        tokens, error = try_count(client, model, messages)
        if error:
            rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
            continue

        counts.append(tokens)
        row = [model["name"], fmt_int(tokens)]
        if args.baseline:
            base, _ = try_count(client, model, build_messages(BASELINE_TEXT))
            row += [fmt_int(base) if base is not None else "-",
                    fmt_int(tokens - base) if base is not None else "-"]

        cost = estimate_cost(model, tokens, args.output_tokens)
        row.append(fmt_usd(cost))
        if args.monthly_calls:
            row.append(fmt_usd(cost * args.monthly_calls))

        rows.append(row)

        if args.output_tokens > model["max_output"]:
            warnings.append(f"{model['name']}: çıktı tahmini, modelin max output sınırını "
                            f"({fmt_int(model['max_output'])}) aşıyor.")

    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    if len(set(counts)) > 1:
        low, high = min(counts), max(counts)
        print(f"Not: Aynı metin modele göre farklı token sayısı verdi "
              f"({fmt_int(low)} – {fmt_int(high)}, fark %{_tr_number(f'{(high / low - 1) * 100:.1f}')}). "
              f"Tokenizer modele özgüdür; her model için ayrı say.")
    for warning in warnings:
        print(f"Uyarı: {warning}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`main` fonksiyonunu da geçersiz API anahtarını yakalayacak şekilde değiştir:

```python
def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()

        return cmd_count(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
```

`try_count` içindeki sıralamaya dikkat et. `AuthenticationError` yakalanıp yeniden fırlatılıyor (`raise`), çünkü geçersiz bir anahtar tek bir modeli değil hepsini etkiler; her satıra "erişilemedi" yazmak yerine programı tek bir anlaşılır mesajla durdurmak daha doğrudur. Diğer API hataları ise yalnızca o modelin satırını etkiler.

**Çalıştır:**

```bash
python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --output-tokens 500 --monthly-calls 100000
python calisma/tokenhesap.py count ornekler/3_teknik_tr.txt --output-tokens 500
```

**Beklenen çıktı:** Tabloda dört satır görmelisin: Haiku 4.5, Sonnet 5.5, Opus 5.5 ve Fable 5.1. Modellerin girdi token sayıları birbirinden farklıysa tablonun altında `Not: Aynı metin modele göre farklı token sayısı verdi` ile başlayan bir satır çıkar. Hesabının bir modele erişimi yoksa o satırda `erişilemedi` yazar ve diğer satırlar normal görünür.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --output-tokens 500 --monthly-calls 100000
Dosya: ornekler/2_eposta_tr.txt  |  720 karakter, 93 kelime
Çıktı tahmini: 500 token (cevap + varsa thinking)

Model              Girdi token  Maliyet/çağrı  Aylık (100.000 çağrı)
-----------------  -----------  -------------  ---------------------
Claude Haiku 4.5           306        $0,0028                $280,60
Claude Sonnet 5.5          390        $0,0058                $578,00
Claude Opus 5.5            390         $0,012              $1.156,00
Claude Fable 5.1           390         $0,029              $2.890,00

Not: Aynı metin modele göre farklı token sayısı verdi (306 – 390, fark %27,5). Tokenizer modele özgüdür; her model için ayrı say.
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

```text
$ python calisma/tokenhesap.py count ornekler/3_teknik_tr.txt --output-tokens 500
Dosya: ornekler/3_teknik_tr.txt  |  949 karakter, 121 kelime
Çıktı tahmini: 500 token (cevap + varsa thinking)

Model              Girdi token  Maliyet/çağrı
-----------------  -----------  -------------
Claude Haiku 4.5           429        $0,0029
Claude Sonnet 5.5          511        $0,0060
Claude Opus 5.5            511         $0,012
Claude Fable 5.1           511         $0,030

Not: Aynı metin modele göre farklı token sayısı verdi (429 – 511, fark %19,1). Tokenizer modele özgüdür; her model için ayrı say.
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

**Kontrol noktası:** Aylık maliyet sütununda en ucuz ve en pahalı modeli karşılaştır. Aradaki fark kaç kat? Bu farkın ne kadarı fiyattan, ne kadarı token sayısındaki farktan geliyor? Bu soruyu cevaplayabiliyorsan adımın asıl amacına ulaştın.

**Bitirdiğinde:** Dosyan [`cozum/adim_4.py`](cozum/adim_4.py) ile aynı işi yapıyor olmalı.

<a id="adim-5"></a>

## Adım 5 — Context doluluğu

**Ne yapacaksın:** Girdi ile beklenen çıktının modelin context window'unun ne kadarını kapladığını hesaplayacak, bunu bir metin çubuğu ve uyarı etiketiyle tabloya ekleyeceksin. Sonra uzun bir log dosyasıyla sınırları zorlayacaksın.

**Neden:** Ders 1.3 §3'te context window'un sınırlı bir çalışma belleği olduğunu ve taşmanın sessiz kesilmeye ya da hataya yol açtığını gördün. Burada iki pratik nokta öğreniyorsun. Birincisi, pencere yalnızca girdiyle dolmaz; model cevabını da aynı pencerenin içinde üretir. Girdi tek başına sığsa bile cevaba yer kalmayabilir. İkincisi, 200K ile 1M token'lık pencereler arasındaki fark soyut bir sayı değildir: aynı dosya bir modelde pencereyi aşarken diğerinde rahatça sığar.

`estimate_cost` fonksiyonunun altına üç hesaplama fonksiyonu ekle:

```python
def context_ratio(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Girdi + çıktı rezervinin context window'a oranı."""
    return (input_tokens + output_tokens) / model["context_window"]


def usage_label(ratio: float) -> str:
    if ratio > 1:
        return "TAŞMA"
    if ratio >= 0.8:
        return "YÜKSEK"
    if ratio >= 0.5:
        return "DİKKAT"
    return "OK"


def render_bar(ratio: float, width: int = 20) -> str:
    filled = min(width, round(min(ratio, 1.0) * width))
    return "█" * filled + "░" * (width - filled)
```

`fmt_usd` fonksiyonunun altına yüzde biçimlendirmesini ekle:

```python
def fmt_pct(ratio: float, decimals: int = 1) -> str:
    sign = "-" if ratio < 0 else ""
    return sign + "%" + _tr_number(f"{abs(ratio) * 100:.{decimals}f}")
```

`cmd_count` fonksiyonunu şu hâliyle değiştir:

```python
def cmd_count(args, client, pricing: dict) -> int:
    text = read_text(args.file)
    models = select_models(pricing, args.models)
    messages = build_messages(text)

    print(f"Dosya: {args.file}  |  {fmt_int(len(text))} karakter, {fmt_int(len(text.split()))} kelime")
    print(f"Çıktı tahmini: {fmt_int(args.output_tokens)} token (cevap + varsa thinking)")
    print()

    headers = ["Model", "Girdi token"]
    if args.baseline:
        headers += ["Taban", "Net"]
    headers += ["Maliyet/çağrı"]
    if args.monthly_calls:
        headers += [f"Aylık ({fmt_int(args.monthly_calls)} çağrı)"]
    headers += ["Context doluluğu"]

    rows, counts, warnings = [], [], []
    for model in models:
        tokens, error = try_count(client, model, messages)
        if error:
            rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
            continue

        counts.append(tokens)
        row = [model["name"], fmt_int(tokens)]
        if args.baseline:
            base, _ = try_count(client, model, build_messages(BASELINE_TEXT))
            row += [fmt_int(base) if base is not None else "-",
                    fmt_int(tokens - base) if base is not None else "-"]

        cost = estimate_cost(model, tokens, args.output_tokens)
        row.append(fmt_usd(cost))
        if args.monthly_calls:
            row.append(fmt_usd(cost * args.monthly_calls))

        ratio = context_ratio(model, tokens, args.output_tokens)
        row.append(f"{render_bar(ratio)} {fmt_pct(ratio)} {usage_label(ratio)}")
        rows.append(row)

        if args.output_tokens > model["max_output"]:
            warnings.append(f"{model['name']}: çıktı tahmini, modelin max output sınırını "
                            f"({fmt_int(model['max_output'])}) aşıyor.")

    print_table(headers, rows, right_align=set(range(1, len(headers) - 1)))
    print()

    if len(set(counts)) > 1:
        low, high = min(counts), max(counts)
        print(f"Not: Aynı metin modele göre farklı token sayısı verdi "
              f"({fmt_int(low)} – {fmt_int(high)}, fark {fmt_pct(high / low - 1)}). "
              f"Tokenizer modele özgüdür; her model için ayrı say.")
    for warning in warnings:
        print(f"Uyarı: {warning}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`usage_label` fonksiyonundaki `if` sıralaması önemlidir. Koşullar yukarıdan aşağıya denenir ve ilk doğru olan fonksiyondan çıkar. En büyük eşiği önce kontrol etmezsen, %120'lik bir oran `DİKKAT` olarak etiketlenir.

**Çalıştır:** Önce uzun log dosyasını üret, sonra ölç:

```bash
python ornekler/uzun_log_uret.py
python calisma/tokenhesap.py count ornekler/uzun_log.txt --output-tokens 4000
```

**Beklenen çıktı:** Tabloya `Context doluluğu` sütunu eklenir. Haiku 4.5 satırında çubuk tamamen dolar ve etiket `TAŞMA` olur: dosya, bu modelin 200K token'lık penceresinin neredeyse iki katı. 1M token'lık pencereye sahip diğer üç modelde çubuk yarıya ulaşmaz ve etiket `OK` olur. Aynı dosyanın Haiku'da diğer modellerden daha az token tuttuğuna da dikkat et; tokenizer farkı burada da görünüyor.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/uzun_log.txt --output-tokens 4000
Dosya: ornekler/uzun_log.txt  |  716.293 karakter, 61.677 kelime
Çıktı tahmini: 4.000 token (cevap + varsa thinking)

Model              Girdi token  Maliyet/çağrı  Context doluluğu
-----------------  -----------  -------------  ---------------------------------
Claude Haiku 4.5       372.018          $0,39  ████████████████████ %188,0 TAŞMA
Claude Sonnet 5.5      422.647          $0,89  █████████░░░░░░░░░░░ %42,7 OK
Claude Opus 5.5        422.647          $1,77  █████████░░░░░░░░░░░ %42,7 OK
Claude Fable 5.1       422.647          $4,43  █████████░░░░░░░░░░░ %42,7 OK

Not: Aynı metin modele göre farklı token sayısı verdi (372.018 – 422.647, fark %13,6). Tokenizer modele özgüdür; her model için ayrı say.
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
def cmd_compare(args, client, pricing: dict) -> int:
    tr_text, en_text = read_text(args.tr_file), read_text(args.en_file)
    models = select_models(pricing, args.models)

    print(f"Türkçe:   {args.tr_file}  |  {fmt_int(len(tr_text))} karakter, {fmt_int(len(tr_text.split()))} kelime")
    print(f"İngilizce: {args.en_file}  |  {fmt_int(len(en_text))} karakter, {fmt_int(len(en_text.split()))} kelime")
    print()

    headers = ["Model", "TR token", "EN token", "TR/EN", "TR fazlası", "1.000 çağrıda ek girdi maliyeti"]
    rows, ratios = [], []
    for model in models:
        tr_tokens, tr_err = try_count(client, model, build_messages(tr_text))
        en_tokens, en_err = try_count(client, model, build_messages(en_text))
        if tr_err or en_err:
            rows.append([model["name"], "-", "-", "-", "-", f"erişilemedi ({tr_err or en_err})"])
            continue
        ratio = tr_tokens / en_tokens
        ratios.append(ratio)
        extra_cost = (tr_tokens - en_tokens) * model["input_per_mtok"] / 1_000_000 * 1000
        rows.append([
            model["name"], fmt_int(tr_tokens), fmt_int(en_tokens),
            _tr_number(f"{ratio:.2f}"), fmt_pct(ratio - 1, 0), fmt_usd(extra_cost),
        ])

    print_table(headers, rows, right_align={1, 2, 3, 4, 5})
    print()
    if ratios:
        avg = sum(ratios) / len(ratios)
        direction = "daha fazla" if avg >= 1 else "daha az"
        print(f"Ortalama: Türkçe metin aynı içerik için {fmt_pct(abs(avg - 1), 0)} {direction} girdi token'ı kullandı.")
        print("Bu oran metin türüne ve modele göre değişir; kendi verinle ölç.")
    return 0
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştir. `main` artık hangi komutun çağrıldığına bakıp işi doğru fonksiyona yolluyor:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenhesap", description="Çağrı öncesi token, maliyet ve context hesaplayıcı.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat dosyası (varsayılan: pricing.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_count = sub.add_parser("count", help="Bir metnin token, maliyet ve context doluluğunu hesapla")
    p_count.add_argument("file", help="Metin dosyası ('-' ile standart girdi)")
    p_count.add_argument("--models", help=MODELS_HELP)
    p_count.add_argument("--output-tokens", type=int, default=1000, help="Beklenen çıktı token'ı (varsayılan: 1000)")
    p_count.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet gösterilir")
    p_count.add_argument("--baseline", action="store_true", help="Mesaj iskeletinin taban token'ını ve net metin token'ını göster")

    p_compare = sub.add_parser("compare", help="Aynı içeriğin Türkçe ve İngilizce token sayılarını karşılaştır")
    p_compare.add_argument("tr_file", help="Türkçe metin dosyası")
    p_compare.add_argument("en_file", help="İngilizce metin dosyası")
    p_compare.add_argument("--models", help=MODELS_HELP)
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()

        if args.command == "count":
            return cmd_count(args, client, pricing)
        return cmd_compare(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
```

**Çalıştır:**

```bash
python calisma/tokenhesap.py compare ornekler/1_kisa_tr.txt ornekler/1_kisa_en.txt
python calisma/tokenhesap.py compare ornekler/2_eposta_tr.txt ornekler/2_eposta_en.txt
python calisma/tokenhesap.py compare ornekler/3_teknik_tr.txt ornekler/3_teknik_en.txt
```

**Beklenen çıktı:** Her komut iki dosyanın karakter ve kelime sayısını, ardından dört satırlık bir tablo basar. Tabloda `TR token`, `EN token`, `TR/EN`, `TR fazlası` ve `1.000 çağrıda ek girdi maliyeti` sütunları bulunur. En altta tüm modellerin ortalama oranını veren bir cümle yer alır.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py compare ornekler/1_kisa_tr.txt ornekler/1_kisa_en.txt
Türkçe:   ornekler/1_kisa_tr.txt  |  86 karakter, 10 kelime
İngilizce: ornekler/1_kisa_en.txt  |  85 karakter, 16 kelime

Model              TR token  EN token  TR/EN  TR fazlası  1.000 çağrıda ek girdi maliyeti
-----------------  --------  --------  -----  ----------  -------------------------------
Claude Haiku 4.5         41        25   1,64         %64                           $0,016
Claude Sonnet 5.5        52        34   1,53         %53                           $0,036
Claude Opus 5.5          52        34   1,53         %53                           $0,072
Claude Fable 5.1         52        34   1,53         %53                            $0,18

Ortalama: Türkçe metin aynı içerik için %56 daha fazla girdi token'ı kullandı.
Bu oran metin türüne ve modele göre değişir; kendi verinle ölç.
```

```text
$ python calisma/tokenhesap.py compare ornekler/2_eposta_tr.txt ornekler/2_eposta_en.txt
Türkçe:   ornekler/2_eposta_tr.txt  |  720 karakter, 93 kelime
İngilizce: ornekler/2_eposta_en.txt  |  753 karakter, 126 kelime

Model              TR token  EN token  TR/EN  TR fazlası  1.000 çağrıda ek girdi maliyeti
-----------------  --------  --------  -----  ----------  -------------------------------
Claude Haiku 4.5        306       166   1,84         %84                            $0,14
Claude Sonnet 5.5       390       230   1,70         %70                            $0,32
Claude Opus 5.5         390       230   1,70         %70                            $0,64
Claude Fable 5.1        390       230   1,70         %70                            $1,60

Ortalama: Türkçe metin aynı içerik için %73 daha fazla girdi token'ı kullandı.
Bu oran metin türüne ve modele göre değişir; kendi verinle ölç.
```

```text
$ python calisma/tokenhesap.py compare ornekler/3_teknik_tr.txt ornekler/3_teknik_en.txt
Türkçe:   ornekler/3_teknik_tr.txt  |  949 karakter, 121 kelime
İngilizce: ornekler/3_teknik_en.txt  |  994 karakter, 155 kelime

Model              TR token  EN token  TR/EN  TR fazlası  1.000 çağrıda ek girdi maliyeti
-----------------  --------  --------  -----  ----------  -------------------------------
Claude Haiku 4.5        429       207   2,07        %107                            $0,22
Claude Sonnet 5.5       511       308   1,66         %66                            $0,41
Claude Opus 5.5         511       308   1,66         %66                            $0,81
Claude Fable 5.1        511       308   1,66         %66                            $2,03

Ortalama: Türkçe metin aynı içerik için %76 daha fazla girdi token'ı kullandı.
Bu oran metin türüne ve modele göre değişir; kendi verinle ölç.
```

**Kontrol noktası:** Üç metin türündeki oranları karşılaştır. Kısa cümle, e-posta ve teknik olay raporu aynı oranı mı veriyor? Türkçe metinlerin kelime sayısının İngilizce karşılıklarından az, token sayısının ise fazla olması ne anlama geliyor? Sonuçlarını Ders 1.3'teki kaba tabloyla karşılaştır.

**Bitirdiğinde:** Dosyan [`cozum/adim_6.py`](cozum/adim_6.py) ile aynı işi yapıyor olmalı.

<a id="adim-7"></a>

## Adım 7 — Tahmin ile gerçeği karşılaştır

**Ne yapacaksın:** `--verify` seçeneği ekleyeceksin. Bu seçenek verildiğinde araç, aynı mesajı önce `count_tokens` ile sayacak, sonra gerçekten modele gönderecek ve iki ölçümü yan yana gösterecek.

**Neden:** Ders 1.4 §6.1'de `count_tokens` ile `usage` arasındaki farkı okudun: biri çağrı öncesi bir tahmin, diğeri faturada esas alınan kesin ölçüm. Bu adım iki ölçümü aynı ekranda gösteriyor ve sana hangisini ne zaman kullanacağını kalıcı olarak öğretiyor. Ayrıca çıktı token'ı hakkında önemli bir gerçekle yüzleşiyorsun: çağrıdan önce cevabın kaç token olacağını bilemezsin. Bu yüzden tahmin satırında çıktı için `max_tokens` üst sınırı, yani en kötü durum kullanılıyor.

Sabitlerin arasına, `BASELINE_TEXT` satırının altına doğrulama talimatını ekle:

```python
# --verify modunda modele gönderilen talimat. count_tokens ve gerçek çağrı
# AYNI mesajı kullanır; böylece tahmin ile gerçek ölçüm karşılaştırılabilir.
VERIFY_INSTRUCTION = "Aşağıdaki metni tek cümleyle özetle:\n\n"
```

`cmd_count` fonksiyonundan sonra doğrulama fonksiyonunu ekle:

```python
def run_verify(client, model: dict, text: str, max_tokens: int) -> None:
    """Tek bir gerçek çağrı yapıp count_tokens tahminini usage ile karşılaştırır.

    Çağrı öncesinde çıktı uzunluğu bilinemez; tahmin satırında çıktı için
    max_tokens üst sınırı kullanılır (en kötü durum maliyeti).
    """
    messages = build_messages(VERIFY_INSTRUCTION + text)
    estimated = count_input_tokens(client, model["id"], messages)
    response = client.messages.create(model=model["id"], max_tokens=max_tokens, messages=messages)
    usage = response.usage

    print(f"Doğrulama ({model['name']}, gerçek çağrı, max_tokens={max_tokens})")
    print_table(
        ["", "Girdi token", "Çıktı token", "Maliyet"],
        [
            ["Tahmin (count_tokens + max_tokens)", fmt_int(estimated), fmt_int(max_tokens),
             fmt_usd(estimate_cost(model, estimated, max_tokens))],
            ["Gerçek (usage)", fmt_int(usage.input_tokens), fmt_int(usage.output_tokens),
             fmt_usd(estimate_cost(model, usage.input_tokens, usage.output_tokens))],
        ],
        right_align={1, 2, 3},
    )
    diff = usage.input_tokens - estimated
    print(f"Girdi farkı: {diff:+d} token. Faturada esas alınan değer usage'dır.")
    answer = "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
    if answer:
        print(f"Model yanıtı: {answer}")
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/tokenhesap.py count ornekler/2_eposta_tr.txt --models haiku-4-5 --verify
Dosya: ornekler/2_eposta_tr.txt  |  720 karakter, 93 kelime
Çıktı tahmini: 1.000 token (cevap + varsa thinking)

Model             Girdi token  Maliyet/çağrı  Context doluluğu
----------------  -----------  -------------  ----------------------------
Claude Haiku 4.5          306        $0,0053  ░░░░░░░░░░░░░░░░░░░░ %0,7 OK

Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)

Doğrulama (Claude Haiku 4.5, gerçek çağrı, max_tokens=300)
                                    Girdi token  Çıktı token   Maliyet
----------------------------------  -----------  -----------  --------
Tahmin (count_tokens + max_tokens)          325          300   $0,0018
Gerçek (usage)                              325          131  $0,00098
Girdi farkı: +0 token. Faturada esas alınan değer usage'dır.
Model yanıtı: Fatura entegrasyonu testlerinde yüzde 95 başarılı sonuç alınmış, kalan yüzde 5'lik sorunlu kayıtlar için otomatik kontrol sistemi önerilirken, canlıya geçmeden önce Ayşe Hanım'ın ekibinin bir hafta boyunca raporu incelemesi ve salı günü öğleden sonra yapılacak görüşmede detaylar konuşulması istenmektedir.
```

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
