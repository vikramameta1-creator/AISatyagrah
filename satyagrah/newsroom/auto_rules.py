# D:\AISatyagrah\satyagrah\newsroom\auto_rules.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from satyagrah.paths import ROOT_DIR

RULES_PATH = ROOT_DIR / "config" / "rules.json"


def load_rules() -> Dict[str, List[Dict[str, Any]]]:
    """Load platform-specific auto-approve rules from config/rules.json."""
    if not RULES_PATH.exists():
        return {}
    try:
        data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        # must be dict[str, list[rule]]
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _any_in(text: str, needles: List[str]) -> bool:
    t = text.lower()
    for n in needles:
        if _norm(n) and _norm(n) in t:
            return True
    return False


def _all_in(text: str, needles: List[str]) -> bool:
    t = text.lower()
    for n in needles:
        if not _norm(n) or _norm(n) not in t:
            return False
    return True


def _matches_rule(item: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """Supported keys (all optional; any true → match):
       - any: [str,...]                   -> match if ANY appears anywhere
       - all: [str,...]                   -> match if ALL appear anywhere
       - title_contains: [str,...]
       - snippet_contains: [str,...]
       - hashtags_contains: [str,...]
    """
    title = _norm(item.get("title"))
    snippet = _norm(item.get("snippet") or item.get("joke") or "")
    hashtags = _norm(item.get("hashtags"))
    omni = " ".join([title, snippet, hashtags]).strip().lower()

    # broad checks first
    if isinstance(rule.get("any"), list) and _any_in(omni, rule["any"]):
        return True
    if isinstance(rule.get("all"), list) and _all_in(omni, rule["all"]):
        return True

    # targeted fields
    if isinstance(rule.get("title_contains"), list) and _any_in(title, rule["title_contains"]):
        return True
    if isinstance(rule.get("snippet_contains"), list) and _any_in(snippet, rule["snippet_contains"]):
        return True
    if isinstance(rule.get("hashtags_contains"), list) and _any_in(hashtags, rule["hashtags_contains"]):
        return True

    return False


def apply_auto_approve(items: List[Dict[str, Any]], rules: Dict[str, List[Dict[str, Any]]], platform: Optional[str] = None) -> int:
    """Set status='approved' for draft items that match at least one rule.
       Returns count of items changed.
    """
    if not rules:
        return 0

    changed = 0
    for it in items:
        plat = str(it.get("platform") or "")
        if platform and plat != platform:
            continue
        st = (str(it.get("status") or "") or "draft").lower()
        if st != "draft":
            continue

        for rule in rules.get(plat, []):
            if _matches_rule(it, rule):
                it["status"] = "approved"
                changed += 1
                break
    return changed


def explain_matches(items: List[Dict[str, Any]], rules: Dict[str, List[Dict[str, Any]]], platform: Optional[str] = None):
    """Return which draft rows would be approved by which rule (no mutation)."""
    out = []
    if not rules:
        return out

    for it in items:
        plat = str(it.get("platform") or "")
        if platform and plat != platform:
            continue
        st = (str(it.get("status") or "") or "draft").lower()
        if st != "draft":
            continue

        rule_list = rules.get(plat, [])
        for idx, rule in enumerate(rule_list):
            if _matches_rule(it, rule):
                out.append({
                    "id": it.get("id"),
                    "topic_id": it.get("topic_id"),
                    "platform": plat,
                    "title": it.get("title"),
                    "matched_rule_index": idx,
                    "rule": rule,
                })
                break
    return out
