## ПогодаБот — Telegram Web App (Нижневартовск)

Бот открывает встроенное мини‑приложение в Telegram, где:
- показывается **актуальная погода** в Нижневартовске
- ниже кнопка **«Показать прогноз на месяц»** (фактически — **на максимальный доступный период** у бесплатного API, обычно 7–10 дней)

Источник погоды: **api.met.no** (Meteorologisk institutt, Norway) — бесплатно, без регистрации и API‑ключа.

### Как это работает на GitHub Pages

- WebApp лежит в папке `docs/` (это и есть GitHub Pages сайт).
- Данные погоды лежат в `docs/data/current.json` и `docs/data/forecast.json`.
- GitHub Actions (`.github/workflows/update-weather.yml`) каждые 30 минут обновляет эти JSON, подтягивая данные с `api.met.no`.

Так WebApp всегда доступен по **публичному HTTPS** от GitHub Pages и не требует своего сервера.

### Установка (для запуска бота локально)

```powershell
cd "c:\Users\tmini\Desktop\ПогодаБот"
pip install -r requirements.txt
```

Создай `.env` (можно скопировать `.env.example`) и укажи:
- `BOT_TOKEN` — токен от `@BotFather`
- `WEBAPP_URL` — публичный **HTTPS** URL твоего GitHub Pages (например `https://<user>.github.io/<repo>/`)

### Включить GitHub Pages

1) Залей проект в GitHub репозиторий.
2) `Settings → Pages`
3) `Build and deployment → Source: Deploy from a branch`
4) `Branch: main`, `Folder: /docs`
5) Сохрани — появится HTTPS адрес Pages.

### Включить авто‑обновление данных

GitHub Actions уже добавлен. После первого пуша:
- открой вкладку `Actions`
- запусти workflow `Update weather data` вручную (кнопка `Run workflow`), чтобы данные сразу появились

Опционально: чтобы `api.met.no` видел корректный User‑Agent, в репозитории можно добавить переменную:
`Settings → Secrets and variables → Actions → Variables → New repository variable`
и создать `MET_USER_AGENT`.

### Запуск бота

```powershell
cd "c:\Users\tmini\Desktop\ПогодаБот"
python bot.py
```

В Telegram:
- `/start` — присылает кнопку открытия WebApp
- `/app` — то же самое
- `/weather` — отправляет текущую погоду текстом (на всякий случай)

