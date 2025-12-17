// ui/newsroom.js
(() => {
  const $ = (id) => document.getElementById(id);

  const els = {
    token: $("tokenInput"),
    saveToken: $("saveTokenBtn"),
    clearToken: $("clearTokenBtn"),
    authBadge: $("authBadge"),

    platform: $("platformSel"),
    date: $("dateInput"),

    loadPlan: $("loadPlanBtn"),
    latest: $("latestBtn"),
    browse: $("browseBtn"),
    importBtn: $("importBtn"),
    csvFile: $("csvFile"),

    approveAll: $("approveAllBtn"),
    dryRun: $("dryRunBtn"),
    publish: $("publishBtn"),
    igCaptions: $("igCaptionsBtn"),
    logs: $("logsBtn"),
    metrics: $("metricsBtn"),
    copyCurl: $("copyCurlBtn"),

    q: $("searchInput"),
    search: $("searchBtn"),

    tabAll: $("tabAll"),
    tabDraft: $("tabDraft"),
    tabApproved: $("tabApproved"),
    tabSent: $("tabSent"),

    statusLine: $("statusLine"),
    cards: $("cards"),

    toast: $("toast"),
    modal: $("modal"),
    modalTitle: $("modalTitle"),
    modalBody: $("modalBody"),
    modalClose: $("modalClose"),
  };

  const LS_KEY = "xauth";

  const state = {
    authEnabled: null,      // null until probed
    lastReq: null,          // {method,url,headers,body}
    busy: false,
    suppress401Until: 0,

    plan: {
      date: "",
      platform: "telegram",
      counts: { draft: 0, approved: 0, sent: 0 },
      items: [],
    },

    filter: "all",
    query: "",
  };

  // ---------------- Toast / Modal ----------------
  function toast(msg, ms = 2400) {
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
    window.clearTimeout(toast._t);
    toast._t = window.setTimeout(() => els.toast.classList.add("hidden"), ms);
  }

  function toast401Once() {
    const now = Date.now();
    if (now < state.suppress401Until) return;
    state.suppress401Until = now + 5000;
    toast("Token missing/invalid (401). Save the correct token or run server with AUTH OFF.", 4200);
  }

  function openModal(title, body) {
    els.modalTitle.textContent = title;
    els.modalBody.textContent = body || "";
    els.modal.classList.remove("hidden");
  }
  function closeModal() {
    els.modal.classList.add("hidden");
  }

  // ---------------- Auth helpers ----------------
  function readToken() {
    return (els.token.value || "").trim();
  }
  function loadTokenFromLocalStorage() {
    const t = (localStorage.getItem(LS_KEY) || "").trim();
    if (t) els.token.value = t;
  }
  function saveTokenToLocalStorage() {
    const t = readToken();
    if (!t) {
      toast("Token is empty (nothing saved).");
      return;
    }
    localStorage.setItem(LS_KEY, t);
    toast("Token saved.");
  }
  function clearToken() {
    localStorage.removeItem(LS_KEY);
    els.token.value = "";
    toast("Token cleared.");
  }

  function setAuthBadge(enabled) {
    if (enabled) {
      els.authBadge.textContent = "AUTH ON";
      els.authBadge.classList.remove("badgeOff");
      els.authBadge.classList.add("badgeOn");
    } else {
      els.authBadge.textContent = "AUTH OFF";
      els.authBadge.classList.remove("badgeOn");
      els.authBadge.classList.add("badgeOff");
    }
  }

  // ✅ Step 10: probe auth once on load
  async function probeAuthEnabled() {
    try {
      const r = await fetch("/api/auth/enabled", { cache: "no-store" });
      const j = await r.json();
      state.authEnabled = !!j.enabled;
      setAuthBadge(state.authEnabled);
    } catch (e) {
      state.authEnabled = null;
      els.authBadge.textContent = "AUTH ?";
      els.authBadge.classList.add("badgeOff");
    }
  }

  function authHeaders() {
    const h = {};
    const t = readToken();
    if (t) h["x-auth"] = t;
    return h;
  }

  // ---------------- Request wrappers ----------------
  async function apiFetch(url, opts = {}) {
    const method = (opts.method || "GET").toUpperCase();
    const headers = Object.assign({}, opts.headers || {}, authHeaders());

    // record last request (for Copy curl)
    state.lastReq = {
      method,
      url,
      headers,
      body: opts.body || null,
    };

    const r = await fetch(url, { ...opts, method, headers, cache: "no-store" });

    if (r.status === 401) {
      toast401Once();
    }

    return r;
  }

  async function apiJson(url, opts = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    const r = await apiFetch(url, { ...opts, headers });

    if (!r.ok) {
      const t = await r.text().catch(() => "");
      throw new Error(`${r.status} ${r.statusText} :: ${t}`.trim());
    }
    return r.json();
  }

  async function downloadBlob(url, filenameFallback) {
    const r = await apiFetch(url, { method: "GET" });
    if (!r.ok) {
      const t = await r.text().catch(() => "");
      throw new Error(`${r.status} ${r.statusText} :: ${t}`.trim());
    }

    const blob = await r.blob();

    let fn = filenameFallback || "download.txt";
    const cd = r.headers.get("content-disposition") || "";
    const m = cd.match(/filename="([^"]+)"/i);
    if (m && m[1]) fn = m[1];

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fn;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  }

  function setBusy(on, btn) {
    state.busy = on;
    const buttons = document.querySelectorAll("button");
    buttons.forEach((b) => (b.disabled = on));

    // keep Close enabled
    els.modalClose.disabled = false;

    if (btn) btn.disabled = on;
  }

  async function guarded(btn, fn) {
    if (state.busy) return;
    try {
      setBusy(true, btn);
      await fn();
    } catch (e) {
      toast(String(e.message || e), 5200);
      console.error(e);
    } finally {
      setBusy(false, btn);
    }
  }

  // ---------------- Rendering ----------------
  function setTabs(active) {
    state.filter = active;
    [els.tabAll, els.tabDraft, els.tabApproved, els.tabSent].forEach((t) => t.classList.remove("tabOn"));
    const map = { all: els.tabAll, draft: els.tabDraft, approved: els.tabApproved, sent: els.tabSent };
    (map[active] || els.tabAll).classList.add("tabOn");
    render();
  }

  function setStatusLine() {
    const d = state.plan.date || "(date?)";
    const p = state.plan.platform || "(platform?)";
    const c = state.plan.counts || { draft: 0, approved: 0, sent: 0 };
    els.statusLine.textContent = `date=${d} • platform=${p} • counts: draft=${c.draft} approved=${c.approved} sent=${c.sent} • showing=${filteredItems().length}`;
  }

  function filteredItems() {
    const q = (state.query || "").toLowerCase().trim();
    return (state.plan.items || []).filter((it) => {
      const st = (it.status || "draft").toLowerCase();
      if (state.filter !== "all" && st !== state.filter) return false;
      if (!q) return true;

      const text = [
        it.id, it.topic_id, it.title, it.snippet, it.hashtags, it.platform, it.status
      ].join(" ").toLowerCase();

      return text.includes(q);
    });
  }

  function pillStatusClass(st) {
    st = (st || "draft").toLowerCase();
    if (st === "approved") return "pillStatusApproved";
    if (st === "sent") return "pillStatusSent";
    return "pillStatusDraft";
  }

  async function cycleStatus(item) {
    const order = ["draft", "approved", "sent"];
    const cur = (item.status || "draft").toLowerCase();
    const next = order[(order.indexOf(cur) + 1) % order.length];

    await apiJson(`/api/newsroom/status?date=${encodeURIComponent(state.plan.date)}&platform=${encodeURIComponent(state.plan.platform)}`, {
      method: "POST",
      body: JSON.stringify({ id: item.id, status: next }),
    });

    await loadPlan();
  }

  async function undoStatus(item) {
    await apiJson(`/api/newsroom/undo?date=${encodeURIComponent(state.plan.date)}&platform=${encodeURIComponent(state.plan.platform)}`, {
      method: "POST",
      body: JSON.stringify({ id: item.id }),
    });
    await loadPlan();
  }

  function render() {
    setStatusLine();
    const items = filteredItems();

    els.cards.innerHTML = "";
    for (const it of items) {
      const st = (it.status || "draft").toLowerCase();

      const card = document.createElement("div");
      card.className = "card";

      const top = document.createElement("div");
      top.className = "cardTop";
      top.innerHTML = `
        <span class="pill ${pillStatusClass(st)}">${st.toUpperCase()}</span>
        <span class="pill">${it.platform || ""}</span>
        <span class="pill">${it.id || ""}</span>
      `;

      const title = document.createElement("div");
      title.className = "cardTitle";
      title.textContent = it.title && it.title.trim() ? it.title.trim() : "(no title)";

      const body = document.createElement("div");
      body.className = "cardBody";
      body.textContent = `${(it.snippet || "").trim()}\n\n${(it.hashtags || "").trim()}`.trim();

      const meta = document.createElement("div");
      meta.className = "cardMeta";
      meta.innerHTML = `<span>topic: ${it.topic_id || it.id || ""}</span><span>${it.sent_at ? "sent_at: " + it.sent_at : ""}</span>`;

      const actions = document.createElement("div");
      actions.className = "cardActions";

      const cycleBtn = document.createElement("button");
      cycleBtn.className = "btn btnGhost";
      cycleBtn.textContent = "Cycle";
      cycleBtn.onclick = () => guarded(cycleBtn, () => cycleStatus(it));

      const undoBtn = document.createElement("button");
      undoBtn.className = "btn btnGhost";
      undoBtn.textContent = "Undo";
      undoBtn.onclick = () => guarded(undoBtn, () => undoStatus(it));

      actions.appendChild(cycleBtn);
      actions.appendChild(undoBtn);

      card.appendChild(top);
      card.appendChild(title);
      card.appendChild(body);
      card.appendChild(meta);
      card.appendChild(actions);

      els.cards.appendChild(card);
    }
  }

  // ---------------- Actions ----------------
  async function loadPlan() {
    const d = (els.date.value || "").trim();
    const p = (els.platform.value || "telegram").trim();

    const j = await apiJson(`/api/newsroom/plan?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`, { method: "GET" });
    state.plan.date = j.date;
    state.plan.platform = j.platform;
    state.plan.counts = j.counts || { draft: 0, approved: 0, sent: 0 };
    state.plan.items = j.items || [];
    render();
  }

  async function loadLatest() {
    const p = (els.platform.value || "telegram").trim();
    const j = await apiJson(`/api/newsroom/latest?platform=${encodeURIComponent(p)}`, { method: "GET" });
    els.date.value = j.date;
    await loadPlan();
  }

  async function approveAll() {
    const d = state.plan.date || els.date.value;
    const p = state.plan.platform || els.platform.value;
    await apiJson(`/api/newsroom/approve_all?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`, { method: "POST" });
    await loadPlan();
  }

  async function dryRun() {
    const payload = { date: state.plan.date || els.date.value, platform: state.plan.platform || els.platform.value, dry_run: true, confirm: false };
    const j = await apiJson(`/api/newsroom/run`, { method: "POST", body: JSON.stringify(payload) });
    openModal("Dry-Run Preview", JSON.stringify(j, null, 2));
    await loadPlan();
  }

  async function publishConfirm() {
    if (!confirm("Publish (mark approved items as sent)?")) return;
    const payload = { date: state.plan.date || els.date.value, platform: state.plan.platform || els.platform.value, dry_run: false, confirm: true };
    const j = await apiJson(`/api/newsroom/run`, { method: "POST", body: JSON.stringify(payload) });
    openModal("Publish Result", JSON.stringify(j, null, 2));
    await loadPlan();
  }

  async function importCsvFlow() {
    els.csvFile.click();
  }

  async function doImport(file) {
    const d = state.plan.date || els.date.value;
    const p = state.plan.platform || els.platform.value;

    const fd = new FormData();
    fd.append("file", file);

    const r = await apiFetch(`/api/newsroom/import_csv?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`, {
      method: "POST",
      body: fd,
      headers: {}, // DO NOT set content-type for FormData
    });

    if (!r.ok) {
      const t = await r.text().catch(() => "");
      throw new Error(`${r.status} ${r.statusText} :: ${t}`.trim());
    }

    const j = await r.json();
    toast(`CSV imported: added=${j.added} updated=${j.updated}`);
    await loadPlan();
  }

  async function downloadPlanJson() {
    const d = state.plan.date || els.date.value;
    const p = state.plan.platform || els.platform.value;
    const url = `/api/newsroom/plan?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`;
    await downloadBlob(url, `newsroom_plan_${d}_${p}.json`);
  }

  async function downloadIgCaptions() {
    const d = state.plan.date || els.date.value;
    await downloadBlob(`/api/newsroom/ig_captions?date=${encodeURIComponent(d)}`, `instagram_captions_${d}.txt`);
  }

  async function showLogs() {
    const d = state.plan.date || els.date.value;
    const r = await apiFetch(`/api/newsroom/logs?date=${encodeURIComponent(d)}`, { method: "GET" });
    const t = await r.text();
    openModal("logs.jsonl", t || "(empty)");
  }

  async function showMetrics() {
    const d = state.plan.date || els.date.value;
    const p = state.plan.platform || els.platform.value;
    const j = await apiJson(`/api/newsroom/metrics?date=${encodeURIComponent(d)}&platform=${encodeURIComponent(p)}`, { method: "GET" });
    openModal("Metrics", JSON.stringify(j, null, 2));
  }

  async function copyCurl() {
    if (!state.lastReq) {
      toast("No request recorded yet.");
      return;
    }
    const { method, url, headers, body } = state.lastReq;

    const hdrs = Object.entries(headers || {})
      .map(([k, v]) => `-H "${k}: ${String(v).replace(/"/g, '\\"')}"`)
      .join(" ");

    let cmd = `curl -sS -X ${method} ${hdrs} "http://127.0.0.1:9000${url}"`;
    if (body) {
      const b = typeof body === "string" ? body : "";
      if (b) cmd += ` -d '${b.replace(/'/g, "'\\''")}'`;
    }

    await navigator.clipboard.writeText(cmd);
    toast("curl copied to clipboard.");
  }

  // ---------------- Wire up ----------------
  function todayISO() {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  async function init() {
    // set defaults
    els.date.value = todayISO();
    loadTokenFromLocalStorage();

    // modal
    els.modalClose.onclick = closeModal;
    els.modal.onclick = (e) => { if (e.target === els.modal) closeModal(); };

    // tabs
    els.tabAll.onclick = () => setTabs("all");
    els.tabDraft.onclick = () => setTabs("draft");
    els.tabApproved.onclick = () => setTabs("approved");
    els.tabSent.onclick = () => setTabs("sent");

    // token buttons
    els.saveToken.onclick = () => saveTokenToLocalStorage();
    els.clearToken.onclick = () => clearToken();

    // actions
    els.loadPlan.onclick = () => guarded(els.loadPlan, loadPlan);
    els.latest.onclick = () => guarded(els.latest, loadLatest);
    els.approveAll.onclick = () => guarded(els.approveAll, approveAll);
    els.dryRun.onclick = () => guarded(els.dryRun, dryRun);
    els.publish.onclick = () => guarded(els.publish, publishConfirm);
    els.importBtn.onclick = () => guarded(els.importBtn, importCsvFlow);
    els.browse.onclick = () => guarded(els.browse, downloadPlanJson);
    els.igCaptions.onclick = () => guarded(els.igCaptions, downloadIgCaptions);
    els.logs.onclick = () => guarded(els.logs, showLogs);
    els.metrics.onclick = () => guarded(els.metrics, showMetrics);
    els.copyCurl.onclick = () => guarded(els.copyCurl, copyCurl);

    els.search.onclick = () => { state.query = (els.q.value || "").trim(); render(); };
    els.q.addEventListener("keydown", (e) => { if (e.key === "Enter") { state.query = (els.q.value || "").trim(); render(); } });

    els.csvFile.addEventListener("change", () => {
      const f = els.csvFile.files && els.csvFile.files[0];
      els.csvFile.value = "";
      if (!f) return;
      guarded(els.importBtn, () => doImport(f));
    });

    // ✅ Step 10 start: probe auth & set badge
    await probeAuthEnabled();

    // initial plan
    await guarded(els.loadPlan, loadPlan);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
