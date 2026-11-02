/* tgbuild: clock id macros mirror _time.h (whose enum lacks CLOCK_UPTIME_RAW in the
   sdk-free tree). Macro-to-enum-constant form so the Swift importer aliases them. */
#ifndef TGBUILD_CLOCK_SHIM_H
#define TGBUILD_CLOCK_SHIM_H
#define CLOCK_UPTIME_RAW _CLOCK_UPTIME_RAW
#define CLOCK_MONOTONIC _CLOCK_MONOTONIC
#define CLOCK_REALTIME _CLOCK_REALTIME
#endif
