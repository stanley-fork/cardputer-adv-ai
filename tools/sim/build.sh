#!/bin/sh
# Build the host screen simulator into tools/sim/build/sim.
# Needs clang++ and SDL2 headers (brew install sdl2) — M5GFX's host platform
# layer includes them, though nothing here opens a window.
set -e
cd "$(dirname "$0")/../.."
GFX=managed_components/m5stack__m5gfx/src
OUT=tools/sim/build
[ -d "$GFX" ] || { echo "run a firmware build first (fetches managed_components/)"; exit 1; }
mkdir -p "$OUT/obj"
cp main/main.cpp "$OUT/main_fw.cpp"
SDL_CFLAGS=$(sdl2-config --cflags)
SDL_LIBS=$(sdl2-config --libs)
INC="-I tools/sim -I tools/host -I main -I $OUT -I $GFX $SDL_CFLAGS"
CXX="clang++ -std=c++17 -O2 -w $INC"
CC="clang -O2 -w $INC"
objs=""
for f in $GFX/lgfx/v1/*.cpp $GFX/lgfx/v1/misc/*.cpp $GFX/lgfx/v1/platforms/sdl/common.cpp \
         $GFX/lgfx/v1/panel/Panel_Device.cpp; do
  o="$OUT/obj/$(basename "$f" .cpp).o"
  [ "$o" -nt "$f" ] || $CXX -c "$f" -o "$o"
  objs="$objs $o"
done
for f in $GFX/lgfx/utility/*.c $GFX/lgfx/Fonts/efont/*.c $GFX/lgfx/Fonts/IPA/*.c; do
  o="$OUT/obj/$(basename "$f" .c).o"
  [ "$o" -nt "$f" ] || $CC -c "$f" -o "$o"
  objs="$objs $o"
done
for f in main/model_data.cpp main/tok_data.cpp; do   # the exact embedded model
  o="$OUT/obj/$(basename "$f" .cpp).o"
  [ "$o" -nt "$f" ] || clang++ -std=c++17 -O0 -c "$f" -o "$o"
  objs="$objs $o"
done
$CXX tools/sim/sim.cpp main/ui.cpp main/llm.cpp $objs $SDL_LIBS -o "$OUT/sim"
echo "built $OUT/sim"
