"""
IPF - Image Processing Functions
Tkinter tabanlı grafik arayüz.

Yerleşim
--------
  Sol panel      : dosya yükleme, filtre seçimi, parametreler
  Üst orta       : girdi ve çıktı görüntüleri yan yana
  Alt orta       : analiz sekmeleri (histogram, KDF, spektrum, profil, fark)
  Sağ üst        : istatistik ve metrik tablosu, altyapı/pipeline özeti
  Sağ alt        : seçili fonksiyonun matematiksel açıklaması

İşleme tamamen yereldir; hiçbir veri dışarı gönderilmez.
"""

import os
import sys
import threading
import time
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

# Paket içinden veya doğrudan çalıştırmayı destekle
try:
    from . import filters, analysis, imageio, explanations
except ImportError:  # python ipf_gui/app.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ipf_gui import filters, analysis, imageio, explanations


# ---------------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------------

BG        = "#1e1f26"
BG_PANEL  = "#262832"
BG_INPUT  = "#31333f"
FG        = "#e4e6ef"
FG_DIM    = "#9aa0b4"
ACCENT    = "#5b9dd9"
ACCENT_2  = "#d98f5b"
OK        = "#6bbf7b"
WARN      = "#d9695b"
FONT      = ("Segoe UI", 9)
FONT_B    = ("Segoe UI", 9, "bold")
FONT_H    = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 9)

PLOT_STYLE = {
    "figure.facecolor": BG_PANEL,
    "axes.facecolor": BG_PANEL,
    "axes.edgecolor": "#4a4d5e",
    "axes.labelcolor": FG_DIM,
    "axes.titlecolor": FG,
    "text.color": FG,
    "xtick.color": FG_DIM,
    "ytick.color": FG_DIM,
    "grid.color": "#3a3d4d",
    "figure.dpi": 96,
}


class IPFApp:

    def __init__(self, root):
        self.root = root
        self.root.title("IPF — Image Processing Functions")
        self.root.minsize(1180, 720)
        self.root.configure(bg=BG)
        self._fit_to_screen()

        # Durum
        self.source = None        # ImageData
        self.result = None        # (B,H,W) float32
        self.current_key = None
        self.param_widgets = {}
        self.busy = False
        self.last_elapsed = 0.0

        self._photo_in = None     # GC koruması
        self._photo_out = None

        self._setup_style()
        self._build_layout()
        self._populate_filters()
        self._set_status("Hazır — bir görüntü yükleyin.")

    def _fit_to_screen(self):
        """Pencereyi ekrana sığdırıp ortalar.

        Sabit bir geometri, küçük ekranlarda sağ paneli görünür alanın
        dışına taşıyordu. Tercih edilen boyut ekranın %92'si ile
        sınırlanır.
        """
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        w = min(1680, int(sw * 0.92))
        h = min(980, int(sh * 0.92))
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2 - 20, 0)

        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Dar ekranlarda yan panelleri daralt
        self.left_w = 290 if w >= 1500 else 250
        self.right_w = 400 if w >= 1500 else 330

    # ------------------------------------------------------------------
    # Stil
    # ------------------------------------------------------------------

    def _setup_style(self):
        matplotlib.rcParams.update(PLOT_STYLE)

        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass

        s.configure(".", background=BG_PANEL, foreground=FG, font=FONT)
        s.configure("TFrame", background=BG_PANEL)
        s.configure("Dark.TFrame", background=BG)
        s.configure("TLabel", background=BG_PANEL, foreground=FG, font=FONT)
        s.configure("Dim.TLabel", background=BG_PANEL, foreground=FG_DIM)
        s.configure("Head.TLabel", background=BG_PANEL, foreground=ACCENT,
                    font=FONT_H)
        s.configure("TLabelframe", background=BG_PANEL, foreground=ACCENT,
                    bordercolor="#3a3d4d")
        s.configure("TLabelframe.Label", background=BG_PANEL,
                    foreground=ACCENT, font=FONT_B)

        s.configure("TButton", background=BG_INPUT, foreground=FG,
                    borderwidth=0, focuscolor=BG_INPUT, padding=(10, 6))
        s.map("TButton",
              background=[("active", "#3d4052"), ("disabled", "#2a2c36")],
              foreground=[("disabled", FG_DIM)])

        s.configure("Accent.TButton", background=ACCENT, foreground="#12141a",
                    font=FONT_B, padding=(10, 8))
        s.map("Accent.TButton",
              background=[("active", "#6fb0e8"), ("disabled", "#3a4a5a")],
              foreground=[("disabled", FG_DIM)])

        # Combobox: readonly durumunda clam teması alanı seçili gibi
        # boyar ve metin okunmaz hale gelir; her iki durumu da açıkça
        # sabitliyoruz. Açılır liste ayrı bir Tk penceresi olduğu için
        # option_add ile ayarlanmalı.
        s.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_INPUT,
                    foreground=FG, arrowcolor=FG, selectbackground=BG_INPUT,
                    selectforeground=FG, padding=4)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG_INPUT), ("focus", BG_INPUT)],
              selectbackground=[("readonly", BG_INPUT), ("focus", BG_INPUT)],
              selectforeground=[("readonly", FG), ("focus", FG)],
              foreground=[("readonly", FG), ("focus", FG)],
              background=[("readonly", BG_INPUT), ("active", "#3d4052")])

        self.root.option_add("*TCombobox*Listbox.background", BG_INPUT)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#12141a")
        self.root.option_add("*TCombobox*Listbox.font", FONT)
        s.configure("TNotebook", background=BG_PANEL, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_INPUT, foreground=FG_DIM,
                    padding=(14, 6), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", BG_PANEL)],
              foreground=[("selected", ACCENT)])

        s.configure("Horizontal.TScale", background=BG_PANEL,
                    troughcolor=BG_INPUT)
        s.configure("TCheckbutton", background=BG_PANEL, foreground=FG)
        s.map("TCheckbutton", background=[("active", BG_PANEL)])
        s.configure("TPanedwindow", background=BG)
        s.configure("Horizontal.TProgressbar", background=ACCENT,
                    troughcolor=BG_INPUT, borderwidth=0)

    # ------------------------------------------------------------------
    # Yerleşim
    # ------------------------------------------------------------------

    def _build_layout(self):
        outer = ttk.Frame(self.root, style="Dark.TFrame")
        outer.pack(fill="both", expand=True, padx=6, pady=6)

        # Üç ana sütun
        left = ttk.Frame(outer, style="TFrame", width=self.left_w)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        right = ttk.Frame(outer, style="TFrame", width=self.right_w)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        center = ttk.Frame(outer, style="Dark.TFrame")
        center.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)
        self._build_statusbar()

    # --------------------------- SOL PANEL ----------------------------

    def _build_left(self, parent):
        ttk.Label(parent, text="IPF", style="Head.TLabel").pack(
            anchor="w", padx=12, pady=(10, 0))
        ttk.Label(parent, text="Image Processing Functions",
                  style="Dim.TLabel").pack(anchor="w", padx=12, pady=(0, 8))

        # --- Görüntü ---
        gf = ttk.Labelframe(parent, text=" Görüntü ")
        gf.pack(fill="x", padx=10, pady=6)

        ttk.Button(gf, text="Görüntü Yükle…", command=self.on_load).pack(
            fill="x", padx=8, pady=(8, 4))

        self.lbl_file = ttk.Label(gf, text="Yüklenmedi", style="Dim.TLabel",
                                  wraplength=250, justify="left")
        self.lbl_file.pack(fill="x", padx=8, pady=(0, 8))

        # --- Filtre ---
        ff = ttk.Labelframe(parent, text=" Filtre ")
        ff.pack(fill="x", padx=10, pady=6)

        ttk.Label(ff, text="Kategori", style="Dim.TLabel").pack(
            anchor="w", padx=8, pady=(8, 2))
        self.cmb_cat = ttk.Combobox(ff, state="readonly", font=FONT)
        self.cmb_cat.pack(fill="x", padx=8)
        self.cmb_cat.bind("<<ComboboxSelected>>", self.on_category)

        ttk.Label(ff, text="Fonksiyon", style="Dim.TLabel").pack(
            anchor="w", padx=8, pady=(8, 2))
        self.cmb_filter = ttk.Combobox(ff, state="readonly", font=FONT)
        self.cmb_filter.pack(fill="x", padx=8, pady=(0, 8))
        self.cmb_filter.bind("<<ComboboxSelected>>", self.on_filter)

        # --- Parametreler ---
        pf = ttk.Labelframe(parent, text=" Parametreler ")
        pf.pack(fill="both", expand=True, padx=10, pady=6)
        self.params_host = ttk.Frame(pf)
        self.params_host.pack(fill="both", expand=True, padx=8, pady=8)

        # --- Eylemler ---
        af = ttk.Frame(parent)
        af.pack(fill="x", padx=10, pady=(6, 4))

        self.btn_apply = ttk.Button(af, text="▶  Filtreyi Uygula",
                                    style="Accent.TButton",
                                    command=self.on_apply, state="disabled")
        self.btn_apply.pack(fill="x", pady=(0, 4))

        row = ttk.Frame(af)
        row.pack(fill="x")
        self.btn_chain = ttk.Button(row, text="Zincirle", width=10,
                                    command=self.on_chain, state="disabled")
        self.btn_chain.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_reset = ttk.Button(row, text="Sıfırla", width=10,
                                    command=self.on_reset, state="disabled")
        self.btn_reset.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.btn_save = ttk.Button(af, text="Çıktıyı Kaydet…",
                                   command=self.on_save, state="disabled")
        self.btn_save.pack(fill="x", pady=(4, 0))

        self.progress = ttk.Progressbar(parent, mode="indeterminate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=10, pady=(4, 10))

    # -------------------------- ORTA PANEL ----------------------------

    def _build_center(self, parent):
        pane = ttk.Panedwindow(parent, orient="vertical")
        pane.pack(fill="both", expand=True)

        # --- Üst: görüntüler ---
        top = ttk.Frame(pane, style="TFrame")
        pane.add(top, weight=5)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Label(bar, text="Girdi / Çıktı", style="Head.TLabel").pack(side="left")

        self.var_stretch = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="%2–%98 görüntüleme germesi",
                        variable=self.var_stretch,
                        command=self._refresh_images).pack(side="right")

        imgs = ttk.Frame(top)
        imgs.pack(fill="both", expand=True, padx=8, pady=6)
        imgs.columnconfigure(0, weight=1, uniform="img")
        imgs.columnconfigure(1, weight=1, uniform="img")
        imgs.rowconfigure(0, weight=1)

        self.frm_in, self.cv_in, self.lbl_in = self._image_pane(
            imgs, "GİRDİ", 0)
        self.frm_out, self.cv_out, self.lbl_out = self._image_pane(
            imgs, "ÇIKTI", 1)

        self.cv_in.bind("<Configure>", lambda e: self._refresh_images())
        self.cv_out.bind("<Configure>", lambda e: self._refresh_images())

        # --- Alt: analiz sekmeleri ---
        bottom = ttk.Frame(pane, style="TFrame")
        pane.add(bottom, weight=4)

        head = ttk.Frame(bottom)
        head.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Label(head, text="Analiz", style="Head.TLabel").pack(side="left")
        self.lbl_analysis_hint = ttk.Label(
            head, text="", style="Dim.TLabel")
        self.lbl_analysis_hint.pack(side="right")

        self.nb = ttk.Notebook(bottom)
        self.nb.pack(fill="both", expand=True, padx=8, pady=6)

        self.figures = {}
        for key, label in [
            ("hist", "Histogram"),
            ("cdf", "Kümülatif Dağılım"),
            ("transfer", "Transfer Eğrisi"),
            ("spectrum", "Frekans Spektrumu"),
            ("profile", "Satır Profili"),
            ("diff", "Fark Haritası"),
            ("metrics", "Metrik Karşılaştırma"),
        ]:
            tab = ttk.Frame(self.nb)
            self.nb.add(tab, text=label)
            fig = Figure(figsize=(7, 3.2), facecolor=BG_PANEL)
            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.figures[key] = (fig, canvas)

        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._draw_current_tab())

    def _image_pane(self, parent, title, col):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=col, sticky="nsew",
                   padx=(0, 4) if col == 0 else (4, 0))

        ttk.Label(frame, text=title, style="Dim.TLabel").pack(anchor="w")

        canvas = tk.Canvas(frame, bg="#15161c", highlightthickness=1,
                           highlightbackground="#3a3d4d")
        canvas.pack(fill="both", expand=True)

        info = ttk.Label(frame, text="—", style="Dim.TLabel", font=FONT_MONO)
        info.pack(anchor="w", pady=(2, 0))
        return frame, canvas, info

    # -------------------------- SAĞ PANEL -----------------------------

    def _build_right(self, parent):
        pane = ttk.Panedwindow(parent, orient="vertical")
        pane.pack(fill="both", expand=True)

        # --- Üst: istatistik + altyapı ---
        top = ttk.Frame(pane, style="TFrame")
        pane.add(top, weight=5)

        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        tab_stats = ttk.Frame(nb)
        nb.add(tab_stats, text="İstatistik")
        self.txt_stats = self._scrolled_text(tab_stats)

        tab_infra = ttk.Frame(nb)
        nb.add(tab_infra, text="Altyapı")
        self.txt_infra = self._scrolled_text(tab_infra)

        # --- Alt: matematiksel bilgilendirme ---
        bottom = ttk.Frame(pane, style="TFrame")
        pane.add(bottom, weight=6)

        head = ttk.Frame(bottom)
        head.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(head, text="ƒ  Matematiksel Bilgilendirme",
                  style="Head.TLabel").pack(side="left")

        self.txt_info = self._scrolled_text(bottom, pady=(4, 8))
        self._configure_info_tags()
        self._show_welcome_info()
        self._update_infra()

    def _scrolled_text(self, parent, pady=(8, 8)):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True, padx=8, pady=pady)

        sb = ttk.Scrollbar(wrap, orient="vertical")
        sb.pack(side="right", fill="y")

        txt = tk.Text(wrap, bg=BG_INPUT, fg=FG, font=FONT_MONO,
                      relief="flat", wrap="word", padx=10, pady=8,
                      insertbackground=FG, yscrollcommand=sb.set,
                      selectbackground=ACCENT, selectforeground="#12141a")
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        txt.config(state="disabled")
        return txt

    def _configure_info_tags(self):
        t = self.txt_info
        t.tag_configure("title", foreground=ACCENT,
                        font=("Segoe UI", 11, "bold"), spacing3=6)
        t.tag_configure("section", foreground=ACCENT_2,
                        font=("Segoe UI", 9, "bold"), spacing1=8, spacing3=3)
        t.tag_configure("formula", foreground="#a8d8b0", font=("Consolas", 9),
                        lmargin1=12, lmargin2=12, spacing1=2, spacing3=2)
        t.tag_configure("kernel", foreground="#d8c8a8", font=("Consolas", 9),
                        lmargin1=12, lmargin2=12)
        t.tag_configure("body", foreground=FG, font=("Segoe UI", 9),
                        lmargin1=4, lmargin2=4, spacing2=2)
        t.tag_configure("dim", foreground=FG_DIM, font=("Segoe UI", 9))

    # -------------------------- DURUM ÇUBUĞU --------------------------

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=BG_PANEL, height=24)
        bar.pack(side="bottom", fill="x")

        self.lbl_status = tk.Label(bar, text="", bg=BG_PANEL, fg=FG_DIM,
                                   font=FONT, anchor="w", padx=10)
        self.lbl_status.pack(side="left", fill="x", expand=True)

        backend = "rasterio + Pillow" if imageio.HAS_RASTERIO else "Pillow"
        tk.Label(bar, text=f"yerel işleme · {backend} · maks 1080p",
                 bg=BG_PANEL, fg=FG_DIM, font=FONT, padx=10).pack(side="right")

    def _set_status(self, text, color=FG_DIM):
        self.lbl_status.config(text=text, fg=color)
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Filtre listesi ve parametreler
    # ------------------------------------------------------------------

    def _populate_filters(self):
        self.cmb_cat["values"] = filters.CATEGORY_ORDER
        self.cmb_cat.current(0)
        self.on_category()

    def on_category(self, event=None):
        cat = self.cmb_cat.get()
        keys = [k for k, v in filters.FILTERS.items() if v["category"] == cat]
        names = [filters.FILTERS[k]["name"] for k in keys]
        self._cat_keys = keys
        self.cmb_filter["values"] = names
        if names:
            self.cmb_filter.current(0)
            self.on_filter()

    def on_filter(self, event=None):
        idx = self.cmb_filter.current()
        if idx < 0:
            return
        self.current_key = self._cat_keys[idx]
        self._build_params(self.current_key)
        self._show_info(self.current_key)
        self._update_infra()

    def _build_params(self, key):
        for w in self.params_host.winfo_children():
            w.destroy()
        self.param_widgets = {}

        spec = filters.FILTERS[key]
        params = spec["params"]

        if not params:
            ttk.Label(self.params_host,
                      text="Bu fonksiyon parametresizdir.\nDönüşüm tamamen "
                           "görüntü verisinden\ntüretilir.",
                      style="Dim.TLabel", justify="left").pack(anchor="w")
            return

        for name, label, ptype, default, pmin, pmax, step in params:
            row = ttk.Frame(self.params_host)
            row.pack(fill="x", pady=(0, 10))

            head = ttk.Frame(row)
            head.pack(fill="x")
            ttk.Label(head, text=label, style="Dim.TLabel").pack(side="left")

            var = tk.DoubleVar(value=float(default))
            val_lbl = ttk.Label(head, text=self._fmt(default, ptype),
                                foreground=ACCENT, background=BG_PANEL,
                                font=FONT_B)
            val_lbl.pack(side="right")

            def make_cb(v=var, l=val_lbl, t=ptype, s=step, lo=pmin):
                def cb(_=None):
                    raw = v.get()
                    # Adıma yasla (medyan/pencere boyutları için tek sayı)
                    if t is int:
                        snapped = lo + round((raw - lo) / s) * s
                        snapped = int(round(snapped))
                        l.config(text=str(snapped))
                    else:
                        l.config(text=f"{raw:.2f}")
                return cb

            scale = ttk.Scale(row, from_=pmin, to=pmax, variable=var,
                              orient="horizontal", command=make_cb())
            scale.pack(fill="x", pady=(2, 0))

            self.param_widgets[name] = (var, ptype, pmin, step)

    @staticmethod
    def _fmt(value, ptype):
        return str(int(value)) if ptype is int else f"{float(value):.2f}"

    def _collect_params(self):
        out = {}
        for name, (var, ptype, pmin, step) in self.param_widgets.items():
            raw = var.get()
            if ptype is int:
                snapped = pmin + round((raw - pmin) / step) * step
                out[name] = int(round(snapped))
            else:
                out[name] = float(raw)
        return out

    # ------------------------------------------------------------------
    # Olaylar
    # ------------------------------------------------------------------

    def on_load(self):
        path = filedialog.askopenfilename(
            title="Görüntü seç",
            filetypes=[
                ("Tüm görüntüler",
                 "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.gif"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("TIFF / GeoTIFF", "*.tif *.tiff"),
                ("Tüm dosyalar", "*.*"),
            ])
        if not path:
            return

        try:
            self._set_status("Görüntü yükleniyor…")
            self.source = imageio.load_image(path)
        except Exception as exc:
            messagebox.showerror("Yükleme hatası",
                                 f"Görüntü açılamadı:\n\n{exc}")
            self._set_status("Yükleme başarısız.", WARN)
            return

        self.result = None
        self.last_elapsed = 0.0

        name = os.path.basename(path)
        detail = f"{self.source.width}×{self.source.height} · {self.source.bands} bant"
        if self.source.resized:
            detail += "  (1080p'ye küçültüldü)"
        self.lbl_file.config(text=f"{name}\n{detail}")

        self.btn_apply.config(state="normal")
        self.btn_chain.config(state="disabled")
        self.btn_reset.config(state="normal")
        self.btn_save.config(state="disabled")

        self._refresh_images()
        self._update_stats()
        self._update_infra()
        self._draw_current_tab()

        msg = f"Yüklendi: {name}"
        if self.source.resized:
            ob, oh, ow = self.source.orig_shape
            msg += f" — {ow}×{oh} → {self.source.width}×{self.source.height}"
        self._set_status(msg, OK)

    def on_apply(self, chain=False):
        if self.source is None or self.busy:
            return

        key = self.current_key
        spec = filters.FILTERS[key]

        base = self.result if (chain and self.result is not None) else self.source.data

        if spec.get("multiband_only") and base.shape[0] < 2:
            messagebox.showwarning(
                "Bant sayısı yetersiz",
                f"{spec['name']} en az 2 bantlı bir görüntü gerektirir.\n"
                f"Yüklenen görüntü {base.shape[0]} bantlı.\n\n"
                "İlk bant pankromatik, kalan bantlar çok bantlı veri olarak "
                "kullanılır.")
            return

        params = self._collect_params()
        self._set_busy(True)
        self._set_status(f"{spec['name']} uygulanıyor…", ACCENT)

        def work():
            t0 = time.perf_counter()
            try:
                out = filters.apply_filter(key, base, params)
                elapsed = time.perf_counter() - t0
                self.root.after(0, self._on_done, out, elapsed, spec, chain)
            except Exception:
                tb = traceback.format_exc()
                self.root.after(0, self._on_error, tb)

        threading.Thread(target=work, daemon=True).start()

    def on_chain(self):
        self.on_apply(chain=True)

    def _on_done(self, out, elapsed, spec, chained):
        self.result = out.astype(np.float32)
        self.last_elapsed = elapsed
        self._set_busy(False)

        self.btn_chain.config(state="normal")
        self.btn_save.config(state="normal")

        self._refresh_images()
        self._update_stats()
        self._update_infra()
        self._draw_current_tab()

        prefix = "Zincirlendi" if chained else "Uygulandı"
        self._set_status(f"{prefix}: {spec['name']} — {elapsed:.3f} s", OK)

    def _on_error(self, tb):
        self._set_busy(False)
        self._set_status("İşlem başarısız.", WARN)
        messagebox.showerror("İşlem hatası", tb)

    def on_reset(self):
        self.result = None
        self.last_elapsed = 0.0
        self.btn_chain.config(state="disabled")
        self.btn_save.config(state="disabled")
        self._refresh_images()
        self._update_stats()
        self._update_infra()
        self._draw_current_tab()
        self._set_status("Çıktı sıfırlandı — girdi korundu.")

    def on_save(self):
        if self.result is None:
            return

        base = os.path.splitext(os.path.basename(self.source.path))[0]
        suggested = f"{base}_{self.current_key}"

        path = filedialog.asksaveasfilename(
            title="Çıktıyı kaydet",
            initialfile=suggested,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"),
                       ("TIFF / GeoTIFF", "*.tif"), ("Tüm dosyalar", "*.*")])
        if not path:
            return

        try:
            imageio.save_image(path, self.result, source=self.source,
                               stretch=self.var_stretch.get())
            self._set_status(f"Kaydedildi: {os.path.basename(path)}", OK)
        except Exception as exc:
            messagebox.showerror("Kayıt hatası", str(exc))
            self._set_status("Kayıt başarısız.", WARN)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_apply.config(state=state if self.source is not None else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    # ------------------------------------------------------------------
    # Görüntü çizimi
    # ------------------------------------------------------------------

    def _refresh_images(self):
        stretch = self.var_stretch.get()

        if self.source is not None:
            self._photo_in = self._render(
                self.cv_in, self.source.data, stretch)
            self.lbl_in.config(text=self._pane_info(self.source.data))
        else:
            self.cv_in.delete("all")
            self.lbl_in.config(text="—")

        if self.result is not None:
            self._photo_out = self._render(self.cv_out, self.result, stretch)
            self.lbl_out.config(text=self._pane_info(self.result))
        else:
            self.cv_out.delete("all")
            self._photo_out = None
            self.lbl_out.config(text="—")
            if self.source is not None:
                self._placeholder(self.cv_out, "Filtre uygulanmadı")

    def _render(self, canvas, data, stretch):
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 20 or ch < 20:
            return None

        disp = imageio.to_display(data, stretch=stretch)
        img = Image.fromarray(disp)

        scale = min(cw / img.width, ch / img.height)
        nw = max(int(img.width * scale), 1)
        nh = max(int(img.height * scale), 1)
        img = img.resize((nw, nh), Image.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")
        return photo

    def _placeholder(self, canvas, text):
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 20 or ch < 20:
            return
        canvas.create_text(cw // 2, ch // 2, text=text, fill="#4a4d5e",
                           font=("Segoe UI", 11))

    @staticmethod
    def _pane_info(data):
        return (f"{data.shape[2]}×{data.shape[1]} · {data.shape[0]} bant · "
                f"[{data.min():.3f}, {data.max():.3f}] · "
                f"μ={data.mean():.3f} σ={data.std():.3f}")

    # ------------------------------------------------------------------
    # Grafikler
    # ------------------------------------------------------------------

    def _draw_current_tab(self):
        if self.source is None:
            for key in self.figures:
                self._clear_fig(key, "Görüntü yükleyin")
            return

        idx = self.nb.index(self.nb.select())
        key = list(self.figures.keys())[idx]

        try:
            {
                "hist": self._plot_hist,
                "cdf": self._plot_cdf,
                "transfer": self._plot_transfer,
                "spectrum": self._plot_spectrum,
                "profile": self._plot_profile,
                "diff": self._plot_diff,
                "metrics": self._plot_metrics,
            }[key]()
        except Exception:
            self._clear_fig(key, "Grafik çizilemedi")

    def _clear_fig(self, key, message):
        fig, canvas = self.figures[key]
        fig.clear()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center",
                color=FG_DIM, fontsize=10, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        canvas.draw_idle()

    def _band_pairs(self):
        """Karşılaştırılacak (etiket, girdi bandı, çıktı bandı) üçlüleri."""
        src = self.source.data
        dst = self.result
        n = src.shape[0] if dst is None else min(src.shape[0], dst.shape[0])
        n = min(n, 3)

        labels = ["Kırmızı", "Yeşil", "Mavi"] if n == 3 else \
                 [f"Bant {i+1}" for i in range(n)]
        colors = ["#d9695b", "#6bbf7b", "#5b9dd9"] if n == 3 else \
                 [ACCENT, ACCENT_2, OK][:n]

        for i in range(n):
            yield labels[i], colors[i], src[i], (None if dst is None else dst[i])

    def _plot_hist(self):
        fig, canvas = self.figures["hist"]
        fig.clear()

        has_out = self.result is not None
        axes = fig.subplots(1, 2 if has_out else 1, squeeze=False)[0]

        ax_in = axes[0]
        for label, color, s, _ in self._band_pairs():
            x, h = analysis.histogram_data(s, bins=256)
            ax_in.plot(x, h, color=color, lw=1.0, label=label)
            ax_in.fill_between(x, h, color=color, alpha=0.15)
        ax_in.set_title("Girdi histogramı", fontsize=9)
        ax_in.set_xlabel("Yoğunluk", fontsize=8)
        ax_in.set_ylabel("Piksel sayısı", fontsize=8)
        ax_in.grid(alpha=0.2)
        ax_in.legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                     labelcolor=FG)

        if has_out:
            ax_out = axes[1]
            for label, color, _, d in self._band_pairs():
                if d is None:
                    continue
                x, h = analysis.histogram_data(d, bins=256)
                ax_out.plot(x, h, color=color, lw=1.0, label=label)
                ax_out.fill_between(x, h, color=color, alpha=0.15)
            ax_out.set_title("Çıktı histogramı", fontsize=9)
            ax_out.set_xlabel("Yoğunluk", fontsize=8)
            ax_out.grid(alpha=0.2)

        self.lbl_analysis_hint.config(
            text="Yoğunluk dağılımı — kontrast değişimi doğrudan okunur")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_cdf(self):
        fig, canvas = self.figures["cdf"]
        fig.clear()
        ax = fig.add_subplot(111)

        for label, color, s, d in self._band_pairs():
            x, c = analysis.cdf_data(s)
            ax.plot(x, c, color=color, lw=1.4, ls="--", alpha=0.6,
                    label=f"{label} · girdi")
            if d is not None:
                x2, c2 = analysis.cdf_data(d)
                ax.plot(x2, c2, color=color, lw=1.6, label=f"{label} · çıktı")

        ax.set_title("Kümülatif dağılım fonksiyonu (KDF)", fontsize=9)
        ax.set_xlabel("Yoğunluk", fontsize=8)
        ax.set_ylabel("P(X ≤ x)", fontsize=8)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                  labelcolor=FG, ncol=2)

        self.lbl_analysis_hint.config(
            text="Kesikli: girdi · düz: çıktı — doğruya yaklaşan KDF düzgün dağılım demek")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_transfer(self):
        fig, canvas = self.figures["transfer"]
        fig.clear()
        ax = fig.add_subplot(111)

        if self.result is None:
            self._clear_fig("transfer", "Önce bir filtre uygulayın")
            return

        for label, color, s, d in self._band_pairs():
            if d is None:
                continue
            x, y = analysis.transfer_curve(s, d, bins=128)
            ax.plot(x, y, color=color, lw=1.6, label=label)

        lims = [0, 1]
        ax.plot(lims, lims, color=FG_DIM, lw=0.8, ls=":", label="y = x")

        ax.set_title("Ampirik transfer eğrisi  (girdi → çıktı)", fontsize=9)
        ax.set_xlabel("Girdi yoğunluğu", fontsize=8)
        ax.set_ylabel("Ortalama çıktı yoğunluğu", fontsize=8)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                  labelcolor=FG)

        self.lbl_analysis_hint.config(
            text="Noktasal filtrelerde teorik eğriyle birebir örtüşür")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_spectrum(self):
        fig, canvas = self.figures["spectrum"]
        fig.clear()
        ax = fig.add_subplot(111)

        s = self.source.data[0]
        f1, p1 = analysis.radial_spectrum(s)
        ax.semilogy(f1, np.maximum(p1, 1e-8), color=FG_DIM, lw=1.4,
                    ls="--", label="Girdi")

        if self.result is not None:
            f2, p2 = analysis.radial_spectrum(self.result[0])
            ax.semilogy(f2, np.maximum(p2, 1e-8), color=ACCENT, lw=1.6,
                        label="Çıktı")

        ax.set_title("Radyal ortalama genlik spektrumu (bant 1)", fontsize=9)
        ax.set_xlabel("Normalize uzamsal frekans  (0.5 = Nyquist)", fontsize=8)
        ax.set_ylabel("|F(u,v)| ortalama", fontsize=8)
        ax.grid(alpha=0.2, which="both")
        ax.legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                  labelcolor=FG)

        self.lbl_analysis_hint.config(
            text="Sağ uçtaki düşüş = bulanıklaştırma · yükseliş = keskinleştirme")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_profile(self):
        fig, canvas = self.figures["profile"]
        fig.clear()
        ax = fig.add_subplot(111)

        s = self.source.data[0]
        row = s.shape[0] // 2
        x, y = analysis.row_profile(s, row)
        ax.plot(x, y, color=FG_DIM, lw=1.0, ls="--", label="Girdi")

        if self.result is not None:
            d = self.result[0]
            r2 = min(row, d.shape[0] - 1)
            x2, y2 = analysis.row_profile(d, r2)
            ax.plot(x2, y2, color=ACCENT, lw=1.2, label="Çıktı")

        ax.set_title(f"Yoğunluk profili — satır {row} (bant 1)", fontsize=9)
        ax.set_xlabel("Sütun (piksel)", fontsize=8)
        ax.set_ylabel("Yoğunluk", fontsize=8)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                  labelcolor=FG)

        self.lbl_analysis_hint.config(
            text="Kenar geçişlerinin dikliği ve halo (overshoot) burada görülür")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_diff(self):
        fig, canvas = self.figures["diff"]
        fig.clear()

        if self.result is None:
            self._clear_fig("diff", "Önce bir filtre uygulayın")
            return

        diff = analysis.difference_map(self.source.data, self.result)

        axes = fig.subplots(1, 2, gridspec_kw={"width_ratios": [3, 2]})

        vmax = float(np.abs(diff).max())
        vmax = vmax if vmax > 1e-9 else 1e-9
        im = axes[0].imshow(diff, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        axes[0].set_title("Çıktı − Girdi", fontsize=9)
        axes[0].set_xticks([])
        axes[0].set_yticks([])
        cb = fig.colorbar(im, ax=axes[0], fraction=0.046)
        cb.ax.tick_params(labelsize=7, colors=FG_DIM)
        cb.outline.set_edgecolor("#4a4d5e")

        axes[1].hist(diff.ravel(), bins=128, color=ACCENT, alpha=0.75)
        axes[1].axvline(0, color=FG_DIM, lw=0.8, ls=":")
        axes[1].set_title("Fark dağılımı", fontsize=9)
        axes[1].set_xlabel("Δ yoğunluk", fontsize=8)
        axes[1].grid(alpha=0.2)

        self.lbl_analysis_hint.config(
            text=f"Kırmızı: artış · Mavi: azalış · maks |Δ| = {vmax:.4f}")
        fig.tight_layout()
        canvas.draw_idle()

    def _plot_metrics(self):
        fig, canvas = self.figures["metrics"]
        fig.clear()

        if self.result is None:
            self._clear_fig("metrics", "Önce bir filtre uygulayın")
            return

        c = analysis.compare(self.source.data, self.result)

        groups = [
            ("Ortalama", c["mean_in"], c["mean_out"]),
            ("Std. sapma", c["std_in"], c["std_out"]),
            ("Keskinlik", c["sharpness_in"], c["sharpness_out"]),
            ("Entropi/8", c["entropy_in"] / 8.0, c["entropy_out"] / 8.0),
            ("Kenar yoğ./100", c["edges_in"] / 100.0, c["edges_out"] / 100.0),
        ]

        axes = fig.subplots(1, 2, gridspec_kw={"width_ratios": [3, 2]})

        labels = [g[0] for g in groups]
        vin = [g[1] for g in groups]
        vout = [g[2] for g in groups]
        pos = np.arange(len(groups))
        w = 0.38

        axes[0].bar(pos - w / 2, vin, w, label="Girdi", color=FG_DIM)
        axes[0].bar(pos + w / 2, vout, w, label="Çıktı", color=ACCENT)
        axes[0].set_xticks(pos)
        axes[0].set_xticklabels(labels, fontsize=7, rotation=15)
        axes[0].set_title("Girdi / çıktı ölçütleri (normalize)", fontsize=9)
        axes[0].grid(alpha=0.2, axis="y")
        axes[0].legend(fontsize=7, facecolor=BG_INPUT, edgecolor="#4a4d5e",
                       labelcolor=FG)

        # Benzerlik metrikleri
        sim_labels = ["SSIM", "Korelasyon"]
        sim_vals = [c["ssim"], c["corr"]]
        axes[1].barh(sim_labels, sim_vals, color=[OK, ACCENT_2], height=0.5)
        axes[1].set_xlim(-1.05, 1.05)
        axes[1].axvline(0, color=FG_DIM, lw=0.8)
        axes[1].set_title("Girdiye benzerlik", fontsize=9)
        axes[1].grid(alpha=0.2, axis="x")
        for i, v in enumerate(sim_vals):
            axes[1].text(v, i, f" {v:.4f}", va="center", fontsize=8, color=FG)

        psnr_txt = "∞" if np.isinf(c["psnr"]) else f"{c['psnr']:.2f} dB"
        self.lbl_analysis_hint.config(
            text=f"PSNR = {psnr_txt} · MSE = {c['mse']:.6f}")
        fig.tight_layout()
        canvas.draw_idle()

    # ------------------------------------------------------------------
    # İstatistik ve altyapı metinleri
    # ------------------------------------------------------------------

    def _write(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _update_stats(self):
        if self.source is None:
            self._write(self.txt_stats, "Görüntü yüklenmedi.")
            return

        lines = [self.source.summary(), ""]
        lines.append("─" * 44)
        lines.append("BANT İSTATİSTİKLERİ — GİRDİ")
        lines.append("─" * 44)
        lines.extend(self._stats_block(self.source.data))

        if self.result is not None:
            lines.append("")
            lines.append("─" * 44)
            lines.append("BANT İSTATİSTİKLERİ — ÇIKTI")
            lines.append("─" * 44)
            lines.extend(self._stats_block(self.result))

            c = analysis.compare(self.source.data, self.result)
            psnr_txt = "∞ (özdeş)" if np.isinf(c["psnr"]) else f"{c['psnr']:.3f} dB"
            lines += [
                "",
                "─" * 44,
                "KARŞILAŞTIRMA METRİKLERİ",
                "─" * 44,
                f"MSE            : {c['mse']:.8f}",
                f"PSNR           : {psnr_txt}",
                f"SSIM           : {c['ssim']:.6f}",
                f"Korelasyon (r) : {c['corr']:.6f}",
                "",
                f"Keskinlik      : {c['sharpness_in']:.5f} → {c['sharpness_out']:.5f}"
                f"  ({self._delta(c['sharpness_in'], c['sharpness_out'])})",
                f"Entropi (bit)  : {c['entropy_in']:.4f} → {c['entropy_out']:.4f}"
                f"  ({self._delta(c['entropy_in'], c['entropy_out'])})",
                f"Kenar yoğ. (%) : {c['edges_in']:.3f} → {c['edges_out']:.3f}"
                f"  ({self._delta(c['edges_in'], c['edges_out'])})",
                f"Std. sapma     : {c['std_in']:.5f} → {c['std_out']:.5f}"
                f"  ({self._delta(c['std_in'], c['std_out'])})",
            ]

        self._write(self.txt_stats, "\n".join(lines))

    @staticmethod
    def _delta(a, b):
        if abs(a) < 1e-12:
            return "—"
        pct = (b - a) / abs(a) * 100.0
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"

    @staticmethod
    def _stats_block(data):
        out = []
        n = data.shape[0]
        names = (["R", "G", "B"] if n == 3 else
                 [f"B{i+1}" for i in range(n)])
        for i in range(min(n, 6)):
            s = analysis.band_stats(data[i])
            out += [
                f"[{names[i] if i < len(names) else f'B{i+1}'}]"
                f"  min={s['min']:.4f}  max={s['max']:.4f}",
                f"     μ={s['mean']:.4f}   med={s['median']:.4f}   "
                f"σ={s['std']:.4f}",
                f"     CV={s['cv']:.4f}   çarpıklık={s['skew']:+.3f}   "
                f"basıklık={s['kurtosis']:+.3f}",
                f"     entropi={s['entropy']:.4f} bit   "
                f"P2={s['p2']:.4f}  P98={s['p98']:.4f}",
                "",
            ]
        if n > 6:
            out.append(f"… ve {n - 6} bant daha")
        return out

    def _update_infra(self):
        key = self.current_key
        spec = filters.FILTERS.get(key, {})

        lines = [
            "İŞLEME ALTYAPISI",
            "═" * 44,
            "",
            "Yürütme yeri : yerel makine (offline)",
            f"Python       : {sys.version.split()[0]}",
            f"NumPy        : {np.__version__}",
        ]

        try:
            import scipy
            lines.append(f"SciPy        : {scipy.__version__}")
        except ImportError:
            lines.append("SciPy        : yok")

        lines.append(f"Matplotlib   : {matplotlib.__version__}")
        lines.append(
            f"rasterio     : {'kurulu (GeoTIFF etkin)' if imageio.HAS_RASTERIO else 'yok — Pillow kullanılıyor'}")
        lines += [
            "",
            "─" * 44,
            "VERİ AKIŞI (PIPELINE)",
            "─" * 44,
            "",
            "1. Okuma",
            "   rasterio (.tif) veya Pillow (.png/.jpg)",
            "   → ndarray (B, H, W)",
            "",
            "2. Boyut sınırı",
            f"   {imageio.MAX_PIXELS:,} piksel (1920×1080) üstü Lanczos ile",
            "   oranı korunarak küçültülür",
            "",
            "3. Normalizasyon",
            "   float32, tüm bantlar ortak ölçekle [0, 1]",
            "",
            "4. Filtreleme",
            "   scipy.ndimage konvolüsyon / sıralama süzgeçleri",
            "   bant bant uygulanır, kenarlarda 'reflect' dolgusu",
            "",
            "5. Analiz",
            "   histogram · KDF · FFT radyal spektrum · SSIM · PSNR",
            "",
            "6. Görüntüleme",
            "   %2–%98 yüzdelik germesi (yalnız ekran için;",
            "   analiz her zaman ham veriyle yapılır)",
        ]

        if self.source is not None:
            ob, oh, ow = self.source.orig_shape
            px = self.source.width * self.source.height
            lines += [
                "",
                "─" * 44,
                "GEÇERLİ İŞ",
                "─" * 44,
                "",
                f"Kaynak      : {os.path.basename(self.source.path)}",
                f"Okuyucu     : {self.source.mode}",
                f"Özgün       : {ow}×{oh}, {ob} bant",
                f"İşlenen     : {self.source.width}×{self.source.height}, "
                f"{self.source.bands} bant",
                f"Küçültüldü  : {'evet' if self.source.resized else 'hayır'}",
                f"Piksel      : {px:,}",
                f"Bellek      : ~{self.source.data.nbytes / 1e6:.2f} MB (float32)",
            ]

        if spec:
            lines += [
                "",
                "─" * 44,
                "SEÇİLİ FONKSİYON",
                "─" * 44,
                "",
                f"Ad          : {spec['name']}",
                f"Kategori    : {spec['category']}",
                f"Çağrı       : filters.{spec['func'].__name__}()",
            ]
            params = self._collect_params()
            if params:
                lines.append("Parametreler:")
                for k, v in params.items():
                    val = f"{v}" if isinstance(v, int) else f"{v:.3f}"
                    lines.append(f"   {k} = {val}")
            else:
                lines.append("Parametreler: yok")

        if self.result is not None:
            lines += [
                "",
                f"Son işlem süresi : {self.last_elapsed:.3f} s",
                f"Çıktı şekli      : {self.result.shape}",
                f"Çıktı aralığı    : [{self.result.min():.4f}, "
                f"{self.result.max():.4f}]",
            ]

        self._write(self.txt_infra, "\n".join(lines))

    # ------------------------------------------------------------------
    # Bilgilendirme paneli
    # ------------------------------------------------------------------

    def _show_welcome_info(self):
        t = self.txt_info
        t.config(state="normal")
        t.delete("1.0", "end")
        t.insert("end", "IPF — Image Processing Functions\n", "title")
        t.insert("end",
                 "Sol panelden bir görüntü yükleyin ve bir fonksiyon seçin. "
                 "Seçtiğiniz fonksiyonun matematiksel tanımı, çekirdeği ve "
                 "parametrelerinin etkisi bu panelde açıklanır.\n\n", "body")
        t.insert("end", "Panelin içeriği\n", "section")
        t.insert("end",
                 "• Bağıntı — fonksiyonun kapalı formdaki tanımı\n"
                 "• Çekirdek — konvolüsyon matrisi veya transfer eğrisi\n"
                 "• Matematiksel anlam — işlemin neden işe yaradığı\n"
                 "• Parametreler — her katsayının davranışa etkisi\n"
                 "• Etki — görüntüde gözlenen sonuç\n", "body")
        t.config(state="disabled")

    def _show_info(self, key):
        e = explanations.get_explanation(key)
        t = self.txt_info
        t.config(state="normal")
        t.delete("1.0", "end")

        t.insert("end", e["title"] + "\n", "title")

        t.insert("end", "▸ BAĞINTI\n", "section")
        t.insert("end", e["formula"] + "\n", "formula")

        t.insert("end", "▸ ÇEKİRDEK / DÖNÜŞÜM\n", "section")
        t.insert("end", e["kernel"] + "\n", "kernel")

        t.insert("end", "▸ MATEMATİKSEL ANLAM\n", "section")
        t.insert("end", e["theory"] + "\n", "body")

        t.insert("end", "▸ PARAMETRELER\n", "section")
        t.insert("end", e["params"] + "\n", "formula")

        t.insert("end", "▸ GÖRÜNTÜ ÜZERİNDEKİ ETKİ\n", "section")
        t.insert("end", e["effect"] + "\n", "body")

        t.config(state="disabled")
        t.see("1.0")


def main():
    root = tk.Tk()
    app = IPFApp(root)

    # Tema uyumlu ikon yoksa sessizce geç
    try:
        root.iconname("IPF")
    except tk.TclError:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
