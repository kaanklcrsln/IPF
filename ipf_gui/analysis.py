"""
IPF - Analiz araçları.

Girdi/çıktı görüntülerinden istatistik ve karşılaştırma metrikleri
hesaplar; matplotlib figürlerini doldurur.

Tüm fonksiyonlar (B, H, W) float32 dizileri bekler.
"""

import numpy as np
from scipy.ndimage import convolve, uniform_filter

SOBEL_X = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
SOBEL_Y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)


# ---------------------------------------------------------------------------
# Tek görüntü istatistikleri
# ---------------------------------------------------------------------------

def band_stats(band):
    """Tek bir bandın betimsel istatistikleri."""
    b = band.ravel()
    mean = float(b.mean())
    std = float(b.std())
    return {
        "min": float(b.min()),
        "max": float(b.max()),
        "mean": mean,
        "median": float(np.median(b)),
        "std": std,
        "var": float(b.var()),
        # Değişim katsayısı: göreli kontrast ölçüsü
        "cv": std / mean if abs(mean) > 1e-12 else 0.0,
        "skew": _skewness(b),
        "kurtosis": _kurtosis(b),
        "entropy": shannon_entropy(band),
        "p2": float(np.percentile(b, 2)),
        "p98": float(np.percentile(b, 98)),
    }


def _skewness(x):
    """Üçüncü standart moment — histogramın asimetrisi."""
    std = x.std()
    if std < 1e-12:
        return 0.0
    return float((((x - x.mean()) / std) ** 3).mean())


def _kurtosis(x):
    """Dördüncü standart moment (fazlalık basıklık)."""
    std = x.std()
    if std < 1e-12:
        return 0.0
    return float((((x - x.mean()) / std) ** 4).mean() - 3.0)


def shannon_entropy(band, bins=256):
    """
    H = -Σ p_i log2(p_i)

    Görüntünün bilgi içeriği (bit/piksel). Düzgün dağılmış histogram
    maksimum entropiye (8 bit) yaklaşır.
    """
    hist, _ = np.histogram(band.ravel(), bins=bins)
    p = hist.astype(np.float64)
    total = p.sum()
    if total <= 0:
        return 0.0
    p = p / total
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def gradient_magnitude(band):
    """Sobel gradyan büyüklüğü — keskinlik analizleri için."""
    gx = convolve(band.astype(np.float32), SOBEL_X, mode='reflect')
    gy = convolve(band.astype(np.float32), SOBEL_Y, mode='reflect')
    return np.sqrt(gx ** 2 + gy ** 2)


def sharpness_index(band):
    """
    Ortalama gradyan büyüklüğü — algılanan keskinliğin vekil ölçüsü.
    Keskinleştirme filtrelerinde artar, bulanıklaştırmada düşer.
    """
    return float(gradient_magnitude(band).mean())


def edge_density(band, threshold=None, threshold_ratio=0.1):
    """
    Gradyan büyüklüğü bir eşiği aşan piksellerin yüzdesi.

    threshold verilmezse eşik bandın kendi maksimum gradyanına göre
    belirlenir. Girdi ile çıktıyı karşılaştırırken bu yanıltıcıdır:
    filtre tek bir aykırı pikseli silerse maksimum düşer, eşik de
    onunla birlikte düşer ve kenar oranı sahte biçimde yükselir.
    Bu yüzden compare() her iki görüntü için ORTAK bir eşik geçirir.
    """
    g = gradient_magnitude(band)
    if threshold is None:
        gmax = g.max()
        if gmax <= 0:
            return 0.0
        threshold = threshold_ratio * gmax
    return float((g > threshold).mean() * 100.0)


# ---------------------------------------------------------------------------
# Karşılaştırma metrikleri (input vs output)
# ---------------------------------------------------------------------------

def mse(a, b):
    """Ortalama karesel hata."""
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


def psnr(a, b, data_range=1.0):
    """
    PSNR = 10 · log10(MAX² / MSE)   [dB]

    Yüksek değer, çıktının girdiye yakın olduğunu gösterir.
    Bir kalite ölçüsü değil, bir 'ne kadar değişti' ölçüsüdür:
    güçlü bir iyileştirme filtresinde PSNR düşer.
    """
    e = mse(a, b)
    if e <= 1e-20:
        return float('inf')
    return float(10.0 * np.log10((data_range ** 2) / e))


def ssim(a, b, data_range=1.0, win=7):
    """
    Yapısal Benzerlik İndeksi (Wang ve ark., 2004).

    SSIM = [(2·μx·μy + C1)(2·σxy + C2)] / [(μx² + μy² + C1)(σx² + σy² + C2)]

    Parlaklık, kontrast ve yapı benzerliğini birlikte ölçer.
    Burada Gauss ağırlığı yerine kutu penceresi kullanılmıştır.
    Sonuç [-1, 1] aralığındadır; 1 tam özdeşlik demektir.
    """
    a = a.astype(np.float64)
    b = b.astype(np.float64)

    C1 = (0.01 * data_range) ** 2
    C2 = (0.03 * data_range) ** 2

    mu_a = uniform_filter(a, size=win, mode='reflect')
    mu_b = uniform_filter(b, size=win, mode='reflect')

    mu_a_sq, mu_b_sq, mu_ab = mu_a ** 2, mu_b ** 2, mu_a * mu_b

    sigma_a = uniform_filter(a * a, size=win, mode='reflect') - mu_a_sq
    sigma_b = uniform_filter(b * b, size=win, mode='reflect') - mu_b_sq
    sigma_ab = uniform_filter(a * b, size=win, mode='reflect') - mu_ab

    num = (2 * mu_ab + C1) * (2 * sigma_ab + C2)
    den = (mu_a_sq + mu_b_sq + C1) * (sigma_a + sigma_b + C2)

    ssim_map = np.divide(num, den, out=np.ones_like(num), where=np.abs(den) > 1e-12)
    return float(np.mean(ssim_map))


def correlation(a, b):
    """Pearson korelasyon katsayısı — yapısal ilişkinin korunumu."""
    x = a.ravel().astype(np.float64)
    y = b.ravel().astype(np.float64)
    sx, sy = x.std(), y.std()
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return float(np.mean((x - x.mean()) * (y - y.mean())) / (sx * sy))


def compare(src, dst):
    """Girdi ve çıktı için özet karşılaştırma sözlüğü."""
    # Bant sayıları farklıysa (pansharpening) ortak sayıda banda bak
    n = min(src.shape[0], dst.shape[0])
    a = src[:n]
    b = dst[:n]

    # Metrikler için ortak [0,1] ölçeğine getir
    a_n = _to_unit(a)
    b_n = _to_unit(b)

    # Kenar yoğunluğu için ortak eşik: girdinin gradyan maksimumunun
    # %10'u. Aynı eşik her iki görüntüye uygulanmazsa karşılaştırma
    # anlamsızlaşır (bkz. edge_density belgesi).
    edge_thr = 0.1 * max(
        (float(gradient_magnitude(a_n[i]).max()) for i in range(n)),
        default=0.0)
    if edge_thr <= 0:
        edge_thr = None

    return {
        "mse": mse(a_n, b_n),
        "psnr": psnr(a_n, b_n),
        "ssim": float(np.mean([ssim(a_n[i], b_n[i]) for i in range(n)])),
        "corr": correlation(a_n, b_n),
        "sharpness_in": float(np.mean([sharpness_index(a_n[i]) for i in range(n)])),
        "sharpness_out": float(np.mean([sharpness_index(b_n[i]) for i in range(n)])),
        "entropy_in": float(np.mean([shannon_entropy(a_n[i]) for i in range(n)])),
        "entropy_out": float(np.mean([shannon_entropy(b_n[i]) for i in range(n)])),
        "edges_in": float(np.mean(
            [edge_density(a_n[i], threshold=edge_thr) for i in range(n)])),
        "edges_out": float(np.mean(
            [edge_density(b_n[i], threshold=edge_thr) for i in range(n)])),
        "std_in": float(a_n.std()),
        "std_out": float(b_n.std()),
        "mean_in": float(a_n.mean()),
        "mean_out": float(b_n.mean()),
    }


def _to_unit(arr):
    """Diziyi [0,1] aralığına ölçekler (metrik karşılaştırması için)."""
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-12:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


# ---------------------------------------------------------------------------
# Grafik verisi hazırlayıcıları
# ---------------------------------------------------------------------------

def histogram_data(band, bins=256):
    """Histogram sayımları ve kutu merkezleri."""
    hist, edges = np.histogram(band.ravel(), bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    return centers, hist


def cdf_data(band, bins=256):
    """Kümülatif dağılım fonksiyonu (normalize)."""
    centers, hist = histogram_data(band, bins)
    cdf = hist.cumsum().astype(np.float64)
    if cdf[-1] > 0:
        cdf /= cdf[-1]
    return centers, cdf


def transfer_curve(src_band, dst_band, bins=128):
    """
    Girdi yoğunluğuna karşı ortalama çıktı yoğunluğu.
    Filtrenin fiilen uyguladığı ton eğrisini ampirik olarak ortaya çıkarır;
    noktasal filtrelerde (gama, log, histogram eşitleme) teorik eğriye
    birebir oturur.
    """
    x = src_band.ravel()
    y = dst_band.ravel()

    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.array([lo]), np.array([float(y.mean())])

    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(x, edges) - 1, 0, bins - 1)

    sums = np.bincount(idx, weights=y, minlength=bins)
    counts = np.bincount(idx, minlength=bins)

    valid = counts > 0
    centers = ((edges[:-1] + edges[1:]) / 2.0)[valid]
    means = sums[valid] / counts[valid]
    return centers, means


def radial_spectrum(band, n_bins=128):
    """
    2B Fourier genlik spektrumunun radyal ortalaması.

    Uzamsal frekansa karşı enerji dağılımını verir. Alçak geçiren
    filtreler yüksek frekans kuyruğunu bastırır, keskinleştirme
    filtreleri yükseltir — grafikte doğrudan görülür.
    """
    f = np.fft.fftshift(np.fft.fft2(band.astype(np.float64)))
    mag = np.abs(f)

    h, w = band.shape
    cy, cx = h / 2.0, w / 2.0
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)

    r_max = min(cy, cx)
    if r_max < 1:
        return np.array([0.0]), np.array([0.0])

    bins = np.linspace(0, r_max, n_bins + 1)
    idx = np.clip(np.digitize(r.ravel(), bins) - 1, 0, n_bins - 1)

    sums = np.bincount(idx, weights=mag.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)

    valid = counts > 0
    # Normalize frekans: 0 = DC, 0.5 = Nyquist
    freqs = ((bins[:-1] + bins[1:]) / 2.0)[valid] / (2.0 * r_max)
    power = sums[valid] / counts[valid]
    return freqs, power


def row_profile(band, row=None):
    """Tek bir satırın yoğunluk profili — kenar keskinliğinin kesiti."""
    if row is None:
        row = band.shape[0] // 2
    row = int(np.clip(row, 0, band.shape[0] - 1))
    return np.arange(band.shape[1]), band[row].copy()


def difference_map(src, dst):
    """
    Çıktı ile girdi arasındaki işaretli fark (ilk ortak bant).
    Filtrenin nerede ve ne kadar müdahale ettiğini gösterir.
    """
    n = min(src.shape[0], dst.shape[0])
    a = _to_unit(src[:n]).mean(axis=0)
    b = _to_unit(dst[:n]).mean(axis=0)
    return b - a


METRIC_LABELS = {
    "mse": ("MSE", "Ortalama karesel hata — girdiye göre toplam sapma"),
    "psnr": ("PSNR (dB)", "Tepe sinyal/gürültü oranı — yüksekse girdiye yakın"),
    "ssim": ("SSIM", "Yapısal benzerlik — 1.0 tam özdeşlik"),
    "corr": ("Korelasyon", "Pearson r — yapısal ilişkinin korunumu"),
    "sharpness_out": ("Keskinlik", "Ortalama gradyan büyüklüğü"),
    "entropy_out": ("Entropi (bit)", "Shannon bilgi içeriği"),
    "edges_out": ("Kenar yoğ. (%)", "Güçlü gradyanlı piksel oranı"),
    "std_out": ("Std. sapma", "Küresel kontrast ölçüsü"),
}
