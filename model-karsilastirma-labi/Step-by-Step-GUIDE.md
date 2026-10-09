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
"""Model karşılaştırma lab'ı — Adım 1: i̇lk ölçüm.

Bu dosya, Step-by-Step-GUIDE.md rehberindeki 1. adımın sonunda calisma/modellab.py
dosyasının ulaşması gereken hâldir. Kendi başına çalışır:

    python cozum/adim_1.py run gorevler/1_tek_prompt.yaml
"""

import argparse
import os
import sys
import time

import anthropic
import yaml

# İlk adımda tek model kullanılır; Adım 2'de model bilgisi pricing.yaml dosyasından gelecek.
MODEL_ID = "claude-haiku-4-5-20251001"
MODEL_NAME = "Claude Haiku 4.5"


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_tasks(path: str) -> dict:
    """Görev dosyasını (YAML) okur."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# API çağrıları
# ---------------------------------------------------------------------------

def build_messages(prompt: str) -> list[dict]:
    return [{"role": "user", "content": prompt}]


def stream_call(client, model_id: str, messages: list[dict], max_tokens: int, system: str | None = None,
                extra: dict | None = None) -> dict:
    """Streaming ile tek çağrı yapar; ilk token süresini, toplam süreyi ve usage değerlerini ölçer.

    Süreler saniye cinsindendir. İlk token süresi, isteğin gönderilmesinden ilk metin
    parçasının gelmesine kadar geçen süredir (Ders 1.4 §4.3). `extra`, modele özgü ek
    istek ayarlarıdır (pricing.yaml > cagri_ayarlari); olduğu gibi isteğe eklenir.
    """
    kwargs = {"model": model_id, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    kwargs.update(extra or {})
    start = time.perf_counter()
    first = None
    chunks = []
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if first is None:
                first = time.perf_counter()
            chunks.append(text)
        final = stream.get_final_message()
    end = time.perf_counter()
    return {
        "text": "".join(chunks).strip(),
        "ttft": (first or end) - start,
        "total": end - start,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "stop_reason": final.stop_reason,
    }


# ---------------------------------------------------------------------------
# Biçimlendirme (Türkçe sayı yazımı: binlik ayırıcı nokta, ondalık virgül)
# ---------------------------------------------------------------------------

def _tr_number(formatted: str) -> str:
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_sec(seconds: float) -> str:
    """Süreyi okunur yazar: 1 saniyenin altı milisaniye, üstü saniye."""
    if seconds < 1:
        return f"{round(seconds * 1000)} ms"
    return _tr_number(f"{seconds:.2f}") + " s"


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_run(args, client) -> int:
    tasks = load_tasks(args.tasks)
    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  model: {MODEL_NAME}  |  max_tokens={args.max_tokens}")

    for task in tasks["gorevler"]:
        print()
        print(f"[{task['ad']}]")
        result = stream_call(client, MODEL_ID, build_messages(task["prompt"]), args.max_tokens, task.get("system"))
        print(result["text"])
        print()
        print(f"İlk token: {fmt_sec(result['ttft'])}  |  Toplam: {fmt_sec(result['total'])}  |  "
              f"Girdi: {result['input_tokens']} token  |  Çıktı: {result['output_tokens']} token  |  "
              f"Durma nedeni: {result['stop_reason']}")
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modellab", description="Aynı görev setini modellerde çalıştırıp gecikme, maliyet ve kaliteyi karşılaştır.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Görev setini modellerde çalıştır ve sonuçları kaydet (ücretli)")
    p_run.add_argument("tasks", help="Görev dosyası (YAML)")
    p_run.add_argument("--max-tokens", type=int, default=300, help="Her çağrı için max_tokens (varsayılan: 300)")
    return parser


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
            return 2
        client = anthropic.Anthropic()
    return cmd_run(args, client)


if __name__ == "__main__":
    sys.exit(main())
```

Kodda dikkat etmen gereken üç nokta var. `stream_call` projenin kalbidir: `time.perf_counter()` isteğin hemen öncesinde başlar, ilk metin parçası geldiğinde `first` işaretlenir, akış bitince `end` alınır; `get_final_message()` ise akış bittikten sonra `usage` ve `stop_reason` alanlarını verir. `kwargs` sözlüğü `system` talimatını yalnızca görevde varsa, `extra` sözlüğündeki ek ayarları da varsa isteğe ekler; bu adımda ikisi de boş. `main` fonksiyonundaki `client=None` parametresi testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/1_tek_prompt.yaml
```

**Beklenen çıktı:** İlk satırda görev setinin adı ve model, ardından `[mikroservis]` başlığı altında modelin üç maddelik yanıtı, en altta `İlk token:`, `Toplam:`, `Girdi:`, `Çıktı:` ve `Durma nedeni: end_turn` bilgilerini taşıyan tek bir satır görmelisin.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py run gorevler/1_tek_prompt.yaml
Görev seti: Tek prompt (1 görev)  |  model: Claude Haiku 4.5  |  max_tokens=300

[mikroservis]
1. Dağıtık sistem karmaşıklığı, hata ayıklama ve izlemeyi önemli ölçüde zorlaştırır.

2. Ağ gecikmesi ve bağlantı hatalarından kaynaklanan performans sorunları ortaya çıkabilir.

3. Veri tutarlılığını sağlamak ve hizmetler arasında işlemleri yönetmek operasyonel olarak zordur.

İlk token: 894 ms  |  Toplam: 2,06 s  |  Girdi: 69 token  |  Çıktı: 125 token  |  Durma nedeni: end_turn
```

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
import argparse
import math
import os
import sys
import time
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")
```

`load_tasks` fonksiyonunun üstüne fiyat dosyasını okuyan ve model listesini süzen iki fonksiyon ekle:

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

`stream_call` fonksiyonunun altına hatayı yakalayan sarmalayıcıyı ve ardından iki hesap fonksiyonunu ekle:

```python
def try_call(client, model: dict, messages: list[dict], max_tokens: int, system: str | None) -> tuple[dict | None, str | None]:
    """Bir model için çağrı yapar; o modele erişim yoksa hatayı tabloya yansıtmak üzere döndürür."""
    try:
        return stream_call(client, model["id"], messages, max_tokens, system, model.get("cagri_ayarlari")), None
    except anthropic.AuthenticationError:
        raise  # API anahtarı sorunu tüm modelleri etkiler; yukarıda ele alınır
    except anthropic.APIStatusError as e:
        return None, f"HTTP {e.status_code}"
    except anthropic.APIConnectionError:
        return None, "bağlantı hatası"


def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000


def tokens_per_second(output_tokens: int, ttft: float, total: float) -> float | None:
    """Üretim hızı: ilk token geldikten sonra saniyede kaç çıktı token'ı üretildi.

    Üretim süresi 50 ms'nin altındaysa (birkaç token'lık yanıt) hız güvenilir ölçülemez; None döner.
    """
    generation = total - ttft
    if generation < 0.05:
        return None
    return output_tokens / generation
```

`_tr_number` fonksiyonunun altına sayı biçimlendiricileri ekle:

```python
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
```

`fmt_sec` fonksiyonunun altına hız biçimlendiricisini ve tablo basan yardımcıyı ekle:

```python
def fmt_speed(speed: float | None) -> str:
    """Üretim hızı; ölçülemediyse '-'."""
    return "-" if speed is None else fmt_int(round(speed))


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

`cmd_run` fonksiyonunu şu hâliyle değiştir. Fonksiyon artık üçüncü bir parametre (`pricing`) alıyor ve yanıt metnini yalnızca `--show-output` verildiğinde yazıyor:

```python
def cmd_run(args, client, pricing: dict) -> int:
    tasks = load_tasks(args.tasks)
    models = select_models(pricing, args.models)

    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  {len(models)} model  |  "
          f"max_tokens={fmt_int(args.max_tokens)}")
    print()

    failures = []
    for task in tasks["gorevler"]:
        print(f"[{task['ad']}]" + (f" (tier {task['tier']})" if task.get("tier") else ""))
        messages = build_messages(task["prompt"])
        headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet"]
        rows = []
        for model in models:
            result, error = try_call(client, model, messages, args.max_tokens, task.get("system"))
            if error:
                rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
                failures.append(f"{task['ad']}/{model['key']}")
                continue
            cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
            rows.append([
                model["name"], fmt_sec(result["ttft"]), fmt_sec(result["total"]),
                fmt_speed(tokens_per_second(result["output_tokens"], result["ttft"], result["total"])),
                fmt_int(result["output_tokens"]), fmt_usd(cost),
            ])
            if args.show_output:
                print(f"  {model['name']}:\n" + "\n".join("    " + line for line in result["text"].splitlines()))
        print_table(headers, rows, right_align=set(range(1, len(headers))))
        print()

    if failures:
        print(f"Uyarı: {len(failures)} çağrı başarısız oldu: {', '.join(failures)}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`build_parser` ve `main` fonksiyonlarını da şu hâlleriyle değiştir:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modellab", description="Aynı görev setini modellerde çalıştırıp gecikme, maliyet ve kaliteyi karşılaştır.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat dosyası (varsayılan: pricing.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Görev setini modellerde çalıştır ve sonuçları kaydet (ücretli)")
    p_run.add_argument("tasks", help="Görev dosyası (YAML)")
    p_run.add_argument("--models", help=MODELS_HELP)
    p_run.add_argument("--max-tokens", type=int, default=300, help="Her çağrı için max_tokens (varsayılan: 300)")
    p_run.add_argument("--show-output", action="store_true", help="Model yanıtlarını da yazdır")
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
        return cmd_run(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
```

`try_call` içindeki sıralamaya dikkat et. `AuthenticationError` yakalanıp yeniden fırlatılıyor (`raise`), çünkü geçersiz bir anahtar tek bir modeli değil hepsini etkiler; her satıra "erişilemedi" yazmak yerine programı tek bir anlaşılır mesajla durdurmak daha doğrudur. `try_call` ayrıca modelin `cagri_ayarlari` sözlüğünü `stream_call`'a iletir; `kwargs.update(extra or {})` satırı bu ayarları isteğe ekler. Kod ayarların içeriğini bilmez; bir model yeni bir parametre isterse yalnızca `pricing.yaml` değişir. `tokens_per_second` ise üretim süresi 50 ms'nin altındaysa `None` döndürür: birkaç token'lık bir yanıtta hız ölçülemez ve ölçülemeyen değer uydurulmaz, tabloda "-" olarak kalır.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/1_tek_prompt.yaml --show-output
python calisma/modellab.py run gorevler/1_tek_prompt.yaml --models haiku-4-5,fable-5-1 --max-tokens 40 --show-output
```

**Beklenen çıktı:** İlk komutta dört modelin yanıtı ve ardından dört satırlık bir tablo gelir: `İlk token`, `Toplam`, `token/sn`, `Çıktı token` ve `Maliyet` sütunları. Maliyet modelden modele kat kat değişir; ilk token süresi de değişir ama fiyat sırasını izlemez, en pahalı model ilk token'ı en hızlı verebilir. İkinci komutta yalnızca iki satır vardır; `Çıktı token` sütunu 40'ta kalır ve yanıtlar yarım biter.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py run gorevler/1_tek_prompt.yaml --show-output
Görev seti: Tek prompt (1 görev)  |  4 model  |  max_tokens=300

[mikroservis] (tier 2)
  Claude Haiku 4.5:
    1. Dağıtık sistem yönetimi ve hata ayıklama işlemleri monolitik mimarilere göre çok daha karmaşık ve zaman alıcıdır.

    2. Servisler arasında veri tutarlılığını sağlamak ve network gecikmelerini yönetmek önemli teknik zorluklar yaratır.

    3. İnfrastruktur maliyetleri, monitoring, logging ve deployment otomasyonu gereksinimleri nedeniyle ciddi oranda artış gösterir.
  Claude Sonnet 5.5:
    1. Servisler ağ üzerinden haberleştiği için gecikme, kısmi hatalar ve dağıtık sistemlerin getirdiği karmaşıklık (zincirleme arızalar, tutarsız veri vb.) tek parça bir uygulamaya kıyasla çok daha zor yönetilir.
    2. Servisler arası veri tutarlılığını sağlamak, dağıtık işlemler ve eventual consistency gerektirdiğinden geliştirme ve hata ayıklama süreçlerini ciddi biçimde zorlaştırır.
    3. Çok sayıda bağımsız servisin dağıtımı, izlenmesi, loglanması ve versiyonlanması için gereken operasyonel altyapı ve DevOps olgunluğu hem maliyeti hem de ekip yükünü önemli ölçüde artırır.
  Claude Opus 5.5:
    1. Servisler ağ üzerinden haberleştiği için gecikme, kısmi hatalar ve dağıtık sistemlere özgü karmaşıklık ciddi biçimde artar.
    2. Her servisin kendi veritabanına sahip olması, servisler arası veri tutarlılığını ve dağıtık işlem yönetimini oldukça zorlaştırır.
    3. Çok sayıda bağımsız servisin dağıtımı, izlenmesi ve hata ayıklaması, güçlü bir DevOps altyapısı ve yüksek operasyonel maliyet gerektirir.
  Claude Fable 5.1:
    1. Servisler arası ağ iletişimi gecikme, kısmi arıza ve veri tutarlılığı (dağıtık işlem) sorunlarını beraberinde getirerek sistemin güvenilirliğini zorlaştırır.
    2. Onlarca bağımsız servisin dağıtımı, izlenmesi, loglanması ve hata ayıklanması operasyonel karmaşıklığı ve altyapı maliyetini ciddi ölçüde artırır.
    3. Servis sınırlarının yanlış belirlenmesi, dağıtık bir monolite veya aşırı bağımlı servislere yol açarak hem bakımı hem de yeniden yapılandırmayı monolitten daha zor hâle getirir.
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet
-----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5      717 ms  2,22 s        96          144  $0,00079
Claude Sonnet 5.5     842 ms  3,46 s       113          297   $0,0031
Claude Opus 5.5       1,05 s  3,02 s       106          210   $0,0045
Claude Fable 5.1      586 ms  4,38 s        67          256    $0,014

Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

```text
$ python calisma/modellab.py run gorevler/1_tek_prompt.yaml --models haiku-4-5,fable-5-1 --max-tokens 40 --show-output
Görev seti: Tek prompt (1 görev)  |  2 model  |  max_tokens=40

[mikroservis] (tier 2)
  Claude Haiku 4.5:
    1. Dağıtılmış sistem kompleksitesi nedeniyle hata ayıklama, izleme ve sorun giderme önemli öl
  Claude Fable 5.1:
    1. Servisler arası ağ iletişimi, gecikme, hata toleransı ve dağıtık işlem (dist
Model             İlk token  Toplam  token/sn  Çıktı token   Maliyet
----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5     740 ms  1,11 s       108           40  $0,00027
Claude Fable 5.1     1,11 s  2,05 s        42           40   $0,0029

Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")
```

`print_table` fonksiyonunun altına kayıt fonksiyonlarını ekle:

```python
def default_results_path(tasks_path: str) -> Path:
    return DEFAULT_RESULTS_DIR / (Path(tasks_path).stem + ".jsonl")


def save_results(path: Path, records: list[dict], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

`cmd_run` fonksiyonunu şu hâliyle değiştir. Her başarılı çağrı için bir kayıt sözlüğü oluşturuluyor ve döngü bitince dosyaya yazılıyor:

```python
def cmd_run(args, client, pricing: dict) -> int:
    tasks = load_tasks(args.tasks)
    models = select_models(pricing, args.models)
    out_path = Path(args.out) if args.out else default_results_path(args.tasks)

    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  {len(models)} model  |  "
          f"max_tokens={fmt_int(args.max_tokens)}")
    print()

    records, failures = [], []
    for task in tasks["gorevler"]:
        print(f"[{task['ad']}]" + (f" (tier {task['tier']})" if task.get("tier") else ""))
        messages = build_messages(task["prompt"])
        headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet"]
        rows = []
        for model in models:
            result, error = try_call(client, model, messages, args.max_tokens, task.get("system"))
            if error:
                rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
                failures.append(f"{task['ad']}/{model['key']}")
                continue
            cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
            records.append({
                "tur": "calistirma", "zaman": datetime.now().isoformat(timespec="seconds"),
                "gorev": task["ad"], "tier": task.get("tier"), "model": model["key"], "model_adi": model["name"],
                "ilk_token_sn": round(result["ttft"], 3), "toplam_sn": round(result["total"], 3),
                "girdi_token": result["input_tokens"], "cikti_token": result["output_tokens"],
                "maliyet": cost, "yanit": result["text"],
            })
            rows.append([
                model["name"], fmt_sec(result["ttft"]), fmt_sec(result["total"]),
                fmt_speed(tokens_per_second(result["output_tokens"], result["ttft"], result["total"])),
                fmt_int(result["output_tokens"]), fmt_usd(cost),
            ])
            if args.show_output:
                print(f"  {model['name']}:\n" + "\n".join("    " + line for line in result["text"].splitlines()))
        print_table(headers, rows, right_align=set(range(1, len(headers))))
        print()

    save_results(out_path, records)
    shown = out_path.relative_to(PROJECT_DIR) if out_path.is_relative_to(PROJECT_DIR) else out_path
    print(f"Kaydedildi: {shown.as_posix()} ({len(records)} kayıt)")
    if failures:
        print(f"Uyarı: {len(failures)} çağrı başarısız oldu: {', '.join(failures)}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py run gorevler/2_gorev_seti.yaml --out sonuclar/2_gorev_seti.jsonl
Görev seti: Görev seti (5 görev)  |  4 model  |  max_tokens=300

[siniflandirma] (tier 1)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet
-----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5      634 ms  647 ms         -            5  $0,00019
Claude Sonnet 5.5     762 ms  782 ms         -            5  $0,00045
Claude Opus 5.5       2,46 s  2,46 s         -          101   $0,0028
Claude Fable 5.1      1,92 s  2,89 s         5            5   $0,0023

[veri_cikarma] (tier 1)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet
-----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5      450 ms  835 ms       143           55  $0,00051
Claude Sonnet 5.5     716 ms  942 ms       208           47   $0,0011
Claude Opus 5.5       2,02 s  2,28 s       183           47   $0,0021
Claude Fable 5.1      669 ms  1,44 s        61           47   $0,0053

[ozet] (tier 2)
Model              İlk token  Toplam  token/sn  Çıktı token  Maliyet
-----------------  ---------  ------  --------  -----------  -------
Claude Haiku 4.5      504 ms  2,35 s       101          186  $0,0013
Claude Sonnet 5.5     1,37 s  2,44 s       181          193  $0,0027
Claude Opus 5.5       857 ms  2,25 s       152          212  $0,0058
Claude Fable 5.1      582 ms  2,35 s       102          181   $0,013

[kod] (tier 2)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet
-----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5      472 ms  1,38 s       139          126  $0,00071
Claude Sonnet 5.5     889 ms  1,51 s       199          123   $0,0014
Claude Opus 5.5       1,26 s  2,29 s       119          122   $0,0029
Claude Fable 5.1      1,89 s  3,85 s        62          122   $0,0072

[muhakeme] (tier 3)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet
-----------------  ---------  ------  --------  -----------  --------
Claude Haiku 4.5      506 ms  525 ms         -            7  $0,00013
Claude Sonnet 5.5     563 ms  1,06 s        10            5  $0,00028
Claude Opus 5.5       1,36 s  1,37 s         -           29   $0,0010
Claude Fable 5.1      573 ms  1,21 s         8            5   $0,0014

Kaydedildi: sonuclar/2_gorev_seti.jsonl (20 kayıt)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")

# Görev dosyasında tanınan kontrol türleri. Bilinmeyen bir tür dosya yüklenirken hata verir.
CHECK_KINDS = ("icermeli", "icermeli_biri", "icermemeli", "max_kelime", "json")
```

`load_tasks` fonksiyonunu, görev dosyasını yüklerken doğrulayan şu hâliyle değiştir:

```python
def load_tasks(path: str) -> dict:
    """Görev dosyasını okur; her görevde ad ve prompt olduğunu, kontrol türlerinin tanındığını doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or not data.get("gorevler"):
        raise ValueError(f"{path}: 'gorevler' listesi boş ya da yok.")
    for task in data["gorevler"]:
        if "ad" not in task or "prompt" not in task:
            raise ValueError(f"{path}: her görevde 'ad' ve 'prompt' alanları olmalı.")
        unknown = [k for k in task.get("kontroller", {}) if k not in CHECK_KINDS]
        if unknown:
            raise ValueError(f"{path}: '{task['ad']}' görevinde bilinmeyen kontrol: {', '.join(unknown)}")
    return data
```

`tokens_per_second` fonksiyonunun altına JSON çözücüyü ve kontrol fonksiyonunu ekle:

```python
def _parse_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned[cleaned.find("{"):] if "{" in cleaned else cleaned
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def check_output(text: str, checks: dict) -> tuple[float | None, list[str]]:
    """Çıktıyı görevin kontrollerine göre puanlar: (0–100 puan, başarısız kontrollerin listesi).

    Kontrol yoksa puan None döner. Her kontrol eşit ağırlıktadır.
    """
    if not checks:
        return None, []
    lowered = text.lower()
    failed = []
    for kind, rule in checks.items():
        if kind == "icermeli":
            missing = [s for s in rule if s.lower() not in lowered]
            if missing:
                failed.append(f"icermeli: {', '.join(missing)}")
        elif kind == "icermeli_biri":
            if not any(s.lower() in lowered for s in rule):
                failed.append(f"icermeli_biri: {' | '.join(rule)}")
        elif kind == "icermemeli":
            present = [s for s in rule if s.lower() in lowered]
            if present:
                failed.append(f"icermemeli: {', '.join(present)}")
        elif kind == "max_kelime":
            words = len(text.split())
            if words > rule:
                failed.append(f"max_kelime: {words} > {rule}")
        elif kind == "json":
            parsed = _parse_json(text)
            if not isinstance(parsed, dict):
                failed.append("json: geçerli JSON nesnesi değil")
            else:
                missing = [k for k in rule if k not in parsed]
                if missing:
                    failed.append(f"json: eksik alan {', '.join(missing)}")
    score = (len(checks) - len(failed)) / len(checks) * 100
    return score, failed
```

`fmt_sec` fonksiyonunun altına yüzde biçimlendiricisini, `fmt_speed` fonksiyonunun altına puan biçimlendiricisini ekle:

```python
def fmt_pct(ratio: float, decimals: int = 0) -> str:
    return "%" + _tr_number(f"{ratio * 100:.{decimals}f}")
```

```python
def fmt_score(score: float | None) -> str:
    return "-" if score is None else fmt_pct(score / 100)
```

`cmd_run` fonksiyonunu şu hâliyle değiştir. Tabloya `Puan` sütunu, kayda `kesildi`, `puan` ve `basarisiz` alanları eklendi:

```python
def cmd_run(args, client, pricing: dict) -> int:
    tasks = load_tasks(args.tasks)
    models = select_models(pricing, args.models)
    out_path = Path(args.out) if args.out else default_results_path(args.tasks)

    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  {len(models)} model  |  "
          f"max_tokens={fmt_int(args.max_tokens)}")
    print()

    records, failures = [], []
    for task in tasks["gorevler"]:
        print(f"[{task['ad']}]" + (f" (tier {task['tier']})" if task.get("tier") else ""))
        messages = build_messages(task["prompt"])
        headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet", "Puan"]
        rows = []
        for model in models:
            result, error = try_call(client, model, messages, args.max_tokens, task.get("system"))
            if error:
                rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
                failures.append(f"{task['ad']}/{model['key']}")
                continue
            cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
            score, failed = check_output(result["text"], task.get("kontroller", {}))
            cut = result["stop_reason"] == "max_tokens"
            records.append({
                "tur": "calistirma", "zaman": datetime.now().isoformat(timespec="seconds"),
                "gorev": task["ad"], "tier": task.get("tier"), "model": model["key"], "model_adi": model["name"],
                "ilk_token_sn": round(result["ttft"], 3), "toplam_sn": round(result["total"], 3),
                "girdi_token": result["input_tokens"], "cikti_token": result["output_tokens"],
                "kesildi": cut, "maliyet": cost, "puan": score, "basarisiz": failed, "yanit": result["text"],
            })
            rows.append([
                model["name"], fmt_sec(result["ttft"]), fmt_sec(result["total"]),
                fmt_speed(tokens_per_second(result["output_tokens"], result["ttft"], result["total"])),
                fmt_int(result["output_tokens"]) + (" (kesildi)" if cut else ""), fmt_usd(cost), fmt_score(score),
            ])
            if args.show_output:
                print(f"  {model['name']}:\n" + "\n".join("    " + line for line in result["text"].splitlines()))
        print_table(headers, rows, right_align=set(range(1, len(headers))))
        print()

    save_results(out_path, records)
    shown = out_path.relative_to(PROJECT_DIR) if out_path.is_relative_to(PROJECT_DIR) else out_path
    print(f"Kaydedildi: {shown.as_posix()} ({len(records)} kayıt)")
    if failures:
        print(f"Uyarı: {len(failures)} çağrı başarısız oldu: {', '.join(failures)}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`check_output` içinde kontrol yoksa puanın `None` olduğuna dikkat et: "0 puan" ile "puanlanmadı" farklı şeylerdir ve `fmt_score` ikincisini "-" olarak yazar. Metin küçük harfe çevrilerek karşılaştırılır; böylece "Fatura" ile "fatura" aynı sayılır.

**Çalıştır:**

```bash
python calisma/modellab.py run gorevler/2_gorev_seti.yaml
```

**Beklenen çıktı:** Adım 3'teki tabloların sonuna `Puan` sütunu eklenir. Çoğu satırda `%100` görürsün; bir model bir görevde kuralı kaçırdıysa `%50` ya da `%67` gibi bir değer çıkar. Bir yanıt 300 token'a takılırsa `Çıktı token` sütununda `(kesildi)` yazar.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py run gorevler/2_gorev_seti.yaml --out sonuclar/2_gorev_seti.jsonl
Görev seti: Görev seti (5 görev)  |  4 model  |  max_tokens=300

[siniflandirma] (tier 1)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet  Puan
-----------------  ---------  ------  --------  -----------  --------  ----
Claude Haiku 4.5      591 ms  613 ms         -            5  $0,00019  %100
Claude Sonnet 5.5     721 ms  731 ms         -            5  $0,00045  %100
Claude Opus 5.5       2,26 s  2,27 s         -            5  $0,00090  %100
Claude Fable 5.1      1,79 s  2,72 s         5            5   $0,0023  %100

[veri_cikarma] (tier 1)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet  Puan
-----------------  ---------  ------  --------  -----------  --------  ----
Claude Haiku 4.5      448 ms  828 ms       145           55  $0,00051   %67
Claude Sonnet 5.5     714 ms  881 ms       283           47   $0,0011  %100
Claude Opus 5.5       2,37 s  2,40 s         -          103   $0,0032  %100
Claude Fable 5.1      549 ms  1,36 s        58           47   $0,0053  %100

[ozet] (tier 2)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet  Puan
-----------------  ---------  ------  --------  -----------  --------  ----
Claude Haiku 4.5      552 ms  1,71 s       111          128  $0,00097  %100
Claude Sonnet 5.5     1,34 s  2,77 s       124          176   $0,0026  %100
Claude Opus 5.5       1,00 s  2,36 s       146          199   $0,0056  %100
Claude Fable 5.1      553 ms  2,24 s       107          180    $0,013  %100

[kod] (tier 2)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet  Puan
-----------------  ---------  ------  --------  -----------  --------  ----
Claude Haiku 4.5      459 ms  1,36 s       140          126  $0,00071   %50
Claude Sonnet 5.5     741 ms  1,37 s       197          123   $0,0014  %100
Claude Opus 5.5       1,03 s  1,84 s       150          122   $0,0029  %100
Claude Fable 5.1      1,83 s  3,83 s        61          122   $0,0072  %100

[muhakeme] (tier 3)
Model              İlk token  Toplam  token/sn  Çıktı token   Maliyet  Puan
-----------------  ---------  ------  --------  -----------  --------  ----
Claude Haiku 4.5      518 ms  539 ms         -            7  $0,00013   %50
Claude Sonnet 5.5     751 ms  1,22 s        11            5  $0,00028  %100
Claude Opus 5.5       1,52 s  1,52 s         -           36   $0,0012  %100
Claude Fable 5.1      567 ms  1,19 s         8            5   $0,0014  %100

Kaydedildi: sonuclar/2_gorev_seti.jsonl (20 kayıt)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
def mean(values: list[float]) -> float:
    return sum(values) / len(values)
```

`save_results` fonksiyonunun altına okuma fonksiyonunu ekle:

```python
def load_results(path: str) -> list[dict]:
    """JSONL dosyasını okur. 'calistirma' kayıtları ölçümleri, 'puan' kayıtları etiketsiz puanları taşır."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    if not any(r.get("tur") == "calistirma" for r in records):
        raise ValueError(f"{path}: çalıştırma kaydı yok. Önce 'run' komutunu çalıştır.")
    return records
```

`cmd_run` fonksiyonundan sonra üç fonksiyon ekle: özetleyici, karar satırları ve rapor komutu:

```python
def summarize(records: list[dict]) -> list[dict]:
    """Çalıştırma kayıtlarını model başına özetler."""
    runs = [r for r in records if r.get("tur") == "calistirma"]
    summaries = []
    for key in dict.fromkeys(r["model"] for r in runs):
        mine = [r for r in runs if r["model"] == key]
        scored = [r["puan"] for r in mine if r["puan"] is not None]
        speeds = [v for v in (tokens_per_second(r["cikti_token"], r["ilk_token_sn"], r["toplam_sn"]) for r in mine) if v is not None]
        summaries.append({
            "model": key, "model_adi": mine[0]["model_adi"], "calistirma": len(mine),
            "ilk_token_sn": mean([r["ilk_token_sn"] for r in mine]),
            "toplam_sn": mean([r["toplam_sn"] for r in mine]),
            "token_sn": mean(speeds) if speeds else None,
            "cikti_token": mean([r["cikti_token"] for r in mine]),
            "maliyet": mean([r["maliyet"] for r in mine]),
            "kesilen": sum(1 for r in mine if r["kesildi"]),
            "puan": mean(scored) if scored else None,
        })
    return summaries


def decision_lines(summaries: list[dict]) -> list[str]:
    """Özet tablodan karar cümleleri üretir: en hızlı, en ucuz, en yüksek puan ve puan farkı."""
    fastest = min(summaries, key=lambda s: s["ilk_token_sn"])
    cheapest = min(summaries, key=lambda s: s["maliyet"])
    lines = [
        f"En hızlı ilk token: {fastest['model_adi']} ({fmt_sec(fastest['ilk_token_sn'])})",
        f"En ucuz: {cheapest['model_adi']} ({fmt_usd(cheapest['maliyet'])}/görev)",
    ]
    scored = [s for s in summaries if s["puan"] is not None]
    if scored:
        best = max(scored, key=lambda s: s["puan"])
        lines.append(f"En yüksek otomatik puan: {best['model_adi']} ({fmt_score(best['puan'])})")
        spread = max(s["puan"] for s in scored) - min(s["puan"] for s in scored)
        lines.append(f"Otomatik puan farkı (en yüksek − en düşük): {fmt_int(round(spread))} puan "
                     f"(fark küçükse kararı kalite değil, hız ve maliyet verdirir)")
    return lines


def cmd_report(args, pricing: dict) -> int:
    records = load_results(args.results)
    summaries = summarize(records)

    task_count = len({r["gorev"] for r in records if r.get("tur") == "calistirma"})
    print(f"Sonuç dosyası: {args.results}  |  {task_count} görev, {len(summaries)} model")
    print()

    headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet/görev"]
    if args.monthly_calls:
        headers.append(f"Aylık ({fmt_int(args.monthly_calls)} çağrı)")
    headers.append("Oto puan")
    rows = []
    for s in summaries:
        row = [s["model_adi"], fmt_sec(s["ilk_token_sn"]), fmt_sec(s["toplam_sn"]), fmt_speed(s["token_sn"]),
               fmt_int(round(s["cikti_token"])) + (f" ({s['kesilen']} kesildi)" if s["kesilen"] else ""),
               fmt_usd(s["maliyet"])]
        if args.monthly_calls:
            row.append(fmt_usd(s["maliyet"] * args.monthly_calls))
        row.append(fmt_score(s["puan"]))
        rows.append(row)
    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    for line in decision_lines(summaries):
        print(line)
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`build_parser` içinde `return parser` satırının hemen üstüne yeni komutu ekle:

```python

    p_report = sub.add_parser("report", help="Kaydedilmiş sonuçlardan karşılaştırma raporu üret (çağrı yapmaz)")
    p_report.add_argument("results", help="run komutunun yazdığı JSONL dosyası")
    p_report.add_argument("--monthly-calls", type=int, default=0, help="Aylık çağrı sayısı; verilirse aylık maliyet sütunu eklenir")
```

`main` fonksiyonunu şu hâliyle değiştir. `report` komutu API istemcisi gerektirmediği için anahtar kontrolünden önce yönlendiriliyor:

```python
def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if args.command == "report":
            return cmd_report(args, pricing)

        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        return cmd_run(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
```

`summarize` içindeki `dict.fromkeys(...)` kalıbı model anahtarlarını ilk görüldükleri sırayla ve tekrarsız listeler. Puanlanmamış görevler (`puan` değeri `None`) ortalamaya girmez; sıfır gibi sayılsalardı ortalamayı haksız yere düşürürlerdi.

**Çalıştır:**

```bash
python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl --monthly-calls 100000
```

**Beklenen çıktı:** Dört satırlık bir tablo: `İlk token`, `Toplam`, `token/sn`, `Çıktı token`, `Maliyet/görev`, `Aylık (100.000 çağrı)` ve `Oto puan` sütunları. Altında dört karar satırı: en hızlı ilk token, en ucuz model, en yüksek otomatik puan ve puan farkı.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl --monthly-calls 100000
Sonuç dosyası: sonuclar/2_gorev_seti.jsonl  |  5 görev, 4 model

Model              İlk token  Toplam  token/sn  Çıktı token  Maliyet/görev  Aylık (100.000 çağrı)  Oto puan
-----------------  ---------  ------  --------  -----------  -------------  ---------------------  --------
Claude Haiku 4.5      514 ms  1,01 s       132           64       $0,00050                 $50,28       %73
Claude Sonnet 5.5     854 ms  1,39 s       153           71        $0,0012                $115,52      %100
Claude Opus 5.5       1,64 s  2,08 s       148           93        $0,0028                $275,28      %100
Claude Fable 5.1      1,06 s  2,27 s        48           72        $0,0058                $582,20      %100

En hızlı ilk token: Claude Haiku 4.5 (514 ms)
En ucuz: Claude Haiku 4.5 ($0,00050/görev)
En yüksek otomatik puan: Claude Sonnet 5.5 (%100)
Otomatik puan farkı (en yüksek − en düşük): 27 puan (fark küçükse kararı kalite değil, hız ve maliyet verdirir)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

**Kontrol noktası:** Aylık sütununda en ucuz ve en pahalı modeli karşılaştır: fark kaç kat? Şimdi `Oto puan` sütununa bak: bu kat farkının karşılığında puan farkı ne kadar? Bu iki soruyu birlikte cevaplayabiliyorsan adımın asıl amacına ulaştın. Çağrı yapılmadığını doğrulamak için komutu üç kez çalıştır; sayılar değişmemeli.

**Bitirdiğinde:** Dosyan [`cozum/adim_5.py`](cozum/adim_5.py) ile aynı işi yapıyor olmalı.

<a id="adim-6"></a>

## Adım 6 — Etiketsiz puanlama

**Ne yapacaksın:** İki komut ekleyeceksin. `show` bir görevin dört çıktısını model adları gizlenmiş ve sırası karıştırılmış olarak A, B, C, D etiketleriyle gösterir. `rate` senin 1–5 puanlarını kaydeder, etiketleri açar ve rapora "Etiketsiz" sütununu ekler.

**Neden:** Ders 1.7 §7'deki akışın altıncı adımı insan değerlendirmesidir; §3'teki trap ise "benchmark sıralaması senin görevin için en iyi model değildir" der. Otomatik kontroller kuralları ölçer, kaliteyi değil: iki özet de "sertifika" kelimesini içerebilir ama biri çok daha iyi yazılmış olabilir. Burada okuyucu sensin. Model adını görmeden puanlamanın nedeni basit: en pahalı modelin çıktısını, pahalı olduğunu bildiğin için daha yüksek puanlamaya eğilimlisin. Etiket gizlenince bu eğilim devreden çıkar.

Dosyanın başındaki import ve sabit bloğunu şu hâliyle değiştir (`random` ve `LABELS` eklendi):

```python
import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"

MODELS_HELP = "Virgülle ayrılmış model anahtarları, ör. haiku-4-5,sonnet-5-5 (varsayılan: hepsi)"

REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok", "context_window", "max_output")

# Görev dosyasında tanınan kontrol türleri. Bilinmeyen bir tür dosya yüklenirken hata verir.
CHECK_KINDS = ("icermeli", "icermeli_biri", "icermemeli", "max_kelime", "json")

# Etiketsiz görünümde model adlarının yerine geçen harfler.
LABELS = "ABCDEFGH"
```

`load_results` fonksiyonunun altına süzme ve karıştırma fonksiyonlarını ekle:

```python
def runs_for_task(records: list[dict], task_name: str) -> list[dict]:
    """Bir görevin başarılı çalıştırma kayıtlarını, model başına ilk tekrarla sınırlı olarak döndürür."""
    runs = [r for r in records if r.get("tur") == "calistirma" and r["gorev"] == task_name and r.get("tekrar", 1) == 1]
    if not runs:
        known = sorted({r["gorev"] for r in records if r.get("tur") == "calistirma"})
        raise ValueError(f"'{task_name}' adında görev yok. Görevler: {', '.join(known)}")
    return runs


def anonymize(runs: list[dict], seed: str) -> list[tuple[str, dict]]:
    """Çalıştırmaları karıştırıp A, B, C... etiketleriyle eşler. Aynı tohum aynı sırayı verir."""
    shuffled = list(runs)
    random.Random(seed).shuffle(shuffled)
    return list(zip(LABELS, shuffled))
```

`fmt_score` fonksiyonunun altına etiketsiz puan biçimlendiricisini ekle:

```python
def fmt_rating(rating: float | None) -> str:
    """Etiketsiz puan: 1–5 ölçeğinde ortalama, ör. 4,3/5."""
    return "-" if rating is None else _tr_number(f"{rating:.1f}") + "/5"
```

`summarize`, `decision_lines` ve `cmd_report` fonksiyonlarını etiketsiz puanı da hesaba katan şu hâlleriyle değiştir:

```python
def summarize(records: list[dict]) -> list[dict]:
    """Çalıştırma kayıtlarını model başına özetler; etiketsiz puanlar varsa ortalamasını ekler."""
    runs = [r for r in records if r.get("tur") == "calistirma"]
    ratings = [r for r in records if r.get("tur") == "puan"]
    summaries = []
    for key in dict.fromkeys(r["model"] for r in runs):
        mine = [r for r in runs if r["model"] == key]
        scored = [r["puan"] for r in mine if r["puan"] is not None]
        rated = [r["puan"] for r in ratings if r["model"] == key]
        speeds = [v for v in (tokens_per_second(r["cikti_token"], r["ilk_token_sn"], r["toplam_sn"]) for r in mine) if v is not None]
        summaries.append({
            "model": key, "model_adi": mine[0]["model_adi"], "calistirma": len(mine),
            "ilk_token_sn": mean([r["ilk_token_sn"] for r in mine]),
            "toplam_sn": mean([r["toplam_sn"] for r in mine]),
            "token_sn": mean(speeds) if speeds else None,
            "cikti_token": mean([r["cikti_token"] for r in mine]),
            "maliyet": mean([r["maliyet"] for r in mine]),
            "kesilen": sum(1 for r in mine if r["kesildi"]),
            "puan": mean(scored) if scored else None,
            "etiketsiz_puan": mean(rated) if rated else None,
        })
    return summaries


def decision_lines(summaries: list[dict]) -> list[str]:
    """Özet tablodan karar cümleleri üretir: en hızlı, en ucuz, en yüksek puan ve puan başına maliyet."""
    fastest = min(summaries, key=lambda s: s["ilk_token_sn"])
    cheapest = min(summaries, key=lambda s: s["maliyet"])
    lines = [
        f"En hızlı ilk token: {fastest['model_adi']} ({fmt_sec(fastest['ilk_token_sn'])})",
        f"En ucuz: {cheapest['model_adi']} ({fmt_usd(cheapest['maliyet'])}/görev)",
    ]
    scored = [s for s in summaries if s["puan"] is not None]
    if scored:
        best = max(scored, key=lambda s: s["puan"])
        lines.append(f"En yüksek otomatik puan: {best['model_adi']} ({fmt_score(best['puan'])})")
        spread = max(s["puan"] for s in scored) - min(s["puan"] for s in scored)
        lines.append(f"Otomatik puan farkı (en yüksek − en düşük): {fmt_int(round(spread))} puan "
                     f"(fark küçükse kararı kalite değil, hız ve maliyet verdirir)")
    rated = [s for s in summaries if s["etiketsiz_puan"] is not None]
    if rated:
        best = max(rated, key=lambda s: s["etiketsiz_puan"])
        lines.append(f"En yüksek etiketsiz puan: {best['model_adi']} ({fmt_rating(best['etiketsiz_puan'])})")
    return lines


def cmd_report(args, pricing: dict) -> int:
    records = load_results(args.results)
    summaries = summarize(records)
    rated = any(s["etiketsiz_puan"] is not None for s in summaries)

    task_count = len({r["gorev"] for r in records if r.get("tur") == "calistirma"})
    print(f"Sonuç dosyası: {args.results}  |  {task_count} görev, {len(summaries)} model")
    print()

    headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet/görev"]
    if args.monthly_calls:
        headers.append(f"Aylık ({fmt_int(args.monthly_calls)} çağrı)")
    headers.append("Oto puan")
    if rated:
        headers.append("Etiketsiz")
    rows = []
    for s in summaries:
        row = [s["model_adi"], fmt_sec(s["ilk_token_sn"]), fmt_sec(s["toplam_sn"]), fmt_speed(s["token_sn"]),
               fmt_int(round(s["cikti_token"])) + (f" ({s['kesilen']} kesildi)" if s["kesilen"] else ""),
               fmt_usd(s["maliyet"])]
        if args.monthly_calls:
            row.append(fmt_usd(s["maliyet"] * args.monthly_calls))
        row.append(fmt_score(s["puan"]))
        if rated:
            row.append(fmt_rating(s["etiketsiz_puan"]))
        rows.append(row)
    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    for line in decision_lines(summaries):
        print(line)
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`cmd_report` fonksiyonundan sonra üç fonksiyon ekle: etiketsiz görünüm, puan ayrıştırıcı ve puanlama komutu:

```python
def cmd_show(args) -> int:
    records = load_results(args.results)
    runs = runs_for_task(records, args.task)
    print(f"Görev: {args.task}  |  {len(runs)} çıktı, model adları gizli. "
          f"Puanlamak için: rate {args.results} {args.task} --scores A=4,B=3,...")
    for label, run in anonymize(runs, f"{args.results}:{args.task}"):
        print()
        print(f"--- {label} ---")
        print(run["yanit"])
    return 0


def parse_scores(scores_csv: str, labels: list[str]) -> dict[str, int]:
    """'A=4,B=3' biçimindeki metni {etiket: puan} sözlüğüne çevirir; eksik ya da geçersiz girdiyi reddeder."""
    scores = {}
    for part in (p.strip() for p in scores_csv.split(",") if p.strip()):
        label, _, value = part.partition("=")
        label = label.strip().upper()
        if label not in labels or not value.strip().isdigit() or not 1 <= int(value) <= 5:
            raise ValueError(f"Geçersiz puan girdisi: '{part}'. Biçim: A=4 (1–5 arası).")
        scores[label] = int(value)
    missing = [label for label in labels if label not in scores]
    if missing:
        raise ValueError(f"Eksik puan: {', '.join(missing)}. Her çıktıya puan ver.")
    return scores


def cmd_rate(args) -> int:
    records = load_results(args.results)
    runs = runs_for_task(records, args.task)
    labeled = anonymize(runs, f"{args.results}:{args.task}")
    labels = [label for label, _ in labeled]

    if args.scores:
        scores = parse_scores(args.scores, labels)
    else:
        answers = []
        for label in labels:
            answers.append(f"{label}={input(f'{label} için puan (1–5): ').strip()}")
        scores = parse_scores(",".join(answers), labels)

    ratings = []
    print(f"Görev: {args.task}  |  etiketler açılıyor")
    print()
    rows = []
    for label, run in labeled:
        rows.append([label, run["model_adi"], f"{scores[label]}/5", fmt_score(run["puan"]), fmt_usd(run["maliyet"])])
        ratings.append({"tur": "puan", "zaman": datetime.now().isoformat(timespec="seconds"),
                        "gorev": args.task, "model": run["model"], "model_adi": run["model_adi"], "puan": scores[label]})
    print_table(["Etiket", "Model", "Etiketsiz puan", "Oto puan", "Maliyet"], rows, right_align={2, 3, 4})
    print()
    save_results(Path(args.results), ratings, append=True)
    print(f"Kaydedildi: {args.results} (+{len(ratings)} puan kaydı). Rapora yansıtmak için: report {args.results}")
    return 0
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
def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if args.command == "report":
            return cmd_report(args, pricing)
        if args.command == "show":
            return cmd_show(args)
        if args.command == "rate":
            return cmd_rate(args)

        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        return cmd_run(args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
```

`anonymize` içindeki `random.Random(seed)` tohumlu bir üreteçtir: aynı tohum her seferinde aynı karışıklığı verir. Tohum dosya adı ile görev adından türetildiği için `show` ve `rate` ayrı çalıştırılsa da aynı eşlemeyi kullanır; A harfi iki komutta da aynı modeli gösterir.

**Çalıştır:** Önce çıktıları etiketsiz gör, puanlarını ver, sonra raporu yenile. Aşağıdaki puanlar örnektir; kendi puanlarını yaz.

```bash
python calisma/modellab.py show sonuclar/2_gorev_seti.jsonl ozet
python calisma/modellab.py rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,C=5,D=3
python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl
```

**Beklenen çıktı:** `show` dört yanıtı `--- A ---` … `--- D ---` başlıklarıyla, model adı olmadan basar. `rate` etiketleri açar: her harfin hangi model olduğu, senin puanın, otomatik puan ve maliyet yan yana; en altta `+4 puan kaydı` notu. `report` tabloya `Etiketsiz` sütununu ve karar satırlarına "En yüksek etiketsiz puan" satırını ekler.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py show sonuclar/2_gorev_seti.jsonl ozet
Görev: ozet  |  4 çıktı, model adları gizli. Puanlamak için: rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,...

--- A ---
9 Ekim 2026'da ödeme servisinin banka entegrasyonunda kullanılan TLS sertifikasının süresi dolduğu için bağlantılar el sıkışma aşamasında reddedildi ve 65 dakika boyunca yaklaşık 1.900 ödeme denemesi etkilendi. Sertifika yenilenerek sorun giderildi; tekrarını önlemek için süre dolmadan 30 gün önce uyarı veren bir izleme kuralı eklendi.

--- B ---
# Olay Raporu Özeti

**Kök Neden:** Ödeme servisinin banka entegrasyonunda kullanılan TLS sertifikasının süresi dolması nedeniyle bağlantı el sıkışması aşamasında başarısız olmuştur.

**Alınan Önlem:** Sertifika süresinin dolmadan 30 gün öncesinden uyaran bir izleme kuralı sisteme eklenmiştir.

--- C ---
9 Ekim 2026'da ödeme servisinin banka entegrasyonunda kullandığı TLS sertifikasının süresi dolduğu için bağlantılar el sıkışma aşamasında reddedildi. Bu nedenle 65 dakika boyunca isteklerin %38'i zaman aşımına uğradı ve yaklaşık 1.900 ödeme denemesi etkilendi. Sertifika yenilenerek sorun giderildi ve önlem olarak süre dolmadan 30 gün önce uyaran bir izleme kuralı eklendi.

--- D ---
9 Ekim 2026'da ödeme servisi isteklerinin %38'i, banka entegrasyonunda kullanılan TLS sertifikasının süresinin dolması nedeniyle 65 dakika boyunca başarısız oldu ve yaklaşık 1.900 ödeme denemesi etkilendi. Sertifika yenilenerek sorun giderildi ve tekrarını önlemek için sertifika süresinin dolmasından 30 gün önce uyaran bir izleme kuralı eklendi.
```

```text
$ python calisma/modellab.py rate sonuclar/2_gorev_seti.jsonl ozet --scores A=4,B=3,C=5,D=3
Görev: ozet  |  etiketler açılıyor

Etiket  Model              Etiketsiz puan  Oto puan   Maliyet
------  -----------------  --------------  --------  --------
A       Claude Sonnet 5.5             4/5      %100   $0,0026
B       Claude Haiku 4.5              3/5      %100  $0,00097
C       Claude Opus 5.5               5/5      %100   $0,0056
D       Claude Fable 5.1              3/5      %100    $0,013

Kaydedildi: sonuclar/2_gorev_seti.jsonl (+4 puan kaydı). Rapora yansıtmak için: report sonuclar/2_gorev_seti.jsonl
```

```text
$ python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl
Sonuç dosyası: sonuclar/2_gorev_seti.jsonl  |  5 görev, 4 model

Model              İlk token  Toplam  token/sn  Çıktı token  Maliyet/görev  Oto puan  Etiketsiz
-----------------  ---------  ------  --------  -----------  -------------  --------  ---------
Claude Haiku 4.5      514 ms  1,01 s       132           64       $0,00050       %73      3,0/5
Claude Sonnet 5.5     854 ms  1,39 s       153           71        $0,0012      %100      4,0/5
Claude Opus 5.5       1,64 s  2,08 s       148           93        $0,0028      %100      5,0/5
Claude Fable 5.1      1,06 s  2,27 s        48           72        $0,0058      %100      3,0/5

En hızlı ilk token: Claude Haiku 4.5 (514 ms)
En ucuz: Claude Haiku 4.5 ($0,00050/görev)
En yüksek otomatik puan: Claude Sonnet 5.5 (%100)
Otomatik puan farkı (en yüksek − en düşük): 27 puan (fark küçükse kararı kalite değil, hız ve maliyet verdirir)
En yüksek etiketsiz puan: Claude Opus 5.5 (5,0/5)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
def cmd_run(args, client, pricing: dict) -> int:
    tasks = load_tasks(args.tasks)
    models = select_models(pricing, args.models)
    out_path = Path(args.out) if args.out else default_results_path(args.tasks)

    print(f"Görev seti: {tasks['ad']} ({len(tasks['gorevler'])} görev)  |  {len(models)} model  |  "
          f"max_tokens={fmt_int(args.max_tokens)}  |  tekrar={args.repeat}")
    print()

    records, failures = [], []
    for task in tasks["gorevler"]:
        print(f"[{task['ad']}]" + (f" (tier {task['tier']})" if task.get("tier") else ""))
        messages = build_messages(task["prompt"])
        headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet", "Puan"]
        rows = []
        for model in models:
            for repeat in range(1, args.repeat + 1):
                result, error = try_call(client, model, messages, args.max_tokens, task.get("system"))
                if error:
                    rows.append([model["name"]] + ["-"] * (len(headers) - 2) + [f"erişilemedi ({error})"])
                    failures.append(f"{task['ad']}/{model['key']}")
                    continue
                cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
                score, failed = check_output(result["text"], task.get("kontroller", {}))
                cut = result["stop_reason"] == "max_tokens"
                records.append({
                    "tur": "calistirma", "zaman": datetime.now().isoformat(timespec="seconds"),
                    "gorev": task["ad"], "tier": task.get("tier"), "model": model["key"], "model_adi": model["name"],
                    "tekrar": repeat, "ilk_token_sn": round(result["ttft"], 3), "toplam_sn": round(result["total"], 3),
                    "girdi_token": result["input_tokens"], "cikti_token": result["output_tokens"],
                    "kesildi": cut, "maliyet": cost, "puan": score, "basarisiz": failed, "yanit": result["text"],
                })
                name = model["name"] if args.repeat == 1 else f"{model['name']} #{repeat}"
                rows.append([
                    name, fmt_sec(result["ttft"]), fmt_sec(result["total"]),
                    fmt_speed(tokens_per_second(result["output_tokens"], result["ttft"], result["total"])),
                    fmt_int(result["output_tokens"]) + (" (kesildi)" if cut else ""), fmt_usd(cost), fmt_score(score),
                ])
                if args.show_output:
                    print(f"  {model['name']}:\n" + "\n".join("    " + line for line in result["text"].splitlines()))
        print_table(headers, rows, right_align=set(range(1, len(headers))))
        print()

    save_results(out_path, records)
    shown = out_path.relative_to(PROJECT_DIR) if out_path.is_relative_to(PROJECT_DIR) else out_path
    print(f"Kaydedildi: {shown.as_posix()} ({len(records)} kayıt)")
    if failures:
        print(f"Uyarı: {len(failures)} çağrı başarısız oldu: {', '.join(failures)}")
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
```

`summarize` ve `cmd_report` fonksiyonlarını şu hâlleriyle değiştir:

```python
def summarize(records: list[dict]) -> list[dict]:
    """Çalıştırma kayıtlarını model başına özetler; etiketsiz puanlar varsa ortalamasını ekler."""
    runs = [r for r in records if r.get("tur") == "calistirma"]
    ratings = [r for r in records if r.get("tur") == "puan"]
    summaries = []
    for key in dict.fromkeys(r["model"] for r in runs):
        mine = [r for r in runs if r["model"] == key]
        scored = [r["puan"] for r in mine if r["puan"] is not None]
        rated = [r["puan"] for r in ratings if r["model"] == key]
        totals = [r["toplam_sn"] for r in mine]
        speeds = [v for v in (tokens_per_second(r["cikti_token"], r["ilk_token_sn"], r["toplam_sn"]) for r in mine) if v is not None]
        summaries.append({
            "model": key, "model_adi": mine[0]["model_adi"], "calistirma": len(mine),
            "tekrar": max(r.get("tekrar", 1) for r in mine),
            "ilk_token_sn": mean([r["ilk_token_sn"] for r in mine]),
            "toplam_sn": mean(totals), "toplam_min_sn": min(totals), "toplam_max_sn": max(totals),
            "token_sn": mean(speeds) if speeds else None,
            "cikti_token": mean([r["cikti_token"] for r in mine]),
            "maliyet": mean([r["maliyet"] for r in mine]),
            "kesilen": sum(1 for r in mine if r["kesildi"]),
            "puan": mean(scored) if scored else None,
            "etiketsiz_puan": mean(rated) if rated else None,
        })
    return summaries


def cmd_report(args, pricing: dict) -> int:
    records = load_results(args.results)
    summaries = summarize(records)
    repeated = any(s["tekrar"] > 1 for s in summaries)
    rated = any(s["etiketsiz_puan"] is not None for s in summaries)

    task_count = len({r["gorev"] for r in records if r.get("tur") == "calistirma"})
    print(f"Sonuç dosyası: {args.results}  |  {task_count} görev, {len(summaries)} model"
          + (f", görev başına {summaries[0]['tekrar']} tekrar" if repeated else ""))
    print()

    headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet/görev"]
    if args.monthly_calls:
        headers.append(f"Aylık ({fmt_int(args.monthly_calls)} çağrı)")
    headers.append("Oto puan")
    if rated:
        headers.append("Etiketsiz")
    rows = []
    for s in summaries:
        row = [s["model_adi"], fmt_sec(s["ilk_token_sn"]), fmt_sec(s["toplam_sn"]), fmt_speed(s["token_sn"]),
               fmt_int(round(s["cikti_token"])) + (f" ({s['kesilen']} kesildi)" if s["kesilen"] else ""),
               fmt_usd(s["maliyet"])]
        if args.monthly_calls:
            row.append(fmt_usd(s["maliyet"] * args.monthly_calls))
        row.append(fmt_score(s["puan"]))
        if rated:
            row.append(fmt_rating(s["etiketsiz_puan"]))
        rows.append(row)
    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    if repeated:
        print("Toplam süre aralığı (min–maks): " + "  |  ".join(
            f"{s['model_adi']} {fmt_sec(s['toplam_min_sn'])}–{fmt_sec(s['toplam_max_sn'])}" for s in summaries))
        print()
    for line in decision_lines(summaries):
        print(line)
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")
    return 0
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py run gorevler/1_tek_prompt.yaml --repeat 3 --out sonuclar/tekrar.jsonl
Görev seti: Tek prompt (1 görev)  |  4 model  |  max_tokens=300  |  tekrar=3

[mikroservis] (tier 2)
Model                 İlk token  Toplam  token/sn    Çıktı token   Maliyet  Puan
--------------------  ---------  ------  --------  -------------  --------  ----
Claude Haiku 4.5 #1      713 ms  2,09 s       102            141  $0,00077  %100
Claude Haiku 4.5 #2      606 ms  2,09 s       105            156  $0,00085  %100
Claude Haiku 4.5 #3      612 ms  2,50 s        95            180  $0,00097  %100
Claude Sonnet 5.5 #1     659 ms  3,47 s       107  300 (kesildi)   $0,0032  %100
Claude Sonnet 5.5 #2     616 ms  2,72 s       109            230   $0,0025  %100
Claude Sonnet 5.5 #3     638 ms  3,03 s       125  300 (kesildi)   $0,0032  %100
Claude Opus 5.5 #1       1,18 s  4,13 s        95            281   $0,0060  %100
Claude Opus 5.5 #2       1,07 s  3,93 s        90            258   $0,0055  %100
Claude Opus 5.5 #3       1,09 s  3,52 s       103            251   $0,0054  %100
Claude Fable 5.1 #1      560 ms  4,37 s        69            265    $0,014  %100
Claude Fable 5.1 #2      567 ms  3,68 s        78            244    $0,013  %100
Claude Fable 5.1 #3      571 ms  3,48 s        77            225    $0,012  %100

Kaydedildi: sonuclar/tekrar.jsonl (12 kayıt)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

```text
$ python calisma/modellab.py report sonuclar/tekrar.jsonl
Sonuç dosyası: sonuclar/tekrar.jsonl  |  1 görev, 4 model, görev başına 3 tekrar

Model              İlk token  Toplam  token/sn      Çıktı token  Maliyet/görev  Oto puan
-----------------  ---------  ------  --------  ---------------  -------------  --------
Claude Haiku 4.5      644 ms  2,23 s       101              159       $0,00086      %100
Claude Sonnet 5.5     638 ms  3,07 s       114  277 (2 kesildi)        $0,0029      %100
Claude Opus 5.5       1,11 s  3,86 s        96              263        $0,0056      %100
Claude Fable 5.1      566 ms  3,84 s        75              245         $0,013      %100

Toplam süre aralığı (min–maks): Claude Haiku 4.5 2,09 s–2,50 s  |  Claude Sonnet 5.5 2,72 s–3,47 s  |  Claude Opus 5.5 3,52 s–4,13 s  |  Claude Fable 5.1 3,48 s–4,38 s

En hızlı ilk token: Claude Fable 5.1 (566 ms)
En ucuz: Claude Haiku 4.5 ($0,00086/görev)
En yüksek otomatik puan: Claude Haiku 4.5 (%100)
Otomatik puan farkı (en yüksek − en düşük): 0 puan (fark küçükse kararı kalite değil, hız ve maliyet verdirir)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
```

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
def write_model_card(path: Path, results_path: str, summaries: list[dict]) -> None:
    """Karar kaydını Markdown olarak yazar (Ders 1.7 §7, adım 7). Gerekçe satırlarını öğrenci doldurur."""
    lines = [
        "# Model kartı",
        "",
        f"- Tarih: {datetime.now().date().isoformat()}",
        f"- Sonuç dosyası: `{results_path}`",
        "",
        "| Model | İlk token | Toplam | Maliyet/görev | Oto puan | Etiketsiz |",
        "|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(f"| {s['model_adi']} | {fmt_sec(s['ilk_token_sn'])} | {fmt_sec(s['toplam_sn'])} | "
                     f"{fmt_usd(s['maliyet'])} | {fmt_score(s['puan'])} | {fmt_rating(s['etiketsiz_puan'])} |")
    lines += ["", "## Ölçümün söyledikleri", ""]
    lines += [f"- {line}" for line in decision_lines(summaries)]
    lines += [
        "",
        "## Karar",
        "",
        "- Seçilen model: _(yaz)_",
        "- Gerekçe (kalite, gecikme, maliyet ekseninde): _(yaz)_",
        "- Yedek (fallback) model: _(yaz)_",
        "- Yeniden değerlendirme tarihi: _(yaz)_",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
```

`cmd_report` fonksiyonunu, seçenek verildiğinde kartı yazan şu hâliyle değiştir:

```python
def cmd_report(args, pricing: dict) -> int:
    records = load_results(args.results)
    summaries = summarize(records)
    repeated = any(s["tekrar"] > 1 for s in summaries)
    rated = any(s["etiketsiz_puan"] is not None for s in summaries)

    task_count = len({r["gorev"] for r in records if r.get("tur") == "calistirma"})
    print(f"Sonuç dosyası: {args.results}  |  {task_count} görev, {len(summaries)} model"
          + (f", görev başına {summaries[0]['tekrar']} tekrar" if repeated else ""))
    print()

    headers = ["Model", "İlk token", "Toplam", "token/sn", "Çıktı token", "Maliyet/görev"]
    if args.monthly_calls:
        headers.append(f"Aylık ({fmt_int(args.monthly_calls)} çağrı)")
    headers.append("Oto puan")
    if rated:
        headers.append("Etiketsiz")
    rows = []
    for s in summaries:
        row = [s["model_adi"], fmt_sec(s["ilk_token_sn"]), fmt_sec(s["toplam_sn"]), fmt_speed(s["token_sn"]),
               fmt_int(round(s["cikti_token"])) + (f" ({s['kesilen']} kesildi)" if s["kesilen"] else ""),
               fmt_usd(s["maliyet"])]
        if args.monthly_calls:
            row.append(fmt_usd(s["maliyet"] * args.monthly_calls))
        row.append(fmt_score(s["puan"]))
        if rated:
            row.append(fmt_rating(s["etiketsiz_puan"]))
        rows.append(row)
    print_table(headers, rows, right_align=set(range(1, len(headers))))
    print()

    if repeated:
        print("Toplam süre aralığı (min–maks): " + "  |  ".join(
            f"{s['model_adi']} {fmt_sec(s['toplam_min_sn'])}–{fmt_sec(s['toplam_max_sn'])}" for s in summaries))
        print()
    for line in decision_lines(summaries):
        print(line)
    print(f"Fiyat kaynağı: pricing.yaml (güncelleme: {pricing['updated']})")

    if args.model_card:
        write_model_card(Path(args.model_card), args.results, summaries)
        print(f"Model kartı yazıldı: {args.model_card}")
    return 0
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/modellab.py report sonuclar/2_gorev_seti.jsonl --model-card sonuclar/model-karti.md
Sonuç dosyası: sonuclar/2_gorev_seti.jsonl  |  5 görev, 4 model

Model              İlk token  Toplam  token/sn  Çıktı token  Maliyet/görev  Oto puan  Etiketsiz
-----------------  ---------  ------  --------  -----------  -------------  --------  ---------
Claude Haiku 4.5      514 ms  1,01 s       132           64       $0,00050       %73      3,0/5
Claude Sonnet 5.5     854 ms  1,39 s       153           71        $0,0012      %100      4,0/5
Claude Opus 5.5       1,64 s  2,08 s       148           93        $0,0028      %100      5,0/5
Claude Fable 5.1      1,06 s  2,27 s        48           72        $0,0058      %100      3,0/5

En hızlı ilk token: Claude Haiku 4.5 (514 ms)
En ucuz: Claude Haiku 4.5 ($0,00050/görev)
En yüksek otomatik puan: Claude Sonnet 5.5 (%100)
Otomatik puan farkı (en yüksek − en düşük): 27 puan (fark küçükse kararı kalite değil, hız ve maliyet verdirir)
En yüksek etiketsiz puan: Claude Opus 5.5 (5,0/5)
Fiyat kaynağı: pricing.yaml (güncelleme: 2026-10-05)
Model kartı yazıldı: sonuclar/model-karti.md
```

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
