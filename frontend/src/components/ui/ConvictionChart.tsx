import React from 'react';

import type { ScoreHistoryPointApi } from '../../lib/api/types';

interface ConvictionChartProps {
  points: ScoreHistoryPointApi[];
  loading?: boolean;
}

const WIDTH = 600;
const HEIGHT = 160;
const CHART_TOP = 12;
const CHART_BOTTOM = 128;

const buildLine = (
  points: { x: number; y: number }[],
) => points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');

const scaleY = (value: number) => CHART_BOTTOM - Math.max(0, Math.min(100, value)) * ((CHART_BOTTOM - CHART_TOP) / 100);

export function ConvictionChart({ points, loading = false }: ConvictionChartProps) {
  const [hoveredIndex, setHoveredIndex] = React.useState<number | null>(null);

  const normalized = React.useMemo(() => {
    if (points.length === 0) return [];
    return points.map((point, index) => ({
      x: points.length === 1 ? WIDTH / 2 : 24 + (index / (points.length - 1)) * (WIDTH - 48),
      scoreY: scaleY(point.score),
      probabilityY: scaleY((point.current_probability ?? 0) * 100),
      label: new Date(point.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric' }),
      score: point.score,
      probability: point.current_probability,
    }));
  }, [points]);

  const scorePath = buildLine(normalized.map((point) => ({ x: point.x, y: point.scoreY })));
  const probabilityPath = buildLine(normalized.map((point) => ({ x: point.x, y: point.probabilityY })));
  const hoveredPoint = hoveredIndex !== null ? normalized[hoveredIndex] : null;

  if (loading) {
    return <div className="h-48 animate-pulse rounded-xl border border-border bg-card" />;
  }

  if (points.length < 3) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-border bg-card text-sm text-text-muted">
        Chart building - more data needed
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="min-w-[320px] w-full"
        role="img"
        aria-label={`Conviction score over 48 hours with probability overlay, ${
          points[points.length - 1].score >= points[0].score ? 'rising' : 'falling'
        } from ${Math.round(points[0].score)} to ${Math.round(points[points.length - 1].score)}`}
        onMouseLeave={() => setHoveredIndex(null)}
      >
        <defs>
          <linearGradient id="score-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--rgb-prism-cyan))" stopOpacity="0.15" />
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

        <path d={`${scorePath} L ${normalized[normalized.length - 1].x} ${CHART_BOTTOM} L ${normalized[0].x} ${CHART_BOTTOM} Z`} fill="url(#score-fill)" />
        <path d={`${probabilityPath} L ${normalized[normalized.length - 1].x} ${CHART_BOTTOM} L ${normalized[0].x} ${CHART_BOTTOM} Z`} fill="url(#probability-fill)" />
        <path d={scorePath} fill="none" stroke="rgb(var(--rgb-prism-cyan))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d={probabilityPath} fill="none" stroke="rgb(var(--rgb-prism-violet))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {normalized.map((point, index) => (
          <rect
            key={point.label + index}
            x={index === 0 ? 0 : normalized[index - 1].x}
            y={0}
            width={index === 0 ? point.x + 12 : point.x - normalized[index - 1].x}
            height={HEIGHT}
            fill="transparent"
            onMouseMove={() => setHoveredIndex(index)}
          />
        ))}

        {hoveredPoint && (
          <>
            <line x1={hoveredPoint.x} x2={hoveredPoint.x} y1={CHART_TOP} y2={CHART_BOTTOM} stroke="rgb(var(--rgb-text-muted))" strokeDasharray="3 3" opacity="0.55" />
            <circle cx={hoveredPoint.x} cy={hoveredPoint.scoreY} r="3" fill="rgb(var(--rgb-prism-cyan))" />
            <circle cx={hoveredPoint.x} cy={hoveredPoint.probabilityY} r="3" fill="rgb(var(--rgb-prism-violet))" />
            <g transform={`translate(${Math.min(WIDTH - 170, hoveredPoint.x + 10)}, 18)`}>
              <rect width="160" height="44" rx="8" fill="rgb(var(--rgb-navy))" stroke="rgb(var(--rgb-border))" />
              <text x="10" y="15" fill="rgb(var(--rgb-text-secondary))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                {hoveredPoint.label}
              </text>
              <text x="10" y="30" fill="rgb(var(--rgb-prism-cyan))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                Score {Math.round(hoveredPoint.score)}
              </text>
              <text x="92" y="30" fill="rgb(var(--rgb-prism-violet))" fontSize="10" fontFamily="JetBrains Mono, monospace">
                Prob {Math.round((hoveredPoint.probability ?? 0) * 100)}%
              </text>
            </g>
          </>
        )}

        {normalized.filter((_, index) => index % Math.max(1, Math.floor(normalized.length / 4)) === 0 || index === normalized.length - 1).map((point, index) => (
          <text
            key={`${point.label}-${index}`}
            x={point.x}
            y={150}
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
  );
}
