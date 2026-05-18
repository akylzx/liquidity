"""Stress testing endpoints: list scenarios, run stress test."""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stress import StressScenario, StressResult
from app.services.forecast_engine import get_latest_balances
from app.services.risk_engine import run_stress_test

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios(session: AsyncSession = Depends(get_db)):
    """List all available stress test scenarios."""
    result = await session.execute(
        select(StressScenario).order_by(StressScenario.is_predefined.desc())
    )
    scenarios = result.scalars().all()

    return {
        "scenarios": [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
                "is_predefined": s.is_predefined,
            }
            for s in scenarios
        ]
    }


@router.post("/run/{scenario_id}")
async def run_scenario(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Run a stress test scenario and return results."""
    # Load scenario
    result = await session.execute(
        select(StressScenario).where(StressScenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        return {"error": "Scenario not found"}

    # Get current positions and map field names for the risk engine
    balances = await get_latest_balances(session)
    positions = [
        {
            "account_id": v["account_id"],
            "bank_name": v["bank_name"],
            "currency": v["currency"],
            "current_balance": v["balance"],
            "min_balance": v["min_balance"],
        }
        for v in balances.values()
    ]

    # Generate baseline forecasts (use stored or simple projection)
    baseline_forecasts = []
    for pos in positions:
        avg_daily_net = (pos["current_balance"] - pos["min_balance"]) * 0.01
        baseline = [avg_daily_net * (0.8 + 0.4 * (i % 3) / 3) for i in range(5)]
        if pos["current_balance"] < pos["min_balance"] * 1.5:
            baseline = [-abs(avg_daily_net) * 1.5 for _ in range(5)]
        baseline_forecasts.append(baseline)

    # Run stress test
    stress_result = run_stress_test(
        positions,
        baseline_forecasts,
        {"name": scenario.name, "parameters": scenario.parameters},
    )

    # Store result
    sr = StressResult(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        baseline_json={"positions": stress_result["baseline"]},
        stressed_json={"positions": stress_result["stressed"]},
        impact_summary=stress_result["impact_summary"],
    )
    session.add(sr)
    await session.commit()

    return stress_result


@router.get("/results/{scenario_id}")
async def get_scenario_results(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Get historical results for a scenario."""
    result = await session.execute(
        select(StressResult)
        .where(StressResult.scenario_id == scenario_id)
        .order_by(StressResult.run_at.desc())
        .limit(10)
    )
    results = result.scalars().all()

    return {
        "results": [
            {
                "id": str(r.id),
                "run_at": r.run_at.isoformat(),
                "impact_summary": r.impact_summary,
            }
            for r in results
        ]
    }
