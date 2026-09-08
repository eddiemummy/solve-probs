"""Sonuç + rozet sertifikasını PNG olarak üretir."""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

ROZET_RENK = {
    "Bronz": (176, 141, 87),
    "Gümüş": (158, 165, 173),
    "Altın": (212, 175, 55),
    "Diamond": (110, 200, 220),
}


def _font(boyut, kalin=False):
    adaylar = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if kalin
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if kalin
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for a in adaylar:
        try:
            return ImageFont.truetype(a, boyut)
        except OSError:
            continue
    return ImageFont.load_default()


def _ortala(draw, y, metin, font, renk, w):
    b = draw.textbbox((0, 0), metin, font=font)
    draw.text(((w - (b[2] - b[0])) / 2, y), metin, font=font, fill=renk)


def sertifika_png(ogrenci, ders, konu, seviye, rozet, dogru, toplam, yuzde, tarih):
    W, H = 1000, 700
    renk = ROZET_RENK.get(rozet, (120, 120, 120))
    img = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)

    # çerçeve
    d.rectangle([15, 15, W - 15, H - 15], outline=renk, width=6)
    d.rectangle([28, 28, W - 28, H - 28], outline=(220, 220, 218), width=1)

    _ortala(d, 55, "SINAV SONUÇ BELGESİ", _font(34, True), (40, 40, 40), W)
    _ortala(d, 110, f"{ders} • {konu} • {seviye}", _font(22), (90, 90, 90), W)

    # rozet madalyonu
    cx, cy, r = W // 2, 290, 90
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=renk)
    d.ellipse([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10],
              outline=(255, 255, 255), width=3)
    _ortala(d, cy - 22, rozet.upper(), _font(30, True), (255, 255, 255), W)

    _ortala(d, 415, ogrenci, _font(40, True), (30, 30, 30), W)
    _ortala(d, 480, f"{dogru} / {toplam} doğru   —   %{yuzde}", _font(26), (60, 60, 60), W)

    mesaj = ("Tebrikler! Bir sonraki konuya geçebilirsin."
             if rozet in ("Altın", "Diamond")
             else "Altın rozet için biraz daha çalış!")
    _ortala(d, 545, mesaj, _font(20), renk, W)
    _ortala(d, H - 70, tarih, _font(16), (150, 150, 150), W)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
