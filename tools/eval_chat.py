#!/usr/bin/env python3
"""Masked validation loss of a checkpoint on a val file.

Losses are comparable across checkpoints because all TinyStories models share
the full GPT-2 tokenizer and the same masked encoding (finetune_chat.py).
Typical use — regression-check a new fine-tune against the shipped one on the
frozen val set (which predates the new corpus, so neither model trained on it):

  ../cardputer_ai_venv/bin/python tools/eval_chat.py \
      --model-dir data/chat_model_masked --model-dir data/chat_model_v2
"""

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader, TensorDataset

from finetune_chat import load_blocks, evaluate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", action="append", required=True,
                    help="HF checkpoint dir; repeatable for side-by-side")
    ap.add_argument("--val-file", default="data/eval/val_frozen.txt")
    ap.add_argument("--seq-len", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    from transformers import GPTNeoForCausalLM, GPT2TokenizerFast

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    results = []
    for mdir in args.model_dir:
        tokenizer = GPT2TokenizerFast.from_pretrained(mdir)
        x, y = load_blocks(Path(args.val_file), tokenizer, args.seq_len)
        loader = DataLoader(TensorDataset(x, y), batch_size=args.batch_size)
        model = GPTNeoForCausalLM.from_pretrained(mdir).to(device)
        loss = evaluate(model, loader, device)
        results.append((mdir, loss))
        del model

    print(f"\nmasked val loss on {args.val_file}:")
    for mdir, loss in results:
        print(f"  {loss:.4f}  {mdir}")


if __name__ == "__main__":
    main()
