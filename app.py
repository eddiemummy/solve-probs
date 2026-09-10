"""Ders Anlatma / Soru Çözme Platformu — Streamlit + Ollama Cloud."""
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import quiz_engine as qe
from certificate import sertifika_png

st.set_page_config(page_title="Soru Çöz & Rozet Kazan", page_icon="🎯", layout="centered")

# ---- Kopyalamayı engelleyen CSS + JS -------------------------------------
st.markdown(
    """
    <style>
    * { -webkit-user-select: none !important; -moz-user-select: none !important;
        -ms-user-select: none !important; user-select: none !important; }
    input, textarea { -webkit-user-select: text !important; user-select: text !important; }
    .soru-kutu { background:#ffffff !important; color:#1a1a1a !important;
        border:1px solid #e6e6e6; border-radius:10px;
        padding:14px 18px; margin:6px 0; font-size:17px; line-height:1.5; }
    .soru-kutu b { color:#1a1a1a !important; }
    .rozet-rozet { display:inline-block; padding:4px 14px; border-radius:20px;
        color:#fff; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)
components.html(
    """
    <script>
    const doc = window.parent.document;
    ['contextmenu','copy','cut','selectstart','dragstart'].forEach(e =>
        doc.addEventListener(e, ev => ev.preventDefault(), true));
    doc.addEventListener('keydown', ev => {
        if ((ev.ctrlKey||ev.metaKey) && ['c','x','a','s','p'].includes(ev.key.toLowerCase()))
            ev.preventDefault();
    }, true);
    </script>
    """,
    height=0,
)

# ---- Ayarlar (secrets) ----------------------------------------------------
BASE_URL = st.secrets.get("OLLAMA_BASE_URL", "https://ollama.com")
API_KEY = st.secrets.get("OLLAMA_API_KEY", "")
TEACHER_PIN = st.secrets.get("TEACHER_PIN", "1234")

ss = st.session_state
ss.setdefault("asama", "giris")
ss.setdefault("sorular", [])
ss.setdefault("baslangic", None)

# ---- Puanlama yardımcıları ------------------------------------------------
def _puanla():
    """Cevapları puanlar; (doğru, boş, yanlış sayıları ve inceleme listesi) döndürür."""
    dogru = bos = yanlis = 0
    inceleme = []  # yalnızca cevaplanmış YANLIŞ sorular
    for i, s in enumerate(ss.sorular):
        secilen = ss.get(f"r_{i}")
        if not secilen:
            bos += 1
            continue
        if secilen.strip()[:1].upper() == s["dogru"]:
            dogru += 1
            continue
        # cevaplanmış ama yanlış
        yanlis += 1
        dogru_metin = next(
            (o for o in s["secenekler"] if o.strip()[:1].upper() == s["dogru"]),
            s["dogru"],
        )
        inceleme.append({
            "no": i + 1,
            "soru": s["soru"],
            "secilen": secilen,
            "dogru_metin": dogru_metin,
            "aciklama": s.get("aciklama", ""),
        })
    return dogru, bos, yanlis, inceleme


def _testi_bitir(sure_asildi):
    dogru, bos, yanlis, inceleme = _puanla()
    rozet, yuzde = qe.rozet_hesapla(dogru, len(ss.sorular))
    qe.sonuc_kaydet(ss.ad, ss.ders, ss.konu, ss.seviye, rozet)
    ss.update(asama="sonuc", dogru=dogru, bos=bos, yanlis=yanlis,
              toplam=len(ss.sorular), rozet=rozet, yuzde=yuzde,
              sure_asildi=sure_asildi, inceleme=inceleme)


# ==========================================================================
# ROL SEÇİMİ (Öğrenci / Öğretmen)
# ==========================================================================
rol = st.sidebar.radio("Rol", ["👩‍🎓 Öğrenci", "👨‍🏫 Öğretmen"])

# ==========================================================================
# ÖĞRETMEN PANELİ
# ==========================================================================
if rol == "👨‍🏫 Öğretmen":
    st.title("👨‍🏫 Öğretmen Paneli")
    pin = st.sidebar.text_input("Öğretmen PIN", type="password")
    if pin != TEACHER_PIN:
        st.info("Öğrenci ilerlemelerini görmek için sol menüden PIN gir.")
        st.stop()

    rows = qe.tum_ilerleme()
    if not rows:
        st.warning("Henüz kayıt yok.")
        st.stop()

    veri = [
        {"Öğrenci": r[0], "Ders": r[1], "Konu": r[2], "Seviye": r[3],
         "En İyi Rozet": r[4], "Geçti": "✅" if r[5] else "—", "Tarih": r[6]}
        for r in rows
    ]
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam kayıt", len(rows))
    c2.metric("Öğrenci sayısı", len({r[0] for r in rows}))
    c3.metric("Geçilen konu", sum(r[5] for r in rows))

    ogrenciler = ["(hepsi)"] + sorted({r[0] for r in rows})
    sec = st.selectbox("Öğrenciye göre filtrele", ogrenciler)
    if sec != "(hepsi)":
        veri = [v for v in veri if v["Öğrenci"] == sec]
    st.dataframe(veri, use_container_width=True, hide_index=True)
    st.stop()

# ==========================================================================
# ÖĞRENCİ AKIŞI
# ==========================================================================
st.title("🎯 Soru Çöz & Rozet Kazan")

# ---- 1) GİRİŞ -------------------------------------------------------------
if ss.asama == "giris":
    # Ders seçimi form DIŞINDA: değişince seviye seçenekleri anında güncellenir.
    ders = st.selectbox("Ders", qe.DERSLER)
    seviye = st.selectbox("Sınav Seviyesi", qe.seviyeler_icin(ders))
    st.caption("İngilizce: Elementary/Intermediate · diğer dersler: LGS/TYT/AYT")

    with st.form("giris_form"):
        ad = st.text_input("Adın Soyadın", placeholder="Örn: Ayşe Yılmaz")
        konu = st.text_input("Hangi konudan sınav olmak istiyorsun?",
                             placeholder="Örn: Üslü Sayılar / Present Perfect / Kuvvet")
        baslat = st.form_submit_button("🚀 Testi Oluştur (30 soru • 45 dk)")

    if baslat:
        if not ad.strip() or not konu.strip():
            st.warning("Lütfen adını ve konuyu gir.")
        elif not API_KEY:
            st.error("OLLAMA_API_KEY tanımlı değil. .streamlit/secrets.toml dosyasına ekle.")
        else:
            with st.spinner("Sorular hazırlanıyor..."):
                try:
                    kacin = qe.gorulen_sorulari_al(ad, ders, konu, seviye)
                    sorular = qe.sorular_uret(ders, konu, seviye, BASE_URL, API_KEY, kacin)
                    if len(sorular) < 5:
                        st.error("Yeterli soru üretilemedi, tekrar dene.")
                    else:
                        qe.gorulen_sorulari_kaydet(ad, ders, konu, seviye, sorular)
                        # eski cevapları temizle
                        for i in range(qe.SORU_SAYISI):
                            ss.pop(f"r_{i}", None)
                        ss.update(asama="test", sorular=sorular, baslangic=time.time(),
                                  ad=ad, ders=ders, seviye=seviye, konu=konu)
                        st.rerun()
                except Exception as e:
                    st.error(f"Soru üretilirken hata: {e}")

# ---- 2) TEST --------------------------------------------------------------
elif ss.asama == "test":
    st.markdown(f"**Öğrenci:** {ss.ad}  |  **{ss.ders} • {ss.konu} • {ss.seviye}**")

    # Sessiz süre denetçisi: her 5 sn'de kontrol eder, süre bitince otomatik gönderir.
    @st.fragment(run_every=5)
    def _denetci():
        if ss.asama != "test":
            return
        if (time.time() - ss.baslangic) > qe.SURE_DK * 60:
            _testi_bitir(sure_asildi=True)
            st.rerun()  # tüm uygulamayı yeniden çiz -> sonuç ekranı
    _denetci()

    kalan = qe.SURE_DK * 60 - (time.time() - ss.baslangic)
    components.html(
        f"""
        <div id="sayac" style="font:700 20px sans-serif;color:#c0392b;text-align:center;
             padding:6px;border:2px solid #c0392b;border-radius:8px;"></div>
        <script>
        let k = {int(max(kalan,0))};
        const el = document.getElementById('sayac');
        function tik() {{
            if (k <= 0) {{ el.innerHTML = '⏰ SÜRE DOLDU — sonuç hesaplanıyor...'; return; }}
            let d = Math.floor(k/60), s = k%60;
            el.innerHTML = '⏱️ Kalan Süre: ' + d + ':' + (s<10?'0':'') + s;
            k--; setTimeout(tik, 1000);
        }}
        tik();
        </script>
        """,
        height=55,
    )

    # Cevaplar canlı session_state'e yazılsın diye form kullanmıyoruz.
    for i, s in enumerate(ss.sorular):
        st.markdown(f"<div class='soru-kutu'><b>{i+1}.</b> {s['soru']}</div>",
                    unsafe_allow_html=True)
        st.radio(f"soru_{i}", s["secenekler"], index=None,
                 label_visibility="collapsed", key=f"r_{i}")

    cevaplanan = sum(1 for i in range(len(ss.sorular)) if ss.get(f"r_{i}"))
    st.progress(cevaplanan / len(ss.sorular),
                text=f"{cevaplanan}/{len(ss.sorular)} soru işaretlendi")

    if st.button("✅ Testi Bitir", type="primary"):
        _testi_bitir(sure_asildi=(time.time() - ss.baslangic) > qe.SURE_DK * 60)
        st.rerun()
    if st.button("↩️ İptal et"):
        ss.asama = "giris"
        st.rerun()

# ---- 3) SONUÇ -------------------------------------------------------------
elif ss.asama == "sonuc":
    renkler = {"Bronz": "#b08d57", "Gümüş": "#9ea5ad",
               "Altın": "#d4af37", "Diamond": "#6ec8dc"}
    r = ss.rozet
    if ss.get("sure_asildi"):
        st.info("⏰ Süre dolduğu için test otomatik gönderildi; işaretlenmeyen sorular yanlış sayıldı.")

    st.markdown(
        f"<h2>Sonuç: <span class='rozet-rozet' style='background:{renkler[r]}'>{r}</span></h2>",
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Doğru", ss.dogru)
    m2.metric("❌ Yanlış", ss.yanlis)
    m3.metric("⬜ Boş", ss.bos)
    m4.metric("Başarı", f"%{ss.yuzde}")
    st.caption(f"Toplam {ss.toplam} soru üzerinden.")

    if qe.gecti_mi(r):
        st.success("🎉 Altın ve üzeri! Bir sonraki konuya geçebilirsin.")
    else:
        st.warning("Altın rozet almadan yeni test üretilir. Aynı konuda tekrar dene, "
                   "sorular farklı olacak.")

    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    png = sertifika_png(ss.ad, ss.ders, ss.konu, ss.seviye, r,
                        ss.dogru, ss.toplam, ss.yuzde, tarih)
    st.image(png, caption="Sonuç belgen", use_container_width=True)
    st.download_button("⬇️ Belgeyi PNG olarak indir", png,
                       file_name=f"{ss.ad}_{ss.konu}_{r}.png", mime="image/png")

    # ---- Cevaplanmış yanlış soruların incelemesi -------------------------
    yanlislar = ss.get("inceleme", [])
    if yanlislar:
        st.markdown("---")
        st.subheader(f"❌ Yanlış cevapladığın sorular ({len(yanlislar)})")
        st.caption("Aşağıda yanlış işaretlediğin soruları ve doğru cevabı görebilirsin. "
                   "(Boş bıraktığın sorular burada gösterilmez.)")
        for x in yanlislar:
            with st.expander(f"Soru {x['no']}"):
                st.markdown(
                    f"<div class='soru-kutu'>{x['soru']}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Senin cevabın:** :red[{x['secilen']}]")
                st.markdown(f"**Doğru cevap:** :green[{x['dogru_metin']}]")
                if x["aciklama"]:
                    st.info("💡 " + x["aciklama"])
    elif ss.yanlis == 0 and ss.bos == 0:
        st.success("🌟 Tüm soruları doğru yaptın, harikasın!")

    c1, c2 = st.columns(2)
    if c1.button("🔁 Aynı konudan yeni test"):
        ss.asama = "giris"
        st.rerun()
    if c2.button("🏠 Başa dön"):
        for k in ("sorular", "baslangic"):
            ss.pop(k, None)
        ss.asama = "giris"
        st.rerun()
