# نشر LexGO على Streamlit Community Cloud

## 1. ارفع المشروع إلى GitHub

يجب أن يحتوي المستودع على:

- `streamlit_app.py`
- `requirements.txt`
- `packages.txt`
- `.streamlit/config.toml`
- `legal_parser.py`
- `ingestion.py`
- `rag_engine.py`
- `persistence.py`
- `supabase_schema.sql`

## 2. أنشئ التطبيق

من Streamlit Community Cloud اختر:

- Repository: مستودع GitHub
- Branch: `main`
- Main file path: `streamlit_app.py`

## 3. أضف Secrets

من إعدادات التطبيق أضف:

```toml
OPENAI_API_KEY = "sk-your-openai-key"
OPENAI_MODEL = "gpt-4o-mini"
```

لاستخدام Gemini، أضف `GEMINI_API_KEY` مع نموذج `gemini-3.8-flash`. نموذج `gemini-2.0-flash` لم يعد متاحًا حسب رد Google. ضع المفتاح في خانة Secrets فقط. لا تضعه داخل `streamlit_app.py` ولا ترفعه إلى GitHub، ولا ترسله في المحادثة.

```toml
GEMINI_API_KEY = "AIza..."
GEMINI_MODEL = "gemini-3.8-flash"
```

بعد تسجيل الدخول كـAdmin سيظهر زر `اختبار Gemini API`. استخدمه لمعرفة هل المشكلة من المفتاح أو من اسم النموذج أو من صلاحية الحساب، وستظهر تفاصيل رد Google إذا كان الطلب مرفوضًا.

اكتب اسم النموذج بدون `models/` وبدون `:latest`، مثل:

```toml
GEMINI_MODEL = "gemini-3.8-flash"
```

إذا ظهر 404 بعد تحديث التطبيق، استخدم زر الاختبار؛ سيعرض التطبيق أسماء نماذج Gemini المتاحة لمفتاحك.

## 4. تفعيل حفظ الملفات بعد التحديثات

Streamlit Cloud لا يحفظ مجلد `data/` بشكل دائم. استخدم Supabase:

1. أنشئ مشروعًا في Supabase.
2. افتح SQL Editor والصق محتوى `supabase_schema.sql` ثم نفّذه.
3. من Project Settings > API انسخ Project URL وService Role Key.
4. أضفهما إلى Streamlit Secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ضع-كلمة-مرور-قوية"
# أو عدة مستخدمين:
# USERS_JSON = '[{"username":"admin","password":"...","role":"admin"},{"username":"reader","password":"...","role":"user"}]'
```

بعد ذلك ستظهر حالة `التخزين: قاعدة بيانات دائمة`. أي ملف جديد ترفعه الـAdmin سيُحفظ في Supabase، وسيُعاد تحميله تلقائيًا بعد Reboot أو أي تحديث للكود.

## الصلاحيات

- `role = "admin"`: يستطيع رفع وإضافة القوانين.
- `role = "user"`: يستطيع استخدام الشات والبحث فقط، ولا يرى زر رفع الملفات.
- إذا لم تضف إعدادات المستخدمين، يعمل التطبيق في وضع الضيف للتجربة؛ فعّل `ADMIN_USERNAME` و`ADMIN_PASSWORD` قبل النشر العام.

لا تضع `SUPABASE_SERVICE_ROLE_KEY` في GitHub أو في كود الواجهة.

يدعم التطبيق أيضًا `OPENAI_API_KEY` و`OPENROUTER_API_KEY` كبدائل، لكن إذا وُجد مفتاح Gemini فسيستخدمه أولًا.

بعد الحفظ أعد تشغيل التطبيق. ستظهر في الشريط الجانبي حالة `Gemini متصل` وحالة `التخزين: قاعدة بيانات دائمة`. إذا لم تضف مفتاح Gemini، سيظل البحث يعمل وسيعرض النصوص القانونية والمصادر بدون توليد إجابة.

## 4. ملاحظة مهمة عن الملفات

Streamlit Community Cloud مناسب للتجربة والمشاركة، لكن الملفات التي يرفعها المستخدم داخل `data/` ليست تخزينًا دائمًا مضمونًا. قد تختفي عند إعادة تشغيل التطبيق أو إعادة نشره.

للحفظ الدائم استخدم أحد الحلول التالية:

- قاعدة بيانات أو Object Storage خارجي.
- GitHub لا يصلح لتخزين ملفات المستخدمين تلقائيًا في الإنتاج.
- تشغيل Streamlit على VPS أو جهاز دائم باستخدام Docker، كما هو موضح في `DEPLOY_LOCAL.md`.

## تشغيل محلي بنفس إعدادات Streamlit Cloud

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
