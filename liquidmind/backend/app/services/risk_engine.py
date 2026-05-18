"""Risk engine: predictive alerts, stress testing, and risk scoring."""

import uuid
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Any

import numpy as np


@dataclass
class RiskAlert:
    id: str
    account_id: str
    bank_name: str
    severity: str  # critical, warning, advisory
    alert_type: str
    title: str
    description: str
    projected_impact: float
    horizon_hours: int
    created_at: str


@dataclass
class AccountRiskProfile:
    account_id: str
    bank_name: str
    currency: str
    current_balance: float
    min_balance: float
    projected_balances: list[float]  # daily for next 5 days
    forecast_std: float  # standard deviation of forecast
    concentration_pct: float  # % of total liquidity in this account
    avg_settlement_delay_hours: float
    fx_volatility: float


def generate_alerts(profiles: list[AccountRiskProfile]) -> list[RiskAlert]:
    """Generate predictive alerts based on risk profiles."""
    alerts = []

    for profile in profiles:
        # Dynamic threshold: min_balance + volatility buffer
        volatility_multiplier = 1.5
        dynamic_min = profile.min_balance + volatility_multiplier * profile.forecast_std

        for day_idx, proj_bal in enumerate(profile.projected_balances):
            hours = (day_idx + 1) * 24

            if proj_bal < profile.min_balance:
                # CRITICAL or WARNING based on time horizon
                deficit = profile.min_balance - proj_bal
                if hours <= 4:
                    severity = "critical"
                elif hours <= 24:
                    severity = "critical" if deficit > profile.min_balance * 0.2 else "warning"
                else:
                    severity = "warning"

                alerts.append(RiskAlert(
                    id=str(uuid.uuid4()),
                    account_id=profile.account_id,
                    bank_name=profile.bank_name,
                    severity=severity,
                    alert_type="balance_breach",
                    title=f"{profile.bank_name} ({profile.currency}): Balance breach in {day_idx + 1}d",
                    description=(
                        f"Projected balance of {profile.currency} {proj_bal:,.0f} will fall below "
                        f"minimum {profile.currency} {profile.min_balance:,.0f} "
                        f"by day {day_idx + 1}. Deficit: {profile.currency} {deficit:,.0f}."
                    ),
                    projected_impact=deficit,
                    horizon_hours=hours,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                break  # Only first breach per account

            elif proj_bal < dynamic_min:
                # ADVISORY
                buffer = proj_bal - profile.min_balance
                alerts.append(RiskAlert(
                    id=str(uuid.uuid4()),
                    account_id=profile.account_id,
                    bank_name=profile.bank_name,
                    severity="advisory",
                    alert_type="low_buffer",
                    title=f"{profile.bank_name} ({profile.currency}): Low buffer in {day_idx + 1}d",
                    description=(
                        f"Projected balance buffer of {profile.currency} {buffer:,.0f} "
                        f"is below safety threshold by day {day_idx + 1}."
                    ),
                    projected_impact=buffer,
                    horizon_hours=hours,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                break

        # Concentration risk alert
        if profile.concentration_pct > 0.30:
            alerts.append(RiskAlert(
                id=str(uuid.uuid4()),
                account_id=profile.account_id,
                bank_name=profile.bank_name,
                severity="advisory",
                alert_type="concentration",
                title=f"{profile.bank_name}: High concentration ({profile.concentration_pct:.0%})",
                description=(
                    f"{profile.concentration_pct:.0%} of total {profile.currency} liquidity "
                    f"is concentrated in this single account."
                ),
                projected_impact=profile.current_balance * profile.concentration_pct,
                horizon_hours=0,
                created_at=datetime.now(timezone.utc).isoformat(),
            ))

    # Sort by severity (critical first, then warning, then advisory)
    severity_order = {"critical": 0, "warning": 1, "advisory": 2}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 3), a.horizon_hours))

    return alerts


def compute_risk_score(profile: AccountRiskProfile) -> dict[str, float]:
    """Compute composite risk score for an account (0-100 scale)."""
    # Deficit probability: based on how close projected min is to min_balance
    min_proj = min(profile.projected_balances) if profile.projected_balances else profile.current_balance
    buffer_ratio = (min_proj - profile.min_balance) / profile.min_balance if profile.min_balance > 0 else 1
    deficit_prob = max(0, min(100, (1 - buffer_ratio) * 50))

    # Concentration risk (0-100)
    concentration_score = min(100, profile.concentration_pct * 200)

    # Settlement delay risk (0-100)
    delay_score = min(100, profile.avg_settlement_delay_hours / 72 * 100)

    # Currency volatility risk (0-100)
    fx_score = min(100, profile.fx_volatility * 10000)  # scale 1% vol to 100

    # Counterparty risk (simplified: based on country)
    counterparty_score = 20  # baseline low risk for developed countries

    # Composite
    composite = (
        0.30 * deficit_prob
        + 0.25 * concentration_score
        + 0.20 * delay_score
        + 0.15 * fx_score
        + 0.10 * counterparty_score
    )

    return {
        "composite": round(composite, 1),
        "deficit_probability": round(deficit_prob, 1),
        "concentration_risk": round(concentration_score, 1),
        "settlement_delay_risk": round(delay_score, 1),
        "currency_volatility_risk": round(fx_score, 1),
        "counterparty_risk": round(counterparty_score, 1),
    }


# --- Stress Testing ---

def apply_stress_scenario(
    positions: list[dict],
    forecasts: list[list[float]],
    scenario: dict,
) -> list[list[float]]:
    """Apply a stress scenario to forecasts and return stressed projections.

    Args:
        positions: list of account position dicts
        forecasts: list of forecast arrays (one per account, each with daily values)
        scenario: scenario parameters dict

    Returns:
        Stressed forecast arrays
    """
    params = scenario.get("parameters", scenario)
    scenario_type = params.get("type", "")

    stressed = [list(f) for f in forecasts]  # deep copy

    if scenario_type == "delay":
        # Delay: push inflows forward by extra_delay days
        extra_delay = params.get("extra_delay_hours", 48) // 24
        channel = params.get("channel", "swift")
        for i, acct_forecasts in enumerate(stressed):
            # Reduce near-term inflows, add them later
            for day in range(min(extra_delay, len(acct_forecasts))):
                # Assume 40% of positive flow is from the delayed channel
                if acct_forecasts[day] > 0:
                    delayed_amount = acct_forecasts[day] * 0.4
                    acct_forecasts[day] -= delayed_amount
                    # Add to a later day if within horizon
                    later_day = day + extra_delay
                    if later_day < len(acct_forecasts):
                        acct_forecasts[later_day] += delayed_amount

    elif scenario_type == "volume_spike":
        multiplier = params.get("multiplier", 1.4)
        direction = params.get("direction", "out")
        days_affected = params.get("days", 3)
        for i, acct_forecasts in enumerate(stressed):
            for day in range(min(days_affected, len(acct_forecasts))):
                if direction == "out":
                    # Increase outflows (make net flow more negative)
                    if acct_forecasts[day] < 0:
                        acct_forecasts[day] *= multiplier
                    else:
                        acct_forecasts[day] -= abs(acct_forecasts[day]) * (multiplier - 1)
                else:
                    if acct_forecasts[day] > 0:
                        acct_forecasts[day] *= multiplier

    elif scenario_type == "fx_shock":
        shock_pct = params.get("shock_pct", -0.05)
        # FX shock affects the value of non-USD accounts
        for i, acct_forecasts in enumerate(stressed):
            if positions[i].get("currency") != "USD":
                for day in range(len(acct_forecasts)):
                    acct_forecasts[day] *= (1 + shock_pct)

    elif scenario_type == "account_freeze":
        acct_index = params.get("account_index", 0)
        freeze_days = params.get("freeze_days", 3)
        if acct_index < len(stressed):
            for day in range(min(freeze_days, len(stressed[acct_index]))):
                # Zero out all flows — account is frozen
                stressed[acct_index][day] = 0

    return stressed


def run_stress_test(
    positions: list[dict],
    baseline_forecasts: list[list[float]],
    scenario: dict,
) -> dict[str, Any]:
    """Run a full stress test and compute impact summary."""
    stressed_forecasts = apply_stress_scenario(positions, baseline_forecasts, scenario)

    # Compute baseline vs stressed balance projections
    baseline_results = []
    stressed_results = []

    for i, pos in enumerate(positions):
        bal = pos["current_balance"]
        min_bal = pos["min_balance"]

        # Baseline trajectory
        base_trajectory = [bal]
        for flow in baseline_forecasts[i]:
            base_trajectory.append(base_trajectory[-1] + flow)
        baseline_results.append({
            "account_id": pos["account_id"],
            "bank_name": pos["bank_name"],
            "currency": pos["currency"],
            "trajectory": [round(b, 2) for b in base_trajectory],
            "min_balance_threshold": min_bal,
            "breaches_threshold": any(b < min_bal for b in base_trajectory),
        })

        # Stressed trajectory
        stress_trajectory = [bal]
        for flow in stressed_forecasts[i]:
            stress_trajectory.append(stress_trajectory[-1] + flow)
        stressed_results.append({
            "account_id": pos["account_id"],
            "bank_name": pos["bank_name"],
            "currency": pos["currency"],
            "trajectory": [round(b, 2) for b in stress_trajectory],
            "min_balance_threshold": min_bal,
            "breaches_threshold": any(b < min_bal for b in stress_trajectory),
        })

    # Impact summary
    baseline_breaches = sum(1 for r in baseline_results if r["breaches_threshold"])
    stressed_breaches = sum(1 for r in stressed_results if r["breaches_threshold"])

    baseline_min_total = sum(min(r["trajectory"]) for r in baseline_results)
    stressed_min_total = sum(min(r["trajectory"]) for r in stressed_results)

    return {
        "scenario": scenario.get("name", "Unknown"),
        "baseline": baseline_results,
        "stressed": stressed_results,
        "impact_summary": {
            "baseline_threshold_breaches": baseline_breaches,
            "stressed_threshold_breaches": stressed_breaches,
            "additional_breaches": stressed_breaches - baseline_breaches,
            "baseline_min_total_balance": round(baseline_min_total, 2),
            "stressed_min_total_balance": round(stressed_min_total, 2),
            "total_balance_impact": round(stressed_min_total - baseline_min_total, 2),
        },
    }
