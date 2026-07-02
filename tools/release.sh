#!/usr/bin/env bash
# Publish a GitHub release with the PlatformIO firmware images.
#
# Usage: tools/release.sh <version> [--notes "release notes"]
#   e.g. tools/release.sh 1.1 --notes "Backtick interrupt; unlimited/unsafe reply length."
#
# Builds (if needed) and uploads two assets:
#   cardputer_ai_<version>.bin       app-only image  (.pio firmware.bin)       — for bmorcelli/Launcher (offset 0x10000)
#   cardputer_ai_<version>_full.bin  full-flash image (.pio firmware.factory)  — bootloader + parts + app for esptool (offset 0x0)
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "usage: tools/release.sh <version> [--notes \"...\"]" >&2
  exit 1
fi
shift

NOTES=""
TITLE="$VERSION"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --notes) NOTES="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

BUILD_DIR=".pio/build/cardputer"
APP_BIN="$BUILD_DIR/firmware.bin"
FULL_BIN="$BUILD_DIR/firmware.factory.bin"

# Build if either image is missing.
if [[ ! -f "$APP_BIN" || ! -f "$FULL_BIN" ]]; then
  echo "==> building firmware (pio run)"
  pio run
fi

OUT_APP="/tmp/cardputer_ai_${VERSION}.bin"
OUT_FULL="/tmp/cardputer_ai_${VERSION}_full.bin"
cp "$APP_BIN" "$OUT_APP"
cp "$FULL_BIN" "$OUT_FULL"

echo "==> creating release $VERSION"
gh release create "$VERSION" "$OUT_APP" "$OUT_FULL" \
  --title "$TITLE" \
  --notes "$NOTES"
