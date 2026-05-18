"""Feature engineering for the LightGBM cash flow forecast model."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.data_generator.generator import HOLIDAYS, BASE_FX


def is_holiday_static(d: date, country: str) -> bool:
    holidays = HOLIDAYS.get(country, [])
    return (d.month, d.day) in holidays


def compute_features(
    transactions_df: pd.DataFrame,
    balances_df: pd.DataFrame,
    fx_df: pd.DataFrame,
    account_id: str,
    currency: str,
    country: str,
    target_date: date,
) -> dict:
    """Compute feature vector for a single (account, date) prediction."""

    # Filter to this account's transactions
    acct_txns = transactions_df[transactions_df["account_id"] == account_id].copy()
    acct_txns["date"] = acct_txns["time"].dt.date

    # --- Temporal features ---
    features = {}
    features["day_of_week"] = target_date.weekday()
    features["day_of_month"] = target_date.day
    features["month"] = target_date.month
    features["week_of_year"] = target_date.isocalendar()[1]
    features["is_weekend"] = int(target_date.weekday() >= 5)
    features["is_holiday"] = int(is_holiday_static(target_date, country))

    # Days to next holiday
    features["days_to_next_holiday"] = 30
    for i in range(1, 31):
        if is_holiday_static(target_date + timedelta(days=i), country):
            features["days_to_next_holiday"] = i
            break

    # Month-end indicators
    if target_date.month == 12:
        last_day = date(target_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
    features["days_to_month_end"] = (last_day - target_date).days
    features["is_month_end_3d"] = int(features["days_to_month_end"] <= 3)
    features["is_quarter_end"] = int(target_date.month in (3, 6, 9, 12) and features["days_to_month_end"] <= 5)
    features["is_year_end"] = int(target_date.month == 12 and features["days_to_month_end"] <= 5)

    # Salary window
    features["is_salary_window"] = int(25 <= target_date.day <= 28)

    # --- Rolling volume features ---
    # Daily aggregates
    daily = acct_txns.groupby(["date", "direction"]).agg(
        count=("amount", "count"),
        total=("amount", "sum"),
    ).reset_index()

    # Compute in/out daily totals
    daily_in = daily[daily["direction"] == "in"].set_index("date")["total"]
    daily_out = daily[daily["direction"] == "out"].set_index("date")["total"]
    daily_count_in = daily[daily["direction"] == "in"].set_index("date")["count"]
    daily_count_out = daily[daily["direction"] == "out"].set_index("date")["count"]

    all_dates = pd.date_range(acct_txns["date"].min(), target_date - timedelta(days=1))
    daily_in = daily_in.reindex(all_dates, fill_value=0)
    daily_out = daily_out.reindex(all_dates, fill_value=0)
    daily_net = daily_in - daily_out
    daily_count = daily_count_in.reindex(all_dates, fill_value=0) + daily_count_out.reindex(all_dates, fill_value=0)

    for window in [1, 3, 7, 14, 30]:
        suffix = f"_{window}d"
        if len(daily_in) >= window:
            features[f"inflow_sum{suffix}"] = daily_in.iloc[-window:].sum()
            features[f"outflow_sum{suffix}"] = daily_out.iloc[-window:].sum()
            features[f"net_flow_sum{suffix}"] = daily_net.iloc[-window:].sum()
            features[f"txn_count{suffix}"] = daily_count.iloc[-window:].sum()
            features[f"net_flow_mean{suffix}"] = daily_net.iloc[-window:].mean()
            features[f"net_flow_std{suffix}"] = daily_net.iloc[-window:].std()
            features[f"outflow_mean{suffix}"] = daily_out.iloc[-window:].mean()
        else:
            for feat in ["inflow_sum", "outflow_sum", "net_flow_sum", "txn_count",
                         "net_flow_mean", "net_flow_std", "outflow_mean"]:
                features[f"{feat}{suffix}"] = 0

    # Volume ratio: last 7d vs 30d average
    if len(daily_net) >= 30:
        avg_7d = daily_net.iloc[-7:].mean()
        avg_30d = daily_net.iloc[-30:].mean()
        features["volume_ratio_7d_30d"] = avg_7d / avg_30d if avg_30d != 0 else 1.0
    else:
        features["volume_ratio_7d_30d"] = 1.0

    # Same-day-last-week comparison
    target_dow = target_date.weekday()
    same_dow = daily_net.iloc[:-1][daily_net.index.weekday == target_dow]
    if len(same_dow) >= 1:
        features["same_dow_last_week_net"] = same_dow.iloc[-1]
        features["same_dow_avg_4w_net"] = same_dow.iloc[-4:].mean() if len(same_dow) >= 4 else same_dow.mean()
    else:
        features["same_dow_last_week_net"] = 0
        features["same_dow_avg_4w_net"] = 0

    # --- Channel-specific features ---
    for channel in ["p2p", "card", "sepa", "swift", "partner"]:
        ch_txns = acct_txns[acct_txns["channel"] == channel]
        ch_daily_out = ch_txns[ch_txns["direction"] == "out"].groupby("date")["amount"].sum()
        ch_daily_out = ch_daily_out.reindex(all_dates, fill_value=0)

        if len(ch_daily_out) >= 7:
            features[f"channel_{channel}_out_7d"] = ch_daily_out.iloc[-7:].sum()
        else:
            features[f"channel_{channel}_out_7d"] = 0

    # In-flight: transactions initiated but not yet settled
    pending = acct_txns[
        (acct_txns["expected_settle"].dt.date > target_date - timedelta(days=1))
        & (acct_txns["time"].dt.date < target_date)
    ]
    features["in_flight_in"] = pending[pending["direction"] == "in"]["amount"].sum()
    features["in_flight_out"] = pending[pending["direction"] == "out"]["amount"].sum()

    # --- Balance features ---
    acct_bals = balances_df[balances_df["account_id"] == account_id].copy()
    acct_bals["date"] = acct_bals["time"].dt.date
    acct_bals = acct_bals.sort_values("date")

    if len(acct_bals) > 0:
        latest_bal = acct_bals.iloc[-1]
        features["current_balance"] = latest_bal["balance"]
        features["current_available"] = latest_bal["available"]

        if len(acct_bals) >= 2:
            features["balance_change_1d"] = acct_bals["balance"].iloc[-1] - acct_bals["balance"].iloc[-2]
        else:
            features["balance_change_1d"] = 0

        if len(acct_bals) >= 7:
            features["balance_change_7d"] = acct_bals["balance"].iloc[-1] - acct_bals["balance"].iloc[-7]
        else:
            features["balance_change_7d"] = 0
    else:
        features["current_balance"] = 0
        features["current_available"] = 0
        features["balance_change_1d"] = 0
        features["balance_change_7d"] = 0

    # --- FX features ---
    ccy_fx = fx_df[fx_df["base_currency"] == currency].copy()
    ccy_fx["date"] = ccy_fx["time"].dt.date
    ccy_fx = ccy_fx.sort_values("date")

    if len(ccy_fx) > 0 and currency != "USD":
        features["fx_rate_current"] = ccy_fx["rate"].iloc[-1]
        if len(ccy_fx) >= 7:
            features["fx_rate_ma7"] = ccy_fx["rate"].iloc[-7:].mean()
            features["fx_rate_ma30"] = ccy_fx["rate"].iloc[-30:].mean() if len(ccy_fx) >= 30 else ccy_fx["rate"].mean()
            features["fx_volatility_30d"] = ccy_fx["rate"].iloc[-30:].std() if len(ccy_fx) >= 30 else ccy_fx["rate"].std()
        else:
            features["fx_rate_ma7"] = ccy_fx["rate"].iloc[-1]
            features["fx_rate_ma30"] = ccy_fx["rate"].iloc[-1]
            features["fx_volatility_30d"] = 0
    else:
        features["fx_rate_current"] = 1.0
        features["fx_rate_ma7"] = 1.0
        features["fx_rate_ma30"] = 1.0
        features["fx_volatility_30d"] = 0

    return features


def build_training_dataset(
    transactions_df: pd.DataFrame,
    balances_df: pd.DataFrame,
    fx_df: pd.DataFrame,
    accounts: list[dict],
    start_date: date,
    end_date: date,
    horizon: int = 1,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build training dataset for all accounts over a date range.

    Returns (X, y) where y is the net flow for `horizon` business days ahead.
    """
    rows = []
    targets = []

    # Pre-compute daily net flows per account
    txn_copy = transactions_df.copy()
    txn_copy["date"] = txn_copy["time"].dt.date
    txn_copy["signed_amount"] = txn_copy.apply(
        lambda r: r["amount"] if r["direction"] == "in" else -r["amount"], axis=1
    )
    daily_net_by_acct = txn_copy.groupby(["account_id", "date"])["signed_amount"].sum()

    current = start_date
    while current <= end_date:
        for acct in accounts:
            aid = acct["id"]
            country = acct["bank_country"]
            currency = acct["currency"]

            # Target: net flow for `horizon` days ahead
            target_dates = []
            d = current
            for _ in range(horizon):
                d += timedelta(days=1)
                target_dates.append(d)

            target_net = 0
            for td in target_dates:
                try:
                    target_net += daily_net_by_acct.loc[(aid, td)]
                except KeyError:
                    pass

            # Skip weekends for training
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            feats = compute_features(
                transactions_df, balances_df, fx_df,
                aid, currency, country, current,
            )
            feats["account_id_hash"] = hash(str(aid)) % 1000
            rows.append(feats)
            targets.append(target_net)

        current += timedelta(days=1)

    X = pd.DataFrame(rows)
    y = pd.Series(targets, name="target_net_flow")
    return X, y
