#!/usr/bin/env python3
"""Export the GPT-Neo chat fine-tune as a mathematically-equivalent GPT-2
checkpoint, for toolchains that don't support plain GPT-Neo (llama.cpp/GGUF,
and therefore Ollama).

Why this is exact (at ctx <= n_positions):
  - GPT-Neo skips the 1/sqrt(head_dim) attention scaling that GPT-2 applies.
    Compensation: multiply q_proj weights by sqrt(head_dim), so GPT-2's
    (q*s)·k / sqrt(d) == q·k.
  - GPT-Neo's alternating "local" attention layers have a 256-token window;
    with n_positions = 256 every position sees the full causal context, so
    local == global.
  - Everything else matches: pre-LN blocks, learned position embeddings,
    gelu_new MLP, tied lm_head. Layout differences are mechanical: GPT-Neo
    uses separate biasless q/k/v Linears + out_proj; GPT-2 uses a fused
    c_attn Conv1D (weights transposed, i.e. [in, out]) with bias.

The script asserts logit parity and identical greedy decodes before saving.

Usage:
  ../cardputer_ai_venv/bin/python tools/export_gpt2.py \
      --model-dir data/chat_model_8m --out-dir data/chat_model_8m_gpt2
"""

import argparse
import json
import math
from pathlib import Path

import torch

CHAT_TEMPLATE = (
    "{% for m in messages %}"
    "{% if m['role'] == 'user' %}User: {{ m['content'] }}\n"
    "{% else %}Bot: {{ m['content'] }}<|endoftext|>\n{% endif %}"
    "{% endfor %}Bot:"
)

TEST_PROMPTS = [
    "User: hi! how are you today?\nBot:",
    "User: what color is the sky?\nBot:",
    "User: what is the capital of France?\nBot:",
    "User: i had a great day at school!\nBot:",
    "User: what sound does a dog make?\nBot:",
    "User: do you want to play a game?\nBot:",
    "Summary: a girl finds a lost cat.\nStory:",
    "Summary: two friends build a sand castle.\nStory:",
    "User: hello!\nBot: Hi! How are you?<|endoftext|>\nUser: i am good. and you?\nBot:",
    "Once upon a time, there was a",
]


def convert(neo, n_positions):
    from transformers import GPT2Config, GPT2LMHeadModel

    ncfg = neo.config
    head_dim = ncfg.hidden_size // ncfg.num_heads
    cfg = GPT2Config(
        vocab_size=ncfg.vocab_size,
        n_positions=n_positions,
        n_embd=ncfg.hidden_size,
        n_layer=ncfg.num_layers,
        n_head=ncfg.num_heads,
        activation_function="gelu_new",
        layer_norm_epsilon=ncfg.layer_norm_epsilon,
        bos_token_id=ncfg.bos_token_id,
        eos_token_id=ncfg.eos_token_id,
        # disable regularization-time dropout mismatches in eval anyway
        resid_pdrop=0.0, embd_pdrop=0.0, attn_pdrop=0.0,
    )
    gpt2 = GPT2LMHeadModel(cfg)

    ns = neo.state_dict()
    gs = gpt2.state_dict()

    def put(name, tensor):
        assert name in gs, name
        assert gs[name].shape == tensor.shape, (name, gs[name].shape, tensor.shape)
        gs[name] = tensor.clone()

    put("transformer.wte.weight", ns["transformer.wte.weight"])
    put("transformer.wpe.weight", ns["transformer.wpe.weight"][:n_positions])
    put("transformer.ln_f.weight", ns["transformer.ln_f.weight"])
    put("transformer.ln_f.bias", ns["transformer.ln_f.bias"])

    d = ncfg.hidden_size
    scale = math.sqrt(head_dim)
    for l in range(ncfg.num_layers):
        n = f"transformer.h.{l}"
        put(f"{n}.ln_1.weight", ns[f"{n}.ln_1.weight"])
        put(f"{n}.ln_1.bias", ns[f"{n}.ln_1.bias"])
        put(f"{n}.ln_2.weight", ns[f"{n}.ln_2.weight"])
        put(f"{n}.ln_2.bias", ns[f"{n}.ln_2.bias"])

        # fused qkv: GPT-2 Conv1D weight is [in, 3*out] = Linear weight
        # transposed; q pre-scaled to absorb GPT-2's 1/sqrt(head_dim)
        q = ns[f"{n}.attn.attention.q_proj.weight"] * scale
        k = ns[f"{n}.attn.attention.k_proj.weight"]
        v = ns[f"{n}.attn.attention.v_proj.weight"]
        put(f"{n}.attn.c_attn.weight", torch.cat([q, k, v], dim=0).t())
        put(f"{n}.attn.c_attn.bias", torch.zeros(3 * d))
        put(f"{n}.attn.c_proj.weight",
            ns[f"{n}.attn.attention.out_proj.weight"].t())
        put(f"{n}.attn.c_proj.bias", ns[f"{n}.attn.attention.out_proj.bias"])

        put(f"{n}.mlp.c_fc.weight", ns[f"{n}.mlp.c_fc.weight"].t())
        put(f"{n}.mlp.c_fc.bias", ns[f"{n}.mlp.c_fc.bias"])
        put(f"{n}.mlp.c_proj.weight", ns[f"{n}.mlp.c_proj.weight"].t())
        put(f"{n}.mlp.c_proj.bias", ns[f"{n}.mlp.c_proj.bias"])

    gpt2.load_state_dict(gs)
    gpt2.tie_weights()
    return gpt2


@torch.no_grad()
def verify(neo, gpt2, tokenizer):
    neo.eval(); gpt2.eval()
    worst = 0.0
    for p in TEST_PROMPTS:
        ids = tokenizer(p, return_tensors="pt").input_ids
        a = neo(ids).logits
        b = gpt2(ids).logits
        d = (a - b).abs().max().item()
        worst = max(worst, d)
        ga = neo.generate(ids, max_new_tokens=40, do_sample=False,
                          pad_token_id=tokenizer.eos_token_id)
        gb = gpt2.generate(ids, max_new_tokens=40, do_sample=False,
                           pad_token_id=tokenizer.eos_token_id)
        assert torch.equal(ga, gb), f"greedy decode diverged on: {p!r}"
    print(f"[+] parity: max |dlogit| = {worst:.2e} over {len(TEST_PROMPTS)} prompts, "
          f"greedy decodes identical")
    assert worst < 1e-3, "logit parity failed"


def add_chat_template(model_dir: Path):
    p = model_dir / "tokenizer_config.json"
    cfg = json.loads(p.read_text()) if p.exists() else {}
    cfg["chat_template"] = CHAT_TEMPLATE
    p.write_text(json.dumps(cfg, indent=2))
    print(f"[+] chat template -> {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="data/chat_model_8m")
    ap.add_argument("--out-dir", default="data/chat_model_8m_gpt2")
    ap.add_argument("--n-positions", type=int, default=256,
                    help="context length of the export (fine-tune used 256)")
    args = ap.parse_args()

    from transformers import GPTNeoForCausalLM, GPT2TokenizerFast

    neo = GPTNeoForCausalLM.from_pretrained(args.model_dir)
    tokenizer = GPT2TokenizerFast.from_pretrained(args.model_dir)
    print(f"[+] loaded {args.model_dir}: dim={neo.config.hidden_size} "
          f"layers={neo.config.num_layers} heads={neo.config.num_heads}")

    gpt2 = convert(neo, args.n_positions)
    verify(neo, gpt2, tokenizer)

    out = Path(args.out_dir)
    gpt2.save_pretrained(out)
    tokenizer.save_pretrained(out)
    add_chat_template(out)
    add_chat_template(Path(args.model_dir))
    print(f"[+] saved GPT-2 export to {out}")


if __name__ == "__main__":
    main()
