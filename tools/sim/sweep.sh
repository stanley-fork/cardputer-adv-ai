#!/bin/sh
# Try one demo scene over many seeds and print each transcript, to pick the
# seed for tools/sim/demo.txt. The scene is a script without seed/snap lines.
#   tools/sim/sweep.sh scene.txt [N=20]
set -e
cd "$(dirname "$0")/../.."
[ -x tools/sim/build/sim ] || tools/sim/build.sh
for seed in $(seq 1 "${2:-20}"); do
  echo "== seed $seed"
  tools/sim/build/sim "$1" /dev/null --seed "$seed" --transcript 2>/dev/null | grep -v '^\[bench\]'
done
