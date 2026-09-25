// Host shim for M5Unified: M5.Display is an off-screen 240x135 LGFX_Sprite,
// so the firmware's own ui.cpp draws with the real M5GFX fonts and primitives.
#pragma once
#include "lgfx/v1/gitTagVersion.h"
#include "lgfx/v1/platforms/device.hpp"
#include "lgfx/v1/platforms/common.hpp"
#include "lgfx/v1/lgfx_filesystem_support.hpp"
#include "lgfx/v1/LGFXBase.hpp"
#include "lgfx/v1/LGFX_Sprite.hpp"


struct SimDisplay : public lgfx::LGFX_Sprite {
  // The sprite is created already landscape (240x135); the device's
  // setRotation(1) on a 135x240 panel lands in the same place.
  void setRotation(int) {}
};

namespace m5 { enum board_t { board_M5Cardputer, board_M5CardputerADV }; }

struct SimM5 {
  SimDisplay Display;
  struct config_t {};
  config_t config() { return {}; }
  void begin(config_t) {
    Display.setColorDepth(16);
    Display.createSprite(240, 135);
  }
  void update() {}
  m5::board_t getBoard() { return m5::board_M5CardputerADV; }
};
extern SimM5 M5;
