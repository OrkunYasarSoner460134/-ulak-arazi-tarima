# Yerel Ulak AI

Sohbet, dış bir dil modeli API'si kullanmadan yerel Qwen2.5-1.5B-Instruct modeli ve LoRA adaptörüyle çalışır. Temel model [Apache 2.0 lisanslıdır](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/LICENSE). İlgili kaynak kartları [knowledge.json](knowledge.json) içinden seçilip modele verilir; bağlantılar uygulama tarafından yanıtın altında gösterilir.

## Yerelde kurulum

RTX 4060 8 GB GPU'da denenen kurulum, proje klasöründeki sanal ortamda:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
.\.venv\Scripts\python.exe -m llm.download_model
.\.venv\Scripts\python.exe -m llm.train
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Model ağırlıkları `models/base`, eğitilen adaptör `models/adapter` altında kalır. Bu büyük dosyalar Git'e eklenmez. Sunucuda `models` klasörünü Docker konteynerindeki `/app/models` konumuna bağlamak gerekir. Örnek: `docker run --gpus all -p 8000:8000 -v <models-klasorunun-mutlak-yolu>:/app/models <imaj-adi>`. Çalıştırma ortamında NVIDIA GPU, sürücü ve GPU destekli konteyner altyapısı gerekir. İlk kurulumda temel model indirilir; daha sonra sohbet çıkarımı yerel dosyalarla çalışır.

## Eğitim kapsamı

- 20 kaynak kartından 40 Türkçe eğitim örneği; aynı kartların farklı ifadelerinden 20 kontrol sorusu.
- LoRA: rank 8, 3 epoch, Qwen2.5-1.5B-Instruct.
- Kontrol kaybı 0,1979'dan 0,0252'ye indi. Bu **aynı kartlara ait soruların yeniden ifade edilmesiyle** ölçüldü; bağımsız jeoteknik uzmanlık, yanlış bilgi oranı veya mühendislik karar kalitesi ölçümü değildir.
- İnce ayar yanıt biçimi ve kart bilgisinin kullanımını öğretir. Kaynak kartları kaldırıldığında modelin bilimsel doğruluğu garanti edilmez.

## Chinchilla ölçek hesabı

Chinchilla çalışması sıfırdan temel model ön eğitimi için parametre ve veri miktarının birlikte büyütülmesini inceler. Yaklaşık 20 token/parametre hesabıyla 1.543.714.304 parametreli temel modelin hedefi **30.874.286.080 token** olur. Bu, Ulak'ın alan uyarlaması için kullandığı LoRA eğitimiyle aynı işlem değildir; hazır temel model zaten önceden eğitilmiştir. Milyarlarca tokenı küçük bir alan veri kümesiyle tekrar etmek bilgi kazandırmaz ve aşırı uyuma yol açar.

Güncel eğitimden sonra gerçek değerleri görmek için:

```powershell
.\.venv\Scripts\python.exe -m llm.scaling_report
```

Alan kalitesi için kaynak çeşitliliği, bağımsız uzman etiketli değerlendirme, yanlış bilgi testleri ve gerçek saha verisi gerekir. Ölçek hesabı tek başına jeoteknik uzmanlık sağlamaz.

Bilgi kartları USGS, FHWA, [AFAD afet terimleri sözlüğü](https://www.afad.gov.tr/aciklamali-afet-yonetimi-terimleri-sozlugu), Google Earth Engine veri kataloğu ve [yerel saha karşılaştırmasına](../validation/REPORT.md) dayanır. Her kartta kaynak bağlantısı vardır. Kaynak dışı bir soru geldiğinde sistem kaynak bulunmadığını söyler. Model parsel güvenliği, yapı izni veya heyelan olasılığı kararı vermek üzere eğitilmemiştir.

Uygulamanın Earth Engine analizi ayrı bir servistir ve yine Google bağlantısı gerektirir; yalnızca **sohbet modeli** dış dil modeli API'si kullanmaz.
