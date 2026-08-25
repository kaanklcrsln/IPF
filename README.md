# IPF - Image Processing Functions

Görüntü iyileştirme, gürültü azaltma ve pansharpening filtrelerinden oluşan
bir koleksiyon ve bunları interaktif olarak kullanmayı sağlayan bir masaüstü
arayüz.

Tüm işlem **yerel makinede** yapılır; hiçbir görüntü dışarı gönderilmez.

<img width="2094" height="1266" alt="arayüz-2" src="https://github.com/user-attachments/assets/16e291a9-958e-4b40-bd71-3cb155ee553e" />

---

## Kurulum

```bash
pip install -r requirements.txt
```

`rasterio` isteğe bağlıdır — kurulu değilse `.tif` dosyaları da Pillow ile
okunur, yalnızca coğrafi referans bilgisi (transform / CRS) korunmaz.

## Çalıştırma

```bash
python main.py
```

---

## GUI

<!-- ---------------------------------------------------------------
     ARAYÜZ GÖRSELİ
     Ekran görüntüsünü docs/ klasörüne koyup aşağıdaki satırın
     yorumunu kaldır (ve altındaki ASCII şemayı silebilirsin):

         mkdir docs
         # ekran görüntüsünü docs/screenshot.png olarak kaydet
--------------------------------------------------------------- -->

<!-- ![IPF arayüzü](docs/screenshot.png) -->

```
┌──────────────┬───────────────────────────────┬──────────────────┐
│ Görüntü      │  GİRDİ            ÇIKTI       │  İstatistik      │
│ Filtre       │  ┌─────────┐    ┌─────────┐   │  Altyapı         │
│  Kategori    │  │         │    │         │   │                  │
│  Fonksiyon   │  └─────────┘    └─────────┘   ├──────────────────┤
│ Parametreler ├───────────────────────────────┤                  │
│  ─────○───   │  Analiz                       │  ƒ Matematiksel  │
│              │  Histogram │ KDF │ Transfer │ │    Bilgilendirme │
│ ▶ Uygula     │  Spektrum │ Profil │ Fark │   │                  │
│ Zincirle     │  Metrik Karşılaştırma         │                  │
│ Kaydet       │  ┌─────────────────────────┐  │                  │
└──────────────┴───────────────────────────────┴──────────────────┘
```

**Sol** — görüntü yükleme, kategori/fonksiyon seçimi, parametre kaydırıcıları.
**Orta üst** — girdi ve çıktı yan yana, altlarında piksel istatistiği.
**Orta alt** — yedi analiz sekmesi.
**Sağ üst** — bant istatistikleri, karşılaştırma metrikleri ve işleme altyapısı.
**Sağ alt** — seçili fonksiyonun matematiksel açıklaması.

### Görüntü yükleme

PNG, JPEG, TIFF/GeoTIFF, BMP, WebP desteklenir. **1080p (1920×1080) üstü
görüntüler** oranı korunarak Lanczos ile küçültülür — yerel işlemede yanıt
süresini öngörülebilir tutmak için.

Veri işlem boyunca `float32`, `[0,1]` aralığında, `(bant, satır, sütun)`
biçiminde tutulur.

### Zincirleme

`Zincirle` düğmesi filtreyi girdi yerine **mevcut çıktıya** uygular; böylece
çok adımlı işlem hatları kurulabilir (örn. medyan → CLAHE → unsharp mask).
`Sıfırla` çıktıyı temizler, girdiyi korur.

---

## Filtreler

| Kategori | Fonksiyon | Parametreler |
|---|---|---|
| Kenar İyileştirme | Laplacian | α |
| | Sobel | α |
| | Prewitt | α |
| | Roberts Cross | α |
| | Canny | σ, alt/üst eşik, α |
| | High-Pass | — |
| Gürültü Azaltma | Gaussian Blur | σ |
| | Median | pencere |
| | Bilateral | σ_s, σ_r, pencere |
| Kontrast | Histogram Equalization | — |
| | CLAHE | kırpma sınırı, blok |
| | Contrast Stretching | alt/üst yüzdelik |
| Parlaklık / Ton | Gamma Correction | γ |
| | Logarithmic Transform | c |
| Keskinleştirme | High-Boost / Unsharp | k, pencere |
| Pansharpening | Brovey | — |
| | IHS | — |
| | PCA | — |

Pansharpening yöntemleri **en az 2 bant** gerektirir; ilk bant pankromatik,
kalanlar çok bantlı veri olarak alınır.

---

## Analiz araçları

<!-- Analiz sekmelerinin görseli için:
     ![Analiz sekmeleri](docs/analysis.png) -->

| Sekme | Gösterdiği |
|---|---|
| **Histogram** | Girdi ve çıktının bant bazlı yoğunluk dağılımı |
| **Kümülatif Dağılım** | KDF eğrileri — kesikli girdi, düz çıktı |
| **Transfer Eğrisi** | Ampirik girdi→çıktı ton eşlemesi; noktasal filtrelerde teorik eğriyle örtüşür |
| **Frekans Spektrumu** | FFT'nin radyal ortalaması — bulanıklaştırma/keskinleştirme doğrudan okunur |
| **Satır Profili** | Orta satırın kesiti — kenar dikliği ve halo (overshoot) |
| **Fark Haritası** | Çıktı − girdi, ıraksak renk ölçeği + fark histogramı |
| **Metrik Karşılaştırma** | Ölçüt çubukları ve SSIM / korelasyon |

### Hesaplanan metrikler

Bant başına: min, maks, ortalama, medyan, standart sapma, değişim katsayısı,
çarpıklık, basıklık, Shannon entropisi, P2/P98 yüzdelikleri.

Karşılaştırma: **MSE**, **PSNR**, **SSIM**, Pearson korelasyonu, keskinlik
(ortalama gradyan büyüklüğü), entropi, kenar yoğunluğu ve standart sapma —
her biri girdi→çıktı yüzde değişimiyle.

> Kenar yoğunluğu girdi ve çıktı için **ortak bir eşik** kullanır. Her
> görüntünün kendi maksimumuna göre eşik alınsaydı, tek bir aykırı pikseli
> silen bir filtre kenar oranını sahte biçimde yükseltirdi.

---

## Matematiksel bilgilendirme

Sağ alt panel, seçili her fonksiyon için beş başlık gösterir:

- **Bağıntı** — kapalı formdaki tanım
- **Çekirdek / Dönüşüm** — konvolüsyon matrisi veya transfer eğrisi
- **Matematiksel anlam** — işlemin neden işe yaradığı
- **Parametreler** — her katsayının davranışa etkisi
- **Etki** — görüntüde gözlenen sonuç

Örneğin CLAHE için kırpma sınırının neden gürültüyü bastırdığı (transfer
eğrisinin eğimini sınırlaması), Sobel'in neden Prewitt'ten daha gürültü
dayanıklı olduğu (üçgen ağırlıklı ayrılabilir yumuşatma) ya da bilateral
süzgecin kenarları nasıl koruduğu (ton benzerliği çarpanının kenar ötesindeki
pikselleri ağırlıklandırmaması) burada açıklanır.

---

## Proje yapısı

```
main.py                 giriş noktası
ipf_gui/
  app.py                Tkinter arayüzü
  filters.py            filtre çekirdeği + kayıt (registry)
  analysis.py           metrikler ve grafik verisi
  explanations.py       matematiksel açıklamalar
  imageio.py            görüntü G/Ç, 1080p sınırı, görüntüleme germesi
```

### Komut satırı scriptleri

Depodaki özgün scriptler (`laplacian_enhancement.py`, `bilateral_filter.py`, …)
olduğu gibi durur ve `Image_HW2.tif` üzerinde bağımsız çalışır:

```bash
python run_all_filters.py       # hepsini çalıştır
python gaussian_blur_filter.py  # tek filtre
```

`ipf_gui/filters.py` aynı algoritmaları rasterio bağımlılığı olmadan, düz
NumPy dizileri üzerinde çalışacak biçimde yeniden paketler; böylece GUI hem
GeoTIFF hem de PNG/JPG girdilerini tek kod yolundan işler.

**Bilateral süzgeç** dışında algoritmalar birebir aynıdır. Özgün sürümdeki iç
içe Python döngüsü `O(H·W·k²)` idi ve 1080p görüntüde dakikalar sürüyordu;
GUI sürümü aynı matematiği pencere kaymaları üzerinden vektörleştirir. Çıktı
sayısal olarak özdeştir (maksimum mutlak fark ≈ 3×10⁻⁸).

---

## Notlar

- Görüntüleme için **%2–%98 yüzdelik germesi** uygulanır (üstteki onay
  kutusundan kapatılabilir). Bu yalnızca ekranı etkiler — **analiz her zaman
  ham veriyle** yapılır.
- Çıktı `.tif` olarak kaydedilirse rasterio ile `float32` yazılır ve varsa
  coğrafi profil korunur; diğer biçimlerde 8-bit olarak yazılır. Görüntü
  küçültülmüşse özgün `transform` artık geçerli olmadığından düşürülür.
- Filtreler ayrı bir iş parçacığında çalışır, arayüz donmaz.
