# -*- coding: utf-8 -*-
def angle_from_title(title: str) -> dict:
    t = (title or "").lower()
    # basic keyword → metaphor/risk map
    if any(k in t for k in ["court","judge","bench","hearing","verdict","order"]):
        return {"one_liner": title.strip(), "metaphor": "courtroom", "style": "rk_lineart", "risk": "high"}
    if any(k in t for k in ["probe","raid","arrest","cbi","ed"]):
        return {"one_liner": title.strip(), "metaphor": "magnifying glass", "style": "rk_lineart", "risk": "med"}
    if any(k in t for k in ["media","anchor","debate","primetime"]):
        return {"one_liner": title.strip(), "metaphor": "microphone", "style": "stencil", "risk": "low"}
    if any(k in t for k in ["budget","gst","inflation","policy","ordinance"]):
        return {"one_liner": title.strip(), "metaphor": "scale", "style": "rk_lineart", "risk": "low"}
    # default
    return {"one_liner": title.strip() or "Satire", "metaphor": "mask", "style": "rk_lineart", "risk": "low"}
