#!/usr/bin/env python3
"""
pdf2svg — تحويل مسارات PDF المتجهيّة إلى SVG، بـPython الخالص.

لماذا بُنيت هذه الأداة
----------------------
شعار العلامة وصل ملفَّ PDF من Illustrator — أي متجهيّاً خالصاً. وهذه
البيئة بلا أي محوّل PDF (pdftoppm, mutool, gs, inkscape, cairosvg) وبلا
Pillow، وPyPI وnpm محجوبان. والبديل الساذج — تحويله صورةً نقطيّة — يُهدر
أثمن ما في الملف: الشعار يجب أن يبقى حادّاً على كل مقاس، من أيقونة ٣٢px
إلى لافتة المطعم.

والحلّ أن مؤثّرات مسارات PDF تقابل أوامر SVG مقابلةً تكاد تكون واحداً
بواحد. فالتحويل ممكن بلا أي اعتماديّة:

    PDF                         SVG
    x y m                   →   M x y
    x y l                   →   L x y
    x1 y1 x2 y2 x3 y3 c     →   C x1 y1 x2 y2 x3 y3
    x2 y2 x3 y3 v           →   C (النقطة الحاليّة) x2 y2 x3 y3
    x1 y1 x3 y3 y           →   C x1 y1 x3 y3 x3 y3
    h                       →   Z
    x y w h re              →   M x y h w v h h -w Z

فرقان جوهريّان يجب التعامل معهما، وإغفال أيّهما يُنتج ملفاً مقلوباً
أو مشوّهاً:

  ١) محور Y في PDF يتّجه للأعلى، وفي SVG للأسفل. فيُلفّ كل شيء في
     مصفوفة قلب: matrix(1 0 0 -1 0 H).

  ٢) PDF يحمل مصفوفة تحويل جاريّة (CTM) تُعدَّل بـ`cm` وتُحفَظ وتُسترجَع
     بـ`q`/`Q`. وإحداثيّات المسار تُكتب في فضاء CTM لا في فضاء الصفحة.
     فلو أُهملت المصفوفة ظهرت الأجزاء متراكبة في مكان خاطئ — وهذا ما
     يحدث فعلاً في شعار كهذا، لأن كل جزء منه ملفوف في
     `q 1 0 0 1 <dx> <dy> cm`. لذا تُضرَب كل نقطة في CTM هنا، وتُكتب
     في SVG بإحداثيّات مطلقة.

الألوان: الشعار يستخدم فضاء ICCBased ثلاثي المكوّنات، فتُقرأ قيم
`scn`/`rg` وتُحوَّل إلى ست عشري مباشرة.

الاستخدام:
  python3 tools/pdf2svg.py <in.pdf> <out.svg> [--page N]
"""

import re
import sys
import zlib


# ----------------------------------------------------------------- مساعدات

def object_streams(data):
    """خريطة: رقم الكائن → محتوى تدفّقه مفكوكاً.

    لا بُدّ من الربط برقم الكائن لا بترتيب الظهور في الملف، لأن
    `/Contents` قد يسرد التدفّقات بترتيب مختلف عن ترتيبها الفيزيائي.
    """
    objs = {}
    for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", data):
        num = int(m.group(1))
        endobj = data.find(b"endobj", m.end())
        if endobj < 0:
            continue
        chunk = data[m.end():endobj]
        sm = re.search(rb"stream\r?\n", chunk)
        if not sm:
            continue
        raw = chunk[sm.end():]
        em = raw.rfind(b"endstream")
        if em >= 0:
            raw = raw[:em]
        try:
            objs[num] = zlib.decompress(raw)
        except Exception:
            objs[num] = raw
    return objs


def page_content(data):
    """محتوى الصفحة الأولى، مُجمَّعاً بترتيب `/Contents` الصحيح.

    ⚠ هذه الخطوة ليست تحسيناً بل شرطٌ للصحّة. محتوى صفحة PDF قد يُقسَّم
    على عدّة كائنات تدفّق، وهي **مستمرّة**: مسار يبدأ في تدفّق وينتهي في
    الذي بعده، ومصفوفة التحويل التي يضعها `cm` في أحدها تسري على ما
    يليه. فمعالجة التدفّقات منفصلةً — أو بترتيب الملف لا بترتيب
    `/Contents` — تُنتج مسارات تبدأ بـ`C` بلا `M` وإحداثيّات في فضاء
    خاطئ. وهذا ما حدث فعلاً في أوّل تشغيل لهذه الأداة على هذا الشعار:
    ٢٧ مساراً كلّها في غير موضعها.
    """
    objs = object_streams(data)

    m = re.search(rb"/Contents\s*\[([^\]]*)\]", data)
    if m:
        order = [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1))]
    else:
        m = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", data)
        order = [int(m.group(1))] if m else []

    if order:
        parts = [objs[n] for n in order if n in objs]
        if parts:
            # فاصل سطر بين الأجزاء: يمنع التصاق مؤثّر بآخر عند الوصل
            return b"\n".join(parts), order

    # احتياط: كل تدفّق فيه مؤثّرات مسار
    fallback = [v for v in objs.values() if re.search(rb"\b[mlc]\b|\bre\b", v)]
    return b"\n".join(fallback), []


def media_box(data):
    m = re.search(rb"/MediaBox\s*\[([^\]]+)\]", data)
    if not m:
        return (0.0, 0.0, 612.0, 792.0)
    v = [float(x) for x in m.group(1).split()]
    return tuple(v)


def mat_mul(a, b):
    """ضرب مصفوفتي PDF [a b c d e f] — a ثم b."""
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (
        a0 * b0 + a1 * b2,
        a0 * b1 + a1 * b3,
        a2 * b0 + a3 * b2,
        a2 * b1 + a3 * b3,
        a4 * b0 + a5 * b2 + b4,
        a4 * b1 + a5 * b3 + b5,
    )


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def fmt(v):
    """رقم مختصر: يحذف الأصفار الزائدة فيصغر حجم الملف كثيراً."""
    s = "%.3f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# -------------------------------------------------------------- المحوّل

TOKEN = re.compile(rb"""
      (?P<num>-?\d*\.?\d+)
    | (?P<name>/[^\s/\[\]<>(){}]+)
    | (?P<op>[A-Za-z*'"]+)
    | (?P<str>\((?:[^()\\]|\\.)*\))
    | (?P<arr>[\[\]])
""", re.X)


def convert(content, ctm0):
    """يُرجع قائمة عناصر SVG من تدفّق محتوى واحد."""
    stack = []                 # مكدّس q/Q
    ctm = ctm0
    fill = "#000000"
    stroke = "#000000"
    lw = 1.0
    ops = []                   # معاملات متراكمة
    path = []                  # أوامر SVG النصّيّة
    cur = (0.0, 0.0)           # النقطة الحاليّة بفضاء المستخدم
    start = (0.0, 0.0)
    out = []

    def num(i):
        """المعامل رقم i من آخر المكدّس (0 = الأخير)."""
        return ops[-1 - i]

    def moveto(x, y):
        nonlocal cur, start
        X, Y = apply(ctm, x, y)
        path.append("M%s %s" % (fmt(X), fmt(Y)))
        cur = (x, y)
        start = (x, y)

    def lineto(x, y):
        nonlocal cur
        X, Y = apply(ctm, x, y)
        path.append("L%s %s" % (fmt(X), fmt(Y)))
        cur = (x, y)

    def curveto(x1, y1, x2, y2, x3, y3):
        nonlocal cur
        p1 = apply(ctm, x1, y1)
        p2 = apply(ctm, x2, y2)
        p3 = apply(ctm, x3, y3)
        path.append("C%s %s %s %s %s %s" % (
            fmt(p1[0]), fmt(p1[1]), fmt(p2[0]), fmt(p2[1]),
            fmt(p3[0]), fmt(p3[1])))
        cur = (x3, y3)

    def emit(do_fill, do_stroke, even_odd=False):
        if not path:
            return
        d = " ".join(path)
        attrs = ['d="%s"' % d]
        if do_fill:
            attrs.append('fill="%s"' % fill)
            if even_odd:
                attrs.append('fill-rule="evenodd"')
        else:
            attrs.append('fill="none"')
        if do_stroke:
            attrs.append('stroke="%s"' % stroke)
            # عرض القلم يتأثّر بمقياس المصفوفة
            scale = (abs(ctm[0]) + abs(ctm[3])) / 2 or 1
            attrs.append('stroke-width="%s"' % fmt(lw * scale))
            attrs.append('stroke-linejoin="round"')
            attrs.append('stroke-linecap="round"')
        out.append("<path " + " ".join(attrs) + "/>")

    for m in TOKEN.finditer(content):
        if m.lastgroup == "num":
            ops.append(float(m.group("num")))
            continue
        if m.lastgroup in ("name", "str", "arr"):
            ops.append(m.group().decode("latin-1"))
            continue

        op = m.group("op").decode("latin-1")

        if op == "q":
            stack.append((ctm, fill, stroke, lw))
        elif op == "Q":
            if stack:
                ctm, fill, stroke, lw = stack.pop()
        elif op == "cm" and len(ops) >= 6:
            ctm = mat_mul(tuple(ops[-6:]), ctm)
        elif op == "m" and len(ops) >= 2:
            moveto(num(1), num(0))
        elif op == "l" and len(ops) >= 2:
            lineto(num(1), num(0))
        elif op == "c" and len(ops) >= 6:
            curveto(*ops[-6:])
        elif op == "v" and len(ops) >= 4:
            # نقطة التحكّم الأولى = النقطة الحاليّة
            curveto(cur[0], cur[1], num(3), num(2), num(1), num(0))
        elif op == "y" and len(ops) >= 4:
            # نقطة التحكّم الثانية = نقطة النهاية
            curveto(num(3), num(2), num(1), num(0), num(1), num(0))
        elif op == "h":
            if path:
                path.append("Z")
                cur = start
        elif op == "re" and len(ops) >= 4:
            x, y, w, h = ops[-4:]
            moveto(x, y)
            lineto(x + w, y)
            lineto(x + w, y + h)
            lineto(x, y + h)
            path.append("Z")
        elif op in ("rg", "sc", "scn") and len(ops) >= 3 and all(
                isinstance(v, float) for v in ops[-3:]):
            r, g, b = ops[-3:]
            fill = "#%02X%02X%02X" % (
                max(0, min(255, round(r * 255))),
                max(0, min(255, round(g * 255))),
                max(0, min(255, round(b * 255))))
        elif op in ("RG", "SC", "SCN") and len(ops) >= 3 and all(
                isinstance(v, float) for v in ops[-3:]):
            r, g, b = ops[-3:]
            stroke = "#%02X%02X%02X" % (
                max(0, min(255, round(r * 255))),
                max(0, min(255, round(g * 255))),
                max(0, min(255, round(b * 255))))
        elif op == "g" and len(ops) >= 1 and isinstance(ops[-1], float):
            v = max(0, min(255, round(ops[-1] * 255)))
            fill = "#%02X%02X%02X" % (v, v, v)
        elif op == "G" and len(ops) >= 1 and isinstance(ops[-1], float):
            v = max(0, min(255, round(ops[-1] * 255)))
            stroke = "#%02X%02X%02X" % (v, v, v)
        elif op == "k" and len(ops) >= 4:
            c, mm2, y2, k = ops[-4:]
            fill = "#%02X%02X%02X" % (
                round(255 * (1 - min(1, c + k))),
                round(255 * (1 - min(1, mm2 + k))),
                round(255 * (1 - min(1, y2 + k))))
        elif op == "w" and len(ops) >= 1 and isinstance(ops[-1], float):
            lw = ops[-1]
        elif op in ("f", "F", "f*"):
            emit(True, False, op == "f*")
            path = []
        elif op in ("B", "B*"):
            emit(True, True, op == "B*")
            path = []
        elif op in ("b", "b*"):
            path.append("Z")
            emit(True, True, op == "b*")
            path = []
        elif op == "S":
            emit(False, True)
            path = []
        elif op == "s":
            path.append("Z")
            emit(False, True)
            path = []
        elif op == "n":
            path = []

        ops = []

    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    src, dst = args[0], args[1]

    data = open(src, "rb").read()
    x0, y0, x1, y1 = media_box(data)
    w, h = x1 - x0, y1 - y0

    # قلب محور Y + إزاحة أصل MediaBox
    base = (1.0, 0.0, 0.0, -1.0, -x0, y1)

    content, order = page_content(data)
    if order:
        print("  contents: %s (concatenated in /Contents order)"
              % " ".join(str(n) for n in order))
    body = convert(content, base)

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" '
               'viewBox="0 0 %s %s" width="%s" height="%s">'
               % (fmt(w), fmt(h), fmt(w), fmt(h)))
    svg.append("<!-- مُحوَّل من %s بـ tools/pdf2svg.py — متجهيّ بالكامل -->"
               % src.split("/")[-1])
    svg.extend(body)
    svg.append("</svg>")

    open(dst, "w", encoding="utf-8").write("\n".join(svg) + "\n")
    print("wrote %s" % dst)
    print("  viewBox : 0 0 %s %s" % (fmt(w), fmt(h)))
    print("  paths   : %d" % len(body))
    print("  bytes   : %d" % len("\n".join(svg)))
    cols = sorted(set(re.findall(r'fill="(#[0-9A-F]{6})"', "\n".join(body))))
    print("  fills   : %s" % ", ".join(cols))
    return 0


if __name__ == "__main__":
    sys.exit(main())
