"""
INAIBA - Anomaly Detection Module
Reusable engine for detecting unusual patterns in business sales data
(revenue, profit, quantity, discounts, and by dimension: product, region).

This module identifies statistically unusual behavior only. It never assumes
or asserts a cause (fraud, error, etc.) — flagged rows are described as
"unusual behavior detected" / "requires investigation" and left for a human
to interpret.

No Streamlit UI and no chart creation here — this module only returns
dataframes / dicts for app.py to render.
"""

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# Transparent severity thresholds (documented, not arbitrary)
# ------------------------------------------------------------------

# Rolling/overall z-score based detection (Revenue/Profit/Quantity trend, dimensions)
Z_SCORE_LOW = 1.5      # minimum deviation to flag at all
Z_SCORE_MEDIUM = 2.0
Z_SCORE_HIGH = 3.0

# IQR-multiple based detection (row-level: Discount, and any metric without a
# clean time trend). "Multiple" = how many IQRs beyond the nearest quartile.
IQR_MULTIPLE_LOW = 1.5   # Tukey's standard outlier fence
IQR_MULTIPLE_MEDIUM = 2.5
IQR_MULTIPLE_HIGH = 4.0  # Tukey's "far out" fence

RESULT_COLUMNS = [
    "Date", "Anomaly Type", "Area", "Actual", "Expected",
    "Deviation", "Deviation %", "Severity", "Business Impact",
]


def _severity_from_zscore(z_abs: float) -> str:
    if z_abs >= Z_SCORE_HIGH:
        return "High"
    if z_abs >= Z_SCORE_MEDIUM:
        return "Medium"
    return "Low"


def _severity_from_iqr_multiple(multiple: float) -> str:
    if multiple >= IQR_MULTIPLE_HIGH:
        return "High"
    if multiple >= IQR_MULTIPLE_MEDIUM:
        return "Medium"
    return "Low"


def _business_impact(anomaly_type: str, area: str, direction: str, deviation_pct, severity: str) -> str:
    """Neutral, non-diagnostic description. Never claims fraud, error, or any specific cause."""
    verb = "rose" if direction == "Increase" else "fell"
    if deviation_pct is not None and pd.notna(deviation_pct):
        magnitude = f"{abs(deviation_pct):.1f}% versus the expected baseline"
    else:
        magnitude = "versus the expected baseline"
    return (
        f"{anomaly_type} for {area} {verb} {magnitude} ({severity} severity). "
        f"Unusual behavior detected; requires investigation."
    )


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


# ------------------------------------------------------------------
# Rolling z-score detection (time trend — overall or per dimension entity)
# ------------------------------------------------------------------

def detect_monthly_anomalies(
    monthly_df: pd.DataFrame,
    value_col: str = "Revenue",
    anomaly_type: str = None,
    min_periods: int = 3,
) -> pd.DataFrame:
    """
    Detects anomalous months in an overall monthly series (e.g. total Revenue,
    Profit, or Quantity per month) using a rolling z-score against each
    point's own trailing window, so results never leak the point being
    scored into its own baseline.

    monthly_df must have a "Month" column and value_col.
    Returns the unified RESULT_COLUMNS schema, or an empty dataframe if the
    data is missing, too short, or has no variation to score against.
    """
    anomaly_type = anomaly_type or f"{value_col} Trend"

    if monthly_df is None or monthly_df.empty:
        return _empty_result()
    if "Month" not in monthly_df.columns or value_col not in monthly_df.columns:
        return _empty_result()

    df = monthly_df[["Month", value_col]].copy()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["Month"]).sort_values("Month")

    if len(df) < min_periods + 1:
        return _empty_result()
    if df[value_col].nunique(dropna=True) <= 1:
        # Flat series: no meaningful baseline variation to compare against
        return _empty_result()

    df[value_col] = df[value_col].fillna(0.0)
    df["RollingMean"] = df[value_col].rolling(window=min_periods, min_periods=min_periods).mean().shift(1)
    df["RollingStd"] = df[value_col].rolling(window=min_periods, min_periods=min_periods).std().shift(1)
    df["ZScore"] = (df[value_col] - df["RollingMean"]) / df["RollingStd"].replace(0, np.nan)
    df["PctDeviation"] = np.where(
        df["RollingMean"] > 0, (df[value_col] - df["RollingMean"]) / df["RollingMean"] * 100, np.nan
    )

    flagged = df[df["ZScore"].abs() >= Z_SCORE_LOW].copy()
    if flagged.empty:
        return _empty_result()

    flagged["Severity"] = flagged["ZScore"].abs().apply(_severity_from_zscore)
    flagged["Direction"] = np.where(flagged["ZScore"] > 0, "Increase", "Decrease")
    flagged["Business Impact"] = flagged.apply(
        lambda r: _business_impact(anomaly_type, "Overall", r["Direction"], r["PctDeviation"], r["Severity"]),
        axis=1,
    )

    out = pd.DataFrame({
        "Date": flagged["Month"].dt.strftime("%b %Y"),
        "Anomaly Type": anomaly_type,
        "Area": "Overall",
        "Actual": flagged[value_col],
        "Expected": flagged["RollingMean"],
        "Deviation": flagged[value_col] - flagged["RollingMean"],
        "Deviation %": flagged["PctDeviation"],
        "Severity": flagged["Severity"],
        "Business Impact": flagged["Business Impact"],
    })
    return out.reset_index(drop=True)


def detect_dimension_anomalies(
    df: pd.DataFrame,
    dim: str,
    value_col: str = "Revenue",
    anomaly_type: str = None,
    min_periods: int = 3,
) -> pd.DataFrame:
    """
    Detects anomalous months at the level of a dimension (Product, Category,
    Region, Branch, ...) using a per-entity rolling z-score on monthly
    value_col totals. Each entity is scored against its own trailing history
    only, so a naturally larger entity isn't flagged just for being larger.

    Returns the unified RESULT_COLUMNS schema, or an empty dataframe if the
    required columns are missing or no entity has enough history.
    """
    anomaly_type = anomaly_type or f"{dim} ({value_col})"

    if df is None or df.empty:
        return _empty_result()
    if dim not in df.columns or "Month" not in df.columns or value_col not in df.columns:
        return _empty_result()

    work = df[[dim, "Month", value_col]].copy()
    work["Month"] = pd.to_datetime(work["Month"], errors="coerce")
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=["Month", dim])
    work[value_col] = work[value_col].fillna(0.0)
    if work.empty:
        return _empty_result()

    grouped = work.groupby([dim, "Month"])[value_col].sum().reset_index()

    rows = []
    for entity, g in grouped.groupby(dim):
        g = g.sort_values("Month")
        if len(g) < min_periods + 1:
            continue
        if g[value_col].nunique(dropna=True) <= 1:
            continue
        g = g.copy()
        g["RollingMean"] = g[value_col].rolling(window=min_periods, min_periods=min_periods).mean().shift(1)
        g["RollingStd"] = g[value_col].rolling(window=min_periods, min_periods=min_periods).std().shift(1)
        g["ZScore"] = (g[value_col] - g["RollingMean"]) / g["RollingStd"].replace(0, np.nan)
        g["PctDeviation"] = np.where(
            g["RollingMean"] > 0, (g[value_col] - g["RollingMean"]) / g["RollingMean"] * 100, np.nan
        )
        flagged = g[g["ZScore"].abs() >= Z_SCORE_LOW].copy()
        if flagged.empty:
            continue
        flagged["Entity"] = entity
        rows.append(flagged)

    if not rows:
        return _empty_result()

    flagged = pd.concat(rows, ignore_index=True)
    flagged["Severity"] = flagged["ZScore"].abs().apply(_severity_from_zscore)
    flagged["Direction"] = np.where(flagged["ZScore"] > 0, "Increase", "Decrease")
    flagged["Business Impact"] = flagged.apply(
        lambda r: _business_impact(anomaly_type, str(r["Entity"]), r["Direction"], r["PctDeviation"], r["Severity"]),
        axis=1,
    )

    out = pd.DataFrame({
        "Date": flagged["Month"].dt.strftime("%b %Y"),
        "Anomaly Type": anomaly_type,
        "Area": flagged["Entity"].astype(str),
        "Actual": flagged[value_col],
        "Expected": flagged["RollingMean"],
        "Deviation": flagged[value_col] - flagged["RollingMean"],
        "Deviation %": flagged["PctDeviation"],
        "Severity": flagged["Severity"],
        "Business Impact": flagged["Business Impact"],
    })
    return out.reset_index(drop=True)


# ------------------------------------------------------------------
# IQR-based row-level detection (no time trend required — e.g. Discount)
# ------------------------------------------------------------------

def detect_iqr_outliers(
    df: pd.DataFrame,
    value_col: str = "Revenue",
    anomaly_type: str = None,
    area_col: str = None,
    date_col: str = None,
) -> pd.DataFrame:
    """
    Row-level IQR-based outlier detection (e.g. unusual discount or order
    values that don't have a clean monthly trend to compare against).

    Expected = median of value_col; severity is based on how many IQRs a
    point sits beyond the nearest quartile (Tukey's fences). Returns the
    unified RESULT_COLUMNS schema, or an empty dataframe if value_col is
    missing/empty or has no spread (constant values) to measure against.
    """
    anomaly_type = anomaly_type or f"{value_col} Outlier"

    if df is None or df.empty or value_col not in df.columns:
        return _empty_result()

    work = df.copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=[value_col])
    if work.empty:
        return _empty_result()

    q1, q3 = work[value_col].quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        # No spread to measure outliers against — flagging here would be arbitrary
        return _empty_result()

    lower_bound = q1 - IQR_MULTIPLE_LOW * iqr
    upper_bound = q3 + IQR_MULTIPLE_LOW * iqr
    outliers = work[(work[value_col] < lower_bound) | (work[value_col] > upper_bound)].copy()
    if outliers.empty:
        return _empty_result()

    median_val = work[value_col].median()
    distance = np.where(
        outliers[value_col] > q3, outliers[value_col] - q3, q1 - outliers[value_col]
    )
    multiple = np.abs(distance) / iqr
    severity = pd.Series(multiple, index=outliers.index).apply(_severity_from_iqr_multiple)
    direction = np.where(outliers[value_col] > median_val, "Increase", "Decrease")
    deviation = outliers[value_col] - median_val
    deviation_pct = np.where(median_val != 0, deviation / median_val * 100, np.nan)

    area = outliers[area_col].astype(str) if (area_col and area_col in outliers.columns) else "Overall"
    if date_col and date_col in outliers.columns:
        parsed_dates = pd.to_datetime(outliers[date_col], errors="coerce")
        date_display = parsed_dates.dt.strftime("%b %d, %Y").fillna("Unknown")
    else:
        date_display = "Unknown"

    business_impact = [
        _business_impact(
            anomaly_type,
            area.iloc[i] if isinstance(area, pd.Series) else area,
            direction[i],
            deviation_pct[i],
            severity.iloc[i],
        )
        for i in range(len(outliers))
    ]

    out = pd.DataFrame({
        "Date": date_display if isinstance(date_display, str) else date_display.values,
        "Anomaly Type": anomaly_type,
        "Area": area,
        "Actual": outliers[value_col].values,
        "Expected": median_val,
        "Deviation": deviation.values,
        "Deviation %": deviation_pct,
        "Severity": severity.values,
        "Business Impact": business_impact,
    })
    return out.reset_index(drop=True)


# ------------------------------------------------------------------
# High-level orchestration: run every applicable detector at once
# ------------------------------------------------------------------

def run_anomaly_scan(
    monthly_df: pd.DataFrame = None,
    detail_df: pd.DataFrame = None,
    revenue_col: str = "Revenue",
    profit_col: str = "Profit",
    quantity_col: str = "Quantity",
    discount_col: str = "Discount",
    product_col: str = "Product",
    region_col: str = None,
    date_col: str = "Month",
    min_periods: int = 3,
) -> pd.DataFrame:
    """
    Runs every detector that the supplied data supports and returns one
    combined dataframe in the unified RESULT_COLUMNS schema:

    - monthly_df (Month + any of Revenue/Profit/Quantity) -> monthly trend
      anomalies for each metric present (covers "Revenue anomalies",
      "Profit anomalies", "Quantity anomalies", "Monthly trend anomalies").
    - detail_df (row-level data, optionally with Product / Region-or-Branch /
      Discount / Month / Revenue columns) -> Product anomalies, Regional
      anomalies (dimension-level, scored on revenue_col), and Discount
      anomalies (row-level IQR, since discounts don't follow a clean
      monthly trend).

    Any piece that isn't present or doesn't have enough data is skipped
    silently rather than raising — callers should treat a missing category
    as "not enough data", not as an error.
    """
    frames = []

    if monthly_df is not None and not monthly_df.empty:
        for col in (revenue_col, profit_col, quantity_col):
            if col in monthly_df.columns:
                frames.append(detect_monthly_anomalies(monthly_df, value_col=col, min_periods=min_periods))

    if detail_df is not None and not detail_df.empty:
        if product_col in detail_df.columns and date_col in detail_df.columns and revenue_col in detail_df.columns:
            dim_df = detail_df.rename(columns={date_col: "Month"}) if date_col != "Month" else detail_df
            frames.append(detect_dimension_anomalies(
                dim_df, dim=product_col, value_col=revenue_col,
                anomaly_type="Product (Revenue)", min_periods=min_periods,
            ))

        region_candidate = region_col
        if region_candidate is None:
            for candidate in ("Region", "Branch"):
                if candidate in detail_df.columns:
                    region_candidate = candidate
                    break
        if region_candidate and region_candidate in detail_df.columns and date_col in detail_df.columns and revenue_col in detail_df.columns:
            dim_df = detail_df.rename(columns={date_col: "Month"}) if date_col != "Month" else detail_df
            frames.append(detect_dimension_anomalies(
                dim_df, dim=region_candidate, value_col=revenue_col,
                anomaly_type="Regional (Revenue)", min_periods=min_periods,
            ))

        if discount_col in detail_df.columns:
            frames.append(detect_iqr_outliers(
                detail_df, value_col=discount_col, anomaly_type="Discount",
                area_col=product_col if product_col in detail_df.columns else region_candidate,
                date_col=date_col,
            ))

    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return _empty_result()
    return pd.concat(frames, ignore_index=True)[RESULT_COLUMNS]


# ------------------------------------------------------------------
# Summary & risk exposure
# ------------------------------------------------------------------

def anomaly_alert_summary(*frames) -> dict:
    """
    Combines any number of anomaly result dataframes (or a single combined
    one) into a High/Medium/Low severity count summary. Accepts either
    several dataframe arguments or one dataframe, for compatibility with
    both single-detector and run_anomaly_scan() output.
    """
    all_frames = []
    for f in frames:
        if f is None:
            continue
        if isinstance(f, dict):
            all_frames.extend(v for v in f.values() if v is not None and not v.empty)
        elif not f.empty:
            all_frames.append(f)

    if not all_frames:
        return {"Total": 0, "High": 0, "Medium": 0, "Low": 0}

    all_sev = pd.concat([f["Severity"] for f in all_frames], ignore_index=True)
    counts = all_sev.value_counts().to_dict()
    return {
        "Total": int(len(all_sev)),
        "High": int(counts.get("High", 0)),
        "Medium": int(counts.get("Medium", 0)),
        "Low": int(counts.get("Low", 0)),
    }


def anomaly_summary(combined: pd.DataFrame) -> dict:
    """
    Full summary for a combined RESULT_COLUMNS dataframe (e.g. from
    run_anomaly_scan): total + severity breakdown + per-metric counts.
    Metric buckets are inferred from the "Anomaly Type" label, since
    Product/Regional anomalies are themselves revenue-based.
    """
    if combined is None or combined.empty:
        return {
            "Total": 0, "High": 0, "Medium": 0, "Low": 0,
            "Revenue anomalies": 0, "Profit anomalies": 0,
            "Quantity anomalies": 0, "Discount anomalies": 0,
        }

    sev_counts = combined["Severity"].value_counts().to_dict()
    types = combined["Anomaly Type"].astype(str)

    return {
        "Total": int(len(combined)),
        "High": int(sev_counts.get("High", 0)),
        "Medium": int(sev_counts.get("Medium", 0)),
        "Low": int(sev_counts.get("Low", 0)),
        "Revenue anomalies": int(types.str.contains("Revenue", case=False).sum()),
        "Profit anomalies": int(types.str.contains("Profit", case=False).sum()),
        "Quantity anomalies": int(types.str.contains("Quantity", case=False).sum()),
        "Discount anomalies": int(types.str.contains("Discount", case=False).sum()),
    }


def calculate_risk_exposure(combined: pd.DataFrame) -> dict:
    """
    Estimates Revenue at risk / Profit at risk from anomaly deviations.

    Methodology: only downside deviations (Actual below Expected) on
    Revenue-related or Profit-related anomalies are summed — an upside
    surprise isn't "at risk", and non-monetary anomaly types (e.g. Discount)
    aren't included since summing them as dollar risk would be misleading.

    Returns None for a risk figure when there's no revenue/profit anomaly
    data to compute it from at all (as opposed to 0, which means anomalies
    were found but none represented downside exposure).
    """
    if combined is None or combined.empty:
        return {"revenue_at_risk": None, "profit_at_risk": None}

    types = combined["Anomaly Type"].astype(str)

    def _downside_sum(mask: pd.Series):
        subset = combined[mask]
        if subset.empty:
            return None
        downside = subset[subset["Deviation"] < 0]["Deviation"]
        return float(downside.abs().sum()) if not downside.empty else 0.0

    revenue_mask = types.str.contains("Revenue", case=False)
    profit_mask = types.str.contains("Profit", case=False)

    return {
        "revenue_at_risk": _downside_sum(revenue_mask),
        "profit_at_risk": _downside_sum(profit_mask),
    }