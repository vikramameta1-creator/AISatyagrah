# satyagrah/train/satyagraph_lora.py
"""
Tiny LoRA training harness for Satyagraph.

Usage (from project root):
    python -m satyagrah.train.satyagraph_lora --date 2025-09-18

Options:
    --model-name     HuggingFace model id (default: gpt2)
    --output-dir     Where to save LoRA adapter (default: models/satyagraph_lora_<date>)
    --use-dml        Use DirectML (Intel Arc) if available
    --epochs         Training epochs (default: 3)
    --batch-size     Per-device batch size (default: 1)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import torch
from torch.utils.data import Dataset, DataLoader

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    get_linear_schedule_with_warmup,
)

from peft import LoraConfig, get_peft_model, PeftModel


# -----------------------
# Data loading
# -----------------------

def load_satyagraph_examples(run_date: str, root: Path) -> List[Dict[str, Any]]:
    """
    Load examples from data/runs/<date>/satyagraph_train.jsonl.
    """
    run_dir = root / "data" / "runs" / run_date
    path = run_dir / "satyagraph_train.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing JSONL: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


@dataclass
class SatyagraphExample:
    input_text: str
    output_text: str


class SatyagraphDataset(Dataset):
    def __init__(self, examples: List[SatyagraphExample], tokenizer, max_length: int = 512):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        ex = self.examples[idx]
        # Simple supervised fine-tuning: concatenate input + output
        # You can change this to your preferred prompt format later.
        text = ex.input_text.strip()
        if ex.output_text:
            text = text + "\n\nAnswer: " + ex.output_text.strip()

        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        labels = input_ids.clone()

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


# -----------------------
# Training harness
# -----------------------

def pick_device(use_dml: bool) -> torch.device:
    if use_dml:
        try:
            import torch_directml
            return torch_directml.device()
        except Exception as e:
            print(f"[lora] Could not import torch_directml ({e}); falling back to CUDA/CPU.")

    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def create_lora_model(base_model_name: str, device: torch.device):
    print(f"[lora] Loading base model: {base_model_name}")
    model = AutoModelForCausalLM.from_pretrained(base_model_name)
    model.to(device)

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


def train_lora(
    run_date: str,
    model_name: str,
    output_dir: Path,
    root: Path,
    use_dml: bool = False,
    epochs: int = 3,
    batch_size: int = 1,
    lr: float = 5e-5,
):
    device = pick_device(use_dml)
    print(f"[lora] Using device: {device}")

    # Load data
    raw = load_satyagraph_examples(run_date, root)
    examples: List[SatyagraphExample] = []
    for row in raw:
        inp = row.get("input", "").strip()
        out = row.get("output", "").strip()
        if not inp:
            continue
        examples.append(SatyagraphExample(input_text=inp, output_text=out))

    if not examples:
        raise RuntimeError("No usable examples found in JSONL (missing 'input' field).")

    print(f"[lora] Loaded {len(examples)} examples.")

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        # For models like GPT-2, pad_token is not set; use eos_token as pad.
        tokenizer.pad_token = tokenizer.eos_token

    dataset = SatyagraphDataset(examples, tokenizer, max_length=512)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Model + LoRA
    model = create_lora_model(model_name, device)
    model.train()

    # Optimizer + scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    total_steps = epochs * len(loader)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps,
    )

    # Training loop
        # Training loop
    step = 0
    for epoch in range(epochs):
        print(f"[lora] Epoch {epoch + 1}/{epochs}")
        for batch in loader:
            step += 1
            # Move batch to device
            batch = {k: v.to(device) for k, v in batch.items()}

            try:
                outputs = model(**batch)
                loss = outputs.loss
                loss.backward()
            except RuntimeError as e:
                # DirectML (or other backends) sometimes throw vague "unknown error"
                # during backward. For now, stop training early but still save the adapter.
                print(f"[lora] RuntimeError during backward at step {step}: {e}")
                print("[lora] Stopping training early and proceeding to save adapter.")
                break

            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            if step % 10 == 0 or step == 1:
                print(f"[lora] Step {step}/{total_steps}, loss={loss.item():.4f}")
        else:
            # inner loop didn't 'break'
            continue
        # inner loop DID 'break' → break outer loop too
        break


    # Save only the LoRA adapter
        output_dir = Path(models_root) / f"satyagraph_lora_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[lora] Saving LoRA adapter to {output_dir}")

    # IMPORTANT: move to CPU before saving.
    # DirectML (dml) tensors use OpaqueTensorImpl and safetensors can't
    # inspect their storage, which caused:
    #   NotImplementedError: Cannot access storage of OpaqueTensorImpl
    try:
        model_cpu = model.to("cpu")
    except Exception:
        # If anything goes wrong, fall back to the original model object.
        model_cpu = model

    model_cpu.save_pretrained(output_dir)
    print("[lora] Done.")



def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m satyagrah.train.satyagraph_lora",
        description="Tiny LoRA training harness for Satyagraph.",
    )
    parser.add_argument("--date", required=True, help="Run date, e.g. 2025-09-18")
    parser.add_argument(
        "--model-name",
        default="gpt2",
        help="Base HF model to fine-tune (default: gpt2)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for LoRA adapter (default: models/satyagraph_lora_<date>)",
    )
    parser.add_argument(
        "--use-dml",
        action="store_true",
        help="Use DirectML (Intel Arc) via torch-directml if available",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Batch size (default: 1)",
    )

    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]  # project root (D:/AISatyagrah)
    run_date = args.date

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = root / "models" / f"satyagraph_lora_{run_date}"

    train_lora(
        run_date=run_date,
        model_name=args.model_name,
        output_dir=out_dir,
        root=root,
        use_dml=args.use_dml,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
