"""
bg_music.py - موسيقى خلفية بأيقونة سماعة عائمة وقابلة للسحب لتطبيقات Streamlit.

الاستخدام في streamlit_app.py (بعد st.set_page_config مباشرة):

    from bg_music import add_background_music

    add_background_music(
        "https://soundcloud.com/ARTIST/TRACK",  # الرابط الكامل للأغنية
        position="bottom",   # مكان البداية: "bottom" أو "top"
        side="left",         # مكان البداية: "left" أو "right"
        volume=30,           # مستوى الصوت الافتراضي 0-100
        offset=96,           # المسافة من الحافة في البداية (بكسل)
    )

المصدر (track_url) يمكن أن يكون:
- رابط SoundCloud الكامل:  https://soundcloud.com/ARTIST/TRACK
- رابط مباشر لملف صوتي:    https://example.com/music.mp3
- ملف محلي داخل المشروع:   "assets/music.mp3"  (يُفضّل أقل من 5 ميجا)

التحكم:
- اسحب أيقونة السماعة وحرّكها لأي مكان في الشاشة (يُحفظ مكانها في المتصفح).
- مرّر الماوس عليها فيظهر شريط مستوى الصوت.
- اضغط عليها (بدون سحب) لكتم الصوت / إلغاء الكتم.
- أول ضغطة في الصفحة (حتى على الأيقونة) تبدأ التشغيل فقط، فالمتصفحات تمنع التشغيل التلقائي.
- لو فشل التشغيل تظهر نافذة صغيرة بالسبب مع مشغّل SoundCloud الأصلي لتجربته يدويًا.
"""

import base64
import json
import mimetypes
from pathlib import Path

import streamlit.components.v1 as components

_HTML = r"""
<script>
function main(CFG) {
  var P = window, D = document;
  var oldWrap = D.getElementById('lexa-music');
  if (oldWrap) oldWrap.remove();
  var oldStyle = D.getElementById('lexa-music-style');
  if (oldStyle) oldStyle.remove();
  var oldAudio = D.getElementById('lexa-audio');
  if (oldAudio) { try { oldAudio.pause(); } catch (e) {} oldAudio.remove(); }
  var oldFrame = D.getElementById('lexa-sc-frame');
  if (oldFrame) oldFrame.remove();

  var BOX = 50, MARGIN = 8;

  function load(k, d) {
    try { var v = P.localStorage.getItem(k); return v === null ? d : v; }
    catch (e) { return d; }
  }
  function save(k, v) { try { P.localStorage.setItem(k, v); } catch (e) {} }
  function log() {
    try { console.log.apply(console, ['[lexa-music]'].concat([].slice.call(arguments))); } catch (e) {}
  }
  function vw() { return P.innerWidth || D.documentElement.clientWidth || 1024; }
  function vh() { return P.innerHeight || D.documentElement.clientHeight || 768; }

  // يبدأ الصوت دائمًا بالمستوى الافتراضي المحدد من التطبيق (30%) عند تحميل الصفحة.
  // يمكن للمستخدم تغيير المستوى أثناء الجلسة من شريط الصوت.
  var vol = Math.max(0, Math.min(100, Number(CFG.volume) || 30));
  save('lexa_music_vol', vol);
  var muted = false;
  try { P.localStorage.removeItem('lexa_music_muted'); } catch (e) {}

  var player = null, ready = false, wantPlay = false, playing = false, playTimer = null;
  var px = 0, py = 0, cur = null;
  var autoShown = false, suppressClick = false, firstIconStart = false;

  // ---------- الستايل ----------
  var style = D.createElement('style');
  style.id = 'lexa-music-style';
  style.textContent = `
    #lexa-music{position:fixed;z-index:999999;display:flex;align-items:center;direction:ltr;box-sizing:border-box;
      height:50px;min-width:50px;background:rgba(33,20,15,.88);color:#f8fafc;border-radius:999px;padding:4px;
      border:1px solid rgba(212,175,55,.38);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
      box-shadow:0 6px 18px rgba(0,0,0,.35);font-family:system-ui,sans-serif;
      -webkit-user-select:none;user-select:none}
    #lexa-music.flip{flex-direction:row-reverse}
    #lexa-music .lm-btn{width:40px;height:40px;flex:0 0 40px;border:0;border-radius:50%;background:transparent;
      color:inherit;cursor:grab;display:flex;align-items:center;justify-content:center;padding:0;touch-action:none}
    #lexa-music .lm-btn{animation:lexa-music-glow 3.2s ease-in-out infinite}
    @keyframes lexa-music-glow{
      0%,100%{background:rgba(232,199,102,0);box-shadow:0 0 0 0 rgba(232,199,102,0)}
      50%{background:rgba(232,199,102,.10);box-shadow:0 0 12px 2px rgba(212,175,55,.20)}
    }
    #lexa-music .lm-btn:hover{background:rgba(232,199,102,.18);box-shadow:0 0 14px 3px rgba(212,175,55,.28)}
    #lexa-music.dragging,#lexa-music.dragging .lm-btn{cursor:grabbing}
    #lexa-music.dragging .lm-btn{animation:none}
    @media (prefers-reduced-motion: reduce){#lexa-music .lm-btn{animation:none}}
    #lexa-music .lm-panel{display:flex;align-items:center;gap:8px;max-width:0;opacity:0;
      overflow:hidden;white-space:nowrap}
    #lexa-music:hover:not(.dragging) .lm-panel,#lexa-music:focus-within:not(.dragging) .lm-panel{max-width:190px;opacity:1;padding:0 10px}
    #lexa-music .lm-range{width:100px;accent-color:#e8c766;cursor:pointer}
    #lexa-music .lm-val{font-size:12px;width:36px;text-align:center;font-variant-numeric:tabular-nums}
    #lexa-music .lm-slash{display:none;stroke:#ff6b6b}
    #lexa-music.muted .lm-slash{display:block}
    #lexa-music.muted .lm-btn{opacity:.8}
    #lexa-music.error{border-color:#ffb347}
    #lexa-music.error .lm-btn{color:#ffb347}
    #lexa-music .lm-pop{position:absolute;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;
      direction:rtl;border-radius:14px;background:#21140f;color:#ffcf8a;font-size:12px;line-height:1.6}
    #lexa-music[data-v="up"] .lm-pop{bottom:calc(100% + 10px)}
    #lexa-music[data-v="down"] .lm-pop{top:calc(100% + 10px)}
    #lexa-music[data-h="l"] .lm-pop{left:0}
    #lexa-music[data-h="r"] .lm-pop{right:0}
    #lexa-music .lm-pop.show{width:300px;max-width:calc(100vw - 24px);height:auto;opacity:1;pointer-events:auto;
      border:1px solid rgba(212,175,55,.38);box-shadow:0 10px 28px rgba(0,0,0,.45)}
    #lexa-music .lm-pop-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;padding:8px 10px}
    #lexa-music .lm-pop-x{border:0;background:transparent;color:#f8fafc;cursor:pointer;font-size:14px;padding:0 2px}
    #lexa-music .lm-pop-body{width:100%;height:120px}
    #lexa-music .lm-pop.noframe .lm-pop-body{display:none}
    #lexa-music .lm-pop-body iframe{width:100%;height:100%;border:0}
  `;
  D.head.appendChild(style);

  // إخفاء حاوية المكوّن الفارغة حتى لا تضيف مسافة في الصفحة
  var gap = D.createElement('style');
  gap.textContent = '[data-testid="stElementContainer"]:has(iframe[height="0"]){position:absolute;height:0;margin:0;overflow:hidden}';
  D.head.appendChild(gap);

  // ---------- العناصر ----------
  var wrap = D.createElement('div');
  wrap.id = 'lexa-music';
  wrap.innerHTML =
    '<button class="lm-btn" type="button" aria-label="Music">' +
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="pointer-events:none">' +
      '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>' +
      '<line class="lm-slash" x1="3" y1="3" x2="21" y2="21"/>' +
      '</svg></button>' +
    '<div class="lm-panel">' +
      '<input class="lm-range" type="range" min="0" max="100" step="1" aria-label="Volume">' +
      '<span class="lm-val"></span>' +
    '</div>' +
    '<div class="lm-pop' + (CFG.mode === 'audio' ? ' noframe' : '') + '">' +
      '<div class="lm-pop-head"><span class="lm-pop-msg"></span>' +
      '<button class="lm-pop-x" type="button" aria-label="Close">✕</button></div>' +
      '<div class="lm-pop-body"></div>' +
    '</div>';
  D.body.appendChild(wrap);

  var btn = wrap.querySelector('.lm-btn');
  var range = wrap.querySelector('.lm-range');
  var val = wrap.querySelector('.lm-val');
  var pop = wrap.querySelector('.lm-pop');
  var popMsg = wrap.querySelector('.lm-pop-msg');
  var popBody = wrap.querySelector('.lm-pop-body');

  // ---------- الموضع (قابل للسحب) ----------
  function place(x, y) {
    var W = vw(), H = vh();
    x = Math.min(Math.max(x, MARGIN), Math.max(MARGIN, W - BOX - MARGIN));
    y = Math.min(Math.max(y, MARGIN), Math.max(MARGIN, H - BOX - MARGIN));
    px = x; py = y;
    var rightHalf = (x + BOX / 2) > W / 2;
    wrap.classList.toggle('flip', rightHalf);
    wrap.setAttribute('data-h', rightHalf ? 'r' : 'l');
    wrap.setAttribute('data-v', (y + BOX / 2) > H / 2 ? 'up' : 'down');
    if (rightHalf) { wrap.style.left = 'auto'; wrap.style.right = (W - x - BOX) + 'px'; }
    else { wrap.style.right = 'auto'; wrap.style.left = x + 'px'; }
    wrap.style.top = y + 'px';
    wrap.style.bottom = 'auto';
  }
  function toRatios() {
    return {
      x: (px - MARGIN) / Math.max(1, vw() - BOX - 2 * MARGIN),
      y: (py - MARGIN) / Math.max(1, vh() - BOX - 2 * MARGIN)
    };
  }
  function fromRatios(r) {
    return {
      x: MARGIN + r.x * (vw() - BOX - 2 * MARGIN),
      y: MARGIN + r.y * (vh() - BOX - 2 * MARGIN)
    };
  }

  var saved = null;
  try { saved = JSON.parse(load('lexa_music_pos', 'null')); } catch (e) {}
  if (saved && typeof saved.x === 'number' && typeof saved.y === 'number') {
    var p0 = fromRatios(saved);
    place(p0.x, p0.y);
    cur = saved;
  } else {
    place(CFG.side === 'left' ? 16 : vw() - BOX - 16,
          CFG.position === 'top' ? CFG.offset : vh() - BOX - CFG.offset);
    cur = toRatios();
  }
  P.addEventListener('resize', function () {
    var p = fromRatios(cur);
    place(p.x, p.y);
  });

  var drag = null, moved = false;
  btn.addEventListener('pointerdown', function (e) {
    if (e.button > 0) return;
    drag = { sx: e.clientX, sy: e.clientY, ox: px, oy: py };
    moved = false;
    try { btn.setPointerCapture(e.pointerId); } catch (err) {}
  });
  btn.addEventListener('pointermove', function (e) {
    if (!drag) return;
    var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
    if (!moved && Math.abs(dx) + Math.abs(dy) < 6) return;
    moved = true;
    wrap.classList.add('dragging');
    place(drag.ox + dx, drag.oy + dy);
  });
  function endDrag() {
    if (!drag) return;
    drag = null;
    wrap.classList.remove('dragging');
    if (moved) {
      cur = toRatios();
      save('lexa_music_pos', JSON.stringify(cur));
      suppressClick = true;
      setTimeout(function () { suppressClick = false; }, 60);
    }
  }
  btn.addEventListener('pointerup', endDrag);
  btn.addEventListener('pointercancel', endDrag);

  // ---------- الصوت والحالة ----------
  function apply() {
    var effective = muted ? 0 : vol;
    range.value = effective;
    val.textContent = effective + '%';
    wrap.classList.toggle('muted', effective === 0);
    if (!wrap.classList.contains('error')) {
      btn.title = (muted ? 'إلغاء الكتم' : 'كتم') + ' · اسحب لتحريك الأيقونة';
    }
    if (player && ready) player.setVolume(effective);
  }
  function showPop(msg) {
    popMsg.textContent = msg || '';
    pop.classList.add('show');
    autoShown = true;
  }
  wrap.querySelector('.lm-pop-x').addEventListener('click', function () {
    pop.classList.remove('show');
    autoShown = false;
  });
  function fail(msg) {
    wrap.classList.add('error');
    btn.title = msg;
    showPop(msg);
    log('PROBLEM:', msg);
  }
  function onPlaying() {
    playing = true;
    clearTimeout(playTimer);
    wrap.classList.remove('error');
    if (autoShown) { pop.classList.remove('show'); autoShown = false; }
    log('playing');
    apply();
  }
  function tryPlay() {
    if (!player) return;
    log('play() requested');
    player.play();
    clearTimeout(playTimer);
    playTimer = setTimeout(function () {
      if (!playing) fail('لم يبدأ التشغيل: ربما المقطع غير قابل للتضمين خارج SoundCloud، أو الرابط غير صحيح، أو المتصفح منع الصوت.');
    }, 6000);
  }

  range.addEventListener('input', function () {
    var v = Number(range.value);
    if (v > 0) { vol = v; muted = false; save('lexa_music_vol', vol); } else { muted = true; }
    apply();
  });

  btn.addEventListener('click', function () {
    if (suppressClick) return; // كان سحبًا وليس ضغطة

    // قبل بدء الموسيقى، كل ضغطة تطلب التشغيل ولا تكتم الصوت.
    wantPlay = true;
    if (!playing) {
      muted = false;
      if (vol < 5) vol = CFG.volume;
      save('lexa_music_vol', vol);
      apply();

      if (ready) {
        tryPlay(); // داخل حدث click مباشرةً لتوافق قيود المتصفح
      } else {
        showPop('المشغل لسه بيحمّل. انتظر لحظات ثم اضغط على السماعة مرة أخرى.');
        log('play requested before player ready');
      }
      firstIconStart = false;
      return;
    }

    // بعد بدء الموسيقى فقط، تتحول الضغطة إلى كتم / إلغاء كتم.
    muted = !muted;
    if (!muted && vol < 5) vol = CFG.volume;
    save('lexa_music_vol', vol);
    apply();
  });

  // ---------- المشغّل ----------
  function initAudio() {
    var a = D.createElement('audio');
    a.id = 'lexa-audio';
    a.loop = true;
    a.preload = 'auto';
    a.style.display = 'none';
    a.src = CFG.src;
    D.body.appendChild(a);
    a.addEventListener('playing', onPlaying);
    a.addEventListener('error', function () { fail('تعذر تحميل ملف الصوت - تأكد من الرابط أو المسار.'); });
    player = {
      play: function () {
        var p = a.play();
        if (p && p.catch) p.catch(function (e) { fail('المتصفح منع التشغيل: ' + (e && e.name)); });
      },
      setVolume: function (v) { a.volume = v / 100; }
    };
    ready = true;
    apply();
    if (wantPlay && !playing) {
      showPop('المشغل جاهز. اضغط على السماعة لبدء الموسيقى.');
    }
  }

  function initSoundCloud() {
    if (CFG.src.indexOf('on.soundcloud.com') !== -1) {
      log('تحذير: الرابط القصير قد لا يعمل مع المشغّل، استخدم الرابط الكامل soundcloud.com/artist/track');
    }
    var frame = D.createElement('iframe');
    frame.id = 'lexa-sc-frame';
    frame.allow = 'autoplay; encrypted-media';
    frame.src = 'https://w.soundcloud.com/player/?url=' + encodeURIComponent(CFG.src) +
      '&auto_play=false&hide_related=true&show_comments=false&show_user=false' +
      '&show_reposts=false&show_teaser=false&visual=false';
    popBody.appendChild(frame);

    function init() {
      var w = P.SC.Widget(frame);
      var readyTimer = setTimeout(function () {
        if (!ready) fail('تعذر تحميل المقطع من SoundCloud. استخدم الرابط الكامل وتأكد أن المقطع يسمح بالتضمين.');
      }, 10000);
      w.bind(P.SC.Widget.Events.READY, function () {
        clearTimeout(readyTimer);
        player = {
          play: function () { w.play(); },
          setVolume: function (v) { w.setVolume(v); }
        };
        ready = true;
        log('soundcloud widget ready');
        apply();
        // لا نبدأ التشغيل تلقائيًا من READY؛ بعض المتصفحات تعتبره خارج
        // تفاعل المستخدم. اطلب من المستخدم الضغط مرة أخرى بعد اكتمال التحميل.
        if (wantPlay && !playing) {
          showPop('المشغل جاهز. اضغط على السماعة لبدء الموسيقى.');
        }
      });
      w.bind(P.SC.Widget.Events.PLAY, onPlaying);
      w.bind(P.SC.Widget.Events.ERROR, function (event) {
        log('SoundCloud widget error:', event || '(no details)');
        fail('SoundCloud رفض تشغيل المقطع. جرّب فتحه من مشغّل SoundCloud الظاهر هنا، أو استخدم رابط مقطع يسمح بالتضمين.');
      });
      w.bind(P.SC.Widget.Events.FINISH, function () { playing = false; w.seekTo(0); w.play(); });
    }

    if (P.SC && P.SC.Widget) {
      init();
    } else {
      var s = D.createElement('script');
      s.src = 'https://w.soundcloud.com/player/api.js';
      s.onload = init;
      s.onerror = function () { fail('تعذر تحميل مكتبة SoundCloud (قد يكون الاتصال محظورًا).'); };
      D.head.appendChild(s);
    }
  }

  if (CFG.mode === 'audio') initAudio(); else initSoundCloud();

  // ---------- التشغيل عند أول تفاعل (قيود المتصفح) ----------
  function start(ev) {
    if (wantPlay) return;
    wantPlay = true;
    if (ev && ev.target && wrap.contains(ev.target)) firstIconStart = true;
    if (ready) tryPlay();
  }
  ['pointerdown', 'keydown'].forEach(function (ev) {
    D.addEventListener(ev, start, { capture: true, once: true });
  });

  apply();
}

(function () {
  var pdoc = window.parent.document;
  var s = pdoc.createElement('script');
  // نشغّل الكود داخل الصفحة الأم حتى يبقى شغالًا بعد إعادة تحميل مكوّن Streamlit
  s.textContent = '(' + main.toString() + ')(' + JSON.stringify(__CFG__) + ');';
  pdoc.head.appendChild(s);
})();
</script>
"""


def _resolve_source(track):
    """يحدد نوع المصدر: SoundCloud أو ملف صوتي (رابط مباشر / ملف محلي)."""
    t = str(track).strip()
    if not t:
        raise ValueError("track_url is empty")
    if t.lower().startswith(("http://", "https://")):
        return ("soundcloud" if "soundcloud.com" in t.lower() else "audio"), t
    path = Path(t)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / t
    if not path.is_file():
        raise FileNotFoundError(f"audio file not found: {path}")
    if path.stat().st_size > 15 * 1024 * 1024:
        raise ValueError("audio file is larger than 15MB; use a smaller file or a direct URL")
    mime = mimetypes.guess_type(path.name)[0] or "audio/mpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return "audio", f"data:{mime};base64,{data}"


def add_background_music(track_url, position="bottom", side="left", volume=30, offset=96):
    """يضيف أيقونة سماعة عائمة تشغّل موسيقى في الخلفية."""
    if position not in ("top", "bottom"):
        raise ValueError("position must be 'top' or 'bottom'")
    if side not in ("left", "right"):
        raise ValueError("side must be 'left' or 'right'")

    mode, src = _resolve_source(track_url)
    cfg = json.dumps(
        {
            "mode": mode,
            "src": src,
            "position": position,
            "side": side,
            "volume": max(0, min(100, int(volume))),
            "offset": max(0, int(offset)),
        }
    ).replace("</", "<\\/")

    components.html(_HTML.replace("__CFG__", cfg), height=0)
