# satyagrah/train/satyagraph_lora_infer.py
"""
Use a trained Satyagraph LoRA adapter to generate satire one-liners.

Usage (from project root):

    # Basic CPU/auto device
    python -m satyagrah.train.satyagraph_lora_infer --date 2025-09-18 --topic-id t1

    # Explicit adapter path
    python -m satyagrah.train.satyagraph_lora_infer --date 2025-09-18 ^
        --topic-id t1 ^
        --adapter-path models/satyagraph_lora_2025-09-18

    # Try DirectML (may or may not work depending on ops)
    python -m satyagrah.train.satyagraph_lora_infer --date 2025-09-18 --topic-id t1 --use-dml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from .satyagraph_lora import pick_device  # reuse the same device picker


def load_example_for_topic(run_date: str, root: Path, topic_id: str) -> Dict[str, Any]:
    run_dir = root / "data" / "runs" / run_date
    path = run_dir / "satyagraph_train.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing JSONL: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("topic_id") == topic_id:
                return obj
    raise KeyError(f"Topic {topic_id!r} not found in {path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.train.satyagraph_lora_infer",
        description="Generate a satirical one-liner using a Satyagraph LoRA adapter.",
    )
    parser.add_argument("--date", required=True, help="Run date, e.g. 2025-09-18")
    parser.add_argument("--topic-id", required=True, help="Topic id, e.g. t1")
    parser.add_argument(
        "--adapter-path",
        help="Directory with LoRA adapter (default: models/satyagraph_lora_<date>)",
    )
    parser.add_argument(
        "--model-name",
        default="gpt2",
        help="Base HF model used during training (default: gpt2)",
    )
    parser.add_argument(
        "--use-dml",
        action="store_true",
        help="Use DirectML if available (torch-directml)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=40,
        help="Max new tokens to generate (default: 40)",
    )

    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]  # D:/AISatyagrah
    run_date = args.date
    topic_id = args.topic_id

    # Find adapter path
    if args.adapter_path:
        adapter_dir = Path(args.adapter_path)
    else:
        adapter_dir = root / "models" / f"satyagraph_lora_{run_date}"

    if not adapter_dir.exists():
        raise FileNotFoundError(f"Adapter directory does not exist: {adapter_dir}")

    # Load example
    ex = load_example_for_topic(run_date, root, topic_id)
    prompt = ex.get("input", "")
    print("=" * 80)
    print("INPUT PROMPT:")
    print(prompt)
    print("=" * 80)

    # Device
    device = pick_device(args.use_dml)
    print(f"[infer] Using device: {device}")

    # Load base + LoRA
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model_name = args.model_name
    print(f"[infer] Loading base model: {base_model_name}")
    base_model = AutoModelForCausalLM.from_pretrained(base_model_name)
    model = PeftModel.from_pretrained(base_model, adapter_dir)
    model.to(device)
    model.eval()

    # Encode prompt
    enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    input_ids = enc["input_ids"].to(device)

    with torch.no_grad():
        gen_ids = model.generate(
            input_ids=input_ids,
            max_new_tokens=args.max_new_tokens,
            do_sample=True,
            top_p=0.9,
            temperature=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    output_text = tokenizer.decode(gen_ids[0], skip_special_tokens=True)
    # Show only the new part after the prompt
    full = output_text.strip()
    if full.startswith(prompt.strip()):
        gen_only = full[len(prompt.strip()):].strip()
    else:
        gen_only = full

    print("\nGENERATED TEXT:")
    print(gen_only.strip() or full)
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
