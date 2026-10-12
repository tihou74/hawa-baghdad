#!/usr/bin/env python3
"""
seal — يبني ختم العلامة المتجهيّ من كلمة الشعار الموجودة.

لماذا مولَّد لا مرسوم يدوياً
----------------------------
الختم في البروفايل صورة نقطيّة، وتكبيرها يُظهر البكسلات. والحلقة
المتآكلة شكل هندسي بسيط: دائرتان سميكتان، وشريط خرز بينهما، وقناع
يأكل من الحبر قطعاً غير منتظمة. فتوليدها متجهيّاً يعطي:

  * حدّة على كل مقاس — من الأيقونة إلى لافتة المطعم.
  * ملفّاً صغيراً (كيلوبايتات) بلا صورة نقطيّة.
  * `currentColor` للحبر، فيتحكّم CSS في اللون ولا يتكرّر الملفّ
    لكل خلفيّة.
  * تآكلاً **ثابتاً** لا عشوائياً في كل بناء (بذرة مثبَّتة)، فلا
    يتغيّر الختم بين إصدار وإصدار.

والكلمة نفسها لا تُعاد رسمها: تُقرأ مساراتها من
`assets/img/logo-mono-navy.svg` فتبقى مصدراً واحداً للحقيقة.

الاستخدام
---------
  python3 tools/seal.py                    # إلى assets/img/seal.svg
  python3 tools/seal.py out.svg
"""

import math
import os
import random
import re
import sys

SRC = "assets/img/logo-mono-navy.svg"
SIZE = 1000.0
C = SIZE / 2

R_OUTER = 470.0          # الحلقة الخارجيّة
W_OUTER = 15.0
R_BEADS = 436.0          # شريط الخرز
BEAD_R = 10.5
N_BEADS = 58
R_INNER = 398.0          # الحلقة الداخليّة السميكة
W_INNER = 26.0
WORD_W = 540.0           # عرض الكلمة داخل الختم

SEED = 20261012          # ثابت: الختم لا يتغيّر بين البناءات


def wordmark():
    """يقرأ مسارات الكلمة وviewBox من ملفّ الشعار الأحادي."""
    if not os.path.exists(SRC):
        sys.exit("لا يوجد %s" % SRC)
    svg = open(SRC, encoding="utf-8").read()
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if not m:
        sys.exit("تعذّر قراءة viewBox من %s" % SRC)
    vw, vh = float(m.group(1)), float(m.group(2))
    paths = re.findall(r"<path\b[^>]*?/>", svg)
    if not paths:
        sys.exit("لا مسارات في %s" % SRC)
    # الحبر يأتي من CSS، فتُنزع الألوان المثبَّتة ويُترك currentColor.
    # و`stroke` تُنزع أيضاً: أحد عشر مساراً في ملفّ الشعار تحمل
    # `stroke="#00008B"` — وهي حروف HAWA BAGHDAD — فنزع `fill` وحده
    # كان يُبقيها بالأزرق الفاقع داخل ختم كحلي.
    #
    # وتُصمَّت هذه الحروف: في ختم البروفايل هي **مصمَّتة**، لكن
    # تحويل الـPDF أخرجها مُفرَّغة (`fill="none"` مع حدّ رقيق) فتبدو
    # هشّة على المقاسات الصغيرة وتختفي حدودها في الطباعة.
    clean = []
    for p in paths:
        p = re.sub(r'\s*fill="none"', ' fill="currentColor"', p)
        p = re.sub(r'\s*fill="(?!none|currentColor)[^"]*"', "", p)
        p = re.sub(r'\s*stroke="[^"]*"', ' stroke="currentColor"', p)
        clean.append("    " + p)
    return vw, vh, "\n".join(clean)


def erosion():
    """قطع غير منتظمة تُؤكل من الحبر — تآكل الختم المطّاطي.

    تُوزَّع على نطاق الحلقات وحدها (وقليلاً على حدود الكلمة) لأن
    أكل وسط الكلمة يُقرأ كخلل طباعة لا كختم."""
    rnd = random.Random(SEED)
    out = []

    # تآكل على نطاق الحلقتين وشريط الخرز
    for _ in range(96):
        a = rnd.uniform(0, math.tau)
        r = rnd.choice([
            rnd.uniform(R_INNER - W_INNER, R_INNER + W_INNER),
            rnd.uniform(R_BEADS - 16, R_BEADS + 16),
            rnd.uniform(R_OUTER - W_OUTER * 1.4, R_OUTER + W_OUTER * 1.4),
        ])
        x, y = C + r * math.cos(a), C + r * math.sin(a)
        rx, ry = rnd.uniform(5, 19), rnd.uniform(4, 13)
        rot = math.degrees(a) + rnd.uniform(-40, 40)
        out.append(
            '    <ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f"'
            ' transform="rotate(%.1f %.1f %.1f)"/>'
            % (x, y, rx, ry, rot, x, y))

    # خدوش طويلة: تعطي إحساس ضغط غير مستوٍ
    for _ in range(8):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(R_INNER - 10, R_OUTER + 10)
        x, y = C + r * math.cos(a), C + r * math.sin(a)
        ln = rnd.uniform(30, 80)
        out.append(
            '    <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"'
            ' transform="rotate(%.1f %.1f %.1f)"/>'
            % (x, y, ln, rnd.uniform(3, 9),
               math.degrees(a) + 90 + rnd.uniform(-25, 25), x, y))

    # لمسات خفيفة على أطراف الكلمة
    for _ in range(12):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(WORD_W * 0.30, WORD_W * 0.50)
        x, y = C + r * math.cos(a), C + r * math.sin(a)
        out.append('    <ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f"/>'
                   % (x, y, rnd.uniform(3, 8), rnd.uniform(2, 6)))
    return "\n".join(out)


def build():
    vw, vh, paths = wordmark()
    k = WORD_W / vw
    tx = C - (vw * k) / 2
    ty = C - (vh * k) / 2

    beads = []
    for i in range(N_BEADS):
        a = math.tau * i / N_BEADS
        beads.append('    <circle cx="%.1f" cy="%.1f" r="%.2f"/>'
                     % (C + R_BEADS * math.cos(a),
                        C + R_BEADS * math.sin(a), BEAD_R))

    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"
     width="%d" height="%d" color="#2E3154"
     role="img" aria-label="ختم هوى بغداد">
<!-- ختم هوى بغداد — مولَّد بـ tools/seal.py من assets/img/logo-mono-navy.svg
     الحبر `currentColor`: يُضبط من CSS فلا يتكرّر الملفّ لكل خلفيّة.
     لا تُحرّر هذا الملفّ يدوياً — أعِد توليده. -->
  <mask id="ink-wear" maskUnits="userSpaceOnUse" x="0" y="0"
        width="%d" height="%d">
    <rect width="%d" height="%d" fill="#fff"/>
    <g fill="#000">
%s
    </g>
  </mask>
  <g mask="url(#ink-wear)" fill="currentColor">
    <circle cx="%.1f" cy="%.1f" r="%.1f" fill="none"
            stroke="currentColor" stroke-width="%.1f"/>
%s
    <circle cx="%.1f" cy="%.1f" r="%.1f" fill="none"
            stroke="currentColor" stroke-width="%.1f"/>
    <g transform="translate(%.2f %.2f) scale(%.5f)">
%s
    </g>
  </g>
</svg>
""" % (SIZE, SIZE, SIZE, SIZE, SIZE, SIZE, SIZE, SIZE, erosion(),
       C, C, R_OUTER, W_OUTER, "\n".join(beads),
       C, C, R_INNER, W_INNER, tx, ty, k, paths)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/img/seal.svg"
    svg = build()
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(svg)
    print("  %s  %.1fKB" % (out, len(svg.encode()) / 1024))
