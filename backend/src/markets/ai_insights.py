import asyncio
import json
from typing import Any

from groq import Groq
from pydantic import BaseModel, ValidationError

from src.config import Config
from src.markets.schemas import EventDetailRead
from src.utils.logger import logger


class AIInsightPayload(BaseModel):
    ai_insight: str


class AIInsightServices:
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    REQUEST_TIMEOUT_SECONDS = 12

    def __init__(self, *, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or getattr(Config, "GROQ_API_KEY", None)
        self.model = model
        self._client = Groq(api_key=self.api_key) if self.api_key else None

    @property
    def is_enabled(self) -> bool:
        return bool(self._client)

    def _build_prompt(self, event_detail: EventDetailRead) -> tuple[str, str]:
        market_summaries: list[dict[str, Any]] = []
        for market in event_detail.markets[:8]:
            market_summaries.append(
                {
                    "market_id": market.market_id,
                    "market_title": market.market_title,
                    "current_probability": market.current_probability,
                    "probability_delta": market.probability_delta,
                    "market_total_orders": market.market_total_orders,
                    "buy_notional": market.buy_notional,
                    "sell_notional": market.sell_notional,
                    "signal_score": market.signal.score,
                    "signal_direction": market.signal.direction,
                    "signal_classification": market.signal.classification,
                    "signal_notes": market.signal.notes[:4],
                }
            )

        payload = {
            "event_id": event_detail.event_id,
            "event_title": event_detail.event_title,
            "source": event_detail.source.value,
            "currency": event_detail.currency.value,
            "category": event_detail.category,
            "status": event_detail.status,
            "total_liquidity": event_detail.total_liquidity,
            "event_total_orders": event_detail.event_total_orders,
            "tracked_markets_count": event_detail.tracked_markets_count,
            "highest_scoring_market": (
                {
                    "market_id": event_detail.highest_scoring_market.market_id,
                    "market_title": event_detail.highest_scoring_market.market_title,
                    "focus_outcome_side": event_detail.highest_scoring_market.focus_outcome_side,
                    "focus_outcome_label": event_detail.highest_scoring_market.focus_outcome_label,
                    "current_probability": event_detail.highest_scoring_market.current_probability,
                    "probability_delta": event_detail.highest_scoring_market.probability_delta,
                    "signal_score": event_detail.highest_scoring_market.signal.score,
                    "signal_direction": event_detail.highest_scoring_market.signal.direction,
                    "signal_classification": event_detail.highest_scoring_market.signal.classification,
                    "signal_notes": event_detail.highest_scoring_market.signal.notes[:4],
                }
                if event_detail.highest_scoring_market
                else None
            ),
            "markets": market_summaries,
        }

        system_prompt = (
            "You write market reads for everyday users of a prediction-market app. "
            "Turn structured market data into a calm, clear explanation that helps a beginner understand what the screen means.\n\n"
            "RULES:\n"
            "- Explain what the market is leaning toward right now in plain English.\n"
            "- Be explicit about which side is moving: YES, NO, or the named outcome itself.\n"
            "- Use the strongest market, probability, delta, signal score, liquidity, and order flow as evidence when available.\n"
            "- Make the wording understandable to a smart beginner, not a quant.\n"
            "- Do not merely restate the top probability; explain what it means.\n"
            "- Do not mention providers, prompts, hidden models, or internal formulas.\n"
            "- Do not overclaim certainty; speak in probabilities, momentum, and conviction.\n"
            "- Write 3 short sentences, maximum 120 words total.\n"
            "- Sentence 1: what the market currently seems to favor.\n"
            "- Sentence 2: why Prism sees that from the data.\n"
            "- Sentence 3: how a normal user should interpret that read.\n"
            "- Return JSON only with one key: ai_insight.\n"
        )
        user_prompt = (
            "Generate an AI insight for this event detail payload:\n"
            f"{json.dumps(payload, ensure_ascii=True)}"
        )
        return system_prompt, user_prompt

    def _generate_sync(self, event_detail: EventDetailRead) -> str | None:
        if not self._client:
            return None

        system_prompt, user_prompt = self._build_prompt(event_detail)
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=180,
        )
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            return None

        try:
            parsed = AIInsightPayload(**json.loads(content))
        except (ValidationError, json.JSONDecodeError):
            logger.warning("AI insight response schema mismatch", exc_info=True)
            return None

        insight = parsed.ai_insight.strip()
        return insight[:400] if insight else None

    async def generate_event_insight(self, event_detail: EventDetailRead) -> str | None:
        if not self._client:
            return None
        try:
            logger.info("Generating AI insight for event %s", event_detail.event_id)
            insight = await asyncio.wait_for(
                asyncio.to_thread(self._generate_sync, event_detail),
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            if insight:
                logger.info("Generated AI insight for event %s", event_detail.event_id)
            return insight
        except asyncio.TimeoutError:
            logger.warning("AI insight generation timed out for event %s", event_detail.event_id)
        except Exception:
            logger.warning("AI insight generation failed for event %s", event_detail.event_id, exc_info=True)
        return None
