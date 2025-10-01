# -*- coding: utf-8 -*-
BASE_NEG = "text, watermark, lowres, logo, extra fingers, nsfw, photoreal skin"

STYLE = {
    "rk_lineart": "editorial cartoon, RK Laxman inspired line art, cross-hatching, clean white background, high contrast, sparse red accent",
    "stencil":    "Banksy-like stencil poster, rough wall texture, monochrome with single accent color"
}

def build_prompt(angle: dict, style_default: str = "rk_lineart") -> dict:
    """
    angle = {
      "one_liner": "string",
      "metaphor": "courtroom|puppet|mic|...",
      "style": "rk_lineart|stencil|None",
      "risk": "low|med|high"
    }
    """
    style = angle.get("style") or style_default
    guard = ""
    if angle.get("risk") == "high":
        guard = "generic judge silhouettes, anonymous faces, no real person likeness"
    pos = f"{STYLE.get(style, STYLE['rk_lineart'])}, {angle.get('metaphor','courtroom')} metaphor, {guard}, 4:5 composition, bold headline space"
    # Put the one-liner first so it influences composition
    pos = f"{angle.get('one_liner','Satire')} — " + pos

    return {
        "positive": pos,
        "negative": BASE_NEG,
        "width": 1024,
        "height": 1280,
        "steps": 34,
        "cfg": 6.5,
        "sampler": "DPM++ 2M Karras",
        "seed": 3117,
        "style": style
    }
