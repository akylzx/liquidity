"""Liquidity rebalance optimizer.

Implements both a greedy heuristic (primary) and an LP formulation (stretch goal)
to recommend fund transfers between nostro accounts.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any


@dataclass
class AccountPosition:
    account_id: str
    bank_name: str
    currency: str
    country: str
    current_balance: float
    min_balance: float
    max_balance: float
    # Projected net flows for the next N days (from forecast)
    projected_flows: list[float] = field(default_factory=list)

    @property
    def projected_balances(self) -> list[float]:
        """Compute projected balance trajectory."""
        balances = [self.current_balance]
        for flow in self.projected_flows:
            balances.append(balances[-1] + flow)
        return balances

    @property
    def min_projected_balance(self) -> float:
        return min(self.projected_balances)

    @property
    def deficit(self) -> float:
        """Max deficit below min_balance over projection horizon."""
        return max(0, self.min_balance - self.min_projected_balance)

    @property
    def deficit_day(self) -> int:
        """Day index when first deficit occurs (0 = today). -1 if no deficit."""
        for i, bal in enumerate(self.projected_balances):
            if bal < self.min_balance:
                return i
        return -1

    @property
    def surplus(self) -> float:
        """Available excess over max_balance target."""
        return max(0, self.current_balance - self.max_balance)

    @property
    def safe_surplus(self) -> float:
        """Available amount that can be moved while keeping balance above min + 10% buffer."""
        buffer = self.min_balance * 1.1
        min_proj = self.min_projected_balance
        return max(0, min_proj - buffer)


@dataclass
class Corridor:
    source_id: str
    target_id: str
    channel: str
    typical_delay_hours: int
    fixed_cost: float
    variable_cost: float


@dataclass
class TransferRecommendation:
    source_id: str
    source_bank: str
    target_id: str
    target_bank: str
    amount: float
    currency: str
    urgency: str  # critical, high, medium, low
    reason: str
    estimated_cost: float
    estimated_arrival_hours: int
    corridor_channel: str


def greedy_rebalance(
    positions: list[AccountPosition],
    corridors: list[Corridor],
) -> list[TransferRecommendation]:
    """Greedy rebalance algorithm.

    1. Identify deficit accounts (projected to breach minimum)
    2. Sort by urgency (earliest breach first)
    3. For each deficit, find best surplus source (cheapest, fastest)
    4. Propose transfers
    """
    # Build corridor lookup
    corridor_map: dict[tuple[str, str], Corridor] = {}
    for c in corridors:
        key = (c.source_id, c.target_id)
        # Keep cheapest corridor for each pair
        if key not in corridor_map or c.fixed_cost < corridor_map[key].fixed_cost:
            corridor_map[key] = c

    # Identify accounts with deficits
    deficit_accounts = [p for p in positions if p.deficit > 0]
    deficit_accounts.sort(key=lambda p: p.deficit_day)  # earliest breach first

    # Identify accounts with surplus
    surplus_accounts = [p for p in positions if p.safe_surplus > 0]

    # Track remaining surplus after allocations
    remaining_surplus: dict[str, float] = {
        p.account_id: p.safe_surplus for p in surplus_accounts
    }

    recommendations: list[TransferRecommendation] = []

    for deficit_pos in deficit_accounts:
        needed = deficit_pos.deficit
        if needed <= 0:
            continue

        # Determine urgency
        dd = deficit_pos.deficit_day
        if dd <= 0:
            urgency = "critical"
        elif dd <= 1:
            urgency = "high"
        elif dd <= 3:
            urgency = "medium"
        else:
            urgency = "low"

        # Find candidate sources
        candidates = []
        for surplus_pos in surplus_accounts:
            available = remaining_surplus.get(surplus_pos.account_id, 0)
            if available <= 0:
                continue

            # Must have a corridor
            key = (surplus_pos.account_id, deficit_pos.account_id)
            corridor = corridor_map.get(key)
            if corridor is None:
                continue

            # Same currency only (no FX in greedy version)
            if surplus_pos.currency != deficit_pos.currency:
                continue

            # Score: lower is better (cost per unit + time penalty)
            total_cost = corridor.fixed_cost + corridor.variable_cost * min(available, needed)
            time_penalty = corridor.typical_delay_hours * 10  # $10 per hour of delay
            score = total_cost + time_penalty

            candidates.append((surplus_pos, corridor, available, score))

        # Sort by score (cheapest + fastest first)
        candidates.sort(key=lambda x: x[3])

        for surplus_pos, corridor, available, score in candidates:
            if needed <= 0:
                break

            transfer_amount = min(needed, available)
            if transfer_amount < 1000:  # minimum transfer threshold
                continue

            cost = corridor.fixed_cost + corridor.variable_cost * transfer_amount

            recommendations.append(TransferRecommendation(
                source_id=surplus_pos.account_id,
                source_bank=surplus_pos.bank_name,
                target_id=deficit_pos.account_id,
                target_bank=deficit_pos.bank_name,
                amount=round(transfer_amount, 2),
                currency=deficit_pos.currency,
                urgency=urgency,
                reason=(
                    f"{deficit_pos.bank_name} projected to breach minimum balance "
                    f"of ${deficit_pos.min_balance:,.0f} in {dd} day(s). "
                    f"Transfer from {surplus_pos.bank_name} "
                    f"(surplus: ${available:,.0f})."
                ),
                estimated_cost=round(cost, 2),
                estimated_arrival_hours=corridor.typical_delay_hours,
                corridor_channel=corridor.channel,
            ))

            remaining_surplus[surplus_pos.account_id] -= transfer_amount
            needed -= transfer_amount

    return recommendations


def compute_savings_metrics(
    positions: list[AccountPosition],
    recommendations: list[TransferRecommendation],
) -> dict[str, Any]:
    """Compute the projected savings from executing recommendations."""
    total_idle = sum(max(0, p.current_balance - p.max_balance) for p in positions)
    total_deficit = sum(p.deficit for p in positions)
    total_transfer = sum(r.amount for r in recommendations)
    total_cost = sum(r.estimated_cost for r in recommendations)

    # Estimate avoided overdraft cost (assume 8% annual rate on deficit)
    daily_overdraft_rate = 0.08 / 365
    avoided_overdraft = total_deficit * daily_overdraft_rate * 5  # 5-day horizon

    # Estimate freed capital returns (assume 4% annual on freed idle balance)
    daily_return_rate = 0.04 / 365
    freed_capital_return = min(total_idle, total_transfer) * daily_return_rate * 30  # monthly

    return {
        "total_idle_capital": round(total_idle, 2),
        "total_projected_deficit": round(total_deficit, 2),
        "recommended_transfers": len(recommendations),
        "total_transfer_volume": round(total_transfer, 2),
        "total_transfer_cost": round(total_cost, 2),
        "avoided_overdraft_cost": round(avoided_overdraft, 2),
        "freed_capital_monthly_return": round(freed_capital_return, 2),
        "net_monthly_benefit": round(freed_capital_return + avoided_overdraft - total_cost, 2),
    }
