#!/usr/bin/env python3
"""
video — فحص ملفّات الفيديو واستخراج صورة الغلاف، بلا ffmpeg.

القيد الذي شكّل هذه الأداة
--------------------------
لا `ffmpeg` ولا `ffprobe` ولا `mediainfo` في هذه البيئة، وPyPI محجوب.
فلا يمكن **تحويل** الفيديو ولا ضغطه — ولهذا يجب أن يصل جاهزاً للويب.

لكن شيئين ممكنان بلا أي اعتماديّة:

  probe  : بنية MP4 عبارة عن «صناديق» (boxes) متداخلة موصوفة في
           المعيار ISO/IEC 14496-12. فتُقرأ الأبعاد من `tkhd` والمدّة
           من `mvhd` والمرمّز من `stsd` بقراءة بايتات الترويسة وحدها،
           بلا فكّ أي إطار.

  poster : المتصفّح يفكّ الفيديو أصلاً. فتُحمَّل الصورة في صفحة
           مخفيّة، ويُطلب منها الانتقال إلى ثانية محدّدة، ثم تُرسم
           على `<canvas>` ويُطلب `toDataURL`. فنحصل على إطار بصيغة
           JPEG/WebP بلا محوّل.
           وهذا مهم لا تجميلي: الفيديو بلا `poster` يُظهر مستطيلاً
           أسود حتى يبدأ التحميل، وعلى اتصال بطيء قد لا يبدأ أبداً.

الاستخدام
---------
  python3 tools/video.py probe  media/video/*.mp4
  python3 tools/video.py poster media/video/fire.mp4 assets/img/video 1.5
"""

import base64
import functools
import http.server
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading

MAX_EDGE = 2000           # حدّ قراءة الصور
WARN_MB = 8               # فوقه يُثقل الهاتف
HARD_MB = 100             # حدّ GitHub الصلب لكل ملف


# ----------------------------------------------------- تحليل صناديق MP4

def boxes(data, start, end):
    """يمرّ على صناديق المستوى الواحد ويُرجع (نوع, بداية المحتوى, نهايته)."""
    i = start
    while i + 8 <= end:
        size = struct.unpack(">I", data[i:i + 4])[0]
        typ = data[i + 4:i + 8]
        if size == 1:                       # حجم 64-بت
            if i + 16 > end:
                return
            size = struct.unpack(">Q", data[i + 8:i + 16])[0]
            body = i + 16
        elif size == 0:                     # يمتدّ إلى آخر الملف
            size = end - i
            body = i + 8
        else:
            body = i + 8
        if size < 8:
            return
        yield typ, body, min(i + size, end)
        i += size


def find(data, path, start=0, end=None):
    """يبحث عن صندوق بمسار مثل [b'moov', b'mvhd']."""
    end = len(data) if end is None else end
    for typ, b, e in boxes(data, start, end):
        if typ == path[0]:
            if len(path) == 1:
                return b, e
            r = find(data, path[1:], b, e)
            if r:
                return r
    return None


def probe(path):
    data = open(path, "rb").read()
    info = {"file": path, "bytes": os.path.getsize(path)}

    ft = find(data, [b"ftyp"])
    if ft:
        info["brand"] = data[ft[0]:ft[0] + 4].decode("latin-1", "replace")

    mv = find(data, [b"moov", b"mvhd"])
    if mv:
        b = mv[0]
        ver = data[b]
        if ver == 1:
            ts = struct.unpack(">I", data[b + 20:b + 24])[0]
            dur = struct.unpack(">Q", data[b + 24:b + 32])[0]
        else:
            ts = struct.unpack(">I", data[b + 12:b + 16])[0]
            dur = struct.unpack(">I", data[b + 16:b + 20])[0]
        if ts:
            info["seconds"] = round(dur / ts, 2)

    # أكبر مسار أبعاداً هو مسار الصورة
    best = (0, 0)
    mo = find(data, [b"moov"])
    if mo:
        for typ, b, e in boxes(data, mo[0], mo[1]):
            if typ != b"trak":
                continue
            tk = find(data, [b"tkhd"], b, e)
            if tk:
                tb = tk[0]
                # إزاحة width/height من بداية محتوى tkhd:
                #   نسخة 0: flags4 + ctime4 + mtime4 + id4 + res4 + dur4 = 24
                #   نسخة 1: flags4 + ctime8 + mtime8 + id4 + res4 + dur8 = 36
                #   ثم reserved8 + layer2 + alt2 + volume2 + res2 = 16
                #   ثم matrix36  →  76 (نسخة 0) أو 88 (نسخة 1)
                off = 88 if data[tb] == 1 else 76
                if tb + off + 8 <= len(data):
                    w = struct.unpack(">I", data[tb + off:tb + off + 4])[0] >> 16
                    h = struct.unpack(">I", data[tb + off + 4:tb + off + 8])[0] >> 16
                    if w * h > best[0] * best[1]:
                        best = (w, h)
            sd = find(data, [b"mdia", b"minf", b"stbl", b"stsd"], b, e)
            if sd:
                codec = data[sd[0] + 12:sd[0] + 16].decode("latin-1", "replace")
                if codec.strip() and "codec" not in info:
                    info["codec"] = codec
    if best != (0, 0):
        info["width"], info["height"] = best

    # صوت؟ وجود مسار بـ mp4a
    info["has_audio"] = b"mp4a" in data[:min(len(data), 2_000_000)]
    # هل البيانات الوصفيّة في المقدّمة؟ (faststart) — شرط البدء السريع
    mo_i = data.find(b"moov")
    md_i = data.find(b"mdat")
    info["faststart"] = (mo_i != -1 and (md_i == -1 or mo_i < md_i))
    return info


def cmd_probe(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith((".mp4", ".m4v", ".mov", ".webm"))]
        elif os.path.isfile(p):
            files.append(p)
    if not files:
        print("لا ملفّات فيديو في المسار المحدَّد.")
        return 0

    problems = 0
    for p in files:
        print("=" * 72)
        if p.lower().endswith(".webm"):
            mb = os.path.getsize(p) / 1048576
            print("  %s\n  صيغة webm — الفحص هنا لـMP4 فقط. الحجم %.1fMB" % (p, mb))
            continue
        try:
            i = probe(p)
        except Exception as e:
            print("  %s\n  ⛔ تعذّر التحليل: %s" % (p, e))
            problems += 1
            continue

        mb = i["bytes"] / 1048576
        print("  الملف    : %s" % i["file"])
        print("  الأبعاد  : %sx%s" % (i.get("width", "?"), i.get("height", "?")))
        print("  المدّة    : %s ثانية" % i.get("seconds", "?"))
        print("  المرمّز   : %s" % i.get("codec", "?"))
        print("  الحجم    : %.2f MB" % mb)
        print("  صوت      : %s" % ("نعم" if i.get("has_audio") else "لا"))
        print("  faststart: %s" % ("نعم" if i.get("faststart") else "لا"))
        print("  ---")

        ok = True
        w, h = i.get("width", 0), i.get("height", 0)
        if mb > HARD_MB:
            print("  ⛔ أكبر من %dMB — GitHub **يرفض** الرفع." % HARD_MB); ok = False
        elif mb > WARN_MB:
            print("  ⚠ %.1fMB أثقل من اللازم لخلفيّة ويب. المستهدف أقل من %dMB."
                  % (mb, WARN_MB)); ok = False
        if w and w > 1280:
            print("  ⚠ العرض %d أكبر من 1280 — بلا فائدة مرئيّة وبكلفة أداء." % w)
            ok = False
        if h > w and w:
            print("  ⚠ عمودي. الخلفيّة العريضة تحتاج أفقياً (16:9).")
        if i.get("seconds", 0) > 20:
            print("  ⚠ %s ثانية طويل لمقطع يُكرَّر. المستهدف 8–12."
                  % i.get("seconds")); ok = False
        if i.get("codec") not in ("avc1", "avc3"):
            print("  ⚠ المرمّز %s — الأوسع توافقاً H.264 (avc1)."
                  % i.get("codec", "?"))
        if not i.get("faststart"):
            print("  ⚠ البيانات الوصفيّة ليست في المقدّمة: البدء سيتأخّر.")
        if i.get("has_audio"):
            print("  ℹ فيه مسار صوت. سيُكتم في الصفحة (التشغيل التلقائي"
                  " يتطلّب الكتم)، لكن حذفه يوفّر حجماً.")
        if ok:
            print("  ✅ صالح للاستخدام كخلفيّة.")
        else:
            problems += 1

    print("=" * 72)
    print("%d ملف، %d بحاجة إلى معالجة." % (len(files), problems))
    print("\n⚠ لا ffmpeg في هذه البيئة، فلا يمكنني التحويل أو الضغط.")
    print("  إن ظهر تحذير، صدّر المقطع من برنامج التحرير بالمواصفات")
    print("  المكتوبة في media/video/README.md — أو ارفعه كما هو وسأبني")
    print("  الموقع ليستخدم صورة الغلاف على الاتصالات البطيئة.")
    return 0


# ----------------------------------------------------- استخراج الغلاف

def cmd_poster(src, outdir, at=1.0):
    """يستخرج إطاراً عبر المتصفّح: يُحمَّل الفيديو، يُنتقَل إلى ثانية،
    يُرسَم على canvas، ويُصدَّر JPEG + WebP."""
    chrome = None
    for c in ("chrome", "chromium", "google-chrome"):
        if subprocess.call(["which", c], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0:
            chrome = c
            break
    if not chrome:
        print("لا متصفّح متاح.")
        return 1

    os.makedirs(outdir, exist_ok=True)
    stem = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(
        os.path.basename(src))[0].lower()).strip("-")
    if not stem:          # اسم عربي بالكامل لا يُبقي حرفاً لاتينياً
        stem = "poster-%x" % (abs(hash(os.path.abspath(src))) % 0xffff)

    page = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<pre id="OUT">pending</pre>
<script>
var v = document.createElement('video');
v.muted = true; v.preload = 'auto'; v.src = 'v.mp4';
function fail(m){ document.getElementById('OUT').textContent = 'ERR:'+m; }
v.onerror = function(){ fail('load'); };
v.onloadeddata = function(){
  // تُقصّ على المدّة نفسها لا على نصفها — القصّ على النصف كان
  // يُرجع الإطار ذاته لكل طلب بعد المنتصف بلا أي تنبيه.
  var d = v.duration || 1;
  var t = Math.max(0, Math.min(%s, d - 0.05));
  v.currentTime = t;
};
v.onseeked = function(){
  try{
    var w = v.videoWidth, h = v.videoHeight;
    var cap = %d;
    if (Math.max(w,h) > cap){ var k = cap/Math.max(w,h); w = Math.round(w*k); h = Math.round(h*k); }
    var c = document.createElement('canvas');
    c.width = w; c.height = h;
    var x = c.getContext('2d');
    x.imageSmoothingQuality = 'high';
    x.drawImage(v, 0, 0, w, h);
    document.getElementById('OUT').textContent = JSON.stringify({
      w: w, h: h,
      jpg: c.toDataURL('image/jpeg', 0.84),
      webp: c.toDataURL('image/webp', 0.84)
    });
  } catch(e){ fail(String(e)); }
};
</script></body></html>""" % (at, min(MAX_EDGE, 1600))

    # يجب أن تُقدَّم الصفحة والفيديو عبر HTTP لا عبر file://
    # ---------------------------------------------------------------
    # على file:// يرفض Chrome تحميل الوسائط من مسار آخر (حتى مع
    # --allow-file-access-from-files) فلا يُطلق onloadeddata ولا
    # onerror، وتبقى الصفحة «pending» حتى تنتهي الميزانيّة الزمنيّة.
    # فيُقدَّم الملفّان من أصل http واحد باسم ثابت `v.mp4` — وهذا
    # يحلّ أيضاً أسماء الملفّات العربيّة وذات المسافات، فلا تحتاج
    # ترميزاً في العنوان.
    work = tempfile.mkdtemp(prefix="poster-")
    try:
        shutil.copy2(src, os.path.join(work, "v.mp4"))
        with open(os.path.join(work, "index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(page)

        with socket.socket() as probe_sock:          # منفذ حرّ
            probe_sock.bind(("127.0.0.1", 0))
            port = probe_sock.getsockname()[1]

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=work)
        handler.log_message = lambda *a, **k: None   # بلا ضجيج
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            res = subprocess.run(
                [chrome, "--headless", "--no-sandbox", "--disable-gpu",
                 "--autoplay-policy=no-user-gesture-required",
                 "--virtual-time-budget=30000", "--dump-dom",
                 "http://127.0.0.1:%d/index.html" % port],
                capture_output=True, text=True, timeout=120)
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    m = re.search(r'<pre id="OUT">(.*?)</pre>', res.stdout, re.S)
    if not m:
        print("فشل: لم يُرجع المتصفّح شيئاً.")
        return 1
    import html as H
    out = H.unescape(m.group(1)).strip()
    if out.startswith("ERR:") or out == "pending":
        print("فشل استخراج الإطار (%s)." % out)
        print("قد يكون المرمّز غير مدعوم في هذا المتصفّح — جرّب H.264.")
        return 1

    import json
    d = json.loads(out)
    for kind in ("jpg", "webp"):
        raw = base64.b64decode(d[kind].split(",", 1)[1])
        p = os.path.join(outdir, "%s-poster.%s" % (stem, kind))
        open(p, "wb").write(raw)
        print("  %s  %dx%d  %.0fKB" % (p, d["w"], d["h"], len(raw) / 1024))
    assert max(d["w"], d["h"]) <= MAX_EDGE
    print("  ✅ الغلاف ≤ %dpx — آمن للقراءة." % MAX_EDGE)
    return 0


# ----------------------------------------------------- ورقة المراجعة

SHEET_JS = """
var FILES = %s, COLS = %d, TW = %d, TH = %d, STAMPS = [0.12, 0.5, 0.88];
var c = document.createElement('canvas');
c.width = COLS * TW; c.height = STAMPS.length * TH;
var x = c.getContext('2d');
x.fillStyle = '#111'; x.fillRect(0, 0, c.width, c.height);
var out = document.getElementById('OUT');

function tile(v, col, row, name, failed) {
  var bx = col * TW, by = row * TH;
  var k = Math.min(TW / v.videoWidth, TH / v.videoHeight);
  var w = v.videoWidth * k, h = v.videoHeight * k;
  x.drawImage(v, bx + (TW - w) / 2, by + (TH - h) / 2, w, h);
  if (failed) {
    /* تُوسَم صراحةً: البلاطة السوداء بلا وسم تُقرأ «المقطع أسود»
       وهو حكم خاطئ على مادّة سليمة. */
    x.fillStyle = 'rgba(190,40,40,.92)';
    x.fillRect(bx, by + TH / 2 - 11, TW, 22);
    x.fillStyle = '#fff'; x.font = 'bold 12px monospace';
    x.textAlign = 'center';
    x.fillText('DECODE FAILED', bx + TW / 2, by + TH / 2 - 7);
    x.textAlign = 'start';
  }
  x.font = '11px monospace'; x.textBaseline = 'top';
  x.fillStyle = 'rgba(0,0,0,.7)'; x.fillRect(bx, by, TW, 14);
  x.fillStyle = '#fff'; x.fillText(name.slice(0, 30), bx + 3, by + 2);
}

/* هل البلاطة سوداء فعلاً؟ تُقاس الإضاءة لا تُفترض. */
function luma(v) {
  var c = document.createElement('canvas');
  c.width = 64; c.height = 64;
  var x = c.getContext('2d');
  try { x.drawImage(v, 0, 0, 64, 64); } catch (e) { return -1; }
  var p = x.getImageData(0, 0, 64, 64).data, s = 0;
  for (var i = 0; i < p.length; i += 4) s += p[i] + p[i + 1] + p[i + 2];
  return s / (p.length / 4) / 3;
}

/* الرسم بعد **عرض** الإطار لا بعد `seeked`
   ------------------------------------------------------------------
   `seeked` يُطلق حين يستقرّ موضع التشغيل، لا حين يُعرض الإطار
   الجديد. فالرسم عليه مباشرةً كان يُنتج بلاطات سوداء من مقاطع
   سليمة تماماً — ويُقرأ ذلك خطأً كأن المقطع أسود.
   `requestVideoFrameCallback` يُطلق عند عرض إطار فعلاً، ومعه
   احتياط إطارَي رسم للمتصفّحات التي لا تدعمه. */
function afterFrame(v, cb) {
  /* سباق لا اعتماد على واحد: `requestVideoFrameCallback` لا يُطلق
     في متصفّح بلا عتاد رسومي لفيديو متوقّف، فالاعتماد عليه وحده
     يُعلّق السلسلة. ومعه إطارا رسم ثم مهلة قصيرة — فأيّهما سبق
     يُسلّم، ولا يُسلّم مرّتين. */
  var fired = false;
  function go() { if (fired) return; fired = true; cb(); }
  if (v.requestVideoFrameCallback) {
    try { v.requestVideoFrameCallback(go); } catch (e) { /* يُتجاهل */ }
  }
  /* مؤقّت لا `requestAnimationFrame`: في المتصفّح بلا رأس لا شيء
     يُركَّب على الشاشة فلا يُطلق rAF أصلاً، والاعتماد عليه كان
     يُنتج ورقة فارغة تماماً. والمؤقّتات تتقدّم مع الميزانيّة
     الزمنيّة الافتراضيّة. */
  setTimeout(go, 140);
}

/* تسلسلياً: فكّ عدّة مقاطع معاً في متصفّح بلا عتاد رسومي يفشل. */
function one(i, done) {
  if (i >= FILES.length) return done();
  var v = document.createElement('video');
  v.muted = true; v.preload = 'auto'; v.playsInline = true;
  v.src = encodeURIComponent(FILES[i]);
  var si = 0, tries = 0;
  var dead = setTimeout(function () { next(); }, 20000);
  function next() { clearTimeout(dead); v.removeAttribute('src'); one(i + 1, done); }
  v.onerror = next;
  v.onloadeddata = function () { seek(); };
  function seek() {
    if (si >= STAMPS.length) return next();
    var d = v.duration || 1;
    var t = Math.max(0, Math.min(STAMPS[si] * d + tries * 0.22, d - 0.05));
    v.currentTime = t;
  }
  v.onseeked = function () {
    afterFrame(v, function () {
      /* سوداء تماماً مع وجود محتوى = فشل فكّ، لا مشهد أسود.
         فتُعاد المحاولة بإزاحة صغيرة قبل التسليم. */
      if (luma(v) < 1.2 && tries < 3) { tries++; return seek(); }
      try { tile(v, i, si, FILES[i], luma(v) < 1.2); } catch (e) {}
      si++; tries = 0; seek();
    });
  };
}
one(0, function () {
  out.textContent = JSON.stringify({ w: c.width, h: c.height,
                                     jpg: c.toDataURL('image/jpeg', 0.82) });
});
"""


def cmd_sheet(folder, outpath):
    """يبني صورة واحدة فيها ثلاث لحظات من كل مقطع — لمراجعة
    المحتوى والحقوق (علامات مائيّة، شعارات جهات أخرى) بنظرة واحدة
    بدل استخراج غلاف لكل ملف على حدة."""
    chrome = None
    for c in ("chrome", "chromium", "google-chrome"):
        if subprocess.call(["which", c], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0:
            chrome = c
            break
    if not chrome:
        print("لا متصفّح متاح.")
        return 1

    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".mp4"))
    if not files:
        print("لا ملفّات mp4 في %s" % folder)
        return 1

    # تُحسب أبعاد البلاطة لتبقى الورقة كلها تحت حدّ قراءة الصور
    tw = max(120, min(320, (MAX_EDGE - 100) // len(files)))
    th = int(tw * 1.78)
    if 3 * th > MAX_EDGE - 40:
        th = (MAX_EDGE - 40) // 3
        tw = min(tw, int(th / 1.78))

    work = tempfile.mkdtemp(prefix="sheet-")
    try:
        for f in files:
            shutil.copy2(os.path.join(folder, f), os.path.join(work, f))
        import json as J
        with open(os.path.join(work, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<!DOCTYPE html><meta charset="utf-8">'
                     '<pre id="OUT">pending</pre><script>%s</script>'
                     % (SHEET_JS % (J.dumps(files), len(files), tw, th)))

        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=work)
        handler.log_message = lambda *a, **k: None
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            res = subprocess.run(
                [chrome, "--headless", "--no-sandbox", "--disable-gpu",
                 "--autoplay-policy=no-user-gesture-required",
                 "--virtual-time-budget=%d" % (26000 * len(files)),
                 "--dump-dom", "http://127.0.0.1:%d/index.html" % port],
                capture_output=True, text=True, timeout=90 * len(files) + 180)
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    m = re.search(r'<pre id="OUT">(.*?)</pre>', res.stdout, re.S)
    if not m or m.group(1).strip() in ("pending", ""):
        print("فشل بناء الورقة.")
        return 1
    import html as H
    import json as J
    d = J.loads(H.unescape(m.group(1)).strip())
    raw = base64.b64decode(d["jpg"].split(",", 1)[1])
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)
    open(outpath, "wb").write(raw)
    print("  %s  %dx%d  %.0fKB  (%d مقطع × ٣ لحظات)"
          % (outpath, d["w"], d["h"], len(raw) / 1024, len(files)))
    if max(d["w"], d["h"]) > MAX_EDGE:
        print("  ⚠ الورقة تجاوزت %dpx — غير آمنة للقراءة." % MAX_EDGE)
        return 1
    print("  ✅ ≤ %dpx — آمنة للقراءة." % MAX_EDGE)
    print("  راجعها بحثاً عن: علامة مائيّة، شعار جهة أخرى، نصّ محروق،"
          " وجوه أشخاص حقيقيّين.")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == "probe":
        return cmd_probe(sys.argv[2:] or ["media/video"])
    if sys.argv[1] == "sheet":
        folder = sys.argv[2] if len(sys.argv) > 2 else "media/video"
        out = sys.argv[3] if len(sys.argv) > 3 else "docs/evidence/sheet.jpg"
        return cmd_sheet(folder, out)
    if sys.argv[1] == "poster":
        src = sys.argv[2]
        out = sys.argv[3] if len(sys.argv) > 3 else "assets/img/video"
        at = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        return cmd_poster(src, out, at)
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
