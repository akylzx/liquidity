"""High-level forecast service that orchestrates ML predictions and stores results."""

import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.forecast import Forecast
from app.models.transaction import Transaction, BalanceSnapshot
from app.models.fx import FxRate


async def get_latest_balances(session: AsyncSession) -> dict[str, dict]:
    """Get the latest balance snapshot for each account."""
    query = text("""
        SELECT DISTINCT ON (account_id)
            bs.account_id, bs.balance, bs.available, bs.in_flight_in, bs.in_flight_out, bs.time,
            a.bank_name, a.currency, a.bank_country, a.min_balance, a.max_balance
        FROM balance_snapshots bs
        JOIN accounts a ON a.id = bs.account_id
        ORDER BY account_id, time DESC
    """)
    result = await session.execute(query)
    rows = result.fetchall()
    return {
        str(row.account_id): {
            "account_id": str(row.account_id),
            "bank_name": row.bank_name,
            "currency": row.currency,
            "country": row.bank_country,
            "balance": float(row.balance),
            "available": float(row.available),
            "in_flight_in": float(row.in_flight_in),
            "in_flight_out": float(row.in_flight_out),
            "min_balance": float(row.min_balance),
            "max_balance": float(row.max_balance),
            "as_of": row.time.isoformat(),
        }
        for row in rows
    }


async def get_account_forecasts(
    session: AsyncSession,
    account_id: str,
) -> list[dict]:
    """Get stored forecasts for an account."""
    query = (
        select(Forecast)
        .where(Forecast.account_id == account_id)
        .order_by(Forecast.horizon_date)
    )
    result = await session.execute(query)
    forecasts = result.scalars().all()
    return [
        {
            "horizon_date": str(f.horizon_date),
            "predicted_net": float(f.predicted_net),
            "predicted_in": float(f.predicted_in) if f.predicted_in else None,
            "predicted_out": float(f.predicted_out) if f.predicted_out else None,
            "confidence_low": float(f.confidence_low) if f.confidence_low else None,
            "confidence_high": float(f.confidence_high) if f.confidence_high else None,
            "model_version": f.model_version,
            "features_json": f.features_json,
        }
        for f in forecasts
    ]


async def get_daily_flows(
    session: AsyncSession,
    account_id: str | None = None,
    days: int = 30,
) -> pd.DataFrame:
    """Get daily aggregated flows for charting."""
    params: dict[str, Any] = {"days": days}

    if account_id:
        conditions = "AND account_id = CAST(:account_id AS uuid)"
        params["account_id"] = account_id
    else:
        conditions = ""

    query = text(f"""
        SELECT
            date_trunc('day', time) as day,
            account_id,
            direction,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions
        WHERE time >= NOW() - make_interval(days => :days)
        {conditions}
        GROUP BY day, account_id, direction
        ORDER BY day
    """)
    result = await session.execute(query, params)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        [{"day": r.day, "account_id": str(r.account_id), "direction": r.direction,
          "total": float(r.total), "count": r.count} for r in rows]
    )
