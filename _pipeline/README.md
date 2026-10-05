# Proje hazırlama pipeline'ı

`agentic-ai-projects` reposundaki her projenin rehberini, kod rehberlerini, demosunu ve platform sayfasını tek kaynaktan üreten araç. Standart `proje-hazirlama-yonergesi.md` (v2.0), aşamalar ve onay kapıları `proje-hazirlama-pipeline.md` dokümanındadır. Bu klasör öğrenciler için değil, içerik hazırlayanlar içindir.

## Kurulum

```bash
pip install -r _pipeline/requirements.txt
playwright install chromium
cd _pipeline/demo-player && npm install && cd ../..
```

## Kullanım

```bash
python _pipeline/arac/pipeline.py <slug> <aşama> [--onizleme]
```

| Aşama | İş |
|-------|-----|
| `iskelet` | Yeni proje için repo klasörü ve girdi dosyaları |
| `olcum` | Gerçek API ile ölçüm (`ANTHROPIC_API_KEY` gerekir); `--onizleme` ile sahte istemci |
| `simulasyon` | Rehber talimatlarının ara sürümleri ürettiğini doğrular |
| `rehberler` | `kod-rehberi.html`, `kod-rehberi-yan-yana.html` |
| `demo` | `demo.json` (platform), `demo.html` (repo) |
| `icerik` | `project.mdx` (platform), `Step-by-Step-GUIDE.md` (repo) |
| `dogrula` | Testler, lint, simülasyon, UTF-8, bağlantılar, MDX, demo.json, JS |
| `ekran` | Ekran görüntüleri; yatay taşma ve konsol hatası kontrolü |
| `uret` | simulasyon + rehberler + demo + icerik + dogrula |

## Klasörler

| Yol | İçerik |
|-----|--------|
| `arac/` | Pipeline motoru (Python) ve sayfa şablonları |
| `demo-player/` | `<ProjectDemo />` React bileşeni; platforma kopyalanır ve `demo.html` için derlenir |
| `projeler/<slug>/` | Projeye özgü girdiler: `proje.yaml`, şablonlar, rehber YAML'ları, simülasyon tarifi, gerçek ölçüm çıktısı |
| `cikti/<slug>/` | Platforma kopyalanacak `project.mdx` ve `demo.json`; önizleme ve ekran görüntüleri (repoya eklenmez) |

Referans proje: `projeler/token-maliyet-hesaplayici/`.
