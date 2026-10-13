from __future__ import annotations

import json
import hmac
import html
import hashlib
import os
import re
import secrets
import sys
import time
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

st.set_page_config(page_title="LexGO | المستشار القانوني", page_icon="⚖️", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Noto+Kufi+Arabic:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { direction: rtl; text-align: right; font-family: 'IBM Plex Sans Arabic', sans-serif; }
[data-testid="stSidebar"] { direction: rtl; background: linear-gradient(180deg,rgba(33,20,15,.72) 0%,rgba(47,29,20,.58) 100%); border-left: 1px solid rgba(212,175,55,.22); backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px); }
section[data-testid="stSidebar"] { width: min(350px, 88vw) !important; min-width: min(350px, 88vw) !important; }
[data-testid="stSidebar"] .block-container { padding-top: 2rem; padding-right:1.15rem; padding-left:1.15rem; direction:rtl; text-align:right; }
[data-testid="stSidebar"] .block-container, [data-testid="stSidebar"] .block-container * { direction:rtl; text-align:right; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { text-align:right; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 { text-align:right; }
[data-testid="stSidebar"] button { justify-content:flex-start; text-align:right !important; direction:rtl; }
[data-testid="stSidebar"] button div, [data-testid="stSidebar"] button p { text-align:right !important; width:100%; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea { direction:rtl; text-align:right !important; }
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { direction:rtl; text-align:right; }
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] > div { justify-content:flex-start; text-align:right; }
[data-testid="stSidebar"] [data-testid="stMetric"] { direction:rtl; text-align:right; }
[data-testid="stSidebar"] [data-testid="stMetricLabel"], [data-testid="stSidebar"] [data-testid="stMetricValue"] { text-align:right; }
.stApp { background: radial-gradient(circle at 85% 5%, rgba(180,130,40,.16), transparent 28%), radial-gradient(circle at 10% 80%, rgba(104,54,28,.22), transparent 30%), #170e0a; }
.main .block-container { max-width: 980px; width:100%; margin:0 auto; padding: 2.5rem 1.5rem 5rem; }
.brand-mark { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.brand-icon { width:44px; height:44px; display:grid; place-items:center; border-radius:14px; background:linear-gradient(135deg,#f4d06f,#a87519); color:#2b180b; font-size:24px; box-shadow:0 10px 28px rgba(212,175,55,.22); }
.brand-name { font-family:'Noto Kufi Arabic',sans-serif; font-size:1.32rem; font-weight:800; color:#f8fafc; letter-spacing:-.5px; }
.brand-sub { color:#e6c56a; font-size:.78rem; margin:0 0 1.2rem 56px; }
.hero { max-width:900px; margin:0 auto 1.5rem; padding:1.65rem 2rem; border:1px solid rgba(255,222,135,.28); border-radius:22px; background:linear-gradient(135deg,rgba(111,72,38,.34),rgba(42,24,17,.30)); box-shadow:0 18px 50px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.10); backdrop-filter:blur(18px) saturate(125%); -webkit-backdrop-filter:blur(18px) saturate(125%); }
.hero-kicker { color:#e8c766; font-weight:700; font-size:.82rem; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:.5rem; }
.hero h1 { color:#f8fafc; font-family:'Noto Kufi Arabic',sans-serif; font-size:2rem; font-weight:700; line-height:1.55; margin:0 0 .55rem; letter-spacing:-.4px; }
.hero p { color:#e8dcca; font-size:1.02rem; margin:0; max-width:720px; }
.legal-cover { position:relative; overflow:hidden; max-width:900px; margin:0 auto 1.25rem; padding:2.35rem 2rem 1.65rem; text-align:center; border:1px solid rgba(255,222,135,.34); border-radius:28px; background:linear-gradient(135deg,rgba(102,63,31,.48),rgba(37,21,15,.60) 55%,rgba(103,69,32,.30)); box-shadow:0 24px 70px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.13); backdrop-filter:blur(22px) saturate(135%); -webkit-backdrop-filter:blur(22px) saturate(135%); }
.legal-cover:before, .legal-cover:after { content:""; position:absolute; width:180px; height:180px; border:1px solid rgba(232,199,102,.13); border-radius:50%; pointer-events:none; }
.legal-cover:before { top:-105px; right:-55px; box-shadow:0 0 0 18px rgba(232,199,102,.04), 0 0 0 36px rgba(232,199,102,.025); }
.legal-cover:after { bottom:-120px; left:-55px; box-shadow:0 0 0 18px rgba(232,199,102,.04), 0 0 0 36px rgba(232,199,102,.025); }
.cover-emblem { position:relative; z-index:1; width:58px; height:58px; display:grid; place-items:center; margin:0 auto .85rem; border:1px solid rgba(255,231,151,.55); border-radius:18px; color:#2b180b; background:linear-gradient(135deg,#f6d978,#ad7b20); font-size:30px; box-shadow:0 12px 28px rgba(212,175,55,.28); }
.cover-kicker { position:relative; z-index:1; color:#e8c766; font-size:.72rem; font-weight:700; letter-spacing:2px; }
.legal-cover h1 { position:relative; z-index:1; margin:.35rem 0 .35rem; color:#fff8e8; font-family:'Noto Kufi Arabic',sans-serif; font-size:2rem; font-weight:800; }
.legal-cover p { position:relative; z-index:1; margin:0; color:#e6d7c1; font-size:.95rem; }
.cover-line { position:relative; z-index:1; width:80px; height:2px; margin:1rem auto .7rem; background:linear-gradient(90deg,transparent,#e8c766,transparent); }
.legal-cover span { position:relative; z-index:1; color:#cdb995; font-size:.78rem; }
.admin-panel-title { color:#f4d37c; font-family:'Noto Kufi Arabic',sans-serif; font-weight:700; text-align:center; margin:.4rem 0 .7rem; }
.language-label { color:#cdb995; font-size:.72rem; text-align:center; margin:0 auto .22rem; }
[data-testid="stPopover"] > button { width:40px !important; min-width:40px !important; height:40px !important; min-height:40px !important; padding:0 !important; margin:0 auto !important; border:1px solid rgba(255,222,135,.42) !important; border-radius:50% !important; background:rgba(255,255,255,.06) !important; color:#f4d37c !important; font-size:1.08rem !important; box-shadow:0 8px 20px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(16px); }
[data-testid="stPopover"] { display:flex; justify-content:center; }
[data-testid="stPopoverBody"] { min-width:220px; border:1px solid rgba(255,222,135,.28) !important; border-radius:16px !important; background:rgba(44,26,17,.94) !important; backdrop-filter:blur(20px); }
[data-testid="stPopoverBody"] [data-testid="stRadio"] label { color:#f5ead8 !important; }
.metric-card { padding:1rem 1.1rem; border-radius:16px; border:1px solid rgba(255,222,135,.24); background:rgba(91,55,30,.25); box-shadow:0 10px 28px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); text-align:center; }
.metric-label { color:#cbb998; font-size:.8rem; text-align:center; }
.metric-value { color:#f8fafc; font-size:1.55rem; font-weight:800; margin-top:.2rem; text-align:center; }
.law-card { padding:1.1rem 1.25rem; border:1px solid rgba(255,222,135,.22); border-radius:16px; margin-bottom:.8rem; background:linear-gradient(135deg,rgba(101,61,32,.30),rgba(35,21,15,.28)); box-shadow:0 10px 28px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(15px); -webkit-backdrop-filter:blur(15px); text-align:center; }
.source-chip { display:inline-block; padding:.3rem .65rem; margin:.15rem; border-radius:999px; background:rgba(212,175,55,.12); color:#f2d47c; font-size:.76rem; border:1px solid rgba(212,175,55,.22); }
.section-title { color:#e2e8f0; font-family:'Noto Kufi Arabic',sans-serif; font-size:1.12rem; font-weight:700; margin:.7rem 0 1rem; }
div[data-testid="stFileUploader"] { border:1px dashed rgba(255,222,135,.55); border-radius:16px; padding:.4rem; background:rgba(91,49,22,.20); box-shadow:inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); }
button[kind="primary"] { background:linear-gradient(135deg,#d4af37,#8f6517); border:0; color:#21140d; }
[data-testid="stChatMessage"] { border:0 !important; background:transparent !important; box-shadow:none !important; padding:0 !important; margin:0 !important; }
[data-testid="stChatMessage"] p { line-height:2; }
[data-testid="stChatInput"] { border:1px solid rgba(255,222,135,.42) !important; border-radius:18px !important; background:rgba(255,255,255,.035) !important; box-shadow:0 10px 26px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.10); backdrop-filter:blur(22px) saturate(135%); -webkit-backdrop-filter:blur(22px) saturate(135%); }
[data-testid="stChatInput"] > div { background:transparent !important; }
[data-testid="stChatInput"] textarea { color:#fff7e6 !important; background:transparent !important; }
[data-testid="stChatInput"] textarea::placeholder { color:rgba(236,220,194,.68) !important; }
[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapsedControl"] button { border:1px solid rgba(255,222,135,.35) !important; border-radius:10px !important; background:rgba(67,39,24,.55) !important; color:#f4d37c !important; }
[data-testid="stExpander"] { border:0 !important; background:transparent !important; box-shadow:none !important; }
[data-testid="stForm"] { max-width:700px; margin:1.2rem auto 0; padding:1.1rem 1.25rem .8rem; border:0 !important; background:rgba(72,42,25,.12); box-shadow:none !important; }
[data-testid="stAlert"] { border:0 !important; border-right:3px solid rgba(212,175,55,.55); background:rgba(212,175,55,.06); box-shadow:none !important; }
[data-testid="stFormSubmitButton"] button { width:100%; border:1px solid rgba(255,231,151,.45) !important; border-radius:12px !important; background:linear-gradient(135deg,#e0bd52,#9b701d) !important; color:#24160d !important; box-shadow:0 8px 20px rgba(212,175,55,.18); }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] > div { background:rgba(35,21,15,.34) !important; border-color:rgba(255,222,135,.28) !important; color:#fff7e6 !important; backdrop-filter:blur(10px); }
.legal-notice { margin-top:1rem; padding:.85rem 1rem; border-right:3px solid #d4af37; border-radius:12px; background:rgba(212,175,55,.09); color:#e8dcca; font-size:.88rem; line-height:1.9; }
blockquote { border-right:3px solid #d4af37 !important; border-left:0 !important; background:rgba(212,175,55,.09); border-radius:12px; color:#e8dcca !important; padding:.75rem 1rem !important; }
.law-card p, .law-card .legal-text { font-family:'Amiri',serif; font-size:1.12rem; line-height:2.05; }
.source-chip { font-family:'IBM Plex Sans Arabic',sans-serif; }
.chat-intro { max-width:900px; margin:0 auto 1.25rem; padding:.85rem 1.1rem; border:1px solid rgba(255,222,135,.16); border-radius:14px; color:#d9cbb7; background:rgba(72,42,25,.18); text-align:center; }
.chat-row { max-width:780px; margin:1.25rem auto 2rem; text-align:center; }
.chat-meta { display:flex; justify-content:center; align-items:center; gap:.55rem; color:#d8bb6a; font-family:'Noto Kufi Arabic',sans-serif; font-size:.76rem; font-weight:600; margin-bottom:.65rem; }
.chat-avatar { width:30px; height:30px; display:inline-grid; place-items:center; border-radius:50%; color:#28170d; background:linear-gradient(135deg,#f5d77c,#a6781f); box-shadow:0 6px 16px rgba(212,175,55,.2); }
.chat-text { color:#f5ead8; font-size:1.02rem; line-height:2.1; padding:0 .8rem 1.15rem; border-bottom:1px solid rgba(212,175,55,.20); }
.chat-row.user .chat-meta { color:#b8a58d; }
.chat-row.user .chat-avatar { background:rgba(212,175,55,.16); color:#f4d37c; box-shadow:none; }
.chat-row.user .chat-text { color:#eadcc7; font-size:.98rem; border-bottom-color:rgba(255,255,255,.10); }
.legal-inline { margin-top:1rem; padding:.65rem .9rem; border-right:3px solid #d4af37; border-radius:10px; background:rgba(212,175,55,.08); color:#d9cbb7; font-size:.86rem; line-height:1.9; text-align:right; }
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
    admin_password_hash = _secret("ADMIN_PASSWORD_HASH")
    admin_password = _secret("ADMIN_PASSWORD")
    if admin_user and (admin_password_hash or admin_password):
        return [{"username": admin_user, "password_hash": admin_password_hash, "password": admin_password, "role": "admin"}]
    return []


def authenticate(username: str, password: str) -> dict | None:
    for user in _users():
        stored_password = str(user.get("password_hash") or user.get("password", ""))
        password_ok = verify_password(password, stored_password)
        if hmac.compare_digest(str(user.get("username", "")), username) and password_ok:
            return {"username": username, "role": user.get("role", "user")}
    return None


def verify_password(password: str, stored: str) -> bool:
    """Accept PBKDF2 hashes; retain plaintext compatibility for existing Secrets during migration."""
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = stored.split("$", 3)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    return bool(stored) and hmac.compare_digest(stored, password)


def hash_password(password: str, iterations: int = 310000) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

configured_users = _users()
if not st.session_state.auth_user:
    st.markdown('<div class="hero"><div class="hero-kicker">LEXGO SECURE ACCESS</div><h1>تسجيل الدخول إلى المستشار القانوني</h1><p>سجّل الدخول للوصول إلى مكتبة القوانين. صلاحية إضافة الملفات متاحة للمدير فقط.</p></div>', unsafe_allow_html=True)
    if not configured_users:
        st.warning("لم يتم إعداد مستخدمين بعد. أضف ADMIN_USERNAME وADMIN_PASSWORD في Streamlit Secrets ثم أعد تشغيل التطبيق.")
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        login_col, guest_col = st.columns(2)
        with login_col:
            submitted = st.form_submit_button("دخول", type="primary", use_container_width=True)
        with guest_col:
            guest_submitted = st.form_submit_button("الدخول كضيف", use_container_width=True)
        if guest_submitted:
            st.session_state.auth_user = {"username": "ضيف", "role": "user", "guest": True}
            st.session_state.chat_history = []
            st.rerun()
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
is_guest = bool(current_user.get("guest"))

LANGUAGES = {
    "ar": {"label": "العربية", "instruction": "اكتب الإجابة باللغة العربية القانونية الواضحة."},
    "en": {"label": "Legal English", "instruction": "Write the answer in precise, formal legal English. Preserve Arabic law titles and article numbers, and provide an English explanation when needed."},
    "fr": {"label": "Français", "instruction": "Rédigez la réponse en français juridique formel et précis. Conservez les titres arabes des lois et les numéros des articles, et expliquez-les en français si nécessaire."},
}
if "response_language" not in st.session_state:
    st.session_state.response_language = "ar"

language_bar = st.container()
with language_bar:
    st.markdown('<div class="language-label">لغة الإجابة</div>', unsafe_allow_html=True)
    with st.popover("🌐", help="اختيار لغة الإجابة"):
        st.markdown("**اختر لغة الإجابة**")
        language_choice = st.radio(
            "اللغة",
            options=list(LANGUAGES),
            index=list(LANGUAGES).index(st.session_state.response_language),
            format_func=lambda code: LANGUAGES[code]["label"],
            label_visibility="collapsed",
            key="language_choice",
        )
        if language_choice != st.session_state.response_language:
            st.session_state.response_language = language_choice
            st.rerun()

LOCALIZED_MESSAGES = {
    "clarify": {
        "ar": "أستطيع مساعدتك، لكن أحتاج تحديدًا أكثر حتى أرجع إلى المصدر الصحيح. اكتب اسم القانون ورقم المادة، أو اذكر الموضوع القانوني الذي تبحث عنه. مثال: ما نص المادة 29 من القانون المدني؟",
        "en": "I can help, but I need more details to retrieve the correct source. Please provide the law name and article number, or specify the legal topic. Example: What is the text of Article 29 of the Civil Code?",
        "fr": "Je peux vous aider, mais j’ai besoin de précisions pour retrouver la source correcte. Indiquez le nom de la loi et le numéro de l’article, ou précisez le sujet juridique. Exemple : quel est le texte de l’article 29 du Code civil ?",
    },
    "not_found": {
        "ar": "لم أجد هذه المعلومة في الملفات القانونية المضافة. إذا كنت تقصد قانونًا أو مادة محددة، اذكر اسم القانون ورقم المادة لأبحث عنها بدقة.",
        "en": "I could not find this information in the uploaded legal files. If you mean a specific law or article, provide its name and number so I can search accurately.",
        "fr": "Je n’ai pas trouvé cette information dans les fichiers juridiques ajoutés. Si vous recherchez une loi ou un article précis, indiquez son nom et son numéro afin que je puisse effectuer une recherche exacte.",
    },
    "notice": {
        "ar": "> **تنبيه مهني:** هذه إجابة إرشادية مبنية على الملفات المتاحة في النظام. إذا لم تحصل على إجابة كاملة، أو كان السؤال متعمقًا أو مرتبطًا بإجراء عملي، يُرجى الرجوع إلى **الشؤون القانونية** أو مستشار قانوني مختص.",
        "en": "> **Professional notice:** This is guidance based on the files available in the system. If the answer is incomplete, highly detailed, or concerns a practical procedure, please consult your **legal affairs department** or a qualified legal adviser.",
        "fr": "> **Avis professionnel :** Cette réponse indicative repose sur les fichiers disponibles dans le système. Si la réponse est incomplète, approfondie ou liée à une procédure pratique, veuillez consulter votre **service juridique** ou un conseiller juridique qualifié.",
    },
}


def localized_message(key: str) -> str:
    language = st.session_state.get("response_language", "ar")
    return LOCALIZED_MESSAGES[key].get(language, LOCALIZED_MESSAGES[key]["ar"])


UI_TEXT = {
    "cover_title": {"ar": "المستشار القانوني", "en": "Legal Counsel", "fr": "Conseiller juridique"},
    "cover_sub": {"ar": "مساحة محادثة رسمية للبحث في القوانين والمواد المرفوعة", "en": "A formal chat space for searching uploaded laws and articles", "fr": "Un espace de discussion officiel pour rechercher les lois et articles importés"},
    "cover_note": {"ar": "إجابة موثقة من مكتبة التشريعات الخاصة بك", "en": "Verified answers from your legislation library", "fr": "Réponses vérifiées à partir de votre bibliothèque législative"},
    "chat_title": {"ar": "محادثتك مع المستشار", "en": "Your conversation with Legal Counsel", "fr": "Votre conversation avec le conseiller"},
    "chat_intro": {"ar": "اكتب سؤالك مباشرة. سيبقى سياق هذه المحادثة مؤقتًا داخل الجلسة، بينما تبقى القوانين محفوظة في قاعدة البيانات.", "en": "Ask your question directly. This conversation remains temporary within the session, while laws remain permanently stored in the database.", "fr": "Posez votre question directement. Le contexte de cette conversation reste temporaire dans la session, tandis que les lois restent enregistrées dans la base de données."},
    "new_chat": {"ar": "محادثة جديدة", "en": "New chat", "fr": "Nouvelle conversation"},
    "input": {"ar": "اكتب سؤالك عن القوانين هنا...", "en": "Ask your legal question here...", "fr": "Écrivez votre question juridique ici..."},
    "no_laws": {"ar": "ارفع أول ملف PDF أو DOCX من القائمة الجانبية للبدء.", "en": "Upload your first PDF or DOCX from the sidebar to begin.", "fr": "Importez votre premier fichier PDF ou DOCX depuis la barre latérale pour commencer."},
}


def ui_text(key: str) -> str:
    language = st.session_state.get("response_language", "ar")
    return UI_TEXT[key].get(language, UI_TEXT[key]["ar"])


def service_error_message() -> str:
    return {"ar": "تعذر تشغيل خدمة الإجابة الذكية حاليًا. حاول مرة أخرى لاحقًا.", "en": "The smart answer service is currently unavailable. Please try again later.", "fr": "Le service de réponse intelligente est momentanément indisponible. Veuillez réessayer plus tard."}.get(st.session_state.get("response_language", "ar"), "تعذر تشغيل خدمة الإجابة الذكية حاليًا. حاول مرة أخرى لاحقًا.")

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


def call_gemini(prompt: str, system_prompt: str = "") -> str:
    key = _secret("GEMINI_API_KEY")
    model_name = _secret("GEMINI_MODEL", "gemini-3-flash-preview").strip()
    if model_name.startswith("models/"):
        model_name = model_name[7:]
    model_name = model_name.split(":", 1)[0]
    model_name = {"gemini-2.0-flash": "gemini-3-flash-preview", "gemini-2.5-flash": "gemini-3-flash-preview", "gemini-3.8-flash": "gemini-3-flash-preview"}.get(model_name, model_name)
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model_name, safe='')}:generateContent?key={urllib.parse.quote(key, safe='')}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]} if system_prompt else None,
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 900},
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            return service_error_message()
        if exc.code in {408, 429, 500, 502, 503, 504}:
            return service_error_message()
        return service_error_message()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return service_error_message()


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
    selected_language = LANGUAGES.get(st.session_state.get("response_language", "ar"), LANGUAGES["ar"])
    system_prompt = f"أنت مساعد بحث قانوني. أجب من النصوص المسترجعة فقط. ابدأ بخلاصة مباشرة، ثم اشرح بنقاط قصيرة عند الحاجة، واذكر رقم القانون والسنة والمادة والفقرة والبند والصفحة. لا تستنتج معلومة غير موجودة ولا تقدم رأيًا قانونيًا شخصيًا. إذا لم تكفِ المصادر قل ذلك بوضوح. {selected_language['instruction']}"
    user_prompt = f"السؤال: {question}\n\nالمصادر:\n{context}"
    if gemini_key:
        return call_gemini(user_prompt, system_prompt)
    if openai_key:
        model_name = secret("OPENAI_MODEL", "gpt-4o-mini")
        client = OpenAI(api_key=openai_key, timeout=60)
    else:
        model_name = secret("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key, timeout=60)
    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=900,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or service_error_message()
    except Exception:
        return service_error_message()


def is_legal_question(question: str) -> bool:
    legal_terms = (
        "قانون", "المادة", "مادة", "فقرة", "بند", "تشريع", "لائحة", "قرار", "مرسوم",
        "محكمة", "دعوى", "حكم", "عقد", "التزام", "مسؤولية", "تعويض", "إدارة قانونية",
        "القوانين", "الملفات القانونية", "نص المادة", "الجريدة الرسمية",
        "article", "articles", "law", "act", "code", "legal", "regulation", "decree",
        "court", "claim", "judgment", "contract", "liability", "compensation", "statute",
        "article de loi", "loi", "code civil", "juridique", "règlement", "décret", "tribunal",
        "jugement", "contrat", "responsabilité", "indemnisation", "texte de l’article",
    )
    return bool(query_filters(question)) or any(term in question for term in legal_terms)


def needs_legal_clarification(question: str, filters: dict) -> bool:
    vague_phrases = ("نص مادة قانونية", "مادة قانونية", "نص مادة", "هل يمكنك المساعدة", "أبحث عن نص")
    if any(phrase in question for phrase in vague_phrases) and not filters.get("article_number") and not filters.get("law_number"):
        return True
    return False


def classify_question(question: str) -> str:
    """Let the configured LLM route the question without giving it legal data."""
    system_prompt = """صنّف سؤال المستخدم فقط، ولا تجب عنه. أعد JSON صالحًا فقط بهذا الشكل:
{"intent":"general"|"legal_specific"|"legal_clarify"}

general: تحية، شكر، سؤال عام غير قانوني، أو محادثة عادية.
legal_specific: سؤال قانوني يمكن البحث عنه لأنه يذكر مادة/قانونًا/موضوعًا قانونيًا واضحًا.
legal_clarify: سؤال قانوني عام أو ناقص يحتاج اسم القانون أو رقم المادة أو تحديد الموضوع.
لا تعتبر كلمة مساعدة وحدها سؤالًا قانونيًا محددًا."""
    raw = ""
    try:
        key = _secret("GEMINI_API_KEY")
        if key:
            raw = call_gemini(question, system_prompt)
        else:
            key = _secret("OPENAI_API_KEY")
            router_key = key or _secret("OPENROUTER_API_KEY")
            if router_key:
                if key:
                    client = OpenAI(api_key=key, timeout=30)
                    model = _secret("OPENAI_MODEL", "gpt-4o-mini")
                else:
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=router_key, timeout=30)
                    model = _secret("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
                response = client.chat.completions.create(
                    model=model, temperature=0, max_tokens=80,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
                )
                raw = response.choices[0].message.content or ""
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        intent = parsed.get("intent")
        if intent in {"general", "legal_specific", "legal_clarify"}:
            return intent
    except Exception:
        pass
    # Safe fallback only when no LLM is configured or its classifier fails.
    if is_legal_question(question):
        return "legal_clarify" if needs_legal_clarification(question, query_filters(question)) else "legal_specific"
    return "general"


def ask_general_llm(question: str) -> str:
    selected_language = LANGUAGES.get(st.session_state.get("response_language", "ar"), LANGUAGES["ar"])
    system_prompt = f"أنت مساعد ودود داخل تطبيق قانوني. يمكنك الرد على التحية والشكر والأسئلة العامة باختصار ووضوح. لا تستخدم أي معلومة قانونية من خارج ملفات المستخدم؛ إذا كان السؤال قانونيًا فاطلب منه تحديد القانون أو المادة، وسيتم البحث في الملفات فقط. لا تدّع أنك محامٍ. {selected_language['instruction']}"
    gemini_key = _secret("GEMINI_API_KEY")
    openai_key = _secret("OPENAI_API_KEY")
    openrouter_key = _secret("OPENROUTER_API_KEY")
    if gemini_key:
        return call_gemini(question, system_prompt)
    if openai_key or openrouter_key:
        if openai_key:
            client = OpenAI(api_key=openai_key, timeout=60)
            model_name = _secret("OPENAI_MODEL", "gpt-4o-mini")
        else:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key, timeout=60)
            model_name = _secret("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=.3,
                max_tokens=300,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
            )
            return response.choices[0].message.content or service_error_message()
        except Exception:
            return service_error_message()
    language = st.session_state.get("response_language", "ar")
    if any(word in question for word in ("شكرا", "شكرًا", "مشكور")):
        return {"ar": "العفو، أنا هنا لمساعدتك.", "en": "You are welcome. I am here to help.", "fr": "Je vous en prie. Je suis là pour vous aider."}.get(language, "العفو، أنا هنا لمساعدتك.")
    if any(word in question for word in ("السلام", "مرحبا", "مرحبًا", "أهلا", "أهلًا")):
        return {"ar": "وعليكم السلام ورحمة الله وبركاته. أهلًا بك، كيف يمكنني مساعدتك؟", "en": "Peace be upon you as well. Welcome. How may I help you?", "fr": "Que la paix soit également sur vous. Bienvenue. Comment puis-je vous aider ?"}.get(language, "وعليكم السلام ورحمة الله وبركاته. أهلًا بك، كيف يمكنني مساعدتك؟")
    return {"ar": "أهلًا بك. أضف مفتاح Gemini أو OpenAI حتى أتمكن من الإجابة عن الأسئلة العامة. وللأسئلة القانونية اذكر اسم القانون ورقم المادة.", "en": "Welcome. Add a Gemini or OpenAI key for general answers. For legal questions, provide the law name and article number.", "fr": "Bienvenue. Ajoutez une clé Gemini ou OpenAI pour les réponses générales. Pour les questions juridiques, indiquez le nom de la loi et le numéro de l’article."}.get(language, "أهلًا بك. أضف مفتاح Gemini أو OpenAI حتى أتمكن من الإجابة عن الأسئلة العامة. وللأسئلة القانونية اذكر اسم القانون ورقم المادة.")

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
    if is_admin and api_provider == "Gemini" and st.button("اختبار Gemini API", use_container_width=True):
        with st.spinner("جاري اختبار Gemini..."):
            gemini_test = call_gemini("اكتب كلمة: متصل", "أجب بكلمة واحدة فقط.")
        if gemini_test.strip() == "متصل":
            st.success("Gemini API يعمل بنجاح.")
        else:
            st.error(gemini_test)
    st.markdown(f'<div class="source-chip">● التخزين: {"قاعدة بيانات دائمة" if storage_configured() else "محلي مؤقت"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="source-chip">● ذاكرة القوانين: {"دائمة في قاعدة البيانات" if storage_configured() else "غير مفعلة"}</div>', unsafe_allow_html=True)
    st.markdown('<div class="source-chip">● ذاكرة الشات: مؤقتة لهذه الجلسة</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="source-chip">● المستخدم: {current_user.get("username")}</div>', unsafe_allow_html=True)
    if is_guest:
        st.markdown('<div class="source-chip">● وضع الضيف: الشات والبحث فقط</div>', unsafe_allow_html=True)
    if configured_users and st.button("تسجيل الخروج", use_container_width=True):
        st.session_state.auth_user = None
        st.session_state.chat_history = []
        st.rerun()
    if is_admin:
        st.markdown("### إضافة قانون جديد")
        if not storage_configured():
            st.error("قاعدة البيانات الدائمة غير متصلة. تم إيقاف الرفع حتى لا يُحفظ القانون في تخزين مؤقت.")
            st.caption("أضف SUPABASE_URL وSUPABASE_SERVICE_ROLE_KEY في Streamlit Secrets ثم أعد تشغيل التطبيق.")
            uploaded = None
        else:
            st.caption("ارفع PDF أو DOC أو DOCX وسيتم تحليله وحفظه مباشرة في قاعدة البيانات.")
            uploaded = st.file_uploader("ارفع قانونًا", type=["pdf", "doc", "docx"])
        if uploaded is not None and storage_configured():
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
    if is_admin:
        st.divider()
        st.caption("تفاصيل المكتبة متاحة من تبويب لوحة الإدارة داخل الصفحة.")
    if st.button("مسح المحادثة", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

st.markdown(f'<section class="legal-cover"><div class="cover-emblem">⚖</div><div class="cover-kicker">LEXGO · LEGAL CHAT</div><h1>{html.escape(ui_text("cover_title"))}</h1><p>{html.escape(ui_text("cover_sub"))}</p><div class="cover-line"></div><span>{html.escape(ui_text("cover_note"))}</span></section>', unsafe_allow_html=True)

if is_admin:
    admin_tab = st.tabs(["لوحة الإدارة"])[0]
    with admin_tab:
        with st.expander("لوحة الإدارة · القوانين والفهرسة", expanded=False):
            st.markdown('<div class="admin-panel-title">إدارة مكتبة التشريعات</div><div class="chat-intro">هذه المعلومات والأدوات ظاهرة للمدير فقط ولا تظهر للمستخدم العادي.</div>', unsafe_allow_html=True)
            stat1, stat2, stat3 = st.columns(3)
            stat1.markdown(f'<div class="metric-card"><div class="metric-label">القوانين المتاحة</div><div class="metric-value">{len([x for x in laws if not x.get("error")])}</div></div>', unsafe_allow_html=True)
            stat2.markdown(f'<div class="metric-card"><div class="metric-label">المواد المفهرسة</div><div class="metric-value">{len(rows)}</div></div>', unsafe_allow_html=True)
            stat3.markdown('<div class="metric-card"><div class="metric-label">نوع البحث</div><div class="metric-value">هجين عربي</div></div>', unsafe_allow_html=True)
            if st.button("تحديث الفهرس", key="admin_refresh_index", use_container_width=True):
                invalidate()
                st.rerun()
            if st.button("إعادة فهرسة كل القوانين", key="admin_reindex_all", use_container_width=True):
                with st.spinner("جاري إعادة تحليل وحفظ كل القوانين..."):
                    fresh_laws, fresh_rows = load_all(DATA_DIR, PARSED_DIR)
                    if storage_configured():
                        for fresh_law in fresh_laws:
                            fresh_id = fresh_law.get("document_id")
                            fresh_law_rows = [r for r in fresh_rows if r.get("document_id") == fresh_id]
                            if fresh_law_rows:
                                save_document(fresh_law, fresh_law_rows)
                invalidate()
                st.success("تمت إعادة فهرسة كل القوانين وحفظها.")
                st.rerun()
            with st.expander("عرض القوانين المفهرسة", expanded=False):
                for law in laws:
                    if law.get("error"):
                        st.error(f"{law.get('file_name')}: {law.get('error')}")
                        continue
                    st.markdown(f'<div class="law-card"><strong>{law.get("title")}</strong><br><span class="source-chip">القانون {law.get("law_number") or "غير مستخرج"}</span><span class="source-chip">سنة {law.get("law_year") or "غير مستخرجة"}</span><span class="source-chip">{law.get("article_count", 0)} مادة</span></div>', unsafe_allow_html=True)
                    if law.get("extraction", {}).get("needs_review"):
                        st.warning("يحتاج هذا القانون إلى مراجعة الحقول المستخرجة.")
    
chat_title, new_chat = st.columns([5, 1])
with chat_title:
    st.markdown(f'<div class="section-title">{html.escape(ui_text("chat_title"))}</div><div class="chat-intro">{html.escape(ui_text("chat_intro"))}</div>', unsafe_allow_html=True)
with new_chat:
    if st.button(ui_text("new_chat"), use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

if not laws:
    st.info(ui_text("no_laws"))
    st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def message_html(content: str, role: str) -> str:
    body = html.escape(content or "").replace("\n", "<br>")
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = body.replace("&gt; <strong>تنبيه مهني:</strong>", '<div class="legal-inline"><strong>تنبيه مهني:</strong>')
    if 'class="legal-inline"' in body:
        body += "</div>"
    label = "المستشار القانوني" if role == "assistant" else "سؤالك"
    avatar = "⚖" if role == "assistant" else "•"
    return f'<div class="chat-row {role}"><div class="chat-meta"><span class="chat-avatar">{avatar}</span><span>{label}</span></div><div class="chat-text">{body}</div></div>'


def complete_article_result(question: str, results: list[dict]) -> list[dict]:
    filters = query_filters(question)
    if not results or not filters.get("article_number"):
        return results[:1]
    top = results[0]
    article_rows = [
        row for row in index.rows
        if str(row.get("document_id")) == str(top.get("document_id"))
        and str(row.get("article_number")) == str(filters["article_number"])
    ]
    article_rows.sort(key=lambda row: (int(row.get("paragraph_number") or 0), int(row.get("clause_number") or 0)))
    if article_rows:
        merged = dict(top)
        merged["text"] = "\n".join(str(row.get("text", "")).strip() for row in article_rows if row.get("text"))
        merged["paragraph_number"] = "كاملة"
        merged["clause_number"] = "كاملة"
        return [merged]
    return results[:1]


def verified_search(question: str) -> list[dict]:
    try:
        return index.search(question, k=50, threshold=70.0)
    except TypeError:
        # Backward compatibility when Streamlit Cloud still has the old rag_engine.py.
        legacy_results = index.search(question, k=50)
        return [row for row in legacy_results if float(row.get("score", 0) or 0) >= 70.0]


def temporary_chat_context() -> str:
    """Return only the current session's recent messages; never read from persistence."""
    recent = st.session_state.chat_history[-8:]
    if not recent:
        return ""
    lines = []
    for message in recent:
        speaker = "المستخدم" if message.get("role") == "user" else "المستشار"
        lines.append(f"{speaker}: {message.get('content', '')}")
    return "\n".join(lines)[-6000:]


def question_with_temporary_context(question: str) -> str:
    context = temporary_chat_context()
    if not context:
        return question
    return f"سياق المحادثة الحالية (للفهم فقط):\n{context}\n\nالسؤال الحالي: {question}"


def guest_request_allowed() -> bool:
    """Limit guest sessions to 20 questions per rolling minute."""
    now = time.time()
    recent = [stamp for stamp in st.session_state.get("guest_requests", []) if now - stamp < 60]
    if len(recent) >= 20:
        st.session_state.guest_requests = recent
        return False
    recent.append(now)
    st.session_state.guest_requests = recent
    return True


for message in st.session_state.chat_history:
    st.markdown(message_html(message["content"], message["role"]), unsafe_allow_html=True)
    if message["role"] == "assistant" and message.get("results"):
        st.markdown('<div class="section-title" style="text-align:center">المراجع القانونية</div>', unsafe_allow_html=True)
        for i, result in enumerate(message["results"][:1], 1):
            citation = f"القانون {result.get('law_number') or '؟'} لسنة {result.get('law_year') or '؟'} — المادة {result.get('article_number') or '؟'} — الفقرة {result.get('paragraph_number') or '؟'} — البند {result.get('clause_number') or '؟'} — صـ {result.get('page_start') or '؟'}"
            with st.expander(f"المادة {result.get('article_number') or '؟'}  ·  المرجع {i}"):
                st.markdown(f'<div class="law-card"><div class="source-chip">{citation}</div><p style="color:#e2e8f0;line-height:2;margin-top:12px;text-align:center">{result.get("text")}</p></div>', unsafe_allow_html=True)
                st.caption(f"مرشحات البحث: {message.get('filters') or 'بحث عام'}")

if not st.session_state.chat_history:
    st.info("اكتب سؤالك في مربع المحادثة أسفل الصفحة، مثل: ما نص المادة 1 من القانون المدني؟")

question = st.chat_input(ui_text("input"))
if question:
    if is_guest and not guest_request_allowed():
        st.warning("تم الوصول إلى الحد المؤقت للضيف (20 سؤالًا في الدقيقة). يرجى الانتظار قليلًا ثم المحاولة مرة أخرى.")
        st.stop()
    filters = query_filters(question)
    intent = classify_question(question)
    legal_query = intent in {"legal_specific", "legal_clarify"}
    with st.spinner("جاري البحث في المواد القانونية..."):
        if intent == "legal_clarify":
            primary_results = []
            answer = localized_message("clarify")
        elif intent == "legal_specific":
            results = verified_search(question)
            primary_results = complete_article_result(question, results)
            if primary_results:
                answer = ask_llm(question_with_temporary_context(question), primary_results)
            else:
                answer = localized_message("not_found")
        else:
            primary_results = []
            answer = ask_general_llm(question_with_temporary_context(question))
        if legal_query:
            if intent == "legal_clarify":
                primary_results = []
            answer += "\n\n" + localized_message("notice")
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append({"role": "assistant", "content": answer, "results": primary_results, "filters": filters})
    st.rerun()
