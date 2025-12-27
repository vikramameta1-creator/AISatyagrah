/* ui/newsroom.js (no BOM)
   Minimal, reliable Newsroom UI client.
   - Calls /api/newsroom/plan, /api/newsroom/run, /api/newsroom/status
   - Sends x-auth header if token saved in localStorage
*/

const AUTH_HEADER = "x-auth";
const LS_TOKEN_KEY = "AISATYAGRAH_XAUTH";

const $ = (sel) => document.querySelector(sel);

function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function setStatusLine(msg) {
  const el = $("#statusLine");
  if (el) el.textContent = msg;
}

function getSavedToken() {
  return (localStorage.getItem(LS_TOKEN_KEY) || "").trim();
}
function saveToken(t) {
  t = (t || "").trim();
  if (t) localStorage.setItem(LS_TOKEN_KEY, t);
  else localStorage.removeItem(LS_TOKEN_KEY);
}

function getDateValue() {
  const el = $("#dateInput");
  return (el && el.value) ? el.value : todayISO();
}

function getPlatformValue() {
  const el = $("#platformInput");
  return (el && el.value) ? el.value : "all";
}

async function apiFetch(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  const tok = getSavedToken();
  if (tok) headers.set(AUTH_HEADER, tok);

  const res = await fetch(path, { ...opts, headers });

  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* ignore */ }

  if (!res.ok) {
    const detail = (data && data.detail) ? data.detail : text || `${res.status} ${res.statusText}`;
    throw new Error(detail);
  }
  return data;
}

async function refreshAuthBanner() {
  const pill = $("#authPill");
  try {
    const data = await apiFetch("/api/auth/enabled");
    if (!pill) return;
    if (data.enabled) {
      pill.textContent = `auth: ON • ${data.header}`;
      pill.classList.add("ok");
    } else {
      pill.textContent = `auth: OFF`;
      pill.classList.remove("ok");
    }
  } catch {
    if (pill) pill.textContent = `auth: unknown`;
  }
}

function renderItems(items) {
  const root = $("#items");
  if (!root) return;

  root.innerHTML = "";
  if (!items || items.length === 0) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = "No items in plan for this date.";
    root.appendChild(div);
    return;
  }

  for (const it of items) {
    const card = document.createElement("div");
    card.className = "card";

    const title = (it.title || it.topic || "(untitled)").toString();
    const platform = (it.platform || "unknown").toString();
    const id = (it.id || "").toString();
    const status = (it.status || "draft").toString().toLowerCase();

    const badge = document.createElement("span");
    badge.className = "badge dim";
    badge.textContent = status;
    if (status === "approved") badge.classList.add("warn");
    if (status === "sent") badge.classList.add("ok");

    const top = document.createElement("div");
    top.className = "cardTop";

    const left = document.createElement("div");
    left.innerHTML = `<div class="title">${escapeHtml(title)}</div>
      <div class="meta">platform=${escapeHtml(platform)} • id=${escapeHtml(id || "-")}</div>`;

    const right = document.createElement("div");
    right.appendChild(badge);

    top.appendChild(left);
    top.appendChild(right);

    const snip = document.createElement("div");
    snip.className = "snip";
    snip.textContent = (it.snippet || it.summary || "").toString();

    const actions = document.createElement("div");
    actions.className = "actions";

    const mkBtn = (label, cls, fn) => {
      const b = document.createElement("button");
      b.className = `btn ${cls || ""}`.trim();
      b.textContent = label;
      b.addEventListener("click", fn);
      return b;
    };

    actions.appendChild(mkBtn("Draft", "ghost", async () => {
      await setItemStatus(it, "draft");
    }));
    actions.appendChild(mkBtn("Approve", "ghost", async () => {
      await setItemStatus(it, "approved");
    }));
    actions.appendChild(mkBtn("Sent", "ghost", async () => {
      await setItemStatus(it, "sent");
    }));

    card.appendChild(top);
    card.appendChild(snip);
    card.appendChild(actions);
    root.appendChild(card);
  }
}

async function setItemStatus(it, status) {
  const date = getDateValue();
  const platform = (it.platform || getPlatformValue() || "telegram").toString();
  const itemId = (it.id || "").toString();
  if (!itemId) {
    setStatusLine("This item has no id yet. Import/ensure ids first.");
    return;
  }
  setStatusLine(`Setting status… ${platform}:${itemId} -> ${status}`);
  await apiFetch(`/api/newsroom/status?date=${encodeURIComponent(date)}&platform=${encodeURIComponent(platform)}&item_id=${encodeURIComponent(itemId)}&status=${encodeURIComponent(status)}`, {
    method: "POST"
  });
  await loadPlan();
}

async function loadPlan() {
  const date = getDateValue();
  const platform = getPlatformValue();
  setStatusLine(`Loading plan… date=${date} platform=${platform}`);

  const data = await apiFetch(`/api/newsroom/plan?date=${encodeURIComponent(date)}&platform=${encodeURIComponent(platform)}`);
  const items = Array.isArray(data.items) ? data.items : [];

  setStatusLine(`date=${data.date} • platform=${data.platform} • items=${items.length}`);
  renderItems(items);
}

async function approveAll() {
  const date = getDateValue();
  const platform = getPlatformValue();
  if (platform === "all") {
    setStatusLine("Approve All requires a specific platform (telegram/instagram).");
    return;
  }
  setStatusLine(`Approving all drafts… date=${date} platform=${platform}`);
  const data = await apiFetch(`/api/newsroom/approve_all?date=${encodeURIComponent(date)}&platform=${encodeURIComponent(platform)}`, { method: "POST" });
  setStatusLine(`Approved ${data.approved} items • ${data.platform}`);
  await loadPlan();
}

async function runPublish(dryRun) {
  const date = getDateValue();
  const platform = getPlatformValue();
  setStatusLine(`${dryRun ? "Dry-run" : "Publish"}… date=${date} platform=${platform}`);

  const url = `/api/newsroom/run?date=${encodeURIComponent(date)}&platform=${encodeURIComponent(platform)}&dry_run=${dryRun ? "true" : "false"}&confirm=${dryRun ? "false" : "true"}`;
  const data = await apiFetch(url, { method: "POST" });

  setStatusLine(`Run OK • candidates=${data.candidates} • sent=${data.sent} • platform=${data.platform}`);
  await loadPlan();
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bind() {
  const dateEl = $("#dateInput");
  if (dateEl && !dateEl.value) dateEl.value = todayISO();

  const tokenInput = $("#tokenInput");
  const saveBtn = $("#saveTokenBtn");
  const clearBtn = $("#clearTokenBtn");

  if (tokenInput) tokenInput.value = getSavedToken();

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      saveToken(tokenInput ? tokenInput.value : "");
      await refreshAuthBanner();
      setStatusLine("Token saved.");
      await loadPlan();
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      saveToken("");
      if (tokenInput) tokenInput.value = "";
      await refreshAuthBanner();
      setStatusLine("Token cleared.");
      await loadPlan();
    });
  }

  $("#loadPlanBtn")?.addEventListener("click", () => loadPlan().catch(e => setStatusLine(`Load failed: ${e.message}`)));
  $("#approveAllBtn")?.addEventListener("click", () => approveAll().catch(e => setStatusLine(`Approve failed: ${e.message}`)));
  $("#dryRunBtn")?.addEventListener("click", () => runPublish(true).catch(e => setStatusLine(`Run failed: ${e.message}`)));
  $("#publishBtn")?.addEventListener("click", () => runPublish(false).catch(e => setStatusLine(`Run failed: ${e.message}`)));

  refreshAuthBanner().finally(() => loadPlan().catch(e => setStatusLine(`Load failed: ${e.message}`)));
}

window.addEventListener("DOMContentLoaded", bind);
