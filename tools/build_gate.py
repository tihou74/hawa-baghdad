#!/usr/bin/env python3
"""
build_gate — يبني بوّابة عشتار كقطعة SVG مُدمَجة في الصفحة.

ثلاثة دروس من المحاولة الأولى شكّلت هذا البناء
----------------------------------------------
١) **الحركة لا تعمل في `<img>`.** الـSVG المُحمَّل كصورة يعمل في وضع
   معزول، والحركة داخله لم تُنفَّذ، ولا يصل إليه CSS الصفحة. فالحلّ
   أن تُدمَج القطعة في HTML مباشرةً وتُحرَّك بـCSS الموقع — فتصير
   مرئيّة للأداة التي تتحكّم بالتوقيت (app.js) وقابلة للاختبار.

٢) **الإزاحة بالنسبة المئويّة خطأ في SVG.** `translateX(-100%)` يُحسب
   افتراضياً على `view-box` أي ١٢٠٠ وحدة، لا على عرض المصراع. فتُكتب
   الإزاحة بوحدات المستخدم صريحةً.

٣) **١٦٧ كيلوبايت غير مقبول.** السبب أن خطوط الآجر رُسمت خطّاً خطّاً
   (آلاف العناصر). البديل `<pattern>` واحد يُكرّره المتصفّح، و`<use>`
   للعناصر المتكرّرة. النتيجة أقل من ١٢ كيلوبايت.

البوّابة التاريخيّة
-------------------
بوّابة عشتار البابليّة (نحو ٥٧٥ ق.م، نبوخذ نصّر الثاني): آجر مزجَّج
لازوردي، وعليها ثلاثة حيوانات بالتبادل —
  • الأسد: عشتار   • الثور: أدد   • المُشخوشّو: مردوخ
أثرٌ في الملك العام، والرسم هنا أصليّ.

الاستخدام:
  python3 tools/build_gate.py        # يكتب القطعة ويحشرها في index.html
"""

import io
import math
import re

W, H = 1200, 900
OX0, OX1 = 460, 740              # حدّا الفتحة
OW = OX1 - OX0
SPRING, APEX = 600, 330
RY = SPRING - APEX
MID = (OX0 + OX1) / 2
LEAF_W = OW / 2

BLUE_DEEP = "#0E2A52"
BLUE = "#15396B"
BLUE_LIT = "#22548F"
GOLD = "#C98F2E"
GOLD_LT = "#E6BE६8".replace("६", "6")
CREAM = "#F0E6D2"
OCHRE = "#D89A3C"


# ============================================================ الزخارف
# قرار تصميمي مُتَّخذ بعد أربع محاولات فاشلة
# -------------------------------------------------------------
# أسود البوّابة وثيرانها وتنانينها أشكال **تصويريّة**. ورسمها بكتابة
# مسارات SVG بلا دورة رسم بصريّة أنتج في كل مرّة أشكالاً بلا نسب
# مقنعة — كتلاً تُشبه قوارض لا أسوداً. وإرسال عملٍ كهذا أسوأ من
# عدم إرساله: الشعار والهويّة محترفان، فزخرفة رديئة تجاورهما
# تخفض قيمة الكلّ.
#
# والبديل ليس تنازلاً. فإفريز الطريق الموكبي في بابل نفسه مبنيّ —
# إلى جانب الحيوانات — على أشرطة **هندسيّة** متكرّرة: الورديّات
# المتجاورة، وشريط النخيلة/اللوتس (palmette)، والشُرَف المدرَّجة.
# وهذه أشكال هندسيّة تُرسم بالأرقام فتخرج دقيقة.
#
# وما يجعل البوّابة معروفة من لمحة هو: الأزرق اللازوردي، والأشرطة
# الذهبيّة، والتسنين، والقوس — لا الحيوانات بالضرورة.
#
# فإن أراد العميل الحيوانات فالطريق الصحيح رسّامٌ مكلَّف، أو صورة
# مرجعيّة يُرسم عليها. وقد كُتب هذا في README.

def palmette(x, y, s=1.0):
    """شريط النخيلة: مروحة سعف من قاعدة بلولبين — زخرفة بابليّة
       متكرّرة على الآجر المزجَّج. هندسيّة بالكامل فتُرسم بدقّة."""
    return (f'<g transform="translate({x},{y}) scale({s})">'
            # القاعدة ولولباها
            f'<path d="M-15,0 C-15,-7 -9,-11 0,-11 C9,-11 15,-7 15,0 Z"/>'
            f'<path d="M-15,0 C-24,0 -27,-6 -23,-11 C-20,-14 -15,-13 -14,-9 '
            f'C-16,-10 -19,-9 -19,-6 C-19,-3 -17,-1 -15,-1 Z"/>'
            f'<path d="M15,0 C24,0 27,-6 23,-11 C20,-14 15,-13 14,-9 '
            f'C16,-10 19,-9 19,-6 C19,-3 17,-1 15,-1 Z"/>'
            # سبع سعفات: الوسطى قائمة والبواقي تميل تدريجياً
            f'<path d="M0,-11 L0,-40 C0,-40 4,-34 3,-26 C2,-19 1,-14 0,-11 Z"/>'
            f'<path d="M0,-11 L-9,-37 C-9,-37 -4,-32 -3,-25 C-2,-18 -1,-14 0,-11 Z"/>'
            f'<path d="M0,-11 L9,-37 C9,-37 4,-32 3,-25 C2,-18 1,-14 0,-11 Z"/>'
            f'<path d="M0,-11 L-17,-31 C-17,-31 -10,-28 -7,-22 C-4,-17 -1,-13 0,-11 Z"/>'
            f'<path d="M0,-11 L17,-31 C17,-31 10,-28 7,-22 C4,-17 1,-13 0,-11 Z"/>'
            f'<path d="M0,-11 L-23,-22 C-23,-22 -15,-21 -10,-17 C-5,-14 -1,-12 0,-11 Z"/>'
            f'<path d="M0,-11 L23,-22 C23,-22 15,-21 10,-17 C5,-14 1,-12 0,-11 Z"/>'
            f'</g>')


def sacred_tree(x, y, h, s=1.0):
    """شجرة الحياة: ساق بعُقد ونخيلة في القمّة. تفصل الأشرطة عمودياً."""
    o = [f'<g transform="translate({x},{y}) scale({s})">']
    o.append(f'<rect x="-3" y="{-h}" width="6" height="{h}" rx="2"/>')
    n = int(h // 34)
    for i in range(n):
        yy = -12 - i * 34
        o.append(f'<path d="M-3,{yy} C-14,{yy-2} -18,{yy-10} -14,{yy-16} '
                 f'C-11,{yy-12} -7,{yy-9} -3,{yy-8} Z"/>')
        o.append(f'<path d="M3,{yy} C14,{yy-2} 18,{yy-10} 14,{yy-16} '
                 f'C11,{yy-12} 7,{yy-9} 3,{yy-8} Z"/>')
    o.append(f'<g transform="translate(0,{-h})">')
    o.append(palmette(0, 0, 0.8))
    o.append("</g></g>")
    return "".join(o)


def main():
    # ---------- الشعار يُدمج: سيُحشر داخل HTML فلا قيد موارد، لكن
    #            الدمج يُبقي القطعة قائمة بنفسها ويوفّر طلب شبكة.
    # ⚠ الشعار الكحلي لا الكريمي هنا، والسبب مقيس:
    #   فتحة البوّابة مضاءة بوهج دافئ (#FFE3B0 → #D89A3C)، والشعار
    #   الكريمي عليه يعطي 1.21:1 و1.76:1 — أي يكاد يختفي. والكحلي
    #   يعطي 15.7:1 و8.1:1. فالقاعدة نفسها التي فرضت نسخةً كريميّة
    #   على الأرضيّة الكحليّة تفرض هنا العكس.
    src = io.open("assets/img/logo.svg", encoding="utf-8").read()
    logo = "".join(re.findall(r"<path[^>]*/>", src))
    vb = re.search(r'viewBox="([\d.\s]+)"', src).group(1).split()
    lw, lh = float(vb[2]), float(vb[3])
    k = (OW * 0.70) / lw
    lx = MID - (lw * k) / 2
    ly = SPRING - 70

    arch = (f"M{OX0},{H} L{OX0},{SPRING} A{OW/2},{RY} 0 0 1 {OX1},{SPRING} "
            f"L{OX1},{H} Z")

    s = []
    s.append(f'<svg class="gate__art" viewBox="0 0 {W} {H}" '
             f'preserveAspectRatio="xMidYMid slice" aria-hidden="true">')

    # ================= defs
    s.append("<defs>")
    s.append(f'<linearGradient id="g-wall" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BLUE_LIT}"/>'
             f'<stop offset=".5" stop-color="{BLUE}"/>'
             f'<stop offset="1" stop-color="{BLUE_DEEP}"/></linearGradient>')
    s.append('<radialGradient id="g-inner" cx=".5" cy=".9" r=".85">'
             '<stop offset="0" stop-color="#FFE3B0"/>'
             f'<stop offset=".35" stop-color="{OCHRE}"/>'
             '<stop offset="1" stop-color="#1B0F06"/></radialGradient>')
    s.append('<linearGradient id="g-leaf" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#4A2E14"/>'
             '<stop offset=".45" stop-color="#6E4820"/>'
             '<stop offset="1" stop-color="#301D0D"/></linearGradient>')

    # آجر: نقشة واحدة يكرّرها المتصفّح — بدل آلاف الخطوط
    s.append(f'<pattern id="g-brick" width="60" height="30" '
             f'patternUnits="userSpaceOnUse">'
             f'<rect width="60" height="30" fill="none"/>'
             f'<g stroke="{BLUE_DEEP}" stroke-width="1.1" opacity=".45">'
             f'<path d="M0,0 H60 M0,15 H60 M0,30 H60"/>'
             f'<path d="M0,0 V15 M30,0 V15 M15,15 V30 M45,15 V30"/>'
             f'</g></pattern>')

    # ورديّة: عنصر واحد يُستدعى في كل موضع
    s.append(f'<g id="ros"><circle r="7.5" fill="{CREAM}"/>'
             f'<circle r="3.2" fill="{BLUE_LIT}"/></g>')


    s.append(f'<clipPath id="g-arch"><path d="{arch}"/></clipPath>')
    s.append("</defs>")

    # ================= داخل الفتحة
    s.append('<g clip-path="url(#g-arch)">')
    s.append(f'<rect x="{OX0}" y="{APEX}" width="{OW}" height="{H-APEX}" '
             f'fill="url(#g-inner)" class="gate__glow"/>')
    # ⚠ خطأ كلّف تشخيصاً: CSS `transform` **يستبدل** سمة `transform`
    #   في SVG لا يُضاف إليها. فحين حُرّك هذا العنصر بـCSS فقد موضعه
    #   وانزلق إلى أصل الإحداثيّات خارج قناع القوس — فلم يظهر الشعار
    #   أبداً مع أن الضوء ظهر.
    #   الحلّ طبقتان: الخارجيّة تحمل التموضع بالسمة ولا يمسّها CSS،
    #   والداخليّة فارغة من السمة فتتحرّك بأمان.
    s.append(f'<g transform="translate({lx:.1f},{ly:.1f}) scale({k:.4f})">'
             f'<g class="gate__logo">{logo}</g></g>')

    # المصراعان — الإزاحة بوحدات المستخدم لا بالنسبة المئويّة
    for cls, x0 in (("gate__leaf gate__leaf--a", OX0),
                    ("gate__leaf gate__leaf--b", MID)):
        s.append(f'<g class="{cls}">')
        s.append(f'<rect x="{x0}" y="{APEX-14}" width="{LEAF_W}" '
                 f'height="{H-APEX+14}" fill="url(#g-leaf)"/>')
        for r in range(6):
            yy = APEX + 40 + r * 84
            s.append(f'<rect x="{x0+10}" y="{yy}" width="{LEAF_W-20}" '
                     f'height="64" fill="none" stroke="{GOLD}" '
                     f'stroke-width="2.2" opacity=".5"/>')
            s.append(f'<circle cx="{x0+26}" cy="{yy+32}" r="4.5" '
                     f'fill="{GOLD_LT}" opacity=".75"/>')
            s.append(f'<circle cx="{x0+LEAF_W-26}" cy="{yy+32}" r="4.5" '
                     f'fill="{GOLD_LT}" opacity=".75"/>')
        s.append("</g>")
    s.append("</g>")

    # ================= الجدار (even-odd: المستطيل ناقص القوس)
    s.append(f'<path fill-rule="evenodd" fill="url(#g-wall)" '
             f'd="M0,0 L{W},0 L{W},{H} L0,{H} Z {arch}"/>')
    s.append(f'<path fill-rule="evenodd" fill="url(#g-brick)" '
             f'd="M0,0 L{W},0 L{W},{H} L0,{H} Z {arch}"/>')

    # شُرَف مسنَّنة
    def merlons(x, w, y, step=58, hgt=38):
        o = []
        n = int(w // step)
        pad = (w - n * step) / 2
        for i in range(n):
            mx = x + pad + step * i
            o.append(f'M{mx+6},{y} V{y-hgt+14} H{mx+15} V{y-hgt} '
                     f'H{mx+step-15} V{y-hgt+14} H{mx+step-6} V{y} Z')
        return (f'<path d="{" ".join(o)}" fill="{BLUE_LIT}"/>')

    def band(x, y, w, h=18):
        o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{GOLD}"/>',
             f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="{GOLD_LT}"/>']
        step = 30
        n = int(w // step)
        pad = (w - n * step) / 2
        for i in range(n):
            o.append(f'<use href="#ros" x="{x+pad+step*i+step/2:.0f}" '
                     f'y="{y+h/2:.0f}" transform="scale(1)"/>')
        return "".join(o)

    # البرجان + الكتلة الوسطى
    for tx, tw, top in ((0, 330, 130), (870, 330, 130), (330, 540, 215)):
        s.append(f'<rect x="{tx}" y="{top}" width="{tw}" height="{H-top}" '
                 f'fill="{BLUE}" opacity=".4"/>')
        s.append(merlons(tx, tw, top))
        s.append(band(tx, top, tw))

    # أشرطة هندسيّة على البرجين: نخيلات متجاورة بين أشرطة ورديّات،
    # وشجرة حياة في وسط كل سجلّ. كلها أشكال تُرسم بالأرقام.
    for tx in (0, 870):
        for i, yy in enumerate((330, 500, 670)):
            # صفّ نخيلات
            step = 66
            n = int((330 - 30) // step)
            pad = (330 - n * step) / 2
            for j in range(n):
                px = tx + pad + j * step + step / 2
                fill = CREAM if (i + j) % 2 == 0 else OCHRE
                s.append(f'<g fill="{fill}">{palmette(px, yy + 46, 0.84)}</g>')
            s.append(band(tx, yy + 54, 330, 14))
        # شجرة الحياة تمتدّ على ارتفاع البرج
        s.append(f'<g fill="{GOLD_LT}" opacity=".5">'
                 f'{sacred_tree(tx + 165, 300, 120, 0.9)}</g>')

    # حاشية القوس
    s.append(f'<path d="{arch}" fill="none" stroke="{GOLD}" stroke-width="16"/>')
    s.append(f'<path d="{arch}" fill="none" stroke="{GOLD_LT}" stroke-width="3"/>')
    for i in range(13):
        ang = math.pi * (1 - i / 12)
        cx = MID + math.cos(ang) * (OW / 2 + 30)
        cy = SPRING - math.sin(ang) * (RY + 30)
        s.append(f'<use href="#ros" x="{cx:.0f}" y="{cy:.0f}"/>')
    for jx in (OX0 - 30, OX1 + 30):
        for r in range(5):
            s.append(f'<use href="#ros" x="{jx}" y="{SPRING+46+r*62}"/>')

    s.append(f'<rect x="0" y="{H-16}" width="{W}" height="16" fill="{BLUE_DEEP}"/>')
    s.append("</svg>")

    frag = "".join(s)

    # ---------- حشر القطعة في index.html داخل الافتتاحيّة
    page = io.open("index.html", encoding="utf-8").read()
    m = re.search(r'<div class="intro" id="intro".*?</div>\s*(?=<!--)', page, re.S)
    if not m:
        print("لم أجد كتلة الافتتاحيّة — لم يُعدَّل index.html")
    else:
        new_intro = (
            '<!-- ============================================================\n'
            '     الافتتاحيّة — بوّابة عشتار تنفتح عن الشعار\n'
            '     القطعة مُدمَجة لا مُحمَّلة كصورة: الحركة داخل ملف SVG\n'
            '     مُحمَّل بـ<img> لا تعمل، ولا يصل إليه CSS الصفحة.\n'
            '     البوّابة أثرٌ بابلي في الملك العام، والرسم أصلي،\n'
            '     ومُولَّد بـ tools/build_gate.py\n'
            '     ============================================================ -->\n'
            '<div class="intro" id="intro" aria-hidden="true">\n'
            '  ' + frag + '\n'
            '</div>\n\n')
        page = page[:m.start()] + new_intro + page[m.end():]
        io.open("index.html", "w", encoding="utf-8").write(page)
        print("index.html: الافتتاحيّة استُبدلت بالبوّابة")

    io.open("assets/img/ishtar-gate.svg", "w", encoding="utf-8").write(
        frag.replace('<svg class="gate__art"',
                     '<svg xmlns="http://www.w3.org/2000/svg" class="gate__art"')
        + "\n")

    print("  fragment bytes : %d  (كان 167236)" % len(frag))
    print("  elements       : %d" % frag.count("<"))
    print("  opening        : x %d..%d  apex=%d  spring=%d  leaf=%d"
          % (OX0, OX1, APEX, SPRING, LEAF_W))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
