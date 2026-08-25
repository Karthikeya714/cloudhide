interface BarDatum {
  label: string;
  value: number;
}

interface BarChartProps {
  data: BarDatum[];
  unit?: string;
  color?: string;
}

const BAR_HEIGHT = 22;
const BAR_GAP = 14;
const LABEL_WIDTH = 140;
const CHART_WIDTH = 420;

export default function BarChart({ data, unit = "", color = "#818cf8" }: BarChartProps) {
  const values = data.map((d) => d.value);
  const max = Math.max(...values, 1);
  const plotWidth = CHART_WIDTH - LABEL_WIDTH;
  const height = data.length * (BAR_HEIGHT + BAR_GAP);

  if (data.length === 0) {
    return <p className="text-sm text-slate-500">No data yet.</p>;
  }

  return (
    <svg
      viewBox={`0 0 ${CHART_WIDTH} ${height}`}
      width="100%"
      role="img"
      aria-label="Bar chart"
      className="overflow-visible"
    >
      {data.map((d, i) => {
        const barWidth = Math.max((d.value / max) * plotWidth, 2);
        const y = i * (BAR_HEIGHT + BAR_GAP);
        return (
          <g key={d.label}>
            <title>
              {d.label}: {d.value.toFixed(1)}
              {unit}
            </title>
            <text
              x={LABEL_WIDTH - 10}
              y={y + BAR_HEIGHT / 2}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-slate-400 text-[11px]"
            >
              {d.label}
            </text>
            <rect
              x={LABEL_WIDTH}
              y={y}
              width={barWidth}
              height={BAR_HEIGHT}
              rx={4}
              fill={color}
            />
            <text
              x={LABEL_WIDTH + barWidth + 8}
              y={y + BAR_HEIGHT / 2}
              dominantBaseline="middle"
              className="fill-slate-300 text-[11px]"
            >
              {d.value.toFixed(1)}
              {unit}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
