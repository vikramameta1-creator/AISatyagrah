from __future__ import annotations
import base64, io, random
from typing import Dict, Any
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont

app = FastAPI(title="SD Mock API")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html><html><head><meta charset="utf-8"/>
<title>SD Mock 7860</title>
<style>
 body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}
 .row{margin:8px 0}
 textarea,input,button{font:inherit}
 img{max-width:360px;border:1px solid #ccc;border-radius:8px}
</style></head><body>
<h2>SD Mock API (port 7860)</h2>
<div class="row"><label>Prompt</label></div>
<div class="row"><textarea id="prompt" rows="4" cols="60">A mock image</textarea></div>
<div class="row">
  <button onclick="gen()">Generate</button>
  <span id="status"></span>
</div>
<div class="row"><img id="out"/></div>
<script>
async function gen(){
  document.getElementById('status').textContent = '…';
  const prompt = document.getElementById('prompt').value;
  const res = await fetch('/sdapi/v1/txt2img', {
    method:'POST', headers:{'content-type':'application/json'},
    body: JSON.stringify({prompt})
  });
  const js = await res.json();
  document.getElementById('status').textContent = res.ok ? 'OK' : 'ERROR';
  if(js?.images?.[0]){
    document.getElementById('out').src = 'data:image/png;base64,' + js.images[0];
  }
}
</script></body></html>
"""

@app.get("/health")
def health(): return {"ok": True}

@app.post("/sdapi/v1/txt2img")
def txt2img(payload: Dict[str, Any] = Body(default={})):
    prompt = (payload.get("prompt") or "mock").strip()
    w = int(payload.get("width") or 512)
    h = int(payload.get("height") or 512)
    # make a simple colored card with text
    img = Image.new("RGB", (w, h), (random.randint(64,192), 128, random.randint(64,192)))
    d = ImageDraw.Draw(img)
    text = (prompt[:80] + "…") if len(prompt) > 80 else prompt
    d.text((16,16), f"MOCK\n{text}", fill=(255,255,255))
    buf = io.BytesIO(); img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"images":[b64], "parameters": payload, "info": "{}"}

@app.get("/sdapi/v1/progress")
def progress(): return {"progress": 1.0, "eta_relative": 0}
