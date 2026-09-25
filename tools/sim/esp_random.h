#pragma once
#include <stdint.h>
uint32_t esp_random();   // deterministic, seeded by SIM_SEED (sim.cpp)
