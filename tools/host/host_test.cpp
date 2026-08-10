// Host-side test driver for llm.cpp. Loads the converter's .bin files and runs
// encode → forward → sample exactly like the firmware does, printing to stdout.
//
// Build (from the sketch root):
//   clang++ -std=c++17 -O2 -I tools/host tools/host/host_test.cpp main/llm.cpp -o /tmp/llm_host
// Run:
//   /tmp/llm_host embed/model_neo_q4.bin embed/tok_neo.bin "Summary: ...\nStory:" [opts]
// Options: --max N   --temp F   --top-p F   --seed N   --kv N
//          --top10 (print top-10 logits per step)
//          --slide (mirror the firmware's sliding context window)
//          --sink N (slots pinned across a slide; default = kv/4, as shipped)
//          --old-policy (pin up to half the window — the eviction policy that
//                        threw away the current question)
//          --replay-by-pos (index prefill by KV slot instead of absolute
//                           position — reproduces the pre-fix replay bug)
#include "../../main/llm.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>

static std::vector<uint8_t> slurp(const char* path) {
  FILE* f = fopen(path, "rb");
  if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::vector<uint8_t> v(n);
  if (fread(v.data(), 1, n, f) != (size_t)n) { fprintf(stderr, "short read\n"); exit(1); }
  fclose(f);
  return v;
}

int main(int argc, char** argv) {
  if (argc < 4) { fprintf(stderr, "usage: %s model.bin tok.bin prompt [--max N] [--temp F] [--top-p F] [--seed N] [--kv N] [--top10]\n", argv[0]); return 1; }
  std::string prompt = argv[3];
  int   max_new = 80, kv = 96;
  float temp = 0.0f, top_p = 1.0f;
  unsigned long seed = 1234;
  bool  top10 = false, slide = false, replay_by_pos = false, old_policy = false;
  int   sink = 0;      // 0 = mirror the firmware's KV_SEQ_LEN/SLIDE_DIV pin
  for (int i = 4; i < argc; i++) {
    if (!strcmp(argv[i], "--slide")) { slide = true; continue; }
    if (!strcmp(argv[i], "--replay-by-pos")) { replay_by_pos = true; continue; }
    if (!strcmp(argv[i], "--old-policy")) { old_policy = true; continue; }
    if (!strcmp(argv[i], "--sink")) { sink = atoi(argv[++i]); continue; }
    if (!strcmp(argv[i], "--max"))  max_new = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--temp")) temp = atof(argv[++i]);
    else if (!strcmp(argv[i], "--top-p")) top_p = atof(argv[++i]);
    else if (!strcmp(argv[i], "--seed")) seed = strtoul(argv[++i], nullptr, 10);
    else if (!strcmp(argv[i], "--kv"))   kv = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--top10")) top10 = true;
  }
  // Allow literal "\n" in the prompt argument.
  for (size_t p; (p = prompt.find("\\n")) != std::string::npos;)
    prompt.replace(p, 2, "\n");

  static std::vector<uint8_t> model, tok;
  model = slurp(argv[1]);
  tok   = slurp(argv[2]);

  static Transformer T;
  static Tokenizer   K;
  static Sampler     S;
  if (!llm_init_embedded(&T, model.data(), model.size(), kv)) {
    fprintf(stderr, "model init failed\n"); return 1;
  }
  if (!llm_tokenizer_from_memory(&K, tok.data(), tok.size(), T.config.vocab_size)) {
    fprintf(stderr, "tokenizer init failed\n"); return 1;
  }
  llm_build_sampler(&S, T.config.vocab_size, temp, top_p, seed);
  fprintf(stderr, "arch=%d dim=%d hidden=%d layers=%d heads=%d vocab=%d seq=%d kv=%d\n",
          T.config.arch, T.config.dim, T.config.hidden_dim, T.config.n_layers,
          T.config.n_heads, T.config.vocab_size, T.config.seq_len, T.kv_seq_len);

  // "<|eos|>" markers split the prompt into segments joined by the EOS token
  // id — mirrors how the firmware's chat mode rebuilds multi-turn history.
  std::vector<int> toks(prompt.size() + 16);
  int n_prompt = 0;
  size_t start = 0;
  while (start <= prompt.size()) {
    size_t mark = prompt.find("<|eos|>", start);
    std::string seg = prompt.substr(start, mark == std::string::npos ? std::string::npos
                                                                     : mark - start);
    int m = 0;
    llm_encode(&K, seg.c_str(), 1, 0, toks.data() + n_prompt, &m);
    n_prompt += m;
    if (mark == std::string::npos) break;
    toks[n_prompt++] = K.eos_id;
    start = mark + 7;
  }
  fprintf(stderr, "prompt tokens (%d):", n_prompt);
  for (int i = 0; i < n_prompt; i++) fprintf(stderr, " %d", toks[i]);
  fprintf(stderr, "\n");

  int token = toks[0];
  char scratch[64];
  int  pos = 0, abspos = 0, tokens_out = 0, n_slides = 0;
  std::vector<int> slot_abs(kv, -1);   // slot -> absolute position written there
  // Mirrors main.cpp stepGeneration(). Without --slide the loop stops when the
  // window fills (the pre-sliding behaviour); with it, the window slides and
  // `pos` (physical KV slot) decouples from `abspos` (sequence position).
  for (; tokens_out < max_new; ) {
    if (abspos >= T.config.seq_len - 1) {
      fprintf(stderr, "[stop] position table exhausted at abspos=%d\n", abspos);
      break;
    }
    if (pos >= kv - 1) {
      if (!slide) break;
      if (abspos < n_prompt - 1) { fprintf(stderr, "[bug] slide during prefill\n"); return 2; }
      int keep_head = sink > 0 ? sink : kv / 4;
      if (n_prompt < keep_head) keep_head = n_prompt;
      int evict = kv / 4;
      if (old_policy) {                       // pre-fix: pin up to half the window
        keep_head = n_prompt > kv / 2 ? kv / 2 : n_prompt;
        evict = (kv - keep_head) / 2;
      }
      if (evict < 1) evict = 1;
      evict = llm_kv_slide(&T, keep_head, evict);
      if (evict < 1) { fprintf(stderr, "[stop] slide refused\n"); break; }
      // Mirror the eviction on the slot->abspos shadow map so we can report
      // which prompt tokens are still resident after the slide.
      memmove(slot_abs.data() + keep_head, slot_abs.data() + keep_head + evict,
              (kv - keep_head - evict) * sizeof(int));
      pos -= evict;
      n_slides++;
      std::vector<bool> res(n_prompt, false);
      for (int i = 0; i < pos; i++)
        if (slot_abs[i] >= 0 && slot_abs[i] < n_prompt) res[slot_abs[i]] = true;
      std::string gone;
      for (int i = 0; i < n_prompt; i++) {
        if (res[i]) continue;
        int j = i; while (j + 1 < n_prompt && !res[j + 1]) j++;
        gone += " " + std::to_string(i) + (j > i ? ".." + std::to_string(j) : "");
        i = j;
      }
      fprintf(stderr, "[slide %d] keep=%d evict=%d -> pos=%d abspos=%d | prompt idx dropped:%s\n",
              n_slides, keep_head, evict, pos, abspos, gone.empty() ? " none" : gone.c_str());
      if (replay_by_pos && pos < n_prompt - 1)
        fprintf(stderr, "[bug] pos rewound into prefill range (pos=%d < n_prompt-1=%d)\n",
                pos, n_prompt - 1);
    }
    float* logits = llm_forward_at(&T, token, pos, abspos);
    slot_abs[pos] = abspos;
    int next;
    // --replay-by-pos reproduces the pre-fix indexing (physical slot instead of
    // absolute position), which re-enters prompt replay after a slide.
    int replay_idx = replay_by_pos ? pos : abspos;
    if (replay_idx < n_prompt - 1) {
      if (n_slides > 0)
        fprintf(stderr, "[bug] re-emitting prompt token idx=%d after slide\n", replay_idx + 1);
      next = toks[replay_idx + 1];
    } else {
      if (top10) {
        std::vector<int> idx(T.config.vocab_size);
        for (int i = 0; i < T.config.vocab_size; i++) idx[i] = i;
        std::partial_sort(idx.begin(), idx.begin() + 10, idx.end(),
                          [&](int a, int b) { return logits[a] > logits[b]; });
        fprintf(stderr, "pos %d top10:", pos);
        for (int i = 0; i < 10; i++) fprintf(stderr, " %d:%.3f", idx[i], logits[idx[i]]);
        fprintf(stderr, "\n");
      }
      next = llm_sample(&S, logits);
      if (next == K.eos_id || (K.style == ARCH_LLAMA && (next == 1 || next == 2))) break;
      printf("%s", llm_decode(&K, token, next, scratch, sizeof(scratch)));
      fflush(stdout);
      tokens_out++;
    }
    token = next;
    pos++;
    abspos++;
  }
  printf("\n");
  fprintf(stderr, "[done] tokens_out=%d abspos=%d slides=%d\n", tokens_out, abspos, n_slides);
  return 0;
}
