(() => {
  const KEY = "AISATYAGRAH_AUTH_TOKEN";
  const $ = (s) => document.querySelector(s);

  function init() {
    const tok = $("#token");
    if (!tok) return;

    // restore token on load
    try {
      const saved = localStorage.getItem(KEY);
      if (saved && !tok.value) tok.value = saved;
    } catch {}

    // autosave on typing
    tok.addEventListener("input", () => {
      try { localStorage.setItem(KEY, tok.value.trim()); } catch {}
    });

    // add a visible Save button (so it feels explicit)
    if (document.getElementById("btnSaveToken")) return;
    const btn = document.createElement("button");
    btn.id = "btnSaveToken";
    btn.type = "button";
    btn.textContent = "Save token";
    btn.style.marginLeft = "8px";
    btn.onclick = () => {
      try { localStorage.setItem(KEY, tok.value.trim()); } catch {}
      alert("Token saved in this browser.");
    };
    tok.parentElement?.appendChild(btn);
  }

  window.addEventListener("DOMContentLoaded", init);
})();
