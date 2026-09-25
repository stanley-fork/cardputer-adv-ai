import React from "react";
import {
  AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { loadFont as loadOrbitron } from "@remotion/google-fonts/Orbitron";
import { loadFont as loadGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadVT } from "@remotion/google-fonts/VT323";
import { bf, pulse, FPS } from "./beats";

const { fontFamily: DISPLAY } = loadOrbitron("normal", { weights: ["500", "700", "900"] });
const { fontFamily: BODY } = loadGrotesk("normal", { weights: ["400", "500", "700"] });
const { fontFamily: MONO } = loadVT();

const PINK = "#ff2e88";
const CYAN = "#29e7ff";
const YELLOW = "#ffd319";
const PURPLE = "#8c1eff";

// Scene boundaries, in beats (4 beats = 1 bar).
const S = {
  intro: 0, chip: 12, stats: 20, impossible: 32, contrast: 40, demo: 52,
  talk: 52, feelings: 80, facts: 96, story: 120, outro: 140, end: 168,
};
export const TOTAL_FRAMES = bf(S.end);

// Dark outline drawn behind the fill (paint-order), so text reads over the sun and grid.
const outline = (px: number): React.CSSProperties =>
  ({ WebkitTextStroke: `${px}px #0a0014`, paintOrder: "stroke fill" });

const glow = (c: string, s = 1) =>
  `0 0 ${8 * s}px ${c}, 0 0 ${24 * s}px ${c}, 0 0 ${48 * s}px ${c}88`;

// Spring that starts at a beat.
const useIn = (beat: number, damping = 200) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - bf(beat), fps, config: { damping, mass: 0.7 }, durationInFrames: 14 });
};

// ---------- background ----------

const Stars: React.FC = () => {
  const frame = useCurrentFrame();
  const stars = React.useMemo(() => Array.from({ length: 90 }, (_, i) => {
    const r = (n: number) => { const x = Math.sin(i * 127.1 + n * 311.7) * 43758.5453; return x - Math.floor(x); };
    return { x: r(1) * 1920, y: r(2) * 520, s: 1 + r(3) * 2.2, p: r(4) * 6.28 };
  }), []);
  return <>{stars.map((s, i) => (
    <div key={i} style={{
      position: "absolute", left: s.x, top: s.y, width: s.s, height: s.s, borderRadius: "50%",
      background: "white", opacity: 0.35 + 0.35 * Math.sin(frame / 12 + s.p),
    }} />
  ))}</>;
};

const HORIZON = 628;
const GridFloor: React.FC<{ phase: number }> = ({ phase }) => {
  const h = 1080 - HORIZON;
  const rows: number[] = [];
  for (let k = 1; k < 40; k++) {
    const z = k - phase;                       // depth; z=1 is the bottom edge
    if (z < 0.6) continue;
    rows.push(HORIZON + h / z);
  }
  const cols = Array.from({ length: 41 }, (_, i) => i - 20);
  const lines = (w: number, op: number) => (
    <g stroke={PINK} strokeWidth={w} opacity={op} fill="none">
      {rows.map((y, i) => <line key={`r${i}`} x1={0} x2={1920} y1={y} y2={y} strokeWidth={w * Math.min(1.6, 0.4 + (y - HORIZON) / h * 1.6)} />)}
      {cols.map((c) => <line key={`c${c}`} x1={960 + c * 26} y1={HORIZON} x2={960 + c * 230} y2={1080} />)}
    </g>
  );
  return (
    <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
      <defs>
        <linearGradient id="floorfade" x1="0" y1={HORIZON} x2="0" y2={1080} gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0a0014" stopOpacity={1} />
          <stop offset="0.35" stopColor="#0a0014" stopOpacity={0.2} />
          <stop offset="1" stopColor="#0a0014" stopOpacity={0} />
        </linearGradient>
        <filter id="gridglow" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="5" /></filter>
      </defs>
      <g filter="url(#gridglow)">{lines(6, 0.7)}</g>
      {lines(2.2, 1)}
      <rect x={0} y={HORIZON} width={1920} height={h} fill="url(#floorfade)" />
    </svg>
  );
};

const Synthwave: React.FC<{ sunRise: number; dim: number }> = ({ sunRise, dim }) => {
  const frame = useCurrentFrame();
  const beatPos = ((frame / FPS - 0.07) / (60 / 129.199));   // grid moves one cell per beat
  return (
    <AbsoluteFill style={{ background: "linear-gradient(#07011a 0%, #1a0536 45%, #3d0b5c 58%, #0a0014 58.2%)" }}>
      <Stars />
      {/* sun */}
      <div style={{
        position: "absolute", left: 960 - 230, top: interpolate(sunRise, [0, 1], [700, 300]),
        width: 460, height: 460, borderRadius: "50%",
        background: `linear-gradient(${YELLOW} 10%, #ff8a3d 45%, ${PINK} 70%, ${PURPLE} 100%)`,
        WebkitMaskImage: "linear-gradient(black 52%, transparent 52%, transparent 56%, black 56%, black 63%, transparent 63%, transparent 67%, black 67%, black 73%, transparent 73%, transparent 78%, black 78%, black 83%, transparent 83%, transparent 89%, black 89%)",
        boxShadow: `0 0 120px ${PINK}66`,
        filter: "drop-shadow(0 0 40px #ff2e8888)",
      }} />
      {/* mountains on the horizon (in front of the sun's lower half) */}
      <svg width={1920} height={240} viewBox="0 0 1920 240" style={{ position: "absolute", left: 0, top: 628 - 240 }}>
        <polygon fill="#240845" stroke="#ff2e8888" strokeWidth={2}
          points="0,240 0,150 120,90 230,140 340,60 470,150 560,110 660,170 700,240 1220,240 1260,170 1350,100 1450,150 1560,50 1680,130 1780,80 1920,140 1920,240" />
        <polygon fill="#160331" stroke={`${CYAN}66`} strokeWidth={2}
          points="0,240 0,200 90,160 200,205 300,150 420,210 520,180 640,240 1280,240 1380,190 1480,215 1600,150 1720,200 1820,170 1920,195 1920,240" />
      </svg>
      {/* horizon clip so the sun sets behind the floor */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 628, bottom: 0, background: "#0a0014" }} />
      {/* perspective grid floor: rows scroll toward the viewer, one row per beat */}
      <GridFloor phase={beatPos - Math.floor(beatPos)} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 624, height: 6, background: PINK, boxShadow: glow(PINK, 1.5) }} />
      <AbsoluteFill style={{ background: "#05000d", opacity: dim }} />
    </AbsoluteFill>
  );
};

// ---------- shared bits ----------

const Title: React.FC<{ children: React.ReactNode; size?: number; color?: string; at: number; style?: React.CSSProperties }> =
  ({ children, size = 96, color = "white", at, style }) => {
    const p = useIn(at);
    return (
      <div style={{
        fontFamily: DISPLAY, fontWeight: 900, fontSize: size, color, letterSpacing: 2,
        // dark halo first (sits on top of the glow), then the neon glow; yellow
        // glows pink so it doesn't wash into the sun
        textShadow: `0 0 14px #0a0014, 0 0 4px #0a0014, ${glow(color === "white" || color === YELLOW ? PINK : color, 0.8)}`,
        textAlign: "center",
        opacity: p, transform: `translateY(${(1 - p) * 18}px)`, filter: `blur(${(1 - p) * 6}px)`,
        ...outline(Math.max(7, size * 0.13)), ...style,
      }}>{children}</div>
    );
  };

const Sub: React.FC<{ children: React.ReactNode; at: number; style?: React.CSSProperties }> = ({ children, at, style }) => {
  const p = useIn(at);
  return <div style={{
    fontFamily: BODY, fontWeight: 500, fontSize: 40, color: "#e8dcff", textAlign: "center", ...outline(6),
    opacity: p, transform: `translateY(${(1 - p) * 10}px)`, ...style,
  }}>{children}</div>;
};

const Chip: React.FC<{ size: number }> = ({ size }) => {
  const pins = Array.from({ length: 10 }, (_, i) => i);
  const u = size / 100;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ filter: `drop-shadow(0 0 ${6 * u}px ${CYAN})` }}>
      {pins.map((i) => {
        const o = 14 + i * 8;
        return <g key={i} fill="#c9cfe0">
          <rect x={o} y={2} width={4} height={10} rx={1} /><rect x={o} y={88} width={4} height={10} rx={1} />
          <rect x={2} y={o} width={10} height={4} rx={1} /><rect x={88} y={o} width={10} height={4} rx={1} />
        </g>;
      })}
      <rect x={11} y={11} width={78} height={78} rx={6} fill="#141225" stroke={CYAN} strokeWidth={1.4} />
      <rect x={19} y={19} width={62} height={62} rx={3} fill="none" stroke="#2c2950" strokeWidth={0.8} />
      <circle cx={24} cy={24} r={2.2} fill="#2c2950" />
      <text x={50} y={49} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={11} fill="white">ESP32-S3</text>
      <text x={50} y={62} textAnchor="middle" fontFamily={BODY} fontSize={6.5} fill={CYAN}>512 KB RAM</text>
    </svg>
  );
};

// ---------- scenes ----------

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const racks = [0, 1, 2, 3, 4, 5, 6];
  const rp = useIn(S.intro + 6, 18);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 70 }}>
      <Title at={2} size={84}>Every chatbot you know</Title>
      <Title at={6} size={84} color={CYAN} style={{ marginTop: 10 }}>lives in a data center.</Title>
      <div style={{ display: "flex", gap: 26, marginTop: 190, opacity: rp, transform: `translateY(${(1 - rp) * 30}px)` }}>
        {racks.map((r) => (
          <div key={r} style={{ width: 90, height: 170, background: "#16112b", border: "2px solid #3a2d66", borderRadius: 6, padding: 8, display: "flex", flexDirection: "column", gap: 7 }}>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((l) => {
              const on = Math.sin(frame * 0.9 + r * 7 + l * 3) > 0.1;
              return <div key={l} style={{ height: 12, background: "#221a40", borderRadius: 2, display: "flex", alignItems: "center", paddingLeft: 6, gap: 5 }}>
                <div style={{ width: 5, height: 5, borderRadius: 3, background: on ? "#39ff88" : "#1b4d32" }} />
                <div style={{ width: 5, height: 5, borderRadius: 3, background: on && l % 2 ? YELLOW : "#4d4419" }} />
              </div>;
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const ChipScene: React.FC = () => {
  const frame = useCurrentFrame();
  const p = useIn(S.chip);
  const beat = pulse(frame, 4);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 60 }}>
      <Title at={S.chip + 2} size={92}>This one lives on a <span style={{ color: YELLOW, textShadow: glow(YELLOW, 0.8) }}>chip.</span></Title>
      <div style={{ marginTop: 40, opacity: p, transform: `scale(${0.85 + 0.15 * p})`, filter: `drop-shadow(0 0 ${20 + 40 * beat}px ${CYAN}88)` }}>
        <Chip size={400} />
      </div>
      <Sub at={S.chip + 5} style={{ marginTop: 30 }}>a few-dollar microcontroller · no internet · no cloud</Sub>
    </AbsoluteFill>
  );
};

const Stat: React.FC<{ at: number; big: string; small: string; color: string }> = ({ at, big, small, color }) => {
  const frame = useCurrentFrame();
  const p = useIn(at);
  const beat = frame >= bf(at) ? pulse(frame, 4) : 0;
  return (
    <div style={{
      width: 520, height: 400, borderRadius: 28, border: `4px solid ${color}`,
      background: "#0d0620cc", boxShadow: `${glow(color, 0.5 + 0.5 * beat)}, inset 0 0 60px ${color}33`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      opacity: p, transform: `scale(${0.9 + 0.1 * p})`,
    }}>
      <div style={{ fontFamily: DISPLAY, fontWeight: 900, fontSize: 116, color: "white", textShadow: glow(color, 0.9), lineHeight: 1, ...outline(10) }}>{big}</div>
      <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 44, color, marginTop: 24, textTransform: "uppercase", letterSpacing: 4, ...outline(6) }}>{small}</div>
    </div>
  );
};

const Stats: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 60 }}>
    <div style={{ display: "flex", gap: 60 }}>
      <Stat at={S.stats} big="8M" small="parameters" color={PINK} />
      <Stat at={S.stats + 4} big="512KB" small="of RAM" color={CYAN} />
      <Stat at={S.stats + 8} big="0" small="internet" color={YELLOW} />
    </div>
  </AbsoluteFill>
);

const Impossible: React.FC = () => {
  const frame = useCurrentFrame();
  const stampAt = bf(S.impossible + 2);
  const st = spring({ frame: frame - stampAt, fps: FPS, config: { damping: 200 }, durationInFrames: 6 });
  const strike = interpolate(frame, [bf(S.impossible + 5), bf(S.impossible + 6)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const RED = "#ff3b3b";
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 80 }}>
      <Title at={S.impossible} size={76}>A real chatbot in 512 KB of RAM?</Title>
      {frame >= stampAt && (
        <div style={{ position: "relative", marginTop: 60, opacity: st, transform: `scale(${1.25 - 0.25 * st}) rotate(-4deg)` }}>
          <div style={{
            fontFamily: DISPLAY, fontWeight: 900, fontSize: 190, color: RED, letterSpacing: 6, ...outline(12),
            border: `10px solid ${RED}`, borderRadius: 24, padding: "0 50px",
            textShadow: glow(RED, 1), boxShadow: `${glow(RED, 0.7)}, inset ${glow(RED, 0.4)}`,
            background: "#12020acc",
          }}>IMPOSSIBLE.</div>
          <div style={{
            position: "absolute", left: -30, top: "50%", height: 18, width: `calc(${strike * 100}% + 60px)`,
            background: CYAN, boxShadow: glow(CYAN, 1), borderRadius: 9, transform: "translateY(-50%)",
            opacity: strike > 0 ? 1 : 0,
          }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

const Typed: React.FC<{ text: string; from: number; to: number; style?: React.CSSProperties }> = ({ text, from, to, style }) => {
  const frame = useCurrentFrame();
  const n = Math.floor(interpolate(frame, [bf(from), bf(to)], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return <span style={style}>{text.slice(0, n)}</span>;
};

const Contrast: React.FC = () => {
  const frame = useCurrentFrame();
  const punch = bf(S.contrast + 8);
  const after = frame >= punch;
  const pp = spring({ frame: frame - punch, fps: FPS, config: { damping: 200 }, durationInFrames: 8 });
  const split = after ? 12 * Math.exp(-(frame - punch) / 3) : 0;
  const tp = useIn(S.contrast + 1);
  if (after) {
    return (
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", transform: `scale(${1.15 - 0.15 * pp})` }}>
          {[[PINK, -split], [CYAN, split], ["white", 0]].map(([c, dx], i) => (
            <div key={i} style={{
              position: i < 2 ? "absolute" : "relative", left: 0, top: 0, width: "100%",
              fontFamily: DISPLAY, fontWeight: 900, fontSize: 170, color: c as string, textAlign: "center",
              transform: `translateX(${dx}px)`, mixBlendMode: i < 2 ? "screen" : "normal",
              textShadow: i === 2 ? glow(PINK, 1.2) : "none", opacity: i < 2 ? 0.8 : 1, whiteSpace: "nowrap",
              ...(i === 2 ? outline(14) : {}),
            }}>THIS ONE CHATS.</div>
          ))}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 70 }}>
      <Title at={S.contrast} size={72}>Tiny AI on chips isn't new.</Title>
      <Sub at={S.contrast + 1} style={{ marginTop: 16 }}>But until now it could only continue stories:</Sub>
      <div style={{
        marginTop: 50, width: 1300, minHeight: 330, padding: "30px 40px", borderRadius: 18,
        background: "#0b0718", border: "2px solid #3a2d66", fontFamily: MONO, fontSize: 54, lineHeight: 1.25,
        opacity: tp, color: "#b8b0d0",
      }}>
        <div><span style={{ color: "#39ff88" }}>&gt; </span><Typed text="Hi! How are you?" from={S.contrast + 1.5} to={S.contrast + 3} style={{ color: "white" }} /></div>
        <Typed text="Once upon a time, there was a little dog named Max. Max liked to run in the park. One day, Max saw a big" from={S.contrast + 3.5} to={S.contrast + 7.8} />
        <span style={{ opacity: frame % 16 < 8 ? 1 : 0, color: "#39ff88" }}>█</span>
      </div>
      <div style={{ fontFamily: BODY, fontSize: 24, color: "#8a80a8", marginTop: 14, ...outline(4) }}>illustration of a story-completion model</div>
    </AbsoluteFill>
  );
};

const CLIPS = [
  { key: "talk", from: S.talk, to: S.feelings, n: "01", label: "Small talk" },
  { key: "feelings", from: S.feelings, to: S.facts, n: "02", label: "Feelings" },
  { key: "facts", from: S.facts, to: S.story, n: "03", label: "Simple facts & knowing its limits" },
  { key: "story", from: S.story, to: S.outro, n: "04", label: "Bedtime stories" },
];

const Demo: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = useIn(S.demo);
  const beat = pulse(frame, 4);
  const clip = CLIPS.find((c) => frame >= bf(c.from) && frame < bf(c.to)) ?? CLIPS[0];
  const lp = spring({ frame: frame - bf(clip.from), fps: FPS, config: { damping: 200 }, durationInFrames: 12 });
  const W = 1440 * 0.86, H = 810 * 0.86;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", perspective: 2200 }}>
      <div style={{ position: "absolute", top: 36, left: 120, display: "flex", alignItems: "center", gap: 22, opacity: lp, transform: `translateX(${(1 - lp) * -24}px)` }}>
        <div style={{ fontFamily: DISPLAY, fontWeight: 900, fontSize: 40, color: "#0a0014", background: CYAN, borderRadius: 10, padding: "4px 16px", boxShadow: glow(CYAN, 0.6) }}>{clip.n}</div>
        <div style={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 46, color: "white", textShadow: glow(PINK, 0.6), ...outline(7) }}>{clip.label}</div>
      </div>
      <div style={{
        marginTop: 70, padding: 22, borderRadius: 28, background: "#16131f",
        border: `3px solid ${PINK}`, boxShadow: `0 0 ${30 + 30 * beat}px ${PINK}aa, 0 0 120px ${PURPLE}66`,
        transform: `scale(${0.94 + 0.06 * enter})`, opacity: enter,
      }}>
        <div style={{ width: W, height: H, background: "black", position: "relative", overflow: "hidden", borderRadius: 6 }}>
          {CLIPS.map((c) => (
            <Sequence key={c.key} from={bf(c.from)} durationInFrames={bf(c.to) - bf(c.from)} layout="none">
              <OffthreadVideo src={staticFile(`clips/${c.key}.mp4`)} muted style={{ width: W, height: H, imageRendering: "pixelated" }} />
            </Sequence>
          ))}
          <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(transparent 0 3px, #00000022 3px 4px)" }} />
        </div>
      </div>
      <div style={{ position: "absolute", bottom: 26, right: 110, fontFamily: BODY, fontWeight: 700, fontSize: 24, color: "#0a0014", background: YELLOW, borderRadius: 8, padding: "6px 14px", opacity: enter }}>
        ▶ 3× SPEED
      </div>
      <div style={{ position: "absolute", bottom: 30, left: 120, fontFamily: BODY, fontSize: 24, color: "#cfc3ef", opacity: enter, ...outline(4) }}>
        Real model output · real firmware UI, captured in a simulator
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const logoAt = S.outro + 8;
  const beat = pulse(frame, 4);
  const lp = useIn(logoAt);
  if (frame < bf(logoAt)) {
    return (
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 90, gap: 10 }}>
        <Title at={S.outro} size={110}>8 million parameters.</Title>
        <Title at={S.outro + 2} size={110} color={CYAN}>512 KB.</Title>
        <Title at={S.outro + 4} size={110} color={YELLOW}>No cloud.</Title>
      </AbsoluteFill>
    );
  }
  const fade = interpolate(frame, [bf(S.end - 3), bf(S.end)], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 150, opacity: fade }}>
      <div style={{ display: "flex", alignItems: "center", gap: 50, opacity: lp, transform: `scale(${0.94 + 0.06 * lp})` }}>
        <div style={{ filter: `drop-shadow(0 0 ${10 + 30 * beat}px ${CYAN})` }}><Chip size={190} /></div>
        <div style={{ fontFamily: DISPLAY, fontWeight: 900, fontSize: 120, color: "white", textShadow: glow(PINK, 0.9 + 0.6 * beat), whiteSpace: "nowrap", ...outline(12) }}>
          CARDPUTER <span style={{ color: CYAN, textShadow: glow(CYAN, 0.8 + 0.6 * beat) }}>AI</span>
        </div>
      </div>
      <Title at={logoAt + 2} size={64} color={YELLOW} style={{ marginTop: 40 }}>The impossible chatbot.</Title>
      <Sub at={logoAt + 5} style={{ marginTop: 22, fontSize: 40, color: "white" }}>A real chatbot, running on a microchip.</Sub>
    </AbsoluteFill>
  );
};

// ---------- composition ----------

export const Promo: React.FC = () => {
  const frame = useCurrentFrame();
  const sunRise = interpolate(frame, [0, bf(10), bf(S.outro + 6), bf(S.outro + 14)], [0, 1, 1, 0.25],
    { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const dim = interpolate(frame, [bf(S.demo - 1), bf(S.demo), bf(S.outro), bf(S.outro + 1)], [0, 0.12, 0.12, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const flash = Math.max(
    ...[S.chip, S.stats, S.impossible + 2, S.contrast, S.contrast + 8, S.demo, S.outro, S.outro + 8].map((b) =>
      interpolate(frame, [bf(b), bf(b) + 8], [0.55, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * (frame >= bf(b) ? 1 : 0)),
  );
  return (
    <AbsoluteFill style={{ background: "black" }}>
      <Audio src={staticFile("music.mp3")} volume={(f) =>
        interpolate(f, [0, 10, TOTAL_FRAMES - 75, TOTAL_FRAMES], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      <Synthwave sunRise={sunRise} dim={dim} />
      {/* scenes read the absolute frame (their timings are in song beats) */}
      {frame < bf(S.chip) && <Intro />}
      {frame >= bf(S.chip) && frame < bf(S.stats) && <ChipScene />}
      {frame >= bf(S.stats) && frame < bf(S.impossible) && <Stats />}
      {frame >= bf(S.impossible) && frame < bf(S.contrast) && <Impossible />}
      {frame >= bf(S.contrast) && frame < bf(S.demo) && <Contrast />}
      {frame >= bf(S.demo) && frame < bf(S.outro) && <Demo />}
      {frame >= bf(S.outro) && <Outro />}
      <AbsoluteFill style={{ background: "white", opacity: flash, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
