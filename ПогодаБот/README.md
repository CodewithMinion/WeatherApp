## ПогодаБот — Telegram Web App (Нижневартовск)

Бот открывает встроенное мини‑приложение в Telegram, где:
- показывается **актуальная погода** в Нижневартовске
- ниже кнопка **«Показать прогноз на месяц»** (фактически — **на максимальный доступный период** у бесплатного API, обычно 7–10 дней)

Источник погоды: **api.met.no** (Meteorologisk institutt, Norway) — бесплатно, без регистрации и API‑ключа.

### Установка

```powershell
cd "c:\Users\tmini\Desktop\ПогодаБот"
pip install -r requirements.txt
```

Создай `.env` (можно скопировать `.env.example`) и укажи:
- `BOT_TOKEN` — токен от `@BotFather`
- `WEBAPP_URL` — публичный **HTTPS** URL твоего WebApp

### Запуск WebApp (локально)

```powershell
cd "c:\Users\tmini\Desktop\ПогодаБот"
uvicorn webapp:app --host 127.0.0.1 --port 8000
```

Открыть в браузере: `http://127.0.0.1:8000/`

### Сделать публичный HTTPS URL (пример через ngrok)

1) Установи ngrok и залогинься (как у них в инструкции).

2) Запусти туннель на порт 8000:

```powershell
ngrok http 8000
```

3) Возьми выданный `https://...ngrok...` и запиши в `.env` как `WEBAPP_URL`.

### Запуск бота

```powershell
cd "c:\Users\tmini\Desktop\ПогодаБот"
python bot.py
```

В Telegram:
- `/start` — присылает кнопку открытия WebApp
- `/app` — то же самое
- `/weather` — отправляет текущую погоду текстом (на всякий случай)

