#pragma once
#include <freertos/FreeRTOS.h>
#include <stdint.h>
#define taskYIELD() ((void)0)
#define pdMS_TO_TICKS(ms) (ms)
extern uint64_t g_sim_us;
static inline void vTaskDelay(uint32_t ticks) { g_sim_us += (uint64_t)ticks * 1000; }
