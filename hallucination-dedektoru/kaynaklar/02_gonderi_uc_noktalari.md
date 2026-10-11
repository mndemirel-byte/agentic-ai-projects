# Kuzey Lojistik Kargo Takip API'si v3 — Gönderi uç noktaları

Bu doküman kurgusaldır; Kuzey Lojistik diye bir şirket ve bu API gerçekte yoktur. Projede kaynak doküman olarak kullanılır.

## Gönderi oluşturma

`POST /v3/gonderiler` yeni bir gönderi oluşturur. İstek gövdesinde şu alanlar zorunludur: `gonderici` (adres nesnesi), `alici` (adres nesnesi), `desi` (tam sayı, 1–300 arası) ve `servis` (`standart` ya da `ekspres`). İsteğe bağlı alanlar: `referans` (en fazla 64 karakterlik müşteri referansı) ve `kapida_odeme` (kuruş cinsinden tutar; verilmezse kapıda ödeme yoktur).

Başarılı istek `201 Created` döner. Yanıtta `takip_no` alanı bulunur; takip numarası `KZ` ön eki ve 10 rakamdan oluşur, örneğin `KZ2026100912`. Aynı `referans` değeriyle 24 saat içinde ikinci bir istek gelirse API yeni gönderi oluşturmaz, var olan gönderiyi `200 OK` ile döner.

## Gönderi sorgulama

`GET /v3/gonderiler/{takip_no}` tek bir gönderinin güncel durumunu döner. Yanıttaki `durum` alanı şu değerlerden birini alır: `olusturuldu`, `toplandi`, `transfer`, `dagitimda`, `teslim_edildi`, `iade`. Durum değişiklikleri `hareketler` dizisinde zaman damgasıyla listelenir; dizi en yeni hareket en üstte olacak şekilde sıralıdır.

Teslim edilen gönderilerde `teslim_alan` alanı alıcının beyan ettiği adı taşır. Bu alan teslimden sonra 90 gün boyunca sorgulanabilir; 90 günün sonunda gönderi arşivlenir ve sorgu `410 Gone` döner.

## Listeleme

`GET /v3/gonderiler` anahtara ait gönderileri listeler. `durum` ve `baslangic` / `bitis` (ISO 8601) sorgu parametreleriyle filtrelenebilir. Sayfalama imleç tabanlıdır: yanıttaki `sonraki_imlec` değeri bir sonraki isteğe `imlec` parametresi olarak verilir. Bir sayfada en fazla 100 kayıt döner; `limit` parametresiyle daha azı istenebilir.

## İptal

`DELETE /v3/gonderiler/{takip_no}` gönderiyi iptal eder. İptal yalnızca `olusturuldu` durumundaki gönderiler için mümkündür; kurye gönderiyi topladıktan sonra iptal isteği `409 Conflict` döner ve iptal için müşteri hizmetleriyle iletişime geçilmesi gerekir.
