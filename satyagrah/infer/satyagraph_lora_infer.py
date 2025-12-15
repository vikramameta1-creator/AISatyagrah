# -*- coding: utf-8 -*-
"""
satyagrah.infer.satyagraph_lora_infer

Tiny LoRA inference harness used by /api/satyagraph/joke.

- Loads base model (default: gpt2)
- Loads LoRA adapter from models/satyagraph_lora_<date> under AISatyagrah root
- Exposes: generate_lora_joke_for_row(row, run_date)

Environment:
- AISATYAGRAH_ROOT (optional) -> project root (defaults to D:\\AISatyagrah or parents[2])
- SATYAGRAH_LORA_DEVICE (optional) -> 'cpu' (default) or 'cuda'
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# -------------------- ROOT / MODELS --------------------


def _root_default() -> Path:
    d = Path(r"D:\AISatyagrah")
    if d.exists():
        return d
    # fall back to two levels up (…/AISatyagrah)
    return Path(__file__).resolve().parents[2]


ROOT: Path = Path(os.environ.get("AISATYAGRAH_ROOT") or _root_default()).resolve()
MODELS_DIR: Path = ROOT / "models"

BASE_MODEL_NAME = os.environ.get("SATYAGRAH_BASE_MODEL", "gpt2")

# -------------------- GLOBALS / DEVICE --------------------

_tokenizer: AutoTokenizer | None = None
_base_model: AutoModelForCausalLM | None = None
_lora_cache: Dict[str, PeftModel] = {}
_device: torch.device | None = None


def _get_device() -> torch.device:
    global _device
    if _device is not None:
        return _device

    dev_str = os.environ.get("SATYAGRAH_LORA_DEVICE", "cpu").lower()
    if dev_str == "cuda" and torch.cuda.is_available():
        _device = torch.device("cuda")
    else:
        # For now we keep it simple: CPU by default.
        # You can change env to 'cuda' once 3060 is wired.
        _device = torch.device("cpu")

    print(f"[satyagraph_lora_infer] Using device: {_device}")
    return _device


def _load_base() -> Tuple[AutoTokenizer, AutoModelForCausalLM]:
    global _tokenizer, _base_model
    if _tokenizer is not None and _base_model is not None:
        return _tokenizer, _base_model  # type: ignore[return-value]

    print(f"[satyagraph_lora_infer] Loading base model: {BASE_MODEL_NAME}")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dev = _get_device()
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL_NAME)
    model.to(dev)
    model.eval()

    _tokenizer = tok
    _base_model = model
    return tok, model


def _find_lora_dir(run_date: str) -> Path:
    """
    Try models/satyagraph_lora_<run_date>*; fall back to latest satyagraph_lora_*.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    pref = f"satyagraph_lora_{run_date}"
    candidates = sorted(MODELS_DIR.glob(pref + "*"))
    if candidates:
        return candidates[-1]

    # Fallback: latest LoRA adapter if specific date not found
    generic = sorted(MODELS_DIR.glob("satyagraph_lora_*"))
    if not generic:
        raise FileNotFoundError(
            f"No LoRA adapter found under {MODELS_DIR} (expected satyagraph_lora_{run_date}*)"
        )
    return generic[-1]


def _load_lora_model(run_date: str) -> Tuple[AutoTokenizer, PeftModel]:
    tok, base = _load_base()
    key = run_date or "default"

    if key in _lora_cache:
        return tok, _lora_cache[key]

    lora_dir = _find_lora_dir(run_date)
    print(f"[satyagraph_lora_infer] Loading LoRA adapter from: {lora_dir}")
    model = PeftModel.from_pretrained(base, lora_dir)
    model.to(_get_device())
    model.eval()
    _lora_cache[key] = model
    return tok, model


# -------------------- PROMPT + GENERATION --------------------


def _build_prompt(row: Dict[str, Any]) -> str:
    """
    Build a short satirical prompt from the topic row.

    Uses (in priority order): one_liner, summary, title.
    """
    title = (row.get("title") or "").strip()
    summary = (row.get("summary") or "").strip()
    one_liner = (row.get("one_liner") or "").strip()

    base = one_liner or summary or title
    if not base:
        base = "A vague political news headline in India."

    prompt = (
        "You are a witty but responsible Indian political satirist.\n"
        "Given the following news summary, write ONE short, sharp joke (1–2 lines).\n"
        "- No hate speech, no slurs, no personal attacks.\n"
        "- Aim for clever wordplay and irony.\n\n"
        f"News: {base}\n"
        "Joke:"
    )
    return prompt


def generate_lora_joke_for_row(
    row: Dict[str, Any],
    run_date: str,
    max_new_tokens: int = 64,
) -> str:
    """
    Main entry point used by jobs_api.py

    :param row: topic row dict from build_topic_rows(...)
    :param run_date: 'YYYY-MM-DD' (used to locate the LoRA adapter folder)
    :param max_new_tokens: maximum tokens to generate
    :return: string joke (trimmed, single snippet)
    """
    tok, model = _load_lora_model(run_date)
    prompt = _build_prompt(row)

    inputs = tok(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_p=0.9,
            temperature=0.9,
            pad_token_id=tok.eos_token_id,
        )

    text = tok.decode(out[0], skip_special_tokens=True)

    # Extract joke after "Joke:"
    if "Joke:" in text:
        joke = text.split("Joke:", 1)[1].strip()
    else:
        # Fallback: strip the prompt off
        joke = text[len(prompt) :].strip()

    # Limit length for UI / social snippets
    joke = joke.replace("\n", " ").strip()
    if len(joke) > 280:
        joke = joke[:277].rstrip() + "..."

    if not joke:
        joke = "(*model returned an empty joke*)"

    return joke
