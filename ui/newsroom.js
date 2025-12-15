(() => {
  const $ = (sel) => document.querySelector(sel);
  const byId = (id) => document.getElementById(id);

  const elToken = byId("token");
  const elPlatform = byId("platform");
  const elDate = byId("date");
  const elKpi = byId("kpi");
  const elItems = byId("items");
  const elToast = byId("toast");
  const elCsv = byId("csv");
  const elQ = byId("q");

  const state = {
    items: [],
    tab: "all",
    q: "",
  };

  function toast(msg, ms=2200) {
    if (!elToast) return;
    elToast.textContent = msg;
    elToast.style.display = "block";
    window.clearTimeout(toast._t);
    toast._t = window.setTimeout(() => elToast.style.display = "none", ms);
  }

  function loadPrefs() {
    // token: accept multiple keys
    const savedTok = localStorage.getItem("xauth") || localStorage.getItem("x-auth") || "";
    if (savedTok && elToken && !elToken.value) elToken.value = savedTok;

    const savedPlatform = localStorage.getItem("platform") || "";
    if (savedPlatform && elPlatform) elPlatform.value = savedPlatform;

    const savedDate = localStorage.getItem("date") || "";
    if (savedDate && elDate) elDate.value = savedDate;

    if (elDate && !elDate.value) {
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth()+1).padStart(2,"0");
      const dd = String(today.getDate()).padStart(2,"0");
      elDate.value = `${yyyy}-${mm}-${dd}`;
    }
  }

  function savePrefs() {
    if (elToken) {
      const t = elToken.value.trim();
      if (t) { localStorage.setItem("xauth", t); localStorage.setItem("x-auth", t); }
      else { localStorage.removeItem("xauth"); localStorage.removeItem("x-auth"); }
    }
    if (elPlatform) localStorage.setItem("platform", elPlatform.value);
    if (elDate) localStorage.setItem("date", elDate.value);
  }

  function token() {
    const t = (elToken?.value || "").trim();
    if (t) return t;
    return (localStorage.getItem("xauth") || localStorage.getItem("x-auth") || "").trim();
  }

  async function api(path, opts={}) {
    const headers = Object.assign({}, opts.headers || {});
    const tok = token();
    if (tok) headers["x-auth"] = tok;

    const res = await fetch(path, Object.assign({}, opts, { headers }));
    const ct = (res.headers.get("content-type") || "");
    let data = null;
    if (ct.includes("application/json")) data = await res.json().catch(() => null);
    else data = await res.text().catch(() => null);

    if (!res.ok) {
      const msg = (typeof data === "string") ? data : JSON.stringify(data);
      throw new Error(msg || `HTTP ${res.status}`);
    }
    return data;
  }

  function statusPill(st) {
    const s = (st || "draft").toLowerCase();
    if (s === "sent") return `<span class="pill sent">SENT</span>`;
    if (s === "approved") return `<span class="pill ok">APPROVED</span>`;
    return `<span class="pill warn">DRAFT</span>`;
  }

  function render() {
    const platform = elPlatform?.value || "telegram";
    const date = elDate?.value || "";

    // filter by tab + search
    const q = (state.q || "").toLowerCase().trim();
    const tab = state.tab;

    let items = state.items.slice();
    if (tab !== "all") {
      items = items.filter(it => (it.status || "draft").toLowerCase() === tab);
    }
    if (q) {
      items = items.filter(it => {
        const blob = `${it.id||""} ${it.topic_id||""} ${it.title||""} ${it.snippet||""} ${it.hashtags||""}`.toLowerCase();
        return blob.includes(q);
      });
    }

    elKpi.textContent = `date=${date || "(auto)"} • platform=${platform} • showing=${items.length}`;

    elItems.innerHTML = items.map(it => {
      const title = (it.title && it.title.trim()) ? it.title.trim() : "(no title)";
      const snippet = (it.snippet || "").trim();
      const hashtags = (it.hashtags || "").trim();
      const id = it.id || "";
      const topic = it.topic_id || "";

      return `
      <div class="card" data-id="${id}">
        <div class="row">
          ${statusPill(it.status)}
          <span class="pill">${platform}</span>
          <span class="pill">${id || "?"}</span>
        </div>

        <div class="title">${escapeHtml(title)}</div>
        <div class="snippet">${escapeHtml(snippet)}${hashtags ? "<br><br>"+escapeHtml(hashtags) : ""}</div>

        <div class="foot">
          <div class="mini">${escapeHtml(topic ? "topic: "+topic : "")}</div>
          <div class="row">
            <button class="btn ghost" data-action="cycle" data-id="${id}">Cycle</button>
            <button class="btn" data-action="undo" data-id="${id}">Undo</button>
          </div>
        </div>
      </div>
      `;
    }).join("");

    // wire card buttons
    elItems.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        const action = btn.getAttribute("data-action");
        if (!id) return;

        try {
          if (action === "undo") {
            await undoOne(id);
          } else if (action === "cycle") {
            await cycleStatus(id);
          }
          await loadPlan();
        } catch (e) {
          toast(String(e.message || e));
        }
      });
    });
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#039;");
  }

  async function loadPlan() {
    savePrefs();
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";

    const qs = new URLSearchParams();
    if (date) qs.set("date", date);
    if (platform) qs.set("platform", platform);

    const data = await api(`/api/newsroom/plan?${qs.toString()}`);
    state.items = data.items || [];
    elKpi.textContent = `date=${data.date} • platform=${data.platform} • draft=${data.counts?.draft||0} • approved=${data.counts?.approved||0} • sent=${data.counts?.sent||0}`;
    render();
  }

  async function latestTelegram() {
    savePrefs();
    const data = await api(`/api/newsroom/latest?platform=telegram`);
    if (elDate) elDate.value = data.date;
    if (elPlatform) elPlatform.value = "telegram";
    await loadPlan();
  }

  async function approveAll() {
    savePrefs();
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";
    if (!date) { toast("Pick a date first"); return; }

    const qs = new URLSearchParams({ date, platform });
    const data = await api(`/api/newsroom/approve_all?${qs.toString()}`, { method: "POST" });
    toast(`Approved: ${data.approved}`);
    await loadPlan();
  }

  async function runPipeline(dryRun) {
    savePrefs();
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";
    if (!date) { toast("Pick a date first"); return; }

    const payload = {
      date,
      platform,
      dry_run: !!dryRun,
      confirm: !dryRun
    };

    const data = await api(`/api/newsroom/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    toast(`${dryRun ? "Dry-run" : "Publish"} candidates=${data.candidates} sent=${data.sent}`);
    await loadPlan();
  }

  async function igCaptions() {
    savePrefs();
    const date = elDate.value || "";
    const qs = new URLSearchParams();
    if (date) qs.set("date", date);

    // trigger download
    window.open(`/api/newsroom/ig_captions?${qs.toString()}`, "_blank");
  }

  async function cycleStatus(id) {
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";
    const it = state.items.find(x => x.id === id);
    const st = (it?.status || "draft").toLowerCase();
    const next = (st === "draft") ? "approved" : (st === "approved") ? "sent" : "draft";

    const qs = new URLSearchParams({ date, platform });
    await api(`/api/newsroom/status?${qs.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status: next })
    });
  }

  async function undoOne(id) {
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";
    const qs = new URLSearchParams({ date, platform });

    await api(`/api/newsroom/undo?${qs.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });
  }

  async function importCsv() {
    savePrefs();
    const platform = elPlatform.value || "telegram";
    const date = elDate.value || "";
    if (!date) { toast("Pick a date first"); return; }

    const f = elCsv.files?.[0];
    if (!f) { toast("Choose a CSV file first"); return; }

    const fd = new FormData();
    fd.append("file", f, f.name);

    const qs = new URLSearchParams({ date, platform });

    const data = await api(`/api/newsroom/import_csv?${qs.toString()}`, {
      method: "POST",
      body: fd
    });

    toast(`CSV imported: added=${data.added} updated=${data.updated}`);
    await loadPlan();
  }

  function setTab(tabId, tabName) {
    ["tabAll","tabDraft","tabApproved","tabSent"].forEach(id => {
      const el = byId(id);
      if (!el) return;
      el.classList.toggle("active", id === tabId);
    });
    state.tab = tabName;
    render();
  }

  function doSearch() {
    state.q = (elQ?.value || "").trim();
    render();
  }

  // Wire toolbar
  function wire() {
    byId("loadPlan")?.addEventListener("click", () => loadPlan().catch(e => toast(e.message || String(e))));
    byId("latestTelegram")?.addEventListener("click", () => latestTelegram().catch(e => toast(e.message || String(e))));
    byId("approveAll")?.addEventListener("click", () => approveAll().catch(e => toast(e.message || String(e))));
    byId("dryRun")?.addEventListener("click", () => runPipeline(true).catch(e => toast(e.message || String(e))));
    byId("publish")?.addEventListener("click", () => {
      if (!confirm("Publish now (will mark approved items as SENT)?")) return;
      runPipeline(false).catch(e => toast(e.message || String(e)));
    });
    byId("igCaptions")?.addEventListener("click", () => igCaptions());

    byId("browseBtn")?.addEventListener("click", () => elCsv.click());
    byId("importCsv")?.addEventListener("click", () => importCsv().catch(e => toast(e.message || String(e))));

    byId("doSearch")?.addEventListener("click", doSearch);

    byId("tabAll")?.addEventListener("click", () => setTab("tabAll","all"));
    byId("tabDraft")?.addEventListener("click", () => setTab("tabDraft","draft"));
    byId("tabApproved")?.addEventListener("click", () => setTab("tabApproved","approved"));
    byId("tabSent")?.addEventListener("click", () => setTab("tabSent","sent"));

    elToken?.addEventListener("change", () => { savePrefs(); loadPlan().catch(()=>{}); });
    elPlatform?.addEventListener("change", () => { savePrefs(); loadPlan().catch(()=>{}); });
    elDate?.addEventListener("change", () => { savePrefs(); loadPlan().catch(()=>{}); });
  }

  // Init
  loadPrefs();
  wire();

  // Try initial load (won't break if no token)
  loadPlan().catch(e => {
    // show error text but keep UI alive
    elKpi.textContent = "Error: " + (e.message || String(e));
  });

})();
