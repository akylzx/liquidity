# LiquidMind

Predictive liquidity management system for neobank nostro account optimization. Forecasts cash flows across multi-currency correspondent accounts using ML, generates rebalancing recommendations, and runs stress tests against adverse scenarios.

## Architecture

```
frontend/          React 18 + TypeScript + Vite + TailwindCSS + Recharts
backend/           Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + LightGBM
├── api/           REST endpoints (accounts, forecasts, alerts, stress tests)
├── models/        SQLAlchemy ORM models (TimescaleDB hypertables)
├── services/      Forecast engine, rebalancing optimizer, alert generator
└── data_generator/ Synthetic data seeder for demo
```

**Infrastructure:** PostgreSQL 15 + TimescaleDB | Redis 7 | Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Run

```bash
git clone <repo-url> && cd liquidmind
docker compose up --build
```

The first run seeds the database with synthetic demo data (8 nostro accounts, ~180K transactions, forecasts, alerts, and rebalancing recommendations).

| Service  | URL                     |
|----------|-------------------------|
| Frontend | http://localhost:5173   |
| API      | http://localhost:8000   |
| API Docs | http://localhost:8000/docs |

### Re-seed the Database

The database is seeded automatically on first launch. If you need to re-seed (e.g. after schema changes or to refresh demo data), wipe the volume and rebuild:

```bash
docker compose down -v
docker compose up --build
```

Alternatively, run the seeder manually inside the running backend container:

```bash
docker compose exec backend python -m app.data_generator.seed_db
```

### Stop

```bash
docker compose down        # keep data
docker compose down -v     # wipe database volume
```

## Features

- **Command Center** — real-time treasury dashboard with account health gauges, balance sparklines, currency distribution, and alert feed
- **Cash Flow Forecasts** — LightGBM-based 5-day net flow predictions with confidence bands, historical flow analysis, and channel breakdowns
- **Rebalancing** — optimal transfer recommendations with animated flow diagram, urgency prioritization, approve/reject actions, and cost-benefit metrics
- **Risk & Stress Testing** — scenario simulation (FX shock, liquidity crisis, correspondent failure), radar-chart alert analysis, impact heatmaps, baseline vs stressed trajectory comparison

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts` | List accounts with summary |
| GET | `/api/accounts/{id}/history` | Balance history |
| GET | `/api/forecasts/{account_id}` | ML forecasts + historical flows |
| GET | `/api/forecasts/accuracy` | Model accuracy metrics |
| GET | `/api/alerts` | Active alerts |
| GET | `/api/recommendations` | Rebalancing recommendations |
| POST | `/api/recommendations/{id}/approve` | Approve transfer |
| POST | `/api/recommendations/{id}/reject` | Reject transfer |
| GET | `/api/stress/scenarios` | Available stress scenarios |
| POST | `/api/stress/run/{scenario_id}` | Execute stress test |
| GET | `/api/savings/metrics` | Cost-benefit analysis |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Recharts, React Query |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (asyncpg), Pydantic v2 |
| ML | LightGBM, pandas, numpy |
| Database | PostgreSQL 15 + TimescaleDB |
| Cache | Redis 7 |
| Infra | Docker Compose |
