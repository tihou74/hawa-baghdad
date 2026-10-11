#!/usr/bin/env python3
"""
intake — بوّابة استقبال الصور: تفحص قبل أن يقرأ أحد.

لماذا بوّابة واحدة
------------------
قراءة صورة يتجاوز أيٌّ من بُعديها ٢٠٠٠ بكسل تُفشل العمليّة بالخطأ
«At least one of the image dimensions exceed max allowed size». والأسوأ
أن الفشل يأتي **بعد** انتهاء العمل كله، فتضيع الجلسة ويُهدر الرصيد.

فالحراسة توضع في نقطة الاختناق التي تمرّ بها كل الصور — هذا الملف — لا
في كل سكربت على حِدة، لأن أي سكربت جديد سيتجاوز الحارس الموضعي.

ما تفعله
--------
  probe   : يقرأ الأبعاد من ترويسة الملف نفسه (بلا Pillow)، ويُخرج
            رمز خروج 2 إن وُجدت صورة واحدة متجاوزة — فيوقف أي أمر
            متسلسل بعده.
  sheet   : يبني لوحة تواصل (contact sheet) بخادم محلي ومتصفّح بلا
            واجهة، فتُصغَّر كل الصور إلى مُصغّرات. اللقطة الناتجة
            مضمونة تحت الحدّ، فتُقرأ بأمان حتى لو كان الأصل ٨٠٠٠px.
  rights  : قائمة فحص الحقوق لكل ملف، تُطبع ليمرّ عليها الإنسان.

الاستخدام
---------
  python3 tools/intake.py probe  media/incoming/*
  python3 tools/intake.py sheet  media/incoming .preview/incoming.png
  python3 tools/intake.py rights media/incoming
"""

import os
import re
import struct
import subprocess
import sys

LIMIT = 2000


# ----------------------------------------------------- قراءة الأبعاد بلا مكتبات

def dim_png(f):
    f.seek(16)
    return struct.unpack(">II", f.read(8))


def dim_gif(f):
    f.seek(6)
    w, h = struct.unpack("<HH", f.read(4))
    return w, h


def dim_jpeg(f):
    """المرور على مقاطع JPEG حتى SOF. لا يُفكّ أي بكسل."""
    f.seek(2)
    while True:
        b = f.read(1)
        if not b:
            return None
        if b != b"\xff":
            continue
        marker = f.read(1)
        while marker == b"\xff":
            marker = f.read(1)
        if not marker:
            return None
        m = marker[0]
        # SOF0..SOF15 ما عدا DHT(C4) و JPG(C8) و DAC(CC)
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            f.read(3)                      # الطول + الدقّة
            h, w = struct.unpack(">HH", f.read(4))
            return w, h
        length = struct.unpack(">H", f.read(2))[0]
        f.seek(length - 2, 1)


def dim_webp(f):
    f.seek(12)
    chunk = f.read(4)
    if chunk == b"VP8X":
        f.seek(24)
        d = f.read(6)
        w = (d[0] | d[1] << 8 | d[2] << 16) + 1
        h = (d[3] | d[4] << 8 | d[5] << 16) + 1
        return w, h
    if chunk == b"VP8 ":
        f.seek(26)
        w, h = struct.unpack("<HH", f.read(4))
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L":
        f.seek(21)
        b = struct.unpack("<I", f.read(4))[0]
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    return None


def dimensions(path):
    """يُرجع (w, h) أو None إن تعذّر — و None تعني **لا تقرأ**."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
            f.seek(0)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return dim_png(f)
            if head[:3] == b"GIF":
                return dim_gif(f)
            if head[:2] == b"\xff\xd8":
                return dim_jpeg(f)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                return dim_webp(f)
            if head[:4] == b"<svg" or b"<svg" in head:
                return ("svg", "svg")
    except Exception:
        return None
    return None


IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".heic"}


def walk(targets):
    out = []
    for t in targets:
        if os.path.isdir(t):
            for root, _, files in os.walk(t):
                for fn in sorted(files):
                    if os.path.splitext(fn)[1].lower() in IMG_EXT:
                        out.append(os.path.join(root, fn))
        elif os.path.isfile(t):
            out.append(t)
    return out


# ------------------------------------------------------------------- الأوامر

def cmd_probe(targets):
    files = walk(targets)
    if not files:
        print("لا صور في المسار المحدَّد.")
        return 0

    over, unknown, ok = [], [], []
    print("%-46s %-13s %-10s %s" % ("الملف", "الأبعاد", "الحجم", "الحالة"))
    print("-" * 92)
    for p in files:
        d = dimensions(p)
        size = "%.1fKB" % (os.path.getsize(p) / 1024)
        name = p if len(p) <= 45 else "…" + p[-44:]
        if d == ("svg", "svg"):
            print("%-46s %-13s %-10s %s" % (name, "متجهيّة", size, "آمنة — بلا أبعاد بكسل"))
            ok.append(p)
        elif d is None:
            print("%-46s %-13s %-10s %s" % (name, "?", size, "⛔ مجهولة — لا تُقرأ"))
            unknown.append(p)
        else:
            w, h = d
            flag = max(w, h) > LIMIT
            print("%-46s %-13s %-10s %s" % (
                name, "%dx%d" % (w, h), size,
                "⛔ متجاوزة (%d > %d)" % (max(w, h), LIMIT) if flag else "آمنة"))
            (over if flag else ok).append(p)

    print("-" * 92)
    print("آمنة: %d   متجاوزة: %d   مجهولة: %d" % (len(ok), len(over), len(unknown)))
    if over or unknown:
        print()
        print("⛔ لا تُقرأ الملفّات المعلَّمة مباشرةً. استعمل:")
        print("   python3 tools/intake.py sheet <dir> .preview/sheet.png")
        print("   فيُصغّرها المتصفّح إلى لوحة واحدة مضمونة تحت الحدّ.")
        return 2
    return 0


def cmd_sheet(src, dst, cols=6, thumb=150):
    """لوحة تواصل: المتصفّح يُصغّر، واللقطة وحدها تُقرأ."""
    files = walk([src])
    if not files:
        print("لا صور.")
        return 1

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    rows = []
    for p in files:
        d = dimensions(p)
        label = "%dx%d" % d if d and d != ("svg", "svg") else (
            "svg" if d == ("svg", "svg") else "?")
        over = bool(d and d != ("svg", "svg") and max(d) > LIMIT)
        rel = os.path.relpath(p, os.path.dirname(dst))
        rows.append(
            '<figure><img src="%s"><figcaption>%s<br>%s%s</figcaption></figure>'
            % (rel, os.path.basename(p)[:22], label,
               ' <b>OVER</b>' if over else ''))

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
        'body{margin:0;background:#fff;font:10px/1.3 monospace;padding:6px}'
        '.g{display:grid;grid-template-columns:repeat(%d,1fr);gap:5px}'
        'figure{margin:0;text-align:center}'
        'img{width:100%%;height:%dpx;object-fit:cover;display:block;background:#eee}'
        'figcaption{font-size:8px;color:#555;padding-top:2px}b{color:#c00}'
        '</style></head><body><div class="g">%s</div></body></html>'
        % (cols, thumb, "".join(rows)))

    page = os.path.join(os.path.dirname(dst) or ".", "_sheet.html")
    open(page, "w", encoding="utf-8").write(html)

    rowcount = (len(files) + cols - 1) // cols
    height = min(1900, rowcount * (thumb + 22) + 20)
    width = min(1900, cols * 230)

    chrome = None
    for c in ("chrome", "chromium", "google-chrome"):
        if subprocess.call(["which", c], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0:
            chrome = c
            break
    if not chrome:
        print("لا متصفّح متاح.")
        return 1

    subprocess.call([
        chrome, "--headless", "--no-sandbox", "--disable-gpu",
        "--hide-scrollbars", "--window-size=%d,%d" % (width, height),
        "--virtual-time-budget=12000", "--screenshot=" + dst,
        "file://" + os.path.abspath(page)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(dst):
        print("فشل بناء اللوحة.")
        return 1

    with open(dst, "rb") as f:
        f.seek(16)
        w, h = struct.unpack(">II", f.read(8))
    status = "آمنة للقراءة" if max(w, h) <= LIMIT else "⛔ متجاوزة — لا تقرأها"
    print("%s  %dx%d  %s  (%d صورة)" % (dst, w, h, status, len(files)))
    return 0 if max(w, h) <= LIMIT else 2


RIGHTS = [
    "علامة مائيّة أو إمضاء فنّان (افحص الزوايا والحواشي بتقريب ٢٠٠٪)",
    "شخص حقيقي يُمكن التعرّف عليه → يحتاج إذناً مكتوباً",
    "علامة تجاريّة لجهة أخرى (شعار، عبوة، لافتة، سيارة)",
    "عمل فنّي لشخص آخر (لوحة، تمثال، معمار حديث محمي)",
    "منيو أو مادّة تسويقيّة لمطعم منافس",
    "مصدرها جوجل أو بنترست أو إنستغرام → تُرفَض",
    "صورة أرشيفيّة: هل الترخيص يشمل الاستخدام التجاري؟",
]


def cmd_rights(src):
    files = walk([src])
    print("فحص الحقوق — %d ملفاً\n" % len(files))
    print("لكل ملف، تأكّد من غياب:")
    for i, r in enumerate(RIGHTS, 1):
        print("  %d) %s" % (i, r))
    print("\nالملفّات:")
    for p in files:
        print("  [ ] %s" % p)
    print("\nالدليل على المصدر يُحفَظ في docs/evidence/ باسم الأصل الذي يوثّقه.")
    print("التفصيل في docs/rights.md")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "probe":
        return cmd_probe(sys.argv[2:] or ["media/incoming"])
    if cmd == "sheet":
        src = sys.argv[2] if len(sys.argv) > 2 else "media/incoming"
        dst = sys.argv[3] if len(sys.argv) > 3 else ".preview/incoming.png"
        return cmd_sheet(src, dst)
    if cmd == "rights":
        return cmd_rights(sys.argv[2] if len(sys.argv) > 2 else "media/incoming")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
