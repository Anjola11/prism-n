import React from 'react';

interface ScoreSparklineProps {
  points: { score: number; created_at: string }[];
  width?: number;
  height?: number;
  loading?: boolean;
}

const getStrokeClass = (points: { score: number }[]) => {
  if (points.length < 2) return 'signal-trend-neutral';
  const first = points[0].score;
  const last = points[points.length - 1].score;
  if (last > first) return 'signal-trend-up';
  if (last < first) return 'signal-trend-down';
  return 'signal-trend-neutral';
};

export function ScoreSparkline({ points, width = 80, height = 28, loading = false }: ScoreSparklineProps) {
  const normalized = React.useMemo(() => {
    if (points.length === 0) return [];
    if (points.length === 1) {
      return [{ x: width / 2, y: height / 2, score: points[0].score }];
    }
    return points.map((point, index) => {
      const x = (index / (points.length - 1)) * (width - 4) + 2;
      const y = 26 - Math.max(0, Math.min(100, point.score)) * 0.24;
      return { x, y, score: point.score };
    });
  }, [height, points, width]);

  const polylinePoints = normalized.map((point) => `${point.x},${point.y}`).join(' ');
  const lastPoint = normalized[normalized.length - 1];
  const strokeClass = getStrokeClass(points);
  const trendLabel =
    points.length >= 2
      ? points[points.length - 1].score > points[0].score
        ? `rising from ${Math.round(points[0].score)} to ${Math.round(points[points.length - 1].score)}`
        : points[points.length - 1].score < points[0].score
          ? `falling from ${Math.round(points[0].score)} to ${Math.round(points[points.length - 1].score)}`
          : `holding near ${Math.round(points[0].score)}`
      : 'building';

  if (loading) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label="Score history loading"
        className="opacity-70"
      >
        <line
          x1="2"
          x2={width - 2}
          y1={height / 2}
          y2={height / 2}
          className="stroke-current text-text-muted"
          strokeDasharray="3 3"
          strokeWidth="1.5"
        />
      </svg>
    );
  }

  if (normalized.length === 0) {
    return null;
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
      aria-label={`Conviction sparkline ${trendLabel}`}
      className={`${strokeClass} overflow-visible`}
    >
      <defs>
        <filter id={`sparkline-glow-${width}-${height}`}>
          <feDropShadow dx="0" dy="0" stdDeviation="1.5" floodOpacity="0.4" />
        </filter>
      </defs>
      <polyline
        points={polylinePoints}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        filter={`url(#sparkline-glow-${width}-${height})`}
      />
      {lastPoint && <circle cx={lastPoint.x} cy={lastPoint.y} r="2" fill="currentColor" />}
    </svg>
  );
}
