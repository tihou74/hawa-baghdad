#!/usr/bin/env python3
"""hook_image_guard — يمنع قراءة صورة تتجاوز ٢٠٠٠ بكسل، آلياً.

المشكلة التي يحلّها
-------------------
قراءة صورة يتجاوز أحد بُعديها ٢٠٠٠ بكسل تُفشل الطلب بالخطأ:

    At least one of the image dimensions exceed max allowed size
    for many-image requests: 2000 pixels

والفشل يأتي **بعد انتهاء العمل كله**، فتضيع الجلسة ويُهدر الرصيد.
وقد حدث فعلاً: جلسة ضاعت بعد ٨:٥٦ دقيقة و٣٠٫٣٨ رصيداً.

ولماذا لا يكفي `tools/imgguard.py`
----------------------------------
`imgguard` حارس **موضعي**: يحمي إن استُدعي. وأي سكربت جديد — أو
نسيان واحد — يتجاوزه. فالحارس الحقيقي يجب أن يكون على **فعل
القراءة نفسه**، لا على أداةٍ بعينها.

فيُستدعى هذا من خطّاف `PreToolUse` قبل كل قراءة ملف: يقرأ وصف
الاستدعاء من المدخل القياسي، ويستخرج منه مسارات الصور، ويقيس
أبعادها من **ترويسة الملف** (بلا فكّ أي بكسل)، ويرفض بالخروج ٢
إن تجاوزت — فيُحجب الاستدعاء قبل أن يصل إلى النموذج.

الخروج
------
  0 : آمن (أو لا صورة في الاستدعاء)
  2 : صورة تتجاوز الحدّ — يُحجب الاستدعاء ويُعرض السبب
"""

import json
import os
import re
import sys

LIMIT = 2000
EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


# ------------------------------------------------- أبعاد من الترويسة وحدها
def _dims(path):
    """يُرجع (w, h) أو None إن تعذّر — بلا أي اعتماديّة."""
    try:
        import struct
        with open(path, "rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:2] == b"BM":
                f.seek(18)
                w, h = struct.unpack("<ii", f.read(8))
                return abs(w), abs(h)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                f.seek(12)
                blob = f.read(24)
                if blob[:4] == b"VP8X":
                    w = int.from_bytes(blob[8:11], "little") + 1
                    h = int.from_bytes(blob[11:14], "little") + 1
                    return w, h
                if blob[:4] == b"VP8 ":
                    w, h = struct.unpack("<HH", blob[14:18])
                    return w & 0x3FFF, h & 0x3FFF
                if blob[:4] == b"VP8L":
                    b = int.from_bytes(blob[9:13], "little")
                    return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
                return None
            if head[:2] == b"\xff\xd8":          # JPEG
                f.seek(2)
                while True:
                    b = f.read(1)
                    if not b:
                        return None
                    if b != b"\xff":
                        continue
                    m = f.read(1)
                    while m == b"\xff":
                        m = f.read(1)
                    if not m:
                        return None
                    if m[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6,
                                0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    ln = f.read(2)
                    if len(ln) < 2:
                        return None
                    f.seek(struct.unpack(">H", ln)[0] - 2, 1)
    except Exception:
        return None
    return None


def _paths(blob):
    """كل ما يشبه مسار صورة في وصف الاستدعاء.

    الشكل الدقيق للمدخل غير مضمون بين الإصدارات، فلا يُعتمد على
    مفتاح بعينه: يُفتَّش النصّ كله. والإفراط في الالتقاط آمن —
    الملفّ غير الموجود يُتجاهل."""
    found = []
    try:
        data = json.loads(blob)

        def walk(x):
            if isinstance(x, str):
                found.append(x)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(data)
    except Exception:
        pass
    # احتياط: التقاط بالتعبير النمطي إن لم يكن JSON صالحاً
    found += re.findall(r'[\w./\\~-]+(?:' + "|".join(
        e.replace(".", r"\.") for e in EXTS) + r')', blob, re.I)

    out, seen = [], set()
    for p in found:
        if not p.lower().endswith(EXTS):
            continue
        p = os.path.expanduser(p.strip().strip('"\''))
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def main():
    blob = sys.stdin.read()
    if not blob.strip():
        return 0

    bad = []
    for p in _paths(blob):
        if not os.path.isfile(p):
            continue
        d = _dims(p)
        if d and max(d) > LIMIT:
            bad.append((p, d))

    if not bad:
        return 0

    lines = ["⛔ قراءة محجوبة: صورة تتجاوز حدّ %d بكسل." % LIMIT]
    for p, (w, h) in bad:
        lines.append("   %s  →  %dx%d" % (p, w, h))
    lines.append("")
    lines.append("قراءتها تُفشل الطلب وتُسقط الجلسة بعد انتهاء العمل.")
    lines.append("صغّرها أولاً ثم اقرأ الناتج:")
    lines.append("   python3 tools/imgguard.py safe '%s'" % bad[0][0])
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
