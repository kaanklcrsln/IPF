"""
IPF - Görüntü giriş/çıkış katmanı.

Görüntüleri (B, H, W) float32 [0,1] biçimine getirir ve geri yazar.
GeoTIFF için rasterio varsa kullanılır; yoksa Pillow'a düşülür.
1080p (1920x1080) üstü görüntüler otomatik olarak küçültülür — işlem
kullanıcının kendi makinesinde yapıldığı için bu sınır yanıt süresini
öngörülebilir tutar.
"""

import os
import numpy as np
from PIL import Image

try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# 1080p sınırı: toplam piksel sayısı üzerinden uygulanır, böylece
# dikey (portrait) görüntüler de adil biçimde ölçeklenir.
MAX_PIXELS = 1920 * 1080

RASTER_EXT = {".tif", ".tiff"}
PIL_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ppm", ".pgm"}


class ImageData:
    """Yüklenmiş bir görüntünün taşıyıcısı."""

    def __init__(self, data, path, orig_shape, resized, mode, profile=None):
        self.data = data              # (B, H, W) float32, [0,1]
        self.path = path
        self.orig_shape = orig_shape  # (B, H, W) — küçültme öncesi
        self.resized = resized
        self.mode = mode              # "rasterio" | "pillow"
        self.profile = profile        # GeoTIFF profili (varsa)

    @property
    def bands(self):
        return self.data.shape[0]

    @property
    def height(self):
        return self.data.shape[1]

    @property
    def width(self):
        return self.data.shape[2]

    def summary(self):
        ob, oh, ow = self.orig_shape
        lines = [
            f"Dosya       : {os.path.basename(self.path)}",
            f"Okuyucu     : {self.mode}",
            f"Özgün boyut : {ow} x {oh} piksel, {ob} bant",
            f"İşlenen     : {self.width} x {self.height} piksel, {self.bands} bant",
        ]
        if self.resized:
            lines.append("Not         : 1080p sınırı için küçültüldü")
        lines.append(f"Piksel sayısı: {self.width * self.height:,}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Yükleme
# ---------------------------------------------------------------------------

def load_image(path, max_pixels=MAX_PIXELS):
    """Görüntüyü (B,H,W) float32 [0,1] olarak yükler."""
    ext = os.path.splitext(path)[1].lower()

    if ext in RASTER_EXT and HAS_RASTERIO:
        data, profile = _read_rasterio(path)
        mode = "rasterio"
    else:
        data, profile = _read_pillow(path)
        mode = "pillow"

    orig_shape = data.shape
    data, resized = _limit_size(data, max_pixels)
    data = _to_unit(data)

    return ImageData(data, path, orig_shape, resized, mode, profile)


def _read_rasterio(path):
    with rasterio.open(path) as src:
        data = src.read().astype(np.float32)
        profile = src.profile.copy()
    return data, profile


def _read_pillow(path):
    img = Image.open(path)

    # Paletli ve alfa kanallı biçimleri normalize et
    if img.mode == "P":
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        img = img.convert("RGB")
    elif img.mode == "LA":
        img = img.convert("L")
    elif img.mode not in ("L", "RGB", "I", "I;16", "F"):
        img = img.convert("RGB")

    arr = np.array(img).astype(np.float32)
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]          # (1, H, W)
    else:
        arr = np.transpose(arr, (2, 0, 1))  # (B, H, W)
    return arr, None


def _limit_size(data, max_pixels):
    """Toplam piksel sayısı sınırı aşıyorsa oranı koruyarak küçültür."""
    _, h, w = data.shape
    if h * w <= max_pixels:
        return data, False

    scale = np.sqrt(max_pixels / float(h * w))
    new_h = max(int(h * scale), 1)
    new_w = max(int(w * scale), 1)

    out = np.empty((data.shape[0], new_h, new_w), dtype=np.float32)
    for b in range(data.shape[0]):
        band = data[b]
        lo, hi = float(band.min()), float(band.max())
        # Pillow'a vermek için geçici olarak [0,255]'e taşı
        if hi - lo < 1e-12:
            scaled = np.zeros_like(band)
        else:
            scaled = (band - lo) / (hi - lo) * 255.0
        im = Image.fromarray(scaled.astype(np.uint8))
        im = im.resize((new_w, new_h), Image.LANCZOS)
        res = np.array(im).astype(np.float32) / 255.0
        out[b] = res * (hi - lo) + lo if hi - lo >= 1e-12 else lo

    return out, True


def _to_unit(data):
    """Tüm bantları ortak ölçekle [0,1] aralığına getirir."""
    lo, hi = float(data.min()), float(data.max())
    if hi - lo < 1e-12:
        return np.zeros_like(data, dtype=np.float32)
    return ((data - lo) / (hi - lo)).astype(np.float32)


# ---------------------------------------------------------------------------
# Görselleştirme
# ---------------------------------------------------------------------------

def to_display(data, stretch=True, p_low=2.0, p_high=98.0):
    """
    (B,H,W) veriyi ekranda gösterilebilir uint8 diziye çevirir.
    3+ bant → RGB (ilk üç bant), aksi halde gri tonlama.

    stretch=True ise %2-%98 yüzdelik germesi uygulanır; bu yalnızca
    GÖRÜNTÜLEME içindir, analiz her zaman ham veriyle yapılır.
    """
    if data.shape[0] >= 3:
        arr = np.transpose(data[:3], (1, 2, 0))
    else:
        arr = data[0]

    arr = arr.astype(np.float32)

    if stretch:
        lo = np.percentile(arr, p_low)
        hi = np.percentile(arr, p_high)
    else:
        lo, hi = float(arr.min()), float(arr.max())

    if hi - lo < 1e-12:
        norm = np.zeros_like(arr)
    else:
        norm = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)

    return (norm * 255.0).astype(np.uint8)


# ---------------------------------------------------------------------------
# Kaydetme
# ---------------------------------------------------------------------------

def save_image(path, data, source=None, stretch=True):
    """
    İşlenmiş veriyi diske yazar.

    .tif/.tiff  : rasterio varsa float32 olarak, coğrafi profil korunarak
    diğer       : 8-bit PNG/JPG olarak (görüntüleme germesi uygulanır)
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in RASTER_EXT and HAS_RASTERIO:
        _write_rasterio(path, data, source)
        return path

    disp = to_display(data, stretch=stretch)
    Image.fromarray(disp).save(path)
    return path


def _write_rasterio(path, data, source):
    profile = {}
    if source is not None and source.profile is not None:
        profile = source.profile.copy()

    profile.update(
        driver="GTiff",
        count=data.shape[0],
        height=data.shape[1],
        width=data.shape[2],
        dtype="float32",
    )
    # Küçültme yapıldıysa özgün geotransform artık geçerli değil
    if source is not None and source.resized:
        profile.pop("transform", None)

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data.astype(np.float32))
