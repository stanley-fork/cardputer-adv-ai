// Host shim for the Cardputer keyboard: sim.cpp queues one scripted key event
// at a time and main.cpp's loop() reads it back through the same API.
#pragma once
#include <vector>

struct Keyboard_Class {
  struct KeysState {
    std::vector<char> word;
    bool tab = false, fn = false, enter = false, del = false;
  };
  static KeysState pending;
  static bool      has_pending;
  void begin() {}
  void updateKeyList() {}
  void updateKeysState() {}
  bool isChange()  { return has_pending; }
  bool isPressed() { return has_pending; }
  KeysState keysState() { KeysState s = pending; has_pending = false; pending = {}; return s; }
};
