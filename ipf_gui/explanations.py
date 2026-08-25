"""
IPF - Filtrelerin matematiksel açıklamaları.

Her giriş şu alanlardan oluşur:
    title    : Başlık
    formula  : Ana bağıntı (düz metin matematik gösterimi)
    kernel   : Varsa çekirdek matrisi metni
    theory   : Fonksiyonun ne yaptığının matematiksel anlatımı
    params   : Parametrelerin etkisi
    effect   : Görüntü üzerindeki pratik sonuç
"""

EXPLANATIONS = {

    # =====================================================================
    "laplacian": {
        "title": "Laplacian Kenar İyileştirme",
        "formula": (
            "∇²f = ∂²f/∂x² + ∂²f/∂y²\n"
            "g(x,y) = f(x,y) + α · ∇²f(x,y)"
        ),
        "kernel": (
            "  0  -1   0\n"
            " -1   4  -1\n"
            "  0  -1   0"
        ),
        "theory": (
            "Laplacian, görüntünün ikinci mertebeden türevidir. Ayrık halde "
            "merkez pikselin komşularının ortalamasından ne kadar saptığını "
            "ölçer:\n\n"
            "  ∇²f ≈ 4f(x,y) − f(x+1,y) − f(x−1,y) − f(x,y+1) − f(x,y−1)\n\n"
            "Düz (sabit yoğunluklu) bölgelerde çekirdek katsayıları toplamı "
            "sıfır olduğu için çıktı sıfırdır. Yalnız yoğunluğun ikinci "
            "türevinin sıfırdan farklı olduğu yerlerde — yani kenar geçişlerinde "
            "— tepki verir. Bu izole edilmiş kenar bileşeni α ağırlığı ile "
            "orijinale geri eklenerek kenarlar vurgulanır.\n\n"
            "Yönden bağımsızdır (izotropik): görüntüyü döndürmek Laplacian "
            "yanıtını değiştirmez. İkinci türev olduğundan gürültüye birinci "
            "türev operatörlerinden daha duyarlıdır."
        ),
        "params": (
            "α = 0      : değişiklik yok (g = f)\n"
            "α ∈ (0,1)  : yumuşak kenar vurgusu\n"
            "α > 1      : güçlü vurgu, kenar çevresinde halo ve gürültü artışı"
        ),
        "effect": (
            "Kenarlar ve ince detaylar belirginleşir; yüzey dokusu ve "
            "gürültü de birlikte güçlenir."
        ),
    },

    # =====================================================================
    "sobel": {
        "title": "Sobel Kenar İyileştirme",
        "formula": (
            "G_x = S_x * f,  G_y = S_y * f\n"
            "|∇f| = √(G_x² + G_y²)\n"
            "θ = arctan(G_y / G_x)\n"
            "g = f + α · |∇f|"
        ),
        "kernel": (
            "S_x:            S_y:\n"
            " -1  0  1       -1 -2 -1\n"
            " -2  0  2        0  0  0\n"
            " -1  0  1        1  2  1"
        ),
        "theory": (
            "Sobel, birinci mertebeden türevin ayrık yaklaşımıdır. Çekirdek "
            "iki bileşene ayrılabilir (separable):\n\n"
            "  S_x = [1 2 1]ᵀ · [−1 0 1]\n\n"
            "Yani merkez satıra 2 ağırlık veren bir üçgen yumuşatma ile "
            "merkezî fark türevinin çarpımıdır. Bu yapı, türev alırken dik "
            "yönde hafif bir alçak geçiren filtreleme yapar; bu yüzden Sobel "
            "saf merkezî farka ve Prewitt'e göre gürültüye daha dayanıklıdır.\n\n"
            "Gradyan vektörü ∇f = (G_x, G_y) yoğunluğun en hızlı arttığı yönü "
            "gösterir; büyüklüğü |∇f| o yöndeki değişim hızıdır. Kenarlar "
            "gradyan büyüklüğünün yerel maksimum olduğu noktalardır."
        ),
        "params": (
            "α : gradyan büyüklüğünün orijinale katkı ağırlığı.\n"
            "    |∇f| ≥ 0 olduğundan sonuç her zaman parlaklaşma yönündedir;\n"
            "    büyük α değerlerinde genel parlaklık da artar."
        ),
        "effect": (
            "Yönelimli kenarlar (özellikle yatay ve düşey) güçlenir. "
            "Laplacian'a göre daha kalın ama daha gürültüsüz kenar yanıtı."
        ),
    },

    # =====================================================================
    "prewitt": {
        "title": "Prewitt Kenar İyileştirme",
        "formula": (
            "G_x = P_x * f,  G_y = P_y * f\n"
            "|∇f| = √(G_x² + G_y²)\n"
            "g = f + α · |∇f|"
        ),
        "kernel": (
            "P_x:            P_y:\n"
            " -1  0  1       -1 -1 -1\n"
            " -1  0  1        0  0  0\n"
            " -1  0  1        1  1  1"
        ),
        "theory": (
            "Prewitt de ayrılabilir bir operatördür:\n\n"
            "  P_x = [1 1 1]ᵀ · [−1 0 1]\n\n"
            "Sobel'den tek farkı, dik yöndeki yumuşatmanın üçgen [1 2 1] "
            "yerine düzgün (kutu) [1 1 1] olmasıdır. Kutu ortalama, üçgen "
            "ortalamaya göre frekans alanında daha kötü sönümlenir "
            "(sinc fonksiyonunun yan lobları), bu nedenle Prewitt yüksek "
            "frekanslı gürültüye Sobel'den biraz daha duyarlıdır.\n\n"
            "Buna karşılık merkez satıra ağırlık vermediği için gradyan "
            "yanıtı yönler arasında daha eşit dağılır."
        ),
        "params": (
            "α : gradyan katkı ağırlığı. Sobel ile aynı ölçekte davranır,\n"
            "    ancak kenar yanıtı tipik olarak biraz daha zayıftır."
        ),
        "effect": (
            "Sobel'e çok yakın sonuç; gürültülü görüntülerde biraz daha "
            "fazla yanlış kenar üretir."
        ),
    },

    # =====================================================================
    "roberts": {
        "title": "Roberts Çapraz Gradyan",
        "formula": (
            "G_x = f(x,y) − f(x+1,y+1)\n"
            "G_y = f(x,y+1) − f(x+1,y)\n"
            "|∇f| = √(G_x² + G_y²)\n"
            "g = f + α · |∇f|"
        ),
        "kernel": (
            "R_x:        R_y:\n"
            "  1  0       0  1\n"
            "  0 -1      -1  0"
        ),
        "theory": (
            "Roberts operatörü 2×2'lik en küçük gradyan yaklaşımıdır ve "
            "türevi eksenler yerine 45°/135° çapraz yönlerde alır.\n\n"
            "Çok küçük destek bölgesi (support) iki sonuç doğurur:\n"
            "  • Hesaplama ucuzdur ve kenar konumu çok keskin belirlenir.\n"
            "  • Hiç yumuşatma içermediği için gürültüye en duyarlı "
            "operatördür.\n\n"
            "Ayrıca 2×2 çekirdek çift boyutlu olduğundan yanıt yarım piksel "
            "kayar; kenar tam olarak piksel merkezine oturmaz. Bu yüzden "
            "modern uygulamalarda çoğunlukla Sobel tercih edilir."
        ),
        "params": (
            "α : çapraz gradyan katkısı. Yanıt Sobel'den küçük ölçekli\n"
            "    olduğu için aynı görsel etki için daha büyük α gerekir."
        ),
        "effect": (
            "İnce, keskin kenar çizgileri; gürültülü görüntülerde belirgin "
            "benek artışı."
        ),
    },

    # =====================================================================
    "canny": {
        "title": "Canny Tabanlı Kenar İyileştirme",
        "formula": (
            "1) f_s = G_σ * f                (Gauss yumuşatma)\n"
            "2) |∇f_s| = √(G_x² + G_y²)      (Sobel gradyanı)\n"
            "3) M = |∇f_s| / max|∇f_s|       (normalizasyon)\n"
            "4) E = 1·[M > T_h] + 0.5·[T_l ≤ M ≤ T_h]\n"
            "5) g = f + α · E · M"
        ),
        "kernel": (
            "G_σ(x,y) = (1/2πσ²) · exp(−(x²+y²)/2σ²)\n"
            "ardından Sobel S_x, S_y"
        ),
        "theory": (
            "Canny'nin özgün yöntemi kenar saptamada üç ölçütü birlikte "
            "eniyilemek üzere türetilmiştir: iyi saptama, iyi konumlandırma "
            "ve tek yanıt.\n\n"
            "Zincir şöyledir: önce Gauss süzgeci gürültüyü bastırır "
            "(σ ölçek parametresidir), sonra gradyan hesaplanır, ardından "
            "maksimum olmayan bastırma (non-maximum suppression) kenarı tek "
            "piksel kalınlığına indirir, en son çift eşikleme ve histerezis "
            "ile zayıf kenarlardan yalnız güçlü kenarlara bağlı olanlar "
            "korunur.\n\n"
            "Bu uygulamada — depodaki özgün scriptte olduğu gibi — maksimum "
            "olmayan bastırma ve histerezis bağlantı adımı atlanmıştır. "
            "Yerine iki eşik arasındaki pikseller 0.5 ağırlıkla, üst eşiğin "
            "üstündekiler 1.0 ağırlıkla puanlanır ve bu maske gradyan "
            "büyüklüğü ile çarpılarak orijinale eklenir. Sonuç bir kenar "
            "haritası değil, kenar-ağırlıklı bir iyileştirmedir."
        ),
        "params": (
            "σ    : yumuşatma ölçeği. Büyük σ gürültüyü bastırır ama ince\n"
            "       detayları da siler ve kenar konumunu kaydırır.\n"
            "T_l  : alt eşik — bunun altındaki gradyanlar tamamen atılır.\n"
            "T_h  : üst eşik — bunun üstü kesin kenar sayılır.\n"
            "       Tipik oran T_h ≈ 2·T_l ile 3·T_l arasıdır.\n"
            "α    : kenar katkısının ağırlığı."
        ),
        "effect": (
            "Gürültüden arındırılmış, eşiklenmiş kenarlar vurgulanır. "
            "Ham Sobel'e göre çok daha temiz, seçici bir keskinleştirme."
        ),
    },

    # =====================================================================
    "highpass": {
        "title": "Yüksek Geçiren Süzgeç",
        "formula": (
            "g = h * f,   Σ h_ij = 0\n"
            "Frekans alanında:  G(u,v) = H(u,v) · F(u,v)"
        ),
        "kernel": (
            "(1/9) ·\n"
            " -1  -1  -1\n"
            " -1   8  -1\n"
            " -1  -1  -1"
        ),
        "theory": (
            "Çekirdek katsayılarının toplamı sıfırdır (8 − 8 = 0). Bu, DC "
            "bileşeninin — yani ortalama parlaklığın — tamamen bastırılması "
            "demektir: H(0,0) = 0.\n\n"
            "Bu çekirdek aslında bir tümleyen ilişkisinin ifadesidir:\n\n"
            "  yüksek geçiren = özdeşlik − alçak geçiren\n"
            "  h_hp = δ − h_lp\n\n"
            "burada h_lp 3×3 kutu ortalamadır. Yani filtre, her pikselden "
            "kendi yerel ortalamasını çıkarır ve geriye yalnız yerel "
            "değişim, yani yüksek uzamsal frekanslar kalır.\n\n"
            "Diğer kenar filtrelerinden farkı: sonuç orijinale eklenmez, "
            "doğrudan yüksek frekans bileşeninin kendisi çıktı olur. "
            "Bu yüzden çıktı sıfır ortalamalıdır ve negatif değerler içerir."
        ),
        "params": (
            "Parametresizdir; çekirdek sabittir. Etki şiddeti ancak\n"
            "çekirdek boyutu değiştirilerek ayarlanabilir."
        ),
        "effect": (
            "Görüntünün düz bölgeleri griye (sıfıra) düşer, yalnız kenarlar "
            "ve doku görünür kalır. Bir iyileştirme değil, bileşen ayrıştırma "
            "işlemidir."
        ),
    },

    # =====================================================================
    "gaussian": {
        "title": "Gauss Bulanıklaştırma",
        "formula": (
            "G(x,y) = (1 / 2πσ²) · exp(−(x² + y²) / 2σ²)\n"
            "g = G_σ * f\n"
            "Frekans alanında:  Ĝ(u,v) = exp(−2π²σ²(u² + v²))"
        ),
        "kernel": (
            "σ = 1 için yaklaşık 3×3 (normalize):\n"
            " 0.075  0.124  0.075\n"
            " 0.124  0.204  0.124\n"
            " 0.075  0.124  0.075"
        ),
        "theory": (
            "Gauss çekirdeği görüntü işlemede benzersiz bir konuma sahiptir, "
            "çünkü:\n\n"
            "  • Ayrılabilirdir: G(x,y) = G(x)·G(y). İki boyutlu konvolüsyon "
            "iki adet bir boyutlu konvolüsyona iner, maliyet O(k²)'den "
            "O(2k)'ya düşer.\n"
            "  • Fourier dönüşümü yine bir Gauss'tur — yani ne uzamsal ne de "
            "frekans alanında halka (ringing) üretir.\n"
            "  • Belirsizlik ilkesinin eşitlik durumunu sağlar: uzamsal ve "
            "frekans yayılımının çarpımı en küçüktür.\n"
            "  • Isı denklemi çözümüdür; σ artışı bir difüzyon süreci gibi "
            "davranır ve ölçek-uzay (scale-space) kuramının temelidir.\n\n"
            "Gürültü bastırma açısından: bağımsız beyaz gürültünün varyansı, "
            "n piksellik ağırlıklı ortalamada Σw² oranında düşer."
        ),
        "params": (
            "σ : standart sapma, bulanıklığın ölçeği.\n"
            "    Etkin çekirdek yarıçapı ≈ 3σ.\n"
            "    σ → 0 : değişiklik yok\n"
            "    σ büyük : ağır bulanıklık, kenarlar da silinir"
        ),
        "effect": (
            "Gürültü düzgün biçimde bastırılır, ancak kenarlar da aynı oranda "
            "yumuşar — filtre kenar ile gürültüyü ayırt etmez."
        ),
    },

    # =====================================================================
    "median": {
        "title": "Medyan Süzgeç",
        "formula": (
            "g(x,y) = medyan{ f(i,j) : (i,j) ∈ W(x,y) }\n"
            "W : (x,y) merkezli n×n pencere"
        ),
        "kernel": (
            "Sabit çekirdek yoktur — sıralama tabanlı (rank) bir\n"
            "istatistik uygulanır. 3×3 pencerede 9 değer sıralanır,\n"
            "5. (ortanca) değer seçilir."
        ),
        "theory": (
            "Medyan süzgeç doğrusal DEĞİLDİR: medyan(a+b) ≠ medyan(a) + "
            "medyan(b). Bu yüzden konvolüsyon teoremi ve frekans yanıtı "
            "kavramı burada geçerli değildir.\n\n"
            "Gücü, kırılma noktası (breakdown point) kavramında yatar: bir "
            "pencerede değerlerin %50'sinden azı bozuksa medyan hâlâ doğru "
            "değeri verir. Ortalama filtrenin kırılma noktası ise sıfırdır — "
            "tek bir aşırı değer sonucu bozar.\n\n"
            "Bu nedenle tuz-biber (impulse) gürültüsünde medyan, Gauss "
            "filtresinden çok daha üstündür: aykırı piksel sıralamanın uçlarına "
            "düşer ve seçilmez.\n\n"
            "Ayrıca medyan basamak kenarını korur: bir kenarın iki yanındaki "
            "değerlerden hangisi çoğunluktaysa o seçilir, ara ton üretilmez."
        ),
        "params": (
            "n (pencere boyutu, tek sayı):\n"
            "  3 : hafif, detay korur\n"
            "  5 : dengeli\n"
            "  7+ : güçlü gürültü giderme, ince yapılar ve köşeler yuvarlanır"
        ),
        "effect": (
            "Tuz-biber gürültüsü neredeyse tamamen temizlenir, kenarlar "
            "keskin kalır. Büyük pencerelerde görüntü 'boyanmış' bir görünüm alır."
        ),
    },

    # =====================================================================
    "bilateral": {
        "title": "Bilateral Süzgeç",
        "formula": (
            "g(p) = (1/W_p) · Σ_{q∈S} G_σs(‖p−q‖) · G_σr(|f(p)−f(q)|) · f(q)\n"
            "W_p = Σ_{q∈S} G_σs(‖p−q‖) · G_σr(|f(p)−f(q)|)"
        ),
        "kernel": (
            "Uyarlanır — her piksel için farklıdır:\n"
            "  w(p,q) = exp(−‖p−q‖²/2σ_s²) · exp(−(f(p)−f(q))²/2σ_r²)\n"
            "           └── uzamsal yakınlık ──┘ └── ton benzerliği ──┘"
        ),
        "theory": (
            "Gauss süzgeci yalnız konuma bakar; bu yüzden kenarın karşı "
            "yanındaki çok farklı bir pikseli de ortalamaya katar ve kenarı "
            "bulanıklaştırır.\n\n"
            "Bilateral süzgeç ağırlığı iki çarpana ayırır: piksel hem "
            "uzamsal olarak yakın hem de tonca benzer olmalıdır. Bir kenarın "
            "diğer yanındaki piksel için ton farkı büyüktür, dolayısıyla "
            "G_σr terimi neredeyse sıfır olur ve o piksel ortalamaya "
            "katılmaz.\n\n"
            "Sonuç: düz bölgelerde Gauss gibi davranır (gürültüyü siler), "
            "kenarlarda ise filtre kendiliğinden kenarın bir yanıyla "
            "sınırlanır. Bu yüzden 'kenar koruyan yumuşatma' denir.\n\n"
            "Doğrusal değildir ve ayrılabilir değildir; naif hesaplama "
            "maliyeti O(H·W·k²)'dir. Bu uygulamada k² pencere kayması "
            "üzerinden vektörleştirilerek Python döngüsü görüntü boyutundan "
            "bağımsız hale getirilmiştir."
        ),
        "params": (
            "σ_s (uzamsal) : filtrenin kaç piksellik alana baktığı.\n"
            "                Büyük σ_s → daha geniş yumuşatma.\n"
            "σ_r (yoğunluk): hangi ton farkının 'kenar' sayılacağı.\n"
            "                σ_r küçük  → çok az yumuşatma, her fark kenar sayılır\n"
            "                σ_r büyük  → Gauss filtresine yakınsar\n"
            "n (pencere)   : hesaplanan komşuluk boyutu, ≈ 2·(3σ_s)+1 seçilmeli."
        ),
        "effect": (
            "Gürültü ve doku silinirken nesne sınırları keskin kalır. "
            "Aşırı kullanımda karakteristik 'yağlı boya / cartoon' görünümü."
        ),
    },

    # =====================================================================
    "histeq": {
        "title": "Histogram Eşitleme",
        "formula": (
            "p_r(r_k) = n_k / N          (normalize histogram)\n"
            "s_k = T(r_k) = Σ_{j=0}^{k} p_r(r_j)     (KDF)\n"
            "g(x,y) = T( f(x,y) )"
        ),
        "kernel": (
            "Uzamsal çekirdek yoktur — noktasal (point-wise) bir\n"
            "yoğunluk dönüşümüdür. Transfer eğrisi görüntünün kendi\n"
            "kümülatif dağılım fonksiyonudur."
        ),
        "theory": (
            "Olasılık kuramından bir sonuç: eğer r rastgele değişkeninin "
            "kümülatif dağılım fonksiyonu F_r ise, s = F_r(r) dönüşümü "
            "[0,1] üzerinde düzgün (uniform) dağılımlıdır.\n\n"
            "Görüntüye uygulandığında bu, yoğunluk histogramını olabildiğince "
            "düzleştirmek anlamına gelir. Sürekli halde sonuç tam düzgün "
            "dağılımdır; ayrık halde ise aynı gri seviyedeki pikseller "
            "ayrılamayacağı için ancak yaklaşık düzleşme elde edilir.\n\n"
            "Dönüşümün önemli bir özelliği monoton artan olmasıdır: iki "
            "pikselin parlaklık sıralaması korunur, yalnız aralarındaki "
            "mesafe değişir. Histogramın yoğun olduğu bölgelerde KDF'nin "
            "eğimi diktir, dolayısıyla o ton aralığı genişletilir — "
            "kontrast, piksellerin en çok bulunduğu yere yeniden dağıtılır.\n\n"
            "Sınırlaması: küresel bir işlemdir. Görüntünün bir bölgesi çok "
            "karanlık, başka bir bölgesi çok parlaksa tek bir eğri ikisine "
            "birden uyamaz. Bu, CLAHE'nin çıkış noktasıdır."
        ),
        "params": (
            "Parametresizdir; dönüşüm tamamen görüntünün kendi\n"
            "histogramından türetilir."
        ),
        "effect": (
            "Genel kontrast belirgin artar, düşük kontrastlı görüntüler "
            "açılır. Yan etki: düz bölgelerdeki gürültü de yükseltilir, "
            "histogramda taraklanma (boşluklar) oluşur."
        ),
    },

    # =====================================================================
    "clahe": {
        "title": "CLAHE — Kontrast Sınırlı Uyarlanır Histogram Eşitleme",
        "formula": (
            "Her T bloğu için:\n"
            "  h'(i) = min(h(i), C·M/L)                 (kırpma)\n"
            "  E = Σ_i max(h(i) − C·M/L, 0)             (taşan kütle)\n"
            "  h''(i) = h'(i) + E/L                     (yeniden dağıtım)\n"
            "  s = Σ_{j≤i} h''(j) / Σ_j h''(j)          (blok KDF'si)"
        ),
        "kernel": (
            "Blok başına ayrı transfer eğrisi.\n"
            "M = bloktaki piksel sayısı, L = 256 gri seviye,\n"
            "C = kırpma sınırı (clip limit)."
        ),
        "theory": (
            "CLAHE, küresel histogram eşitlemenin iki sorununu çözer.\n\n"
            "Birincisi yerellik: görüntü küçük bloklara (tile) bölünür ve her "
            "blok kendi KDF'si ile eşitlenir. Böylece karanlık bir köşe, "
            "parlak bir bölgeden bağımsız olarak açılır.\n\n"
            "İkincisi gürültü yükseltme: neredeyse düz bir blokta histogram "
            "tek bir tepeye yığılır; KDF'nin o noktadaki eğimi çok diktir ve "
            "eşitleme, sensör gürültüsünü tüm ton aralığına yayarak devasa "
            "biçimde büyütür. Kırpma sınırı C tam olarak bu eğimi "
            "sınırlandırır — histogramın hiçbir kutusu C·M/L değerini "
            "aşamaz, dolayısıyla transfer eğrisinin eğimi de C ile sınırlıdır.\n\n"
            "Kırpılan kütle atılmaz, tüm kutulara eşit dağıtılır; böylece "
            "toplam piksel sayısı ve dönüşümün monotonluğu korunur.\n\n"
            "Not: özgün CLAHE, blok sınırlarındaki süreksizliği gidermek için "
            "komşu blokların eğrileri arasında çift doğrusal enterpolasyon "
            "yapar. Bu uygulama — depodaki scriptte olduğu gibi — blok başına "
            "doğrudan eşitleme yapar, bu yüzden büyük blok boyutlarında "
            "blok sınırları görülebilir."
        ),
        "params": (
            "C (kırpma sınırı):\n"
            "  C = 1   : neredeyse hiç kontrast artışı yok\n"
            "  C = 2-3 : tipik, dengeli kullanım\n"
            "  C > 5   : agresif kontrast, gürültü belirgin\n"
            "T (blok boyutu):\n"
            "  Küçük T : çok yerel kontrast, blok yapısı ve halo riski\n"
            "  Büyük T : küresel eşitlemeye yakınsar"
        ),
        "effect": (
            "Gölge ve parlak alanlardaki detaylar aynı anda ortaya çıkar. "
            "Tıbbi görüntüleme ve uydu görüntülerinde standart yöntemdir."
        ),
    },

    # =====================================================================
    "stretch": {
        "title": "Kontrast Germe (Percentile Stretch)",
        "formula": (
            "r_low  = P_pmin(f),   r_high = P_pmax(f)\n"
            "g = (f − r_low) / (r_high − r_low) · (max − min) + min\n"
            "g = clip(g, min, max)"
        ),
        "kernel": (
            "Doğrusal noktasal dönüşüm — transfer eğrisi bir doğrudur:\n"
            "  g = a·f + b,   a = (max−min)/(r_high−r_low)"
        ),
        "theory": (
            "En basit kontrast iyileştirme: mevcut değer aralığı hedef "
            "aralığa doğrusal olarak gerilir.\n\n"
            "Kritik ayrıntı, gerdirme sınırları için minimum ve maksimum "
            "yerine YÜZDELİK değerlerin kullanılmasıdır. Tek bir ölü piksel "
            "ya da bir güneş parıltısı, gerçek min/max'ı uçlara taşır ve "
            "gerdirme etkisiz kalır. %2–%98 gibi yüzdelikler bu aykırı "
            "değerleri dışarıda bırakır.\n\n"
            "Bu sınırların dışında kalan pikseller kırpılır (clip): "
            "alttakiler minimuma, üsttekiler maksimuma sabitlenir. Yani "
            "kontrast kazancı, uçlardaki bilginin kalıcı kaybı pahasına "
            "elde edilir.\n\n"
            "Histogram eşitlemeden farkı: dönüşüm doğrusaldır. Ton "
            "ilişkileri korunur, histogramın şekli değişmez — yalnız "
            "yatayda ölçeklenir. Bu yüzden görüntü 'doğal' kalır."
        ),
        "params": (
            "p_min, p_max (yüzdelikler):\n"
            "  (0, 100)  : saf min-max gerdirme, aykırı değerlere savunmasız\n"
            "  (2, 98)   : uzaktan algılamada standart\n"
            "  (5, 95)   : agresif, daha çok kırpma ve daha yüksek kontrast"
        ),
        "effect": (
            "Soluk, düşük kontrastlı görüntüler canlanır. Histogram "
            "eşitlemenin aksine yapay bir görünüm oluşturmaz."
        ),
    },

    # =====================================================================
    "gamma": {
        "title": "Gama Düzeltmesi (Kuvvet Yasası Dönüşümü)",
        "formula": (
            "s = c · r^γ,   r ∈ [0,1]\n"
            "Bu uygulamada c = 1, sonra özgün aralığa geri ölçeklenir."
        ),
        "kernel": (
            "Noktasal, doğrusal olmayan transfer eğrisi:\n"
            "  γ < 1  → yukarı bükülen eğri (görüntü açılır)\n"
            "  γ = 1  → doğru (değişiklik yok)\n"
            "  γ > 1  → aşağı bükülen eğri (görüntü koyulaşır)"
        ),
        "theory": (
            "Kuvvet yasası dönüşümü iki ayrı gereksinimden doğar.\n\n"
            "Birincisi donanımsaldır: CRT ekranların ışık çıkışı giriş "
            "voltajıyla yaklaşık L ∝ V^2.2 ilişkisindedir. Görüntüyü "
            "1/2.2 ≈ 0.45 üssü ile önceden düzelterek bu doğrusal olmayan "
            "yanıt telafi edilir. sRGB standardı bu yüzden gama kodludur.\n\n"
            "İkincisi algısaldır: Weber–Fechner yasasına göre insan gözünün "
            "parlaklık algısı yaklaşık logaritmiktir — karanlık tonlardaki "
            "küçük farkları, aydınlık tonlardakinden çok daha iyi ayırt "
            "ederiz. γ < 1 dönüşümü, sayısal kod değerlerinin daha büyük "
            "bölümünü karanlık bölgeye ayırarak bu duyarlılığa uyum sağlar.\n\n"
            "Dönüşüm monoton artandır, dolayısıyla piksellerin parlaklık "
            "sıralaması hiç bozulmaz; yalnız tonlar arası mesafeler yeniden "
            "dağıtılır. Türev ds/dr = γr^(γ−1) yerel kontrast kazancını verir: "
            "γ < 1 için karanlıkta kazanç yüksek, aydınlıkta düşüktür."
        ),
        "params": (
            "γ = 0.4-0.5 : karanlık görüntüleri güçlü biçimde açar\n"
            "γ = 0.8     : hafif açma\n"
            "γ = 1.0     : değişiklik yok\n"
            "γ = 1.5-2.5 : aşırı pozlanmış görüntüleri koyulaştırır"
        ),
        "effect": (
            "Genel parlaklık ve ton dağılımı değişir. Kırpma olmadığı için "
            "kontrast germenin aksine hiçbir uç bilgi kaybolmaz."
        ),
    },

    # =====================================================================
    "log": {
        "title": "Logaritmik Dönüşüm",
        "formula": (
            "s = c · log(1 + r)\n"
            "ardından [min, max] aralığına yeniden ölçekleme"
        ),
        "kernel": (
            "Noktasal, içbükey (concave) transfer eğrisi.\n"
            "Türev: ds/dr = c/(1+r) — r arttıkça kazanç azalır."
        ),
        "theory": (
            "Logaritmik dönüşüm dinamik aralık sıkıştırması için "
            "kullanılır. Eğrinin eğimi girişle ters orantılıdır: karanlık "
            "tonlarda (r ≈ 0) kazanç c'ye yakındır, parlak tonlarda "
            "(r büyük) kazanç düşer.\n\n"
            "Sonuç, dar bir karanlık ton aralığının geniş bir çıkış "
            "aralığına yayılması, buna karşılık geniş bir parlak aralığın "
            "dar bir aralığa sıkıştırılmasıdır.\n\n"
            "Klasik uygulaması Fourier spektrumunun görselleştirilmesidir: "
            "|F(u,v)| değerleri 0 ile 10⁶ arasında değişebilir; doğrusal "
            "gösterimde yalnız DC bileşeni görünür. log(1+|F|) tüm spektrumu "
            "görünür kılar.\n\n"
            "1 + r biçimi, r = 0'da log'un tanımsız olmasını önler ve "
            "s(0) = 0 koşulunu sağlar. Bu uygulamada ayrıca girdi negatif "
            "olmayacak biçimde ötelenir."
        ),
        "params": (
            "c (ölçek katsayısı): çıktı yeniden ölçeklendiği için görsel\n"
            "    etkisi sınırlıdır; esas iş eğrinin biçiminde yapılır.\n"
            "    Büyük c değerleri karanlık bölgedeki açılmayı artırır."
        ),
        "effect": (
            "Karanlık bölgelerdeki gizli detaylar ortaya çıkar, parlak "
            "bölgeler sıkışır. Yüksek dinamik aralıklı verilerde etkilidir."
        ),
    },

    # =====================================================================
    "highboost": {
        "title": "High-Boost / Unsharp Masking",
        "formula": (
            "f_blur = h_lp * f                (bulanık kopya)\n"
            "g_mask = f − f_blur              (maske = yüksek frekans)\n"
            "g = f + k · g_mask\n"
            "        = (1+k)·f − k·f_blur"
        ),
        "kernel": (
            "h_lp : n×n kutu ortalama (uniform filter)\n"
            "Eşdeğer tek çekirdek (k=1, 3×3 için):\n"
            "  (1/9) ·\n"
            "   -1  -1  -1\n"
            "   -1  17  -1\n"
            "   -1  -1  -1"
        ),
        "theory": (
            "Adı karanlık oda tekniğinden gelir: negatifin bulanık bir "
            "pozitif kopyası ('unsharp mask') ile üst üste bindirilerek "
            "keskinleştirme yapılırdı.\n\n"
            "Matematiksel mantık ayrıştırmadır. Herhangi bir görüntü, "
            "alçak frekans ve yüksek frekans bileşenlerinin toplamıdır:\n\n"
            "  f = f_lp + f_hp   ⟹   f_hp = f − f_lp\n\n"
            "Maske tam olarak f_hp'dir — kenarlar, doku ve gürültü. Bunu k "
            "katsayısıyla geri eklemek, yüksek frekansları (1+k) kat "
            "yükseltmek demektir. Yani işlem frekans alanında bir yükseltme "
            "(boost) filtresidir:\n\n"
            "  H(u,v) = 1 + k·(1 − H_lp(u,v))\n\n"
            "k = 1 iken klasik unsharp masking, k > 1 iken high-boost "
            "filtreleme adını alır.\n\n"
            "Laplacian keskinleştirme ile akrabadır: h_lp Gauss seçilirse "
            "maske, Laplacian-of-Gaussian'a yaklaşır."
        ),
        "params": (
            "k (destek katsayısı):\n"
            "  k = 0     : değişiklik yok\n"
            "  k ≈ 1     : klasik unsharp masking\n"
            "  k = 1.5-3 : güçlü keskinleştirme, halo riski\n"
            "n (bulanıklık penceresi):\n"
            "  Küçük n : ince detay keskinleşir\n"
            "  Büyük n : geniş ölçekli yerel kontrast artar (clarity etkisi)"
        ),
        "effect": (
            "Algılanan keskinlik belirgin artar. Aşırı k değerlerinde "
            "kenar çevresinde açık/koyu halka (halo, overshoot) belirir — "
            "bu Gibbs olayının uzamsal karşılığıdır."
        ),
    },

    # =====================================================================
    "brovey": {
        "title": "Brovey Dönüşümü (Pansharpening)",
        "formula": (
            "I = (1/N) · Σ_i MS_i           (yoğunluk)\n"
            "MS_i' = (MS_i / I) · PAN"
        ),
        "kernel": (
            "Bant başına oransal (multiplicative) yeniden ölçekleme.\n"
            "Bu GUI'de ilk bant PAN, kalan bantlar MS olarak alınır."
        ),
        "theory": (
            "Pansharpening'in amacı, yüksek uzamsal çözünürlüklü tek bantlı "
            "pankromatik görüntünün detayını, düşük çözünürlüklü çok bantlı "
            "görüntünün renk bilgisiyle birleştirmektir.\n\n"
            "Brovey yöntemi bir renk normalizasyonudur. MS_i / I oranı, "
            "pikselin toplam parlaklığından bağımsız 'saf renk' bileşenidir "
            "— bu oran bantlar arası göreli ilişkiyi, yani kromatik bilgiyi "
            "taşır. Bu oran PAN ile çarpılarak parlaklık bilgisi tamamen "
            "pankromatik banttan alınır.\n\n"
            "Yani işlem şudur: renk oranını koru, parlaklığı değiştir.\n\n"
            "Toplamı sabit tutan bu yapı sayesinde renk tonu (hue) iyi "
            "korunur ve sonuç görsel olarak canlıdır. Buna karşılık "
            "radyometrik doğruluk bozulur: çıktı piksel değerleri artık "
            "fiziksel yansıma değerleriyle orantılı değildir. Bu nedenle "
            "Brovey görsel yorumlama için uygundur, nicel analiz için değil."
        ),
        "params": (
            "Parametresizdir. En az 2 bantlı görüntü gerektirir\n"
            "(1 PAN + en az 1 MS)."
        ),
        "effect": (
            "Yüksek uzamsal detay ve doygun renkler. Belirgin renk "
            "sapması (spektral distorsiyon) riski vardır."
        ),
    },

    # =====================================================================
    "ihs": {
        "title": "IHS Dönüşümü (Pansharpening)",
        "formula": (
            "I = (R + G + B) / 3\n"
            "I' = PAN\n"
            "MS_i' = MS_i + (PAN − I)"
        ),
        "kernel": (
            "Toplamsal (additive) bileşen değiştirme.\n"
            "RGB → IHS → yoğunluğu değiştir → RGB"
        ),
        "theory": (
            "IHS (Intensity–Hue–Saturation) dönüşümü, RGB uzayındaki "
            "birbirine bağlı üç kanalı algısal olarak ayrık üç bileşene "
            "çevirir: parlaklık (I), renk tonu (H) ve doygunluk (S).\n\n"
            "Bu ayrıştırmanın değeri şudur: uzamsal detay neredeyse tamamen "
            "I bileşeninde, renk bilgisi ise H ve S bileşenlerinde bulunur. "
            "Dolayısıyla I'yı yüksek çözünürlüklü PAN ile değiştirip geri "
            "dönüştürmek, rengi bozmadan detay kazandırır.\n\n"
            "Uygulamada tam ileri-geri IHS dönüşümü yapmak yerine cebirsel "
            "olarak eşdeğer bir kısayol kullanılır: yoğunluk farkı "
            "(PAN − I) her banda eşit eklenir. Toplamsal olduğu için "
            "bantlar arası FARKLAR — yani hue ve saturation — tam olarak "
            "korunur.\n\n"
            "Yöntemin temel varsayımı, PAN'ın spektral duyarlılığının MS "
            "bantlarının toplamıyla örtüştüğüdür. Gerçek uydu "
            "sistemlerinde PAN çoğu zaman yakın kızılötesini de kapsar; "
            "bu uyuşmazlık bitki örtüsünde karakteristik renk sapmasına "
            "yol açar."
        ),
        "params": (
            "Parametresizdir. En az 3 MS bandı beklenir; daha az bant\n"
            "varsa mevcut bantlar tekrarlanarak tamamlanır."
        ),
        "effect": (
            "Uzamsal detay yüksek, renk tonu Brovey'e göre daha iyi korunur. "
            "Spektral uyuşmazlıkta renk sapması görülebilir."
        ),
    },

    # =====================================================================
    "pca": {
        "title": "PCA Tabanlı Pansharpening",
        "formula": (
            "Σ = Cov(MS)\n"
            "Σ·v_k = λ_k·v_k              (özdeğer ayrışımı)\n"
            "PC = MS · V                  (ileri dönüşüm)\n"
            "PC_1 ← PAN (istatistik eşlenmiş)\n"
            "MS' = PC · Vᵀ                (geri dönüşüm)"
        ),
        "kernel": (
            "Bantlar arası kovaryans matrisinin özvektörleriyle\n"
            "dik (ortogonal) dönüşüm. V sütunları λ'ya göre azalan sırada."
        ),
        "theory": (
            "Temel Bileşenler Analizi, bantları istatistiksel olarak "
            "ilişkisiz (uncorrelated) yeni bir koordinat sistemine taşır. "
            "Kovaryans matrisi simetrik olduğundan özvektörleri diktir ve "
            "dönüşüm tersinirdir: V⁻¹ = Vᵀ.\n\n"
            "Çok bantlı uydu görüntülerinde bantlar birbiriyle güçlü "
            "korelasyon içindedir; bu yüzden birinci temel bileşen PC₁ "
            "toplam varyansın çoğunu (tipik olarak %85–95) taşır ve "
            "esasen bantlar arası ORTAK bilgiyi — yani parlaklık ve "
            "uzamsal yapıyı — temsil eder. Renk bilgisi ise PC₂, PC₃ gibi "
            "sonraki bileşenlere düşer.\n\n"
            "Bu, IHS'deki I bileşeninin istatistiksel karşılığıdır. Fark "
            "şu ki dönüşüm sabit değil, verinin kendisinden öğrenilir; bu "
            "yüzden PCA keyfi sayıda banda uygulanabilir.\n\n"
            "Kritik ayrıntı: PAN doğrudan PC₁ yerine konursa ölçek uyuşmaz "
            "ve geri dönüşümde radyometri bozulur. Bu uygulamada PAN, "
            "PC₁'in ortalama ve standart sapmasına eşlenerek yerleştirilir:\n\n"
            "  PAN' = (PAN − μ_PAN)/σ_PAN · σ_PC₁ + μ_PC₁"
        ),
        "params": (
            "Parametresizdir. Anlamlı sonuç için en az 3 bant önerilir\n"
            "(1 PAN + en az 2 MS)."
        ),
        "effect": (
            "Bant sayısı fazla olduğunda IHS'den daha iyi spektral koruma "
            "sağlar. PC₁ varyansın büyük kısmını taşımıyorsa sonuç bozulur."
        ),
    },
}


def get_explanation(key):
    """Bir filtrenin açıklama sözlüğünü döndürür."""
    return EXPLANATIONS.get(key, {
        "title": "Açıklama bulunamadı",
        "formula": "-",
        "kernel": "-",
        "theory": "Bu filtre için henüz açıklama yazılmamış.",
        "params": "-",
        "effect": "-",
    })


def format_explanation(key):
    """Açıklamayı metin kutusunda gösterilecek biçimde düzenler."""
    e = get_explanation(key)
    parts = [
        e["title"],
        "=" * 46,
        "",
        "▸ BAĞINTI",
        e["formula"],
        "",
        "▸ ÇEKİRDEK / DÖNÜŞÜM",
        e["kernel"],
        "",
        "▸ MATEMATİKSEL ANLAM",
        e["theory"],
        "",
        "▸ PARAMETRELER",
        e["params"],
        "",
        "▸ GÖRÜNTÜ ÜZERİNDEKİ ETKİ",
        e["effect"],
    ]
    return "\n".join(parts)
