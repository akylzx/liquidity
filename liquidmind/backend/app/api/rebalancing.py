"""Rebalancing endpoints: get recommendations, approve transfers."""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rebalance import RebalanceRecommendation
from app.models.account import Account
from app.services.rebalance_optimizer import (
    AccountPosition, Corridor as CorridorData, greedy_rebalance, compute_savings_metrics,
)
from app.services.forecast_engine import get_latest_balances

router = APIRouter()


@router.get("/recommendations")
async def get_recommendations(session: AsyncSession = Depends(get_db)):
    """Get current rebalancing recommendations."""
    # Get latest batch of recommendations
    query = text("""
        SELECT
            r.*,
            s.bank_name as source_bank,
            t.bank_name as target_bank,
            s.currency
        FROM rebalance_recommendations r
        JOIN accounts s ON s.id = r.source_id
        JOIN accounts t ON t.id = r.target_id
        WHERE r.status = 'pending'
        ORDER BY
            CASE r.urgency
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            r.created_at DESC
    """)
    result = await session.execute(query)
    rows = result.fetchall()

    items = []
    for row in rows:
        items.append({
            "id": str(row.id),
            "source_id": str(row.source_id),
            "source_bank": row.source_bank,
            "target_id": str(row.target_id),
            "target_bank": row.target_bank,
            "amount": float(row.amount),
            "currency": row.currency,
            "urgency": row.urgency,
            "reason": row.reason,
            "estimated_cost": float(row.estimated_cost) if row.estimated_cost else 0,
            "estimated_arrival": row.estimated_arrival.isoformat() if row.estimated_arrival else None,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        })

    return {"recommendations": items, "count": len(items)}


@router.post("/approve/{recommendation_id}")
async def approve_recommendation(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Approve a rebalancing recommendation for execution."""
    result = await session.execute(
        select(RebalanceRecommendation).where(RebalanceRecommendation.id == recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return {"error": "Recommendation not found"}

    rec.status = "approved"
    rec.approved_by = "treasury_analyst"
    rec.approved_at = datetime.now(timezone.utc)
    await session.commit()

    return {
        "id": str(rec.id),
        "status": "approved",
        "message": f"Transfer of {rec.currency} {float(rec.amount):,.2f} approved for execution.",
    }


@router.post("/reject/{recommendation_id}")
async def reject_recommendation(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Reject a rebalancing recommendation."""
    result = await session.execute(
        select(RebalanceRecommendation).where(RebalanceRecommendation.id == recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return {"error": "Recommendation not found"}

    rec.status = "rejected"
    await session.commit()

    return {"id": str(rec.id), "status": "rejected"}


@router.get("/savings")
async def get_savings_metrics(session: AsyncSession = Depends(get_db)):
    """Get projected savings from the rebalancing system."""
    # This returns demo metrics based on approved recommendations
    query = text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
            SUM(amount) FILTER (WHERE status = 'approved') as total_transferred,
            SUM(estimated_cost) FILTER (WHERE status = 'approved') as total_cost,
            COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
            COUNT(*) as total_count
        FROM rebalance_recommendations
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """)
    result = await session.execute(query)
    row = result.fetchone()

    total_transferred = float(row.total_transferred) if row.total_transferred else 0
    total_cost = float(row.total_cost) if row.total_cost else 0

    # Estimated metrics
    avoided_overdraft = total_transferred * 0.08 / 365 * 5  # 8% rate, 5-day window
    freed_capital_return = total_transferred * 0.04 / 365 * 30  # 4% rate, 30 days

    return {
        "period": "last_30_days",
        "approved_transfers": row.approved_count or 0,
        "pending_transfers": row.pending_count or 0,
        "total_transferred": round(total_transferred, 2),
        "total_cost": round(total_cost, 2),
        "avoided_overdraft_cost": round(avoided_overdraft, 2),
        "freed_capital_monthly_return": round(freed_capital_return, 2),
        "net_monthly_benefit": round(freed_capital_return + avoided_overdraft - total_cost, 2),
        "idle_capital_reduced": round(total_transferred * 0.6, 2),  # estimate
    }
