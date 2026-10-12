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

## 2. أنشئ التطبيق

من Streamlit Community Cloud اختر:

- Repository: مستودع GitHub
- Branch: `main`
- Main file path: `streamlit_app.py`

## 3. أضف Secrets

من إعدادات التطبيق أضف:

```toml
OPENROUTER_API_KEY = "your_key"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
```

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
