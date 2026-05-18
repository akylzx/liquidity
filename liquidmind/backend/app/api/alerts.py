"""Alert endpoints: list alerts, acknowledge alerts."""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert

router = APIRouter()


@router.get("")
async def list_alerts(
    severity: str | None = None,
    acknowledged: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """List active alerts, optionally filtered by severity."""
    query = select(Alert).where(Alert.is_acknowledged == acknowledged)
    if severity:
        query = query.where(Alert.severity == severity)
    query = query.order_by(
        # critical first
        text("CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 WHEN 'advisory' THEN 2 ELSE 3 END"),
        Alert.created_at.desc(),
    )

    result = await session.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": str(a.id),
                "account_id": str(a.account_id) if a.account_id else None,
                "severity": a.severity,
                "alert_type": a.alert_type,
                "title": a.title,
                "description": a.description,
                "projected_impact": float(a.projected_impact) if a.projected_impact else None,
                "horizon_hours": a.horizon_hours,
                "is_acknowledged": a.is_acknowledged,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "count": len(alerts),
        "critical_count": sum(1 for a in alerts if a.severity == "critical"),
        "warning_count": sum(1 for a in alerts if a.severity == "warning"),
        "advisory_count": sum(1 for a in alerts if a.severity == "advisory"),
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert."""
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        return {"error": "Alert not found"}

    alert.is_acknowledged = True
    alert.acknowledged_by = "treasury_analyst"
    await session.commit()

    return {"id": str(alert.id), "status": "acknowledged"}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Mark an alert as resolved."""
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        return {"error": "Alert not found"}

    alert.is_acknowledged = True
    alert.resolved_at = datetime.now(timezone.utc)
    await session.commit()

    return {"id": str(alert.id), "status": "resolved"}
