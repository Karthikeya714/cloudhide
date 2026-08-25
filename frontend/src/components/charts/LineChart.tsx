interface LinePoint {
  label: string;
  value: number;
}

interface LineChartProps {
  data: LinePoint[];
  unit?: string;
  color?: string;
}

const WIDTH = 560;
const HEIGHT = 180;
const PADDING = 28;

export default function LineChart({ data, unit = "", color = "#818cf8" }: LineChartProps) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-500">No data yet.</p>;
  }

  const values = data.map((d) => d.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const plotWidth = WIDTH - PADDING * 2;
  const plotHeight = HEIGHT - PADDING * 2;

  const points = data.map((d, i) => {
    const x = PADDING + (data.length === 1 ? plotWidth / 2 : (i / (data.length - 1)) * plotWidth);
    const y = PADDING + plotHeight - ((d.value - min) / range) * plotHeight;
    return { ...d, x, y };
  });

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const baselineY = PADDING + plotHeight;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width="100%"
      role="img"
      aria-label="Line chart"
      className="overflow-visible"
    >
      <line
        x1={PADDING}
        y1={baselineY}
        x2={WIDTH - PADDING}
        y2={baselineY}
        stroke="#334155"
        strokeWidth={1}
      />
      <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" />
      {points.map((p) => (
        <g key={p.label}>
          <title>
            {p.label}: {p.value.toFixed(1)}
            {unit}
          </title>
          <circle cx={p.x} cy={p.y} r={4} fill={color} />
        </g>
      ))}
    </svg>
  );
}
