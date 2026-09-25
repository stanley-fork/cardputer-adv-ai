# Cardputer AI — developer notes

Everything you need to rebuild, retrain, test and hack on Cardputer AI.
Back to the [README](../README.md).

## How the chat model was made

The shipping model is **TinyTalk 2 (8M)**: [roneneldan/TinyStories-Instruct-8M][hf-neo8]
(GPT-Neo) fine-tuned on simple-English dialogues (filtered [allenai/SODA][soda] +
[DailyDialog][dd], formatted `User: ...\nBot: ...<|endoftext|>`, loss masked
to bot replies) mixed with 30% story data so the story skill survives, plus
two small hand-templated skills: kindergarten Q&A it *can* answer (colors,
animal sounds, opposites — `tools/qa_facts.py`) and graceful "I don't know"
replies for questions beyond a tiny model (paired with [SciQ][sciq]
questions). The same recipe on TinyStories-Instruct-3M gave TinyTalk 1.

The engine also still runs the original [Maykeye/TinyLLama-v0][hf-llama]
completion model — the embedded model's header selects the architecture
(LLaMA vs GPT-Neo) at boot. Swap models by re-running the matching converter.

Weights are quantized to **Q4_0** and embedded into the firmware binary, so
flashing through [bmorcelli/Launcher][lc] installs everything in one step —
no SD card, no model partition flashing, no setup.

[hf-neo8]: https://huggingface.co/roneneldan/TinyStories-Instruct-8M
[soda]: https://huggingface.co/datasets/allenai/soda
[dd]: https://huggingface.co/datasets/li2017dailydialog/daily_dialog
[sciq]: https://huggingface.co/datasets/allenai/sciq
[hf-llama]: https://huggingface.co/Maykeye/TinyLLama-v0
[lc]: https://github.com/bmorcelli/Launcher

## Modes

- **chat** (default): turn-taking small talk. The firmware rebuilds the
  training format every turn — recent exchanges joined by EOS tokens — and
  trims the oldest exchanges to fit the prompt budget. `/new` resets the
  conversation. Replies end when the model emits EOS (it learned to stop).
- **story**: wraps your text as `Summary: <text>\nStory:` — type what the
  story should be about, get that story.
- **raw**: plain completion, no wrapper (works with the old LLaMA model too).

Honest limits: kindergarten English and a 72-token context on the 8M model
(80 on the 3M) — about 3 short exchanges of memory. It can answer kindergarten facts it was trained on
(colors, animal sounds, opposites) and is trained to say "I don't know" to
questions beyond it, instead of confabulating — mostly. It's still a
3M-param model; expect charming nonsense at the edges.

## Fine-tune pipeline (rebuild the chat model from scratch)

```sh
../cardputer_ai_venv/bin/python tools/prepare_chat_data.py       # ~15 min
../cardputer_ai_venv/bin/python tools/finetune_chat.py --epochs 2 \
    --warmup 400 --out-dir data/chat_model_v2                    # ~1 h MPS
../cardputer_ai_venv/bin/python tools/convert_tinystories_instruct.py \
    --model-dir data/chat_model_v2 --corpus data/chat_train.txt \
    --min-count 8 --keep-bin
```

The data prep keeps the longest *window* of simple turns per SODA dialogue
(not just the prefix) and renames speakers to TinyStories-frequent names —
together those roughly double the usable-dialogue yield vs the old prefix
filter. Loss is masked to bot replies and story bodies (the model never
trains on producing user turns), and chat samples are tokenized
segment-by-segment in exactly the shapes the firmware feeds at inference.

To compare a new fine-tune against the previous one before flashing:

```sh
# masked val loss on the frozen val set (predates the current corpus)
../cardputer_ai_venv/bin/python tools/eval_chat.py \
    --model-dir data/chat_model_masked --model-dir data/chat_model_v2
# fixed prompt battery through the host harness (facts / IDK / over-refusal)
../cardputer_ai_venv/bin/python tools/eval_battery.py \
    --model old=path/to/old/model_neo_q4.bin,path/to/old/tok_neo.bin \
    --model new=embed/model_neo_q4.bin,embed/tok_neo.bin
```

NOTE: keep the venv (and anything containing PyTorch) outside the repo so
build tooling never walks into torch's headers.

## What's in the box

```
cardputer_ai/
├── platformio.ini             PlatformIO build (espidf framework, IDF 5.5)
├── CMakeLists.txt             plain ESP-IDF build (`idf.py build`) works too
├── sdkconfig.defaults         flash/CPU/WDT config for the Cardputer ADV
├── partitions.csv             6 MB factory app slot for app + embedded model
├── main/                      the ESP-IDF "main" component
│   ├── main.cpp               boot + chat loop + story-mode prompt wrapper
│   ├── llm.{h,cpp}            Q4_0 engine: LLaMA + GPT-Neo forward paths,
│   │                          dual-core matmul, exact byte-level BPE
│   ├── ui.{h,cpp}             chat UI
│   ├── keyboard/              Cardputer keyboard driver, ported to ESP-IDF
│   │                          from m5stack/M5Cardputer v1.1.1 (MIT)
│   ├── model_data.cpp         generated — Q4 model bytes (~5.5 MB for 8M)
│   └── tok_data.cpp           generated — pruned GPT-2 tokenizer (~190 KB)
└── tools/
    ├── prepare_chat_data.py              SODA/DailyDialog/QA/IDK → corpus
    ├── qa_facts.py                       hand-written kindergarten Q&A + deflections
    ├── finetune_chat.py                  masked-loss fine-tune (MPS/CPU)
    ├── eval_chat.py                      masked val loss, old vs new checkpoint
    ├── eval_battery.py / eval_prompts.txt  fixed prompt battery, scored
    ├── convert_tinystories_instruct.py   HF GPT-Neo → Q4_0 + pruned vocab
    ├── convert_tinyllama_v0.py           the old TinyLLama-v0 converter
    ├── host/                             macOS/Linux test harness for llm.cpp
    └── sim/                              screen simulator → docs/media (see below)
```

The display (and board autodetect, power, etc.) comes from the
`m5stack/m5unified` + `m5stack/m5gfx` managed components, resolved from the
ESP Component Registry on first build (`main/idf_component.yml`).

## One-time setup

```sh
python3 -m venv ../cardputer_ai_venv   # keep the venv outside the repo
../cardputer_ai_venv/bin/pip install huggingface_hub tokenizers torch numpy datasets transformers
../cardputer_ai_venv/bin/python tools/convert_tinystories_instruct.py            # base 3M model
../cardputer_ai_venv/bin/python tools/convert_tinystories_instruct.py --model 8M # bigger, ~5MB
```

The converter downloads the model, prunes the 50,257-token GPT-2 vocab to the
~12K tokens the TinyStories dataset actually uses (closed under BPE merge
derivation, so encoding stays exact), quantizes to Q4_0, and writes
**`main/model_data.cpp`** / **`main/tok_data.cpp`**.

Why prune? The full GPT-2 embedding table would be 13M params — bigger than
the 3M transformer itself — and a 50K-logit buffer (196 KB) doesn't fit our
heap. Pruned: ~1.9 MB total model, ~50 KB logits.

## Build & flash

PlatformIO (the `espidf` framework via the [pioarduino] platform, which ships
ESP-IDF v5.5 — the official `espressif32` platform stopped at 5.4):

```sh
pio run                # build → .pio/build/cardputer/firmware.bin
pio run -t upload      # flash over USB
pio device monitor     # serial logs
```

One image covers both the original Cardputer and the ADV: they share the
M5Stamp-S3 module, the keyboard driver is chosen at runtime from
`M5.getBoard()`, and M5Unified autodetects the display. Flash the same
`firmware.bin` to either board.

The same tree is a standard ESP-IDF project, so this works too:

```sh
idf.py build flash monitor
```

Settings that used to be Arduino IDE menu choices (8 MB flash, DIO/80 MHz, no
PSRAM, custom partition table, 240 MHz CPU) live in `sdkconfig.defaults`.

For [bmorcelli/Launcher][lc] installs, ship
`.pio/build/cardputer/firmware.bin` — the partition table in this repo
keeps the factory app at offset 0x10000, which is where Launcher writes it.
(`firmware.factory.bin` in the same directory is the full-flash image:
bootloader + partition table + app, for esptool at offset 0x0.)

**Upgrading from a pre-8M build**: the partition table changed (the unused
SPIFFS partition was removed to make room for the 8M model) and the flash
mode changed DIO→QIO. The flash mode lives in the *bootloader* header, which
Launcher does not rewrite — so for full speed, flash the complete image once
over USB:

```sh
pio run -t upload   # or: esptool.py write_flash 0x0 firmware.factory.bin
```

If boot logs show ~13 MB/s flash bandwidth instead of ~25, the bootloader is
still DIO.

[pioarduino]: https://github.com/pioarduino/platform-espressif32

## Host testing (no hardware needed)

`tools/host/` stubs the ESP32 APIs so the exact engine code runs on your Mac:

```sh
../cardputer_ai_venv/bin/python tools/convert_tinystories_instruct.py --keep-bin --no-cpp
clang++ -std=c++17 -O2 -I tools/host tools/host/host_test.cpp main/llm.cpp -o /tmp/llm_host
/tmp/llm_host embed/model_neo_q4.bin embed/tok_neo.bin \
  "Summary: a girl finds a lost cat.\nStory:" --temp 0.8 --top-p 0.9 --kv 80
```

## Screen simulator (README / press media)

`tools/sim/` runs the firmware's own `main.cpp`, `ui.cpp` and `llm.cpp` on a
Mac with the display swapped for an off-screen M5GFX sprite (same fonts, same
pixels) and the keyboard driven by a script. Time is virtual: every forward
pass is charged the measured on-device 196 ms, so recordings play at real
device speed. The embedded model is the one in `main/model_data.cpp`.

```sh
brew install sdl2 ffmpeg uv    # SDL2 only for M5GFX's host headers — no window opens
tools/sim/record.sh            # → docs/media/*.png, demo.gif, demo.mp4, demo-transcript.txt
```

`tools/sim/demo.txt` is the script (`type`, `enter`, `tab`, `wait`, `seed`,
`snap`, ...). Seeds were picked by running each scene over 20–30 seeds with
`--transcript` and keeping a good one; the text itself is never edited.

## Memory budget (Cardputer ADV, ~280 KB free heap)

| Buffer (8M model, dim=256)           | Bytes    |
|--------------------------------------|----------|
| KV cache, ctx=72, int4 + group scales| ~166 KB  |
| Logits (vocab=12929)                 | ~50 KB   |
| Activations + attention scores       | ~19 KB   |
| FreeRTOS + matmul worker stack       | 5 KB     |

(The 3M model at dim=128 uses an 80-token window and only ~90 KB of KV.)
The KV window is picked from the model header at boot (`kvLenForModel` in
`main/main.cpp`). The converter enforces `--max-vocab` (default 15,500) so
a corpus change can't silently blow the logits budget.

The GPT-Neo KV cache is stored as **int4 with one bf16 scale per 32-element
group** (the LLaMA path keeps bf16) — ~1.2 KB/position at dim=256, which is
what makes a 72-token window fit next to the logits. `KV_SEQ_LEN` lives in
`main/main.cpp`; the model ships 256 position embeddings, so RAM is the
binding constraint, not flash.

## Engine notes

- GPT-Neo forward path: LayerNorm (+bias), learned position embeddings,
  GELU MLP, and — faithful to the original — **no 1/sqrt(d) attention
  scaling**. The alternating "local attention" layers have a 256-token
  window ≥ our context, so they degenerate to global causal attention.
- **ESP32-S3 PIE SIMD matmul** (`main/dot_q4_pie.S`): activations are
  quantized to int8 once per matmul (llama.cpp's Q4_0×Q8_0 scheme), then
  each 32-weight block is 2× `EE.VMULAS.S8.ACCX` — 16 int8 MACs per
  instruction. The CRDP v3 blob stores weights row-planar
  ([bf16 scales | pad | 16-byte nibble groups]) so every vector load is
  16-byte aligned. A boot-time selftest compares the SIMD kernel against
  the scalar reference on real weight rows and refuses to run on mismatch.
  Host builds (and `-DLLM_FORCE_SCALAR`) use the scalar path.
- **KV cache is int4** (nibbles + one bf16 scale per 32-element group,
  Q4_0-style asymmetric). Each head lies inside one scale group, so
  attention applies a single scale per (head, position). Measured on the
  eval battery this matches int8-KV quality — and it's what fits the 8M
  model's 72-token window in SRAM.
- Weights stream from MMU-mapped flash every token, so **flash bandwidth is
  the throughput ceiling** for the 8M model — the build uses QIO + 64-byte
  cache lines, and boot logs the measured flash bandwidth over serial.
- Tokenizer is **exact** GPT-2 byte-level BPE: the blob embeds the merge
  pair table (binary-searched from flash); verified 0 mismatches vs
  HuggingFace on 500 dataset lines.
- Q4 logits match the fp32 HF reference closely (top-3 identical on test
  prompts); divergence in long greedy decodes is normal quantization noise.
- Sampler: greedy at T=0; otherwise softmax + **top-p (nucleus)** sampling
  over the 64 most likely tokens (single pass, no full-vocab sort — a
  min-tracked candidate array costs ~1 compare per vocab entry). Top-p 1.0
  falls back to the exact full-vocab multinomial. Temperature and top-p are
  live in the settings screen.

## What's not great yet

- 72 tokens of context (8M model) ≈ 3 short exchanges of conversational memory; older
  turns silently fall out of the prompt. Within a single reply the window
  now *slides* rather than stopping, so replies can run past it — but
  sliding evicts old context to make room, so a long reply trades memory
  for length.
- Reply length tops out around 250 tokens of *useful* output. That is the
  model, not the firmware: TinyStories-Instruct-8M was fine-tuned at
  `--seq-len 256`, and generating past that (even in PyTorch with full
  attention and no sliding window) degenerates into looping `Summary:`
  fragments. The converter's 256 position embeddings sit right at that
  limit deliberately — exporting more buys tokens the model can't use.
- Only kindergarten facts. Everything else gets a (trained) "I don't know" —
  for real factual Q&A you'd need Wi-Fi + an API, or different hardware.
- ~5 tok/s measured on device for the 8M model (196 ms/token; PIE SIMD +
  QIO + 64-byte cache lines). The ceiling is flash streaming (~30 MB/s,
  ~5.6 MB read per token); the next levers are a harder vocab prune, 120 MHz
  flash (experimental HPM), or batched/speculative decoding.
- Chat quality is bounded by 8M params — noticeably better grammar and
  context-tracking than 3M, still no real-world knowledge.

## Get the model (without a Cardputer)

The chat fine-tune is published as **TinyTalk 2**:

- [TheREZOR/TinyTalk-2](https://huggingface.co/TheREZOR/TinyTalk-2) —
  safetensors (transformers, GPT-Neo), with embedded chat template
- [TheREZOR/TinyTalk-2-GGUF](https://huggingface.co/TheREZOR/TinyTalk-2-GGUF) —
  GGUF for llama.cpp / Ollama: `ollama run hf.co/TheREZOR/TinyTalk-2-GGUF`
  (GGUF uses a mathematically-exact GPT-2 conversion, `tools/export_gpt2.py`,
  since llama.cpp doesn't support plain GPT-Neo)
- [TheREZOR/TinyTalk](https://huggingface.co/TheREZOR/TinyTalk) — v1 (3M)
