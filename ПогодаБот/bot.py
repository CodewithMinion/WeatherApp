"""
Telegram-бот погоды для Нижневартовска.
Данные: API Norwegian Meteorological Institute (api.met.no) — бесплатно, без ключа и регистрации.
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# Нижневартовск
LAT = 60.9394
LON = 76.5692
CITY = "Нижневартовск"
TZ = ZoneInfo("Asia/Yekaterinburg")

MET_URL = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
# Met.no требует идентифицирующий User-Agent (без регистрации)
USER_AGENT = os.environ.get(
    "MET_USER_AGENT",
    "NizhnevartovskWeatherBot/1.0 (+https://github.com/)",
)

WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip()

SYMBOL_RU: dict[str, str] = {
    "clearsky": "ясно",
    "fair": "малооблачно",
    "partlycloudy": "переменная облачность",
    "cloudy": "облачно",
    "fog": "туман",
    "lightrain": "небольшой дождь",
    "rain": "дождь",
    "heavyrain": "сильный дождь",
    "lightrainandthunder": "небольшой дождь, гроза",
    "rainandthunder": "дождь, гроза",
    "heavyrainandthunder": "сильный дождь, гроза",
    "lightsleet": "небольшой мокрый снег",
    "sleet": "мокрый снег",
    "heavysleet": "сильный мокрый снег",
    "lightsnow": "небольшой снег",
    "snow": "снег",
    "heavysnow": "сильный снег",
    "lightrainshowers": "небольшие ливни",
    "rainshowers": "ливни",
    "heavyrainshowers": "сильные ливни",
    "lightssleetshowers": "небольшой мокрый снег",
    "ssleetshowers": "мокрый снег",
    "heavysleetshowers": "сильный мокрый снег",
    "lightssnowshowers": "небольшой снегопад",
    "ssnowshowers": "снегопад",
    "heavysnowshowers": "сильный снегопад",
}


def symbol_to_ru(code: str | None) -> str:
    if not code:
        return "—"
    base = re.sub(r"_(day|night|polartwilight)$", "", code)
    return SYMBOL_RU.get(base, base.replace("_", " "))


def wind_dir_ru(deg: float | None) -> str:
    if deg is None:
        return "—"
    dirs = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    idx = int((deg + 22.5) // 45) % 8
    return dirs[idx]


async def fetch_met_json() -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            MET_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()


def webapp_keyboard() -> InlineKeyboardMarkup:
    if not WEBAPP_URL:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("⚠️ WebApp URL не настроен", callback_data="noop")]]
        )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌤 Открыть погоду",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


def format_current(data: dict) -> str:
    ts = data["properties"]["timeseries"]
    if not ts:
        return "Нет данных о погоде."
    first = ts[0]
    inst = first["data"]["instant"]["details"]
    t = inst.get("air_temperature")
    hum = inst.get("relative_humidity")
    wind = inst.get("wind_speed")
    wdir = inst.get("wind_from_direction")
    pressure = inst.get("air_pressure_at_sea_level")

    sym = None
    for key in ("next_1_hours", "next_6_hours", "next_12_hours"):
        block = first["data"].get(key)
        if block and block.get("summary"):
            sym = block["summary"].get("symbol_code")
            break

    lines = [
        f"🌤 <b>{CITY}</b> — сейчас",
        "",
        f"🌡 Температура: <b>{t:.0f}°C</b>" if t is not None else "🌡 Температура: —",
        f"💧 Влажность: {hum:.0f}%" if hum is not None else "💧 Влажность: —",
        f"💨 Ветер: {wind:.0f} м/с, {wind_dir_ru(wdir)}" if wind is not None else "💨 Ветер: —",
        f"🔽 Давление: {pressure:.0f} гПа" if pressure is not None else "🔽 Давление: —",
        f"☁ Условия: {symbol_to_ru(sym)}",
        "",
        "<i>Источник: api.met.no (Meteorologisk institutt, Норвегия)</i>",
    ]
    return "\n".join(lines)


def aggregate_by_day(data: dict) -> list[tuple[date, dict]]:
    ts = data["properties"]["timeseries"]
    by_day: dict[date, list[float]] = defaultdict(list)
    symbols: dict[date, str | None] = {}

    for entry in ts:
        t_iso = entry["time"]
        dt_utc = datetime.fromisoformat(t_iso.replace("Z", "+00:00"))
        local = dt_utc.astimezone(TZ)
        d = local.date()
        temp = entry["data"]["instant"]["details"].get("air_temperature")
        if temp is not None:
            by_day[d].append(temp)

        sym = None
        for key in ("next_12_hours", "next_6_hours", "next_1_hours"):
            block = entry["data"].get(key)
            if block and block.get("summary"):
                sym = block["summary"].get("symbol_code")
                break
        if sym and d not in symbols:
            symbols[d] = sym

    days_sorted = sorted(by_day.keys())
    out: list[tuple[date, dict]] = []
    for d in days_sorted:
        temps = by_day[d]
        out.append(
            (
                d,
                {
                    "tmin": min(temps),
                    "tmax": max(temps),
                    "symbol": symbols.get(d),
                },
            )
        )
    return out


def format_forecast_period(data: dict) -> str:
    daily = aggregate_by_day(data)
    if not daily:
        return "Нет данных прогноза."

    lines = [
        f"📆 <b>{CITY}</b> — прогноз по дням",
        "",
        "<i>Бесплатные метеослужбы обычно дают детальный прогноз на 7–10 дней, "
        "а не на полный календарный месяц. Ниже — максимальный доступный период.</i>",
        "",
    ]
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for d, info in daily:
        wd = weekdays[d.weekday()]
        sym = symbol_to_ru(info["symbol"])
        lines.append(
            f"• <b>{d.strftime('%d.%m')}</b> ({wd}): "
            f"{info['tmin']:.0f}…{info['tmax']:.0f}°C, {sym}"
        )
    lines.append("")
    lines.append("<i>Источник: api.met.no</i>")
    return "\n".join(lines)


def split_telegram(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not WEBAPP_URL:
        await update.message.reply_text(
            "Сначала настрой WebApp.\n\n"
            "1) Запусти веб-сервер (FastAPI)\n"
            "2) Получи публичный HTTPS URL (например, через ngrok)\n"
            "3) Запиши его в .env как WEBAPP_URL\n\n"
            "После этого команда /app откроет мини‑приложение."
        )
        return
    await update.message.reply_html(
        f"Привет! Это мини‑приложение погоды для <b>{CITY}</b>.\n\n"
        "Нажми кнопку ниже, чтобы открыть Web‑App прямо в Telegram.",
        reply_markup=webapp_keyboard(),
    )


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = await fetch_met_json()
        await update.message.reply_html(format_current(data), reply_markup=webapp_keyboard())
    except Exception as e:
        log.exception("weather")
        await update.message.reply_text(f"Ошибка: {e}")

async def cmd_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not WEBAPP_URL:
        await update.message.reply_text("WEBAPP_URL не задан. Смотри `.env.example`.")
        return
    await update.message.reply_html(
        f"Открыть мини‑приложение погоды для <b>{CITY}</b>:",
        reply_markup=webapp_keyboard(),
    )


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("Задайте переменную окружения BOT_TOKEN (токен от @BotFather).")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("app", cmd_app))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(MessageHandler(filters.CALLBACK_QUERY, lambda *_: None))

    log.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
