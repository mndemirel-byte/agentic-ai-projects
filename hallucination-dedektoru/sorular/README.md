# Sorular

Her dosya, `answer` ve `chain` komutlarına verilecek tek bir soru içerir. Komut, ikinci argüman bir dosya yoluysa soruyu dosyadan okur; değilse argümanı sorunun kendisi sayar.

| Dosya | Kaynak | Niteliği |
|---|---|---|
| `01_iptal.txt` | `kaynaklar/02_gonderi_uc_noktalari.md` | Kaynak soruyu tamamen cevaplıyor |
| `02_hiz_limiti.txt` | `kaynaklar/01_kimlik_ve_limitler.md` | Kaynak soruyu tamamen cevaplıyor |
| `03_webhook_imza.txt` | `kaynaklar/03_webhook_ve_hatalar.md` | Kaynak soruyu kısmen cevaplıyor: imzanın geçerlilik süresi ve zaman damgası dokümanda yok |
| `04_sandbox.txt` | `kaynaklar/01_kimlik_ve_limitler.md` | Kaynak soruyu kısmen cevaplıyor: sandbox'a özgü limit ve veri silme süresi dokümanda yok |

Kısmen cevaplanan sorular bilerek seçildi: modelin dokümandaki boşluğu "dokümanda yok" diyerek mi, yoksa makul görünen bir ayrıntıyla doldurarak mı geçtiğini zincir gösterir (Ders 1.6 §3.3 confabulation).
