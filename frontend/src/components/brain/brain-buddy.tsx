/** The Brain's character (docs/design/brain-character, direction B): one drawing, moods as settings. Drawn in the
 * theme's own colours (--brain-* tokens in globals.css, made from --primary/--card/--ring), so it follows every theme
 * and dark mode. Moves gently (float, blink, thinking dots) unless the person has asked for less motion.
 *
 *   <BrainBuddy mood="thinking" size={56} />          full character (arms and feet)
 *   <BrainBuddy mood="happy" size={20} head />        just the head, for buttons and icons
 */
export type BrainMood = "happy" | "thinking" | "pointing" | "celebrating" | "puzzled" | "sleepy" | "waving";

const BODY = "M48,112 C30,104 32,74 52,70 C52,50 74,40 92,48 C100,38 120,38 128,48 C146,40 168,52 166,72 C184,78 184,106 166,114 C168,134 148,148 130,140 C122,152 98,154 88,142 C68,150 46,136 48,112 Z";
const FOLDS = ["M100,48 C97,57 103,64 99,72", "M70,62 C77,57 86,62 82,70", "M130,58 C138,54 148,60 144,68"];
const EX = 82, EX2 = 118, EY = 98, MY = EY + 24;

const LINE = "var(--brain-line)", BODYC = "var(--brain-body)", SPARK = "var(--brain-spark)";

function Arms({ mood }: { mood: BrainMood }) {
  const arm = (d: string, end: [number, number], cls?: string) => (
    <g className={cls}>
      <path d={d} fill="none" stroke={LINE} strokeWidth={6} strokeLinecap="round" />
      <circle cx={end[0]} cy={end[1]} r={6} fill={BODYC} stroke={LINE} strokeWidth={3} />
    </g>
  );
  const left = arm("M50,122 Q36,132 34,142", [34, 143]);
  if (mood === "celebrating") return <>{arm("M50,104 Q36,84 32,66", [32, 64])}{arm("M150,104 Q164,84 168,66", [168, 64])}</>;
  if (mood === "pointing") return <>{left}{arm("M156,108 Q174,96 188,90", [189, 89])}</>;
  if (mood === "thinking") return <>{left}{arm("M150,124 Q140,140 120,134", [118, 133])}</>;
  if (mood === "waving") return <>{left}{arm("M152,106 Q168,92 172,74", [172, 72], "brain-wave")}</>;
  return <>{left}{arm("M150,122 Q164,132 166,142", [166, 143])}</>;
}

function Eyes({ mood }: { mood: BrainMood }) {
  const look = ({ thinking: [-3, -4], pointing: [4, 0], puzzled: [2, -1] } as Record<string, [number, number]>)[mood] ?? [0, 0];
  if (mood === "celebrating")
    return <>{[EX, EX2].map((x) => <path key={x} d={`M${x - 8},${EY + 2} Q${x},${EY - 8} ${x + 8},${EY + 2}`} fill="none" stroke={LINE} strokeWidth={4} strokeLinecap="round" />)}</>;
  if (mood === "sleepy")
    return <>{[EX, EX2].map((x) => <path key={x} d={`M${x - 8},${EY} Q${x},${EY + 6} ${x + 8},${EY}`} fill="none" stroke={LINE} strokeWidth={3.5} strokeLinecap="round" />)}</>;
  return (
    <g className="brain-blink">
      {[EX, EX2].map((x) => (
        <g key={x}>
          <circle cx={x + look[0]} cy={EY + look[1]} r={6.5} fill={LINE} />
          <circle cx={x + look[0] + 2} cy={EY + look[1] - 2} r={2} fill="var(--card)" />
        </g>
      ))}
    </g>
  );
}

function Mouth({ mood }: { mood: BrainMood }) {
  const p = { fill: "none", stroke: LINE, strokeWidth: 3.5, strokeLinecap: "round" as const };
  switch (mood) {
    case "thinking": return <path d={`M94,${MY + 3} Q101,${MY} 107,${MY + 4}`} {...p} />;
    case "puzzled": return <path d={`M90,${MY + 3} q5,-5 10,0 t10,0`} {...p} />;
    case "sleepy": return <ellipse cx={100} cy={MY + 3} rx={4} ry={3} fill={LINE} />;
    case "celebrating": return <path d={`M87,${MY - 2} Q100,${MY - 2} 113,${MY - 2} Q111,${MY + 14} 100,${MY + 14} Q89,${MY + 14} 87,${MY - 2} Z`} fill={LINE} />;
    default: return <path d={`M89,${MY} Q100,${MY + 11} 111,${MY}`} {...p} />;
  }
}

function Extras({ mood }: { mood: BrainMood }) {
  if (mood === "thinking")
    return <g className="brain-dots"><circle cx={158} cy={42} r={4} fill={SPARK} /><circle cx={170} cy={29} r={5.5} fill={SPARK} /><circle cx={185} cy={15} r={7} fill={SPARK} /></g>;
  if (mood === "puzzled") return <text x={160} y={52} fontSize={34} fontWeight={800} fill={SPARK} fontFamily="inherit">?</text>;
  if (mood === "sleepy")
    return <g className="brain-zz" fill={SPARK} fontWeight={800} fontFamily="inherit"><text x={150} y={48} fontSize={18}>z</text><text x={164} y={32} fontSize={24}>z</text></g>;
  if (mood === "celebrating")
    return (
      <g className="brain-confetti">
        {([[22, 40, "var(--chart-5)", 4], [178, 34, SPARK, 4], [40, 18, SPARK, 3], [160, 14, "var(--warn)", 3], [100, 14, "var(--chart-2)", 4], [190, 60, "var(--warn)", 3], [12, 66, SPARK, 3]] as const)
          .map(([x, y, c, r], i) => <circle key={i} cx={x} cy={y} r={r} fill={c} />)}
      </g>
    );
  return null;
}

export function BrainBuddy({ mood = "happy", size = 56, head = false, still = false, className = "", title }: {
  mood?: BrainMood; size?: number; head?: boolean; still?: boolean; className?: string; title?: string;
}) {
  // the head alone is cropped tight so it reads at 16-24px
  const viewBox = head ? "30 36 156 120" : "0 0 200 175";
  return (
    <svg viewBox={viewBox} width={size} height={head ? size * (120 / 156) : size * (175 / 200)} role={title ? "img" : undefined}
      aria-label={title} aria-hidden={title ? undefined : true} data-mood={mood}
      className={`brain-buddy ${still ? "" : "brain-move"} ${className}`} style={{ overflow: "visible" }}>
      <g className="brain-float">
        {!head && <Arms mood={mood} />}
        {!head && <><ellipse cx={86} cy={157} rx={11} ry={6} fill={LINE} /><ellipse cx={114} cy={157} rx={11} ry={6} fill={LINE} /></>}
        <path d={BODY} fill={BODYC} stroke={LINE} strokeWidth={head ? 6 : 4.5} strokeLinejoin="round" />
        {FOLDS.map((d) => <path key={d} d={d} fill="none" stroke={LINE} strokeWidth={head ? 5.5 : 4} strokeLinecap="round" />)}
        {!head && <><ellipse cx={68} cy={EY + 18} rx={8} ry={5} fill="var(--brain-cheek)" /><ellipse cx={132} cy={EY + 18} rx={8} ry={5} fill="var(--brain-cheek)" /></>}
        <Eyes mood={mood} />
        {mood === "thinking" && <path d={`M${EX2 - 9},${EY - 18} Q${EX2},${EY - 24} ${EX2 + 9},${EY - 19}`} fill="none" stroke={LINE} strokeWidth={3} strokeLinecap="round" />}
        {mood === "puzzled" && <>
          <path d={`M${EX - 9},${EY - 17} L${EX + 8},${EY - 20}`} stroke={LINE} strokeWidth={3} strokeLinecap="round" />
          <path d={`M${EX2 - 8},${EY - 23} Q${EX2},${EY - 27} ${EX2 + 9},${EY - 21}`} fill="none" stroke={LINE} strokeWidth={3} strokeLinecap="round" />
        </>}
        <Mouth mood={mood} />
      </g>
      {!head && <Extras mood={mood} />}
    </svg>
  );
}
