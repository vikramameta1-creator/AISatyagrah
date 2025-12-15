from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

# ---------------------------------------------------------------------------
# Category & emoji helpers
# ---------------------------------------------------------------------------

CATEGORY_EMOJI = {
    "election": "🗳️",
    "scandal": "🚨",
    "corruption": "🚨",
    "crime": "🚔",
    "economy": "💰",
    "business": "💼",
    "environment": "🌱",
    "climate": "🌱",
    "diplomacy": "🌍",
    "foreign": "🌍",
    "protest": "✊",
    "rights": "✊",
    "judiciary": "⚖️",
    "default": "📰",
}


@dataclass
class NormalisedItem:
    id: str
    category: str
    title: str
    summary: str
    snippet: str
    hashtags: str
    date: str  # ISO YYYY-MM-DD or ""


def _get_str(item: Mapping[str, Any], key: str) -> str:
    v = item.get(key, "")
    if v is None:
        return ""
    return str(v).strip()


def _infer_category(item: Mapping[str, Any]) -> str:
    """Try to infer a high-level category from explicit column or keywords."""
    raw = _get_str(item, "category").lower()

    if not raw:
        # fall back to simple keyword scan over title / summary
        text = (
            _get_str(item, "title") + " " +
            _get_str(item, "summary") + " " +
            _get_str(item, "snippet")
        ).lower()
    else:
        text = raw

    def has(*words: str) -> bool:
        return any(w in text for w in words)

    if has("poll", "vote", "voting", "election", "constituency", "seat"):
        return "election"
    if has("scam", "fraud", "sting", "embezzle", "kickback"):
        return "scandal"
    if has("corruption", "bribe", "bribery"):
        return "corruption"
    if has("murder", "assault", "robbery", "arrest", "fir", "crime"):
        return "crime"
    if has("gdp", "inflation", "market", "stock", "rupee", "tax", "budget"):
        return "economy"
    if has("climate", "pollution", "air quality", "rain", "drought", "forest"):
        return "environment"
    if has("foreign", "diplomat", "embassy", "border", "china", "pakistan"):
        return "diplomacy"
    if has("protest", "rally", "dharna", "march"):
        return "protest"
    if has("court", "verdict", "supreme court", "high court", "judge"):
        return "judiciary"

    if raw:
        # if category was explicitly set but not matched, keep it
        return raw

    return "default"


def _emoji_for(item: Mapping[str, Any]) -> str:
    cat = _infer_category(item)
    # normalise key
    key = cat.lower().strip()
    if key in CATEGORY_EMOJI:
        return CATEGORY_EMOJI[key]
    # map some fuzzy categories
    if "econom" in key or "finance" in key or "market" in key:
        return CATEGORY_EMOJI["economy"]
    if "env" in key or "climate" in key or "green" in key:
        return CATEGORY_EMOJI["environment"]
    if "elect" in key or "poll" in key:
        return CATEGORY_EMOJI["election"]
    if "court" in key or "judic" in key:
        return CATEGORY_EMOJI["judiciary"]
    if "crime" in key or "scam" in key:
        return CATEGORY_EMOJI["crime"]
    return CATEGORY_EMOJI["default"]


def _normalise(item: Mapping[str, Any]) -> NormalisedItem:
    topic_id = _get_str(item, "id") or _get_str(item, "topic_id") or "item"
    cat = _infer_category(item)
    title = _get_str(item, "title")
    summary = _get_str(item, "summary")
    snippet = _get_str(item, "snippet")
    hashtags = _get_str(item, "hashtags")
    date = _get_str(item, "date")

    # Choose best “body” sentence:
    # 1) summary, 2) snippet (without hashtags), 3) title itself
    body = summary
    if not body:
        # try to strip hashtags from snippet
        if snippet and "#" in snippet:
            body = snippet.split("#", 1)[0].strip()
        else:
            body = snippet
    if not body:
        body = title

    # Truncate excessively long body for messaging
    if body and len(body) > 500:
        body = body[:497].rstrip() + "..."

    return NormalisedItem(
        id=topic_id,
        category=cat,
        title=title or body,
        summary=body,
        snippet=snippet,
        hashtags=hashtags,
        date=date,
    )


# ---------------------------------------------------------------------------
# Telegram formatting
# ---------------------------------------------------------------------------


def _escape_html(text: str) -> str:
    """Very small HTML escape for Telegram <b> mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_telegram(item: Mapping[str, Any]) -> str:
    """
    Build a nicely formatted Telegram message with:

        <b>🗳️ Title</b>

        Summary sentence.

        #hashtags

        YYYY-MM-DD
    """
    n = _normalise(item)
    emoji = _emoji_for(item)

    title = _escape_html(n.title) if n.title else ""
    body = _escape_html(n.summary) if n.summary else ""
    hashtags = n.hashtags
    date = n.date

    parts = []

    if title:
        parts.append(f"<b>{emoji} {title}</b>")
    elif emoji:
        parts.append(emoji)

    if body:
        parts.append(body)

    if hashtags:
        parts.append(hashtags)

    if date:
        parts.append(date)

    return "\n\n".join(parts).strip() or "(empty message)"


# ---------------------------------------------------------------------------
# Instagram formatting
# ---------------------------------------------------------------------------


def format_instagram_caption(item: Mapping[str, Any]) -> str:
    """
    Instagram caption style:

        🗳️ Title

        Summary sentence.

        #hashtags

        YYYY-MM-DD
    """
    n = _normalise(item)
    emoji = _emoji_for(item)

    title_line = f"{emoji} {n.title}" if n.title else emoji
    lines = []

    if title_line.strip():
        lines.append(title_line.strip())

    if n.summary and n.summary != n.title:
        lines.append("")  # blank line
        lines.append(n.summary)

    if n.hashtags:
        lines.append("")
        lines.append(n.hashtags)

    if n.date:
        lines.append("")
        lines.append(n.date)

    return "\n".join(lines).strip()


# Backwards-compat alias if older code calls format_instagram(...)
def format_instagram(item: Mapping[str, Any]) -> str:
    return format_instagram_caption(item)
