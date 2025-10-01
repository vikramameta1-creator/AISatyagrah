# -*- coding: utf-8 -*-
import sys, pathlib, datetime
from jinja2 import Template
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]  # D:\AISatyagrah
TPL  = ROOT / "satyagrah" / "layout" / "templates" / "onepager_smoke.html.j2"
CSS  = ROOT / "satyagrah" / "layout" / "templates" / "styles.css"
OUT  = ROOT / "exports"

def render_smoke(date: str | None = None) -> pathlib.Path:
    """Render the simple smoke-test one-pager and return the PNG path."""
    if not TPL.exists():
        sys.exit(f"Missing template: {TPL}")
    if not CSS.exists():
        sys.exit(f"Missing CSS: {CSS}")

    date = date or datetime.date.today().isoformat()
    css = CSS.read_text(encoding="utf-8")
    tpl = Template(TPL.read_text(encoding="utf-8"))

    html = tpl.render(date=date, css=css)
    OUT.mkdir(parents=True, exist_ok=True)
    html_path = OUT / "onepager_smoke.html"
    html_path.write_text(html, encoding="utf-8")

    png_4x5 = OUT / "onepager_smoke_4x5.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width":1080, "height":1350, "deviceScaleFactor":1})
            page.goto(html_path.resolve().as_uri())
            page.wait_for_timeout(300)
            page.screenshot(path=str(png_4x5), full_page=True)
        finally:
            browser.close()
    return png_4x5
