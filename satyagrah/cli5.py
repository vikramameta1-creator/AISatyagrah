# -*- coding: utf-8 -*-
"""
satyagrah.cli5

End-to-end Satyagraph pipeline driver.

This ties together the main steps we’ve been running manually:

1. facts_satire      -> builds facts_satire.csv for the date
2. satyagraph_jsonl  -> builds satyagraph_train.jsonl for LoRA
3. lora_train        -> trains LoRA adapter (optional)
4. satyagraph_jokes  -> generates LoRA jokes and updates satire.json
5. exporter_meta     -> writes satyagraph_meta.pdf / .pptx
6. social_csv        -> writes satyagraph_social.csv (snippets + hashtags)

Typical usage from project root:

    python -m satyagrah.cli5 --date 2025-09-18
    python -m satyagrah.cli5 --date 2025-09-18 --with-train off

This script is intentionally “dumb”: it shells out to the per-module CLIs
so each step can be debugged in isolation.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence


ROOT = Path(__file__).resolve().parents[1]


def _quote(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(c) for c in cmd)


def _run_step(step: str, mod: str, args: Sequence[str], env: dict | None = None) -> int:
    """
    Run `python -m <mod> <args...>` as a subprocess.

    Returns process returncode. Logs the command and step id.
    """
    cmd = [sys.executable, "-m", mod, *args]
    print(f"[cli5] STEP {step}: {_quote(cmd)}")
    rc = subprocess.call(cmd, env=env)
    if rc != 0:
        print(f"[cli5] ERROR in {step} (exit code {rc})", file=sys.stderr)
    return rc


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Satyagraph pipeline for a given date."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Run date (YYYY-MM-DD) under data/runs/<date>",
    )
    parser.add_argument(
        "--with-train",
        choices=["on", "off"],
        default="on",
        help="Whether to run the LoRA training step (default: on).",
    )
    parser.add_argument(
        "--use-dml",
        action="store_true",
        help="Use DirectML for LoRA steps (EXPERIMENTAL; may hit safetensors bug).",
    )
    parser.add_argument(
        "--skip-jokes",
        action="store_true",
        help="Skip satyagraph_jokes step.",
    )
    parser.add_argument(
        "--skip-exporter-meta",
        action="store_true",
        help="Skip exporter_meta step.",
    )
    parser.add_argument(
        "--skip-social-csv",
        action="store_true",
        help="Skip publish.social_csv step.",
    )

    args = parser.parse_args(argv)
    day = args.date

    # Shared env – we hint LoRA device via SATYAGRAH_LORA_DEVICE when --use-dml
    env = os.environ.copy()
    if args.use_dml:
        env["SATYAGRAH_LORA_DEVICE"] = "dml"
    else:
        # be explicit so inference scripts fall back to CPU unless user overrides
        env.setdefault("SATYAGRAH_LORA_DEVICE", "cpu")

    # 1) facts_satire (build combined CSV; safe even if already present)
    rc = _run_step(
        "1-facts_satire",
        "satyagrah.analysis.facts_satire",
        ["--date", day, "--write-csv"],
        env=env,
    )
    if rc != 0:
        return rc

    # 2) satyagraph_jsonl (training data)
    rc = _run_step(
        "2-satyagraph_jsonl",
        "satyagrah.analysis.satyagraph_jsonl",
        ["--date", day],
        env=env,
    )
    if rc != 0:
        return rc

    # 3) LoRA training (optional)
    if args.with_train == "on":
        lora_args = ["--date", day]
        if args.use_dml:
            lora_args.append("--use-dml")
        rc = _run_step(
            "3-lora_train",
            "satyagrah.train.satyagraph_lora",
            lora_args,
            env=env,
        )
        if rc != 0:
            return rc
    else:
        print("[cli5] Skipping 3-lora_train (--with-train off).")

    # 4) satyagraph_jokes (optional)
    if not args.skip_jokes:
        rc = _run_step(
            "4-satyagraph_jokes",
            "satyagrah.analysis.satyagraph_jokes",
            ["--date", day],
            env=env,
        )
        if rc != 0:
            return rc
    else:
        print("[cli5] Skipping 4-satyagraph_jokes (--skip-jokes).")

    # 5) exporter_meta (optional)
    if not args.skip_exporter_meta:
        rc = _run_step(
            "5-exporter_meta",
            "satyagrah.exporter_meta",
            ["--date", day],
            env=env,
        )
        if rc != 0:
            return rc
    else:
        print("[cli5] Skipping 5-exporter_meta (--skip-exporter-meta).")

    # 6) social_csv (optional)
    if not args.skip_social_csv:
        out_csv = ROOT / "data" / "runs" / day / "satyagraph_social.csv"
        rc = _run_step(
            "6-social_csv",
            "satyagrah.publish.social_csv",
            ["--date", day, "--outfile", str(out_csv)],
            env=env,
        )
        if rc != 0:
            return rc
    else:
        print("[cli5] Skipping 6-social_csv (--skip-social-csv).")

    print("[cli5] Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
