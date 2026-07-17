/* The Journey web app. Vanilla JS, no build step. */
"use strict";

/* ============================== helpers ============================== */

const $ = (sel) => document.querySelector(sel);
const KG_PER_LB = 1 / 2.2046226218;

const state = {
  token: localStorage.getItem("journey_token") || null,
  unit: localStorage.getItem("journey_unit") === "lb" ? "lb" : "kg",
  authMode: "dev",
  entries: [],   // ascending by date
  stats: null,
  goal: null,    // GoalProgress or null
  range: 30,     // days, or "all"
  firstRender: true,
};

function toUnit(kg) { return state.unit === "kg" ? kg : kg * 2.2046226218; }
function fromUnit(v) { return state.unit === "kg" ? v : v * KG_PER_LB; }
function fmtW(kg, { sign = false, unit = true } = {}) {
  if (kg == null) return "--";
  const v = toUnit(kg);
  const s = (sign && v > 0 ? "+" : "") + v.toFixed(1);
  return unit ? `${s} ${state.unit}` : s;
}
function parseDate(iso) { return new Date(iso + "T00:00:00"); }
function fmtDate(iso, opts = { month: "short", day: "numeric" }) {
  return parseDate(iso).toLocaleDateString("en-US", opts);
}
function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/* ============================== api ============================== */

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let res;
  try {
    res = await fetch(path, { ...options, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }
  if (res.status === 401 && state.token) {
    signOut();
    throw new ApiError(401, "Session expired. Sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not json */ }
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
    throw new ApiError(res.status, String(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

/* ============================== toasts ============================== */

function toast(message, { error = false, action = null, duration = 5000 } = {}) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  const span = document.createElement("span");
  span.textContent = message;
  el.appendChild(span);
  if (action) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = action.label;
    btn.addEventListener("click", () => { dismiss(); action.onClick(); });
    el.appendChild(btn);
  }
  $("#toasts").appendChild(el);
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("show")));
  let gone = false;
  function dismiss() {
    if (gone) return;
    gone = true;
    el.classList.remove("show");
    el.addEventListener("transitionend", () => el.remove(), { once: true });
    setTimeout(() => el.remove(), 400); // reduced-motion fallback
  }
  setTimeout(dismiss, duration);
}

/* ============================== theme ============================== */

const SUN = "M120,40V16a8,8,0,0,1,16,0V40a8,8,0,0,1-16,0Zm72,88a64,64,0,1,1-64-64A64.07,64.07,0,0,1,192,128Zm-16,0a48,48,0,1,0-48,48A48.05,48.05,0,0,0,176,128ZM58.34,69.66A8,8,0,0,0,69.66,58.34l-16-16A8,8,0,0,0,42.34,53.66Zm0,116.68-16,16a8,8,0,0,0,11.32,11.32l16-16a8,8,0,0,0-11.32-11.32ZM192,72a8,8,0,0,0,5.66-2.34l16-16a8,8,0,0,0-11.32-11.32l-16,16A8,8,0,0,0,192,72Zm5.66,114.34a8,8,0,0,0-11.32,11.32l16,16a8,8,0,0,0,11.32-11.32ZM48,128a8,8,0,0,0-8-8H16a8,8,0,0,0,0,16H40A8,8,0,0,0,48,128Zm80,80a8,8,0,0,0-8,8v24a8,8,0,0,0,16,0V216A8,8,0,0,0,128,208Zm112-88H216a8,8,0,0,0,0,16h24a8,8,0,0,0,0-16Z";
const MOON = "M233.54,142.23a8,8,0,0,0-8-2,88.08,88.08,0,0,1-109.8-109.8,8,8,0,0,0-10-10,104.84,104.84,0,0,0-52.91,37A104,104,0,0,0,136,224a103.09,103.09,0,0,0,62.52-20.88,104.84,104.84,0,0,0,37-52.91A8,8,0,0,0,233.54,142.23ZM188.9,190.34A88,88,0,0,1,65.66,67.11a89,89,0,0,1,31.4-26A106,106,0,0,0,96,56,104.11,104.11,0,0,0,200,160a106,106,0,0,0,14.92-1.06A89,89,0,0,1,188.9,190.34Z";

function effectiveTheme() {
  const t = document.documentElement.dataset.theme;
  if (t === "light" || t === "dark") return t;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function renderThemeIcon() {
  $("#theme-icon").innerHTML = `<path d="${effectiveTheme() === "dark" ? SUN : MOON}"/>`;
}
$("#theme-toggle").addEventListener("click", () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("journey_theme", next);
  renderThemeIcon();
});

/* ============================== unit toggle ============================== */

function renderUnit() {
  document.querySelectorAll("[data-unit]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.unit === state.unit));
  });
  document.querySelectorAll(".unit-label").forEach((el) => { el.textContent = `(${state.unit})`; });
}
document.querySelectorAll("[data-unit]").forEach((b) => {
  b.addEventListener("click", () => {
    if (b.dataset.unit === state.unit) return;
    state.unit = b.dataset.unit;
    localStorage.setItem("journey_unit", state.unit);
    renderUnit();
    renderAll();
  });
});

/* ============================== auth ============================== */

function showLogin() {
  $("#app-view").hidden = true;
  $("#login-view").hidden = false;
  $("#dev-identity-block").hidden = state.authMode !== "dev";
  $("#prod-note").hidden = state.authMode === "dev";
}
function signOut() {
  state.token = null;
  localStorage.removeItem("journey_token");
  showLogin();
}
$("#signout").addEventListener("click", signOut);

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const provider = e.submitter?.dataset.provider || "apple";
  const errEl = $("#login-error");
  errEl.hidden = true;

  if (state.authMode !== "dev") {
    toast("Real sign-in needs the provider SDK. Use the iOS app, or run the backend with AUTH_MODE=dev.", { error: true, duration: 7000 });
    return;
  }
  const identity = $("#dev-identity").value.trim();
  if (!identity) return;
  try {
    const data = await api(`/auth/${provider}`, {
      method: "POST",
      body: JSON.stringify({ id_token: identity }),
    });
    state.token = data.access_token;
    localStorage.setItem("journey_token", state.token);
    enterApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

/* ============================== data load ============================== */

async function loadData() {
  const [entries, stats, goal] = await Promise.all([
    api("/weights?limit=1000"),
    api("/weights/stats"),
    api("/goals/current").catch((e) => { if (e.status === 404) return null; throw e; }),
  ]);
  state.entries = entries.slice().reverse(); // API returns desc; keep asc
  state.stats = stats;
  state.goal = goal;
}

async function refresh() {
  try {
    await loadData();
    renderAll();
  } catch (err) {
    if (err.status !== 401) toast(err.message, { error: true });
  }
}

function enterApp() {
  $("#login-view").hidden = true;
  $("#app-view").hidden = false;
  renderUnit();
  renderThemeIcon();
  $("#add-date").value = todayISO();
  $("#add-date").max = todayISO();
  refresh();
}

/* ============================== stat tiles ============================== */

function goalDirection() {
  // -1 when the goal is to lose, +1 to gain, 0 when no goal
  if (!state.goal) return 0;
  return Math.sign(state.goal.goal.target_weight_kg - state.goal.goal.start_weight_kg) || -1;
}

function setTile(name, value, sub, positive = false) {
  const tile = document.querySelector(`.tile[data-stat="${name}"]`);
  const v = tile.querySelector(".tile-value");
  v.classList.remove("skeleton");
  v.textContent = value;
  const s = tile.querySelector(".tile-sub");
  s.textContent = sub;
  s.classList.toggle("positive", positive);
}

function renderStats() {
  const st = state.stats;
  if (!st || st.count === 0) {
    setTile("current", "--", "");
    setTile("change", "--", "");
    setTile("avg", "--", "");
    setTile("pace", "--", "");
    return;
  }
  const dir = goalDirection();
  const change = st.total_change_kg;
  const movingTowardGoal = dir !== 0 && change !== 0 && Math.sign(change) === dir;

  setTile("current", fmtW(st.latest_weight_kg), `as of ${fmtDate(st.latest_date)}`);
  setTile("change", fmtW(change, { sign: true }), `from ${fmtW(st.start_weight_kg)} on ${fmtDate(st.first_date)}`, movingTowardGoal);

  const windowStart = new Date(parseDate(st.latest_date).getTime() - 6 * 86400e3);
  const inWindow = state.entries.filter((en) => parseDate(en.date) >= windowStart).length;
  setTile("avg", fmtW(st.moving_avg_7d_kg), `${inWindow} ${inWindow === 1 ? "entry" : "entries"} this week`);

  const pace = st.avg_weekly_change_kg;
  if (pace == null) {
    setTile("pace", "--", "needs entries on 2+ days");
  } else {
    let sub = "";
    let positive = false;
    if (state.goal && state.goal.remaining_kg != null && dir !== 0 && Math.sign(pace) === dir && Math.abs(pace) > 0.01) {
      const weeksLeft = Math.abs(state.goal.remaining_kg) / Math.abs(pace);
      if (weeksLeft < 520) {
        const eta = new Date(Date.now() + weeksLeft * 7 * 86400e3);
        sub = `goal around ${eta.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
        positive = true;
      }
    }
    setTile("pace", `${fmtW(pace, { sign: true })}/wk`, sub, positive);
  }
}

/* ============================== entries list ============================== */

const PENCIL = "M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM92.69,208H48V163.31l88-88L180.69,120ZM192,108.68,147.31,64l24-24L216,84.68Z";
const TRASH = "M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM96,40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8v8H96Zm96,168H64V64H192ZM112,104v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Z";

function iconButton(path, label, danger, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "icon-btn" + (danger ? " danger" : "");
  b.setAttribute("aria-label", label);
  b.innerHTML = `<svg viewBox="0 0 256 256" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="${path}"/></svg>`;
  b.addEventListener("click", onClick);
  return b;
}

function renderEntries() {
  const list = $("#entries-list");
  const empty = $("#entries-empty");
  const badge = $("#entry-count");
  $("#entries-skeleton").hidden = true;

  list.innerHTML = "";
  const desc = state.entries.slice().reverse();
  badge.hidden = desc.length === 0;
  badge.textContent = String(desc.length);
  empty.hidden = desc.length !== 0;
  list.hidden = desc.length === 0;
  if (!desc.length) return;

  // Cascade only on the first paint; later re-renders are instant.
  list.classList.toggle("cascade", state.firstRender);

  desc.forEach((entry, i) => {
    const li = document.createElement("li");
    li.style.setProperty("--i", Math.min(i, 12));

    const date = document.createElement("span");
    date.className = "entry-date";
    date.textContent = fmtDate(entry.date, { month: "short", day: "numeric", year: parseDate(entry.date).getFullYear() !== new Date().getFullYear() ? "numeric" : undefined });

    const weight = document.createElement("span");
    weight.className = "entry-weight";
    weight.textContent = fmtW(entry.weight_kg);

    const delta = document.createElement("span");
    delta.className = "entry-delta";
    const idx = state.entries.indexOf(entry);
    if (idx > 0) {
      const d = entry.weight_kg - state.entries[idx - 1].weight_kg;
      delta.textContent = fmtW(d, { sign: true, unit: false });
      const dir = goalDirection();
      if (dir !== 0 && d !== 0 && Math.sign(d) === dir) delta.classList.add("down");
    }

    const note = document.createElement("span");
    note.className = "entry-note";
    note.textContent = entry.note || "";

    const actions = document.createElement("span");
    actions.className = "entry-actions";
    actions.appendChild(iconButton(PENCIL, `Edit entry for ${entry.date}`, false, () => openEdit(entry)));
    actions.appendChild(iconButton(TRASH, `Delete entry for ${entry.date}`, true, () => deleteEntry(entry)));

    li.append(date, weight, delta, note, actions);
    list.appendChild(li);
  });
}

async function deleteEntry(entry) {
  try {
    await api(`/weights/${entry.id}`, { method: "DELETE" });
    await refresh();
    toast(`Deleted ${fmtDate(entry.date)}.`, {
      action: {
        label: "Undo",
        onClick: async () => {
          try {
            await api("/weights", {
              method: "POST",
              body: JSON.stringify({ date: entry.date, weight_kg: entry.weight_kg, note: entry.note, source: entry.source }),
            });
            await refresh();
          } catch (err) { toast(err.message, { error: true }); }
        },
      },
    });
  } catch (err) { toast(err.message, { error: true }); }
}

/* ---------- edit dialog ---------- */

let editing = null;
const editDialog = $("#edit-dialog");

function openEdit(entry) {
  editing = entry;
  $("#edit-title").textContent = `Edit ${fmtDate(entry.date, { month: "long", day: "numeric" })}`;
  $("#edit-weight").value = toUnit(entry.weight_kg).toFixed(1);
  $("#edit-note").value = entry.note || "";
  $("#edit-error").hidden = true;
  editDialog.showModal();
}
$("#edit-cancel").addEventListener("click", () => editDialog.close());
$("#edit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const kg = fromUnit(parseFloat($("#edit-weight").value));
  try {
    await api(`/weights/${editing.id}`, {
      method: "PUT",
      body: JSON.stringify({ weight_kg: Math.round(kg * 100) / 100, note: $("#edit-note").value.trim() || null }),
    });
    editDialog.close();
    await refresh();
  } catch (err) {
    const el = $("#edit-error");
    el.textContent = err.message;
    el.hidden = false;
  }
});

/* ============================== add form ============================== */

$("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = $("#add-error");
  errEl.hidden = true;
  const kg = fromUnit(parseFloat($("#add-weight").value));
  const btn = $("#add-submit");
  btn.disabled = true;
  try {
    await api("/weights", {
      method: "POST",
      body: JSON.stringify({
        date: $("#add-date").value,
        weight_kg: Math.round(kg * 100) / 100,
        note: $("#add-note").value.trim() || null,
      }),
    });
    $("#add-weight").value = "";
    $("#add-note").value = "";
    await refresh();
  } catch (err) {
    errEl.textContent = err.status === 409
      ? "Already logged for this date. Edit that entry in the list instead."
      : err.message;
    errEl.hidden = false;
  } finally {
    btn.disabled = false;
  }
});

/* ============================== goal ============================== */

const goalDialog = $("#goal-dialog");
$("#goal-edit").addEventListener("click", () => {
  const g = state.goal?.goal;
  $("#goal-weight").value = g ? toUnit(g.target_weight_kg).toFixed(1) : "";
  $("#goal-date").value = g?.target_date || "";
  $("#goal-error").hidden = true;
  goalDialog.showModal();
});
$("#goal-cancel").addEventListener("click", () => goalDialog.close());
$("#goal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const kg = fromUnit(parseFloat($("#goal-weight").value));
  try {
    await api("/goals", {
      method: "PUT",
      body: JSON.stringify({
        target_weight_kg: Math.round(kg * 100) / 100,
        target_date: $("#goal-date").value || null,
      }),
    });
    goalDialog.close();
    await refresh();
  } catch (err) {
    const el = $("#goal-error");
    el.textContent = err.status === 400 ? "Log at least one weight first." : err.message;
    el.hidden = false;
  }
});

function renderGoal() {
  $("#goal-skeleton").hidden = true;
  const g = state.goal;
  $("#goal-empty").hidden = !!g;
  $("#goal-body").hidden = !g;
  $("#goal-edit").textContent = g ? "Change" : "Set goal";
  if (!g) return;

  $("#goal-lost").textContent = fmtW(Math.abs(g.lost_kg ?? 0));
  $("#goal-left").textContent = fmtW(Math.abs(g.remaining_kg ?? 0));
  $("#goal-pct").textContent = `${Math.round(g.percent_complete ?? 0)}%`;
  const bar = $("#goal-bar");
  bar.setAttribute("aria-valuenow", String(Math.round(g.percent_complete ?? 0)));
  $("#goal-fill").style.transform = `scaleX(${(g.percent_complete ?? 0) / 100})`;
  const target = g.goal.target_date ? ` by ${fmtDate(g.goal.target_date, { month: "short", day: "numeric", year: "numeric" })}` : "";
  $("#goal-range").textContent = `${fmtW(g.goal.start_weight_kg)} to ${fmtW(g.goal.target_weight_kg)}${target}`;
}

/* ============================== chart ============================== */

const NS = "http://www.w3.org/2000/svg";
// Paint/text properties go through style so var(--token) works (CSS variables
// are invalid inside SVG presentation attributes).
const SVG_STYLE_PROPS = new Set([
  "fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-linejoin",
  "stroke-linecap", "opacity", "font-size", "font-weight", "text-anchor",
]);
function svgEl(name, attrs = {}) {
  const el = document.createElementNS(NS, name);
  // Apply a style string first so it can't clobber routed style props below.
  if (attrs.style) el.setAttribute("style", attrs.style);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "style") continue;
    if (SVG_STYLE_PROPS.has(k)) el.style.setProperty(k, v);
    else el.setAttribute(k, v);
  }
  return el;
}

function visibleEntries() {
  if (state.range === "all") return state.entries;
  const cutoff = Date.now() - Number(state.range) * 86400e3;
  return state.entries.filter((e) => parseDate(e.date).getTime() >= cutoff);
}

function movingAvg(entries) {
  // For each point: mean of entries within the preceding 7 days (inclusive).
  return entries.map((e, i) => {
    const end = parseDate(e.date).getTime();
    const start = end - 6 * 86400e3;
    const win = entries.filter((x) => {
      const t = parseDate(x.date).getTime();
      return t >= start && t <= end;
    });
    return { ...e, avg: win.reduce((s, x) => s + x.weight_kg, 0) / win.length };
  });
}

function niceTicks(min, max, count = 4) {
  const span = max - min;
  const step = Math.pow(10, Math.floor(Math.log10(span / count)));
  const err = span / count / step;
  const mult = err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
  const s = mult * step;
  const ticks = [];
  for (let v = Math.ceil(min / s) * s; v <= max + 1e-9; v += s) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

let chartGeom = null; // {points, x, y, pad, w, h} for the tooltip layer

function renderChart() {
  const svg = $("#chart");
  const wrap = $("#chart-wrap");
  $("#chart-skeleton").hidden = true;

  const data = movingAvg(visibleEntries());
  const emptyEl = $("#chart-empty");
  const hasLine = data.length >= 2;
  emptyEl.hidden = hasLine;
  // .hidden is an HTMLElement property; SVG needs the attribute toggled.
  svg.toggleAttribute("hidden", !hasLine);
  $("#chart-legend").hidden = !hasLine;
  chartGeom = null;
  if (!hasLine) {
    emptyEl.querySelector("p").textContent = state.entries.length >= 2
      ? "No entries in this range. Try a wider one."
      : "Your trend line starts with two entries.";
    return;
  }

  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.innerHTML = "";
  const pad = { top: 14, right: 14, bottom: 26, left: 44 };

  // Work in the display unit so axis ticks come out round in kg AND lb.
  const goalKg = state.goal?.goal.target_weight_kg;
  const goalV = goalKg != null ? toUnit(goalKg) : null;
  const values = data.map((d) => toUnit(d.weight_kg));
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  const near = toUnit(3);
  if (goalV != null && goalV >= lo - near && goalV <= hi + near) { lo = Math.min(lo, goalV); hi = Math.max(hi, goalV); }
  const spread = Math.max(hi - lo, 1);
  lo -= spread * 0.12;
  hi += spread * 0.12;

  const t0 = parseDate(data[0].date).getTime();
  const t1 = parseDate(data[data.length - 1].date).getTime();
  const x = (t) => pad.left + ((t - t0) / Math.max(t1 - t0, 1)) * (w - pad.left - pad.right);
  const y = (v) => pad.top + ((hi - v) / (hi - lo)) * (h - pad.top - pad.bottom);

  // grid + y labels (already in the display unit)
  for (const tick of niceTicks(lo, hi)) {
    const gy = y(tick);
    svg.appendChild(svgEl("line", { x1: pad.left, x2: w - pad.right, y1: gy, y2: gy, stroke: "var(--gridline)", "stroke-width": 1 }));
    const label = svgEl("text", { x: pad.left - 8, y: gy + 3.5, "text-anchor": "end", fill: "var(--text-muted)", "font-size": 11, style: "font-variant-numeric: tabular-nums" });
    label.textContent = Number.isInteger(tick) ? String(tick) : tick.toFixed(1);
    svg.appendChild(label);
  }

  // x labels: ~5, from the time domain
  const nx = Math.min(5, data.length);
  for (let i = 0; i < nx; i++) {
    const t = t0 + ((t1 - t0) * i) / Math.max(nx - 1, 1);
    const d = new Date(t);
    const label = svgEl("text", { x: x(t), y: h - 8, "text-anchor": i === 0 ? "start" : i === nx - 1 ? "end" : "middle", fill: "var(--text-muted)", "font-size": 11 });
    label.textContent = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    svg.appendChild(label);
  }

  // baseline
  svg.appendChild(svgEl("line", { x1: pad.left, x2: w - pad.right, y1: h - pad.bottom, y2: h - pad.bottom, stroke: "var(--hairline)", "stroke-width": 1 }));

  const pts = data.map((d) => ({ ...d, px: x(parseDate(d.date).getTime()), py: y(toUnit(d.weight_kg)), pa: y(toUnit(d.avg)) }));
  const linePath = pts.map((p, i) => `${i ? "L" : "M"}${p.px.toFixed(1)},${p.py.toFixed(1)}`).join("");
  const avgPath = pts.map((p, i) => `${i ? "L" : "M"}${p.px.toFixed(1)},${p.pa.toFixed(1)}`).join("");

  // area fill under the weight line
  const defs = svgEl("defs");
  defs.innerHTML = `<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" style="stop-color: var(--accent); stop-opacity: 0.14"/>
      <stop offset="1" style="stop-color: var(--accent); stop-opacity: 0"/>
    </linearGradient>`;
  svg.appendChild(defs);
  svg.appendChild(svgEl("path", { d: `${linePath}L${pts[pts.length - 1].px},${h - pad.bottom}L${pts[0].px},${h - pad.bottom}Z`, fill: "url(#area)" }));

  // goal line (dashed) + direct label
  if (goalV != null && goalV > lo && goalV < hi) {
    const gy = y(goalV);
    svg.appendChild(svgEl("line", { x1: pad.left, x2: w - pad.right, y1: gy, y2: gy, stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "5 4" }));
    const gl = svgEl("text", { x: w - pad.right, y: gy - 5, "text-anchor": "end", fill: "var(--text-secondary)", "font-size": 11, "font-weight": 600 });
    gl.textContent = `Goal ${fmtW(goalKg)}`;
    svg.appendChild(gl);
    $("#legend-goal").hidden = false;
  } else {
    $("#legend-goal").hidden = true;
  }

  // 7-day average line
  svg.appendChild(svgEl("path", { d: avgPath, fill: "none", stroke: "var(--text-muted)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", opacity: 0.9 }));
  // weight line
  svg.appendChild(svgEl("path", { d: linePath, fill: "none", stroke: "var(--accent)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));

  // dots when sparse enough to read individually
  if (pts.length <= 60) {
    for (const p of pts) {
      svg.appendChild(svgEl("circle", { cx: p.px, cy: p.py, r: 2.5, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 1.5 }));
    }
  }

  // crosshair + hover marker (hidden until pointermove)
  const cross = svgEl("line", { y1: pad.top, y2: h - pad.bottom, stroke: "var(--text-muted)", "stroke-width": 1, opacity: 0, "stroke-dasharray": "2 3" });
  cross.id = "crosshair";
  svg.appendChild(cross);
  const marker = svgEl("circle", { r: 4.5, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2, opacity: 0 });
  marker.id = "hover-marker";
  svg.appendChild(marker);

  chartGeom = { pts, pad, w, h };
}

/* tooltip layer: pointer tracks 1:1, snaps to nearest point */
$("#chart-wrap").addEventListener("pointermove", (e) => {
  if (!chartGeom) return;
  const rect = $("#chart-wrap").getBoundingClientRect();
  const mx = ((e.clientX - rect.left) / rect.width) * chartGeom.w;
  let best = chartGeom.pts[0];
  for (const p of chartGeom.pts) if (Math.abs(p.px - mx) < Math.abs(best.px - mx)) best = p;

  const cross = $("#crosshair");
  const marker = $("#hover-marker");
  cross.setAttribute("x1", best.px); cross.setAttribute("x2", best.px);
  cross.style.opacity = 0.5;
  marker.setAttribute("cx", best.px); marker.setAttribute("cy", best.py);
  marker.style.opacity = 1;

  const tip = $("#chart-tip");
  tip.innerHTML = `<div class="tip-date">${fmtDate(best.date, { weekday: "short", month: "short", day: "numeric" })}</div>
    <div class="tip-main">${fmtW(best.weight_kg)}</div>
    <div class="tip-avg">7d avg ${fmtW(best.avg)}</div>`;
  tip.hidden = false;
  const tipW = tip.offsetWidth;
  const px = (best.px / chartGeom.w) * rect.width;
  const py = (best.py / chartGeom.h) * rect.height;
  const flip = px + 14 + tipW > rect.width;
  tip.style.left = `${flip ? px - tipW - 14 : px + 14}px`;
  tip.style.top = `${Math.max(0, py - 30)}px`;
});
$("#chart-wrap").addEventListener("pointerleave", () => {
  $("#chart-tip").hidden = true;
  const cross = $("#crosshair");
  const marker = $("#hover-marker");
  if (cross) cross.style.opacity = 0;
  if (marker) marker.style.opacity = 0;
});

/* range picker */
$("#range-picker").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-range]");
  if (!btn) return;
  state.range = btn.dataset.range === "all" ? "all" : Number(btn.dataset.range);
  document.querySelectorAll("#range-picker [data-range]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b === btn));
  });
  renderChart();
});

/* redraw on container resize */
new ResizeObserver(() => { if (!$("#app-view").hidden) renderChart(); }).observe($("#chart-wrap"));

/* ============================== render all ============================== */

function renderAll() {
  renderStats();
  renderEntries();
  renderGoal();
  renderChart();
  renderUnit();
  state.firstRender = false;
}

/* ============================== boot ============================== */

(async function boot() {
  renderThemeIcon();
  try {
    const cfg = await api("/auth/config");
    state.authMode = cfg.mode;
  } catch { /* default dev */ }

  if (state.token) {
    try {
      await api("/auth/me");
      enterApp();
      return;
    } catch { /* fall through to login */ }
  }
  showLogin();
})();
