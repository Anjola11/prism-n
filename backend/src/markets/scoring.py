from pydantic import BaseModel, Field

from src.markets.models import MarketEngine, MarketSource


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


class MarketScoreClassification(str):
    NOISE = "noise"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    HIGH_CONVICTION = "high_conviction"


class MarketScoringInput(BaseModel):
    source: MarketSource = MarketSource.BAYSE
    engine: MarketEngine
    event_id: str
    market_id: str

    current_probability: float
    previous_probability: float | None = None
    baseline_sigma: float | None = None

    event_liquidity: float | None = None
    market_total_orders: int | None = None
    event_total_orders: int | None = None
    price_updates_in_window: int | None = None
    persistence_ticks: int = 0

    top_bid_depth: float | None = None
    top_ask_depth: float | None = None
    top_5_bid_depth: float | None = None
    top_5_ask_depth: float | None = None
    spread_bps: float | None = None
    buy_notional: float | None = None
    sell_notional: float | None = None

    orderbook_supported: bool | None = None
    ticker_supported: bool | None = None
    has_recent_reversal: bool = False
    nearing_close: bool = False


class ScoreFactorBreakdown(BaseModel):
    move: float = Field(ge=0.0, le=1.0)
    liquidity: float = Field(ge=0.0, le=1.0)
    volume: float = Field(ge=0.0, le=1.0)
    persistence: float = Field(ge=0.0, le=1.0)
    order_flow: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MarketScoreResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    classification: str
    formula: str
    factors: ScoreFactorBreakdown
    notes: list[str] = Field(default_factory=list)


class ScoringServices:
    def compute_signal_score(self, metrics: MarketScoringInput) -> MarketScoreResult:
        if metrics.engine == MarketEngine.CLOB:
            return self._compute_clob_score(metrics)
        return self._compute_amm_score(metrics)

    def _compute_clob_score(self, metrics: MarketScoringInput) -> MarketScoreResult:
        move = self._compute_move_factor(metrics)
        liquidity = self._compute_clob_liquidity_factor(metrics)
        volume = self._compute_volume_factor(metrics)
        order_flow = self._compute_order_flow_factor(metrics)
        persistence = self._compute_persistence_factor(metrics)

        raw_score = 100 * (
            (0.30 * move)
            + (0.25 * liquidity)
            + (0.20 * volume)
            + (0.15 * order_flow)
            + (0.10 * persistence)
        )

        factors = ScoreFactorBreakdown(
            move=move,
            liquidity=liquidity,
            volume=volume,
            persistence=persistence,
            order_flow=order_flow,
            confidence=None,
        )
        notes = self._build_notes(metrics, factors, formula="clob")

        return MarketScoreResult(
            score=round(_clamp(raw_score, 0.0, 100.0), 2),
            classification=self._classify_score(raw_score),
            formula="CLOB: 0.30M + 0.25L + 0.20V + 0.15O + 0.10P",
            factors=factors,
            notes=notes,
        )

    def _compute_amm_score(self, metrics: MarketScoringInput) -> MarketScoreResult:
        move = self._compute_move_factor(metrics)
        volume = self._compute_volume_factor(metrics)
        persistence = self._compute_persistence_factor(metrics)
        liquidity = self._compute_amm_liquidity_factor(metrics)
        confidence = self._compute_confidence_factor(metrics)

        raw_score = 100 * (
            (0.40 * move)
            + (0.20 * volume)
            + (0.20 * persistence)
            + (0.10 * liquidity)
            + (0.10 * confidence)
        )

        factors = ScoreFactorBreakdown(
            move=move,
            liquidity=liquidity,
            volume=volume,
            persistence=persistence,
            order_flow=None,
            confidence=confidence,
        )
        notes = self._build_notes(metrics, factors, formula="amm")

        return MarketScoreResult(
            score=round(_clamp(raw_score, 0.0, 100.0), 2),
            classification=self._classify_score(raw_score),
            formula="AMM: 0.40M + 0.20V + 0.20P + 0.10L + 0.10C",
            factors=factors,
            notes=notes,
        )

    def _compute_move_factor(self, metrics: MarketScoringInput) -> float:
        if metrics.previous_probability is None:
            return 0.0

        move = abs(metrics.current_probability - metrics.previous_probability)
        sigma = metrics.baseline_sigma or 0.05
        if sigma <= 0:
            sigma = 0.05

        normalized_move = move / max(sigma, 1e-6)
        return _clamp(normalized_move / 3.0)

    def _compute_clob_liquidity_factor(self, metrics: MarketScoringInput) -> float:
        depth_total = sum(
            value or 0.0
            for value in (
                metrics.top_bid_depth,
                metrics.top_ask_depth,
                metrics.top_5_bid_depth,
                metrics.top_5_ask_depth,
            )
        )
        depth_score = _clamp(depth_total / 100.0)

        spread_bps = metrics.spread_bps if metrics.spread_bps is not None else 10_000.0
        spread_score = _clamp(1.0 - (spread_bps / 500.0))

        return _clamp((0.65 * depth_score) + (0.35 * spread_score))

    def _compute_amm_liquidity_factor(self, metrics: MarketScoringInput) -> float:
        if metrics.event_liquidity is None:
            return 0.0
        return _clamp(metrics.event_liquidity / 1_000.0)

    def _compute_volume_factor(self, metrics: MarketScoringInput) -> float:
        event_orders = float(metrics.event_total_orders or 0)
        market_orders = float(metrics.market_total_orders or 0)
        update_count = float(metrics.price_updates_in_window or 0)

        blended_activity = (0.55 * market_orders) + (0.30 * event_orders) + (0.15 * update_count)
        return _clamp(blended_activity / 100.0)

    def _compute_order_flow_factor(self, metrics: MarketScoringInput) -> float:
        buy = float(metrics.buy_notional or 0.0)
        sell = float(metrics.sell_notional or 0.0)
        total = buy + sell
        if total <= 0:
            return 0.0

        imbalance = abs(buy - sell) / total
        directional_support = buy / total if buy >= sell else sell / total
        return _clamp((0.7 * imbalance) + (0.3 * directional_support))

    def _compute_persistence_factor(self, metrics: MarketScoringInput) -> float:
        base = _clamp(metrics.persistence_ticks / 6.0)
        if metrics.has_recent_reversal:
            base *= 0.5
        return _clamp(base)

    def _compute_confidence_factor(self, metrics: MarketScoringInput) -> float:
        confidence = 0.0
        if metrics.event_liquidity is not None:
            confidence += 0.35 * _clamp(metrics.event_liquidity / 1_000.0)
        if metrics.market_total_orders is not None:
            confidence += 0.30 * _clamp(metrics.market_total_orders / 50.0)
        if metrics.persistence_ticks:
            confidence += 0.20 * _clamp(metrics.persistence_ticks / 6.0)
        if not metrics.has_recent_reversal:
            confidence += 0.10
        if not metrics.nearing_close:
            confidence += 0.05
        return _clamp(confidence)

    def _classify_score(self, score: float) -> str:
        bounded = _clamp(score, 0.0, 100.0)
        if bounded < 30:
            return MarketScoreClassification.NOISE
        if bounded < 50:
            return MarketScoreClassification.WEAK
        if bounded < 70:
            return MarketScoreClassification.MODERATE
        if bounded < 85:
            return MarketScoreClassification.STRONG
        return MarketScoreClassification.HIGH_CONVICTION

    def _build_notes(
        self,
        metrics: MarketScoringInput,
        factors: ScoreFactorBreakdown,
        *,
        formula: str,
    ) -> list[str]:
        notes: list[str] = []
        if formula == "clob" and (metrics.orderbook_supported is False or metrics.ticker_supported is False):
            notes.append("CLOB score used fallback assumptions for unsupported microstructure fields.")
        if formula == "amm" and factors.confidence is not None and factors.confidence < 0.25:
            notes.append("AMM confidence is weak because participation/liquidity support is limited.")
        if metrics.baseline_sigma in (None, 0):
            notes.append("Baseline sigma was missing, so move normalization used a conservative fallback.")
        if metrics.previous_probability is None:
            notes.append("Previous probability was missing, so move factor was neutralized.")
        return notes
