# overwrite satyagrah\utils\packager.py to add JPGs too
# -*- coding: utf-8 -*-
import json, zipfile, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]

def _date_or_today(d=None):
    return d or datetime.date.today().isoformat()

def _one_liner_from_prompt(pjson: dict) -> str:
    pos = pjson.get("positive","")
    return (pos.split("—",1)[0] or "Satire").strip()

def make_postpack(topic_id: str, date: str | None = None) -> pathlib.Path:
    date = _date_or_today(date)

    run_dir = ROOT / "data" / "runs" / date
    exp_dir = ROOT / "exports" / date
    art_dir = run_dir / "art"
    prompts_dir = run_dir / "prompts"

    sizes = ["4x5","1x1","9x16"]
    pngs = {s: exp_dir / f"onepager_{s}.png"  for s in sizes}
    jpgs = {s: exp_dir / f"onepager_{s}.jpg"  for s in sizes}
    onepager_html = exp_dir / "onepager.html"

    hero_png    = art_dir / f"{topic_id}_hero.png"
    prompt_json = art_dir / f"{topic_id}.prompt.json"
    if not prompt_json.exists():
        prompt_json = prompts_dir / f"{topic_id}.prompt.json"

    caption_path = exp_dir / "caption_en.txt"
    if not caption_path.exists():
        caption = "AI Satyagrah — prototype caption"
        if prompt_json.exists():
            pj = json.loads(prompt_json.read_text(encoding="utf-8"))
            caption = _one_liner_from_prompt(pj)
        exp_dir.mkdir(parents=True, exist_ok=True)
        caption_path.write_text(caption, encoding="utf-8")

    # need hero + at least one PNG or JPG
    any_image = any(p.exists() for p in list(pngs.values()) + list(jpgs.values()))
    if not hero_png.exists():
        raise FileNotFoundError(f"Missing required file: {hero_png}")
    if not any_image:
        raise FileNotFoundError("No one-pager found (need one of the PNG/JPG onepagers).")

    zip_path = exp_dir / "postpack.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # add any onepagers that exist (prefer PNG name, also include JPGs if present)
        for s in sizes:
            if pngs[s].exists(): z.write(pngs[s], arcname=f"onepager_{s}.png")
            if jpgs[s].exists(): z.write(jpgs[s], arcname=f"onepager_{s}.jpg")
        if onepager_html.exists(): z.write(onepager_html, arcname="onepager.html")
        if hero_png.exists():      z.write(hero_png,      arcname=f"art/{hero_png.name}")
        if prompt_json.exists():   z.write(prompt_json,   arcname=f"art/{prompt_json.name}")
        if caption_path.exists():  z.write(caption_path,  arcname="caption_en.txt")
    return zip_path
