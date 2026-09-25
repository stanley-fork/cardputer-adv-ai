#!/bin/sh
# Regenerate the README / press media in docs/media from tools/sim/demo.txt.
# Needs: clang++, SDL2 headers, ffmpeg, uv. Everything on screen is produced by
# the firmware's own ui.cpp + main.cpp + llm.cpp and the embedded model, with
# every forward pass charged the measured on-device latency (196 ms, 8M model).
set -e
cd "$(dirname "$0")/../.."
OUT=docs/media
TMP=tools/sim/build/rec
mkdir -p "$OUT" "$TMP"
tools/sim/build.sh
tools/sim/build/sim tools/sim/demo.txt "$TMP/demo.rgb" --snap-dir "$TMP" --transcript | grep -v "^\[bench\]" > "$OUT/demo-transcript.txt"
RAW="-f rawvideo -pix_fmt rgb24 -s 240x135 -r 20 -i $TMP/demo.rgb"
FF="ffmpeg -loglevel error -y"

# Screen stills at 8x = exactly 1920x1080.
for f in "$TMP"/*.ppm; do
  $FF -i "$f" -vf scale=1920:1080:flags=neighbor "$OUT/screen-$(basename "$f" .ppm).png"
done

# Device frame + social banner (flat illustration around the real screen).
set -- $(uv run -q tools/sim/frame.py "$TMP" "$TMP/01-chat-live.ppm")
SX=$1 SY=$2
cp "$TMP/banner.png" "$OUT/banner.png"
$FF -i "$TMP/frame.png" -i "$TMP/05-story-live.ppm" \
    -filter_complex "[1]scale=720:405:flags=neighbor[s];[0][s]overlay=$SX:$SY" "$OUT/device-story.png"
$FF -i "$TMP/frame.png" -i "$TMP/01-chat-live.ppm" \
    -filter_complex "[1]scale=720:405:flags=neighbor[s];[0][s]overlay=$SX:$SY" "$OUT/device-chat.png"

# Full demo, real time: 1080p screen-only MP4 and a framed GIF for the README.
$FF $RAW -vf scale=1920:1080:flags=neighbor -c:v libx264 -preset slow -crf 18 \
    -tune animation -pix_fmt yuv420p -movflags +faststart "$OUT/demo.mp4"
$FF -loop 1 -i "$TMP/frame.png" $RAW -filter_complex \
    "[1]fps=10,scale=720:405:flags=neighbor[s];[0][s]overlay=$SX:$SY:shortest=1,split[a][b];[a]palettegen=max_colors=48:stats_mode=full[p];[b][p]paletteuse=dither=none" \
    "$OUT/demo.gif"
ls -la "$OUT"
