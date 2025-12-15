<script>
(function(){
  const $ = (q, el=document)=>el.querySelector(q);
  const $$ = (q, el=document)=>Array.from(el.querySelectorAll(q));
  const API = location.origin;
  const tokenInput = document.querySelector('input[type="text"][placeholder*="token"], #token, [name="token"]') || {value:""};
  const xauth = ()=> tokenInput.value.trim();

  function drawer(){
    const host = document.createElement('div');
    host.id = 'more-drawer';
    host.innerHTML = `
      <h4>Utilities</h4>
      <form id="csvform" enctype="multipart/form-data">
        <label>Import CSV →</label>
        <input type="date" id="csvDate">
        <select id="csvPlat"><option>telegram</option><option>instagram</option></select>
        <input type="file" id="csvFile" accept=".csv">
        <button type="submit">Upload</button>
      </form>
      <form id="roleform">
        <label>Roles → token</label>
        <input type="text" id="roleTok" placeholder="token">
        <select id="roleVal"><option>viewer</option><option>editor</option><option>admin</option></select>
        <button type="submit">Set</button>
        <button type="button" id="roleList">List</button>
      </form>
      <form id="testform">
        <label>Test mode</label>
        <select id="testVal"><option value="true">enable</option><option value="false">disable</option></select>
        <button type="submit">Apply</button>
      </form>
      <pre id="moreOut" style="white-space:pre-wrap;background:#0c1020;padding:10px;border-radius:10px;max-height:240px;overflow:auto"></pre>
    `;
    return host;
  }

  function attach(){
    const panel = drawer();
    const anchor = document.querySelector('main') || document.body;
    anchor.prepend(panel);
    const out = $('#moreOut', panel);
    const headers = ()=> xauth()? {'x-auth':xauth()} : {};

    $('#csvform',panel).addEventListener('submit', async (e)=>{
      e.preventDefault();
      const d = $('#csvDate').value;
      const p = $('#csvPlat').value;
      const f = $('#csvFile').files[0];
      const form = new FormData();
      form.append('date', d);
      form.append('platform', p);
      form.append('file', f);
      const r = await fetch(`${API}/api/newsroom/import_csv`, {method:'POST', headers:headers(), body:form});
      out.textContent = await r.text();
    });

    $('#roleform',panel).addEventListener('submit', async (e)=>{
      e.preventDefault();
      const tok = $('#roleTok').value; const role = $('#roleVal').value;
      const r = await fetch(`${API}/api/newsroom/roles`, {method:'POST', headers:{'content-type':'application/json',...headers()}, body:JSON.stringify({token:tok, role})});
      out.textContent = await r.text();
    });
    $('#roleList',panel).addEventListener('click', async ()=>{
      const r = await fetch(`${API}/api/newsroom/roles`, {headers:headers()});
      out.textContent = await r.text();
    });

    $('#testform',panel).addEventListener('submit', async (e)=>{
      e.preventDefault();
      const enabled = $('#testVal').value === 'true';
      const r = await fetch(`${API}/api/newsroom/test_mode`, {method:'POST', headers:{'content-type':'application/json',...headers()}, body:JSON.stringify({enabled})});
      out.textContent = await r.text();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', attach); else attach();
})();
</script>
