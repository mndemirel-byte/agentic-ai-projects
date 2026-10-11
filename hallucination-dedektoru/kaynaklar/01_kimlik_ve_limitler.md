# Kuzey Lojistik Kargo Takip API'si v3 — Kimlik doğrulama ve limitler

Bu doküman kurgusaldır; Kuzey Lojistik diye bir şirket ve bu API gerçekte yoktur. Projede kaynak doküman olarak kullanılır: modelin bu API hakkında dokümandan başka bir bilgi kaynağı olamaz.

## Temel adres ve sürüm

Tüm istekler `https://api.kuzeylojistik.example/v3` adresine HTTPS ile yapılır. API sürümü yoldaki `v3` parçasıyla belirlenir; ayrı bir sürüm başlığı yoktur. v2 uç noktaları 31 Mart 2026'da kapatılmıştır.

## Kimlik doğrulama

Her istek `X-Kuzey-Key` başlığında bir API anahtarı taşır. Anahtarlar müşteri panelinden üretilir ve `kz_live_` ya da `kz_test_` ön ekiyle başlar. `kz_test_` anahtarları yalnızca sandbox ortamında (`https://sandbox.kuzeylojistik.example/v3`) geçerlidir; sandbox'ta oluşturulan gönderiler gerçek sevkiyata dönüşmez.

Anahtar eksikse ya da geçersizse API `401 Unauthorized` döner. Bir anahtar en fazla 10 IP adresiyle sınırlandırılabilir; sınırlandırılmış anahtar başka bir IP'den kullanıldığında `403 Forbidden` döner.

## Hız limitleri

Standart plandaki bir anahtar dakikada en fazla 120 istek yapabilir. Limit aşıldığında API `429 Too Many Requests` döner ve `Retry-After` başlığında kaç saniye beklenmesi gerektiğini yazar. Kurumsal planda limit dakikada 600 istektir. Limitler anahtar başına hesaplanır, IP başına değil.

Toplu gönderi oluşturma uç noktası (`POST /v3/gonderiler/toplu`) tek istekte en fazla 50 gönderi kabul eder ve hız limitinde tek istek sayılır.

## Zaman ve biçim

Tüm tarih-saat alanları ISO 8601 biçiminde ve UTC'dir, örneğin `2026-10-09T14:30:00Z`. Para tutarları kuruş cinsinden tam sayı olarak taşınır: `12550` değeri 125,50 TL demektir. İstek ve yanıt gövdeleri JSON'dır; `Content-Type: application/json` başlığı zorunludur.
