// Host shim: time is virtual, advanced by the simulator (sim.cpp), so on-screen
// timings match the device instead of the host CPU.
#pragma once
#include <stdint.h>
extern uint64_t g_sim_us;
static inline int64_t esp_timer_get_time() { return (int64_t)g_sim_us; }
