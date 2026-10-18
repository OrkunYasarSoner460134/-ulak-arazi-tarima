# Ulak'ı çalıştırma

Bu uygulama tek bir Python sunucusundan hem web sayfasını hem API'yi sunar. Sayfayı `file://` ile açmayın; sunucu adresinden açın.

## Yerelde

Python 3.11 kurulu bir terminalde, bu klasörde:

```powershell
python -m pip install -r requirements.txt
earthengine authenticate
$env:EARTH_ENGINE_PROJECT = "ulak-arazi"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Ardından `http://127.0.0.1:8000/` adresini açın. `ulak-arazi` yerine Earth Engine erişimi olan gerçek Google Cloud proje kimliğinizi kullanın.

## Canlı sunucu

Docker destekleyen bir barındırma hizmetinde bu klasörü uygulama kökü olarak dağıtın. Hizmetin verdiği herkese açık HTTPS adresi hem arayüzü hem API'yi sunar; frontend için ayrı bir API adresi gerekmez.

Sunucu ortam değişkenleri:

- `EARTH_ENGINE_PROJECT`: Earth Engine API'si açık ve erişim izni verilmiş Google Cloud proje kimliği.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Earth Engine erişimi olan servis hesabının **JSON dosyasının içeriği**. Bunu yalnızca barındırma hizmetinin gizli ortam değişkenleri bölümüne koyun. Google Cloud üzerinde uygulamaya bir servis hesabı atanmışsa bu değişken yerine platformun varsayılan kimliği kullanılabilir.
- `PORT`: Barındırma hizmeti tarafından verilir; yoksa Docker imajı 8000 kullanır.

Servis hesabının Earth Engine projesine erişimi ve projenin Earth Engine kaydı gerekir. Ayrıntılar: https://developers.google.com/earth-engine/guides/service_account

`AIza...` biçimindeki Google API key bu Python Earth Engine sorgularını yetkilendirmez. Bu anahtarı HTML, Python kodu veya GitHub deposuna eklemeyin. Paylaşılan anahtarı Google Cloud Credentials ekranından silin veya yenileyin.

Dağıtımdan sonra `/health` sunucunun açık olduğunu gösterir. Gerçek Earth Engine bağlantısını doğrulamak için arayüzden bir konum analiz edin. Earth Engine kimlik doğrulaması veya veri sorgusu başarısızsa artık gerçek hata gösterilir; sahte uydu sonucu üretilmez.

**Risk puanı sınırı:** Gösterge kural tabanlıdır; heyelan olasılığı veya yapılaşma kararı değildir.

Türkiye'deki 13 gerçek saha profiliyle yapılan kil/kum karşılaştırmasının yöntemi ve sonuçları [Ulak/validation/REPORT.md](Ulak/validation/REPORT.md) dosyasındadır. Bu çalışma mühendislik zemin etüdü veya erozyon riski doğrulaması değildir.

Yerel, LoRA ile ince ayarlı sohbet modelinin kurulumu ve sınırları [Ulak/llm/README.md](Ulak/llm/README.md) dosyasındadır. Sohbet dış dil modeli API'si kullanmaz; çalışması için model dosyaları ve GPU gerekir.

## Depo yapısı

```text
./
├── main.py                 # FastAPI sunucusu ve analiz uçları
├── index.html              # Web arayüzü
├── Ulak/llm/               # Yerel model eğitimi, çıkarım ve bilgi kartları
├── Ulak/validation/        # WoSIS karşılaştırma kodu, veri ve rapor
├── Dockerfile
├── requirements.txt
└── requirements-llm.txt
```

`.venv`, indirilen temel model ve eğitilmiş adaptör Git'e eklenmez. Model dosyaları yerel kurulum sırasında `models/` altında oluşturulur.
