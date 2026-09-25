// Cardputer AI screen simulator: runs the firmware's own main.cpp + ui.cpp +
// llm.cpp on a host, with the display swapped for an off-screen M5GFX sprite
// and the keyboard driven by a script. Time is virtual: every forward pass
// costs the measured on-device latency, so recordings play at device speed.
//
// Usage: sim SCRIPT OUT.rgb [--fps N] [--seed N] [--ms-per-token N] [--snap-dir DIR]
//          [--transcript]   (print the chat scrollback as text at the end)
//   Writes raw 240x135 rgb24 frames to OUT.rgb; see tools/sim/record.sh.
//
// Script lines:  wait MS | type TEXT | enter | tab | key C | snap NAME
//                snapgen NAME N  (snap once the next reply reaches N tokens)
//                seed N  (re-seed the sampler as if booted with --seed N)
//                # comment
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include "llm.h"

uint64_t g_sim_us = 0;
static uint32_t g_rng = 1;
uint32_t esp_random() { g_rng = g_rng * 1664525u + 1013904223u; return g_rng; }

static int g_ms_per_token = 196;   // 8M model, measured on the Cardputer ADV
static float* sim_forward_at(Transformer* t, int token, int slot, int abspos) {
  g_sim_us += (uint64_t)g_ms_per_token * 1000;
  return llm_forward_at(t, token, slot, abspos);
}
static float* sim_forward(Transformer* t, int token, int pos) {
  return llm_forward(t, token, pos);   // boot benchmark only; not recorded
}

// Scrollback is read back for --transcript (seed sweeps).
#define private public
#include "ui.h"
#undef private

// Pull in the firmware (a copy, so its quoted includes resolve to our shims).
#define app_main firmware_app_main
#define llm_forward_at sim_forward_at
#define llm_forward sim_forward
#include "main_fw.cpp"
#undef llm_forward_at
#undef llm_forward

#include "keyboard/Keyboard.h"
Keyboard_Class::KeysState Keyboard_Class::pending;
bool Keyboard_Class::has_pending = false;
SimM5 M5;

static FILE*    g_out = nullptr;
static int      g_fps = 20;
static uint64_t g_next_frame_us = 0;
static long     g_frames = 0;
static std::string g_snap_dir = ".";

static void grab(uint8_t* rgb) {
  auto* buf = (const uint16_t*)M5.Display.getBuffer();
  for (int i = 0; i < 240 * 135; i++) {
    uint16_t v = __builtin_bswap16(buf[i]);          // sprite stores swapped RGB565
    rgb[i*3+0] = ((v >> 11) & 31) * 255 / 31;
    rgb[i*3+1] = ((v >> 5)  & 63) * 255 / 63;
    rgb[i*3+2] = ( v        & 31) * 255 / 31;
  }
}

static void pump() {   // emit every frame whose timestamp has passed
  static uint8_t rgb[240 * 135 * 3];
  if (g_sim_us < g_next_frame_us) return;
  grab(rgb);
  while (g_sim_us >= g_next_frame_us) {
    fwrite(rgb, 1, sizeof(rgb), g_out);
    g_frames++;
    g_next_frame_us += 1000000ull / g_fps;
  }
}

static void advance(uint64_t ms) {
  uint64_t end = g_sim_us + ms * 1000;
  while (g_sim_us < end) { g_sim_us += 1000; pump(); }
}

static void snap(const std::string& name);
static std::string g_gen_snap;       // "snapgen": grab a still mid-reply
static int         g_gen_snap_at = 0;

static void press(Keyboard_Class::KeysState st) {
  Keyboard_Class::pending = st;
  Keyboard_Class::has_pending = true;
  loop();
  while (gen.active) {
    loop(); pump();
    if (g_gen_snap.size() && gen.tokens_out >= g_gen_snap_at) { snap(g_gen_snap); g_gen_snap.clear(); }
  }
}

static void snap(const std::string& name) {
  static uint8_t rgb[240 * 135 * 3];
  grab(rgb);
  fprintf(stderr, "snap %s at %.1f s\n", name.c_str(), (double)g_sim_us / 1e6);
  std::string path = g_snap_dir + "/" + name + ".ppm";
  FILE* f = fopen(path.c_str(), "wb");
  if (!f) { perror(path.c_str()); exit(1); }
  fprintf(f, "P6\n240 135\n255\n");
  fwrite(rgb, 1, sizeof(rgb), f);
  fclose(f);
}

int main(int argc, char** argv) {
  if (argc < 3) { fprintf(stderr, "usage: %s script out.rgb [--fps N] [--seed N] [--ms-per-token N] [--snap-dir D]\n", argv[0]); return 1; }
  bool transcript = false;
  for (int i = 3; i < argc; i++) {
    if (!strcmp(argv[i], "--transcript")) { transcript = true; continue; }
    if (i + 1 >= argc) break;
    if      (!strcmp(argv[i], "--fps"))          g_fps = atoi(argv[i+1]);
    else if (!strcmp(argv[i], "--seed"))         g_rng = (uint32_t)atol(argv[i+1]);
    else if (!strcmp(argv[i], "--ms-per-token")) g_ms_per_token = atoi(argv[i+1]);
    else if (!strcmp(argv[i], "--snap-dir"))     g_snap_dir = argv[i+1];
    i++;
  }
  FILE* sf = fopen(argv[1], "r");
  if (!sf) { perror(argv[1]); return 1; }
  g_out = fopen(argv[2], "wb");
  if (!g_out) { perror(argv[2]); return 1; }

  setup();
  g_sim_us = 0;               // recording starts on the ready screen
  g_next_frame_us = 0;
  pump();

  char line[1024];
  uint32_t jitter = 12345;
  while (fgets(line, sizeof(line), sf)) {
    std::string l(line);
    while (l.size() && (l.back() == '\n' || l.back() == '\r')) l.pop_back();
    if (l.empty() || l[0] == '#') continue;
    std::string cmd = l.substr(0, l.find(' '));
    std::string arg = l.find(' ') == std::string::npos ? "" : l.substr(l.find(' ') + 1);
    Keyboard_Class::KeysState st;
    if (cmd == "wait") advance(atoi(arg.c_str()));
    else if (cmd == "type") {
      for (char c : arg) {
        st = {}; st.word.push_back(c); press(st);
        jitter = jitter * 1103515245u + 12345u;
        advance(70 + (jitter >> 16) % 90 + (c == ' ' ? 40 : 0));   // human-ish typing
      }
    }
    else if (cmd == "enter") { st = {}; st.enter = true; press(st); }
    else if (cmd == "tab")   { st = {}; st.tab = true; press(st); }
    else if (cmd == "key")   { st = {}; st.word.push_back(arg[0]); press(st); }
    else if (cmd == "snap")  snap(arg);
    else if (cmd == "snapgen") {     // snapgen NAME N: snap when the next reply hits N tokens
      g_gen_snap = arg.substr(0, arg.find(' '));
      g_gen_snap_at = atoi(arg.substr(arg.find(' ') + 1).c_str());
    }
    else if (cmd == "seed") {        // same sampler state as booting with --seed N
      g_rng = (uint32_t)atol(arg.c_str());
      llm_build_sampler(&sampler, transformer.config.vocab_size, settings.temp,
                        settings.top_p, esp_random());
    }
    else { fprintf(stderr, "bad script line: %s\n", l.c_str()); return 1; }
    pump();
  }
  fclose(g_out);
  if (transcript) {
    int oldest = ui.line_count_ > ChatUI::MAX_LINES ? ui.line_count_ - ChatUI::MAX_LINES : 0;
    for (int i = oldest; i < ui.line_count_; i++) {
      std::string t;
      for (char c : ui.lines_[i % ChatUI::MAX_LINES]) if ((uint8_t)c >= 8) t += c;
      printf("%s\n", t.c_str());
    }
  }
  fprintf(stderr, "%ld frames (%.1f s at %d fps)\n", g_frames, (double)g_frames / g_fps, g_fps);
  return 0;
}
