import math
from pydantic import BaseModel, Field

from src.markets.models import MarketEngine, MarketSource


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _log_scale(val: float, max_target: float) -> float:
    if val <= 0:
        return 0.0
    return _clamp(math.log1p(val) / math.log1p(max_target))


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
        """
        Score how significant this price move is.

        For prediction markets at Polymarket scale, even a 1-3% move in a deeply
        liquid market represents substantial capital conviction.  Using a flat
        divisor of 0.35 means a 3% move (which is enormous in a 95%+ market)
        only scores 0.09 — completely wrong.

        Instead we use the *sigma-multiple* logarithmically scaled: how many
        standard-deviation moves is this?  A 1-sigma move scores ~0.50,
        2-sigma ~0.75, 4-sigma (very rare, extreme news) ~0.90.
        We blend with a small absolute component to handle cases where sigma
        hasn't warmed up yet.
        """
        if metrics.previous_probability is None:
            return 0.0

        move = abs(metrics.current_probability - metrics.previous_probability)
        if move == 0.0:
            return 0.0

        sigma = metrics.baseline_sigma or 0.02  # tighter default: 2% is already notable
        if sigma <= 0:
            sigma = 0.02

        # Sigma-multiple component: log-scaled so 1σ ≈ 0.5, 2σ ≈ 0.7, 4σ ≈ 0.9
        sigma_multiple = move / sigma
        sigma_score = _log_scale(sigma_multiple, 6.0)  # 6σ = ceiling

        # Absolute component: calibrated so 5% move = 0.5, 15% = 0.9 (log scale)
        abs_score = _log_scale(move, 0.15)

        return _clamp((0.65 * sigma_score) + (0.35 * abs_score))

    def _compute_clob_liquidity_factor(self, metrics: MarketScoringInput) -> float:
        """
        Score depth and tightness of the CLOB.

        Real Polymarket top-of-book depth on active markets runs $10k–$200k
        per side.  The previous benchmark of $25k total (all 4 levels combined)
        saturated at ~$6k per level — far too low.  We benchmark against $500k
        total depth (top-1 + top-5 bid + ask combined) so only the deepest
        markets score 1.0.

        Spread: Polymarket CLOB normal spread is 1–30 bps on liquid markets,
        200–500 bps on thin ones.  Previous 500 bps ceiling was right but
        1 – x/500 is linear; we keep that since spread should penalise sharply.
        """
        depth_total = sum(
            value or 0.0
            for value in (
                metrics.top_bid_depth,
                metrics.top_ask_depth,
                metrics.top_5_bid_depth,
                metrics.top_5_ask_depth,
            )
        )
        depth_score = _log_scale(depth_total, 500_000.0)

        spread_bps = metrics.spread_bps if metrics.spread_bps is not None else 5_000.0
        spread_score = _clamp(1.0 - (spread_bps / 500.0))

        return _clamp((0.75 * depth_score) + (0.25 * spread_score))

    def _compute_amm_liquidity_factor(self, metrics: MarketScoringInput) -> float:
        if metrics.event_liquidity is None or metrics.event_liquidity <= 0:
            return 0.0
        # Bayse AMM pools: active events have $10k–$2M TVL.  Benchmark $500k.
        return _log_scale(metrics.event_liquidity, 500_000.0)

    def _compute_volume_factor(self, metrics: MarketScoringInput) -> float:
        """
        Score trading activity.

        Polymarket active markets have 10k–500k+ lifetime orders.  The previous
        5k benchmark meant any market with 5k+ orders got 1.0 — all candidates
        in a combined event would score identically.  We raise the ceiling to
        50k for market-level and 500k for event-level so there is real spread.

        price_updates_in_window measures how frequently the best bid/ask has moved
        in the current observation window; 50 updates is extremely active.
        """
        market_orders = float(metrics.market_total_orders or 0)
        event_orders = float(metrics.event_total_orders or 0)
        update_count = float(metrics.price_updates_in_window or 0)

        market_orders_score = _log_scale(market_orders, 50_000.0)
        event_orders_score = _log_scale(event_orders, 500_000.0)
        update_score = _log_scale(update_count, 50.0)

        return _clamp((0.70 * market_orders_score) + (0.20 * event_orders_score) + (0.10 * update_score))

    def _compute_order_flow_factor(self, metrics: MarketScoringInput) -> float:
        """
        Score directional conviction from order flow imbalance.

        On Polymarket CLOB the order book notional per side can run $5k–$5M
        on a single fill event.  The previous $10k total benchmark meant anything
        with $10k+ flow was already at max scale — removing all differentiation
        between a $10k tick and a $5M institutional sweep.  Raise to $500k.
        """
        buy = float(metrics.buy_notional or 0.0)
        sell = float(metrics.sell_notional or 0.0)
        total = buy + sell
        if total <= 0:
            return 0.0

        imbalance = abs(buy - sell) / total
        directional_support = buy / total if buy >= sell else sell / total
        flow_quality = (0.7 * imbalance) + (0.3 * directional_support)
        notional_scale = _log_scale(total, 500_000.0)

        return _clamp(flow_quality * (0.3 + 0.7 * notional_scale))


    def _compute_persistence_factor(self, metrics: MarketScoringInput) -> float:
        base = _clamp(metrics.persistence_ticks / 12.0)
        if metrics.has_recent_reversal:
            base *= 0.5
        return _clamp(base)

    def _compute_confidence_factor(self, metrics: MarketScoringInput) -> float:
        confidence = 0.0
        if metrics.event_liquidity is not None:
            confidence += 0.35 * _log_scale(metrics.event_liquidity, 100_000.0)
        if metrics.market_total_orders is not None:
            confidence += 0.30 * _log_scale(metrics.market_total_orders, 1_000.0)
        if metrics.persistence_ticks:
            confidence += 0.20 * _clamp(metrics.persistence_ticks / 12.0)
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
        if metrics.baseline_sigma in (None, 0) and factors.move > 0:
            notes.append("Historical baseline is still warming up, so move normalization used a conservative fallback.")
        if metrics.previous_probability is None:
            notes.append("Previous probability was missing, so move factor was neutralized.")
        return notes
