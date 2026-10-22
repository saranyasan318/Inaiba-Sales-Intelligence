"""
INAIBA - Data Validator / Quality Assessment
Computes transparent, explainable data quality metrics.
"""

import pandas as pd
import numpy as np


def assess_quality(raw: pd.DataFrame, cleaned: pd.DataFrame, cleaning_report: dict) -> dict:
    """
    Produces a data quality summary.
    Completeness % = non-null cells / total cells in the mapped raw dataset.
    Reliability status is derived transparently from completeness + error rates.
    """
    total_rows_raw = int(len(raw))
    total_cols_raw = int(raw.shape[1]) if total_rows_raw else 0
    total_cells = total_rows_raw * total_cols_raw if total_cols_raw else 0
    missing_cells = int(raw.isna().sum().sum()) if total_cells else 0
    completeness = round(100 * (1 - missing_cells / total_cells), 1) if total_cells else 0.0

    duplicate_records = cleaning_report.get("duplicates_handled", 0)
    invalid_dates = sum(1 for n in cleaning_report.get("notes", []) if "date could not be interpreted" in n)
    invalid_numeric = cleaning_report.get("invalid_records_flagged", 0)
    negative_values = sum(1 for n in cleaning_report.get("notes", []) if "negative revenue" in n)

    valid_records = int(len(cleaned))

    error_rate = 0.0
    if total_rows_raw:
        error_rate = round(
            100 * (cleaning_report.get("rows_removed", 0) + cleaning_report.get("invalid_records_flagged", 0))
            / total_rows_raw,
            1,
        )

    # Transparent reliability scoring
    if completeness >= 95 and error_rate <= 2:
        status = "Reliable"
    elif completeness >= 85 and error_rate <= 10:
        status = "Acceptable"
    elif completeness >= 60:
        status = "Limited Reliability"
    else:
        status = "Low Reliability"

    return {
        "rows": total_rows_raw,
        "columns": total_cols_raw,
        "valid_records": valid_records,
        "missing_values": missing_cells,
        "duplicate_records": duplicate_records,
        "invalid_dates": invalid_dates,
        "invalid_numeric_values": invalid_numeric,
        "negative_or_invalid_sales": negative_values,
        "completeness_pct": completeness,
        "error_rate_pct": error_rate,
        "reliability_status": status,
    }


def sufficient_for_forecasting(cleaned: pd.DataFrame, min_months: int = 4) -> tuple[bool, str]:
    """Checks whether there is enough historical data for a meaningful forecast."""
    if "Month" not in cleaned.columns or cleaned.empty:
        return False, "No usable date information is available for forecasting."
    n_months = cleaned["Month"].nunique()
    if n_months < min_months:
        return False, (
            f"Only {n_months} month(s) of history are available. "
            f"At least {min_months} months are recommended for a reliable forecast."
        )
    return True, ""
