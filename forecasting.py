"""
INAIBA - Forecasting Module
Multiple models (statistical + optional ML), historical validation, automatic
selection, prediction intervals. Supports Revenue, Profit, Quantity and Orders.
Designed to degrade gracefully when a library or sufficient history is unavailable.

No Streamlit UI and no chart creation here — this module only returns
calculations / dataframes / result dicts for app.py to render.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# Optional dependency detection (module must work without sklearn)
# ------------------------------------------------------------------

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_LINEAR_AVAILABLE = True
except ImportError:
    SKLEARN_LINEAR_AVAILABLE = False

try:
    from sklearn.tree import DecisionTreeRegressor
    SKLEARN_TREE_AVAILABLE = True
except ImportError:
    SKLEARN_TREE_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    SKLEARN_ENSEMBLE_AVAILABLE = True
except ImportError:
    SKLEARN_ENSEMBLE_AVAILABLE = False


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

SUPPORTED_TARGETS = ["Revenue", "Profit", "Quantity", "Orders"]
SUPPORTED_HORIZONS = [3, 6, 12]

MIN_MONTHS_FOR_FORECAST = 4     # below this, forecast is produced but flagged unreliable
MIN_MONTHS_FOR_SEASONAL = 24    # need 2 full cycles for Seasonal Naive
MIN_MONTHS_FOR_ML = 6           # tree-based models need a minimum sample to be meaningful


# ------------------------------------------------------------------
# Time series preparation
# ------------------------------------------------------------------

def prepare_monthly_series(df: pd.DataFrame, date_col: str, target_col: str, agg: str = "sum") -> pd.Series:
    """
    Parses dates, sorts chronologically, aggregates to monthly totals, and
    reindexes over the full month range so gaps (months with no transactions)
    are filled with 0 rather than silently skipped or interpolated.

    Raises ValueError (with a clear, user-facing message) for missing columns,
    an empty dataframe, or a date column that cannot be parsed at all.
    """
    if df is None or df.empty:
        raise ValueError("No data provided.")
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in the data.")
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in the data.")

    work = df[[date_col, target_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work[target_col] = pd.to_numeric(work[target_col], errors="coerce")

    work = work.dropna(subset=[date_col])
    if work.empty:
        raise ValueError(f"No valid dates could be parsed from '{date_col}'.")

    work[target_col] = work[target_col].fillna(0.0)
    work = work.sort_values(date_col)
    work["__period"] = work[date_col].dt.to_period("M")

    grouped = work.groupby("__period")[target_col].agg(agg)
    grouped.index = grouped.index.to_timestamp()

    full_range = pd.date_range(grouped.index.min(), grouped.index.max(), freq="MS")
    series = grouped.reindex(full_range, fill_value=0.0)
    series.index.name = "Month"
    series.name = target_col
    return series


def monthly_df_from_raw(df: pd.DataFrame, date_col: str, target_col: str, agg: str = "sum") -> pd.DataFrame:
    """Convenience wrapper: returns a Month/<target_col> dataframe, same shape generate_forecast expects."""
    series = prepare_monthly_series(df, date_col, target_col, agg=agg)
    return series.reset_index().rename(columns={"index": "Month"})


def _build_time_features(
    index: pd.DatetimeIndex,
    offset: int = 0,
) -> np.ndarray:
    """
    Builds a feature matrix from a monthly date index.

    Features:
    - Linear time step
    - Month-of-year sine component
    - Month-of-year cosine component

    The input is explicitly normalized to DatetimeIndex so that
    .month is always available.
    """

    # --------------------------------------------------------------
    # Normalize the input to a real DatetimeIndex
    # --------------------------------------------------------------
    index = pd.DatetimeIndex(
        pd.to_datetime(
            index,
            errors="coerce",
        )
    )

    # --------------------------------------------------------------
    # Validate dates
    # --------------------------------------------------------------
    if index.isna().any():
        raise ValueError(
            "Forecasting index contains invalid dates."
        )

    # --------------------------------------------------------------
    # Linear time feature
    # --------------------------------------------------------------
    t = (
        np.arange(
            offset,
            offset + len(index),
        )
        .reshape(-1, 1)
        .astype(float)
    )

    # --------------------------------------------------------------
    # Month-of-year feature
    # --------------------------------------------------------------
    month = index.month.to_numpy(
        dtype=float
    )

    # --------------------------------------------------------------
    # Seasonal features
    # --------------------------------------------------------------
    sin_m = np.sin(
        2 * np.pi * month / 12
    ).reshape(-1, 1)

    cos_m = np.cos(
        2 * np.pi * month / 12
    ).reshape(-1, 1)

    # --------------------------------------------------------------
    # Final feature matrix
    # --------------------------------------------------------------
    return np.hstack(
        [
            t,
            sin_m,
            cos_m,
        ]
    )

def _future_index(
    series: pd.Series,
    horizon: int,
) -> pd.DatetimeIndex:
    """
    Creates the next `horizon` monthly periods from the
    last valid date in the historical series.
    """

    if not isinstance(
        series,
        pd.Series,
    ):
        raise TypeError(
            "Forecast input must be a pandas Series."
        )

    if series.empty:
        raise ValueError(
            "Cannot create future forecast dates from an empty series."
        )

    # --------------------------------------------------------------
    # Normalize the series index
    # --------------------------------------------------------------
    normalized_index = pd.DatetimeIndex(
        pd.to_datetime(
            series.index,
            errors="coerce",
        )
    )

    normalized_index = normalized_index[
        ~normalized_index.isna()
    ]

    if len(normalized_index) == 0:
        raise ValueError(
            "Forecast series does not contain valid dates."
        )

    # --------------------------------------------------------------
    # Last historical date
    # --------------------------------------------------------------
    last_date = normalized_index.max()

    # --------------------------------------------------------------
    # Future monthly dates
    # --------------------------------------------------------------
    return pd.date_range(
        start=(
            last_date
            + pd.offsets.MonthBegin(1)
        ),
        periods=int(horizon),
        freq="MS",
    )
# ------------------------------------------------------------------
# Individual forecasting methods
# Each returns: np.array of point forecasts, length = horizon
# ------------------------------------------------------------------

def moving_average_forecast(series: pd.Series, horizon: int, window: int = 3) -> np.ndarray:
    window = max(1, min(window, len(series)))
    avg = series.tail(window).mean()
    return np.full(horizon, avg if pd.notna(avg) else 0.0)


def drift_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    """Hyndman's drift method: extrapolates the average change between the first and last observation."""
    values = series.values.astype(float)
    n = len(values)
    if n < 2:
        return np.full(horizon, values[-1] if n else 0.0)
    slope = (values[-1] - values[0]) / (n - 1)
    steps = np.arange(1, horizon + 1)
    forecast = values[-1] + slope * steps
    return np.maximum(forecast, 0)


def linear_regression_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    x = np.arange(len(series)).reshape(-1, 1)
    y = series.values.astype(float)
    if SKLEARN_LINEAR_AVAILABLE:
        model = LinearRegression()
        model.fit(x, y)
        future_x = np.arange(len(series), len(series) + horizon).reshape(-1, 1)
        preds = model.predict(future_x)
    else:
        # Fallback: numpy polyfit (degree 1) — keeps this model working without sklearn
        coeffs = np.polyfit(x.flatten(), y, 1)
        future_x = np.arange(len(series), len(series) + horizon)
        preds = np.polyval(coeffs, future_x)
    return np.maximum(preds, 0)


def exponential_smoothing_forecast(series: pd.Series, horizon: int, alpha: float = 0.4) -> np.ndarray:
    """Simple exponential smoothing (level only) implemented natively, no external dependency."""
    values = series.values.astype(float)
    level = values[0]
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level
    return np.full(horizon, level)


def double_exponential_smoothing_forecast(series: pd.Series, horizon: int, alpha: float = 0.4, beta: float = 0.2) -> np.ndarray:
    """Holt's linear trend method (level + trend), native implementation."""
    values = series.values.astype(float)
    if len(values) < 2:
        return np.full(horizon, values[-1] if len(values) else 0.0)
    level = values[0]
    trend = values[1] - values[0]
    for v in values[1:]:
        last_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
    return np.array([max(level + (i + 1) * trend, 0) for i in range(horizon)])


def seasonal_naive_forecast(series: pd.Series, horizon: int, period: int = 12) -> np.ndarray:
    """Repeats the same month from one seasonal cycle ago, with a light trend adjustment."""
    if len(series) < period:
        return moving_average_forecast(series, horizon)
    last_cycle = series.values[-period:]
    reps = int(np.ceil(horizon / period))
    tiled = np.tile(last_cycle, reps)[:horizon]
    recent_avg = series.tail(period).mean()
    prior_avg = series.head(period).mean() if len(series) >= 2 * period else recent_avg
    trend_factor = (recent_avg / prior_avg) if prior_avg else 1.0
    return np.maximum(tiled * trend_factor, 0)


def _ml_tree_forecast(model, series: pd.Series, horizon: int) -> np.ndarray:
    """Shared fit/predict path for decision-tree-style sklearn regressors."""
    X = _build_time_features(series.index, offset=0)
    y = series.values.astype(float)
    model.fit(X, y)
    future_index = _future_index(series, horizon)
    X_future = _build_time_features(future_index, offset=len(series))
    preds = model.predict(X_future)
    return np.maximum(preds, 0)


def decision_tree_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    if not SKLEARN_TREE_AVAILABLE:
        return moving_average_forecast(series, horizon)
    max_depth = 4 if len(series) >= 12 else 2
    model = DecisionTreeRegressor(max_depth=max_depth, random_state=42)
    return _ml_tree_forecast(model, series, horizon)


def random_forest_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    if not SKLEARN_ENSEMBLE_AVAILABLE:
        return moving_average_forecast(series, horizon)
    n_estimators = 200 if len(series) >= 12 else 50
    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=5, random_state=42)
    return _ml_tree_forecast(model, series, horizon)


def gradient_boosting_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    if not SKLEARN_ENSEMBLE_AVAILABLE:
        return moving_average_forecast(series, horizon)
    n_estimators = 150 if len(series) >= 12 else 50
    model = GradientBoostingRegressor(n_estimators=n_estimators, max_depth=3, random_state=42)
    return _ml_tree_forecast(model, series, horizon)


# Base models that always work, no optional dependency required.
MODEL_REGISTRY = {
    "Moving Average": moving_average_forecast,
    "Drift": drift_forecast,
    "Linear Regression": linear_regression_forecast,
    "Exponential Smoothing": exponential_smoothing_forecast,
    "Holt's Trend (Double Exp. Smoothing)": double_exponential_smoothing_forecast,
}

# ML models that require sklearn; only registered when the dependency is present.
ML_MODEL_REGISTRY = {}
if SKLEARN_TREE_AVAILABLE:
    ML_MODEL_REGISTRY["Decision Tree"] = decision_tree_forecast
if SKLEARN_ENSEMBLE_AVAILABLE:
    ML_MODEL_REGISTRY["Random Forest"] = random_forest_forecast
    ML_MODEL_REGISTRY["Gradient Boosting"] = gradient_boosting_forecast


def get_available_models(n_obs: int) -> dict:
    """
    Returns the {model_name: forecast_fn} dict applicable given the amount of
    history available and which optional libraries are installed. This is the
    list app.py should use to populate a model-choice dropdown.
    """
    registry = dict(MODEL_REGISTRY)
    if n_obs >= MIN_MONTHS_FOR_ML:
        registry.update(ML_MODEL_REGISTRY)
    if n_obs >= MIN_MONTHS_FOR_SEASONAL:
        registry["Seasonal Naive"] = seasonal_naive_forecast
    return registry


# ------------------------------------------------------------------
# Validation & model selection
# ------------------------------------------------------------------

def _holdout_split(series: pd.Series, test_size: int):
    train = series.iloc[: len(series) - test_size]
    test = series.iloc[len(series) - test_size:]
    return train, test


def evaluate_model(model_fn, series: pd.Series, test_size: int) -> dict | None:
    """
    Backtests a model: fits on the training portion only, predicts the held-out
    portion, and scores those predictions against the actuals. Returns
    MAE, RMSE, R2 and MAPE — never inf/NaN; metrics that are mathematically
    undefined for the given data (e.g. R2 with a single test point, MAPE with
    an all-zero actuals window) are returned as None instead.
    """
    if len(series) <= test_size or test_size < 1:
        return None
    train, test = _holdout_split(series, test_size)
    try:
        preds = model_fn(train, test_size)
    except (ValueError, np.linalg.LinAlgError) as exc:
        # A specific, understood failure mode (e.g. degenerate fit) — treat as
        # "this model can't be scored on this data" rather than crashing.
        return {"MAE": None, "RMSE": None, "R2": None, "MAPE": None, "error": str(exc)}

    actual = test.values.astype(float)
    preds = np.asarray(preds, dtype=float)[: len(actual)]

    errors = actual - preds
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    r2 = (1 - ss_res / ss_tot) if (len(actual) >= 2 and ss_tot > 0) else None

    nonzero = actual != 0
    mape = float(np.mean(np.abs(errors[nonzero] / actual[nonzero])) * 100) if nonzero.any() else None

    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


def select_best_model(series: pd.Series, model_choice: str = "Auto Select") -> dict:
    """
    Evaluates applicable models via holdout backtesting and selects the one
    with the lowest RMSE (the documented selection metric — RMSE penalizes
    large misses more than MAE, which suits forecast planning use cases).

    If model_choice names a specific, available model, that model is used
    directly and not compared against the others (results still include
    every candidate's metrics for the comparison table).
    """
    n = len(series)
    test_size = max(1, min(3, n // 4))

    candidates = get_available_models(n)

    results = {}
    for name, fn in candidates.items():
        metrics = evaluate_model(fn, series, test_size)
        if metrics is not None and metrics.get("RMSE") is not None:
            results[name] = metrics

    if model_choice and model_choice != "Auto Select" and model_choice in candidates:
        return {
            "selected_model": model_choice,
            "results": results,
            "validated": model_choice in results,
        }

    if not results:
        # Not enough data to validate any model — default to Moving Average, no accuracy claim
        return {
            "selected_model": "Moving Average",
            "results": {},
            "validated": False,
        }

    best_model = min(results.items(), key=lambda kv: kv[1]["RMSE"])[0]
    return {"selected_model": best_model, "results": results, "validated": True}


# ------------------------------------------------------------------
# Prediction intervals
# ------------------------------------------------------------------

def prediction_intervals(point_forecast: np.ndarray, residual_std: float, z: float = 1.28) -> tuple[np.ndarray, np.ndarray]:
    """~80% interval by default (z=1.28). Widens with forecast horizon step to reflect growing uncertainty."""
    steps = np.arange(1, len(point_forecast) + 1)
    widening = np.sqrt(steps)
    margin = z * residual_std * widening
    lower = np.maximum(point_forecast - margin, 0)
    upper = point_forecast + margin
    return lower, upper


def residual_std_from_validation(series: pd.Series, model_fn, test_size: int) -> float:
    fallback = float(series.std()) if pd.notna(series.std()) else 0.0
    if len(series) <= test_size or test_size < 1:
        return fallback
    train, test = _holdout_split(series, test_size)
    try:
        preds = np.asarray(model_fn(train, test_size), dtype=float)[: len(test)]
    except (ValueError, np.linalg.LinAlgError):
        return fallback
    residuals = test.values.astype(float) - preds
    return float(np.std(residuals)) if len(residuals) else fallback


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def generate_forecast(
    monthly_df: pd.DataFrame,
    horizon: int = 3,
    target_column: str = "Revenue",
    model_choice: str = "Auto Select",
) -> dict:
    """
    monthly_df: a dataframe with a "Month" column and a target_column column
    (e.g. the output of analytics.monthly_revenue(), or monthly_df_from_raw()
    for Profit / Quantity / Orders). Returns a dict with the forecast table,
    selected model, accuracy metrics, historical values, and a
    data-sufficiency flag — never raises for bad/missing/insufficient data.
    """
    if horizon not in SUPPORTED_HORIZONS:
        horizon = min(SUPPORTED_HORIZONS, key=lambda h: abs(h - horizon)) if horizon else 3

    if monthly_df is None or monthly_df.empty:
        return {"sufficient_data": False, "message": "No data provided for forecasting."}

    if "Month" not in monthly_df.columns:
        return {"sufficient_data": False, "message": "Expected a 'Month' column in the monthly data."}
    if target_column not in monthly_df.columns:
        return {
            "sufficient_data": False,
            "message": f"'{target_column}' was not found in the monthly data. "
                       f"Supported targets: {', '.join(SUPPORTED_TARGETS)}.",
        }

    work = monthly_df[["Month", target_column]].copy()
    work[target_column] = pd.to_numeric(work[target_column], errors="coerce")
    if work[target_column].isna().all():
        return {"sufficient_data": False, "message": f"'{target_column}' contains no valid numeric values."}
    work[target_column] = work[target_column].fillna(0.0)

    if len(work) < 2:
        return {
            "sufficient_data": False,
            "message": "Insufficient historical data for reliable forecasting. At least a few months of history are needed.",
        }

    series = work.set_index("Month")[target_column].astype(float)
    n = len(series)
    is_constant = bool(series.nunique() <= 1)

    selection = select_best_model(series, model_choice=model_choice)
    model_name = selection["selected_model"]
    available = get_available_models(n)
    model_fn = available.get(model_name, moving_average_forecast)

    point_forecast = model_fn(series, horizon)

    test_size = max(1, min(3, n // 4))
    res_std = residual_std_from_validation(series, model_fn, test_size)
    lower, upper = prediction_intervals(point_forecast, res_std)

    future_months = _future_index(series, horizon)

    forecast_table = pd.DataFrame({
        "Period": future_months,
        "PeriodLabel": future_months.strftime("%b %Y"),
        "Forecast": point_forecast,
        "Lower Bound": lower,
        "Upper Bound": upper,
    })
    last_actual = float(series.iloc[-1])
    forecast_table["Growth %"] = np.where(
        last_actual != 0,
        (forecast_table["Forecast"] - last_actual) / last_actual * 100,
        np.nan,
    )

    sufficient = n >= MIN_MONTHS_FOR_FORECAST
    reliability_note = ""
    if not sufficient:
        reliability_note = (
            f"Only {n} month(s) of history are available. Forecast reliability is limited; "
            f"treat these figures as indicative rather than precise."
        )
    if is_constant:
        note = "History is flat (no variation), so accuracy metrics like R2/MAPE may be undefined."
        reliability_note = f"{reliability_note} {note}".strip()

    historical_table = series.reset_index()
    historical_table.columns = ["Period", target_column]

    return {
        "sufficient_data": True,
        "reliable": sufficient,
        "reliability_note": reliability_note,
        "target_column": target_column,
        "horizon": horizon,
        "selected_model": model_name,
        "model_validated": selection["validated"],
        "model_comparison": selection["results"],
        "available_models": list(available.keys()),
        "forecast_table": forecast_table,
        "historical_table": historical_table,
        "next_month_forecast": float(point_forecast[0]) if horizon >= 1 else None,
        "three_month_forecast": float(np.sum(point_forecast[:3])) if horizon >= 3 else float(np.sum(point_forecast)),
        "expected_growth_next_month": float(forecast_table["Growth %"].iloc[0]) if len(forecast_table) else None,
        "history_months": n,
    }