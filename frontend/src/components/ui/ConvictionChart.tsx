import React from 'react';

import type { ScoreHistoryPointApi } from '../../lib/api/types';

interface ConvictionChartProps {
  points: ScoreHistoryPointApi[];
  loading?: boolean;
  observedPoints?: number;
  note?: string | null;
}

const WIDTH = 600;
const HEIGHT = 180;
const CHART_TOP = 16;
const CHART_BOTTOM = 132;

const buildLine = (points: { x: number; y: number }[]) =>
  points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');

const scaleY = (value: number) =>
  CHART_BOTTOM - Math.max(0, Math.min(100, value)) * ((CHART_BOTTOM - CHART_TOP) / 100);

export function ConvictionChart({
  points,
  loading = false,
  observedPoints = points.filter((point) => !point.estimated).length,
  note,
}: ConvictionChartProps) {
  const [hoveredIndex, setHoveredIndex] = React.useState<number | null>(null);

  const normalized = React.useMemo(() => {
    if (points.length === 0) return [];
    return points.map((point, index) => ({
      ...point,
      x: points.length === 1 ? WIDTH / 2 : 24 + (index / Math.max(points.length - 1, 1)) * (WIDTH - 48),
      scoreY: scaleY(point.score),
      probabilityY: scaleY((point.current_probability ?? 0) * 100),
      label: new Date(point.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric' }),
      probabilityPercent: Math.round((point.current_probability ?? 0) * 100),
    }));
  }, [points]);

  const scorePoints = normalized.map((point) => ({ x: point.x, y: point.scoreY }));
  const probabilityPoints = normalized.map((point) => ({ x: point.x, y: point.probabilityY }));
  const scorePath = scorePoints.length > 0 ? buildLine(scorePoints) : '';
  const probabilityPath = probabilityPoints.length > 0 ? buildLine(probabilityPoints) : '';
  const hoveredPoint = hoveredIndex !== null ? normalized[hoveredIndex] : null;
  const warmup = observedPoints < 3;

  if (loading && points.length === 0) {
    return <div className="h-56 animate-pulse rounded-xl border border-border bg-card" />;
  }

  if (points.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border border-border bg-card text-sm text-text-muted">
        Chart building - more data needed
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col items-start gap-2 font-mono text-[10px] uppercase tracking-[0.18em]">
        <span className="inline-flex items-center gap-2 text-prism-cyan">
          <span className="h-2 w-2 rounded-full bg-prism-cyan" />
          Conviction
        </span>
        <span className="inline-flex items-center gap-2 text-prism-violet">
          <span className="h-2 w-2 rounded-full bg-prism-violet" />
          Probability
        </span>
        <span className="text-text-muted">
          {warmup ? `${observedPoints} real snapshot${observedPoints === 1 ? '' : 's'} + warm-start bridge` : `${observedPoints} real snapshots`}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-card p-3">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="min-w-[320px] w-full"
          role="img"
          aria-label="Conviction and probability chart"
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <defs>
            <linearGradient id="score-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgb(var(--rgb-prism-cyan))" stopOpacity="0.18" />
              <stop offset="100%" stopColor="rgb(var(--rgb-prism-cyan))" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="probability-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgb(var(--rgb-prism-violet))" stopOpacity="0.12" />
              <stop offset="100%" stopColor="rgb(var(--rgb-prism-violet))" stopOpacity="0" />
            </linearGradient>
          </defs>

          {[25, 50, 75].map((marker) => (
            <line
              key={marker}
              x1="24"
              x2={WIDTH - 24}
              y1={scaleY(marker)}
              y2={scaleY(marker)}
              stroke="rgb(var(--rgb-text-muted))"
              strokeDasharray="2 4"
              opacity={marker === 50 ? 0.35 : 0.2}
            />
          ))}

          {scorePoints.length > 1 ? (
            <path
              d={`${scorePath} L ${normalized[normalized.length - 1].x} ${CHART_BOTTOM} L ${normalized[0].x} ${CHART_BOTTOM} Z`}
              fill="url(#score-fill)"
            />
          ) : null}
          {probabilityPoints.length > 1 ? (
            <path
              d={`${probabilityPath} L ${normalized[normalized.length - 1].x} ${CHART_BOTTOM} L ${normalized[0].x} ${CHART_BOTTOM} Z`}
              fill="url(#probability-fill)"
            />
          ) : null}

          {scorePoints.length > 1 ? (
            <path d={scorePath} fill="none" stroke="rgb(var(--rgb-prism-cyan))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          ) : null}
          {probabilityPoints.length > 1 ? (
            <path d={probabilityPath} fill="none" stroke="rgb(var(--rgb-prism-violet))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          ) : null}

          {normalized.map((point, index) => (
            <g key={`${point.created_at}-${index}`}>
              <circle cx={point.x} cy={point.scoreY} r={point.estimated ? 2.5 : 3.5} fill="rgb(var(--rgb-prism-cyan))" opacity={point.estimated ? 0.65 : 1} />
              <circle cx={point.x} cy={point.probabilityY} r={point.estimated ? 2.5 : 3.5} fill="rgb(var(--rgb-prism-violet))" opacity={point.estimated ? 0.65 : 1} />
              <rect
                x={index === 0 ? Math.max(point.x - 18, 0) : normalized[index - 1].x}
                y={0}
                width={index === 0 ? 36 : Math.max(point.x - normalized[index - 1].x, 22)}
                height={HEIGHT}
                fill="transparent"
                onMouseMove={() => setHoveredIndex(index)}
              />
            </g>
          ))}

          {hoveredPoint ? (
            <>
              <line x1={hoveredPoint.x} x2={hoveredPoint.x} y1={CHART_TOP} y2={CHART_BOTTOM} stroke="rgb(var(--rgb-text-muted))" strokeDasharray="3 3" opacity="0.55" />
              <g transform={`translate(${Math.min(WIDTH - 188, hoveredPoint.x + 10)}, 18)`}>
                <rect width="178" height="54" rx="8" fill="rgb(var(--rgb-navy))" stroke="rgb(var(--rgb-border))" />
                <text x="10" y="15" fill="rgb(var(--rgb-text-secondary))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                  {hoveredPoint.label}
                </text>
                <text x="10" y="31" fill="rgb(var(--rgb-prism-cyan))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                  Conviction {Math.round(hoveredPoint.score)}
                </text>
                <text x="92" y="31" fill="rgb(var(--rgb-prism-violet))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                  Probability {hoveredPoint.probabilityPercent}%
                </text>
                {hoveredPoint.estimated ? (
                  <text x="10" y="45" fill="rgb(var(--rgb-text-muted))" fontSize="9" fontFamily="JetBrains Mono, monospace">
                    Estimated warm-start point
                  </text>
                ) : null}
              </g>
            </>
          ) : null}

          {normalized
            .filter((_, index) => index % Math.max(1, Math.floor(normalized.length / 4)) === 0 || index === normalized.length - 1)
            .map((point, index) => (
              <text
                key={`${point.label}-${index}`}
                x={point.x}
                y={160}
                textAnchor="middle"
                fill="rgb(var(--rgb-text-muted))"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
              >
                {point.label}
              </text>
            ))}
        </svg>
      </div>

      <div className="flex flex-col items-start gap-2">
        <p className="text-sm leading-6 text-text-secondary">
          Conviction shows how strong Prism thinks the move is. Probability shows where the market is priced. When both rise together, the move is strengthening; when probability moves without conviction, treat the move with more caution.
        </p>
        {warmup ? (
          <span className="rounded border border-prism-blue/30 bg-prism-blue/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-prism-cyan">
            Warm-up mode
          </span>
        ) : null}
      </div>
      {note ? <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">{note}</p> : null}
    </div>
  );
}
