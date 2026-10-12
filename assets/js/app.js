/* ============================================================================
   هوى بغداد — التحسين التدريجي فقط
   ----------------------------------------------------------------------------
   كل محتوى الصفحة موجود في HTML. هذا الملف يضيف صِقلاً. إن فشل تحميله
   تبقى الصفحة مقروءة وقابلة للتنقّل بالكامل.

   مبادئ ثابتة في هذا الملف:
   ١) لا قياس للتخطيط (layout read) داخل حدث التمرير إلا في إطار
      requestAnimationFrame واحد، وإلا تعثّر التمرير.
   ٢) كل ما يُحرَّك يُحرَّك بـ transform أو opacity — لا خصائص تُجبر
      المتصفّح على إعادة التخطيط.
   ٣) كل ميزة في دالّة معزولة لها حارسها: إن غاب عنصرها خرجت بصمت
      ولم تُسقط الميزات التي بعدها.
   ========================================================================== */
(function () {
  "use strict";

  /* المستند يصل بـ class="no-js" حتى تبقى عناصر [data-reveal] ظاهرة
     لمن لا يعمل عنده الجافاسكربت — بدل أن تبقى عند opacity:0 فتُنشر
     صفحة غير مرئيّة. إزالة الصنف هي أوّل ما يحدث. */
  var root = document.documentElement;
  root.classList.remove("no-js");

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasIO = "IntersectionObserver" in window;

  /* اتجاه الصفحة الفعليّ. تُقرأ مرّة واحدة وتُستخدم في حساب اللفّ
     الأفقي: الإشارة تختلف بين RTL و LTR. */
  var isRTL = (root.getAttribute("dir") || "").toLowerCase() === "rtl";

  /* الافتتاحيّة (بوّابة عشتار) أُزيلت بطلب العميل: رآها غير
     مناسبة. والصفحة تفتح الآن على الواجهة مباشرةً — وهو
     أسرع أصلاً: لا قفل تمرير، ولا طبقة ثابتة بحجم الشاشة،
     ولا ٥٤ كيلوبايت SVG مُدمَجة في HTML. */


  /* ==========================================================================
     ٢) الكشف عند الظهور — بديل مسار CSS
     المتصفّحات التي تدعم `animation-timeline: view()` تتولّى الأمر في
     cinematic.css. إضافة الصنف هنا لا تضرّها.
     ========================================================================== */
  (function reveal() {
    var els = document.querySelectorAll("[data-reveal]");
    if (!els.length) return;

    if (!hasIO || reduce) {
      els.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);     /* يُكشف مرّة واحدة */
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });

    els.forEach(function (el) { io.observe(el); });

    /* القوس المرسوم يستخدم نفس البوّابة */
    document.querySelectorAll(".arch-draw").forEach(function (el) { io.observe(el); });
  })();

  /* ==========================================================================
     ٣) محرّك ضوء الشناشيل + الترويسة + شريط التقدّم + العمق
     كلّها تعتمد على موضع التمرير، فتُجمع في إطار واحد. فصلها إلى
     مستمعات مستقلّة يعني قراءة التخطيط عدّة مرّات في الإطار نفسه.
     ========================================================================== */
  (function scrollEngine() {
    var hdr = document.getElementById("hdr");
    var pour = document.getElementById("pour");
    var hero = document.getElementById("top");
    var shafts = document.querySelector(".shanashil-light");
    var layers = Array.prototype.slice.call(document.querySelectorAll("[data-parallax]"));
    var ticking = false;

    function frame() {
      var y = window.scrollY || window.pageYOffset;
      var vh = window.innerHeight;
      var scrollable = document.documentElement.scrollHeight - vh;

      /* الترويسة تكتسب خلفيّتها بعد أن يبدأ التمرير فعلاً */
      if (hdr) hdr.classList.toggle("is-stuck", y > 60);

      /* شريط التقدّم: متغيّر واحد يقرؤه CSS بـ scaleX.
         لا تعديل على العرض — العرض يُجبر إعادة تخطيط، scaleX لا. */
      if (pour) {
        pour.style.setProperty("--progress", scrollable > 0 ? (y / scrollable).toFixed(4) : 0);
      }

      /* ---- مرور النهار ----
         `--sun` بين ٠ و١ يمثّل الوقت: ٠ فجر، ١ ليل. يُربط بتقدّم
         التمرير في أوّل ثلاث شاشات، ثم يستقرّ على ١ — لأن الهدف
         انتقال مزاجي في بداية الرحلة لا تذبذب طول الصفحة. */
      var sun = Math.min(1, y / Math.max(1, vh * 3));
      root.style.setProperty("--sun", sun.toFixed(4));

      /* شفرات الضوء تظهر بعد الواجهة وتخبو في أعماق الصفحة:
         ضوء النافذة منطقيّ في النهار لا في كل مكان. */
      if (shafts) {
        var inBody = Math.min(1, Math.max(0, (y - vh * 0.5) / (vh * 0.9)));
        var fade = scrollable > 0 ? Math.min(1, Math.max(0, (scrollable - y) / (vh * 1.4))) : 1;
        root.style.setProperty("--shaft-opacity", (inBody * fade * 0.5).toFixed(3));
      }

      /* ---- عمق الشرائط ----
         بـ transform لا background-attachment: fixed — الأخيرة تُجبر
         إعادة رسم الخلفيّة كل إطار فيتقطّع التمرير على الهاتف. */
      if (!reduce) {
        layers.forEach(function (layer) {
          var band = layer.parentElement;
          if (!band) return;
          var r = band.getBoundingClientRect();
          if (r.bottom < 0 || r.top > vh) return;      /* خارج الشاشة: لا حساب */
          var p = (r.top + r.height / 2 - vh / 2) / vh;
          layer.style.transform = "translate3d(0," + (p * -44).toFixed(2) + "px,0)";
        });
      }

      ticking = false;
    }

    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(frame);
    }, { passive: true });
    window.addEventListener("resize", frame, { passive: true });
    frame();

    /* الواجهة تبدأ عند الفجر دائماً */
    if (hero) root.style.setProperty("--sun", "0");
  })();

  /* ==========================================================================
     ٤) شارع بغداد — اللفّ الأفقي المربوط بالتمرير
     --------------------------------------------------------------------------
     ⚠ هذا الموضع بالتحديد كلّف جلسةً كاملة في مشروع سابق، فليُقرأ
     التعليق قبل تعديل أي إشارة:

     في صفحة RTL تمتدّ الزيادة في حاوية flex إلى *اليسار* من نقطة
     البداية. فالكشف عن المحتوى المخفيّ يتطلّب تحريك الشريط إلى
     *اليمين* — أي `translateX` بقيمة **موجبة**. القيمة السالبة تدفعه
     بعيداً عن الشاشة فيبدو للعميل أن «لا شيء يتحرّك».

     في LTR العكس تماماً: القيمة سالبة.
     لذا الإشارة مشتقّة من `isRTL` ولا تُكتب يدوياً.
     ========================================================================== */
  (function rail() {
    var stage = document.querySelector("[data-rail]");
    if (!stage || reduce) return;

    var sticky = stage.querySelector(".rail-sticky");
    var track = stage.querySelector("[data-rail-track]");
    var prog = stage.querySelector("[data-rail-prog]");
    if (!sticky || !track) return;

    var cards = Array.prototype.slice.call(track.querySelectorAll(".rail__card"));
    var mobile = window.matchMedia("(max-width: 860px)");
    var raf = null;

    /* ارتفاع المسرح يُحسب من طول الشريط: يجب أن تكفي مسافة التمرير
       العموديّة لعرض كل اللفّ الأفقي. ١٢٠٪ هامش يمنح نَفَساً في
       أوّل القسم وآخره. */
    function size() {
      if (mobile.matches) { stage.style.removeProperty("height"); return; }
      var dist = Math.max(0, track.scrollWidth - sticky.clientWidth);
      stage.style.height = (window.innerHeight + dist * 1.2) + "px";
    }

    function run() {
      raf = null;
      if (mobile.matches) { track.style.removeProperty("transform"); return; }

      var r = stage.getBoundingClientRect();
      var total = stage.offsetHeight - window.innerHeight;
      var p = total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : 0;

      var dist = Math.max(0, track.scrollWidth - sticky.clientWidth);
      var sign = isRTL ? 1 : -1;        /* ← الإشارة الحرجة. لا تُغيَّر يدوياً. */
      track.style.transform = "translate3d(" + (sign * p * dist).toFixed(1) + "px,0,0)";

      if (prog) prog.style.width = (p * 100).toFixed(1) + "%";

      /* إضاءة البطاقة الأقرب لمنتصف الشاشة */
      var mid = window.innerWidth / 2, best = null, bestD = Infinity;
      cards.forEach(function (c) {
        var b = c.getBoundingClientRect();
        var d = Math.abs(b.left + b.width / 2 - mid);
        if (d < bestD) { bestD = d; best = c; }
      });
      cards.forEach(function (c) { c.classList.toggle("is-focus", c === best); });
    }

    function kick() { if (!raf) raf = window.requestAnimationFrame(run); }

    size();
    run();
    window.addEventListener("scroll", kick, { passive: true });
    window.addEventListener("resize", function () { size(); kick(); }, { passive: true });
    /* أبعاد الشريط تتغيّر بعد تحميل الخطوط والصور، فيُعاد القياس */
    window.addEventListener("load", function () { size(); kick(); });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () { size(); kick(); });
    }
    mobile.addEventListener("change", function () { size(); kick(); });
  })();

  /* ==========================================================================
     ٥) المشهد المثبَّت — الصورة تتبع الخطوة المقروءة
     CSS يتولّى تثبيت العمود؛ هذه الدالّة تقرّر أي لوحة تظهر فقط.
     ========================================================================== */
  (function scene() {
    var media = document.querySelector("[data-scene-media]");
    if (!media || !hasIO) return;

    var figures = media.querySelectorAll("[data-scene]");
    var steps = document.querySelectorAll("[data-scene-step]");
    if (!figures.length || !steps.length) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var want = entry.target.getAttribute("data-scene-step");
        figures.forEach(function (fig) {
          fig.classList.toggle("is-active", fig.getAttribute("data-scene") === want);
        });
      });
    }, { rootMargin: "-45% 0px -45% 0px" });

    steps.forEach(function (s) { io.observe(s); });
  })();

  /* ==========================================================================
     ٦) إبراز القسم الحالي في التنقّل
     ========================================================================== */
  (function activeNav() {
    var links = {};
    document.querySelectorAll(".nav a[href^='#']").forEach(function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });
    var ids = Object.keys(links);
    if (!ids.length || !hasIO) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        ids.forEach(function (k) { links[k].removeAttribute("aria-current"); });
        var a = links[entry.target.id];
        if (a) a.setAttribute("aria-current", "true");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });

    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) io.observe(el);
    });
  })();

  /* ==========================================================================
     ٧) قائمة الهاتف
     ========================================================================== */
  (function burger() {
    var btn = document.getElementById("burger");
    var nav = document.getElementById("nav");
    if (!btn || !nav) return;

    function close() {
      btn.setAttribute("aria-expanded", "false");
      nav.classList.remove("is-open");
    }

    btn.addEventListener("click", function () {
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      nav.classList.toggle("is-open", !open);
    });

    /* تُغلق عند اختيار رابط، وعند Escape */
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
  })();

  /* ==========================================================================
     ٨) تصفية المائدة
     `hidden` لا `display:none` بـ JS: يُخرج العنصر من شجرة الوصوليّة
     أيضاً، فلا يقرأ قارئ الشاشة أصنافاً مخفيّة.
     ========================================================================== */
  (function filters() {
    var buttons = document.querySelectorAll(".filter");
    var items = document.querySelectorAll("[data-category]");
    if (!buttons.length || !items.length) return;

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var want = btn.getAttribute("data-filter");

        buttons.forEach(function (b) {
          b.setAttribute("aria-pressed", String(b === btn));
        });

        items.forEach(function (item) {
          item.hidden = !(want === "all" || item.getAttribute("data-category") === want);
        });
      });
    });
  })();

  /* ==========================================================================
     ٩) جمر النار — توزيع عشوائي خفيف
     القيم مكتوبة في HTML أصلاً فيعمل القسم بلا جافاسكربت؛ هذه الدالّة
     تكسر التناسق فقط فلا يتكرّر النمط بشكل ملحوظ.
     ========================================================================== */
  (function embers() {
    if (reduce) return;
    document.querySelectorAll(".fire__embers b").forEach(function (b) {
      b.style.setProperty("--t", (Math.random() * 6).toFixed(2) + "s");
      b.style.setProperty("--d", (5.5 + Math.random() * 4.5).toFixed(2) + "s");
      b.style.setProperty("--dx", ((Math.random() - 0.5) * 70).toFixed(0) + "px");
    });
  })();

  /* ==========================================================================
     ١٠) السنة في الذيل — بالأرقام العربيّة-الهنديّة
     الصفحة عربيّة، فالأرقام تتبعها. التحويل يدوي لأن
     `toLocaleString('ar-EG')` يختلف سلوكه بين المتصفّحات.
     ========================================================================== */
  (function year() {
    var el = document.getElementById("year");
    if (!el) return;
    var AR = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];
    el.textContent = String(new Date().getFullYear()).replace(/\d/g, function (d) {
      return AR[+d];
    });
  })();

  /* ==========================================================================
     ١١) تمرير سلس لروابط المرساة فقط
     `scroll-behavior: smooth` على html يجعل كل قفزة رحلةً بطيئة —
     بما فيها القفزات البرمجيّة. فيُقصر على نيّة المستخدم الصريحة.
     ========================================================================== */
  (function anchors() {
    if (reduce) return;
    document.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute("href").slice(1);
      if (!id) return;
      var target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      /* يُحدَّث العنوان دون إضافة مدخل لسجلّ التصفّح */
      history.replaceState(null, "", "#" + id);
    });
  })();
})();

/* ============================================================================
   تأثيرات إضافيّة — تُحمَّل بعد الأساس
   ----------------------------------------------------------------------------
   كلها تحسين تدريجي: إن لم تعمل بقي المحتوى كاملاً ومقروءاً. وكلها
   تُلغى عند `prefers-reduced-motion`، ولا تُشغَّل إلا حيث تُجدي —
   فالتأثير المربوط بالمؤشّر لا معنى له على الهاتف.
   ========================================================================== */
(function () {
  "use strict";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  /* ==========================================================================
     المشعل — ضوء يكشف الصورة المُعتَّمة
     القناع الدائري يتبع المؤشّر، ونصف قطره ينمو بالتنعيم لا قفزاً.
     ========================================================================== */
  (function torch() {
    var els = document.querySelectorAll(".torch");
    if (!els.length || reduce) return;

    els.forEach(function (el) {
      var r = 0, target = 0, raf = null;

      function grow() {
        r += (target - r) * 0.18;
        el.style.setProperty("--tr", r.toFixed(1) + "px");
        if (Math.abs(target - r) > 0.6) {
          raf = window.requestAnimationFrame(grow);
        } else {
          r = target;
          el.style.setProperty("--tr", r.toFixed(1) + "px");
          raf = null;
        }
      }
      function kick() { if (!raf) raf = window.requestAnimationFrame(grow); }

      function move(x, y) {
        var b = el.getBoundingClientRect();
        el.style.setProperty("--tx", (((x - b.left) / b.width) * 100).toFixed(2) + "%");
        el.style.setProperty("--ty", (((y - b.top) / b.height) * 100).toFixed(2) + "%");
      }

      el.addEventListener("pointerenter", function (e) {
        el.classList.add("is-live");
        move(e.clientX, e.clientY);
        target = Math.min(el.clientWidth, el.clientHeight) * 0.46;
        kick();
      });
      el.addEventListener("pointermove", function (e) { move(e.clientX, e.clientY); });
      el.addEventListener("pointerleave", function () {
        target = 0;
        kick();
        /* الصنف يُزال بعد انقباض القناع، وإلا عاد التعتيم فجأةً */
        window.setTimeout(function () {
          if (target === 0) el.classList.remove("is-live");
        }, 420);
      });

      /* على اللمس: المشعل يتبع الإصبع */
      el.addEventListener("touchmove", function (e) {
        if (!e.touches.length) return;
        el.classList.add("is-live");
        move(e.touches[0].clientX, e.touches[0].clientY);
        target = Math.min(el.clientWidth, el.clientHeight) * 0.5;
        kick();
      }, { passive: true });
    });
  })();

  /* ==========================================================================
     الميل ثلاثي الأبعاد
     ⚠ مُقيَّد بـ(hover:hover) و(pointer:fine): تأثيرٌ لا يعمل على
     الهاتف أصلاً، وتشغيله هناك يُضيف حساباً بلا أي فائدة مرئيّة.
     ========================================================================== */
  (function tilt() {
    if (reduce || !fine) return;
    var els = document.querySelectorAll(".tilt");
    if (!els.length) return;

    els.forEach(function (el) {
      var raf = null, nx = 0, ny = 0;

      function apply() {
        raf = null;
        el.style.transform =
          "perspective(900px) rotateY(" + (nx * 5).toFixed(2) + "deg) rotateX(" +
          (-ny * 5).toFixed(2) + "deg) translateY(-4px)";
      }

      el.addEventListener("pointermove", function (e) {
        var b = el.getBoundingClientRect();
        nx = (e.clientX - (b.left + b.width / 2)) / (b.width / 2);
        ny = (e.clientY - (b.top + b.height / 2)) / (b.height / 2);
        if (!raf) raf = window.requestAnimationFrame(apply);
      });
      el.addEventListener("pointerleave", function () {
        if (raf) { window.cancelAnimationFrame(raf); raf = null; }
        el.style.transform = "";
      });
    });
  })();

  /* ==========================================================================
     جمر النار — توزيع عشوائي خفيف
     القيم الافتراضيّة في CSS، وهذه تكسر التناسق فقط.
     ========================================================================== */
  (function embers() {
    if (reduce) return;
    document.querySelectorAll(".fire__embers b").forEach(function (b) {
      b.style.setProperty("--t", (Math.random() * 7).toFixed(2) + "s");
      b.style.setProperty("--d", (6 + Math.random() * 5).toFixed(2) + "s");
      b.style.setProperty("--dx", ((Math.random() - 0.5) * 80).toFixed(0) + "px");
    });
  })();
})();

/* ============================================================================
   الفيديو — حمايات، وتشغيل جزء محدّد
   ----------------------------------------------------------------------------
   `<video autoplay>` وحده يُنزّل ميغابايتات على كل زائر، حتى من كان على
   بيانات جوّال أو طلب تقليل الحركة. فالشروط تُفحَص أوّلاً:

     ١) تقليل الحركة   : لا تحميل إطلاقاً.
     ٢) توفير البيانات : saveData أو شبكة 2g — لا تحميل.
     ٣) القرب من الشاشة: لا تحميل قبل أن يقترب العنصر.
     ٤) فشل التحميل    : يُهمَل بصمت ويبقى البديل (صورة).

   واستخدام **جزء** من المقطع:
   لا ffmpeg في بيئة البناء فلا يمكن قصّ الملف. والحلّ أن يُحصَر
   التشغيل في مدى `data-start`..`data-end` ويُكرَّر منه — فالنتيجة
   كالقصّ بلا قصّ، ويبقى الملف الأصلي كاملاً على القرص.
   و`data-end="0"` تعني «إلى آخر المقطع».
   ========================================================================== */
(function () {
  "use strict";

  var vids = document.querySelectorAll("video[data-src]");
  if (!vids.length) return;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    vids.forEach(function (v) { v.remove(); });
    return;
  }

  var net = navigator.connection || {};
  if (net.saveData || /(^|-)(2g|slow-2g)$/.test(net.effectiveType || "")) {
    vids.forEach(function (v) { v.remove(); });
    return;
  }

  function setup(v) {
    var start = parseFloat(v.getAttribute("data-start")) || 0;
    var end = parseFloat(v.getAttribute("data-end")) || 0;

    /* `data-rate`: إبطاء المقطع القصير
       ------------------------------------------------------------
       مقطع ١٫٧ ثانية يُكرَّر كل ثانيتين، فيُقرأ تشنّجاً لا حركة.
       والإبطاء يُضاعف مدّته المحسوسة بلا ملفّ جديد — وصبّ الصلصة
       بطيئاً أفخم بصرياً من سرعته الأصليّة، فالمكسب مزدوج. */
    var rate = parseFloat(v.getAttribute("data-rate"));
    if (rate > 0) {
      v.addEventListener("loadedmetadata", function () {
        try { v.playbackRate = rate; } catch (e) { /* يُتجاهل */ }
      }, { once: true });
    }

    v.src = v.getAttribute("data-src");
    v.removeAttribute("data-src");

    /* الحلقة اليدويّة تُغني عن `loop`: لا بدّ من العودة إلى
       `start` لا إلى الصفر. */
    if (start > 0 || end > 0) v.removeAttribute("loop");

    v.addEventListener("loadedmetadata", function () {
      /* لا يُنقَل الموضع قبل بدء التشغيل.
         ------------------------------------------------------------
         كان `currentTime = start` يُضبط هنا، قبل أي تشغيل. وبعض
         الملفّات يفشل فيها الانتقال فلا يُطلق `canplay` أبداً —
         فلا يبدأ التشغيل، ولا يُضاف `has-video`، وتبقى الصورة
         الثابتة. وهذا ما حدث مع `hero.mp4`: ظهرت الصورة بدل
         النار على الهاتف وفي الصندوق معاً.
         فالانتقال صار **بعد** أن يبدأ التشغيل فعلاً، وفشله لا
         يمنع ظهور المقطع. */

      /* المصدر العموديّ لا يُفرَش على حاوية عريضة.
         ------------------------------------------------------------
         مقطع هاتف 480×848 مفروشاً على خلفيّة 1440 عريضة يُقصّ إلى
         شريط أوسط بعرض ~283px ثم يُكبَّر ٣×، فيخرج ضبابياً ويفقد
         المشهد. فتُقاس النسبة من الملفّ نفسه — لا تُفترض — وتُعلَّم
         الحالة ليتولّى CSS عرضه في «نافذة» رأسيّة بأبعاده.
         والقياس هنا لأن الأبعاد لا تُعرف قبل وصول البيانات
         الوصفيّة. */
      if (v.videoWidth && v.videoHeight) {
        var portrait = v.videoHeight > v.videoWidth;
        v.classList.toggle("is-portrait", portrait);

        /* الأطراف تُملأ بنفس المقطع مضبَّباً — لا بصورة أخرى.
           ------------------------------------------------------------
           المحاولة الأولى تركت الصورة الثابتة خلف الفيديو، فظهرت
           ثلاث صور متجاورة بخطّين واضحين (سمكة | نار | سمكة).
           فتُنسخ نسخة ثانية من **نفس** الملفّ تملأ العرض مكبَّرة
           ومضبَّبة: المشهد واحد فلا يُدرَك خطّ القصّ.

           وتُنشأ من هنا لا من HTML: لا تُعرف نسبة الملفّ قبل وصول
           بياناته الوصفيّة، وإنشاؤها دائماً يعني فكّ مقطع إضافي
           على كل زائر حتى لو كان المصدر أفقياً. */
        var host = v.parentElement;
        /* المشهد (`.reel`) لا يحتاج ملئاً ضبابياً: المقطع يملأ
           الشاشة على الهاتف، ويصير عموداً على الشاشة العريضة. */
        if (portrait && host && !host.classList.contains("reel")
            && !host.querySelector(".vid-fill")) {
          var wide = host.clientWidth > host.clientHeight;
          if (wide) {
            var bg = document.createElement("video");
            bg.className = "vid-fill";
            bg.muted = true;
            bg.loop = true;
            bg.playsInline = true;
            bg.setAttribute("aria-hidden", "true");
            bg.src = v.currentSrc || v.src;
            host.insertBefore(bg, v);
            bg.play().then(function () {
              bg.classList.add("is-ready");
            }).catch(function () {
              bg.remove();          /* لا تبقى طبقة سوداء */
            });
          }
        }
      }
    }, { once: true });

    /* `timeupdate` يكفي: دقّته نحو ٢٥٠ms وهي كافية لحلقة خلفيّة،
       وأرخص بكثير من requestAnimationFrame لكل إطار. */
    if (start > 0 || end > 0) {
      v.addEventListener("timeupdate", function () {
        var stop = end > start ? end : (v.duration || 0);
        if (stop && v.currentTime >= stop - 0.05) {
          try { v.currentTime = start; } catch (e) { /* يُتجاهل */ }
          v.play().catch(function () {});
        }
      });
    }

    var launched = false;
    function launch() {
      if (launched) return;
      launched = true;
      v.play().then(function () {
        v.classList.add("is-ready");
        /* تُخفى الصورة الثابتة الآن فقط — بعد تأكّد التشغيل.
           إخفاؤها مبكّراً يترك مستطيلاً فارغاً إن فشل الفيديو. */
        if (v.parentElement) v.parentElement.classList.add("has-video");
        /* الانتقال بعد التشغيل: فشله يقصّر المقطع ولا يُخفيه */
        if (start > 0 && start < (v.duration || Infinity)) {
          try { v.currentTime = start; } catch (e) { /* يُتجاهل */ }
        }
      }).catch(function () {
        /* رُفض التشغيل التلقائي: تبقى الصورة الثابتة. */
        launched = false;
      });
    }

    /* ثلاث فرص لا واحدة: `loadeddata` أسرع من `canplay`، وبعض
       الملفّات لا تُطلق `canplay` إطلاقاً. والمؤقّت حارسٌ أخير. */
    v.addEventListener("loadeddata", launch, { once: true });
    v.addEventListener("canplay", launch, { once: true });
    setTimeout(launch, 3500);

    v.addEventListener("error", function () {
      /* الملف غير مرفوع بعد أو تعذّر فكّه: تعود الصورة الثابتة
         وتُزال طبقة الملء، فلا يبقى فراغ ولا ضباب بلا مقطع. */
      var host = v.parentElement;
      if (host) {
        host.classList.remove("has-video");
        var fill = host.querySelector(".vid-fill");
        if (fill) fill.remove();
      }
      v.remove();
    }, { once: true });
  }

  if (!("IntersectionObserver" in window)) {
    vids.forEach(setup);
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      setup(e.target);
    });
  }, { rootMargin: "250px" });
  vids.forEach(function (v) { io.observe(v); });

  /* إيقاف ما خرج عن الشاشة: فكّ عدّة مقاطع في وقت واحد يُسخّن
     الهاتف بلا فائدة. */
  var vis = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var v = e.target;
      if (v.hasAttribute("data-src")) return;
      if (e.isIntersecting) { v.play().catch(function () {}); }
      else { v.pause(); }
    });
  }, { threshold: 0.2 });
  vids.forEach(function (v) { vis.observe(v); });
})();

/* ============================================================================
   خطّ الرحلة — المحطّات والتقدّم
   ----------------------------------------------------------------------------
   المحطّات تُبنى من الأقسام التي تحمل `data-chapter`، فإضافة فصل أو
   حذفه لا يحتاج تعديل هذا الملف. وموضع كل محطّة يُحسب من موضع قسمها
   في الصفحة، فيبقى الخطّ مطابقاً للمحتوى أيّاً كان طوله.
   ========================================================================== */
(function () {
  "use strict";

  var spine = document.querySelector(".spine");
  if (!spine) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    spine.remove();
    return;
  }

  var list = spine.querySelector(".spine__stops");
  var flow = spine.querySelector(".spine__flow");
  var secs = Array.prototype.slice.call(document.querySelectorAll("[data-chapter]"));
  if (!list || !secs.length) { spine.remove(); return; }

  var stops = secs.map(function (sec) {
    var li = document.createElement("li");
    li.className = "spine__stop";
    li.innerHTML = '<i></i><b>' +
      (sec.getAttribute("data-chapter-name") || "") + "</b>";
    list.appendChild(li);
    return { el: li, sec: sec };
  });

  var raf = null;

  function place() {
    var docH = document.documentElement.scrollHeight;
    stops.forEach(function (s) {
      var top = s.sec.getBoundingClientRect().top + window.scrollY;
      s.el.style.insetBlockStart = (top / docH * 100).toFixed(3) + "%";
    });
  }

  function frame() {
    raf = null;
    var y = window.scrollY || window.pageYOffset;
    var scrollable = document.documentElement.scrollHeight - window.innerHeight;
    var p = scrollable > 0 ? y / scrollable : 0;
    if (flow) flow.style.setProperty("--flow", p.toFixed(4));

    /* المحطّة الحاليّة: أقرب قسم تجاوز منتصف الشاشة */
    var mid = y + window.innerHeight * 0.42;
    var here = -1;
    stops.forEach(function (s, i) {
      var top = s.sec.getBoundingClientRect().top + y;
      if (top <= mid) here = i;
    });
    stops.forEach(function (s, i) {
      s.el.classList.toggle("is-passed", i <= here);
      s.el.classList.toggle("is-here", i === here);
    });
  }

  function kick() { if (!raf) raf = window.requestAnimationFrame(frame); }

  place();
  frame();
  window.addEventListener("scroll", kick, { passive: true });
  window.addEventListener("resize", function () { place(); kick(); }, { passive: true });
  window.addEventListener("load", function () { place(); kick(); });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { place(); kick(); });
  }
})();

/* ============================================================================
   القنديل — وهج يتبع المؤشّر على الفصول الداكنة
   ========================================================================== */
(function () {
  "use strict";
  var el = document.querySelector(".lantern");
  if (!el) return;
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.remove();
    return;
  }
  var raf = null, x = 0, y = 0;
  function apply() {
    raf = null;
    el.style.setProperty("--lx", x + "px");
    el.style.setProperty("--ly", y + "px");
  }
  window.addEventListener("pointermove", function (e) {
    x = e.clientX; y = e.clientY;
    /* يُضاء على الأرضيّات الداكنة فقط: على الفاتحة لا يُرى أثره
       ويبدو كضباب. */
    var over = document.elementFromPoint(x, y);
    var dark = over && over.closest(".on-dark, .band, .hero, .signature");
    el.classList.toggle("is-on", !!dark);
    if (!raf) raf = window.requestAnimationFrame(apply);
  }, { passive: true });
  window.addEventListener("pointerleave", function () { el.classList.remove("is-on"); });
})();

/* ============================================================================
   ترقيم كلمات العناوين — لتتابع الكشف
   ========================================================================== */
(function () {
  "use strict";
  document.querySelectorAll(".h2--words").forEach(function (h) {
    h.querySelectorAll(".w").forEach(function (w, i) {
      w.querySelector("i").style.setProperty("--i", i);
    });
  });
})();
