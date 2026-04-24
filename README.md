# Prism: Predictive Market Intelligence Engine

> **Institutional-grade market aggregation, signal normalization, and real-time intelligence for decentralized prediction markets.**

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-306998?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19+-61DAFB?style=flat-square&logo=react&logoColor=white)](https://react.dev/)
[![TypeScript 6](https://img.shields.io/badge/TypeScript-6+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)

---

## Executive Summary

### The Problem
Prediction markets are fundamentally fragmented. Traders and analysts struggle with inconsistent pricing, disparate liquidity pools, and a lack of standardized risk metrics across platforms like **Polymarket** and **Bayse**. Identifying high-conviction signals amidst the noise of "thin" order books and low-activity markets requires deep technical expertise and manual aggregation.

### The Solution
**Prism** is a unified intelligence layer designed to normalize prediction market data into actionable insights. By aggregating real-time streams from multiple sources and applying a sophisticated scoring engine, Prism provides a standardized "Conviction Score" for any event. Whether a market uses a **Central Limit Order Book (CLOB)** or an **Automated Market Maker (AMM)**, Prism translates raw microstructure data into a single, institutional-grade intelligence feed.

---

## Business Logic & Value Proposition

### The Prism Scoring Engine
The core of Prism is its dual-engine scoring architecture. Unlike simple price aggregators, Prism analyzes the underlying "health" of a market to determine the validity of a price move.

*   **CLOB Normalization**: Analyzes bid-ask depth, spread stability (in basis points), and order flow imbalance to identify true institutional conviction vs. temporary noise.
*   **AMM Normalization**: Focuses on liquidity density, persistence ticks, and volume-to-liquidity ratios to detect slippage-resistant signals.
*   **Unified Scoring**: All signals are normalized on a 0-100 scale and classified from "Noise" to "High Conviction," allowing for seamless comparison across different market architectures.

### Data Flow & Scalability
Prism is built for sub-second intelligence.
1.  **Ingestion**: Real-time WebSocket managers maintain persistent connections to Polymarket and Bayse.
2.  **Processing**: Asynchronous workers compute market baselines and signal snapshots without blocking the main event loop.
3.  **Intelligence**: An AI-driven insight layer (powered by Groq) enriches raw market data with qualitative analysis of trending events.
4.  **Delivery**: A service-layer-first pagination system ensures O(1) response times, even as the global event database scales into the thousands.

---

## High-Level Architecture

Prism utilizes a decoupled architecture designed for high throughput and low-latency data delivery.

*   **Frontend**: A premium React application utilizing **TanStack Router** for type-safe navigation and **TanStack Query** for efficient server-state management.
*   **Backend**: A high-performance **FastAPI** service layer using asynchronous SQLAlchemy and Redis for real-time state synchronization.
*   **Database Layer**: **PostgreSQL** serves as the primary source of truth for historical baselines, while **Redis** handles hot-data caching and session management.

---

## Tech Stack

### 🎨 Frontend
*   **Core**: React 19, TypeScript 6, Vite 6
*   **State & Routing**: TanStack Query (React Query), TanStack Router
*   **Styling**: Tailwind CSS 3.4
*   **Visuals**: Recharts (Data Viz), Lucide React (Icons), GSAP (Micro-animations), Three.js (3D Components)

### ⚙️ Backend
*   **Framework**: FastAPI (Asynchronous Python 3.13)
*   **Persistence**: PostgreSQL 16 (via SQLModel/SQLAlchemy), Alembic (Migrations)
*   **Caching**: Redis 7.3
*   **API Clients**: HTTPX (Pooled Async), WebSockets
*   **Intelligence**: Groq AI SDK

### 🛠️ Tooling
*   **Package Management**: `uv` (Python), `npm` (Node.js)
*   **Communications**: Brevo (Email/OTP)

---

## Project Structure

```text
prism_new/
├── backend/                  # FastAPI Application
│   ├── src/
│   │   ├── admin/            # Administrative Management
│   │   ├── auth/             # JWT & OTP Security Layer
│   │   ├── db/               # PostgreSQL & Redis Configuration
│   │   ├── markets/          # CORE: Scoring Engine & Market Workers
│   │   │   ├── scoring.py    # CLOB/AMM Normalization Logic
│   │   │   ├── services.py   # Aggregation & Business Logic
│   │   │   └── discovery_worker.py # Background Sync Workers
│   │   └── utils/            # Bayse/Polymarket API Clients
│   ├── pyproject.toml        # Backend Dependencies
│   └── main.py               # Application Entry Point
├── frontend/                 # React Application
│   ├── src/
│   │   ├── components/       # UI & Brand Components
│   │   ├── hooks/            # Custom React Hooks (Infinite Scroll)
│   │   ├── lib/              # API Clients & Shared Types
│   │   └── pages/            # View Components
│   ├── package.json          # Frontend Dependencies
│   └── vite.config.ts        # Build Configuration
└── README.md
```

---

## Detailed Setup Guide

### Environment Configuration
Create a `.env` file in the `backend/` directory with the following variables:

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection string (`redis://...`) |
| `JWT_SECRET_KEY` | Secret key for token generation |
| `BAYSE_API_KEY` | API Key for Bayse Relay access |
| `GROQ_API_KEY` | API Key for AI Insights layer |
| `BREVO_API_KEY` | API Key for Email/OTP services |

---

### Backend Setup

#### Method A: Standard (pip)
1.  Navigate to the backend directory: `cd backend`
2.  Create a virtual environment: `python -m venv .venv`
3.  Activate the environment:
    *   Windows: `.\.venv\Scripts\Activate.ps1`
    *   Unix: `source .venv/bin/activate`
4.  Install dependencies: `pip install -r requirements.txt` (or `pip install .`)
5.  Run migrations: `alembic upgrade head`
6.  Start the server: `python main.py`

#### Method B: Modern (uv - Recommended)
1.  Navigate to the backend directory: `cd backend`
2.  Sync and install dependencies: `uv sync`
3.  Run migrations: `uv run alembic upgrade head`
4.  Start the server: `uv run python main.py`

---

### Frontend Setup
1.  Navigate to the frontend directory: `cd frontend`
2.  Install dependencies: `npm install`
3.  Start the development server: `npm run dev`
4.  Access the UI at `http://localhost:5173`

---

## Key Features

### Technical Features
*   **Normalized Scoring Engine**: Dedicated algorithms for CLOB and AMM liquidity structures.
*   **Asynchronous Task Processing**: Background workers for market discovery and baseline updates.
*   **Real-time WebSocket Integration**: Sub-second price and order book updates from multiple sources.
*   **O(1) Service Pagination**: Optimized data retrieval layer for large-scale market indices.
*   **JWT & OTP Authentication**: Secure, enterprise-grade user authentication flow.

### User Features
*   **Unified Discovery Hub**: High-conviction events across all markets in a single view.
*   **Deep Intelligence Cards**: Detailed breakdown of score factors (Liquidity, Volume, Persistence).
*   **Real-time Portfolio Tracking**: Live monitoring of tracked positions with instant price updates.
*   **AI Market Insights**: Narrative analysis of market trends and emerging opportunities.

---

## API Documentation

Prism provides an interactive API documentation interface. Once the backend is running, you can explore the endpoints at:

👉 **[http://localhost:8000/docs](http://localhost:8000/docs)** (Swagger UI)

All primary endpoints for Market Discovery, Portfolio Tracking, and Authentication are documented with full request/response schemas.
