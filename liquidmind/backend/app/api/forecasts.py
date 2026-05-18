"""Forecast endpoints: get forecasts per account, aggregate forecasts."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.forecast import Forecast
from app.services.forecast_engine import get_account_forecasts, get_daily_flows

router = APIRouter()


@router.get("/account/{account_id}")
async def get_forecast(
    account_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Get cash flow forecast for a specific account."""
    forecasts = await get_account_forecasts(session, str(account_id))

    # Also get recent historical flows for context
    query = text("""
        SELECT
            date_trunc('day', time) as day,
            direction,
            channel,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions
        WHERE account_id = :account_id
          AND time >= NOW() - INTERVAL '30 days'
        GROUP BY day, direction, channel
        ORDER BY day
    """)
    result = await session.execute(query, {"account_id": str(account_id)})
    rows = result.fetchall()

    historical = {}
    for row in rows:
        day_str = row.day.isoformat()
        if day_str not in historical:
            historical[day_str] = {"date": day_str, "inflows": {}, "outflows": {}}
        bucket = "inflows" if row.direction == "in" else "outflows"
        historical[day_str][bucket][row.channel] = {
            "total": round(float(row.total), 2),
            "count": row.count,
        }

    return {
        "account_id": str(account_id),
        "forecasts": forecasts,
        "historical_30d": list(historical.values()),
    }


@router.get("/aggregate")
async def get_aggregate_forecast(session: AsyncSession = Depends(get_db)):
    """Get aggregated forecast across all accounts, grouped by currency."""
    query = text("""
        SELECT
            f.currency,
            f.horizon_date,
            SUM(f.predicted_net) as total_predicted_net,
            SUM(f.confidence_low) as total_confidence_low,
            SUM(f.confidence_high) as total_confidence_high
        FROM forecasts f
        GROUP BY f.currency, f.horizon_date
        ORDER BY f.currency, f.horizon_date
    """)
    result = await session.execute(query)
    rows = result.fetchall()

    by_currency = {}
    for row in rows:
        ccy = row.currency
        if ccy not in by_currency:
            by_currency[ccy] = []
        by_currency[ccy].append({
            "date": row.horizon_date.isoformat(),
            "predicted_net": round(float(row.total_predicted_net), 2),
            "confidence_low": round(float(row.total_confidence_low), 2) if row.total_confidence_low else None,
            "confidence_high": round(float(row.total_confidence_high), 2) if row.total_confidence_high else None,
        })

    return {"forecasts_by_currency": by_currency}


@router.get("/accuracy")
async def get_forecast_accuracy(session: AsyncSession = Depends(get_db)):
    """Get forecast accuracy metrics (MAPE, directional accuracy)."""
    # Compare forecasts with actual flows for dates that have passed
    query = text("""
        WITH actuals AS (
            SELECT
                account_id,
                date_trunc('day', time)::date as day,
                SUM(CASE WHEN direction = 'in' THEN amount ELSE -amount END) as actual_net
            FROM transactions
            WHERE time >= NOW() - INTERVAL '30 days'
            GROUP BY account_id, day
        ),
        forecast_vs_actual AS (
            SELECT
                f.account_id,
                f.horizon_date,
                f.predicted_net,
                a.actual_net,
                ABS(f.predicted_net - a.actual_net) as absolute_error,
                CASE WHEN SIGN(f.predicted_net) = SIGN(a.actual_net) THEN 1 ELSE 0 END as direction_correct
            FROM forecasts f
            JOIN actuals a ON f.account_id = a.account_id AND f.horizon_date = a.day
        )
        SELECT
            COUNT(*) as sample_count,
            AVG(absolute_error) as mae,
            AVG(direction_correct) as directional_accuracy
        FROM forecast_vs_actual
    """)
    result = await session.execute(query)
    row = result.fetchone()

    if row and row.sample_count > 0:
        return {
            "sample_count": row.sample_count,
            "mae": round(float(row.mae), 2),
            "directional_accuracy": round(float(row.directional_accuracy), 4),
        }
    return {"sample_count": 0, "mae": None, "directional_accuracy": None}
