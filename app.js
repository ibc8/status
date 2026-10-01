const MAX_AGE_MS = 15 * 60 * 1000;
const LABELS = {ok:"Работает",warning:"Есть проблемы",down:"Недоступен",unknown:"Нет данных"};
const IDS = ["freeturn", "mieru", "free_pool"];

function setCard(id, item) {
  const card = document.querySelector(`[data-service="${id}"]`);
  const state = LABELS[item?.state] ? item.state : "unknown";
  const pill = card.querySelector(".pill");
  pill.className = `pill ${state}`;
  pill.textContent = LABELS[state];
  card.querySelector(".description").textContent = item?.summary || "Нет свежих результатов проверки.";
  card.querySelector(".detail").textContent = item?.detail || "—";
}

function render(data) {
  const checked = new Date(data?.checked_at || 0);
  const fresh = Number.isFinite(checked.getTime()) && checked.getTime() > 0 &&
    Math.abs(Date.now() - checked.getTime()) <= MAX_AGE_MS;
  document.querySelector("#checked-at").textContent = checked.getTime() > 0
    ? checked.toLocaleString("ru-RU", {dateStyle:"medium", timeStyle:"short"})
    : "нет данных";

  const services = fresh ? data.services || {} : {};
  for (const id of IDS) setCard(id, services[id]);
  const states = IDS.map(id => services[id]?.state || "unknown");
  let state = "unknown", label = "Нет свежих данных";
  if (fresh) {
    if (states.includes("down")) { state = "down"; label = "Есть недоступные сервисы"; }
    else if (states.includes("warning") || states.includes("unknown")) { state = "warning"; label = "Некоторые проверки требуют внимания"; }
    else { state = "ok"; label = "Все три сервиса отвечают"; }
  }
  document.querySelector("#overall").className = `overall ${state}`;
  document.querySelector("#overall-text").textContent = label;
}

async function refresh() {
  try {
    const response = await fetch(`status.json?t=${Date.now()}`, {cache:"no-store"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch {
    render(null);
  }
}

refresh();
setInterval(refresh, 60_000);
