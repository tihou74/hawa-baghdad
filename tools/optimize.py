#!/usr/bin/env python3
"""
optimize — تحسين الصور للويب عبر canvas المتصفّح.

لماذا بهذه الطريقة
------------------
هذه البيئة بلا Pillow وبلا ImageMagick، وPyPI وnpm محجوبان. فلا أداة
تحويل صور متاحة... إلا واحدة موجودة أصلاً: **المتصفّح**.

فكلّ ما يفعله هذا السكربت أنه يبني صفحة تَرسم كل صورة على
`<canvas>` بالمقاس المطلوب، ثم تطلب `canvas.toDataURL('image/webp')`.
والمتصفّح يتولّى فكّ التشفير وإعادة التحجيم (بتصفية ثنائيّة الخطّ)
وترميز WebP. ثم تُستخرج النتائج من DOM وتُكتب ملفّات.

المكاسب حقيقيّة لا تجميليّة
---------------------------
  • WebP أصغر من JPEG بنحو ٣٠٪ وأصغر من PNG بكثير جدّاً لصور
    فوتوغرافيّة (PNG بلا ضياع فمقاسه ضخم للصور الواقعيّة).
  • تُولَّد عدّة عروض فيستطيع HTML أن يقدّم `srcset`، فلا يُنزّل
    الهاتف صورةً بعرض ١٢٠٠px ليعرضها في ٣٩٠px.

حدّ ٢٠٠٠ بكسل
-------------
كل المخرجات مقيَّدة بـ`MAX_EDGE`، فلا يُنتج هذا السكربت أبداً ملفاً
يتجاوز الحدّ — ولو كان الأصل أكبر. وبهذا تكون الصور الخارجة منه
آمنة للقراءة دائماً.

الاستخدام
---------
  python3 tools/optimize.py <src-dir> <out-dir> [--widths 480,960,1440]
  python3 tools/optimize.py media/incoming assets/img/photo
"""

import base64
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

MAX_EDGE = 2000
DEFAULT_WIDTHS = [480, 960, 1440]
QUALITY = 0.82


def dims(path):
    """أبعاد JPEG/PNG من الترويسة، بلا فكّ بكسل."""
    with open(path, "rb") as f:
        head = f.read(8)
        f.seek(0)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            f.seek(16)
            return struct.unpack(">II", f.read(8))
        if head[:2] == b"\xff\xd8":
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
                mv = m[0]
                if 0xC0 <= mv <= 0xCF and mv not in (0xC4, 0xC8, 0xCC):
                    f.read(3)
                    h, w = struct.unpack(">HH", f.read(4))
                    return w, h
                ln = struct.unpack(">H", f.read(2))[0]
                f.seek(ln - 2, 1)
    return None


def slug(name):
    """اسم لاتيني بلا مسافات: المسافات والعربيّة تنكسر في عناوين الويب."""
    base = os.path.splitext(name)[0]
    s = base.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "img"


def find_chrome():
    for c in ("chrome", "chromium", "google-chrome"):
        if subprocess.call(["which", c], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0:
            return c
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    src, out = args[0], args[1]

    widths = DEFAULT_WIDTHS
    for a in sys.argv[1:]:
        if a.startswith("--widths"):
            widths = [int(x) for x in a.split("=", 1)[1].split(",")]

    chrome = find_chrome()
    if not chrome:
        print("لا متصفّح متاح.")
        return 1

    os.makedirs(out, exist_ok=True)

    jobs = []
    for fn in sorted(os.listdir(src)):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        p = os.path.join(src, fn)
        d = dims(p)
        if not d:
            print("  تخطّي (أبعاد مجهولة): %s" % fn)
            continue
        w, h = d
        for tw in widths:
            if tw > w:                      # لا تكبير: يُنتج ضبابيّة لا تفصيلاً
                continue
            th = round(h * tw / w)
            if max(tw, th) > MAX_EDGE:      # ⚠ الحدّ الصلب
                continue
            jobs.append({"src": os.path.abspath(p), "name": slug(fn),
                         "w": tw, "h": th})
        # دائماً مقاس واحد على الأقل، مقيَّد بالحدّ
        if not any(j["name"] == slug(fn) for j in jobs):
            scale = min(1.0, MAX_EDGE / max(w, h))
            jobs.append({"src": os.path.abspath(p), "name": slug(fn),
                         "w": round(w * scale), "h": round(h * scale)})

    if not jobs:
        print("لا شيء للتحويل.")
        return 1

    page = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<pre id="OUT"></pre><script>
var JOBS = %s, Q = %s;
function one(j){
  return new Promise(function(res){
    var im = new Image();
    im.onload = function(){
      var c = document.createElement('canvas');
      c.width = j.w; c.height = j.h;
      var x = c.getContext('2d');
      x.imageSmoothingEnabled = true;
      x.imageSmoothingQuality = 'high';
      x.drawImage(im, 0, 0, j.w, j.h);
      var webp = c.toDataURL('image/webp', Q);
      var jpg  = c.toDataURL('image/jpeg', Q);
      res({name:j.name, w:j.w, h:j.h, webp:webp, jpg:jpg});
    };
    im.onerror = function(){ res({name:j.name, w:j.w, h:j.h, err:1}); };
    im.src = 'file://' + j.src;
  });
}
(async function(){
  var all = [];
  for (var i=0;i<JOBS.length;i++) all.push(await one(JOBS[i]));
  document.getElementById('OUT').textContent = JSON.stringify(all);
})();
</script></body></html>""" % (json.dumps(jobs), QUALITY)

    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                      encoding="utf-8")
    tmp.write(page)
    tmp.close()

    res = subprocess.run(
        [chrome, "--headless", "--no-sandbox", "--disable-gpu",
         "--allow-file-access-from-files",
         "--virtual-time-budget=60000", "--dump-dom", "file://" + tmp.name],
        capture_output=True, text=True)
    os.unlink(tmp.name)

    m = re.search(r'<pre id="OUT">(.*?)</pre>', res.stdout, re.S)
    if not m or not m.group(1).strip():
        print("فشل التحويل: لم يُرجع المتصفّح نتائج.")
        return 1

    import html as H
    data = json.loads(H.unescape(m.group(1)))

    total_in = total_out = 0
    print("%-34s %-12s %-11s %-11s %s" % ("الملف", "الأبعاد", "webp", "jpeg", "التوفير"))
    print("-" * 86)
    for r in data:
        if r.get("err"):
            print("  فشل: %s" % r["name"])
            continue
        stem = "%s-%d" % (r["name"], r["w"])
        wrote = {}
        for kind, key in (("webp", "webp"), ("jpg", "jpg")):
            b64 = r[key].split(",", 1)[1]
            raw = base64.b64decode(b64)
            path = os.path.join(out, "%s.%s" % (stem, kind))
            with open(path, "wb") as f:
                f.write(raw)
            wrote[kind] = len(raw)
        src_sz = os.path.getsize(
            os.path.join(src, next(fn for fn in os.listdir(src)
                                   if slug(fn) == r["name"])))
        total_in += src_sz
        total_out += wrote["webp"]
        print("%-34s %-12s %-11s %-11s %s" % (
            stem,
            "%dx%d" % (r["w"], r["h"]),
            "%.0fKB" % (wrote["webp"] / 1024),
            "%.0fKB" % (wrote["jpg"] / 1024),
            "%.0f%%" % (100 - wrote["webp"] / src_sz * 100)))

    print("-" * 86)
    print("أُنتجت %d صورة في %s" % (len(data) * 2, out))
    print("كل المخرجات ≤ %dpx — آمنة للقراءة." % MAX_EDGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
