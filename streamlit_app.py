from __future__ import annotations

import base64
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
from persistence import configured as storage_configured, create_user as create_persisted_user, document_exists as remote_document_exists, load_rows as load_remote_rows, load_users as load_persisted_users, save_document, summarize_laws
from rag_engine import LegalIndex, query_filters
from bg_music import add_background_music

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
header[data-testid="stHeader"], header[data-testid="stHeader"] > div, [data-testid="stToolbar"], [data-testid="stDecoration"] { background: transparent !important; background-color: transparent !important; box-shadow: none !important; border: 0 !important; }
header[data-testid="stHeader"] { height: 3.5rem !important; }
footer, footer::before, [data-testid="stStatusWidget"], [data-testid="stBottom"], [data-testid="stBottom"]::before, [data-testid="stBottom"]::after, [data-testid="stBottom"] > div, [data-testid="stBottom"] > div > div, .stBottom, .stBottom > div, [data-testid="stBottomBlockContainer"], [data-testid="stBottomBlockContainer"] > div, [data-testid="stBottomBlockContainer"]::before, [data-testid="stBottomBlockContainer"]::after { background: transparent !important; background-color: transparent !important; box-shadow: none !important; border: 0 !important; }
#MainMenu { background: transparent !important; }
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
.stApp > header { background: transparent !important; }
.main .block-container { max-width: 980px; width:100%; margin:0 auto; padding: 2.5rem 1.5rem 5rem; }
.brand-mark { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.brand-icon { width:44px; height:44px; display:grid; place-items:center; border-radius:14px; background:linear-gradient(135deg,#f4d06f,#a87519); color:#2b180b; font-size:24px; box-shadow:0 10px 28px rgba(212,175,55,.22); }
.brand-name { font-family:'Noto Kufi Arabic',sans-serif; font-size:1.32rem; font-weight:800; color:#f8fafc; letter-spacing:-.5px; }
.brand-sub { color:#e6c56a; font-size:.78rem; margin:0 0 1.2rem 56px; }
.hero { max-width:900px; margin:0 auto 1.5rem; padding:1.65rem 2rem; border:1px solid rgba(255,222,135,.28); border-radius:22px; background:linear-gradient(135deg,rgba(111,72,38,.34),rgba(42,24,17,.30)); box-shadow:0 18px 50px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.10); backdrop-filter:blur(18px) saturate(125%); -webkit-backdrop-filter:blur(18px) saturate(125%); }
.hero-kicker { color:#e8c766; font-weight:700; font-size:.82rem; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:.5rem; }
.hero h1 { color:#f8fafc; font-family:'Noto Kufi Arabic',sans-serif; font-size:2rem; font-weight:700; line-height:1.55; margin:0 0 .55rem; letter-spacing:-.4px; }
.hero p { color:#e8dcca; font-size:1.02rem; margin:0; max-width:720px; }
.legal-cover { position:relative; overflow:hidden; max-width:900px; margin:0 auto .85rem; padding:1.35rem 1.5rem 1rem; text-align:center; border:1px solid rgba(255,222,135,.34); border-radius:22px; background:linear-gradient(135deg,rgba(102,63,31,.48),rgba(37,21,15,.60) 55%,rgba(103,69,32,.30)); box-shadow:0 18px 48px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.13); backdrop-filter:blur(22px) saturate(135%); -webkit-backdrop-filter:blur(22px) saturate(135%); }
.legal-cover:before, .legal-cover:after { content:""; position:absolute; width:180px; height:180px; border:1px solid rgba(232,199,102,.13); border-radius:50%; pointer-events:none; }
.legal-cover:before { top:-105px; right:-55px; box-shadow:0 0 0 18px rgba(232,199,102,.04), 0 0 0 36px rgba(232,199,102,.025); }
.legal-cover:after { bottom:-120px; left:-55px; box-shadow:0 0 0 18px rgba(232,199,102,.04), 0 0 0 36px rgba(232,199,102,.025); }
.cover-emblem { position:relative; z-index:1; width:58px; height:58px; display:grid; place-items:center; margin:0 auto .85rem; border:1px solid rgba(255,231,151,.55); border-radius:18px; color:#2b180b; background:linear-gradient(135deg,#f6d978,#ad7b20); font-size:30px; box-shadow:0 12px 28px rgba(212,175,55,.28); }
.cover-kicker { position:relative; z-index:1; color:#e8c766; font-size:.72rem; font-weight:700; letter-spacing:2px; }
.legal-cover h1 { position:relative; z-index:1; margin:.25rem 0 .25rem; color:#fff8e8; font-family:'Noto Kufi Arabic',sans-serif; font-size:1.55rem; font-weight:800; }
.legal-cover p { position:relative; z-index:1; margin:0; color:#e6d7c1; font-size:.95rem; }
.cover-line { position:relative; z-index:1; width:80px; height:2px; margin:1rem auto .7rem; background:linear-gradient(90deg,transparent,#e8c766,transparent); }
.legal-cover span { position:relative; z-index:1; color:#cdb995; font-size:.78rem; }
.admin-panel-title { color:#f4d37c; font-family:'Noto Kufi Arabic',sans-serif; font-weight:700; text-align:center; margin:.4rem 0 .7rem; }
.language-label { color:#cdb995; font-size:.72rem; text-align:center; margin:0 auto .22rem; }
[data-testid="stPopover"] > button { width:40px !important; min-width:40px !important; height:40px !important; min-height:40px !important; padding:0 !important; margin:0 auto !important; border:1px solid rgba(255,222,135,.42) !important; border-radius:50% !important; background:rgba(255,255,255,.06) !important; color:#f4d37c !important; font-size:1.08rem !important; box-shadow:0 8px 20px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(16px); }
[data-testid="stPopover"] { display:flex; justify-content:center; }
[data-testid="stPopoverBody"] { min-width:220px; border:1px solid rgba(255,222,135,.28) !important; border-radius:16px !important; background:rgba(44,26,17,.94) !important; backdrop-filter:blur(20px); }
[data-testid="stPopoverBody"] [data-testid="stRadio"] label { color:#f5ead8 !important; }
.topbar-shell { width:100%; margin:0; padding:0; display:flex; align-items:center; min-height:32px; }
.st-key-lexgo-topbar { position:fixed !important; top:0 !important; right:245px !important; z-index:1001 !important; width:330px !important; max-width:calc(100vw - 270px) !important; margin:0 !important; padding:3px 8px !important; border:1px solid rgba(255,222,135,.25); border-top:0; border-radius:0 0 14px 14px; background:rgba(30,22,18,.62); box-shadow:0 8px 24px rgba(0,0,0,.14), inset 0 1px 0 rgba(255,255,255,.10); backdrop-filter:blur(24px) saturate(145%); -webkit-backdrop-filter:blur(24px) saturate(145%); }
.st-key-lexgo-topbar [data-testid="stHorizontalBlock"] { align-items:center; gap:.45rem; }
.st-key-lexgo-topbar [data-testid="column"] { display:flex; align-items:center; justify-content:center; }
.topbar-brand { color:#f4d37c; font-family:'Noto Kufi Arabic',sans-serif; font-size:.78rem; font-weight:700; text-align:right; padding:.2rem .25rem; white-space:nowrap; letter-spacing:.2px; }
.st-key-lexgo-topbar [data-testid="stPopover"] > button { margin:0 !important; border-radius:10px !important; min-height:30px !important; height:30px !important; }
.topbar-user { color:#eadcc7; font-size:.78rem; text-align:right; padding:.5rem .3rem; white-space:nowrap; }
.topbar-user strong { color:#fff7e6; }
.topbar-avatar { display:inline-grid; place-items:center; width:28px; height:28px; margin-left:.35rem; border-radius:50%; color:#2b180b; background:linear-gradient(135deg,#f6d978,#ad7b20); font-size:.75rem; font-weight:800; vertical-align:middle; }
[data-testid="stVerticalBlock"]:has(.topbar-shell) [data-testid="stPopover"] > button { margin:0 !important; border-radius:10px !important; min-height:30px !important; height:30px !important; }
@media (max-width:640px) {
 .st-key-lexgo-topbar { position:relative !important; top:auto !important; right:auto !important; width:calc(100% - .8rem) !important; max-width:none !important; margin:0 auto .6rem !important; border-top:1px solid rgba(255,222,135,.25); border-radius:14px; }
 .topbar-brand { font-size:.76rem; }
}
.privacy-copy { color:#e6d7c1; font-size:.84rem; line-height:1.9; }
.login-hero { max-width:640px; margin:2.5rem auto 1rem; padding:2rem 1.8rem 1.5rem; text-align:center; border:1px solid rgba(255,222,135,.30); border-radius:26px; background:linear-gradient(145deg,rgba(111,72,38,.42),rgba(42,24,17,.52)); box-shadow:0 24px 70px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(22px); -webkit-backdrop-filter:blur(22px); }
.login-emblem { width:62px; height:62px; display:grid; place-items:center; margin:0 auto .75rem; border-radius:20px; color:#2b180b; background:linear-gradient(135deg,#f6d978,#ad7b20); font-size:32px; box-shadow:0 12px 30px rgba(212,175,55,.28); }
.login-hero h1 { color:#fff8e8; font-family:'Noto Kufi Arabic',sans-serif; font-size:1.75rem; margin:.35rem 0 .45rem; }
.login-hero p { color:#e6d7c1; margin:0 auto; max-width:480px; line-height:1.9; }
.login-value { color:#e8c766; font-size:.78rem; margin-top:.75rem; }
.login-privacy { max-width:640px; margin:.75rem auto; color:#bcae99; text-align:center; font-size:.76rem; line-height:1.8; }
.st-key-signup-action { max-width:360px; margin:.35rem auto 0; text-align:center; }
.signup-prompt { color:#bcae99; font-size:.76rem; text-align:center; margin:.25rem 0 .35rem; }
.st-key-signup-action button { min-height:34px !important; height:34px !important; border:1px solid rgba(255,222,135,.32) !important; border-radius:10px !important; background:rgba(255,255,255,.035) !important; color:#e8c766 !important; font-size:.78rem !important; box-shadow:none !important; }
.chat-empty { max-width:760px; margin:1.2rem auto 1.5rem; padding:1.3rem; text-align:center; border:1px solid rgba(255,222,135,.20); border-radius:20px; background:rgba(255,255,255,.035); backdrop-filter:blur(16px); }
.chat-empty-title { color:#f4d37c; font-family:'Noto Kufi Arabic',sans-serif; font-weight:700; margin-bottom:.45rem; }
.suggestion-pill { display:inline-block; margin:.25rem; padding:.55rem .8rem; border:1px solid rgba(255,222,135,.22); border-radius:999px; color:#e6d7c1; background:rgba(212,175,55,.07); font-size:.78rem; }

.metric-card { padding:1rem 1.1rem; border-radius:16px; border:1px solid rgba(255,222,135,.24); background:rgba(91,55,30,.25); box-shadow:0 10px 28px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); text-align:center; }
.metric-label { color:#cbb998; font-size:.8rem; text-align:center; }
.metric-value { color:#f8fafc; font-size:1.55rem; font-weight:800; margin-top:.2rem; text-align:center; }
.law-card { padding:1.1rem 1.25rem; border:1px solid rgba(255,222,135,.22); border-radius:16px; margin-bottom:.8rem; background:linear-gradient(135deg,rgba(101,61,32,.30),rgba(35,21,15,.28)); box-shadow:0 10px 28px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(15px); -webkit-backdrop-filter:blur(15px); text-align:center; }
.source-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.45rem; margin:.55rem 0 .85rem; }
.source-field { padding:.5rem .35rem; border:1px solid rgba(255,222,135,.14); border-radius:10px; background:rgba(255,255,255,.035); text-align:center; }
.source-field small { display:block; color:#bcae99; font-size:.68rem; }
.source-field strong { display:block; color:#f4d37c; font-size:.82rem; margin-top:.15rem; }
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
.chat-row { max-width:860px; margin:1.05rem auto 1.45rem; text-align:right; }
.chat-row.user { text-align:right; }
.chat-row.assistant { text-align:left; }
.chat-meta { display:flex; justify-content:flex-start; align-items:center; gap:.55rem; color:#d8bb6a; font-family:'Noto Kufi Arabic',sans-serif; font-size:.76rem; font-weight:600; margin-bottom:.65rem; }
.chat-avatar { width:30px; height:30px; display:inline-grid; place-items:center; border-radius:50%; color:#28170d; background:linear-gradient(135deg,#f5d77c,#a6781f); box-shadow:0 6px 16px rgba(212,175,55,.2); }
.chat-text { display:inline-block; max-width:86%; color:#f5ead8; font-size:1.02rem; line-height:2.05; padding:.85rem 1rem; border:1px solid rgba(212,175,55,.22); border-radius:18px; background:rgba(255,255,255,.045); box-shadow:0 10px 28px rgba(0,0,0,.13), inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(14px); text-align:right; }
.chat-row.user .chat-meta { color:#b8a58d; }
.chat-row.user .chat-avatar { background:rgba(212,175,55,.16); color:#f4d37c; box-shadow:none; }
.chat-row.user .chat-text { color:#eadcc7; font-size:.98rem; border-color:rgba(212,175,55,.18); background:rgba(91,55,30,.34); }
.chat-row.assistant .chat-text { margin-left:0; }
.legal-inline { margin-top:1rem; padding:.65rem .9rem; border-right:3px solid #d4af37; border-radius:10px; background:rgba(212,175,55,.08); color:#d9cbb7; font-size:.86rem; line-height:1.9; text-align:right; }
</style>""", unsafe_allow_html=True)

BACKGROUND_PATH = APP_ROOT / "assets" / "legal-library-background.jpg"
if BACKGROUND_PATH.exists():
    background_source = f"url(\"data:image/jpeg;base64,{base64.b64encode(BACKGROUND_PATH.read_bytes()).decode('ascii')}\")"
else:
    # Fallback for deployments where the assets directory was not committed.
    background_source = 'url("https://i.pinimg.com/736x/ed/f1/21/edf121540936156cf73f74e6a08e4440.jpg")'
st.markdown(f"""<style>
    .stApp {{
        background-image: linear-gradient(rgba(23,14,10,.84), rgba(23,14,10,.90)), {background_source};
        background-size: 100% 100%;
        background-position: center center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-color: #170e0a;
        min-height: 100vh;
    }}
    @media (max-width: 768px) {{
        .stApp {{
            background-size: cover;
            background-position: center top;
        }}
    }}
    header[data-testid="stHeader"], footer {{ background: transparent !important; }}
</style>""", unsafe_allow_html=True)

# موسيقى الخلفية: أيقونة سماعة عائمة (مرر الماوس لمستوى الصوت، اضغط للكتم)
# إن لم تعمل الموسيقى بالرابط القصير، افتح المقطع في المتصفح وانسخ الرابط الكامل (soundcloud.com/artist/track)
MUSIC_TRACK_URL = os.getenv("LEXA_MUSIC_URL", "https://soundcloud.com/hossam-sukar/omar-khairat-the-case-of-am").strip()
if MUSIC_TRACK_URL:
    add_background_music(MUSIC_TRACK_URL, position="bottom", side="left", volume=30, offset=96)


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _users() -> list[dict]:
    users = []
    raw = _secret("USERS_JSON")
    if raw:
        try:
            parsed_users = json.loads(raw)
            if isinstance(parsed_users, list):
                users = parsed_users
        except json.JSONDecodeError:
            pass
    admin_user = _secret("ADMIN_USERNAME")
    admin_password_hash = _secret("ADMIN_PASSWORD_HASH")
    admin_password = _secret("ADMIN_PASSWORD")
    if admin_user and (admin_password_hash or admin_password):
        users.append({"username": admin_user, "password_hash": admin_password_hash, "password": admin_password, "role": "admin"})
    if storage_configured():
        try:
            users.extend(load_persisted_users())
        except Exception:
            pass
    return users


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
    st.markdown('<div class="login-hero"><div class="login-emblem">⚖</div><div class="hero-kicker">LEXGO · LEGAL CHAT</div><h1>مرحبًا بك في LexGO</h1><p>مستشارك الذكي للبحث والمحادثة داخل مكتبة التشريعات الخاصة بك.</p><div class="login-value">إجابات موثقة · خصوصية الجلسة · وصول آمن</div></div>', unsafe_allow_html=True)
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
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False
    with st.container(key="signup-action"):
        st.markdown('<div class="signup-prompt">ليس لديك حساب؟</div>', unsafe_allow_html=True)
        if st.button("إنشاء حساب جديد", key="signup_toggle", use_container_width=True):
            st.session_state.show_signup = not st.session_state.show_signup
            st.rerun()
    if st.session_state.show_signup:
        st.markdown('<div class="chat-intro">إنشاء الحساب متاح للمستخدم العادي فقط. صلاحية المدير تُدار من إعدادات النظام.</div>', unsafe_allow_html=True)
        with st.form("signup_form"):
            new_username = st.text_input("اسم المستخدم الجديد")
            new_password = st.text_input("كلمة المرور الجديدة", type="password")
            confirm_password = st.text_input("تأكيد كلمة المرور", type="password")
            signup_submitted = st.form_submit_button("إنشاء الحساب", type="primary", use_container_width=True)
            if signup_submitted:
                clean_username = new_username.strip()
                if not storage_configured():
                    st.error("إنشاء الحساب يحتاج اتصال قاعدة البيانات الدائمة. أضف إعدادات Supabase أولًا.")
                elif len(clean_username) < 3 or len(clean_username) > 40:
                    st.error("اسم المستخدم يجب أن يكون بين 3 و40 حرفًا.")
                elif len(new_password) < 8:
                    st.error("كلمة المرور يجب أن تكون 8 أحرف على الأقل.")
                elif new_password != confirm_password:
                    st.error("تأكيد كلمة المرور غير مطابق.")
                elif any(str(user.get("username", "")).casefold() == clean_username.casefold() for user in configured_users):
                    st.error("اسم المستخدم مستخدم بالفعل. اختر اسمًا آخر.")
                elif create_persisted_user(clean_username, hash_password(new_password), "user"):
                    st.session_state.auth_user = {"username": clean_username, "role": "user"}
                    st.session_state.show_signup = False
                    st.rerun()
                else:
                    st.error("تعذر إنشاء الحساب حاليًا. حاول مرة أخرى.")
    st.markdown('<div class="login-privacy">الدخول كضيف يتيح الشات والبحث فقط. لا يستطيع الضيف رفع الملفات أو الوصول إلى الإدارة، ولا تُحفظ ذاكرة محادثته المؤقتة كقوانين.</div>', unsafe_allow_html=True)
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


def llm_failed(answer: str) -> bool:
    return answer in {
        "تعذر تشغيل خدمة الإجابة الذكية حاليًا. حاول مرة أخرى لاحقًا.",
        "The smart answer service is currently unavailable. Please try again later.",
        "Le service de réponse intelligente est momentanément indisponible. Veuillez réessayer plus tard.",
    }

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
    if not key:
        return service_error_message()
    model_name = _secret("GEMINI_MODEL", "gemini-flash-latest").strip()
    if model_name.startswith("models/"):
        model_name = model_name[7:]
    model_name = model_name.split(":", 1)[0]
    model_name = {
        "gemini-2.0-flash": "gemini-flash-latest",
        "gemini-2.5-flash": "gemini-flash-latest",
        "gemini-2.5-flash-latest": "gemini-flash-latest",
        "gemini-3.8-flash": "gemini-flash-latest",
    }.get(model_name, model_name)
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model_name, safe='')}:generateContent?key={urllib.parse.quote(key, safe='')}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]} if system_prompt else None,
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 700},
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            # Recover silently when a configured model is retired or unavailable.
            try:
                models_url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + urllib.parse.quote(key, safe="")
                with urllib.request.urlopen(models_url, timeout=30) as models_response:
                    models_data = json.loads(models_response.read().decode("utf-8"))
                available = [
                    item.get("name", "").replace("models/", "")
                    for item in models_data.get("models", [])
                    if "generateContent" in item.get("supportedGenerationMethods", [])
                ]
                preferred = next((name for name in ("gemini-flash-latest", "gemini-3-flash-preview", "gemini-2.5-flash") if name in available), None)
                if preferred and preferred != model_name:
                    retry_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(preferred, safe='')}:generateContent?key={urllib.parse.quote(key, safe='')}"
                    retry_request = urllib.request.Request(retry_endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(retry_request, timeout=25) as response:
                        retry_data = json.loads(response.read().decode("utf-8"))
                    return retry_data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass
            return service_error_message()
        if exc.code in {408, 429, 500, 502, 503, 504}:
            time.sleep(.35)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    retry_data = json.loads(response.read().decode("utf-8"))
                return retry_data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass
            return service_error_message()
        return service_error_message()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return service_error_message()


def ask_llm(question: str, results: list[dict]) -> str:
    source_only = "\n\n".join(
        f"**المادة {r.get('article_number')}**:\n{r.get('text')}"
        for r in results[:3]
    )
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
        return source_only
    context = "\n\n".join(
        f"[مصدر {i}] القانون رقم {r.get('law_number')} لسنة {r.get('law_year')}، المادة {r.get('article_number')}، الفقرة {r.get('paragraph_number')}، البند {r.get('clause_number')}، الصفحة {r.get('page_start')}\n{r.get('text')}"
        for i, r in enumerate(results, 1)
    )
    selected_language = LANGUAGES.get(st.session_state.get("response_language", "ar"), LANGUAGES["ar"])
    system_prompt = f"أنت مساعد بحث قانوني. أجب من النصوص المسترجعة فقط. ابدأ بخلاصة مفهومة بلغة بسيطة للمستخدم، ولا تكتفِ بعبارة مثل (تنص المادة) دون شرح مختصر لمعناها. استخدم نقاطًا قصيرة إذا كان النص يحتوي على عناصر متعددة. لا تعِد كتابة النص الكامل؛ سيعرضه التطبيق بعد خلاصة الإجابة. اذكر رقم القانون والسنة والمادة والفقرة والبند والصفحة عند توفرها. لا تستنتج معلومة غير موجودة ولا تقدم رأيًا قانونيًا شخصيًا. إذا لم تكفِ المصادر قل ذلك بوضوح. {selected_language['instruction']}"
    user_prompt = f"السؤال: {question}\n\nالمصادر:\n{context}"
    if gemini_key:
        answer = call_gemini(user_prompt, system_prompt)
        return source_only if llm_failed(answer) else answer
    if openai_key:
        model_name = secret("OPENAI_MODEL", "gpt-4o-mini")
        client = OpenAI(api_key=openai_key, timeout=25)
    else:
        model_name = secret("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key, timeout=25)
    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=700,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = response.choices[0].message.content or service_error_message()
        return source_only if llm_failed(answer) else answer
    except Exception:
        return source_only


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


def is_library_question(question: str) -> bool:
    normalized = (question or "").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    markers = (
        "مدرب على اي قانون", "مدرب على أي قانون", "بتعرف اي قوانين", "بتعرف أي قوانين",
        "القوانين الموجودة", "القوانين المتاحة", "الملفات الموجودة", "المصادر الموجودة",
        "ما هي القوانين", "ما القوانين", "ايه القوانين", "إيه القوانين",
    )
    return any(marker.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا") in normalized for marker in markers)


def library_answer(available_laws: list[dict]) -> str:
    if not available_laws:
        return "حاليًا لا توجد قوانين مفهرسة في قاعدة البيانات. اطلب من المدير رفع ملف قانوني أولًا."
    items = []
    for law in available_laws:
        title = str(law.get("title") or law.get("file_name") or "قانون غير مسمى")
        number = law.get("law_number")
        year = law.get("law_year")
        reference = f"القانون رقم {number} لسنة {year}" if number and year else "بيانات الرقم والسنة غير مستخرجة بالكامل"
        items.append(f"- **{title}** — {reference} ({law.get('article_count', 0)} مادة مفهرسة)")
    return "أنا لا أُدرَّب مسبقًا على قوانين عامة من خارج النظام؛ أنا أبحث فقط في القوانين التي رفعها المدير وحُفظت في قاعدة البيانات.\n\nالقوانين المتاحة حاليًا:\n" + "\n".join(items) + "\n\nيمكنك أن تسأل مثلًا: ما نص المادة 1 من القانون المدني؟"


def classify_question(question: str) -> str:
    """Let the configured LLM route the question without giving it legal data."""
    quick_filters = query_filters(question)
    if is_legal_question(question):
        return "legal_clarify" if needs_legal_clarification(question, quick_filters) else "legal_specific"
    if any(word in question.casefold() for word in ("شكرا", "شكرًا", "مشكور", "السلام", "مرحبا", "مرحبًا", "أهلا", "أهلًا", "hello", "hi", "merci", "bonjour")):
        return "general"
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
                    client = OpenAI(api_key=key, timeout=12)
                    model = _secret("OPENAI_MODEL", "gpt-4o-mini")
                else:
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=router_key, timeout=12)
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
api_provider = next((name for name in ("Gemini", "OpenAI", "OpenRouter") if _secret(f"{name.upper()}_API_KEY")), "")
api_key_ready = bool(api_provider)


# Compact glass header: app identity and account menu share one row.
with st.container(key="lexgo-topbar"):
    brand_col, menu_col = st.columns([8, 1], vertical_alignment="center")
    with brand_col:
        st.markdown('<div class="topbar-shell"><div class="topbar-brand">LEXGO · LEGAL CHAT</div></div>', unsafe_allow_html=True)
    with menu_col:
        with st.popover("👤", help="الحساب والإعدادات"):
            username = html.escape(str(current_user.get("username", "ضيف")))
            role_label = "مدير" if is_admin else ("ضيف" if is_guest else "مستخدم")
            initial = html.escape(username[:1] or "؟")
            st.markdown(f'<div class="topbar-user"><span class="topbar-avatar">{initial}</span><strong>{username}</strong><br><small>الصلاحية: {role_label}</small></div>', unsafe_allow_html=True)
            st.divider()
            st.markdown("**لغة الإجابة**")
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
            st.divider()
            st.markdown("**الإعدادات**")
            st.caption("ذاكرة المحادثة مؤقتة لهذه الجلسة فقط.")
            st.caption("القوانين محفوظة في قاعدة البيانات الدائمة.")
            st.markdown("**سياسة الخصوصية**")
            st.markdown('<div class="privacy-copy">تُستخدم الأسئلة داخل جلسة المحادثة لتقديم الإجابة وتحسين سياق الحوار. لا تُحفظ ذاكرة الشات المؤقتة كقوانين في قاعدة البيانات. الملفات القانونية يحفظها المدير في مكتبة النظام الدائمة.</div>', unsafe_allow_html=True)
            if is_admin:
                st.divider()
                st.markdown("**إدارة القوانين**")
                st.caption("رفع الملفات متاح للمدير فقط، ويتم الحفظ في قاعدة البيانات الدائمة.")
                if not storage_configured():
                    st.error("قاعدة البيانات الدائمة غير متصلة. أضف إعدادات Supabase أولًا.")
                    uploaded = None
                else:
                    uploaded = st.file_uploader("رفع قانون PDF أو DOC أو DOCX", type=["pdf", "doc", "docx"], key="account_law_uploader")
                if uploaded is not None and storage_configured():
                    target = DATA_DIR / uploaded.name
                    incoming = uploaded.getvalue()
                    document_id = "doc_" + hashlib.sha256(incoming).hexdigest()[:16]
                    same_file = target.exists() and target.read_bytes() == incoming
                    try:
                        already_stored = remote_document_exists(document_id)
                    except Exception:
                        already_stored = False
                    if same_file or already_stored:
                        st.info("هذا الملف محفوظ بالفعل في مكتبة القوانين وجاهز للبحث. لم تتم إضافته مرة أخرى.")
                    else:
                        write_ok = True
                        try:
                            target.write_bytes(incoming)
                        except Exception as exc:
                            write_ok = False
                            if target.exists():
                                target.unlink()
                            st.error("تعذر حفظ الملف المرفوع مؤقتًا على الخادم.")
                            with st.expander("تفاصيل التشخيص للمدير"):
                                st.code(f"{type(exc).__name__}: {exc}")
                        law = None
                        law_rows = []
                        if write_ok:
                            try:
                                with st.spinner("جاري قراءة الملف وتحليل القانون وفهرسته..."):
                                    law, law_rows = ingest_file(target, PARSED_DIR)
                            except Exception as exc:
                                if target.exists():
                                    target.unlink()
                                st.error("تم رفع الملف، لكن تعذر قراءة محتواه. تأكد أنه PDF أو DOC أو DOCX سليم.")
                                with st.expander("تفاصيل التشخيص للمدير"):
                                    st.code(f"{type(exc).__name__}: {exc}")
                        if law is not None:
                            try:
                                with st.spinner("جاري حفظ القانون في قاعدة البيانات الدائمة..."):
                                    save_document(law, law_rows)
                                invalidate()
                                st.success(f"تم الحفظ والفهرسة: {law.get('article_count', 0)} مادة و{len(law_rows)} مقطع")
                                st.rerun()
                            except Exception as exc:
                                if target.exists():
                                    target.unlink()
                                st.error("تمت قراءة الملف، لكن فشل حفظه في Supabase. راجع مفتاح service_role وصلاحيات Data API.")
                                with st.expander("تفاصيل التشخيص للمدير"):
                                    st.code(f"{type(exc).__name__}: {exc}")
                st.caption(f"التخزين: {'قاعدة بيانات دائمة' if storage_configured() else 'غير متصل'}")
                if st.button("اختبار اتصال قاعدة البيانات", key="account_test_supabase", use_container_width=True):
                    try:
                        remote_count = len(load_remote_rows())
                        st.success(f"اتصال Supabase يعمل. عدد المقاطع المحفوظة: {remote_count}")
                    except Exception as exc:
                        st.error("الاتصال موجود لكن Supabase رفض الطلب. راجع service_role key واسم الجداول.")
                        with st.expander("تفاصيل التشخيص للمدير"):
                            st.code(f"{type(exc).__name__}: {exc}")
                st.caption(f"API: {api_provider + ' متصل' if api_key_ready else 'غير مضاف'}")
                st.caption(f"نموذج Gemini: {_secret('GEMINI_MODEL', 'gemini-flash-latest')}")
                if st.button("اختبار اتصال Gemini", key="account_test_gemini", use_container_width=True):
                    with st.spinner("جاري اختبار Gemini..."):
                        gemini_test = call_gemini("Reply with exactly: OK", "Reply with exactly one word: OK")
                    if not llm_failed(gemini_test) and gemini_test.strip().upper() == "OK":
                        st.success("اتصال Gemini يعمل.")
                    else:
                        st.error("تعذر اتصال Gemini. راجع GEMINI_API_KEY وGEMINI_MODEL في Secrets.")
            if st.button("مسح المحادثة", key="account_clear_chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
            if st.button("تسجيل الخروج", key="account_logout", use_container_width=True):
                st.session_state.auth_user = None
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
    
st.markdown(f'<div class="section-title" style="text-align:center">{html.escape(ui_text("chat_title"))}</div><div class="chat-intro">{html.escape(ui_text("chat_intro"))}</div>', unsafe_allow_html=True)
_new_chat_left, new_chat, _new_chat_right = st.columns([2, 1, 2])
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
    if filters.get("paragraph_number") is not None:
        article_rows = [
            row for row in article_rows
            if str(row.get("paragraph_number", "")) == str(filters["paragraph_number"])
        ]
    if filters.get("clause_number") is not None:
        article_rows = [
            row for row in article_rows
            if str(row.get("clause_number", "")) == str(filters["clause_number"])
        ]
    def hierarchy_sort_key(row: dict) -> tuple:
        values = []
        for key in ("paragraph_number", "clause_number"):
            try:
                values.append(int(row.get(key) or 0))
            except (TypeError, ValueError):
                values.append(999)
        return tuple(values)
    article_rows.sort(key=hierarchy_sort_key)
    if article_rows:
        merged = dict(top)
        merged["text"] = "\n\n".join(str(row.get("text", "")).strip() for row in article_rows if row.get("text"))
        merged["paragraph_number"] = filters.get("paragraph_number", "كاملة")
        merged["clause_number"] = filters.get("clause_number", "كاملة")
        return [merged]
    return []


def format_legal_answer(answer: str, question: str, results: list[dict]) -> str:
    """Present the authoritative retrieved article in a readable chat layout."""
    answer = (answer or "").strip()
    filters = query_filters(question)
    if not results or not filters.get("article_number"):
        return answer
    full_text = str(results[0].get("text") or "").strip()
    if not full_text:
        return answer
    # For an explicit article-text request, never let an LLM summarize or omit
    # wording. The database text is shown verbatim, with blank lines separating
    # the indexed paragraphs/chunks for easier reading.
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    hierarchy = [f"المادة {filters['article_number']}"]
    if filters.get("paragraph_number") is not None:
        hierarchy.append(f"الفقرة {filters['paragraph_number']}")
    if filters.get("clause_number") is not None:
        hierarchy.append(f"البند {filters['clause_number']}")
    return f"**النص المطلوب: {' · '.join(hierarchy)}**\n\n{full_text}"


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
            with st.expander(f"المادة {result.get('article_number') or '؟'}  ·  المرجع {i}"):
                st.markdown(f'''<div class="law-card"><div class="source-grid">
                    <div class="source-field"><small>القانون</small><strong>{html.escape(str(result.get("law_number") or "؟"))}</strong></div>
                    <div class="source-field"><small>السنة</small><strong>{html.escape(str(result.get("law_year") or "؟"))}</strong></div>
                    <div class="source-field"><small>المادة</small><strong>{html.escape(str(result.get("article_number") or "؟"))}</strong></div>
                    <div class="source-field"><small>الفقرة</small><strong>{html.escape(str(result.get("paragraph_number") or "؟"))}</strong></div>
                    <div class="source-field"><small>البند</small><strong>{html.escape(str(result.get("clause_number") or "؟"))}</strong></div>
                    <div class="source-field"><small>الصفحة</small><strong>{html.escape(str(result.get("page_start") or "؟"))}</strong></div>
                </div><div class="source-chip">المصدر: مكتبة القوانين المحفوظة</div></div>''', unsafe_allow_html=True)

if not st.session_state.chat_history:
    st.markdown('<div class="chat-empty"><div class="chat-empty-title">كيف يمكنني مساعدتك؟</div><div style="color:#d9cbb7;font-size:.86rem;line-height:1.8">اسأل عن نص مادة، رقم قانون، فقرة أو بند داخل الملفات المرفوعة.</div><div style="margin-top:.6rem"><span class="suggestion-pill">ما نص المادة 29 من القانون المدني؟</span><span class="suggestion-pill">اعرض الفقرات والبنود داخل المادة</span><span class="suggestion-pill">هل توجد هذه المعلومة في الملفات؟</span></div></div>', unsafe_allow_html=True)

question = st.chat_input(ui_text("input"))
if question:
    if is_guest and not guest_request_allowed():
        st.warning("تم الوصول إلى الحد المؤقت للضيف (20 سؤالًا في الدقيقة). يرجى الانتظار قليلًا ثم المحاولة مرة أخرى.")
        st.stop()
    filters = query_filters(question)
    if is_library_question(question):
        primary_results = []
        answer = library_answer(laws)
        legal_query = False
        intent = "general"
    else:
        # Source-first pipeline: retrieve from the user's indexed database before any LLM call.
        pre_results = verified_search(question)
        intent = classify_question(question)
        legal_query = intent in {"legal_specific", "legal_clarify"}
    with st.spinner("جاري البحث في المواد القانونية..."):
        if is_library_question(question):
            pass
        elif intent == "legal_clarify":
            primary_results = []
            answer = localized_message("clarify")
        elif intent == "legal_specific":
            primary_results = complete_article_result(question, pre_results)
            if primary_results:
                if filters.get("article_number"):
                    # Exact article requests are answered directly from Supabase.
                    answer = format_legal_answer("", question, primary_results)
                else:
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
