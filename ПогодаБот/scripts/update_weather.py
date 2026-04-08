from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

# Нижневартовск
LAT = 60.9394
LON = 76.5692
CITY = "Нижневартовск"
TZ = ZoneInfo("Asia/Yekaterinburg")

MET_URL = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
USER_AGENT = os.environ.get(
    "MET_USER_AGENT",
    "NizhnevartovskWeatherBot/1.0 (GitHub Actions; contact: you@example.com)",
)

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


def fetch_met_json() -> dict:
    with httpx.Client() as client:
        r = client.get(MET_URL, headers={"User-Agent": USER_AGENT}, timeout=30.0)
        r.raise_for_status()
        return r.json()


def aggregate_by_day(data: dict) -> list[dict]:
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
            by_day[d].append(float(temp))

        sym = None
        for key in ("next_12_hours", "next_6_hours", "next_1_hours"):
            block = entry["data"].get(key)
            if block and block.get("summary"):
                sym = block["summary"].get("symbol_code")
                break
        if sym and d not in symbols:
            symbols[d] = sym

    out: list[dict] = []
    for d in sorted(by_day.keys()):
        temps = by_day[d]
        out.append(
            {
                "date": d.isoformat(),
                "tmin": min(temps),
                "tmax": max(temps),
                "symbol": symbol_to_ru(symbols.get(d)),
            }
        )
    return out


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "docs" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = fetch_met_json()
    ts = data["properties"]["timeseries"]
    first = ts[0]
    inst = first["data"]["instant"]["details"]

    sym = None
    for key in ("next_1_hours", "next_6_hours", "next_12_hours"):
        block = first["data"].get(key)
        if block and block.get("summary"):
            sym = block["summary"].get("symbol_code")
            break

    current = {
        "city": CITY,
        "temperature_c": inst.get("air_temperature"),
        "humidity_pct": inst.get("relative_humidity"),
        "wind_speed_mps": inst.get("wind_speed"),
        "wind_dir": wind_dir_ru(inst.get("wind_from_direction")),
        "pressure_hpa": inst.get("air_pressure_at_sea_level"),
        "condition": symbol_to_ru(sym),
        "source": "api.met.no",
        "updated_at_utc": first["time"],
    }

    forecast = {
        "city": CITY,
        "note": (
            "Бесплатные метеослужбы обычно дают детальный прогноз на 7–10 дней, "
            "а не на полный календарный месяц. Ниже — максимальный доступный период."
        ),
        "days": aggregate_by_day(data),
        "source": "api.met.no",
        "updated_at_utc": first["time"],
    }

    (out_dir / "current.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "forecast.json").write_text(
        json.dumps(forecast, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

