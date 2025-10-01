# -*- coding: utf-8 -*-
# Minimal i18n shim for captions. Offline-friendly: no network calls.
# If you later add a real translator, plug it in here.
def make_caption_lines(one_liner: str, summary: str, lang: str = "en") -> list[str]:
    lang = (lang or "en").lower()
    if lang == "hi":
        return [
            f"आज का व्यंग्य: {one_liner}",
            f"सार: {summary}",
            "👇 अपनी राय बताइए"
        ]
    # default: English
    return [
        f"Today’s satire: {one_liner}",
        f"Summary: {summary}",
        "👇 Tell us what you think"
    ]
