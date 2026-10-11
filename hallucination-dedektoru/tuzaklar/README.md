# Tuzaklar

Bu klasör ikili çalışmanın "tuzakçı" rolü içindir (rehber, Adım 7). Tuzakçı, `answer` komutunun ürettiği bir yanıtı kopyalar, içine kaynakta olmayan birkaç cümle yerleştirir ve bunları bir YAML dosyasında etiketler. Dedektör rolündeki partner zinciri `chain --answer` ile bu yanıt üzerinde çalıştırır; `score` komutu dedektörün kaç tuzağı yakaladığını ölçer.

| Dosya | İçerik |
|---|---|
| `01_iptal_tuzakli.md` | `sorular/01_iptal.txt` sorusuna verilmiş bir yanıtın tuzaklı kopyası (örnek) |
| `01_iptal_tuzaklar.yaml` | Bu yanıttaki tuzakların etiketleri: tür, anahtar, beklenen sonuç |

Örnek yanıt elle yazılmıştır; kendi setini kurarken `answer` çıktından yola çık ki yanıtın üslubu gerçek bir model yanıtına benzesin. Üç tuzak türü ve bir kontrol cümlesi bulunan bir set, dedektörün hem yakalama oranını hem yanlış alarm eğilimini gösterir.
