"""
bg_music.py - موسيقى خلفية بأيقونة سماعة عائمة لتطبيقات Streamlit.

الاستخدام في streamlit_app.py (بعد st.set_page_config مباشرة):

    from bg_music import add_background_music

    add_background_music(
        "https://soundcloud.com/ARTIST/TRACK",  # الرابط الكامل للأغنية
        position="bottom",   # "bottom" أو "top"
        side="left",         # "left" أو "right"
        volume=30,           # مستوى الصوت الافتراضي 0-100
        offset=96,           # المسافة من الحافة بالبكسل (96 تتجنب شريط الكتابة)
    )

التحكم:
- مرّر الماوس على أيقونة السماعة فيظهر شريط مستوى الصوت.
- اضغط على السماعة لكتم الصوت / إلغاء الكتم.
- يتم حفظ مستوى الصوت وحالة الكتم في المتصفح.
- المتصفحات تمنع التشغيل التلقائي، فتبدأ الموسيقى عند أول ضغطة أو لمسة في الصفحة.
"""

import json

import streamlit.components.v1 as components

_HTML = r"""
<script>
function main(CFG) {
  var P = window, D = document;
  if (D.getElementById('lexa-music')) return;

  function load(k, d) {
    try { var v = P.localStorage.getItem(k); return v === null ? d : v; }
    catch (e) { return d; }
  }
  function save(k, v) { try { P.localStorage.setItem(k, v); } catch (e) {} }

  var vol = Math.min(100, Math.max(0, Number(load('lexa_music_vol', CFG.volume))));
  var muted = load('lexa_music_muted', '0') === '1';
  var widget = null, ready = false, wantPlay = false;

  // ---------- الستايل ----------
  var style = D.createElement('style');
  style.id = 'lexa-music-style';
  style.textContent = `
    #lexa-music{position:fixed;z-index:999999;display:flex;align-items:center;direction:ltr;
      background:rgba(33,20,15,.88);color:#f8fafc;border-radius:999px;padding:4px;
      border:1px solid rgba(212,175,55,.38);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
      box-shadow:0 6px 18px rgba(0,0,0,.35);font-family:system-ui,sans-serif}
    #lexa-music .lm-btn{width:40px;height:40px;border:0;border-radius:50%;background:transparent;
      color:inherit;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0}
    #lexa-music .lm-btn:hover{background:rgba(232,199,102,.18)}
    #lexa-music .lm-panel{display:flex;align-items:center;gap:8px;max-width:0;opacity:0;
      overflow:hidden;white-space:nowrap;transition:max-width .25s,opacity .25s,padding .25s}
    #lexa-music:hover .lm-panel,#lexa-music:focus-within .lm-panel{max-width:190px;opacity:1;padding:0 10px}
    #lexa-music .lm-range{width:100px;accent-color:#e8c766;cursor:pointer}
    #lexa-music .lm-val{font-size:12px;width:36px;text-align:center;font-variant-numeric:tabular-nums}
    #lexa-music .lm-slash{display:none;stroke:#ff6b6b}
    #lexa-music.muted .lm-slash{display:block}
    #lexa-music.muted .lm-btn{opacity:.8}
  `;
  D.head.appendChild(style);

  // إخفاء حاوية المكوّن الفارغة حتى لا تضيف مسافة في الصفحة
  var gap = D.createElement('style');
  gap.textContent = '[data-testid="stElementContainer"]:has(iframe[height="0"]){position:absolute;height:0;margin:0;overflow:hidden}';
  D.head.appendChild(gap);

  // ---------- العناصر ----------
  var wrap = D.createElement('div');
  wrap.id = 'lexa-music';
  wrap.style[CFG.position] = CFG.offset + 'px';
  wrap.style[CFG.side] = '16px';
  if (CFG.side === 'right') wrap.style.flexDirection = 'row-reverse';
  wrap.innerHTML =
    '<button class="lm-btn" type="button" aria-label="Music volume">' +
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>' +
      '<line class="lm-slash" x1="3" y1="3" x2="21" y2="21"/>' +
      '</svg></button>' +
    '<div class="lm-panel">' +
      '<input class="lm-range" type="range" min="0" max="100" step="1" aria-label="Volume">' +
      '<span class="lm-val"></span>' +
    '</div>';
  D.body.appendChild(wrap);

  var btn = wrap.querySelector('.lm-btn');
  var range = wrap.querySelector('.lm-range');
  var val = wrap.querySelector('.lm-val');

  function apply() {
    var effective = muted ? 0 : vol;
    range.value = effective;
    val.textContent = effective + '%';
    wrap.classList.toggle('muted', effective === 0);
    btn.title = muted ? 'Unmute' : 'Mute';
    if (widget && ready) widget.setVolume(effective);
  }

  range.addEventListener('input', function () {
    var v = Number(range.value);
    if (v > 0) { vol = v; muted = false; } else { muted = true; }
    save('lexa_music_vol', vol);
    save('lexa_music_muted', muted ? '1' : '0');
    apply();
  });

  btn.addEventListener('click', function () {
    muted = !muted;
    if (!muted && vol === 0) vol = 30;
    save('lexa_music_vol', vol);
    save('lexa_music_muted', muted ? '1' : '0');
    apply();
  });

  // ---------- مشغّل SoundCloud (مخفي) ----------
  var frame = D.createElement('iframe');
  frame.id = 'lexa-sc-frame';
  frame.allow = 'autoplay';
  frame.tabIndex = -1;
  frame.setAttribute('aria-hidden', 'true');
  frame.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;border:0;opacity:0;pointer-events:none';
  frame.src = 'https://w.soundcloud.com/player/?url=' + encodeURIComponent(CFG.track) +
    '&auto_play=false&hide_related=true&show_comments=false&show_user=false' +
    '&show_reposts=false&show_teaser=false&visual=false';
  D.body.appendChild(frame);

  function init() {
    widget = P.SC.Widget(frame);
    widget.bind(P.SC.Widget.Events.READY, function () {
      ready = true;
      apply();
      if (wantPlay) widget.play();
    });
    widget.bind(P.SC.Widget.Events.PLAY, apply);
    widget.bind(P.SC.Widget.Events.FINISH, function () { widget.seekTo(0); widget.play(); });
  }

  if (P.SC && P.SC.Widget) {
    init();
  } else {
    var s = D.createElement('script');
    s.src = 'https://w.soundcloud.com/player/api.js';
    s.onload = init;
    D.head.appendChild(s);
  }

  // ---------- التشغيل عند أول تفاعل (قيود المتصفح) ----------
  function start() {
    if (wantPlay) return;
    wantPlay = true;
    if (ready) widget.play();
  }
  ['pointerdown', 'keydown'].forEach(function (ev) {
    D.addEventListener(ev, start, { capture: true, once: true });
  });

  apply();
}

(function () {
  var pdoc = window.parent.document;
  if (pdoc.getElementById('lexa-music')) return;
  var s = pdoc.createElement('script');
  // نشغّل الكود داخل الصفحة الأم حتى يبقى شغالًا بعد إعادة تحميل مكوّن Streamlit
  s.textContent = '(' + main.toString() + ')(' + JSON.stringify(__CFG__) + ');';
  pdoc.head.appendChild(s);
})();
</script>
"""


def add_background_music(track_url, position="bottom", side="left", volume=30, offset=96):
    """يضيف أيقونة سماعة عائمة تشغّل مقطع SoundCloud في الخلفية."""
    if position not in ("top", "bottom"):
        raise ValueError("position must be 'top' or 'bottom'")
    if side not in ("left", "right"):
        raise ValueError("side must be 'left' or 'right'")

    cfg = json.dumps(
        {
            "track": track_url,
            "position": position,
            "side": side,
            "volume": max(0, min(100, int(volume))),
            "offset": max(0, int(offset)),
        }
    ).replace("</", "<\\/")

    components.html(_HTML.replace("__CFG__", cfg), height=0)
