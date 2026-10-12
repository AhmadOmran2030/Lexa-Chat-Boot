# تشغيل LexGO كموقع محلي دائم

هذه النسخة لا تعتمد على استضافة Manus. شغّلها على جهاز أو VPS يظل متصلًا.

## الطريقة الموصى بها: Docker

المتطلبات:

- Docker
- Docker Compose
- منفذ 8501 مفتوح إذا كان الموقع سيُستخدم خارج الجهاز

الأوامر:

```bash
cp .env.example .env
# اختياري: ضع OPENROUTER_API_KEY داخل .env
docker compose up -d --build
```

افتح:

```text
http://SERVER_IP:8501
```

الملفات المرفوعة محفوظة دائمًا في `data/`، ونتائج التحليل في `parsed_laws/`. إعادة تشغيل الحاوية لا تحذفها.

لرؤية السجل:

```bash
docker compose logs -f lexgo
```

لإيقاف الموقع:

```bash
docker compose down
```

## بدون Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.fileWatcherType none
```

للتشغيل التلقائي بعد إعادة تشغيل Linux، استخدم systemd أو شغّل Docker Compose مع `restart: unless-stopped`.

## ملاحظة أمنية

لا تفتح المنفذ مباشرة على الإنترنت في بيئة إنتاجية بدون Reverse Proxy مثل Nginx مع HTTPS، ولا تضع مفتاح OpenRouter داخل Git.
