"""
IPF - Image Processing Functions
=================================
Filtre çekirdeği. Depodaki rasterio tabanlı scriptlerin algoritmaları,
burada doğrudan NumPy dizileri üzerinde çalışacak şekilde yeniden
paketlenmiştir. Böylece GUI hem GeoTIFF hem de PNG/JPG girdilerini
aynı kod yolundan işleyebilir.

Veri sözleşmesi:
    Girdi : float32 ndarray, şekil (B, H, W), değerler [0, 1] aralığında
    Çıktı : float32 ndarray, aynı şekil
"""

import numpy as np
from scipy.ndimage import (
    convolve,
    gaussian_filter,
    median_filter as nd_median_filter,
    uniform_filter,
)

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _per_band(func):
    """Tek bantlık bir fonksiyonu (B, H, W) yığını üzerinde çalıştırır."""
    def wrapper(data, *args, **kwargs):
        out = np.empty_like(data, dtype=np.float32)
        for b in range(data.shape[0]):
            out[b] = func(data[b].astype(np.float32), *args, **kwargs)
        return out
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def _normalize(band):
    """Bandı [0,1] aralığına taşır; (normalized, vmin, vmax) döndürür."""
    vmin, vmax = float(band.min()), float(band.max())
    if vmax == vmin:
        return band.copy(), vmin, vmax
    return (band - vmin) / (vmax - vmin), vmin, vmax


def _denormalize(norm, vmin, vmax):
    if vmax == vmin:
        return norm
    return norm * (vmax - vmin) + vmin


# ---------------------------------------------------------------------------
# 1. KENAR İYİLEŞTİRME (Edge Enhancement)
# ---------------------------------------------------------------------------

LAPLACIAN_KERNEL = np.array([[0, -1, 0],
                             [-1, 4, -1],
                             [0, -1, 0]], dtype=np.float32)

SOBEL_X = np.array([[-1, 0, 1],
                    [-2, 0, 2],
                    [-1, 0, 1]], dtype=np.float32)

SOBEL_Y = np.array([[-1, -2, -1],
                    [0, 0, 0],
                    [1, 2, 1]], dtype=np.float32)

PREWITT_X = np.array([[-1, 0, 1],
                      [-1, 0, 1],
                      [-1, 0, 1]], dtype=np.float32)

PREWITT_Y = np.array([[-1, -1, -1],
                      [0, 0, 0],
                      [1, 1, 1]], dtype=np.float32)

ROBERTS_X = np.array([[1, 0],
                      [0, -1]], dtype=np.float32)

ROBERTS_Y = np.array([[0, 1],
                      [-1, 0]], dtype=np.float32)

HIGHPASS_KERNEL = np.array([[-1, -1, -1],
                            [-1, 8, -1],
                            [-1, -1, -1]], dtype=np.float32) / 9.0


@_per_band
def laplacian_enhancement(band, alpha=0.5):
    """g = f + alpha * Laplacian(f)"""
    lap = convolve(band, LAPLACIAN_KERNEL, mode='reflect')
    return band + alpha * lap


@_per_band
def sobel_enhancement(band, alpha=0.5):
    """g = f + alpha * |grad_sobel(f)|"""
    gx = convolve(band, SOBEL_X, mode='reflect')
    gy = convolve(band, SOBEL_Y, mode='reflect')
    return band + alpha * np.sqrt(gx ** 2 + gy ** 2)


@_per_band
def prewitt_enhancement(band, alpha=0.5):
    """g = f + alpha * |grad_prewitt(f)|"""
    gx = convolve(band, PREWITT_X, mode='reflect')
    gy = convolve(band, PREWITT_Y, mode='reflect')
    return band + alpha * np.sqrt(gx ** 2 + gy ** 2)


@_per_band
def roberts_enhancement(band, alpha=0.5):
    """g = f + alpha * |grad_roberts(f)| (2x2 çapraz çekirdek)"""
    gx = convolve(band, ROBERTS_X, mode='reflect')
    gy = convolve(band, ROBERTS_Y, mode='reflect')
    return band + alpha * np.sqrt(gx ** 2 + gy ** 2)


@_per_band
def highpass_filter(band):
    """Yüksek geçiren 3x3 çekirdek ile konvolüsyon (yalnız kenar bileşeni)."""
    return convolve(band, HIGHPASS_KERNEL, mode='reflect')


@_per_band
def canny_edge_enhancement(band, sigma=1.0, low_threshold=0.1,
                           high_threshold=0.2, alpha=0.5):
    """
    Canny tabanlı kenar iyileştirme (depodaki basitleştirilmiş sürüm).
    Gauss yumuşatma -> Sobel gradyanı -> çift eşikleme -> ağırlıklı ekleme.
    """
    smoothed = gaussian_filter(band, sigma=sigma, mode='reflect')
    gx = convolve(smoothed, SOBEL_X, mode='reflect')
    gy = convolve(smoothed, SOBEL_Y, mode='reflect')
    magnitude = np.sqrt(gx ** 2 + gy ** 2)

    mag_max = magnitude.max()
    if mag_max > 0:
        magnitude = magnitude / mag_max

    strong = magnitude > high_threshold
    weak = (magnitude >= low_threshold) & (magnitude <= high_threshold)
    edges = strong.astype(np.float32) + 0.5 * weak.astype(np.float32)

    return band + alpha * edges * magnitude


# ---------------------------------------------------------------------------
# 2. GÜRÜLTÜ AZALTMA (Noise Reduction)
# ---------------------------------------------------------------------------

@_per_band
def gaussian_blur(band, sigma=1.0):
    """Gauss çekirdeği ile alçak geçiren süzgeç."""
    return gaussian_filter(band, sigma=sigma, mode='reflect')


@_per_band
def median_filter(band, size=3):
    """Sıralama tabanlı (doğrusal olmayan) medyan süzgeci."""
    return nd_median_filter(band, size=int(size), mode='reflect')


@_per_band
def bilateral_filter(band, sigma_spatial=1.5, sigma_intensity=0.1,
                     window_size=5):
    """
    Kenar koruyan bilateral süzgeç.

    Depodaki iç içe Python döngüsü O(H*W*k^2) idi ve 1080p görüntüde
    dakikalar sürüyordu. Burada aynı matematik, pencere kaymaları üzerinden
    vektörleştirilmiştir: k^2 kaydırmanın her biri için tüm piksellere aynı
    anda NumPy işlemi uygulanır. Sonuç sayısal olarak özdeştir.
    """
    size = int(window_size)
    if size % 2 == 0:
        size += 1
    pad = size // 2

    norm, vmin, vmax = _normalize(band)
    if vmax == vmin:
        return band

    padded = np.pad(norm, pad, mode='reflect')

    num = np.zeros_like(norm, dtype=np.float32)
    den = np.zeros_like(norm, dtype=np.float32)
    h, w = norm.shape

    inv_s = 1.0 / (2.0 * sigma_spatial ** 2)
    inv_i = 1.0 / (2.0 * sigma_intensity ** 2)

    for dy in range(-pad, pad + 1):
        for dx in range(-pad, pad + 1):
            shifted = padded[pad + dy: pad + dy + h,
                             pad + dx: pad + dx + w]
            w_spatial = np.exp(-(dx * dx + dy * dy) * inv_s)
            w_intensity = np.exp(-((shifted - norm) ** 2) * inv_i)
            weight = w_spatial * w_intensity
            num += shifted * weight
            den += weight

    filtered = np.where(den > 0, num / np.maximum(den, 1e-12), norm)
    return _denormalize(filtered, vmin, vmax)


# ---------------------------------------------------------------------------
# 3. KONTRAST İYİLEŞTİRME (Contrast Enhancement)
# ---------------------------------------------------------------------------

@_per_band
def histogram_equalization(band):
    """Kümülatif dağılım fonksiyonunu transfer eğrisi olarak kullanır."""
    norm, vmin, vmax = _normalize(band)
    if vmax == vmin:
        return band

    hist, bins = np.histogram(norm.ravel(), bins=256, range=(0.0, 1.0))
    cdf = hist.cumsum()
    if cdf[-1] == 0:
        return band
    cdf_norm = cdf / cdf[-1]

    equalized = np.interp(norm.ravel(), bins[:-1], cdf_norm).reshape(band.shape)
    return _denormalize(equalized, vmin, vmax)


@_per_band
def clahe(band, clip_limit=2.0, tile_size=8):
    """
    Kontrast sınırlı uyarlanır histogram eşitleme.
    Görüntü tile_size x tile_size piksellik bloklara bölünür, her bloğun
    histogramı clip_limit ile budanır, artan kütle eşit dağıtılır.
    """
    rows, cols = band.shape
    norm, vmin, vmax = _normalize(band)
    if vmax == vmin:
        return band

    ts = max(int(tile_size), 2)
    output = np.zeros_like(norm, dtype=np.float32)

    n_tile_rows = int(np.ceil(rows / ts))
    n_tile_cols = int(np.ceil(cols / ts))

    for i in range(n_tile_rows):
        r0, r1 = i * ts, min((i + 1) * ts, rows)
        for j in range(n_tile_cols):
            c0, c1 = j * ts, min((j + 1) * ts, cols)
            tile = norm[r0:r1, c0:c1]
            if tile.size == 0:
                continue

            hist, bins = np.histogram(tile.ravel(), bins=256, range=(0.0, 1.0))
            limit = clip_limit * tile.size / 256.0
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit) + excess / 256.0

            cdf = hist.cumsum()
            if cdf[-1] <= 0:
                output[r0:r1, c0:c1] = tile
                continue
            cdf_norm = cdf / cdf[-1]

            output[r0:r1, c0:c1] = np.interp(
                tile.ravel(), bins[:-1], cdf_norm).reshape(tile.shape)

    return _denormalize(output, vmin, vmax)


@_per_band
def contrast_stretching(band, p_low=2.0, p_high=98.0):
    """Yüzdelik kırpma ile doğrusal kontrast germe."""
    lo = np.percentile(band, p_low)
    hi = np.percentile(band, p_high)
    if hi == lo:
        return band

    omin, omax = float(band.min()), float(band.max())
    stretched = (band - lo) / (hi - lo)
    stretched = stretched * (omax - omin) + omin
    return np.clip(stretched, omin, omax)


# ---------------------------------------------------------------------------
# 4. PARLAKLIK / TON EĞRİSİ (Brightness)
# ---------------------------------------------------------------------------

@_per_band
def gamma_correction(band, gamma=1.2):
    """s = c * r^gamma (normalize edilmiş alanda)."""
    norm, vmin, vmax = _normalize(band)
    if vmax == vmin:
        return band
    return _denormalize(np.power(np.clip(norm, 0, 1), gamma), vmin, vmax)


@_per_band
def log_transform(band, c=1.0):
    """s = c * log(1 + r); dinamik aralık sıkıştırma."""
    shifted = band - band.min() + 1.0
    logged = c * np.log(1.0 + shifted)
    lmin, lmax = float(logged.min()), float(logged.max())
    if lmax == lmin:
        return band
    norm = (logged - lmin) / (lmax - lmin)
    return _denormalize(norm, float(band.min()), float(band.max()))


# ---------------------------------------------------------------------------
# 5. KESKİNLEŞTİRME (Sharpening)
# ---------------------------------------------------------------------------

@_per_band
def highboost_unsharp(band, k=1.5, size=3):
    """
    Maskeyle keskinleştirme / yüksek destekli süzgeç.
    mask = f - blur(f);  g = f + k * mask
    k = 1 -> unsharp masking, k > 1 -> high-boost.
    """
    blurred = uniform_filter(band, size=int(size), mode='reflect')
    return band + k * (band - blurred)


# ---------------------------------------------------------------------------
# 6. PANSHARPENING
# ---------------------------------------------------------------------------

def _split_pan_ms(data):
    """İlk bandı pankromatik, kalanını çok bantlı veri olarak ayırır."""
    if data.shape[0] > 1:
        return data[0], data[1:]
    return data[0], data


def pansharpen_brovey(data):
    """MS_i' = (MS_i / I) * PAN, I = ortalama(MS)."""
    pan, ms = _split_pan_ms(data)
    intensity = np.mean(ms, axis=0)
    intensity = np.where(np.abs(intensity) < 1e-8, 1e-8, intensity)
    out = np.empty_like(ms, dtype=np.float32)
    for i in range(ms.shape[0]):
        out[i] = (ms[i] / intensity) * pan
    return out


def pansharpen_ihs(data):
    """Yoğunluk bileşenini PAN ile değiştirir: MS_i' = MS_i + (PAN - I)."""
    pan, ms = _split_pan_ms(data)
    while ms.shape[0] < 3:
        ms = np.concatenate([ms, ms[:1]], axis=0)
    intensity = (ms[0] + ms[1] + ms[2]) / 3.0
    diff = pan - intensity
    return (ms + diff).astype(np.float32)


def pansharpen_pca(data):
    """Birinci temel bileşeni PAN ile değiştirip geri dönüştürür."""
    pan, ms = _split_pan_ms(data)
    if ms.shape[0] < 2:
        return ms.astype(np.float32)

    bands, rows, cols = ms.shape
    flat = ms.reshape(bands, -1).T.astype(np.float64)

    cov = np.cov(flat.T)
    eigenvals, eigenvecs = np.linalg.eigh(cov)
    order = np.argsort(eigenvals)[::-1]
    eigenvecs = eigenvecs[:, order]

    pcs = flat @ eigenvecs

    # PAN'ı PC1'in istatistiklerine uyarla (histogram eşleme)
    pc1 = pcs[:, 0]
    pan_flat = pan.ravel().astype(np.float64)
    pan_std = pan_flat.std()
    if pan_std > 1e-12:
        pan_matched = ((pan_flat - pan_flat.mean()) / pan_std
                       * pc1.std() + pc1.mean())
    else:
        pan_matched = pan_flat
    pcs[:, 0] = pan_matched

    back = pcs @ eigenvecs.T
    return back.T.reshape(bands, rows, cols).astype(np.float32)


# ---------------------------------------------------------------------------
# Filtre kaydı (registry)
# ---------------------------------------------------------------------------
# Parametre biçimi: (ad, etiket, tür, varsayılan, min, max, adım)

FILTERS = {
    # --- Kenar iyileştirme ---
    "laplacian": {
        "name": "Laplacian Enhancement",
        "category": "Kenar İyileştirme",
        "func": laplacian_enhancement,
        "params": [("alpha", "α (kenar ağırlığı)", float, 0.5, 0.0, 3.0, 0.05)],
    },
    "sobel": {
        "name": "Sobel Enhancement",
        "category": "Kenar İyileştirme",
        "func": sobel_enhancement,
        "params": [("alpha", "α (kenar ağırlığı)", float, 0.5, 0.0, 3.0, 0.05)],
    },
    "prewitt": {
        "name": "Prewitt Enhancement",
        "category": "Kenar İyileştirme",
        "func": prewitt_enhancement,
        "params": [("alpha", "α (kenar ağırlığı)", float, 0.5, 0.0, 3.0, 0.05)],
    },
    "roberts": {
        "name": "Roberts Cross Enhancement",
        "category": "Kenar İyileştirme",
        "func": roberts_enhancement,
        "params": [("alpha", "α (kenar ağırlığı)", float, 0.5, 0.0, 3.0, 0.05)],
    },
    "canny": {
        "name": "Canny Edge Enhancement",
        "category": "Kenar İyileştirme",
        "func": canny_edge_enhancement,
        "params": [
            ("sigma", "σ (Gauss yumuşatma)", float, 1.0, 0.1, 5.0, 0.1),
            ("low_threshold", "Alt eşik", float, 0.1, 0.0, 1.0, 0.01),
            ("high_threshold", "Üst eşik", float, 0.2, 0.0, 1.0, 0.01),
            ("alpha", "α (kenar ağırlığı)", float, 0.5, 0.0, 3.0, 0.05),
        ],
    },
    "highpass": {
        "name": "High-Pass Filter",
        "category": "Kenar İyileştirme",
        "func": highpass_filter,
        "params": [],
    },

    # --- Gürültü azaltma ---
    "gaussian": {
        "name": "Gaussian Blur",
        "category": "Gürültü Azaltma",
        "func": gaussian_blur,
        "params": [("sigma", "σ (yayılım)", float, 1.0, 0.1, 10.0, 0.1)],
    },
    "median": {
        "name": "Median Filter",
        "category": "Gürültü Azaltma",
        "func": median_filter,
        "params": [("size", "Pencere boyutu", int, 3, 3, 15, 2)],
    },
    "bilateral": {
        "name": "Bilateral Filter",
        "category": "Gürültü Azaltma",
        "func": bilateral_filter,
        "params": [
            ("sigma_spatial", "σ_s (uzamsal)", float, 1.5, 0.5, 10.0, 0.1),
            ("sigma_intensity", "σ_r (yoğunluk)", float, 0.1, 0.01, 1.0, 0.01),
            ("window_size", "Pencere boyutu", int, 5, 3, 15, 2),
        ],
    },

    # --- Kontrast ---
    "histeq": {
        "name": "Histogram Equalization",
        "category": "Kontrast İyileştirme",
        "func": histogram_equalization,
        "params": [],
    },
    "clahe": {
        "name": "CLAHE (Adaptive Hist. Eq.)",
        "category": "Kontrast İyileştirme",
        "func": clahe,
        "params": [
            ("clip_limit", "Kırpma sınırı", float, 2.0, 1.0, 10.0, 0.1),
            ("tile_size", "Blok boyutu", int, 8, 2, 128, 1),
        ],
    },
    "stretch": {
        "name": "Contrast Stretching",
        "category": "Kontrast İyileştirme",
        "func": contrast_stretching,
        "params": [
            ("p_low", "Alt yüzdelik", float, 2.0, 0.0, 49.0, 0.5),
            ("p_high", "Üst yüzdelik", float, 98.0, 51.0, 100.0, 0.5),
        ],
    },

    # --- Parlaklık ---
    "gamma": {
        "name": "Gamma Correction",
        "category": "Parlaklık / Ton",
        "func": gamma_correction,
        "params": [("gamma", "γ", float, 1.2, 0.1, 5.0, 0.05)],
    },
    "log": {
        "name": "Logarithmic Transform",
        "category": "Parlaklık / Ton",
        "func": log_transform,
        "params": [("c", "c (ölçek)", float, 1.0, 0.1, 5.0, 0.1)],
    },

    # --- Keskinleştirme ---
    "highboost": {
        "name": "High-Boost / Unsharp Mask",
        "category": "Keskinleştirme",
        "func": highboost_unsharp,
        "params": [
            ("k", "k (destek katsayısı)", float, 1.5, 0.0, 5.0, 0.1),
            ("size", "Bulanıklık penceresi", int, 3, 3, 15, 2),
        ],
    },

    # --- Pansharpening ---
    "brovey": {
        "name": "Brovey Pansharpening",
        "category": "Pansharpening",
        "func": pansharpen_brovey,
        "params": [],
        "multiband_only": True,
    },
    "ihs": {
        "name": "IHS Pansharpening",
        "category": "Pansharpening",
        "func": pansharpen_ihs,
        "params": [],
        "multiband_only": True,
    },
    "pca": {
        "name": "PCA Pansharpening",
        "category": "Pansharpening",
        "func": pansharpen_pca,
        "params": [],
        "multiband_only": True,
    },
}


CATEGORY_ORDER = [
    "Kenar İyileştirme",
    "Gürültü Azaltma",
    "Kontrast İyileştirme",
    "Parlaklık / Ton",
    "Keskinleştirme",
    "Pansharpening",
]


def apply_filter(key, data, params=None):
    """Kayıttaki filtreyi (B,H,W) float32 verisine uygular."""
    spec = FILTERS[key]
    params = params or {}
    return spec["func"](data.astype(np.float32), **params)
