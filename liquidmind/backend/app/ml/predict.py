"""Inference module: load trained models and generate forecasts."""

import pickle
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.ml.features import compute_features

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class ForecastEngine:
    """Loads pre-trained models and produces cash flow forecasts."""

    def __init__(self):
        self.models: dict[int, lgb.Booster] = {}
        self.quantile_models: dict[tuple[int, str], lgb.Booster] = {}
        self.meta: dict[int, dict] = {}

    def load_models(self, horizons: list[int] = None):
        """Load all trained models from disk."""
        if horizons is None:
            horizons = [1, 3, 5]

        for h in horizons:
            model_path = MODEL_DIR / f"lgbm_h{h}.txt"
            if model_path.exists():
                self.models[h] = lgb.Booster(model_file=str(model_path))
                print(f"Loaded model for horizon={h}")

                meta_path = MODEL_DIR / f"lgbm_h{h}_meta.pkl"
                if meta_path.exists():
                    with open(meta_path, "rb") as f:
                        self.meta[h] = pickle.load(f)

            # Quantile models
            for qname in ["p5", "p95"]:
                qpath = MODEL_DIR / f"lgbm_h{h}_{qname}.txt"
                if qpath.exists():
                    self.quantile_models[(h, qname)] = lgb.Booster(model_file=str(qpath))

    def predict(
        self,
        transactions_df: pd.DataFrame,
        balances_df: pd.DataFrame,
        fx_df: pd.DataFrame,
        account_id: str,
        currency: str,
        country: str,
        target_date: date,
        horizon: int = 1,
    ) -> dict:
        """Predict net cash flow for a given account and horizon.

        Returns dict with predicted_net, confidence_low, confidence_high,
        and top feature contributions.
        """
        if horizon not in self.models:
            raise ValueError(f"No model loaded for horizon={horizon}")

        features = compute_features(
            transactions_df, balances_df, fx_df,
            account_id, currency, country, target_date,
        )
        features["account_id_hash"] = hash(str(account_id)) % 1000

        # Ensure feature order matches training
        feature_names = self.meta.get(horizon, {}).get("feature_names", list(features.keys()))
        X = pd.DataFrame([features])

        # Add missing columns
        for col in feature_names:
            if col not in X.columns:
                X[col] = 0
        X = X[feature_names]
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Point prediction
        predicted_net = float(self.models[horizon].predict(X)[0])

        # Confidence interval
        confidence_low = predicted_net
        confidence_high = predicted_net
        if (horizon, "p5") in self.quantile_models:
            confidence_low = float(self.quantile_models[(horizon, "p5")].predict(X)[0])
        if (horizon, "p95") in self.quantile_models:
            confidence_high = float(self.quantile_models[(horizon, "p95")].predict(X)[0])

        # Feature importance (top drivers for this prediction)
        top_features = self.meta.get(horizon, {}).get("top_features", [])[:5]
        feature_drivers = {}
        for feat_name, _ in top_features:
            if feat_name in features:
                feature_drivers[feat_name] = features[feat_name]

        return {
            "predicted_net": round(predicted_net, 2),
            "confidence_low": round(confidence_low, 2),
            "confidence_high": round(confidence_high, 2),
            "feature_drivers": feature_drivers,
            "model_version": f"lgbm_h{horizon}_v1",
        }

    def predict_multi_horizon(
        self,
        transactions_df: pd.DataFrame,
        balances_df: pd.DataFrame,
        fx_df: pd.DataFrame,
        account_id: str,
        currency: str,
        country: str,
        base_date: date,
    ) -> list[dict]:
        """Predict for all available horizons from a base date."""
        results = []
        for horizon in sorted(self.models.keys()):
            target_date = base_date + timedelta(days=horizon)
            pred = self.predict(
                transactions_df, balances_df, fx_df,
                account_id, currency, country, base_date, horizon,
            )
            pred["horizon"] = horizon
            pred["target_date"] = str(target_date)
            results.append(pred)
        return results


# Singleton
_engine: ForecastEngine | None = None


def get_forecast_engine() -> ForecastEngine:
    global _engine
    if _engine is None:
        _engine = ForecastEngine()
        _engine.load_models()
    return _engine
