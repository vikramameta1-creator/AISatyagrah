# -*- coding: utf-8 -*-
import sys, pathlib, datetime, json, re
from jinja2 import Template
from playwright.sync_api import sync_playwright

ROOT     = pathlib.Path(__file__).resolve().parents[2]
TPL_REAL = ROOT / "satyagrah" / "layout" / "templates" / "onepager_real.html.j2"
CSS      = ROOT / "satyagrah" / "layout" / "templates" / "styles.css"
OUT_ROOT = ROOT / "exports"

_ASPECTS = {
    "4x5":  (1080, 1350),
    "1x1":  (1080, 1080),
    "9x16": (1080, 1920),
}

def _one_liner_from_prompt_json(pjson: dict) -> str:
    pos = pjson.get("positive","")
    parts = [s.strip() for s in pos.split("—", 1)]
    return parts[0] if parts and parts[0] else "Satire"

def _facts_for(date: str, topic_id: str) -> tuple[str, list[str]]:
    f = ROOT / "data" / "runs" / date / "facts.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        t = d.get(topic_id, {})
        return t.get("summary", "No facts yet."), t.get("bullets", [])
    return "No facts yet.", []

def _inject_watermark(html: str, text: str, pos: str = "br", opacity: float = 0.22) -> str:
    pos = (pos or "br").lower()
    # choose anchors
    style_pos = {
        "br": "right:18px; bottom:18px;",
        "bl": "left:18px;  bottom:18px;",
        "tr": "right:18px; top:18px;",
        "tl": "left:18px;  top:18px;",
    }.get(pos, "right:18px; bottom:18px;")

    wm_div = f"""
<div style="
  position:fixed; {style_pos}
  z-index:9999; pointer-events:none; user-select:none;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
  font-size: 14px; letter-spacing:.3px;
  color:#000; opacity:{opacity:.2f};
  background:rgba(255,255,255,0.0);
  padding:6px 10px; border-radius:10px;
  text-shadow: 0 1px 2px rgba(255,255,255,.5);
  mix-blend-mode:multiply;">
  {text}
</div>"""

    # insert before </body> if present
    m = re.search(r"</body\s*>", html, flags=re.IGNORECASE)
    if m:
        i = m.start()
        return html[:i] + wm_div + html[i:]
    return html + wm_div

def render_onepager(
    date: str | None,
    topic_id: str,
    aspect: str = "4x5",
    watermark: str = "off",
    wm_text: str | None = None,
    wm_pos: str = "br",
    wm_opacity: float = 0.22,
) -> pathlib.Path:
    date = date or datetime.date.today().isoformat()

    hero = ROOT / "data" / "runs" / date / "art" / f"{topic_id}_hero.png"
    pjson = ROOT / "data" / "runs" / date / "art" / f"{topic_id}.prompt.json"
    if not hero.exists():
        sys.exit(f"Missing hero image: {hero}")
    if not pjson.exists():
        alt = ROOT / "data" / "runs" / date / "prompts" / f"{topic_id}.prompt.json"
        pjson = alt if alt.exists() else pjson

    if not TPL_REAL.exists():
        sys.exit(f"Missing template: {TPL_REAL}")
    if not CSS.exists():
        sys.exit(f"Missing CSS: {CSS}")

    css = CSS.read_text(encoding="utf-8")
    tpl = Template(TPL_REAL.read_text(encoding="utf-8"))

    one_liner = "Satire"
    if pjson.exists():
        one_liner = _one_liner_from_prompt_json(json.loads(pjson.read_text(encoding="utf-8")))

    summary, bullets = _facts_for(date, topic_id)

    html = tpl.render(
        date=date, css=css,
        hero_src=hero.resolve().as_uri(),
        one_liner=one_liner,
        fuss=summary, facts=bullets
    )

    # optional watermark
    if str(watermark).lower() in ("on","true","1","yes","y"):
        default_text = f"AISatyagrah • {date} • {topic_id}"
        html = _inject_watermark(html, wm_text or default_text, wm_pos, wm_opacity)

    out_dir = OUT_ROOT / date
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "onepager.html"
    html_path.write_text(html, encoding="utf-8")

    # pick size
    aspect = aspect.lower()
    if aspect not in _ASPECTS:
        sys.exit(f"Unknown aspect '{aspect}'. Choose one of: {', '.join(_ASPECTS.keys())}")
    W, H = _ASPECTS[aspect]

    out_png = out_dir / f"onepager_{aspect}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": W, "height": H, "deviceScaleFactor": 1})
            page.goto(html_path.resolve().as_uri())
            page.wait_for_timeout(300)
            page.screenshot(path=str(out_png), full_page=True)
        finally:
            browser.close()
    return out_png
