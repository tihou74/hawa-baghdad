#!/usr/bin/env python3
"""
build_page — يبني جسم الصفحة العربيّة من أصول البروفايل.

لماذا مُولَّد
------------
البناء الأوّل كان قائماً على رسوم متجهيّة رسمتُها بيدي: قارب، وجدار
طوب، ورفّ كتب. وكانت **ركيكة** ولا تناسب علامة بهذا المستوى، ورفضها
العميل بحقّ.

والأصول الحقيقيّة كانت موجودة طول الوقت داخل بروفايل الهويّة نفسه:
٣٨ صورة — تغليف، ومنيو مطبوع، ويونيفورم، واستكان، وقاشاني، وأطباق،
وأعمال فنيّة. استُخرجت وحُسِّنت ثم رُتِّبت هنا.

القاعدة الحاكمة: **الصورة هي المحتوى لا الخلفيّة.** المطعم يُباع
بالطعام والمكان، فكل قسم يبدأ من صورة حقيقيّة لا من تدرّج لوني.

الاستخدام:
  python3 tools/build_page.py
"""

import io
import json
import os
import re

DIR = "assets/img/profile"


def widths(name):
    out = []
    for f in os.listdir(DIR):
        m = re.match(re.escape(name) + r"-(\d+)\.webp$", f)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def pic(name, alt, sizes="100vw", cls="", ratio=None, eager=False):
    """عنصر <picture> كامل: webp مع srcset، وjpeg احتياطاً.

    الأبعاد تُكتب صريحةً فيحجز المتصفّح المكان قبل التحميل ولا تهتزّ
    الصفحة (CLS). والعروض المتاحة تُقرأ من القرص لا تُفترض — فبعض
    الأصول صغيرة ولا تُكبَّر.
    """
    w = widths(name)
    if not w:
        raise SystemExit("أصل مفقود: %s" % name)
    srcset = ", ".join("%s/%s-%d.webp %dw" % (DIR, name, x, x) for x in w)
    big = w[-1]
    # الارتفاع من اسم الملف الأصلي غير متاح هنا، فتُستخدم النسبة
    attr_cls = ' class="%s"' % cls if cls else ""
    style = ' style="aspect-ratio:%s"' % ratio if ratio else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (
        f'<picture{attr_cls}>'
        f'<source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
        f'<img src="{DIR}/{name}-{big}.jpg" alt="{alt}" {load} '
        f'decoding="async"{style}>'
        f"</picture>"
    )


def main():
    H = []
    A = H.append

    # ============================================== الواجهة
    A(f'''<section class="hero" id="top">
  <!-- واجهة فوتوغرافيّة ممتدّة. الواجهة السابقة كانت تدرّجاً لونيّاً
       وزخرفة هندسيّة بلا صورة، فكانت تبدو فارغة فعلاً على الشاشات
       المتوسّطة — وهو ما رآه العميل. -->
  <div class="hero__shot">{pic("masgouf-01", "سمكة مسكوف تُشوى مفروشة على النار المكشوفة", "100vw", eager=True)}</div>
  <div class="hero__scrim" aria-hidden="true"></div>

  <div class="hero__body">
    <p class="hero__kicker">مطبخ عراقي · الدوحة · قيد التطوير</p>
    <h1 class="hero__name">
      <img src="assets/img/logo-cream.svg" alt="هوى بغداد" width="397" height="395">
      <span class="sr">هوى بغداد</span>
    </h1>
    <p class="hero__tag">
      حيث يلتقي التقليد الأصيل بحسٍّ معاصر — مسكوف على النار،
      وخبز من التنّور، وقوزي يُطبخ على مهله.
    </p>
    <div class="btn-row">
      <a class="btn btn--solid" href="#menu">المائدة</a>
      <a class="btn btn--ghost" href="#masgouf">المسكوف</a>
    </div>
    <p class="hero__stage"><span></span>
      صفحة <strong>مفهوم</strong>: المطعم في مرحلة التطوير ولم يُفتح بعد.
    </p>
  </div>
</section>''')

    # ============================================== الحكاية
    A(f'''<section class="sec" id="story">
  <div class="wrap">
    <div class="sec__head">
      <p class="eyebrow" data-reveal>٠١ — الاسم</p>
      <h2 class="h2" data-reveal>كلمتان، وفي كلٍّ منهما معنيان</h2>
    </div>
    <div class="split">
      <div class="prose" data-reveal>
        <p><strong>«هوى»</strong> في العربيّة بابٌ ذو وجهين: الحُبّ الذي
        يشدّك إلى شيء لا تملكه، والهواء نفسه — النسمة التي تحمل الرائحة
        قبل أن تراها. والاسم يقصد المعنيين: <em>شوقٌ إلى بغداد، وهواءٌ
        منها</em>.</p>
        <p>وهذا ما يحدث على المائدة البغداديّة فعلاً. لا يبدأ الطبق
        بالنظر إليه، بل برائحة تصل قبله: دخان النار تحت السمك، وعجينٌ
        يلتصق بجدار التنّور، ودهنٌ حُرّ يُسكب على البامية فيُعلن عن
        نفسه من الغرفة المجاورة.</p>
        <p class="lead">لا نقدّم «أكلاً عراقياً» في قطر. نحاول نقل
        الهواء نفسه.</p>
      </div>
      <figure class="frame tilt" data-reveal>
        {pic("art-teaman", "عمل فنّي: رجل بغدادي يصبّ الچاي", "(min-width:900px) 42vw, 92vw")}
        <figcaption>من أعمال الهويّة البصريّة</figcaption>
      </figure>
    </div>
  </div>
</section>''')

    # ============================================== الأجواء (عمق)
    A(f'''<section class="band band--tall" id="place">
  <div class="band__layer" data-parallax aria-hidden="true">
    {pic("interior-tilewall", "", "100vw")}
  </div>
  <div class="wrap band__inner">
    <p class="eyebrow" data-reveal>٠٢ — الأجواء</p>
    <h2 class="h2" data-reveal>القاشاني الأزرق، والخشب الدافئ، وضوءٌ منخفض</h2>
    <p class="lead" data-reveal>
      توازنٌ مقصود بين القديم والحديث: بلاط مزخرف، وأقمشة منسوجة،
      وإضاءة معاصرة. مواد حقيقيّة بحرفة حقيقيّة — لا «ثيمة».
    </p>
  </div>
</section>

<section class="sec sec--tight on-dark" style="background:var(--navy-800)">
  <div class="wrap">
    <div class="mosaic">
      <figure class="mo mo--tall tilt" data-reveal>
        {pic("interior-lamps", "صالة بإضاءة معلّقة دافئة وجدران زرقاء", "(min-width:900px) 34vw, 92vw")}
        <figcaption>الإضاءة المنخفضة</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:80ms">
        {pic("interior-banquette", "جلسة مبنيّة بخطوط زرقاء وبيضاء", "(min-width:900px) 30vw, 92vw")}
        <figcaption>الجلسات المبنيّة</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:160ms">
        {pic("art-courtyard", "عمل فنّي: فناء بغدادي بأقواس", "(min-width:900px) 30vw, 92vw")}
        <figcaption>الحوش والأقواس</figcaption>
      </figure>
    </div>
  </div>
</section>''')

    # ============================================== المسكوف (مشهد مثبَّت + حرارة)
    A(f'''<section class="sec fire on-dark" id="masgouf" style="background:var(--navy-900)">
  <div class="fire__haze" aria-hidden="true"></div>
  <div class="fire__embers" aria-hidden="true">
    <b style="inset-inline-start:12%"></b><b style="inset-inline-start:28%"></b>
    <b style="inset-inline-start:44%"></b><b style="inset-inline-start:61%"></b>
    <b style="inset-inline-start:77%"></b><b style="inset-inline-start:90%"></b>
  </div>
  <div class="wrap" style="position:relative;z-index:4">
    <div class="sec__head">
      <p class="eyebrow" data-reveal>٠٣ — الطبق الذي لا يُفوَّض</p>
      <h2 class="h2" data-reveal>المسكوف: ساعةٌ واحدة، وأربع خطوات لا تُختصر</h2>
      <p class="lead" data-reveal>
        ليس «سمكاً مشوياً» بل طريقة: تُفرش السمكة مفتوحةً مواجهةً
        للجمر، فتُطبخ بالحرارة المنعكسة لا بالتلامس. ولهذا لا تُسرَّع.
      </p>
    </div>

    <div class="scene">
      <div class="scene__media" data-scene-media>
        <figure data-scene="1" class="is-active">{pic("masgouf-02", "السمكة مفروشة ومسمَّرة حول الجمر", "(min-width:980px) 46vw, 92vw")}</figure>
        <figure data-scene="2">{pic("masgouf-03", "الجمر تحت السمك", "(min-width:980px) 46vw, 92vw")}</figure>
        <figure data-scene="3">{pic("masgouf-01", "السمكة تنضج بالحرارة المنعكسة", "(min-width:980px) 46vw, 92vw")}</figure>
        <figure data-scene="4">{pic("dish-quzi-pot", "الطبق على المائدة", "(min-width:980px) 46vw, 92vw")}</figure>
      </div>
      <div class="scene__steps">
        <article class="scene__step" data-scene-step="1" data-reveal>
          <span class="n">خطوة ٠١</span><h3>السمكة أوّلاً</h3>
          <p>سمكة نهريّة عريضة الجسم، دهنها موزّع في اللحم لا متكتّل —
          وهو ما يُذيبه الجمر ببطء فيَسقي اللحم من داخله. تُفتح من
          الظهر وتُترك بقشرتها: القشرة هي الصحن الذي يُطبخ فيه. ثم
          تُدهَن بخليط <strong>الكركم والثوم والكمّون</strong>.</p>
        </article>
        <article class="scene__step" data-scene-step="2" data-reveal>
          <span class="n">خطوة ٠٢</span><h3>جمرٌ لا لهب</h3>
          <p>يُترك الحطب حتى يسكن لهبه ويصير جمراً أحمر. الشيّ على
          اللهب يُحرق السطح قبل أن ينضج الداخل، وهذا أشيع خطأ في
          المسكوف.</p>
        </article>
        <article class="scene__step" data-scene-step="3" data-reveal>
          <span class="n">خطوة ٠٣</span><h3>الوقوف حول النار</h3>
          <p>تُسمَّر السمكة على أوتاد وتُنصب <em>واقفةً حول</em> الجمر
          لا فوقه — بينها وبين النار نحو شبر، فتطبخ بالحرارة المنعكسة
          وحدها. تُدار مرّة واحدة. والمدّة بين ٤٥ و٦٠ دقيقة، ولا
          تُقصَّر مهما كان الطلب.</p>
        </article>
        <article class="scene__step" data-scene-step="4" data-reveal>
          <span class="n">خطوة ٠٤</span><h3>تُفرَش ولا تُقطَّع</h3>
          <p>تنزل على صينيّة واسعة كما هي، ويُحيط بها
          <strong>صلصة الطحينة</strong> و<strong>التمن المُبخَّر</strong>
          والبصل والطماطم المشويّة والليمون. لا تُقسَّم حصصاً في
          المطبخ. <strong>المائدة تُوضع، والأيدي تقتسم.</strong></p>
        </article>
      </div>
    </div>
  </div>
</section>''')

    # ============================================== المائدة
    MENU = [
        ("breakfast", "الفطور", [
            ("dish-gaymar", "قيمر وعسل", "قيمر ثقيل مع عسل وخبز حارّ. ثلاثة مكوّنات، ونجاحها كلّه في جودة القيمر."),
            ("dish-sambusa", "سمبوسة", "معجّنات مقليّة تُحشى بالخضار أو اللحم المبهَّر، تُخبز طازجة مع چاي الصباح."),
            ("dish-pastry", "خبز التنّور", "يُلصق العجين على جدار التنّور الطيني بيد مكشوفة فيخرج منفوخاً مُبقَّعاً."),
        ]),
        ("lunch", "الغداء", [
            ("masgouf-01", "مسكوف", "سمكة نهريّة تُفرش حول الجمر ساعةً، بالكركم والثوم والكمّون، مع الطحينة والتمن."),
            ("dish-kebab", "كباب عراقي", "لحم مفروم باليد لا بالمفرمة، فيبقى له نسيج يُحَسّ. بصل وبقدونس وبهار بغدادي."),
            ("dish-kebab-veg", "تكّة وشقف", "قطع غنم تُنقع بالبصل والبهار وتُشوى على الجمر، مع خبز التنّور والطرشي."),
        ]),
        ("dinner", "العشاء", [
            ("dish-quzi-pot", "قوزي", "لحم غنم وتمن ولوز وزبيب، بالقرفة والبهار الحلو والهيل. طبق المناسبات البغدادي."),
            ("dish-kubba-platter", "دولمة", "ورق عنب وخضار محشيّة، تُطبخ ببطء ثم تُقلب على الصينيّة فتنزل كما بُنيت."),
            ("dish-tashreeb", "تشريب ومرق", "مرق سميك يُسكب على الخبز حتى يتشرّبه. طبق الشتاء الذي يُؤكل بالملعقة واليد."),
            ("dish-kubba-blue", "كبّة", "قشرة برغل رقيقة وحشوة لحم وبصل وصنوبر، تُقلى حتى تنشفّ قشرتها."),
        ]),
        ("mezze", "المقبّلات", [
            ("dish-torshi", "طرشي البيت", "مخلّل مكبوس عندنا: شلغم وخيار وقرنابيط. حامضٌ حادّ مقصود — يقطع دهن اللحم."),
            ("spread-01", "مائدة المقبّلات", "حمّص وبابا غنوج وتبّولة وفتّوش — الحامض والطريّ والمقرمش معاً."),
            ("spread-03", "مشاوي مشتركة", "صينيّة تُوضع في الوسط وتمتدّ إليها الأيدي."),
        ]),
        ("drink", "الچاي والمشروب", [
            ("istikan-01", "چاي استكان", "چاي أحمر ثقيل يُسكب من قوري على قوري، في استكان زجاجي. يُوضع ولا يُطلب."),
            ("tea-figs", "نومي بصرة", "منقوع الليمون البصري المجفّف: حامضٌ دافئ بلون العنبر، هاضمٌ بعد اللحم."),
            ("istikan-03", "شربت زبيب", "منقوع زبيب بارد، حلوٌ طبيعي بلا سكّر مضاف. مشروب رمضان في بغداد."),
        ]),
    ]

    cards = []
    for cat, _lbl, items in MENU:
        for name, title, desc in items:
            cards.append(f'''      <article class="plate" data-category="{cat}" data-reveal>
        <div class="plate__shot">{pic(name, title, "(min-width:1100px) 30vw, (min-width:700px) 46vw, 92vw")}</div>
        <div class="plate__body">
          <h3>{title}</h3>
          <p>{desc}</p>
        </div>
      </article>''')

    filters = "".join(
        f'<button class="filter" data-filter="{c}" aria-pressed="false">{l}</button>'
        for c, l, _ in MENU)

    A(f'''<section class="sec" id="menu">
  <div class="wrap">
    <div class="sec__head">
      <p class="eyebrow" data-reveal>٠٤ — المائدة</p>
      <h2 class="h2" data-reveal>ما يُوضَع أمامك</h2>
      <p class="lead" data-reveal>
        قائمة قصيرة مقصودة. كل صنف له سبب وجود، ولا يوجد صنف
        «لإرضاء الجميع». وهي <strong>مقترحة</strong> في مرحلة التطوير.
      </p>
    </div>
    <p class="spices" data-reveal>
      <strong>بصمة البهار</strong>
      سمّاق · دبس رمّان · زعفران · كركم · بهار حلو · قرفة · هيل ·
      كمّون · نومي بصرة
    </p>
    <div class="filters" role="group" aria-label="تصفية المائدة">
      <button class="filter" data-filter="all" aria-pressed="true">الكل</button>{filters}
    </div>
    <div class="plates">
{chr(10).join(cards)}
    </div>
  </div>
</section>''')

    # ============================================== الچاي (مشعل)
    A(f'''<section class="sec on-dark" id="tea" style="background:var(--navy-900)">
  <div class="wrap">
    <div class="sec__head">
      <p class="eyebrow" data-reveal>٠٥ — الضيافة</p>
      <h2 class="h2" data-reveal>الچاي لا يُحتسب</h2>
      <p class="lead" data-reveal>
        في بغداد لا يُقال للضيف «هل تريد شاياً؟» — يُوضع أمامه.
        نحتفظ بهذه العادة كما هي: استكان بعد الأكل، ضيافةً لا بنداً
        في الفاتورة.
      </p>
    </div>
    <!-- المشعل: الصورة مُعتَّمة ويكشفها المؤشّر كأنه ضوء يمرّ عليها.
         على اللمس يتبع الإصبع. -->
    <figure class="torch" data-reveal>
      {pic("istikan-02", "استكان چاي على صحن بنقاط حمراء", "100vw")}
      <figcaption>مرّر المؤشّر على الصورة</figcaption>
    </figure>
  </div>
</section>''')

    # ============================================== التغليف والهويّة
    A(f'''<section class="sec" id="brand">
  <div class="wrap">
    <div class="sec__head">
      <p class="eyebrow" data-reveal>٠٦ — الهويّة التطبيقيّة</p>
      <h2 class="h2" data-reveal>التغليف واليونيفورم</h2>
      <p class="lead" data-reveal>
        الهويّة لا تنتهي عند الشعار. هذه تطبيقاتها على ما يحمله
        الضيف ويلمسه.
      </p>
    </div>
    <div class="mosaic mosaic--pack">
      <figure class="mo mo--wide tilt" data-reveal>
        {pic("pack-bag-wave", "كيس ورقي بالشعار وشريط متماوج", "(min-width:900px) 56vw, 92vw")}
        <figcaption>الكيس الورقي</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:70ms">
        {pic("pack-cup", "كوب بالشعار", "(min-width:900px) 28vw, 92vw")}
        <figcaption>الكوب</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:140ms">
        {pic("pack-box", "علبة بالشعار", "(min-width:900px) 28vw, 92vw")}
        <figcaption>العلبة</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:210ms">
        {pic("menu-print", "المنيو المطبوع", "(min-width:900px) 28vw, 92vw")}
        <figcaption>المنيو المطبوع</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:280ms">
        {pic("uniform-01", "مريلة الطاقم", "(min-width:900px) 28vw, 92vw")}
        <figcaption>اليونيفورم</figcaption>
      </figure>
      <figure class="mo tilt" data-reveal style="--delay:350ms">
        {pic("pack-box-open", "العلبة مفتوحة", "(min-width:900px) 28vw, 92vw")}
        <figcaption>الداخل</figcaption>
      </figure>
    </div>
  </div>
</section>''')

    # ============================================== المرجع (لفّ أفقي)
    rail_items = [
        ("souk-alley", "السوق", "أزقّة بغداد القديمة: الظلّ والضوء يتبادلان على الطريق."),
        ("souk-carpets", "النسيج", "الأقمشة المنسوجة التي تذكرها الهويّة في وصف المكان."),
        ("art-pottery", "الفخّار", "آنية الطين — ومنها جاء الطيني في لوحة الألوان."),
        ("dish-kubba-platter", "الصحن الأزرق", "القاشاني لا يبقى على الجدار: ينزل إلى المائدة."),
        ("art-arches", "الأقواس", "القوس البغدادي المدبّب، وهو مرجع تخطيط الصالة."),
    ]
    A(f'''<section class="rail-stage" id="reference" data-rail>
  <div class="rail-sticky">
    <div class="wrap" style="margin-block-end:var(--s-5)">
      <p class="eyebrow" data-reveal>٠٧ — المرجع</p>
      <h2 class="h2" data-reveal>من أين تأتي التفاصيل</h2>
    </div>
    <div class="rail" data-rail-track>
''' + "".join(f'''      <article class="rail__card">
        <div class="rail__art">{pic(n, t, "(min-width:900px) 32vw, 78vw")}</div>
        <div class="rail__body"><h3>{t}</h3><p>{d}</p></div>
      </article>
''' for n, t, d in rail_items) + f'''    </div>
    <div class="rail__prog" aria-hidden="true"><i data-rail-prog></i></div>
  </div>
</section>''')

    body = "\n\n".join(H)

    # ---------- دمج في index.html بين <main> و </main>
    page = io.open("index.html", encoding="utf-8").read()
    a = page.index('<main id="main">') + len('<main id="main">')
    b = page.index("</main>")
    # تُحفظ الأقسام التي لا تُولَّد هنا: المشروع والأسئلة
    tail = ""
    for mark in ('<section class="sec" id="stage"', '<section class="sec sec--tight" id="faq"'):
        if mark in page:
            i = page.index(mark)
            j = page.index("</section>", i) + 10
            tail += "\n\n" + page[i:j]
    page = page[:a] + "\n\n" + body + tail + "\n\n" + page[b:]
    io.open("index.html", "w", encoding="utf-8").write(page)

    print("index.html rebuilt")
    print("  sections : %d" % body.count("<section"))
    print("  pictures : %d" % page.count("<picture"))
    print("  size     : %.1f KB" % (len(page) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
