"""Synthetic data generator for LiquidMind demo.

Generates 12 months of realistic transaction, balance, and FX data
with embedded patterns that demonstrate the system's predictive value.
"""

import uuid
from datetime import datetime, timedelta, date, timezone
from typing import Any

import numpy as np
import pandas as pd

# --- Account definitions ---

ACCOUNTS = [
    {"bank_name": "Deutsche Bank", "bank_country": "DE", "currency": "EUR", "min_balance": 2_000_000, "max_balance": 8_000_000, "account_type": "nostro"},
    {"bank_name": "Societe Generale", "bank_country": "FR", "currency": "EUR", "min_balance": 1_500_000, "max_balance": 6_000_000, "account_type": "nostro"},
    {"bank_name": "JPMorgan Chase", "bank_country": "US", "currency": "USD", "min_balance": 3_000_000, "max_balance": 10_000_000, "account_type": "nostro"},
    {"bank_name": "Bank of America", "bank_country": "US", "currency": "USD", "min_balance": 2_000_000, "max_balance": 7_000_000, "account_type": "nostro"},
    {"bank_name": "Barclays", "bank_country": "GB", "currency": "GBP", "min_balance": 1_000_000, "max_balance": 5_000_000, "account_type": "nostro"},
    {"bank_name": "UBS", "bank_country": "CH", "currency": "CHF", "min_balance": 800_000, "max_balance": 3_000_000, "account_type": "nostro"},
    {"bank_name": "PKO BP", "bank_country": "PL", "currency": "PLN", "min_balance": 500_000, "max_balance": 2_000_000, "account_type": "correspondent"},
    {"bank_name": "HSBC", "bank_country": "GB", "currency": "EUR", "min_balance": 1_000_000, "max_balance": 4_000_000, "account_type": "nostro"},
]

CHANNELS = ["p2p", "card", "sepa", "swift", "partner"]

CHANNEL_DELAYS = {
    "p2p": (0, 0),        # instant
    "card": (24, 120),     # 1-5 days
    "sepa": (4, 24),       # 4h to 1 day
    "swift": (48, 72),     # 2-3 days
    "partner": (24, 48),   # 1-2 days
}

# Channel volume weights (relative probability of each channel)
CHANNEL_WEIGHTS = {"p2p": 0.30, "card": 0.35, "sepa": 0.15, "swift": 0.10, "partner": 0.10}

# Base FX rates (vs USD)
BASE_FX = {"EUR": 1.08, "GBP": 1.27, "CHF": 0.88, "PLN": 0.25, "USD": 1.0}

# Major holidays by country (month, day)
HOLIDAYS = {
    "DE": [(1, 1), (4, 7), (4, 10), (5, 1), (5, 18), (5, 29), (10, 3), (12, 25), (12, 26)],
    "FR": [(1, 1), (4, 10), (5, 1), (5, 8), (5, 18), (5, 29), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)],
    "US": [(1, 1), (1, 16), (2, 20), (5, 29), (6, 19), (7, 4), (9, 4), (10, 9), (11, 10), (11, 23), (12, 25)],
    "GB": [(1, 2), (4, 7), (4, 10), (5, 1), (5, 29), (8, 28), (12, 25), (12, 26)],
    "CH": [(1, 1), (1, 2), (4, 7), (4, 10), (5, 18), (5, 29), (8, 1), (12, 25), (12, 26)],
    "PL": [(1, 1), (1, 6), (4, 9), (4, 10), (5, 1), (5, 3), (5, 28), (6, 8), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)],
}


def is_holiday(d: date, country: str) -> bool:
    holidays = HOLIDAYS.get(country, [])
    return (d.month, d.day) in holidays


def is_business_day(d: date, country: str) -> bool:
    if d.weekday() >= 5:
        return False
    return not is_holiday(d, country)


class SyntheticDataGenerator:
    def __init__(self, seed: int = 42, days: int = 365):
        self.rng = np.random.default_rng(seed)
        self.days = days
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=days)
        self.account_ids = {i: uuid.uuid4() for i in range(len(ACCOUNTS))}

    def generate_accounts(self) -> list[dict[str, Any]]:
        results = []
        for i, acct in enumerate(ACCOUNTS):
            results.append({
                "id": self.account_ids[i],
                **acct,
                "overdraft_limit": acct["min_balance"] * 0.5,
                "transfer_cost": round(self.rng.uniform(5, 25), 2),
                "is_active": True,
            })
        return results

    def generate_holidays(self) -> list[dict[str, Any]]:
        results = []
        for year in range(self.start_date.year, self.end_date.year + 1):
            for country, days_list in HOLIDAYS.items():
                for month, day in days_list:
                    try:
                        d = date(year, month, day)
                    except ValueError:
                        continue
                    if self.start_date <= d <= self.end_date:
                        results.append({
                            "date": d,
                            "country": country,
                            "name": f"Holiday {country}",
                            "affects_sepa": country in ("DE", "FR"),
                            "affects_swift": True,
                            "affects_cards": True,
                        })
        return results

    def _daily_volume_multiplier(self, d: date) -> float:
        """Compute a multiplier for daily transaction volume based on patterns."""
        mult = 1.0

        # Day of week: Mon-Thu normal, Fri slightly higher, Sat/Sun much lower
        dow = d.weekday()
        if dow == 4:
            mult *= 1.15  # Friday
        elif dow == 5:
            mult *= 0.3   # Saturday
        elif dow == 6:
            mult *= 0.2   # Sunday

        # Month-end salary spike (25th-28th)
        if 25 <= d.day <= 28:
            mult *= 1.6

        # Quarter-end surge
        if d.month in (3, 6, 9, 12) and d.day >= 28:
            mult *= 1.3

        # Seasonal e-commerce (Nov-Dec)
        if d.month in (11, 12):
            mult *= 1.30

        # January dip
        if d.month == 1 and d.day <= 10:
            mult *= 0.7

        # Growth trend: +2% per month from start
        months_elapsed = (d.year - self.start_date.year) * 12 + (d.month - self.start_date.month)
        mult *= (1.02 ** months_elapsed)

        return mult

    def _channel_amount_distribution(self, channel: str) -> tuple[float, float]:
        """Return (mean, std) of transaction amounts for a channel."""
        distributions = {
            "p2p": (150, 200),
            "card": (80, 120),
            "sepa": (5000, 8000),
            "swift": (50000, 80000),
            "partner": (25000, 40000),
        }
        return distributions[channel]

    def generate_transactions(self) -> pd.DataFrame:
        """Generate transactions with realistic patterns (~500/day for demo)."""
        records = []
        base_daily_count = 500

        current = self.start_date
        while current <= self.end_date:
            mult = self._daily_volume_multiplier(current)
            daily_count = int(base_daily_count * mult)

            # Distribute across accounts proportionally to max_balance
            total_capacity = sum(a["max_balance"] for a in ACCOUNTS)

            for acct_idx, acct in enumerate(ACCOUNTS):
                acct_share = acct["max_balance"] / total_capacity
                acct_count = max(1, int(daily_count * acct_share))

                # Reduce volume on holidays for this account's country
                if is_holiday(current, acct["bank_country"]):
                    acct_count = int(acct_count * 0.1)

                for _ in range(acct_count):
                    channel = self.rng.choice(
                        list(CHANNEL_WEIGHTS.keys()),
                        p=list(CHANNEL_WEIGHTS.values()),
                    )
                    direction = self.rng.choice(["in", "out"], p=[0.48, 0.52])

                    mean_amt, std_amt = self._channel_amount_distribution(channel)
                    amount = max(1.0, self.rng.normal(mean_amt, std_amt))
                    amount = round(amount, 2)

                    # Time within the day (business hours weighted)
                    hour = int(self.rng.triangular(6, 14, 22))
                    minute = self.rng.integers(0, 60)
                    txn_time = datetime(
                        current.year, current.month, current.day,
                        min(hour, 23), minute, 0,
                        tzinfo=timezone.utc,
                    )

                    # Settlement delay
                    min_delay, max_delay = CHANNEL_DELAYS[channel]
                    delay_hours = self.rng.uniform(min_delay, max_delay)
                    settle_time = txn_time + timedelta(hours=delay_hours)

                    # If settlement lands on a weekend/holiday, push to next business day
                    settle_date = settle_time.date()
                    while not is_business_day(settle_date, acct["bank_country"]):
                        settle_date += timedelta(days=1)
                    settle_time = datetime(
                        settle_date.year, settle_date.month, settle_date.day,
                        settle_time.hour, settle_time.minute, 0,
                        tzinfo=timezone.utc,
                    )

                    records.append({
                        "id": uuid.uuid4(),
                        "time": txn_time,
                        "account_id": self.account_ids[acct_idx],
                        "direction": direction,
                        "amount": amount,
                        "currency": acct["currency"],
                        "channel": channel,
                        "status": "settled",
                        "counterparty": f"CP-{self.rng.integers(1000, 9999)}",
                        "reference": f"REF-{self.rng.integers(100000, 999999)}",
                        "initiated_at": txn_time,
                        "expected_settle": settle_time,
                        "settled_at": settle_time,
                    })

            current += timedelta(days=1)

        # Inject anomalies: 5 random days with 2x volume spike
        anomaly_days = self.rng.choice(
            pd.date_range(self.start_date + timedelta(days=30), self.end_date - timedelta(days=30)),
            size=5,
            replace=False,
        )
        for aday in anomaly_days:
            aday_date = pd.Timestamp(aday).date()
            spike_count = int(base_daily_count * 0.5)  # add 50% extra
            acct_idx = self.rng.integers(0, len(ACCOUNTS))
            acct = ACCOUNTS[acct_idx]
            for _ in range(spike_count):
                channel = "p2p"
                direction = "out"
                amount = round(max(1, self.rng.normal(200, 150)), 2)
                hour = int(self.rng.triangular(10, 15, 20))
                txn_time = datetime(
                    aday_date.year, aday_date.month, aday_date.day,
                    min(hour, 23), self.rng.integers(0, 60), 0,
                    tzinfo=timezone.utc,
                )
                records.append({
                    "id": uuid.uuid4(),
                    "time": txn_time,
                    "account_id": self.account_ids[acct_idx],
                    "direction": direction,
                    "amount": amount,
                    "currency": acct["currency"],
                    "channel": channel,
                    "status": "settled",
                    "counterparty": f"SPIKE-{self.rng.integers(1000, 9999)}",
                    "reference": f"SPIKE-{self.rng.integers(100000, 999999)}",
                    "initiated_at": txn_time,
                    "expected_settle": txn_time,
                    "settled_at": txn_time,
                })

        df = pd.DataFrame(records)
        df = df.sort_values("time").reset_index(drop=True)
        return df

    def generate_balance_snapshots(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Compute balance snapshots from transactions — one per day per account."""
        # Starting balances: midpoint of min/max
        starting_balances = {}
        for i, acct in enumerate(ACCOUNTS):
            starting_balances[self.account_ids[i]] = (acct["min_balance"] + acct["max_balance"]) / 2

        # Pre-compute daily aggregates for efficiency
        df = transactions_df.copy()
        df["date"] = df["time"].dt.date
        df["settle_date"] = df["expected_settle"].dt.date

        # Group by date, account, direction for net flows
        daily_flows = df.groupby(["date", "account_id", "direction"])["amount"].sum().reset_index()

        records = []
        current = self.start_date
        balances = dict(starting_balances)

        while current <= self.end_date:
            for acct_idx, acct in enumerate(ACCOUNTS):
                aid = self.account_ids[acct_idx]

                # Get inflows/outflows for this day and account
                day_acct = daily_flows[
                    (daily_flows["date"] == current) & (daily_flows["account_id"] == aid)
                ]
                inflows = day_acct[day_acct["direction"] == "in"]["amount"].sum()
                outflows = day_acct[day_acct["direction"] == "out"]["amount"].sum()
                net = inflows - outflows
                balances[aid] = balances[aid] + net

                # Compute in-flight (initiated today but settling later)
                day_acct_txns = df[(df["date"] == current) & (df["account_id"] == aid)]
                pending_in = day_acct_txns[
                    (day_acct_txns["direction"] == "in")
                    & (day_acct_txns["settle_date"] > current)
                ]["amount"].sum()
                pending_out = day_acct_txns[
                    (day_acct_txns["direction"] == "out")
                    & (day_acct_txns["settle_date"] > current)
                ]["amount"].sum()

                snapshot_time = datetime(
                    current.year, current.month, current.day, 23, 59, 0,
                    tzinfo=timezone.utc,
                )
                records.append({
                    "id": uuid.uuid4(),
                    "time": snapshot_time,
                    "account_id": aid,
                    "balance": round(balances[aid], 2),
                    "available": round(balances[aid] - pending_out, 2),
                    "in_flight_in": round(pending_in, 2),
                    "in_flight_out": round(pending_out, 2),
                    "source": "synthetic",
                })

            current += timedelta(days=1)

        return pd.DataFrame(records)

    def generate_fx_rates(self) -> pd.DataFrame:
        """Generate daily FX rates with random walk and realistic volatility."""
        records = []
        currencies = ["EUR", "GBP", "CHF", "PLN"]
        rates = dict(BASE_FX)

        current = self.start_date
        while current <= self.end_date:
            for ccy in currencies:
                # Random walk with mean reversion
                shock = self.rng.normal(0, rates[ccy] * 0.003)  # 0.3% daily vol
                mean_revert = (BASE_FX[ccy] - rates[ccy]) * 0.02  # 2% mean reversion
                rates[ccy] = rates[ccy] + shock + mean_revert
                rates[ccy] = max(BASE_FX[ccy] * 0.8, min(BASE_FX[ccy] * 1.2, rates[ccy]))

                rate_time = datetime(
                    current.year, current.month, current.day, 12, 0, 0,
                    tzinfo=timezone.utc,
                )
                records.append({
                    "id": uuid.uuid4(),
                    "time": rate_time,
                    "base_currency": ccy,
                    "quote_currency": "USD",
                    "rate": round(rates[ccy], 6),
                    "source": "synthetic",
                })

            current += timedelta(days=1)

        return pd.DataFrame(records)

    def generate_corridors(self) -> list[dict[str, Any]]:
        """Generate transfer corridors between accounts."""
        corridors = []
        for i in range(len(ACCOUNTS)):
            for j in range(len(ACCOUNTS)):
                if i == j:
                    continue
                src = ACCOUNTS[i]
                tgt = ACCOUNTS[j]

                # Determine channel based on countries/currencies
                if src["currency"] == tgt["currency"] and src["bank_country"] == tgt["bank_country"]:
                    channel = "internal"
                    delay_h, max_delay_h = 1, 4
                    cost = 0
                elif src["currency"] == "EUR" and tgt["currency"] == "EUR":
                    channel = "sepa"
                    delay_h, max_delay_h = 4, 24
                    cost = 0.20
                else:
                    channel = "swift"
                    delay_h, max_delay_h = 48, 72
                    cost = 25.0

                corridors.append({
                    "id": uuid.uuid4(),
                    "source_id": self.account_ids[i],
                    "target_id": self.account_ids[j],
                    "channel": channel,
                    "typical_delay_hours": delay_h,
                    "max_delay_hours": max_delay_h,
                    "fixed_cost": cost,
                    "variable_cost": 0.0001,
                    "cutoff_hour": 14,
                    "max_amount": min(src["max_balance"], tgt["max_balance"]),
                    "is_active": True,
                })
        return corridors

    def generate_stress_scenarios(self) -> list[dict[str, Any]]:
        """Generate predefined stress test scenarios."""
        return [
            {
                "id": uuid.uuid4(),
                "name": "SWIFT Blackout",
                "description": "All SWIFT transfers delayed by additional 2 days",
                "parameters": {"type": "delay", "channel": "swift", "extra_delay_hours": 48},
                "is_predefined": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "Month-End Surge",
                "description": "Outflow volume increases by 40% for last 3 business days of month",
                "parameters": {"type": "volume_spike", "direction": "out", "multiplier": 1.4, "days": 3},
                "is_predefined": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "FX Shock",
                "description": "EUR/USD drops 5% overnight",
                "parameters": {"type": "fx_shock", "pair": "EUR/USD", "shock_pct": -0.05},
                "is_predefined": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "Correspondent Bank Failure",
                "description": "One nostro account becomes inaccessible for 3 days",
                "parameters": {"type": "account_freeze", "account_index": 0, "freeze_days": 3},
                "is_predefined": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "P2P Volume Spike",
                "description": "P2P transfer volume doubles due to viral campaign",
                "parameters": {"type": "volume_spike", "channel": "p2p", "multiplier": 2.0, "days": 5},
                "is_predefined": True,
            },
        ]

    def generate_all(self) -> dict[str, Any]:
        """Generate all synthetic data. Returns dict of DataFrames/lists."""
        print("Generating accounts...")
        accounts = self.generate_accounts()

        print("Generating holidays...")
        holidays = self.generate_holidays()

        print("Generating transactions (this may take a moment)...")
        transactions_df = self.generate_transactions()
        print(f"  Generated {len(transactions_df):,} transactions")

        print("Generating balance snapshots...")
        balances_df = self.generate_balance_snapshots(transactions_df)

        print("Generating FX rates...")
        fx_df = self.generate_fx_rates()

        print("Generating corridors...")
        corridors = self.generate_corridors()

        print("Generating stress scenarios...")
        scenarios = self.generate_stress_scenarios()

        return {
            "accounts": accounts,
            "holidays": holidays,
            "transactions": transactions_df,
            "balance_snapshots": balances_df,
            "fx_rates": fx_df,
            "corridors": corridors,
            "stress_scenarios": scenarios,
        }


if __name__ == "__main__":
    gen = SyntheticDataGenerator(seed=42, days=365)
    data = gen.generate_all()
    print(f"\nSummary:")
    print(f"  Accounts: {len(data['accounts'])}")
    print(f"  Holidays: {len(data['holidays'])}")
    print(f"  Transactions: {len(data['transactions']):,}")
    print(f"  Balance snapshots: {len(data['balance_snapshots']):,}")
    print(f"  FX rates: {len(data['fx_rates']):,}")
    print(f"  Corridors: {len(data['corridors'])}")
    print(f"  Stress scenarios: {len(data['stress_scenarios'])}")
