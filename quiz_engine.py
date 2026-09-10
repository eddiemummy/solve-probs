"""Soru üretimi, rozet mantığı ve ilerleme kaydı."""
import json
import re
import sqlite3
import hashlib
from pathlib import Path

from langchain_ollama import ChatOllama

DB_PATH = Path(__file__).parent / "ilerleme.db"

# ---- Ders / seviye tanımları ---------------------------------------------
DERSLER = ["İngilizce", "Matematik", "Fizik", "Kimya", "Biyoloji", "Fen Bilimleri"]

# İngilizce farklı seviye setine sahip
SEVIYELER = {
    "İngilizce": ["Elementary", "Intermediate"],
    "_default": ["LGS", "TYT", "AYT"],
}

SORU_SAYISI = 30
SURE_DK = 45


def seviyeler_icin(ders: str):
    return SEVIYELER.get(ders, SEVIYELER["_default"])


# ---- Rozet mantığı --------------------------------------------------------
def rozet_hesapla(dogru: int, toplam: int = SORU_SAYISI):
    """Yüzdeye göre rozet döndürür.
    <=%60 Bronz | %60-75 Gümüş | %75-95 Altın | %95-100 Diamond
    """
    yuzde = (dogru / toplam) * 100 if toplam else 0
    if yuzde >= 95:
        rozet = "Diamond"
    elif yuzde >= 75:
        rozet = "Altın"
    elif yuzde >= 60:
        rozet = "Gümüş"
    else:
        rozet = "Bronz"
    return rozet, round(yuzde, 1)


def gecti_mi(rozet: str) -> bool:
    """Altın ve üzeri sonraki konuya geçirir."""
    return rozet in ("Altın", "Diamond")


# ---- Soru üretimi ---------------------------------------------------------
def _model(base_url: str, api_key: str, model_ad: str = "gpt-oss:120b-cloud"):
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return ChatOllama(
        model=model_ad,
        base_url=base_url,
        client_kwargs={"headers": headers},
        temperature=0.8,  # çeşitlilik için yüksek
    )


def _json_ayikla(metin: str):
    """Model çıktısından JSON dizisini güvenli çıkarır."""
    metin = metin.strip()
    metin = re.sub(r"^```(json)?", "", metin).strip()
    metin = re.sub(r"```$", "", metin).strip()
    basla = metin.find("[")
    bitir = metin.rfind("]")
    if basla != -1 and bitir != -1:
        metin = metin[basla : bitir + 1]
    return json.loads(metin)


def sorular_uret(ders, konu, seviye, base_url, api_key, kacinilacak=None):
    """30 çoktan seçmeli soruyu tek çağrıda JSON olarak üretir.

    kacinilacak: daha önce sorulmuş soru metinleri (tekrarı engellemek için).
    Dönen: [{"soru":..., "secenekler":["A) ..","B) .."...], "dogru":"B"}, ...]
    """
    dil_notu = ""
    if ders == "İngilizce":
        dil_notu = (
            "Soru YÖNERGESİ/AÇIKLAMASI Türkçe yazılsın (öğrenciye ne yapması gerektiğini "
            "Türkçe anlat), ancak sorudaki İngilizce cümle/metin ve 4 şıkkın tamamı "
            "İngilizce olsun. Seviye: %s öğrencisine uygun." % seviye
        )
    else:
        dil_notu = "Sorular Türkçe olsun; %s sınavı düzeyinde ve müfredatına uygun." % seviye

    kacinma_notu = ""
    if kacinilacak:
        ornekler = "\n".join(f"- {s}" for s in list(kacinilacak)[:60])
        kacinma_notu = (
            "\nAŞAĞIDAKİ SORULARI VE ÇOK BENZERLERİNİ ASLA TEKRARLAMA:\n" + ornekler
        )

    zorluk_notu = {
        "LGS": "LGS (8. sınıf) gerçek sınav düzeyinde: yeni nesil, akıl yürütme ve problem "
               "içeren, çoğu çok adımlı sorular. Günlük hayat/gerçek durum senaryoları kullan.",
        "TYT": "TYT gerçek sınav düzeyinde: kavramsal, yorum ve işlem birleştiren orta-zor sorular.",
        "AYT": "AYT gerçek sınav düzeyinde: ileri düzey, çok adımlı, analiz gerektiren zor sorular.",
        "Elementary": "A1-A2 seviyesinde ama basmakalıp olmayan, bağlam içeren sorular.",
        "Intermediate": "B1-B2 seviyesinde, bağlam ve anlam ayrımı gerektiren sorular.",
    }.get(seviye, "Sınav düzeyinde, düşündüren sorular.")

    prompt = f"""Sen deneyimli bir sınav hazırlama uzmanısın.
Ders: {ders}
Konu: {konu}
Seviye: {seviye}
{dil_notu}

ZORLUK: {zorluk_notu}

{SORU_SAYISI} adet çoktan seçmeli soru hazırla. Her sorunun 4 şıkkı (A, B, C, D) olsun ve yalnızca bir doğru cevabı olsun.

ÖNEMLİ KURALLAR:
- Sorular ASLA basit/ezber olmasın. Örneğin "üslü sayılar" konusunda sadece "2^3 kaçtır?" gibi tek işlemli sorular YASAK.
- Bunun yerine: çok adımlı işlemler, üslü ifadelerde sadeleştirme, denklem, günlük hayat problemleri, tablo/grafik yorumlama, karşılaştırma ve akıl yürütme içeren sorular kur.
- Çeldiriciler (yanlış şıklar) mantıklı ve öğrencinin yapabileceği tipik hatalara dayalı olsun.
- Sorular orta zordan zora doğru sıralansın ve birbirinden farklı olsun.{kacinma_notu}

Her soru için "aciklama" alanında, doğru cevabın NEDEN doğru olduğunu 1-2 cümlelik kısa bir çözümle Türkçe yaz.

SADECE aşağıdaki formatta geçerli bir JSON dizisi döndür, başka hiçbir açıklama yazma:
[
  {{"soru": "Soru metni", "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."], "dogru": "A", "aciklama": "Doğru cevabın kısa çözümü"}},
  ...
]
Tam olarak {SORU_SAYISI} soru olmalı."""

    model = _model(base_url, api_key)
    cevap = model.invoke(prompt)
    icerik = cevap.content if hasattr(cevap, "content") else str(cevap)
    sorular = _json_ayikla(icerik)

    # temizle / doğrula
    temiz = []
    for s in sorular:
        if not all(k in s for k in ("soru", "secenekler", "dogru")):
            continue
        if len(s["secenekler"]) < 2:
            continue
        s["dogru"] = str(s["dogru"]).strip().upper()[:1]
        s["aciklama"] = str(s.get("aciklama", "")).strip()
        temiz.append(s)
    return temiz[:SORU_SAYISI]


# ---- İlerleme (SQLite) ----------------------------------------------------
def _con():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS ilerleme (
            ogrenci TEXT, ders TEXT, konu TEXT, seviye TEXT,
            en_iyi_rozet TEXT, gecti INTEGER, tarih TEXT,
            PRIMARY KEY (ogrenci, ders, konu, seviye)
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS gorulen_sorular (
            anahtar TEXT PRIMARY KEY, soru TEXT
        )"""
    )
    return con


def gorulen_sorulari_al(ogrenci, ders, konu, seviye):
    con = _con()
    on = hashlib.md5(f"{ogrenci}|{ders}|{konu}|{seviye}".encode()).hexdigest()[:8]
    rows = con.execute(
        "SELECT soru FROM gorulen_sorular WHERE anahtar LIKE ?", (on + "%",)
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def gorulen_sorulari_kaydet(ogrenci, ders, konu, seviye, sorular):
    con = _con()
    on = hashlib.md5(f"{ogrenci}|{ders}|{konu}|{seviye}".encode()).hexdigest()[:8]
    for s in sorular:
        h = on + hashlib.md5(s["soru"].encode()).hexdigest()[:16]
        con.execute(
            "INSERT OR IGNORE INTO gorulen_sorular VALUES (?,?)", (h, s["soru"])
        )
    con.commit()
    con.close()


def tum_ilerleme():
    """Öğretmen paneli için tüm kayıtlar (en yeni önce)."""
    con = _con()
    rows = con.execute(
        "SELECT ogrenci, ders, konu, seviye, en_iyi_rozet, gecti, tarih "
        "FROM ilerleme ORDER BY tarih DESC"
    ).fetchall()
    con.close()
    return rows


def sonuc_kaydet(ogrenci, ders, konu, seviye, rozet):
    from datetime import datetime

    con = _con()
    mevcut = con.execute(
        "SELECT en_iyi_rozet FROM ilerleme WHERE ogrenci=? AND ders=? AND konu=? AND seviye=?",
        (ogrenci, ders, konu, seviye),
    ).fetchone()
    sira = {"Bronz": 1, "Gümüş": 2, "Altın": 3, "Diamond": 4}
    yeni = rozet
    if mevcut and sira.get(mevcut[0], 0) >= sira.get(rozet, 0):
        yeni = mevcut[0]
    con.execute(
        "INSERT OR REPLACE INTO ilerleme VALUES (?,?,?,?,?,?,?)",
        (ogrenci, ders, konu, seviye, yeni, int(gecti_mi(yeni)),
         datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    con.commit()
    con.close()
