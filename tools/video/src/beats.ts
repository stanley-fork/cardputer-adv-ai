// Beat grid of the soundtrack (129.2 BPM, first beat at 0.07 s, measured with
// librosa). Every scene boundary sits on a beat, so cuts land on the music.
export const FPS = 30;
export const BPM = 129.199;
export const BEAT_S = 60 / BPM;
export const OFFSET_S = 0.07;

export const bf = (beat: number) => Math.round((OFFSET_S + beat * BEAT_S) * FPS);

// 1 on every beat, decaying before the next one.
export const pulse = (frame: number, decay = 6) => {
  const t = (frame / FPS - OFFSET_S) / BEAT_S;
  if (t < 0) return 0;
  return Math.exp(-(t - Math.floor(t)) * decay);
};
