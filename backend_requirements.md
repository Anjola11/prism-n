# Backend Payload Requirements (Prism v2)

This document specifies the exact JSON payloads the backend must return to feed the frontend's Universal Tab architecture. By conforming strictly to this format, the frontend can render both Single (Yes/No) and Combined (Multi-Candidate) markets using the exact same React `<EventDetail />` and `<SignalCard />` components.

---

## 1. Get All Events (Discovery / Tracker Feed)
**Endpoint:** `GET /api/v1/events` (and `GET /api/v1/tracker`)

Returns a lightweight array of events suitable for the `<SignalCard />`. We do not need the full list of outcomes here, only the highest scoring market.

```json
{
  "success": true,
  "data": [
    {
      "id": "evt_12345",
      "source": "Bayse",
      "title": "Who will win the 2026 FIFA World Cup?",
      "event_type": "combined", // "single" | "combined"
      "total_liquidity": 4200000,
      "last_updated": "12s ago",
      "highest_scoring_market": {
        "id": "mkt_arg",
        "name": "Argentina",
        "current_probability": 16,
        "probability_delta": -4,
        "signal": {
          "score": 88,
          "classification": "INFORMED_MOVE", // "INFORMED_MOVE" | "NOISE" | "UNCERTAIN"
          "direction": "RISING" // "RISING" | "FALLING" | "STABLE"
        }
      }
    }
  ]
}
```

---

## 2. Get Event Detail (Deep Dive)
**Endpoint:** `GET /api/v1/events/{event_id}`

Returns the full, quantitative payload required for the `EventDetail` deep dive. The crucial detail is the `outcomes` array.

- For **Single Events** (e.g. "Will Arsenal go trophyless?"), the `outcomes` array must contain exactly 2 entries (e.g. YES and NO).
- For **Combined Events** (e.g. "2026 World Cup Winner"), the `outcomes` array contains N entries (one for each team/candidate).

```json
{
  "success": true,
  "data": {
    "id": "evt_12345",
    "source": "Bayse",
    "title": "Who will win the 2026 FIFA World Cup?",
    "event_type": "combined",
    "total_liquidity": 4200000,
    "last_updated": "12s ago",
    "highest_scoring_market": {
      "id": "mkt_arg",
      "name": "Argentina",
      "score": 88
    },
    "ai_insight": "Money is rapidly exiting France and flowing into Argentina with heavy volume against baseline volatility...",
    "outcomes": [
      {
        "id": "mkt_arg",
        "name": "Argentina",
        "current_probability": 16,
        "probability_delta": 6,
        "liquidity": 1200000,
        "orders": 842,
        "volume_ratio": 3.2,
        "signal": {
          "score": 88,
          "classification": "INFORMED_MOVE",
          "direction": "RISING",
          "detected_at": "2026-04-21T14:32:00Z" // For charting the vertical detection line
        },
        "quant_data": {
          "trap_risk": "LOW", // "HIGH" | "MEDIUM" | "LOW"
          "trap_reason": "Strong liquidity and diverse flow reduces manipulation risk.",
          "smart_money_dominant": "Institutional", // "Institutional" | "Crowd" | "Mixed"
          "momentum_verdict": "Likely to Continue",
          "momentum_confidence": 88
        }
      },
      {
        "id": "mkt_fra",
        "name": "France",
        "current_probability": 12,
        "probability_delta": -4,
        "liquidity": 800000,
        "orders": 120,
        "volume_ratio": 1.1,
        "signal": {
          "score": 24,
          "classification": "NOISE",
          "direction": "FALLING",
          "detected_at": "2026-04-21T12:00:00Z"
        },
        "quant_data": {
          "trap_risk": "MEDIUM",
          "trap_reason": "Low volume on stable liquidity indicates minor positional shifting.",
          "smart_money_dominant": "Mixed",
          "momentum_verdict": "Inconclusive",
          "momentum_confidence": 42
        }
      }
      // ... more candidates
    ]
  }
}
```
