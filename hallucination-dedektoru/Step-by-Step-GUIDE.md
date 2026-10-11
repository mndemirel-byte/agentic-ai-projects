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
"""Hallucination dedektörü — Adım 1: kaynağa dayalı yanıt.

answer komutu bir kaynak doküman ve bir soru alır, üretici modelden yanıtı ister, yanıtı dosyaya yazar
ve çağrının token sayılarıyla maliyetini gösterir.

Kullanım:
    python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
"""

import argparse
import math
import os
import sys
import textwrap
from pathlib import Path

import anthropic
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = PROJECT_DIR / "pricing.yaml"
DEFAULT_RESULTS_DIR = PROJECT_DIR / "sonuclar"
REQUIRED_MODEL_FIELDS = ("key", "name", "id", "input_per_mtok", "output_per_mtok")

# Her çağrı için çıktı sınırı. Yanıt kısa tutulur; iddia listesi ve doğrulama JSON'u daha uzun olabilir.
MAX_TOKENS = {"answer": 600, "extract": 800, "verify": 1500}


# ---------------------------------------------------------------------------
# Prompt'lar
# ---------------------------------------------------------------------------

GENERATE_SYSTEM = (
    "Sen bir teknik destek asistanısın. Kullanıcının sorusunu, sana verilen dokümana dayanarak Türkçe "
    "cevapla. Cevabın kısa ve net olsun; en fazla bir paragraf yaz, liste kullanma."
)


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_pricing(path: Path) -> dict:
    """pricing.yaml dosyasını okur; zorunlu alanları ve rol atamalarını doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for model in data["models"]:
        missing = [field for field in REQUIRED_MODEL_FIELDS if field not in model]
        if missing:
            raise ValueError(f"pricing.yaml: '{model.get('key', '?')}' modelinde eksik alan: {', '.join(missing)}")
    for role in ("uretici", "dogrulayici"):
        if role not in data.get("roller", {}):
            raise ValueError(f"pricing.yaml: 'roller' altında '{role}' tanımlı değil.")
    return data


def select_model(pricing: dict, key: str | None, role: str) -> dict:
    """Komut satırında verilen anahtarı, verilmediyse pricing.yaml'daki rol atamasını kullanarak modeli seçer."""
    key = key or pricing["roller"][role]
    by_key = {m["key"]: m for m in pricing["models"]}
    if key not in by_key:
        raise ValueError(f"Bilinmeyen model anahtarı: '{key}'. Geçerli anahtarlar: {', '.join(by_key)}")
    return by_key[key]


def read_text(path: str) -> str:
    """Bir metin dosyasını UTF-8 olarak okur; boş dosyayı reddeder."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path}: dosya boş.")
    return text


def read_question(value: str) -> str:
    """Soru bir dosya yoluysa dosyadan okunur; değilse metnin kendisi sorudur."""
    if Path(value).is_file():
        return read_text(value)
    return value.strip()


# ---------------------------------------------------------------------------
# API çağrıları
# ---------------------------------------------------------------------------

def call_model(client, model: dict, prompt: str, max_tokens: int, system: str | None = None) -> dict:
    """Tek bir non-streaming çağrı yapar; metni, token sayılarını ve durma nedenini döndürür.

    Modelin `cagri_ayarlari` sözlüğü (pricing.yaml) isteğe olduğu gibi eklenir; kod ayarların
    içeriğini bilmez. Yanıt bütün olarak işleneceği için streaming gerekmez (Ders 1.4 §4.4).
    """
    kwargs = {"model": model["id"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    kwargs.update(model.get("cagri_ayarlari") or {})
    message = client.messages.create(**kwargs)
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    return {
        "text": text.strip(),
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "stop_reason": message.stop_reason,
    }


def generate_answer(client, model: dict, source: str, question: str) -> dict:
    """Üretici modelden kaynağa dayalı yanıt alır."""
    prompt = f"DOKÜMAN:\n\"\"\"\n{source}\n\"\"\"\n\nSORU: {question}"
    return call_model(client, model, prompt, MAX_TOKENS["answer"], GENERATE_SYSTEM)


# ---------------------------------------------------------------------------
# Hesaplamalar
# ---------------------------------------------------------------------------

def estimate_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """Tek çağrının USD maliyeti. Fiyatlar 1M token başına (Ders 1.4 §6.2)."""
    return (input_tokens * model["input_per_mtok"] + output_tokens * model["output_per_mtok"]) / 1_000_000


# ---------------------------------------------------------------------------
# Biçimlendirme (Türkçe sayı yazımı: binlik ayırıcı nokta, ondalık virgül)
# ---------------------------------------------------------------------------

def _tr_number(formatted: str) -> str:
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_int(n: int) -> str:
    return _tr_number(f"{n:,}")


def fmt_usd(x: float) -> str:
    if x == 0:
        return "$0"
    # 1 doların altındaki tutarlarda ilk anlamlı basamaktan sonra bir basamak daha göster: 0,0035 → $0,0035
    decimals = 2 if x >= 1 else min(8, -math.floor(math.log10(x)) + 1)
    return "$" + _tr_number(f"{x:,.{decimals}f}")


def fmt_usage(result: dict, model: dict) -> str:
    """Bir çağrının özet satırı: model, token sayıları, maliyet ve durma nedeni."""
    cost = estimate_cost(model, result["input_tokens"], result["output_tokens"])
    cut = "  |  UYARI: yanıt max_tokens sınırında kesildi" if result["stop_reason"] == "max_tokens" else ""
    return (f"{model['name']}  |  girdi {fmt_int(result['input_tokens'])} token, çıktı "
            f"{fmt_int(result['output_tokens'])} token  |  {fmt_usd(cost)}{cut}")


def wrap_text(text: str, width: int = 100) -> str:
    """Uzun bir paragrafı terminalde okunur satırlara böler; dosyaya yazılan metin değişmez."""
    return "\n".join(textwrap.fill(p, width) for p in text.splitlines() if p.strip())


# ---------------------------------------------------------------------------
# Kayıt (JSONL: her satır bir zincir çalıştırması)
# ---------------------------------------------------------------------------

def answer_path(question_path: str) -> Path:
    stem = Path(question_path).stem if Path(question_path).is_file() else "yanit"
    return DEFAULT_RESULTS_DIR / f"{stem}.md"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def shown(path: Path) -> str:
    """Yolu proje klasörüne göre, ters bölü kullanmadan yazar."""
    return (path.relative_to(PROJECT_DIR) if path.is_relative_to(PROJECT_DIR) else path).as_posix()


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------

def cmd_answer(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.generator, "uretici")
    source, question = read_text(args.source), read_question(args.question)
    result = generate_answer(client, model, source, question)
    out = Path(args.out) if args.out else answer_path(args.question)
    write_text(out, result["text"])
    print(f"Soru: {question}")
    print()
    print(wrap_text(result["text"]))
    print()
    print(fmt_usage(result, model))
    print(f"Yanıt kaydedildi: {shown(out)}")
    return 0


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedektor", description="LLM yanıtını iddialara ayır, kaynağa karşı doğrula, risk skoruna göre yönlendir.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat ve model dosyası (varsayılan: pricing.yaml)")
    parser.add_argument("--generator", help="Üretici model anahtarı (varsayılan: pricing.yaml > roller > uretici)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_answer = sub.add_parser("answer", help="Kaynağa dayalı yanıt üret ve dosyaya yaz (ücretli)")
    p_answer.add_argument("source", help="Kaynak doküman (Markdown ya da düz metin)")
    p_answer.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_answer.add_argument("--out", help="Yanıt dosyası (varsayılan: sonuclar/<soru dosyası adı>.md)")
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
        commands = {"answer": cmd_answer}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

Kodda dikkat etmeniz gereken üç nokta var. `call_model` programın API ile konuşan tek fonksiyonudur: `kwargs` sözlüğünü kurar, modelin `cagri_ayarlari` sözlüğünü `update` ile ekler ve yanıtın `content` dizisindeki `text` bloklarını birleştirir; `usage` ve `stop_reason` alanlarını da döndürür. `generate_answer` dokümanı ve soruyu tek bir kullanıcı mesajında birleştirir; davranış çerçevesi `GENERATE_SYSTEM` ile `system` alanından gider (Ders 1.4 §1). `main` fonksiyonundaki `client=None` parametresi testlerin sahte bir istemci vermesine izin verir; gerçek kullanımda bu değer boş gelir ve gerçek istemci kurulur.

**Çalıştırın:**

```bash
python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
```

**Beklenen çıktı:** İlk satırda soru, ardından modelin bir paragraflık yanıtı, altında model adı, girdi ve çıktı token sayıları ile maliyeti taşıyan tek bir satır ve `Yanıt kaydedildi: sonuclar/01_iptal.md` satırı. Girdi token sayısı dokümanın uzunluğunu yansıtır; çıktı birkaç yüz token'ı geçmez.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py answer kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt
Soru: Oluşturduğum bir gönderiyi nasıl iptal ederim? Hangi durumda iptal edemem ve o zaman API ne döner?

Gönderiyi iptal etmek için `DELETE /v3/gonderiler/{takip_no}` isteği gönderebilirsiniz. İptal
yalnızca gönderi `olusturuldu` durumundayken mümkündür; kurye gönderiyi topladıktan sonra (yani
durum `olusturuldu` dışına çıktığında) iptal edemezsiniz ve API `409 Conflict` döner. Bu durumda
iptal için müşteri hizmetleriyle iletişime geçmeniz gerekir.

Claude Sonnet 5.5  |  girdi 1.250 token, çıktı 183 token  |  $0,0043
Yanıt kaydedildi: sonuclar/01_iptal.md
```

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
EXTRACT_PROMPT = """<yanit> etiketleri arasındaki metin, bir teknik destek asistanının bir dokümana dayanarak \
verdiği yanıttır. Bu yanıtı doğrulanabilir atomik iddialara ayır.

Kurallar:
- Her iddia tek bir olgu içersin ve tek başına anlaşılsın (zamir yerine adı yaz).
- Yanıttaki her olgusal ifadeyi bir iddia yap; görüş, öneri ve nezaket cümlelerini atla.
- Yanıt "dokümanda belirtilmiyor" gibi bir boşluğu kabul eden cümleler içerebilir; bunları da iddia olarak yaz \
(ör. "Doküman imzanın geçerlilik süresini belirtmez.").
- Yanıtın içeriğini yorumlama, değerlendirme ya da düzeltme; görevin yalnızca onu iddialara bölmek.
- En fazla 10 iddia çıkar; iddiaları yanıttaki sırayla yaz.
- Yalnızca şu biçimde JSON döndür, başka hiçbir şey yazma:
{"claims": ["iddia 1", "iddia 2"]}

<yanit>
{answer}
</yanit>"""
```

`generate_answer` fonksiyonunun altına iddia çıkarıcıyı ekleyin:

```python
def extract_claims(client, model: dict, answer: str) -> tuple[list[str], dict]:
    """Zincirin 1. aşaması: yanıtı atomik iddialara ayırır. JSON çözülemezse hata verir."""
    result = call_model(client, model, EXTRACT_PROMPT.replace("{answer}", answer), MAX_TOKENS["extract"])
    parsed = _parse_json(result["text"])
    claims = parsed.get("claims") if isinstance(parsed, dict) else None
    if not isinstance(claims, list) or not claims or not all(isinstance(c, str) and c.strip() for c in claims):
        raise ValueError("İddia çıkarma: model geçerli bir {\"claims\": [...]} JSON'u döndürmedi. Yanıt: "
                         + result["text"][:120].replace("\n", " "))
    return [c.strip() for c in claims], result
```

`estimate_cost` fonksiyonunun altına JSON çözücüyü ekleyin:

```python
def _parse_json(text: str):
    """Model çıktısındaki JSON'u çözer; kod bloğu çitlerini (```json ... ```) ve JSON'un çevresindeki metni atar.

    Çözülemezse None döner. Önce metnin tamamı, sonra ilk '{' ile son '}' arasındaki parça denenir;
    böylece "İşte iddialar:" gibi bir giriş cümlesi ayrıştırmayı bozmaz.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned)
    candidates = [cleaned]
    if "{" in cleaned and "}" in cleaned:
        candidates.append(cleaned[cleaned.find("{"): cleaned.rfind("}") + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None
```

`answer_path` fonksiyonunun altına iddia dosyasının yolunu üreten yardımcıyı ekleyin:

```python
def claims_path(answer_file: str) -> Path:
    return DEFAULT_RESULTS_DIR / f"{Path(answer_file).stem}.iddialar.json"
```

`cmd_answer` fonksiyonunun altına yeni komutu ekleyin:

```python
def cmd_extract(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    claims, result = extract_claims(client, model, read_text(args.answer))
    out = Path(args.out) if args.out else claims_path(args.answer)
    write_text(out, json.dumps({"claims": claims}, ensure_ascii=False, indent=2))
    print(f"{len(claims)} iddia çıkarıldı:")
    for i, claim in enumerate(claims, start=1):
        print(f"  {i}. {claim}")
    print()
    print(fmt_usage(result, model))
    print(f"İddialar kaydedildi: {shown(out)}")
    return 0
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştirin. Parser'a `--verifier` seçeneği ve `extract` komutu eklendi; `main` komutları bir sözlükten seçiyor:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedektor", description="LLM yanıtını iddialara ayır, kaynağa karşı doğrula, risk skoruna göre yönlendir.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat ve model dosyası (varsayılan: pricing.yaml)")
    parser.add_argument("--generator", help="Üretici model anahtarı (varsayılan: pricing.yaml > roller > uretici)")
    parser.add_argument("--verifier", help="Doğrulayıcı model anahtarı (varsayılan: pricing.yaml > roller > dogrulayici)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_answer = sub.add_parser("answer", help="Kaynağa dayalı yanıt üret ve dosyaya yaz (ücretli)")
    p_answer.add_argument("source", help="Kaynak doküman (Markdown ya da düz metin)")
    p_answer.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_answer.add_argument("--out", help="Yanıt dosyası (varsayılan: sonuclar/<soru dosyası adı>.md)")

    p_extract = sub.add_parser("extract", help="Yanıtı atomik iddialara ayır ve JSON'a yaz (ücretli)")
    p_extract.add_argument("answer", help="answer komutunun yazdığı yanıt dosyası")
    p_extract.add_argument("--out", help="İddia dosyası (varsayılan: sonuclar/<yanıt dosyası adı>.iddialar.json)")
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
        commands = {"answer": cmd_answer, "extract": cmd_extract}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2
```

`EXTRACT_PROMPT` içindeki kuralları okuyun: her iddia tek olgu, zamir yerine ad, en fazla on iddia. Yanıt `<yanit>` etiketleri arasına konur ve prompt yanıtın ne olduğunu açıkça söyler; bu ayrıntı deneyimden geliyor: yanıt "dokümanda belirtilmiyor" gibi bir cümle içerdiğinde, ne olduğu söylenmemiş bir metni alan doğrulayıcı onu iddialara bölmek yerine yorumlamaya kalkabiliyor ve JSON yerine açıklama döndürüyor. "Yorumlama, değerlendirme, düzeltme" kuralı da aynı nedenle var. Bu kurallar doğrulamanın kalitesini belirler; "bu" ya da "o" ile başlayan bir iddia kaynağa karşı tek başına kontrol edilemez. Prompt'taki `{answer}` yer tutucusu `str.replace` ile dolduruluyor, f-string ile değil; çünkü prompt'un kendisi küme parantezi içeren JSON örneği taşıyor.

**Çalıştırın:**

```bash
python calisma/dedektor.py extract sonuclar/01_iptal.md
```

**Beklenen çıktı:** `N iddia çıkarıldı:` başlığı altında numaralı iddialar, altında doğrulayıcı modelin token ve maliyet satırı ve `İddialar kaydedildi: sonuclar/01_iptal.iddialar.json` satırı. İddia sayısı yanıttaki olgu sayısına yakındır; her iddia yanıttaki bir cümleyi ya da cümle parçasını kendi başına anlaşılır hâle getirmiştir.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py extract sonuclar/01_iptal.md
6 iddia çıkarıldı:
  1. Gönderiyi iptal etmek için `DELETE /v3/gonderiler/{takip_no}` isteği gönderilebilir.
  2. Gönderi iptali yalnızca gönderi `olusturuldu` durumundayken mümkündür.
  3. Kurye gönderiyi topladıktan sonra gönderi iptal edilemez.
  4. Gönderi durumu `olusturuldu` dışına çıktığında iptal edilemez.
  5. Gönderi iptal edilemediğinde API `409 Conflict` döner.
  6. Gönderi iptal edilemediğinde iptal için müşteri hizmetleriyle iletişime geçilmesi gerekir.

Claude Haiku 5.5  |  girdi 612 token, çıktı 239 token  |  $0,00018
İddialar kaydedildi: sonuclar/01_iptal.iddialar.json
```

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
# Doğrulayıcının döndürdüğü karar anahtarları ve ekrandaki Türkçe etiketleri.
VERDICT_LABELS = {"supported": "DESTEKLİ", "unsupported": "DESTEKSİZ", "contradicted": "ÇELİŞİYOR", "suspect": "ŞÜPHELİ"}
```

`EXTRACT_PROMPT` tanımının altına doğrulama prompt'unu ekleyin:

```python
VERIFY_PROMPT = """Aşağıdaki iddiaların her birini yalnızca KAYNAK dokümana göre değerlendir. Kendi bilgini kullanma; \
kaynakta olmayan bir bilgi doğru görünse bile "unsupported" say.

Her iddia için:
- verdict: "supported" (kaynak açıkça söylüyor ya da kaynaktaki bir ifadenin doğrudan sonucu), "contradicted" \
(kaynak aksini söylüyor) ya da "unsupported" (kaynakta bu konuda bilgi yok ya da yetersiz).
- evidence: kararı dayandırdığın cümle ya da cümle parçası, KAYNAKTAN BİREBİR kopyalanmış olarak. \
"unsupported" için boş bırak.
- note: tek cümlelik gerekçe.

Yalnızca şu biçimde JSON döndür, başka hiçbir şey yazma:
{"results": [{"id": 1, "verdict": "supported", "evidence": "...", "note": "..."}]}

KAYNAK:
\"\"\"
{source}
\"\"\"

İDDİALAR:
{claims}"""
```

`read_question` fonksiyonunun altına iddia dosyasını okuyan fonksiyonu ekleyin:

```python
def load_claims(path: str) -> list[str]:
    """extract komutunun yazdığı iddia dosyasını okur."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    claims = data.get("claims") if isinstance(data, dict) else None
    if not claims or not all(isinstance(c, str) and c.strip() for c in claims):
        raise ValueError(f"{path}: 'claims' listesi boş ya da hatalı. Önce 'extract' komutunu çalıştır.")
    return claims
```

`extract_claims` fonksiyonunun altına doğrulayıcıyı ekleyin:

```python
def verify_claims(client, model: dict, source: str, claims: list[str]) -> tuple[list[dict], dict]:
    """Zincirin 2. aşamasının LLM yarısı: her iddiayı kaynağa karşı değerlendirir."""
    numbered = "\n".join(f"{i}. {claim}" for i, claim in enumerate(claims, start=1))
    prompt = VERIFY_PROMPT.replace("{source}", source).replace("{claims}", numbered)
    result = call_model(client, model, prompt, MAX_TOKENS["verify"])
    parsed = _parse_json(result["text"])
    rows = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) != len(claims):
        raise ValueError(f"Doğrulama: model {len(claims)} iddia için {len(rows) if isinstance(rows, list) else 0} "
                         "sonuç döndürdü; geçerli JSON bekleniyordu.")
    verdicts = []
    for claim, row in zip(claims, rows):
        verdict = str(row.get("verdict", "")).strip().lower()
        if verdict not in ("supported", "unsupported", "contradicted"):
            raise ValueError(f"Doğrulama: bilinmeyen karar '{verdict}' (iddia: {claim[:60]})")
        verdicts.append({"iddia": claim, "karar": verdict, "kanit": str(row.get("evidence") or "").strip(),
                         "not": str(row.get("note") or "").strip()})
    return verdicts, result
```

`wrap_text` fonksiyonunun altına üç biçimlendirme yardımcısı ekleyin: metin kısaltıcı, hizalı tablo ve karar tablosu:

```python
def shorten(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def print_table(headers: list[str], rows: list[list[str]], right_align: set[int] = frozenset()) -> None:
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


def print_verdicts(verdicts: list[dict]) -> None:
    """Doğrulama tablosu: iddia, karar, kanıt alıntısı ve gerekçe."""
    rows = []
    for i, row in enumerate(verdicts, start=1):
        evidence = shorten(row["kanit"], 40) if row["kanit"] else "-"
        rows.append([str(i), shorten(row["iddia"], 56), VERDICT_LABELS[row["karar"]], evidence, shorten(row["not"], 44)])
    print_table(["#", "İddia", "Karar", "Kanıt", "Not"], rows, right_align={0})
```

`cmd_extract` fonksiyonunun altına yeni komutu ekleyin:

```python
def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    verdicts, result = verify_claims(client, model, read_text(args.source), load_claims(args.claims))
    print_verdicts(verdicts)
    print()
    print(fmt_usage(result, model))
    return 0
```

`build_parser` ve `main` fonksiyonlarını şu hâlleriyle değiştirin:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedektor", description="LLM yanıtını iddialara ayır, kaynağa karşı doğrula, risk skoruna göre yönlendir.")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH), help="Fiyat ve model dosyası (varsayılan: pricing.yaml)")
    parser.add_argument("--generator", help="Üretici model anahtarı (varsayılan: pricing.yaml > roller > uretici)")
    parser.add_argument("--verifier", help="Doğrulayıcı model anahtarı (varsayılan: pricing.yaml > roller > dogrulayici)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_answer = sub.add_parser("answer", help="Kaynağa dayalı yanıt üret ve dosyaya yaz (ücretli)")
    p_answer.add_argument("source", help="Kaynak doküman (Markdown ya da düz metin)")
    p_answer.add_argument("question", help="Soru metni ya da soruyu içeren dosya")
    p_answer.add_argument("--out", help="Yanıt dosyası (varsayılan: sonuclar/<soru dosyası adı>.md)")

    p_extract = sub.add_parser("extract", help="Yanıtı atomik iddialara ayır ve JSON'a yaz (ücretli)")
    p_extract.add_argument("answer", help="answer komutunun yazdığı yanıt dosyası")
    p_extract.add_argument("--out", help="İddia dosyası (varsayılan: sonuclar/<yanıt dosyası adı>.iddialar.json)")

    p_verify = sub.add_parser("verify", help="İddiaları kaynağa karşı doğrula, kanıtı denetle, risk skoru ver (ücretli)")
    p_verify.add_argument("source", help="Kaynak doküman")
    p_verify.add_argument("claims", help="extract komutunun yazdığı iddia dosyası")
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
        commands = {"answer": cmd_answer, "extract": cmd_extract, "verify": cmd_verify}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2
```

`verify_claims` üç şeyi doğrular: dönen `results` listesinin uzunluğu iddia sayısına eşit mi, her kararın değeri tanınan üç değerden biri mi, `evidence` ve `note` metin mi. Model bir iddiayı atlar ya da yeni bir karar adı uydurursa program sessizce devam etmek yerine durur. Ders 1.6'nın mesajını kendi aracınıza uyguluyorsunuz: doğrulayıcı da bir LLM'dir ve onun çıktısı da doğrulanır.

**Çalıştırın:**

```bash
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
```

**Beklenen çıktı:** İddia başına bir satırlık tablo: `#`, `İddia`, `Karar`, `Kanıt` (alıntının başı) ve `Not` sütunları. Kaynağın tamamen cevapladığı bu soruda kararların tamamı ya da tamamına yakını `DESTEKLİ`dir. Referans ölçümde altı iddiadan biri (müşteri hizmetleriyle iletişim) `DESTEKSİZ` çıktı, oysa kaynak bunu açıkça söylüyor: doğrulayıcı da bir modeldir ve yanlış alarm verebilir; bunu Adım 7'de sayacaksınız. Altta doğrulayıcının token ve maliyet satırı vardır; girdi token sayısı dokümanın tamamı gittiği için `extract` adımından belirgin biçimde yüksektir.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json
#  İddia                                                     Karar      Kanıt                                     Not
-  --------------------------------------------------------  ---------  ----------------------------------------  --------------------------------------------
1  Gönderiyi iptal etmek için `DELETE /v3/gonderiler/{taki…  DESTEKLİ   `DELETE /v3/gonderiler/{takip_no}` gönd…  Doküman, bu uç noktanın gönderiyi iptal ett…
2  Gönderi iptali yalnızca gönderi `olusturuldu` durumunda…  DESTEKLİ   İptal yalnızca `olusturuldu` durumundak…  Doküman iptalin yalnızca bu durumda mümkün…
3  Kurye gönderiyi topladıktan sonra gönderi iptal edileme…  DESTEKLİ   kurye gönderiyi topladıktan sonra iptal…  Kurye toplama sonrası iptal isteğinin redde…
4  Gönderi durumu `olusturuldu` dışına çıktığında iptal ed…  DESTEKLİ   İptal yalnızca `olusturuldu` durumundak…  Yalnızca bu durumda iptal mümkün olduğundan…
5  Gönderi iptal edilemediğinde API `409 Conflict` döner.    DESTEKLİ   kurye gönderiyi topladıktan sonra iptal…  Doküman, iptal isteğinin 409 döndüğü durumu…
6  Gönderi iptal edilemediğinde iptal için müşteri hizmetl…  DESTEKSİZ  -                                         Doküman, müşteri hizmetleriyle iletişim ger…

Claude Haiku 5.5  |  girdi 1.700 token, çıktı 799 token  |  $0,00057
```

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
def tr_lower(text: str) -> str:
    """Türkçe'ye uygun küçük harf: I → ı, İ → i (Python'un lower() fonksiyonu bunu bilmez)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def normalize_text(text: str) -> str:
    """Metni karşılaştırma için sadeleştirir: küçük harf, yalnızca harf ve rakam (boşluk ve noktalama atılır)."""
    return re.sub(r"[^0-9a-zçğıöşü]+", "", tr_lower(text))


def evidence_found(evidence: str, source: str) -> bool:
    """Kanıt alıntısı kaynakta gerçekten geçiyor mu? Boş kanıt bulunmamış sayılır."""
    normalized = normalize_text(evidence)
    return bool(normalized) and normalized in normalize_text(source)


def apply_evidence_check(verdicts: list[dict], source: str) -> list[dict]:
    """Zincirin 2. aşamasının deterministik yarısı: kanıtı kaynakta olmayan 'supported' karar 'suspect' olur.

    Modelin kaynak gösterir gibi görünmesi ile gerçekten kaynağa dayanması aynı şey değildir
    (Ders 1.6 §3.4). Alıntı kaynakta yoksa kararın dayanağı yoktur; iddia şüpheli sayılır.
    """
    for row in verdicts:
        row["kanit_bulundu"] = evidence_found(row["kanit"], source)
        if row["karar"] == "supported" and not row["kanit_bulundu"]:
            row["karar"] = "suspect"
    return verdicts
```

`print_verdicts` fonksiyonunu, `Kanıt` sütununda denetim sonucunu gösteren şu hâliyle değiştirin:

```python
def print_verdicts(verdicts: list[dict]) -> None:
    """Doğrulama tablosu: iddia, karar, kanıt denetimi sonucu ve gerekçe."""
    rows = []
    for i, row in enumerate(verdicts, start=1):
        evidence = "kaynakta" if row["kanit_bulundu"] else ("kaynakta YOK" if row["kanit"] else "yok")
        rows.append([str(i), shorten(row["iddia"], 56), VERDICT_LABELS[row["karar"]], evidence, shorten(row["not"], 44)])
    print_table(["#", "İddia", "Karar", "Kanıt", "Not"], rows, right_align={0})
```

`cmd_verify` fonksiyonunu, doğrulamadan sonra denetimi uygulayan şu hâliyle değiştirin:

```python
def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    source = read_text(args.source)
    verdicts, result = verify_claims(client, model, source, load_claims(args.claims))
    apply_evidence_check(verdicts, source)
    print_verdicts(verdicts)
    print()
    print(fmt_usage(result, model))
    return 0
```

`normalize_text` yalnızca harf ve rakamları tutar: "`409 Conflict` döner." metni `409conflictdöner` olur. Bu sayede modelin alıntıda ters tırnağı atması ya da bir virgülü değiştirmesi eşleşmeyi bozmaz; ama bir kelimeyi değiştirmesi bozar. Denetim kasıtlı olarak katıdır: bulanık eşleme yok. Katı bir denetim bazen doğru alıntıyı da reddeder; bu yanlış alarmları Adım 7'de sayacaksınız.

**Çalıştırın:** Bu kez tuzaklı bir yanıtla çalışın. `tuzaklar/01_iptal_tuzakli.md` dosyası, aynı soruya verilmiş bir yanıtın içine kaynakta olmayan üç cümle yerleştirilmiş hâlidir (Adım 7'de kendi setinizi yapacaksınız).

```bash
python calisma/dedektor.py extract tuzaklar/01_iptal_tuzakli.md --out sonuclar/01_iptal_tuzakli.iddialar.json
python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal_tuzakli.iddialar.json
```

**Beklenen çıktı:** `extract` tuzaklı yanıttan daha uzun bir iddia listesi çıkarır. `verify` tablosunda `Kanıt` sütunu artık üç değerden birini gösterir: `kaynakta` (alıntı bulundu), `kaynakta YOK` (model alıntı verdi ama kaynakta geçmiyor; karar `ŞÜPHELİ`ye düştü) ya da `yok` (model alıntı vermedi; `DESTEKSİZ` kararlarda beklenen durum). Yerleştirilen cümlelere karşılık gelen iddialar `DESTEKSİZ` ya da `ŞÜPHELİ` olmalıdır; hangisinin hangisi olduğu çalıştırmaya göre değişir. Referans ölçümde doğrulayıcının verdiği her alıntı kaynakta bulundu, dolayısıyla `ŞÜPHELİ` görünmedi; üç tuzak da `DESTEKSİZ`. Dördüncü bir `DESTEKSİZ` daha var: `iptal_edilemez` hata kodu. Bu bilgi `kaynaklar/03_webhook_ve_hatalar.md` dokümanında doğru, ama zincire verilen kaynak `02_gonderi_uc_noktalari.md`; doğrulayıcı "kendi bilgini kullanma" talimatına uyup yalnızca verilen kaynağa baktı. Doğru bir bilginin bu kaynağa göre desteksiz olması hata değil, grounding'in tanımıdır.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py extract tuzaklar/01_iptal_tuzakli.md --out sonuclar/01_iptal_tuzakli.iddialar.json
8 iddia çıkarıldı:
  1. Bir gönderiyi iptal etmek için `DELETE /v3/gonderiler/{takip_no}` isteği gönderilir.
  2. Gönderi iptali yalnızca gönderi `olusturuldu` durumundayken mümkündür.
  3. Toplanmış bir gönderi için iptal çağrısı 409 koduyla reddedilir.
  4. Toplanmış bir gönderi için iptal çağrısının yanıtında `iptal_edilemez` hata kodu döner.
  5. Toplanmış bir gönderinin iptali için müşteri hizmetleriyle iletişime geçilmesi gerekir.
  6. İptal isteği, gönderi oluşturulduktan sonraki 2 saat içinde yapılmalıdır.
  7. Birden fazla gönderiyi tek seferde iptal etmek için `POST /v3/gonderiler/toplu-iptal` uç noktası kullanılabilir.
  8. İptal edilen gönderinin `durum` alanı `iade` değerini alır.

Claude Haiku 5.5  |  girdi 730 token, çıktı 356 token  |  $0,00025
İddialar kaydedildi: sonuclar/01_iptal_tuzakli.iddialar.json
```

```text
$ python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal_tuzakli.iddialar.json
#  İddia                                                     Karar      Kanıt     Not
-  --------------------------------------------------------  ---------  --------  --------------------------------------------
1  Bir gönderiyi iptal etmek için `DELETE /v3/gonderiler/{…  DESTEKLİ   kaynakta  Kaynak, iptalin DELETE /v3/gonderiler/{taki…
2  Gönderi iptali yalnızca gönderi `olusturuldu` durumunda…  DESTEKLİ   kaynakta  Kaynak, iptalin yalnızca olusturuldu durumu…
3  Toplanmış bir gönderi için iptal çağrısı 409 koduyla re…  DESTEKLİ   kaynakta  Kaynak, toplanmış gönderi için iptal isteği…
4  Toplanmış bir gönderi için iptal çağrısının yanıtında `…  DESTEKSİZ  yok       Kaynak, 409 yanıtında dönen hata kodu adını…
5  Toplanmış bir gönderinin iptali için müşteri hizmetleri…  DESTEKLİ   kaynakta  Kaynak, toplanmış gönderi iptali için müşte…
6  İptal isteği, gönderi oluşturulduktan sonraki 2 saat iç…  DESTEKSİZ  yok       Kaynakta iptal için 2 saatlik bir süre sını…
7  Birden fazla gönderiyi tek seferde iptal etmek için `PO…  DESTEKSİZ  yok       Kaynakta toplu iptal uç noktası (POST /v3/g…
8  İptal edilen gönderinin `durum` alanı `iade` değerini a…  DESTEKSİZ  yok       Kaynak, iptal edilen gönderilerin durum ala…

Claude Haiku 5.5  |  girdi 1.819 token, çıktı 798 token  |  $0,00058
```

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
# Risk skoru: her kararın ağırlığı (0 = sorun yok, 1 = kaynak dışı iddia).
RISK_WEIGHTS = {"supported": 0.0, "suspect": 0.5, "unsupported": 1.0, "contradicted": 1.0}

# Yönlendirme etiketleri ve İNCELE için varsayılan skor eşiği.
ROUTE_ACCEPT, ROUTE_REVIEW, ROUTE_REJECT = "KABUL", "İNCELE", "RET"
DEFAULT_THRESHOLD = 0.25
```

`apply_evidence_check` fonksiyonunun altına skor ve yönlendirme fonksiyonlarını ekleyin:

```python
def risk_score(verdicts: list[dict]) -> float:
    """Kararların ağırlıklı ortalaması: 0 = tüm iddialar kaynaklı, 1 = hiçbiri değil."""
    return sum(RISK_WEIGHTS[row["karar"]] for row in verdicts) / len(verdicts)


def route(verdicts: list[dict], score: float, threshold: float) -> str:
    """Risk skorunu yönlendirmeye çevirir (Ders 1.6 §5.2 adım 6). Çelişen iddia tek başına RET demektir."""
    if any(row["karar"] == "contradicted" for row in verdicts):
        return ROUTE_REJECT
    if score == 0:
        return ROUTE_ACCEPT
    if score <= threshold:
        return ROUTE_REVIEW
    return ROUTE_REJECT
```

`fmt_usd` fonksiyonunun altına skor biçimlendiricisini, `print_verdicts` fonksiyonunun altına özet satırlarını basan fonksiyonu ekleyin:

```python
def fmt_score(score: float) -> str:
    return _tr_number(f"{score:.2f}")
```

```python
def print_summary(verdicts: list[dict], score: float, decision: str, threshold: float) -> None:
    """Karar dağılımı, risk skoru ve yönlendirme satırları."""
    counts = {key: sum(1 for row in verdicts if row["karar"] == key) for key in VERDICT_LABELS}
    parts = [f"{counts[key]} {tr_lower(label)}" for key, label in VERDICT_LABELS.items() if counts[key]]
    print(f"{len(verdicts)} iddia: " + ", ".join(parts))
    print(f"Risk skoru: {fmt_score(score)} (eşik {fmt_score(threshold)})  →  {decision}")
```

`cmd_verify` fonksiyonunu şu hâliyle değiştirin:

```python
def cmd_verify(args, client, pricing: dict) -> int:
    model = select_model(pricing, args.verifier, "dogrulayici")
    source = read_text(args.source)
    verdicts, result = verify_claims(client, model, source, load_claims(args.claims))
    apply_evidence_check(verdicts, source)
    score = risk_score(verdicts)
    print_verdicts(verdicts)
    print()
    print_summary(verdicts, score, route(verdicts, score, args.threshold), args.threshold)
    print(fmt_usage(result, model))
    return 0
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

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal_tuzakli.iddialar.json
#  İddia                                                     Karar      Kanıt     Not
-  --------------------------------------------------------  ---------  --------  --------------------------------------------
1  Bir gönderiyi iptal etmek için `DELETE /v3/gonderiler/{…  DESTEKLİ   kaynakta  Doküman, iptal için DELETE isteğinin kullan…
2  Gönderi iptali yalnızca gönderi `olusturuldu` durumunda…  DESTEKLİ   kaynakta  Doküman, iptalin yalnızca olusturuldu durum…
3  Toplanmış bir gönderi için iptal çağrısı 409 koduyla re…  DESTEKLİ   kaynakta  Doküman, toplanmış gönderi için iptal isteğ…
4  Toplanmış bir gönderi için iptal çağrısının yanıtında `…  DESTEKSİZ  yok       Doküman, 409 yanıtında dönen hata kodunun a…
5  Toplanmış bir gönderinin iptali için müşteri hizmetleri…  DESTEKLİ   kaynakta  Doküman, toplanmış gönderinin iptali için m…
6  İptal isteği, gönderi oluşturulduktan sonraki 2 saat iç…  DESTEKSİZ  yok       Doküman, iptal için gönderi oluşturulduktan…
7  Birden fazla gönderiyi tek seferde iptal etmek için `PO…  DESTEKSİZ  yok       Doküman toplu iptal uç noktasından ve POST…
8  İptal edilen gönderinin `durum` alanı `iade` değerini a…  DESTEKSİZ  yok       Doküman iptal edilen gönderilerin durum ala…

8 iddia: 4 destekli, 4 desteksiz
Risk skoru: 0,50 (eşik 0,25)  →  RET
Claude Haiku 5.5  |  girdi 1.819 token, çıktı 774 token  |  $0,00057
```

```text
$ python calisma/dedektor.py verify kaynaklar/02_gonderi_uc_noktalari.md sonuclar/01_iptal.iddialar.json --threshold 0.5
#  İddia                                                     Karar      Kanıt     Not
-  --------------------------------------------------------  ---------  --------  --------------------------------------------
1  Gönderiyi iptal etmek için `DELETE /v3/gonderiler/{taki…  DESTEKLİ   kaynakta  Doküman, bu uç noktanın gönderiyi iptal ett…
2  Gönderi iptali yalnızca gönderi `olusturuldu` durumunda…  DESTEKLİ   kaynakta  Doküman, iptalin yalnızca bu durumdaki gönd…
3  Kurye gönderiyi topladıktan sonra gönderi iptal edileme…  DESTEKLİ   kaynakta  Kurye gönderiyi topladıktan sonra iptal ist…
4  Gönderi durumu `olusturuldu` dışına çıktığında iptal ed…  DESTEKLİ   kaynakta  İptal yalnızca `olusturuldu` durumunda mümk…
5  Gönderi iptal edilemediğinde API `409 Conflict` döner.    DESTEKSİZ  yok       Kaynak, iptal isteği reddedildiğinde (kurye…
6  Gönderi iptal edilemediğinde iptal için müşteri hizmetl…  DESTEKSİZ  yok       Kaynak, kurye toplamasından sonra iptal içi…

6 iddia: 4 destekli, 2 desteksiz
Risk skoru: 0,33 (eşik 0,50)  →  İNCELE
Claude Haiku 5.5  |  girdi 1.700 token, çıktı 791 token  |  $0,00057
```

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
DEFAULT_CHAIN_PATH = DEFAULT_RESULTS_DIR / "zincir.jsonl"
```

`write_text` fonksiyonunun altına kayıt fonksiyonunu ekleyin:

```python
def save_record(path: Path, record: dict) -> None:
    """Zincir kaydını JSONL dosyasının sonuna ekler."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

`cmd_verify` fonksiyonunun altına zincir komutunu ekleyin:

```python
def cmd_chain(args, client, pricing: dict) -> int:
    generator = select_model(pricing, args.generator, "uretici")
    verifier = select_model(pricing, args.verifier, "dogrulayici")
    source, question = read_text(args.source), read_question(args.question)
    calls, cost = 0, 0.0

    print(f"Soru: {question}")
    if args.answer:
        answer = read_text(args.answer)
        answer_file = args.answer
        print(f"Yanıt dosyadan okundu: {answer_file} (üretim atlandı)")
    else:
        result = generate_answer(client, generator, source, question)
        answer, answer_file = result["text"], shown(answer_path(args.question))
        write_text(answer_path(args.question), answer)
        calls, cost = calls + 1, cost + estimate_cost(generator, result["input_tokens"], result["output_tokens"])
        print(f"Yanıt ({generator['name']}):")
        print(wrap_text(answer))
    print()

    claims, result = extract_claims(client, verifier, answer)
    calls, cost = calls + 1, cost + estimate_cost(verifier, result["input_tokens"], result["output_tokens"])
    print(f"Aşama 1 — {len(claims)} iddia çıkarıldı ({verifier['name']})")

    verdicts, result = verify_claims(client, verifier, source, claims)
    calls, cost = calls + 1, cost + estimate_cost(verifier, result["input_tokens"], result["output_tokens"])
    apply_evidence_check(verdicts, source)
    score = risk_score(verdicts)
    decision = route(verdicts, score, args.threshold)
    print(f"Aşama 2 — iddialar kaynağa karşı doğrulandı ({verifier['name']})")
    print()
    print_verdicts(verdicts)
    print()
    print_summary(verdicts, score, decision, args.threshold)
    print(f"{calls} çağrı, toplam {fmt_usd(cost)}")

    out = Path(args.out) if args.out else DEFAULT_CHAIN_PATH
    save_record(out, {
        "zaman": datetime.now().isoformat(timespec="seconds"), "kaynak": args.source, "soru": question,
        "yanit_dosyasi": answer_file, "uretici": None if args.answer else generator["key"], "dogrulayici": verifier["key"],
        "iddialar": verdicts, "skor": round(score, 3), "esik": args.threshold, "yonlendirme": decision,
        "cagri": calls, "maliyet": cost,
    })
    print(f"Kaydedildi: {shown(out)}")
    return 0
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
def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        commands = {"answer": cmd_answer, "extract": cmd_extract, "verify": cmd_verify, "chain": cmd_chain}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2
```

`cmd_chain` içindeki kayıt sözlüğüne bakın: iddialar kararlarıyla birlikte, skor, eşik, yönlendirme, çağrı sayısı ve maliyet. `uretici` alanı `--answer` verildiğinde `None` olur; kaydı okuyan biri yanıtın modelden mi dosyadan mı geldiğini görür.

**Çalıştırın:** Önce kaynağın kısmen cevapladığı bir soruyla, sonra tuzaklı yanıtla:

```bash
python calisma/dedektor.py chain kaynaklar/03_webhook_ve_hatalar.md sorular/03_webhook_imza.txt
python calisma/dedektor.py chain kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt --answer tuzaklar/01_iptal_tuzakli.md
```

**Beklenen çıktı:** İlk komutta soru, üreticinin yanıtı, `Aşama 1` ve `Aşama 2` satırları, karar tablosu, özet, `3 çağrı, toplam $...` ve `Kaydedildi: sonuclar/zincir.jsonl`. Webhook sorusunun iki ayrıntısı (imzanın geçerlilik süresi, zaman damgası) dokümanda yoktur; modelin bu boşluğu nasıl geçtiği tabloda görünür. Referans ölçümde Sonnet boşluğu doldurmadı, "dokümanda belirtilmiyor" dedi; çıkarıcı bu cümleleri de iddia yaptı ("Doküman imzanın kaç saniye geçerli olduğunu belirtmez.") ve doğrulayıcı kaynakta böyle bir bilgi olmadığı için onları `DESTEKSİZ` saydı: 10 iddianın 3'ü desteksiz, skor 0,30, yönlendirme `RET`. Model dürüst davrandı, dedektör yine de yanıtı reddetti; bunu kontrol noktasında tartışacaksınız. Aynı soru referans demoda 9 iddia üretip 0,22 ile `İNCELE` aldı: iddia sayısı çalıştırmadan çalıştırmaya değişir ve eşiğe yakın skorlarda yönlendirmeyi değiştirir (Ders 1.5 §5). İkinci komutta `Yanıt dosyadan okundu ... (üretim atlandı)` satırı ve `2 çağrı` görürsünüz.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py chain kaynaklar/03_webhook_ve_hatalar.md sorular/03_webhook_imza.txt
Soru: Webhook isteklerinin imzasını nasıl doğrularım? İmza kaç saniye geçerli ve zaman damgası imza hesabına dahil mi?
Yanıt (Claude Sonnet 5.5):
İmza, `X-Kuzey-Imza` başlığında gelir; bunu doğrulamak için istek gövdesini ham bayt dizisi olarak
alıp panelde gösterilen webhook gizli anahtarıyla HMAC-SHA256 ile hesaplamalı, sonucu hex olarak
kodlayıp başlıktaki değerle karşılaştırmalı ve eşleşmeyen istekleri reddetmelisiniz. JSON'u yeniden
biçimlendirirseniz imza tutmaz. Ancak dokümanda imzanın kaç saniye geçerli olduğuna dair bir bilgi
yok; zaman damgasının imza hesabına dahil olup olmadığı da belirtilmemiş. Dokümana göre imza
yalnızca istek gövdesi üzerinden hesaplanıyor, gövdede `zaman` alanı bulunsa da bunun ayrıca imzaya
katıldığına dair bir ifade yok.

Aşama 1 — 10 iddia çıkarıldı (Claude Haiku 5.5)
Aşama 2 — iddialar kaynağa karşı doğrulandı (Claude Haiku 5.5)

 #  İddia                                                     Karar      Kanıt     Not
--  --------------------------------------------------------  ---------  --------  --------------------------------------------
 1  İmza, X-Kuzey-Imza başlığında gelir.                      DESTEKLİ   kaynakta  Doküman imzanın bu başlıkta geldiğini açıkç…
 2  İmzayı doğrulamak için istek gövdesi ham bayt dizisi ol…  DESTEKLİ   kaynakta  Doküman imza hesabında gövdenin ham bayt di…
 3  İmza, istek gövdesi ham bayt dizisi üzerinden panelde g…  DESTEKLİ   kaynakta  Doküman hesaplama yöntemini HMAC-SHA256, an…
 4  HMAC-SHA256 sonucu hex olarak kodlanıp başlıktaki değer…  DESTEKLİ   kaynakta  Doküman imzanın hex olarak kodlandığını ve…
 5  Başlıktaki değerle eşleşmeyen istekler reddedilmelidir.   DESTEKLİ   kaynakta  Doküman eşleşmeyen isteklerin reddedilmesi…
 6  JSON yeniden biçimlendirilirse imza geçersiz hale gelir.  DESTEKLİ   kaynakta  Doküman yeniden biçimlendirmenin imzayı geç…
 7  Doküman imzanın kaç saniye geçerli olduğunu belirtmez.    DESTEKSİZ  yok       Doküman imzanın geçerlilik süresine dair he…
 8  Doküman zaman damgasının imza hesabına dahil olup olmad…  DESTEKSİZ  yok       Doküman zaman damgasının imza hesabına dahi…
 9  Dokümana göre imza yalnızca istek gövdesi üzerinden hes…  DESTEKLİ   kaynakta  Doküman imzanın yalnızca istek gövdesi üzer…
10  Gövdede zaman alanı bulunsa da doküman bu alanın ayrıca…  DESTEKSİZ  yok       Doküman gövdedeki zaman alanının imzaya kat…

10 iddia: 7 destekli, 3 desteksiz
Risk skoru: 0,30 (eşik 0,25)  →  RET
3 çağrı, toplam $0,0071
Kaydedildi: sonuclar/zincir.jsonl
```

```text
$ python calisma/dedektor.py chain kaynaklar/02_gonderi_uc_noktalari.md sorular/01_iptal.txt --answer tuzaklar/01_iptal_tuzakli.md
Soru: Oluşturduğum bir gönderiyi nasıl iptal ederim? Hangi durumda iptal edemem ve o zaman API ne döner?
Yanıt dosyadan okundu: tuzaklar/01_iptal_tuzakli.md (üretim atlandı)

Aşama 1 — 8 iddia çıkarıldı (Claude Haiku 5.5)
Aşama 2 — iddialar kaynağa karşı doğrulandı (Claude Haiku 5.5)

#  İddia                                                     Karar      Kanıt     Not
-  --------------------------------------------------------  ---------  --------  --------------------------------------------
1  Bir gönderiyi iptal etmek için `DELETE /v3/gonderiler/{…  DESTEKLİ   kaynakta  Kaynak, iptalin bu uç nokta ile yapıldığını…
2  Bir gönderinin iptali yalnızca gönderi `olusturuldu` du…  DESTEKLİ   kaynakta  Kaynak, iptalin yalnızca bu durumda mümkün…
3  Toplanmış bir gönderi için iptal çağrısı 409 koduyla re…  DESTEKLİ   kaynakta  Kaynak, toplanmış gönderi için iptal isteği…
4  Toplanmış bir gönderi için iptal çağrısının yanıtında `…  DESTEKSİZ  yok       Kaynak yanıttaki hata kodlarının adlarını (…
5  Toplanmış bir gönderinin iptali için müşteri hizmetleri…  DESTEKLİ   kaynakta  Kaynak, toplanmış gönderilerin iptali için…
6  İptal isteği, gönderi oluşturulduktan sonraki 2 saat iç…  DESTEKSİZ  yok       Kaynakta oluşturma sonrası iptal için bir z…
7  Birden fazla gönderiyi tek seferde iptal etmek için `PO…  DESTEKSİZ  yok       Kaynakta `POST /v3/gonderiler/toplu-iptal`…
8  İptal edilen gönderinin `durum` alanı `iade` değerini a…  DESTEKSİZ  yok       Kaynak, iptal edilen gönderilerin `durum` a…

8 iddia: 4 destekli, 4 desteksiz
Risk skoru: 0,50 (eşik 0,25)  →  RET
2 çağrı, toplam $0,00083
Kaydedildi: sonuclar/zincir.jsonl
```

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
# Tuzak setinde geçerli beklenti değerleri.
TRAP_EXPECTATIONS = ("yakalanmali", "gecmeli")
```

`load_claims` fonksiyonunun altına tuzak setini okuyan fonksiyonu ekleyin:

```python
def load_traps(path: str) -> dict:
    """Tuzak setini okur ve her tuzakta gerekli alanların bulunduğunu doğrular."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or not data.get("tuzaklar"):
        raise ValueError(f"{path}: 'tuzaklar' listesi boş ya da yok.")
    for trap in data["tuzaklar"]:
        for field in ("id", "tur", "anahtar", "beklenen"):
            if field not in trap:
                raise ValueError(f"{path}: her tuzakta '{field}' alanı olmalı (eksik: {trap.get('id', '?')}).")
        if trap["beklenen"] not in TRAP_EXPECTATIONS:
            raise ValueError(f"{path}: '{trap['id']}' tuzağında bilinmeyen beklenti: {trap['beklenen']}")
    return data
```

`route` fonksiyonunun altına eşleştirme ve değerlendirme fonksiyonlarını ekleyin:

```python
def match_claims(trap: dict, verdicts: list[dict]) -> list[dict]:
    """Tuzağın anahtar parçalarını taşıyan iddiaları bulur. Her parça geçmeli; '|' alternatif ayırır."""
    matched = []
    for row in verdicts:
        text = normalize_text(row["iddia"])
        if all(any(normalize_text(alt) in text for alt in part.split("|")) for part in trap["anahtar"]):
            matched.append(row)
    return matched


def judge_trap(trap: dict, matched: list[dict]) -> str:
    """Tuzağın sonucunu adlandırır: yakalandı, kaçtı, doğru geçti, yanlış alarm ya da iddia çıkarılmadı."""
    if not matched:
        return "iddia çıkarılmadı"
    flagged = any(row["karar"] != "supported" for row in matched)
    if trap["beklenen"] == "yakalanmali":
        return "yakalandı" if flagged else "kaçtı"
    return "yanlış alarm" if flagged else "doğru geçti"
```

`save_record` fonksiyonunun altına kayıt okuyucuyu ekleyin:

```python
def load_records(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    if not records:
        raise ValueError(f"{path}: zincir kaydı yok. Önce 'chain' komutunu çalıştır.")
    return records
```

`cmd_chain` fonksiyonunun altına karne komutunu ekleyin:

```python
def cmd_score(args) -> int:
    traps = load_traps(args.traps)
    records = load_records(args.results)
    target = traps.get("yanit")
    matching = [r for r in records if r.get("yanit_dosyasi") == target] if target else records
    if not matching:
        raise ValueError(f"{args.results}: '{target}' yanıtıyla çalıştırılmış zincir kaydı yok. "
                         f"Önce: chain <kaynak> <soru> --answer {target}")
    record = matching[-1]
    verdicts = record["iddialar"]
    print(f"Zincir kaydı: {record['zaman']}  |  yanıt: {record['yanit_dosyasi']}  |  "
          f"{len(verdicts)} iddia, yönlendirme {record['yonlendirme']}")
    print()

    rows, outcomes = [], []
    for trap in traps["tuzaklar"]:
        matched = match_claims(trap, verdicts)
        outcome = judge_trap(trap, matched)
        outcomes.append((trap, outcome))
        verdict_text = ", ".join(VERDICT_LABELS[row["karar"]] for row in matched) or "-"
        rows.append([trap["id"], trap["tur"], " + ".join(trap["anahtar"]), str(len(matched)), verdict_text, outcome])
    print_table(["Tuzak", "Tür", "Anahtar", "İddia", "Karar", "Sonuç"], rows, right_align={3})
    print()

    planted = [o for t, o in outcomes if t["beklenen"] == "yakalanmali"]
    controls = [o for t, o in outcomes if t["beklenen"] == "gecmeli"]
    caught = planted.count("yakalandı")
    print(f"Yakalama: {caught}/{len(planted)} tuzak yakalandı"
          + (f" ({planted.count('iddia çıkarılmadı')} tuzak iddia olarak çıkarılmadı)" if "iddia çıkarılmadı" in planted else ""))
    if controls:
        print(f"Yanlış alarm: {controls.count('yanlış alarm')}/{len(controls)} kontrol cümlesi haksız yere işaretlendi")
    return 0
```

`build_parser` içinde `return parser` satırının hemen üstüne yeni komutu ekleyin:

```python

    p_score = sub.add_parser("score", help="Tuzak setini zincir kaydıyla karşılaştır (çağrı yapmaz)")
    p_score.add_argument("results", help="chain komutunun yazdığı JSONL dosyası")
    p_score.add_argument("traps", help="Tuzak seti (YAML)")
```

`main` fonksiyonunu şu hâliyle değiştirin. `score` komutu API istemcisi gerektirmediği için anahtar kontrolünden önce yönlendiriliyor:

```python
def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pricing = load_pricing(Path(args.pricing))
        if args.command == "score":
            return cmd_score(args)

        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil.", file=sys.stderr)
                return 2
            client = anthropic.Anthropic()
        commands = {"answer": cmd_answer, "extract": cmd_extract, "verify": cmd_verify, "chain": cmd_chain}
        return commands[args.command](args, client, pricing)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    except anthropic.AuthenticationError:
        print("Hata: API anahtarı geçersiz. ANTHROPIC_API_KEY değerini kontrol et.", file=sys.stderr)
        return 2
    except anthropic.APIStatusError as e:
        print(f"Hata: API isteği reddedildi (HTTP {e.status_code}): {getattr(e, 'message', e)}", file=sys.stderr)
        return 2
    except anthropic.APIConnectionError:
        print("Hata: API'ye bağlanılamadı. Ağ bağlantını kontrol et.", file=sys.stderr)
        return 2
```

`match_claims` tuzağı iddiaya metinle bağlar: tuzak dosyasındaki `anahtar` parçalarının hepsi iddiada geçmeli, `|` ile alternatif yazılabilir (`"2 saat|iki saat"`). Çıkarıcı iddiayı yeniden ifade ettiği için cümlenin tamamı değil, ayırt edici parçası aranır. `judge_trap` beş sonuç üretir: `yakalandı` ve `kaçtı` yerleştirilen hatalar için, `doğru geçti` ve `yanlış alarm` kontrol cümleleri için, `iddia çıkarılmadı` ise cümlenin hiçbir iddiaya dönüşmediği durum için. Son durum dedektörün değil çıkarıcının hatasıdır ve ayrı sayılır.

**Çalıştırın:**

```bash
python calisma/dedektor.py score sonuclar/zincir.jsonl tuzaklar/01_iptal_tuzaklar.yaml
```

**Beklenen çıktı:** Kullanılan zincir kaydının zamanı ve yönlendirmesi, ardından tuzak başına bir satır: tür, anahtar, eşleşen iddia sayısı, karar ve sonuç. Altta `Yakalama: k/3 tuzak yakalandı` ve `Yanlış alarm: m/1 kontrol cümlesi haksız yere işaretlendi` satırları.

Referans çözümle alınmış çıktı (token sayıları metne, modele ve tokenizer sürümüne göre küçük farklar gösterebilir; yapı ve etiketler aynı olmalı):

```text
$ python calisma/dedektor.py score sonuclar/zincir.jsonl tuzaklar/01_iptal_tuzaklar.yaml
Zincir kaydı: 2026-10-11T23:36:58  |  yanıt: tuzaklar/01_iptal_tuzakli.md  |  8 iddia, yönlendirme RET

Tuzak  Tür            Anahtar                  İddia  Karar      Sonuç
-----  -------------  -----------------------  -----  ---------  -----------
T1     fabrication    toplu-iptal|toplu iptal      1  DESTEKSİZ  yakalandı
T2     confabulation  2 saat|iki saat              1  DESTEKSİZ  yakalandı
T3     conflation     iade                         1  DESTEKSİZ  yakalandı
K1     kontrol        409                          1  DESTEKLİ   doğru geçti

Yakalama: 3/3 tuzak yakalandı
Yanlış alarm: 0/1 kontrol cümlesi haksız yere işaretlendi
```

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
