/* global Telegram */

function $(id) {
  return document.getElementById(id);
}

function fmtNum(x, suffix = "") {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${Math.round(Number(x))}${suffix}`;
}

function weekdayRu(d) {
  const arr = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
  return arr[d.getDay()];
}

async function getJson(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`${r.status} ${r.statusText}\n${txt}`);
  }
  return await r.json();
}

function fmtUpdated(isoUtc) {
  if (!isoUtc) return "—";
  try {
    const d = new Date(isoUtc);
    return d.toLocaleString("ru-RU", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
  } catch {
    return "—";
  }
}

async function loadCurrent() {
  $("error").textContent = "";
  const cur = await getJson("./data/current.json?ts=" + Date.now());

  $("city").textContent = cur.city ?? "Нижневартовск";
  $("temp").textContent = `${fmtNum(cur.temperature_c, "°C")}`;
  $("cond").textContent = cur.condition ?? "—";

  $("hum").textContent = `${fmtNum(cur.humidity_pct, "%")}`;
  const wind = `${fmtNum(cur.wind_speed_mps, " м/с")} ${cur.wind_dir ?? ""}`.trim();
  $("wind").textContent = wind || "—";
  $("press").textContent = `${fmtNum(cur.pressure_hpa, " гПа")}`;
  $("updated").textContent = fmtUpdated(cur.updated_at_utc);
}

async function loadForecast() {
  const btn = $("loadForecast");
  btn.disabled = true;
  btn.textContent = "Загружаю…";
  try {
    const fc = await getJson("./data/forecast.json?ts=" + Date.now());
    $("note").textContent = fc.note ?? "";
    $("sourceFoot").textContent = `Источник: ${fc.source ?? "—"} • обновлено: ${fmtUpdated(fc.updated_at_utc)}`;

    const root = $("forecast");
    root.innerHTML = "";

    for (const day of fc.days ?? []) {
      const d = new Date(`${day.date}T00:00:00`);
      const el = document.createElement("div");
      el.className = "day";
      el.innerHTML = `
        <div>
          <div class="d">${d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })} (${weekdayRu(d)})</div>
          <div class="c">${day.symbol ?? "—"}</div>
        </div>
        <div class="t">${fmtNum(day.tmin)}…${fmtNum(day.tmax)}°C</div>
      `;
      root.appendChild(el);
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Показать прогноз на месяц";
  }
}

async function main() {
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  $("refresh").addEventListener("click", async () => {
    try {
      await loadCurrent();
    } catch (e) {
      $("error").textContent = String(e?.message ?? e);
    }
  });

  $("loadForecast").addEventListener("click", async () => {
    try {
      await loadForecast();
    } catch (e) {
      $("error").textContent = String(e?.message ?? e);
    }
  });

  try {
    await loadCurrent();
  } catch (e) {
    $("error").textContent = String(e?.message ?? e);
  }
}

main();

