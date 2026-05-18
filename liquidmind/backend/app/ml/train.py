"""Train LightGBM forecast model on synthetic data."""

import pickle
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

from app.data_generator.generator import SyntheticDataGenerator
from app.ml.features import build_training_dataset

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def train_model(
    transactions_df,
    balances_df,
    fx_df,
    accounts: list[dict],
    horizon: int = 1,
    save: bool = True,
) -> dict:
    """Train a LightGBM model for net flow prediction.

    Returns dict with model, metrics, and feature names.
    """
    # Use first 80% for training, last 20% for validation
    total_days = (transactions_df["time"].dt.date.max() - transactions_df["time"].dt.date.min()).days
    train_days = int(total_days * 0.8)

    start_date = transactions_df["time"].dt.date.min() + timedelta(days=60)  # skip first 60d for rolling features
    split_date = start_date + timedelta(days=train_days)
    end_date = transactions_df["time"].dt.date.max() - timedelta(days=horizon)

    print(f"Building training dataset (horizon={horizon})...")
    print(f"  Train period: {start_date} to {split_date}")
    print(f"  Val period: {split_date} to {end_date}")

    X_train, y_train = build_training_dataset(
        transactions_df, balances_df, fx_df, accounts,
        start_date, split_date, horizon,
    )

    X_val, y_val = build_training_dataset(
        transactions_df, balances_df, fx_df, accounts,
        split_date + timedelta(days=1), end_date, horizon,
    )

    print(f"  Training samples: {len(X_train)}, Validation samples: {len(X_val)}")

    # Replace infinities and NaNs
    X_train = X_train.replace([np.inf, -np.inf], np.nan).fillna(0)
    X_val = X_val.replace([np.inf, -np.inf], np.nan).fillna(0)

    # LightGBM datasets
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    params = {
        "objective": "regression",
        "metric": "mae",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "n_jobs": -1,
    }

    print("Training LightGBM model...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )

    # Evaluate
    y_pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, y_pred)

    # Directional accuracy
    y_val_arr = np.array(y_val)
    correct_dir = np.sum(np.sign(y_pred) == np.sign(y_val_arr))
    dir_accuracy = correct_dir / len(y_val_arr) if len(y_val_arr) > 0 else 0

    print(f"\nMetrics (horizon={horizon}):")
    print(f"  MAE: ${mae:,.2f}")
    print(f"  Directional accuracy: {dir_accuracy:.2%}")

    # Feature importance
    importance = dict(zip(X_train.columns, model.feature_importance(importance_type="gain")))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
    print(f"\nTop 15 features:")
    for feat, imp in top_features:
        print(f"  {feat}: {imp:.0f}")

    if save:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODEL_DIR / f"lgbm_h{horizon}.txt"
        model.save_model(str(model_path))

        meta = {
            "horizon": horizon,
            "feature_names": list(X_train.columns),
            "mae": mae,
            "directional_accuracy": dir_accuracy,
            "top_features": top_features,
        }
        meta_path = MODEL_DIR / f"lgbm_h{horizon}_meta.pkl"
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)

        print(f"\nModel saved to {model_path}")

    return {
        "model": model,
        "feature_names": list(X_train.columns),
        "mae": mae,
        "directional_accuracy": dir_accuracy,
        "top_features": top_features,
    }


def train_quantile_models(
    transactions_df,
    balances_df,
    fx_df,
    accounts: list[dict],
    horizon: int = 1,
) -> dict:
    """Train quantile regression models for confidence intervals (P5 and P95)."""
    total_days = (transactions_df["time"].dt.date.max() - transactions_df["time"].dt.date.min()).days
    train_days = int(total_days * 0.8)

    start_date = transactions_df["time"].dt.date.min() + timedelta(days=60)
    split_date = start_date + timedelta(days=train_days)
    end_date = transactions_df["time"].dt.date.max() - timedelta(days=horizon)

    X_train, y_train = build_training_dataset(
        transactions_df, balances_df, fx_df, accounts,
        start_date, split_date, horizon,
    )

    X_train = X_train.replace([np.inf, -np.inf], np.nan).fillna(0)
    train_data = lgb.Dataset(X_train, label=y_train)

    results = {}
    for alpha, name in [(0.05, "p5"), (0.95, "p95")]:
        params = {
            "objective": "quantile",
            "alpha": alpha,
            "metric": "quantile",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "verbose": -1,
        }

        model = lgb.train(params, train_data, num_boost_round=300)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODEL_DIR / f"lgbm_h{horizon}_{name}.txt"
        model.save_model(str(model_path))
        results[name] = model
        print(f"  Quantile model ({name}) saved to {model_path}")

    return results


if __name__ == "__main__":
    print("Generating synthetic data for training...")
    gen = SyntheticDataGenerator(seed=42, days=365)
    data = gen.generate_all()

    for horizon in [1, 3, 5]:
        print(f"\n{'='*60}")
        print(f"Training model for horizon={horizon}")
        print(f"{'='*60}")
        train_model(
            data["transactions"],
            data["balance_snapshots"],
            data["fx_rates"],
            data["accounts"],
            horizon=horizon,
        )
        train_quantile_models(
            data["transactions"],
            data["balance_snapshots"],
            data["fx_rates"],
            data["accounts"],
            horizon=horizon,
        )
