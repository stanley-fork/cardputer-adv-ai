# Promo video (Remotion)

```sh
npm install
./prepare.sh path/to/music.mp3   # cuts 3x-speed clips + copies the soundtrack (not committed)
npm run studio                    # preview
npm run render                    # → out/cardputer-ai-promo.mp4
```

Scene timing is in song beats (`src/beats.ts`, 129.2 BPM); every cut lands on
a beat. Clips come from `tools/sim` (real firmware UI + model at device
speed), sped up 3x and labelled as such in the video.
