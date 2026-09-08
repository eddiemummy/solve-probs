# 🎯 Soru Çöz & Rozet Kazan

Ortaokul/lise dersleri (İngilizce, Matematik, Fizik, Kimya, Biyoloji, Fen Bilimleri) için
soru çözme ve rozet platformu. **Streamlit + Ollama Cloud (`gpt-oss:120b-cloud`)**.

## Özellikler
- Öğrenci adını girer, ders + seviye seçer, **konuyu kendi yazar**.
- Seviye: İngilizce → Elementary/Intermediate, diğerleri → LGS/TYT/AYT.
- Her testte **30 çoktan seçmeli soru**, **45 dk** süre (canlı geri sayım).
- **Rozetler:** ≤%60 Bronz · %60–75 Gümüş · %75–95 Altın · %95–100 Diamond.
- **Altın ve üzeri** → sonraki konuya geçiş. Altın alınmadıkça **her test farklı** üretilir
  (önceki sorular modele "tekrarlama" diye verilir, SQLite'ta saklanır).
- **Kopyalama engeli:** mouse ile seçme, sağ tık, Ctrl+C/X/A kapalı.
- Sonuç + rozet **PNG belge** olarak indirilebilir.

## Kurulum
```bash
pip install -r requirements.txt
```
`.streamlit/secrets.toml` içine Ollama Cloud API anahtarını yaz:
```toml
OLLAMA_BASE_URL = "https://ollama.com"
OLLAMA_API_KEY = "senin_anahtarin"
```

## Çalıştırma
```bash
streamlit run app.py
```

## Öğrencilere sunma (farklı şehirler)
1. Bu klasörü GitHub'a yükle.
2. [share.streamlit.io](https://share.streamlit.io) → New app → repo'yu seç.
3. **Settings → Secrets** kısmına `OLLAMA_API_KEY`'i gir (koda gömme).
4. Çıkan linki öğrencilerine ver.

> Not: Kopyalama engeli mouse/klavye kopyasını keser ama ekran görüntüsünü engelleyemez;
> 45 dk süre sınırı ek caydırıcıdır.
