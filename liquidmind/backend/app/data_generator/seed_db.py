"""Seed the database with synthetic data."""

import asyncio
import uuid
import sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base
from app.models import (
    Account, Transaction, BalanceSnapshot, Forecast, Corridor,
    Alert, Holiday, FxRate, StressScenario,
)
from app.models.rebalance import RebalanceRecommendation
from app.data_generator.generator import SyntheticDataGenerator, ACCOUNTS


def _convert_timestamps(record: dict) -> dict:
    """Convert pandas Timestamp values to Python datetime for asyncpg compatibility."""
    return {
        k: v.to_pydatetime() if isinstance(v, pd.Timestamp) else v
        for k, v in record.items()
    }


def generate_forecasts(account_ids: dict[int, uuid.UUID], rng: np.random.Generator) -> list[dict]:
    """Generate synthetic forecast data for each account (next 5 days)."""
    now = datetime.now(timezone.utc)
    today = date.today()
    forecasts = []

    for acct_idx, acct in enumerate(ACCOUNTS):
        aid = account_ids[acct_idx]
        base_net = rng.normal(0, acct["max_balance"] * 0.01)

        for horizon in range(1, 6):
            target_date = today + timedelta(days=horizon)
            predicted_net = base_net * (1 + rng.normal(0, 0.3))
            predicted_in = abs(predicted_net) * rng.uniform(1.5, 3.0) if predicted_net > 0 else abs(predicted_net) * rng.uniform(0.3, 0.8)
            predicted_out = predicted_in - predicted_net
            confidence_low = predicted_net - abs(predicted_net) * rng.uniform(0.3, 0.7)
            confidence_high = predicted_net + abs(predicted_net) * rng.uniform(0.3, 0.7)

            forecasts.append({
                "id": uuid.uuid4(),
                "time": now,
                "account_id": aid,
                "currency": acct["currency"],
                "horizon_date": target_date,
                "predicted_net": round(predicted_net, 2),
                "predicted_in": round(predicted_in, 2),
                "predicted_out": round(predicted_out, 2),
                "confidence_low": round(confidence_low, 2),
                "confidence_high": round(confidence_high, 2),
                "model_version": "lgbm_demo_v1",
                "features_json": {
                    "rolling_7d_volume": round(rng.uniform(50000, 500000), 2),
                    "day_of_week_effect": round(rng.uniform(-0.2, 0.3), 4),
                    "month_end_proximity": horizon if today.day >= 25 else 0,
                    "channel_swift_pct": round(rng.uniform(0.05, 0.15), 4),
                    "fx_volatility_7d": round(rng.uniform(0.001, 0.008), 5),
                },
            })

    return forecasts


def generate_alerts(account_ids: dict[int, uuid.UUID], rng: np.random.Generator) -> list[dict]:
    """Generate realistic demo alerts."""
    now = datetime.now(timezone.utc)
    alerts = []

    alert_templates = [
        {
            "severity": "critical",
            "alert_type": "threshold_breach",
            "title": "Balance below minimum threshold",
            "description": "Account balance projected to breach minimum in 4 hours based on pending outflows.",
            "horizon_hours": 4,
            "impact_mult": 0.15,
        },
        {
            "severity": "critical",
            "alert_type": "liquidity_gap",
            "title": "Liquidity gap detected — SWIFT settlement delay",
            "description": "Inbound SWIFT transfer delayed by 48h. Gap of projected shortfall on counterparty.",
            "horizon_hours": 24,
            "impact_mult": 0.08,
        },
        {
            "severity": "warning",
            "alert_type": "concentration_risk",
            "title": "Excess concentration in single nostro account",
            "description": "Over 40% of EUR liquidity held in a single account. Consider redistribution.",
            "horizon_hours": None,
            "impact_mult": 0.25,
        },
        {
            "severity": "warning",
            "alert_type": "forecast_divergence",
            "title": "Forecast divergence — actual outflows 2x predicted",
            "description": "Outflows today exceeding model prediction by 2.1x. Monitoring for correction.",
            "horizon_hours": 8,
            "impact_mult": 0.05,
        },
        {
            "severity": "warning",
            "alert_type": "settlement_delay",
            "title": "SEPA batch settlement delayed",
            "description": "Expected SEPA batch (EUR 1.2M) not received. ETA now T+8h.",
            "horizon_hours": 8,
            "impact_mult": 0.06,
        },
        {
            "severity": "advisory",
            "alert_type": "optimization",
            "title": "Idle capital opportunity detected",
            "description": "Account holding 3x minimum for >72h. Consider rebalancing to higher-yield position.",
            "horizon_hours": None,
            "impact_mult": 0.02,
        },
        {
            "severity": "advisory",
            "alert_type": "fx_exposure",
            "title": "Unhedged FX exposure increasing",
            "description": "Net GBP exposure grown 15% in 7 days. Consider hedging or rebalancing.",
            "horizon_hours": 72,
            "impact_mult": 0.03,
        },
        {
            "severity": "advisory",
            "alert_type": "pattern_anomaly",
            "title": "Unusual P2P volume pattern",
            "description": "P2P outflow volume 40% above seasonal average for past 3 days.",
            "horizon_hours": 48,
            "impact_mult": 0.01,
        },
    ]

    for template in alert_templates:
        # Assign to a random account
        acct_idx = rng.integers(0, len(ACCOUNTS))
        acct = ACCOUNTS[acct_idx]
        impact = acct["max_balance"] * template["impact_mult"]

        alerts.append({
            "id": uuid.uuid4(),
            "created_at": now - timedelta(minutes=int(rng.uniform(5, 120))),
            "account_id": account_ids[acct_idx],
            "severity": template["severity"],
            "alert_type": template["alert_type"],
            "title": template["title"],
            "description": template["description"],
            "projected_impact": round(impact, 2),
            "horizon_hours": template["horizon_hours"],
            "is_acknowledged": False,
        })

    return alerts


def generate_rebalancing(account_ids: dict[int, uuid.UUID], rng: np.random.Generator) -> list[dict]:
    """Generate demo rebalancing recommendations."""
    now = datetime.now(timezone.utc)
    batch_id = uuid.uuid4()
    recommendations = []

    # Create realistic transfer recommendations
    transfers = [
        {"src": 2, "tgt": 0, "urgency": "critical", "reason": "EUR account below minimum — emergency SWIFT transfer from USD surplus"},
        {"src": 3, "tgt": 4, "urgency": "high", "reason": "GBP account approaching threshold — preemptive funding from USD reserve"},
        {"src": 0, "tgt": 1, "urgency": "medium", "reason": "Rebalance EUR positions — idle capital in Deutsche Bank exceeds optimal level"},
        {"src": 2, "tgt": 5, "urgency": "medium", "reason": "CHF account below target — funding from USD surplus for upcoming settlements"},
        {"src": 7, "tgt": 6, "urgency": "low", "reason": "PLN account optimization — move excess EUR from HSBC to PLN correspondent for better yield"},
    ]

    for t in transfers:
        src_acct = ACCOUNTS[t["src"]]
        tgt_acct = ACCOUNTS[t["tgt"]]
        amount = round(rng.uniform(src_acct["min_balance"] * 0.1, src_acct["min_balance"] * 0.5), 2)

        # Estimate cost based on channel
        if src_acct["currency"] == tgt_acct["currency"]:
            cost = round(rng.uniform(0.20, 5.0), 2)
        else:
            cost = round(rng.uniform(15.0, 50.0), 2)

        recommendations.append({
            "id": uuid.uuid4(),
            "created_at": now - timedelta(minutes=int(rng.uniform(1, 30))),
            "batch_id": batch_id,
            "source_id": account_ids[t["src"]],
            "target_id": account_ids[t["tgt"]],
            "amount": amount,
            "currency": src_acct["currency"],
            "urgency": t["urgency"],
            "reason": t["reason"],
            "estimated_cost": cost,
            "estimated_arrival": now + timedelta(hours=int(rng.uniform(2, 48))),
            "status": "pending",
        })

    return recommendations


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    gen = SyntheticDataGenerator(seed=42, days=365)
    data = gen.generate_all()
    rng = np.random.default_rng(42)

    async with session_factory() as session:
        # Accounts
        for a in data["accounts"]:
            session.add(Account(**a))
        await session.commit()
        print(f"Seeded {len(data['accounts'])} accounts")

        # Holidays
        for h in data["holidays"]:
            session.add(Holiday(**h))
        await session.commit()
        print(f"Seeded {len(data['holidays'])} holidays")

        # Corridors
        for c in data["corridors"]:
            session.add(Corridor(**c))
        await session.commit()
        print(f"Seeded {len(data['corridors'])} corridors")

        # Stress scenarios
        for s in data["stress_scenarios"]:
            session.add(StressScenario(**s))
        await session.commit()
        print(f"Seeded {len(data['stress_scenarios'])} stress scenarios")

        # Transactions — bulk insert in batches
        txn_df = data["transactions"]
        batch_size = 10_000
        for start in range(0, len(txn_df), batch_size):
            batch = txn_df.iloc[start:start + batch_size]
            objects = [Transaction(**_convert_timestamps(row)) for row in batch.to_dict("records")]
            session.add_all(objects)
            await session.commit()
            print(f"  Transactions: {min(start + batch_size, len(txn_df)):,}/{len(txn_df):,}")
        print(f"Seeded {len(txn_df):,} transactions")

        # Balance snapshots — bulk insert
        bal_df = data["balance_snapshots"]
        for start in range(0, len(bal_df), batch_size):
            batch = bal_df.iloc[start:start + batch_size]
            objects = [BalanceSnapshot(**_convert_timestamps(row)) for row in batch.to_dict("records")]
            session.add_all(objects)
            await session.commit()
        print(f"Seeded {len(bal_df):,} balance snapshots")

        # FX rates
        fx_df = data["fx_rates"]
        objects = [FxRate(**_convert_timestamps(row)) for row in fx_df.to_dict("records")]
        session.add_all(objects)
        await session.commit()
        print(f"Seeded {len(fx_df):,} FX rates")

        # Forecasts
        forecasts = generate_forecasts(gen.account_ids, rng)
        for f in forecasts:
            session.add(Forecast(**f))
        await session.commit()
        print(f"Seeded {len(forecasts)} forecasts")

        # Alerts
        alerts = generate_alerts(gen.account_ids, rng)
        for a in alerts:
            session.add(Alert(**a))
        await session.commit()
        print(f"Seeded {len(alerts)} alerts")

        # Rebalancing recommendations
        recommendations = generate_rebalancing(gen.account_ids, rng)
        for r in recommendations:
            session.add(RebalanceRecommendation(**r))
        await session.commit()
        print(f"Seeded {len(recommendations)} rebalancing recommendations")

    await engine.dispose()
    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
