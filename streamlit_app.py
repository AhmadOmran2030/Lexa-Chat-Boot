from __future__ import annotations

import json
import hmac
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Ensure local project modules are resolved from the app root on Streamlit Cloud.
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
try:
    st.set_option("server.fileWatcherType", "none")
except Exception:
    pass

from ingestion import ingest_file, load_all
from persistence import configured as storage_configured, load_rows as load_remote_rows, save_document, summarize_laws
from rag_engine import LegalIndex, query_filters

load_dotenv()
BASE = APP_ROOT
DATA_DIR = BASE / "data"
PARSED_DIR = BASE / "parsed_laws"
DATA_DIR.mkdir(exist_ok=True)
PARSED_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="LexGO | المستشار القانوني", page_icon="⚖️", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { direction: rtl; text-align: right; font-family: 'IBM Plex Sans Arabic', 'Cairo', sans-serif; }
[data-testid="stSidebar"] { direction: rtl; background: linear-gradient(180deg,#21140f 0%,#2f1d14 100%); border-left: 1px solid rgba(212,175,55,.18); }
[data-testid="stSidebar"] .block-container { padding-top: 2rem; }
.stApp { background: radial-gradient(circle at 85% 5%, rgba(180,130,40,.16), transparent 28%), radial-gradient(circle at 10% 80%, rgba(104,54,28,.22), transparent 30%), #170e0a; }
.main .block-container { max-width: 1180px; padding: 2.5rem 2rem 5rem; }
.brand-mark { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.brand-icon { width:44px; height:44px; display:grid; place-items:center; border-radius:14px; background:linear-gradient(135deg,#f4d06f,#a87519); color:#2b180b; font-size:24px; box-shadow:0 10px 28px rgba(212,175,55,.22); }
.brand-name { font-family:'Cairo',sans-serif; font-size:1.45rem; font-weight:800; color:#f8fafc; letter-spacing:-.5px; }
.brand-sub { color:#e6c56a; font-size:.78rem; margin:0 0 1.2rem 56px; }
.hero { padding:2rem 2.2rem; border:1px solid rgba(212,175,55,.24); border-radius:24px; background:linear-gradient(135deg,rgba(75,43,24,.94),rgba(34,20,14,.94)); box-shadow:0 18px 50px rgba(0,0,0,.28); margin-bottom:1.5rem; }
.hero-kicker { color:#e8c766; font-weight:700; font-size:.82rem; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:.5rem; }
.hero h1 { color:#f8fafc; font-family:'Cairo',sans-serif; font-size:2.45rem; line-height:1.35; margin:0 0 .55rem; }
.hero p { color:#e8dcca; font-size:1.02rem; margin:0; max-width:720px; }
.metric-card { padding:1rem 1.1rem; border-radius:16px; border:1px solid rgba(212,175,55,.16); background:rgba(55,31,19,.78); }
.metric-label { color:#cbb998; font-size:.8rem; }
.metric-value { color:#f8fafc; font-size:1.55rem; font-weight:800; margin-top:.2rem; }
.law-card { padding:1.1rem 1.25rem; border:1px solid rgba(212,175,55,.18); border-radius:16px; margin-bottom:.8rem; background:linear-gradient(135deg,rgba(66,37,21,.86),rgba(34,20,14,.92)); }
.source-chip { display:inline-block; padding:.3rem .65rem; margin:.15rem; border-radius:999px; background:rgba(212,175,55,.12); color:#f2d47c; font-size:.76rem; border:1px solid rgba(212,175,55,.22); }
.section-title { color:#e2e8f0; font-family:'Cairo',sans-serif; font-size:1.25rem; font-weight:700; margin:.7rem 0 1rem; }
div[data-testid="stFileUploader"] { border:1px dashed rgba(212,175,55,.5); border-radius:16px; padding:.4rem; background:rgba(91,49,22,.24); }
button[kind="primary"] { background:linear-gradient(135deg,#d4af37,#8f6517); border:0; color:#21140d; }
[data-testid="stChatMessage"] { border:1px solid rgba(212,175,55,.12); border-radius:18px; background:rgba(53,29,17,.55); margin-bottom:1rem; }
[data-testid="stChatMessage"] p { line-height:2; }
[data-testid="stChatInput"] { border-color:rgba(212,175,55,.45) !important; background:#2b190f !important; }
[data-testid="stChatInput"] textarea { color:#fff7e6 !important; }
</style>""", unsafe_allow_html=True)


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _users() -> list[dict]:
    raw = _secret("USERS_JSON")
    if raw:
        try:
            users = json.loads(raw)
            if isinstance(users, list):
                return users
        except json.JSONDecodeError:
            pass
    admin_user = _secret("ADMIN_USERNAME")
    admin_password = _secret("ADMIN_PASSWORD")
    if admin_user and admin_password:
        return [{"username": admin_user, "password": admin_password, "role": "admin"}]
    return []


def authenticate(username: str, password: str) -> dict | None:
    for user in _users():
        if hmac.compare_digest(str(user.get("username", "")), username) and hmac.compare_digest(str(user.get("password", "")), password):
            return {"username": username, "role": user.get("role", "user")}
    return None


if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

configured_users = _users()
if configured_users and not st.session_state.auth_user:
    st.markdown('<div class="hero"><div class="hero-kicker">LEXGO SECURE ACCESS</div><h1>تسجيل الدخول إلى المستشار القانوني</h1><p>سجّل الدخول للوصول إلى مكتبة القوانين. صلاحية إضافة الملفات متاحة للمدير فقط.</p></div>', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول", type="primary", use_container_width=True)
        if submitted:
            user = authenticate(username.strip(), password)
            if user:
                st.session_state.auth_user = user
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
    st.stop()

current_user = st.session_state.auth_user or {"username": "guest", "role": "user"}
is_admin = current_user.get("role") == "admin"

@st.cache_data(show_spinner=False)
def load_corpus():
    local_laws, local_rows = load_all(DATA_DIR, PARSED_DIR)
    if storage_configured():
        try:
            remote_rows = load_remote_rows()
            if remote_rows:
                return summarize_laws(remote_rows), remote_rows
            for law in local_laws:
                document_id = law.get("document_id")
                if document_id and not law.get("error"):
                    law_rows = [row for row in local_rows if row.get("document_id") == document_id]
                    if law_rows:
                        save_document(law, law_rows)
        except Exception:
            pass
    return local_laws, local_rows

@st.cache_resource(show_spinner="جاري تحميل نموذج البحث العربي وبناء الفهرس...")
def build_index(rows_json: str):
    return LegalIndex(json.loads(rows_json))


def invalidate():
    load_corpus.clear()
    build_index.clear()


def ask_llm(question: str, results: list[dict]) -> str:
    def secret(name: str, default=None):
        value = os.getenv(name)
        if value:
            return value
        try:
            return st.secrets.get(name, default)
        except Exception:
            return default

    gemini_key = secret("GEMINI_API_KEY")
    openai_key = secret("OPENAI_API_KEY")
    openrouter_key = secret("OPENROUTER_API_KEY")
    if not (gemini_key or openai_key or openrouter_key):
        return "\n\n".join(f"**المادة {r.get('article_number')}**: {r.get('text')}" for r in results[:3])
    context = "\n\n".join(
        f"[مصدر {i}] القانون رقم {r.get('law_number')} لسنة {r.get('law_year')}، المادة {r.get('article_number')}، الفقرة {r.get('paragraph_number')}، البند {r.get('clause_number')}، الصفحة {r.get('page_start')}\n{r.get('text')}"
        for i, r in enumerate(results, 1)
    )
    system_prompt = "أنت مساعد بحث قانوني. أجب بالعربية من المصادر فقط. لا تستنتج معلومة غير موجودة. اذكر الاستشهاد بالمادة والفقرة والبند والصفحة. إذا لم تكفِ المصادر قل ذلك بوضوح."
    user_prompt = f"السؤال: {question}\n\nالمصادر:\n{context}"
    if gemini_key:
        model_name = secret("GEMINI_MODEL", "gemini-2.0-flash")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model_name, safe='')}:generateContent?key={urllib.parse.quote(gemini_key, safe='')}"
        payload = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "user", "parts": [{"text": user_prompt}]}], "generationConfig": {"temperature": 0, "maxOutputTokens": 900}}
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return f"تعذر الاتصال بـ Gemini API: {exc}"
    if openai_key:
        model_name = secret("OPENAI_MODEL", "gpt-4o-mini")
        client = OpenAI(api_key=openai_key, timeout=60)
    else:
        model_name = secret("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key, timeout=60)
    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        max_tokens=900,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or "لم يتم إنشاء إجابة."

laws, rows = load_corpus()
index = build_index(json.dumps(rows, ensure_ascii=False, sort_keys=True))

with st.sidebar:
    st.markdown('<div class="brand-mark"><div class="brand-icon">⚖</div><div class="brand-name">LexGO</div></div><div class="brand-sub">منصة الذكاء القانوني العربي</div>', unsafe_allow_html=True)
    api_provider = ""
    api_key_ready = bool(os.getenv("GEMINI_API_KEY"))
    if api_key_ready:
        api_provider = "Gemini"
    if not api_key_ready:
        try:
            api_key_ready = bool(st.secrets.get("GEMINI_API_KEY"))
            if api_key_ready:
                api_provider = "Gemini"
        except Exception:
            pass
    if not api_key_ready:
        api_key_ready = bool(os.getenv("OPENAI_API_KEY"))
        api_provider = "OpenAI" if api_key_ready else ""
    if not api_key_ready:
        try:
            api_key_ready = bool(st.secrets.get("OPENAI_API_KEY"))
            api_provider = "OpenAI" if api_key_ready else ""
        except Exception:
            pass
    if not api_key_ready:
        api_key_ready = bool(os.getenv("OPENROUTER_API_KEY"))
        api_provider = "OpenRouter" if api_key_ready else ""
    if not api_key_ready:
        try:
            api_key_ready = bool(st.secrets.get("OPENROUTER_API_KEY"))
            api_provider = "OpenRouter" if api_key_ready else ""
        except Exception:
            pass
    st.markdown(f'<div class="source-chip">● API: {api_provider + " متصل" if api_key_ready else "غير مضاف — سيعرض النصوص مباشرة"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="source-chip">● التخزين: {"قاعدة بيانات دائمة" if storage_configured() else "محلي مؤقت"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="source-chip">● المستخدم: {current_user.get("username")}</div>', unsafe_allow_html=True)
    if configured_users and st.button("تسجيل الخروج", use_container_width=True):
        st.session_state.auth_user = None
        st.rerun()
    if is_admin:
        st.markdown("### إضافة قانون جديد")
        st.caption("ارفع PDF أو DOC أو DOCX وسيتم حفظه مباشرة في قاعدة البيانات.")
        uploaded = st.file_uploader("ارفع قانونًا", type=["pdf", "doc", "docx"])
        if uploaded is not None:
            target = DATA_DIR / uploaded.name
            incoming = uploaded.getvalue()
            same_file = target.exists() and target.read_bytes() == incoming
            if not same_file:
                try:
                    target.write_bytes(incoming)
                    with st.spinner("جاري قراءة الملف وتحليل القانون وفهرسته..."):
                        law, law_rows = ingest_file(target, PARSED_DIR)
                    if storage_configured():
                        with st.spinner("جاري حفظ القانون في قاعدة البيانات الدائمة..."):
                            save_document(law, law_rows)
                    invalidate()
                    st.success(f"تم الحفظ والفهرسة: {law.get('article_count', 0)} مادة و{len(law_rows)} مقطع")
                    st.rerun()
                except Exception as exc:
                    if target.exists():
                        target.unlink()
                    st.error(f"فشل رفع أو قراءة الملف: {exc}")
                    st.info("تأكد أن الملف PDF يحتوي على نص أو أن ملف Word سليم.")
            else:
                st.info("هذا الملف محفوظ بالفعل وجاهز للبحث.")
    else:
        st.info("وضع المستخدم: يمكنك استخدام الشات والبحث فقط. إضافة القوانين متاحة للمدير.")
    st.divider()
    st.markdown("### حالة المكتبة")
    st.metric("القوانين المفهرسة", len([x for x in laws if not x.get("error")]))
    st.metric("المواد والمقاطع", len(rows))
    if st.button("تحديث الفهرس", use_container_width=True):
        invalidate()
        st.rerun()
    if st.button("مسح المحادثة", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

st.markdown('<section class="hero"><div class="hero-kicker">LEXGO LEGAL ASSISTANT</div><h1>مستشارك القانوني الذكي</h1><p>تحدث مع مكتبتك القانونية بالعربية. ارفع القوانين، اسأل عن أي مادة، واحصل على إجابة موثقة بالمصدر والصفحة.</p></section>', unsafe_allow_html=True)

stat1, stat2, stat3 = st.columns(3)
stat1.markdown(f'<div class="metric-card"><div class="metric-label">القوانين المتاحة</div><div class="metric-value">{len([x for x in laws if not x.get("error")] )}</div></div>', unsafe_allow_html=True)
stat2.markdown(f'<div class="metric-card"><div class="metric-label">المقاطع المفهرسة</div><div class="metric-value">{len(rows)}</div></div>', unsafe_allow_html=True)
stat3.markdown('<div class="metric-card"><div class="metric-label">نوع البحث</div><div class="metric-value">هجين عربي</div></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">ابدأ محادثتك القانونية</div>', unsafe_allow_html=True)

if not laws:
    st.info("ارفع أول ملف PDF أو DOCX من القائمة الجانبية للبدء.")
    st.stop()

with st.expander("عرض القوانين المفهرسة", expanded=False):
    for law in laws:
        if law.get("error"):
            st.error(f"{law.get('file_name')}: {law.get('error')}")
            continue
        st.markdown(f'<div class="law-card"><strong>{law.get("title")}</strong><br><span class="source-chip">القانون {law.get("law_number") or "غير مستخرج"}</span><span class="source-chip">سنة {law.get("law_year") or "غير مستخرجة"}</span><span class="source-chip">{law.get("article_count", 0)} مادة</span></div>', unsafe_allow_html=True)
        if law.get("extraction", {}).get("needs_review"):
            st.warning("يحتاج هذا القانون إلى مراجعة الحقول المستخرجة.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("results"):
            st.markdown('<div class="section-title">المصادر والتحقق</div>', unsafe_allow_html=True)
            for i, result in enumerate(message["results"], 1):
                citation = f"القانون {result.get('law_number') or '؟'} لسنة {result.get('law_year') or '؟'} — المادة {result.get('article_number') or '؟'} — الفقرة {result.get('paragraph_number') or '؟'} — البند {result.get('clause_number') or '؟'} — صـ {result.get('page_start') or '؟'}"
                with st.expander(f"المصدر {i}  ·  تطابق {result.get('score')}%  ·  المادة {result.get('article_number') or '؟'}"):
                    st.markdown(f'<div class="law-card"><div class="source-chip">{citation}</div><p style="color:#e2e8f0;line-height:2;margin-top:12px">{result.get("text")}</p></div>', unsafe_allow_html=True)
                    st.caption(f"مرشحات البحث: {message.get('filters') or 'بحث عام'}")

if not st.session_state.chat_history:
    st.info("اكتب سؤالك في مربع المحادثة أسفل الصفحة، مثل: ما نص المادة 1 من القانون المدني؟")

question = st.chat_input("اكتب سؤالك عن القوانين هنا...")
if question:
    filters = query_filters(question)
    with st.spinner("جاري البحث في المواد القانونية..."):
        results = index.search(question, k=8)
        if results:
            answer = ask_llm(question, results)
        else:
            answer = "لم أجد نصًا مطابقًا في الملفات المضافة. جرّب ذكر رقم القانون أو رقم المادة أو استخدم كلمات أكثر تحديدًا."
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append({"role": "assistant", "content": answer, "results": results, "filters": filters})
    st.rerun()
