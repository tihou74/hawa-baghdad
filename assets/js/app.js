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
