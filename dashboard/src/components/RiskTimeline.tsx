import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import type { RiskDataPoint } from "../types";

interface RiskTimelineProps {
  data: RiskDataPoint[];
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: RiskDataPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="bg-sardis-surface border border-sardis-border rounded-lg p-3 shadow-xl">
      <p className="text-xs font-mono text-sardis-text-dim mb-1">
        {point.timeLabel}
      </p>
      <p
        className={`text-sm font-bold font-mono ${
          point.score < 0.45
            ? "text-sardis-green"
            : point.score < 0.70
              ? "text-sardis-yellow"
              : point.score < 0.85
                ? "text-sardis-orange"
                : "text-sardis-red"
        }`}
      >
        Score: {point.score.toFixed(4)}
      </p>
      <p className="text-xs text-sardis-cyan font-mono mt-0.5">
        {point.agent}
      </p>
      <p className="text-xs text-sardis-text-dim mt-0.5">
        Action: {point.action}
      </p>
    </div>
  );
}

export function RiskTimeline({ data }: RiskTimelineProps) {
  return (
    <div className="bg-sardis-surface border border-sardis-border rounded-xl flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-sardis-border">
        <h2 className="text-sm font-semibold text-white">
          Risk Score Timeline
        </h2>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-sardis-green" />
            &lt;0.45
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-sardis-yellow" />
            &lt;0.70
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-sardis-orange" />
            &lt;0.85
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-sardis-red" />
            &ge;0.85
          </span>
        </div>
      </div>

      <div className="flex-1 p-4 min-h-0">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sardis-text-dim text-sm">
            Waiting for risk data...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              {/* Color zone backgrounds */}
              <ReferenceArea
                y1={0}
                y2={0.45}
                fill="#22c55e"
                fillOpacity={0.04}
              />
              <ReferenceArea
                y1={0.45}
                y2={0.70}
                fill="#eab308"
                fillOpacity={0.04}
              />
              <ReferenceArea
                y1={0.70}
                y2={0.85}
                fill="#f97316"
                fillOpacity={0.06}
              />
              <ReferenceArea
                y1={0.85}
                y2={1.0}
                fill="#ef4444"
                fillOpacity={0.08}
              />

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#2a2a3a"
                vertical={false}
              />
              <XAxis
                dataKey="timeLabel"
                tick={{ fill: "#8888a0", fontSize: 10 }}
                axisLine={{ stroke: "#2a2a3a" }}
                tickLine={{ stroke: "#2a2a3a" }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 1]}
                ticks={[0, 0.25, 0.45, 0.70, 0.85, 1.0]}
                tick={{ fill: "#8888a0", fontSize: 10 }}
                axisLine={{ stroke: "#2a2a3a" }}
                tickLine={{ stroke: "#2a2a3a" }}
                width={35}
              />
              <Tooltip content={<CustomTooltip />} />

              {/* Threshold lines */}
              <ReferenceLine
                y={0.45}
                stroke="#eab308"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
              <ReferenceLine
                y={0.70}
                stroke="#f97316"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
              <ReferenceLine
                y={0.85}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />

              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={(props: Record<string, unknown>) => {
                  const cx = props.cx as number;
                  const cy = props.cy as number;
                  const payload = props.payload as RiskDataPoint;
                  const index = props.index as number;
                  const color =
                    payload.score < 0.45
                      ? "#22c55e"
                      : payload.score < 0.70
                        ? "#eab308"
                        : payload.score < 0.85
                          ? "#f97316"
                          : "#ef4444";
                  return (
                    <circle
                      key={index}
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill={color}
                      stroke={color}
                      strokeWidth={1}
                      opacity={0.9}
                    />
                  );
                }}
                activeDot={{
                  r: 5,
                  stroke: "#3b82f6",
                  strokeWidth: 2,
                  fill: "#0a0a0f",
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
