# Saha verisi karşılaştırması (18 Eylül 2026)

## Ne test edildi?

Ulak'ın OpenLandMap üzerinden gösterdiği **yüzey kil ve kum yüzdeleri**, ISRIC WoSIS'teki Türkiye konumlu gerçek toprak profillerinin laboratuvar ölçümleriyle karşılaştırıldı. WoSIS verileri farklı kurumların standartlaştırılmış saha profilleridir; yapı parseli için hazırlanmış mühendislik zemin etüdü değildir.

Kaynaklar: [WoSIS veri ve yöntem açıklaması](https://docs.isric.org/globaldata/wosis/faq-wosis.html), [OpenLandMap kil katmanı](https://developers.google.com/earth-engine/datasets/catalog/OpenLandMap_SOL_SOL_CLAY-WFRACTION_USDA-3A1A1A_M_v02), [OpenLandMap kum katmanı](https://developers.google.com/earth-engine/datasets/catalog/OpenLandMap_SOL_SOL_SAND-WFRACTION_USDA-3A1A1A_M_v02).

## Yöntem

- WoSIS WFS servisinden Türkiye sınırlarındaki, CC BY 4.0 lisanslı, üst sınırı 0–10 cm ve alt sınırı en çok 35 cm olan kil ve kum katmanları alındı.
- Kil için 0–0,002 mm, kum için 0,05–2 mm boyu kullanan ölçümler eşleştirildi. Profil başına en üstteki tek katman seçildi.
- 13 profilin koordinatları yerel `/analiz-et` API'sine gönderildi; harita tahminleri ile ölçümler arasındaki mutlak farklar yüzde puan olarak hesaplandı.
- Her iki ölçü de aynı 250 metrelik harita pikselini temsil etmeyebilir: saha örneği noktasal ve belli bir derinlik aralığından, harita ise 0 cm tahmininden gelir.

## Sonuç

| Ölçüt | Kil | Kum |
| --- | ---: | ---: |
| Geçerli profil | 13 | 13 |
| Ortalama mutlak fark | 11,64 yüzde puan | 9,10 yüzde puan |
| Ortalama yanlılık (harita − saha) | −10,24 yüzde puan | +6,51 yüzde puan |
| Farkı en fazla 10 yüzde puan olan profil | 8/13 | 8/13 |

Kil haritası bu küçük örneklemde çoğunlukla düşük, kum haritası yüksek tahmin etti. En büyük kil farkı 49,18 yüzde puandı. Sonuçlar [profil bazlı karşılaştırmada](texture_comparison.csv) ve [makine okunabilir özette](texture_summary.json) bulunur. [Ham saha değerleri](wosis_turkey_texture.csv) WoSIS'ten alınmıştır; kaynak ve lisans bilgisi yukarıdadır.

## Bu sonuç neyi doğrulamaz?

Bu karşılaştırma **erozyon/heyelan risk skorunu, taşıma kapasitesini veya yapılaşmaya uygunluğu doğrulamaz**. WoSIS toprak profillerinde bu sonuçlar için eşleşen olay/karar etiketi yoktur. Ayrıca OpenLandMap küresel toprak profillerinden eğitildiği için WoSIS örnekleriyle eğitim verisi çakışması olasılığı dışlanamaz; bu da karşılaştırmanın bağımsızlığını sınırlar. Örneklem küçük, seçilmiş ve Türkiye genelini temsil etmez.

Zemin kararını doğrulamak için parsel koordinatıyla eşleşen mühendislik sondajları, SPT/CPT, yeraltı suyu ve laboratuvar sonuçları; heyelan tahmini için de tarihli olay envanteri ile temsil edici olaysız alanlar gerekir. Bunlar mevcut veri setinde yoktur. Bu nedenle arayüz artık puanı yalnızca **doğrulanmamış göreli gösterge** olarak sunar; sentetik eğitimli model varsayılan olarak kapalıdır.

## Yeniden çalıştırma

API yerelde çalışırken, proje klasöründe:

```powershell
.\.venv\Scripts\python.exe validation\collect_wosis.py
.\.venv\Scripts\python.exe validation\compare_texture.py
```

WoSIS dinamik bir servistir; sonraki indirmelerde örnek sayısı değişebilir.
