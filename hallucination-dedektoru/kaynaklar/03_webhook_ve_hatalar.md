# Kuzey Lojistik Kargo Takip API'si v3 — Webhook'lar ve hata kodları

Bu doküman kurgusaldır; Kuzey Lojistik diye bir şirket ve bu API gerçekte yoktur. Projede kaynak doküman olarak kullanılır.

## Webhook kaydı

Müşteri panelinden bir webhook adresi tanımlandığında, gönderi durumu her değiştiğinde bu adrese `POST` isteği gönderilir. İstek gövdesinde `olay` (`durum_degisti` ya da `teslim_edildi`), `takip_no`, `durum` ve `zaman` alanları bulunur. Her anahtar için en fazla 3 webhook adresi tanımlanabilir.

## İmza doğrulama

Her webhook isteği `X-Kuzey-Imza` başlığı taşır. İmza, istek gövdesinin panelde gösterilen webhook gizli anahtarıyla HMAC-SHA256 ile hesaplanmış ve hex olarak kodlanmış hâlidir. Alıcı taraf imzayı aynı yöntemle hesaplayıp karşılaştırmalı, eşleşmeyen istekleri reddetmelidir. İmza hesabında gövde ham bayt dizisi olarak kullanılır; JSON yeniden biçimlendirilirse imza tutmaz.

## Yeniden deneme

Webhook adresi 2xx dışında bir yanıt verirse ya da 10 saniye içinde yanıt vermezse istek yeniden denenir. En fazla 5 deneme yapılır; denemeler arası bekleme 1, 5, 30, 120 ve 600 saniyedir. Beş deneme de başarısız olursa olay panelde "teslim edilemedi" olarak işaretlenir ve 7 gün boyunca panelden elle yeniden gönderilebilir.

## Hata kodları

| HTTP kodu | `hata.kod` değeri | Anlamı |
|---|---|---|
| 400 | `gecersiz_istek` | Gövde JSON değil ya da zorunlu alan eksik; `hata.alan` eksik alanı söyler |
| 401 | `kimlik_dogrulanamadi` | `X-Kuzey-Key` başlığı eksik ya da geçersiz |
| 403 | `ip_engellendi` | Anahtar bu IP adresinden kullanılamaz |
| 404 | `gonderi_bulunamadi` | Takip numarası bu anahtara ait bir gönderiyle eşleşmiyor |
| 409 | `iptal_edilemez` | Gönderi toplandıktan sonra iptal istendi |
| 410 | `arsivlendi` | Gönderi 90 günlük sorgu süresini doldurdu |
| 422 | `desi_araligi` | `desi` 1–300 aralığının dışında |
| 429 | `hiz_limiti` | Dakikalık istek limiti aşıldı; `Retry-After` başlığına bak |

Her hata yanıtının gövdesi `hata.kod`, `hata.mesaj` ve istek kimliğini taşıyan `hata.istek_id` alanlarını içerir. Destek taleplerinde `hata.istek_id` değerinin paylaşılması beklenir.
