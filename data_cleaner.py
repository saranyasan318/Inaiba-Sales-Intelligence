"""
INAIBA - Data Cleaning Pipeline
A safe, reusable cleaning layer: cleans uploaded datasets without destroying
useful business information. Every operation that changes or flags data is
counted and recorded in the returned report / cleaning log — nothing is
silently modified or silently dropped.

No Streamlit UI and no chart creation here — this module only returns
dataframes / dicts for app.py to render.
"""

import numpy as np
import pandas as pd

NUMERIC_FIELDS = ["Revenue", "Quantity", "Price", "Cost", "Profit", "Margin", "Discount", "Target"]
TEXT_FIELDS = ["Product", "Category", "Region", "Branch", "Customer", "State", "City", "OrderID"]
CATEGORY_LIKE_FIELDS = ["Product", "Category", "Region", "Branch", "State", "City"]  # OrderID/Customer are IDs, not normalized

# Outlier detection: IQR / Tukey fences — the same approach already used
# elsewhere in INAIBA (anomaly_detection.py), preserved here rather than
# introducing a second method.
IQR_MULTIPLIER = 1.5

# A "sale" recorded further in the future than this many days is treated as
# an impossible date rather than a legitimate advance-dated transaction.
FUTURE_DATE_TOLERANCE_DAYS = 1


# ------------------------------------------------------------------
# Individual, independently reusable detectors
# Each is read-only: none of these functions modify the dataframe.
# ------------------------------------------------------------------

def detect_duplicates(df: pd.DataFrame) -> dict:
    """Detects exact duplicate rows. Does not remove anything."""
    if df is None or df.empty:
        return {"detected": 0}
    dup_mask = df.duplicated(keep="first")
    return {"detected": int(dup_mask.sum())}


def detect_missing_values(df: pd.DataFrame) -> dict:
    """Missing-value count per column, for every column that has at least one."""
    if df is None or df.empty:
        return {}
    counts = df.isna().sum()
    return {col: int(n) for col, n in counts.items() if n > 0}


def detect_invalid_dates(df: pd.DataFrame, date_col: str = "Date") -> dict:
    """
    Detects date values that cannot be parsed. Returns whether the column is
    present and how many originally non-null values failed to parse — never
    lets an invalid date propagate into analytics/forecasting as-is.
    """
    if date_col not in df.columns:
        return {"present": False, "invalid_count": 0}
    original_non_null = df[date_col].notna().sum()
    parsed = pd.to_datetime(df[date_col], errors="coerce")
    invalid = int(parsed.notna().sum() * 0 + (original_non_null - parsed.notna().sum()))
    return {"present": True, "invalid_count": max(invalid, 0)}


def _clean_numeric_string(series: pd.Series) -> pd.Series:
    """Strips thousands separators, common currency symbols, and whitespace before numeric conversion."""
    cleaned = series.astype(str)
    for token in (",", "₹", "$", "€", "£", "\u00a0"):
        cleaned = cleaned.str.replace(token, "", regex=False)
    cleaned = cleaned.str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def convert_numeric_columns(df: pd.DataFrame, columns: list = None) -> tuple[pd.DataFrame, dict]:
    """
    Safely converts the given (or default NUMERIC_FIELDS) columns to numbers,
    handling commas/currency symbols/whitespace. Values that still can't be
    parsed become NaN (never crash, never silently coerced to 0) and are
    counted per column so the caller knows what changed.
    """
    columns = columns or [c for c in NUMERIC_FIELDS if c in df.columns]
    work = df.copy()
    issues = {}
    for col in columns:
        if col not in work.columns:
            continue
        before_na = work[col].isna().sum()
        work[col] = _clean_numeric_string(work[col])
        newly_invalid = int(work[col].isna().sum() - before_na)
        if newly_invalid > 0:
            issues[col] = newly_invalid
    return work, issues


def check_category_consistency(df: pd.DataFrame, columns: list = None) -> dict:
    """
    Flags accidental duplicate category labels that differ only by case
    and/or surrounding whitespace (e.g. "North", "north ", "NORTH"). Proposes
    the most frequent original casing as the canonical label for each group.

    Deliberately narrow: only values that are identical once lowercased and
    stripped are grouped. Anything that differs by more than that (e.g.
    "North" vs "North Region") is left alone as a distinct business entity.

    Returns {column: [{"variants": {label: count, ...}, "canonical": label}]}
    """
    columns = columns or [c for c in CATEGORY_LIKE_FIELDS if c in df.columns]
    result = {}
    for col in columns:
        series = df[col].dropna().astype(str).str.strip()
        series = series[series != ""]
        if series.empty:
            continue
        norm_key = series.str.lower()
        flagged = []
        for key, group in series.groupby(norm_key):
            variant_counts = group.value_counts().to_dict()
            if len(variant_counts) > 1:
                canonical = max(variant_counts.items(), key=lambda kv: kv[1])[0]
                flagged.append({"variants": variant_counts, "canonical": canonical})
        if flagged:
            result[col] = flagged
    return result


def check_business_rules(df: pd.DataFrame) -> dict:
    """
    Flags suspicious-but-not-automatically-altered business values:
    negative Revenue, negative Quantity, and dates recorded in the future.
    Flagging only — see clean_dataset() for how these are surfaced (IsReturn
    column, cleaning log) without silently changing the underlying data.
    """
    flags = {}
    if "Revenue" in df.columns:
        flags["negative_revenue"] = int((pd.to_numeric(df["Revenue"], errors="coerce") < 0).sum())
    if "Quantity" in df.columns:
        flags["negative_quantity"] = int((pd.to_numeric(df["Quantity"], errors="coerce") < 0).sum())
    if "Date" in df.columns:
        parsed = pd.to_datetime(df["Date"], errors="coerce")
        cutoff = pd.Timestamp.now().normalize() + pd.Timedelta(days=FUTURE_DATE_TOLERANCE_DAYS)
        flags["future_dates"] = int((parsed.notna() & (parsed > cutoff)).sum())
    return flags


def detect_outliers_iqr(df: pd.DataFrame, columns: list = None) -> dict:
    """
    Detects statistical outliers per numeric column using IQR (Tukey) fences.
    This is detection only — outliers are never removed here, since a
    statistically unusual value (e.g. one very large order) may be a
    legitimate high-value business transaction rather than an error.

    Returns {column: {"count", "lower_bound", "upper_bound"}} for columns
    where an outlier fence could be computed and at least one value falls
    outside it. A column with zero spread (constant/near-constant values)
    is skipped — an IQR of 0 would flag almost every value, which would be
    misleading rather than informative.
    """
    columns = columns or [c for c in NUMERIC_FIELDS if c in df.columns]
    result = {}
    for col in columns:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr
        count = int(((series < lower) | (series > upper)).sum())
        if count > 0:
            result[col] = {"count": count, "lower_bound": float(lower), "upper_bound": float(upper)}
    return result


def normalize_category_consistency(df: pd.DataFrame, consistency_map: dict) -> tuple[pd.DataFrame, dict]:
    """
    Applies the canonical labels proposed by check_category_consistency():
    rewrites case/whitespace variants of the same value to one consistent
    label. Does not touch any column not present in consistency_map, and
    never merges groups that check_category_consistency() didn't already
    identify as the same entity.
    Returns (updated_df, {column: rows_normalized_count}).
    """
    work = df.copy()
    fixed_counts = {}
    for col, groups in consistency_map.items():
        if col not in work.columns:
            continue
        replace_map = {}
        for group in groups:
            for variant in group["variants"]:
                if variant != group["canonical"]:
                    replace_map[variant] = group["canonical"]
        if not replace_map:
            continue
        stripped = work[col].astype(str).str.strip()
        changed_mask = stripped.isin(replace_map.keys())
        fixed_counts[col] = int(changed_mask.sum())
        work.loc[changed_mask, col] = stripped[changed_mask].map(replace_map)
    return work, fixed_counts


def _log_entry(issue: str, detected: int, fixed: int, remaining: int, status: str) -> dict:
    return {"Issue": issue, "Detected": int(detected), "Fixed": int(fixed), "Remaining": int(remaining), "Status": status}


def build_cleaning_log(
    duplicate_detail: dict,
    missing_by_column: dict,
    invalid_dates: dict,
    numeric_issues: dict,
    remaining_numeric_na: dict,
    category_consistency: dict,
    category_fixed: dict,
    business_flags: dict,
    outliers: dict,
    rows_removed_missing_required: int,
) -> list:
    """Assembles every detector's findings into one Issue/Detected/Fixed/Remaining/Status table."""
    log = []

    dup_detected = duplicate_detail.get("detected", 0)
    if dup_detected > 0:
        log.append(_log_entry("Duplicate rows", dup_detected, dup_detected, 0, "Resolved — removed"))

    for col, count in missing_by_column.items():
        log.append(_log_entry(
            f"Missing values — {col}", count, 0, count,
            "Flagged — left as-is; business meaning of a blank varies by column",
        ))

    if invalid_dates.get("present") and invalid_dates.get("invalid_count", 0) > 0:
        n = invalid_dates["invalid_count"]
        fixed = min(n, rows_removed_missing_required)
        log.append(_log_entry("Unparseable dates", n, fixed, max(n - fixed, 0), "Resolved — row excluded" if fixed >= n else "Partially resolved"))

    for col, count in numeric_issues.items():
        remaining = remaining_numeric_na.get(col, 0)
        log.append(_log_entry(
            f"Non-numeric values — {col}", count, 0, remaining,
            "Flagged — converted to missing, not guessed or zero-filled",
        ))

    if business_flags.get("negative_revenue", 0) > 0:
        n = business_flags["negative_revenue"]
        log.append(_log_entry("Negative Revenue values", n, 0, n, "Flagged for review — marked as possible return (IsReturn)"))

    if business_flags.get("negative_quantity", 0) > 0:
        n = business_flags["negative_quantity"]
        log.append(_log_entry("Negative Quantity values", n, 0, n, "Flagged for review — not altered"))

    if business_flags.get("future_dates", 0) > 0:
        n = business_flags["future_dates"]
        log.append(_log_entry("Future-dated records", n, 0, n, "Flagged for review — not altered"))

    for col, groups in category_consistency.items():
        detected = sum(len(g["variants"]) for g in groups)
        fixed = category_fixed.get(col, 0)
        log.append(_log_entry(
            f"Category name variants — {col}", detected, fixed, 0,
            "Resolved — normalized to the most common casing",
        ))

    for col, info in outliers.items():
        log.append(_log_entry(
            f"Statistical outliers — {col}", info["count"], 0, info["count"],
            "Flagged for review — not removed; may be legitimate high-value transactions",
        ))

    return log


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Cleans a mapped (standardized-column) DataFrame.
    Returns (cleaned_df, report). Never raises.

    report keeps its original top-level keys (rows_processed, rows_removed,
    rows_repaired, missing_values_handled, duplicates_handled,
    invalid_records_flagged, notes, final_row_count) for compatibility, and
    adds structured detail: duplicate_detail, missing_values_by_column,
    numeric_conversion_issues, category_consistency, business_rule_flags,
    outliers, and cleaning_log (Issue/Detected/Fixed/Remaining/Status).
    """
    report = {
        "rows_processed": int(len(df)) if df is not None else 0,
        "rows_removed": 0,
        "rows_repaired": 0,
        "missing_values_handled": 0,
        "duplicates_handled": 0,
        "invalid_records_flagged": 0,
        "notes": [],
    }

    if df is None or df.empty:
        report["final_row_count"] = 0
        report["duplicate_detail"] = {"detected": 0, "removed": 0, "remaining": 0}
        report["missing_values_by_column"] = {}
        report["numeric_conversion_issues"] = {}
        report["category_consistency"] = {}
        report["business_rule_flags"] = {}
        report["outliers"] = {}
        report["cleaning_log"] = []
        report["notes"].append("No data provided to clean.")
        return (df.copy() if df is not None else pd.DataFrame()), report

    work = df.copy()

    # ---- Missing values, measured on the data as received ----
    missing_by_column = detect_missing_values(work)
    report["missing_values_by_column"] = missing_by_column

    # ---- Normalize text/whitespace in text columns ----
    for col in TEXT_FIELDS:
        if col in work.columns:
            before_na = work[col].isna().sum()
            work[col] = work[col].astype(str).str.strip()
            work[col] = work[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})
            after_na = work[col].isna().sum()
            report["missing_values_handled"] += int(max(after_na - before_na, 0))

    # ---- Category consistency: fix accidental case/whitespace duplicates only ----
    consistency_map = check_category_consistency(work)
    work, category_fixed = normalize_category_consistency(work, consistency_map)
    report["category_consistency"] = consistency_map
    if consistency_map:
        total_variants = sum(len(g["variants"]) for groups in consistency_map.values() for g in [groups[0]]) if False else \
            sum(len(g["variants"]) for groups in consistency_map.values() for g in groups)
        report["notes"].append(
            f"Normalized case/whitespace category variants in {len(consistency_map)} column(s) "
            f"({total_variants} distinct label variant(s) consolidated)."
        )

    # ---- Date parsing ----
    invalid_dates = detect_invalid_dates(work, "Date")
    if "Date" in work.columns:
        parsed = pd.to_datetime(work["Date"], errors="coerce")
        if invalid_dates["invalid_count"] > 0:
            report["invalid_records_flagged"] += invalid_dates["invalid_count"]
            report["notes"].append(
                f"{invalid_dates['invalid_count']} record(s) had a date that could not be interpreted; "
                f"these are excluded below so they can't silently break time-based analysis."
            )
        work["Date"] = parsed
    else:
        report["notes"].append("No Date column detected. Time-based analysis will be limited.")

    # ---- Numeric conversion ----
    work, numeric_issues = convert_numeric_columns(work)
    for col, newly_invalid in numeric_issues.items():
        report["invalid_records_flagged"] += newly_invalid
        report["notes"].append(f"{newly_invalid} invalid value(s) in '{col}' could not be converted to numbers.")

    # ---- Business-rule flags (negative values, impossible dates) — flagged, not altered ----
    business_flags = check_business_rules(work)
    report["business_rule_flags"] = business_flags

    if "Revenue" in work.columns:
        negative_mask = pd.to_numeric(work["Revenue"], errors="coerce") < 0
        neg_count = business_flags.get("negative_revenue", int(negative_mask.sum()))
        if neg_count > 0:
            report["notes"].append(
                f"{neg_count} record(s) had negative revenue values (possible returns/refunds) and were flagged, not removed."
            )
        work["IsReturn"] = negative_mask

    if business_flags.get("negative_quantity", 0) > 0:
        report["notes"].append(
            f"{business_flags['negative_quantity']} record(s) had negative quantity values and were flagged, not removed."
        )

    if business_flags.get("future_dates", 0) > 0:
        report["notes"].append(
            f"{business_flags['future_dates']} record(s) are dated in the future and were flagged, not removed."
        )

    # ---- Drop rows missing required fields (Date, Revenue) ----
    required_present = [c for c in ["Date", "Revenue"] if c in work.columns]
    rows_removed_missing_required = 0
    if required_present:
        mask_valid = pd.Series(True, index=work.index)
        for c in required_present:
            mask_valid &= work[c].notna()
        removed = int((~mask_valid).sum())
        if removed > 0:
            rows_removed_missing_required = removed
            report["rows_removed"] += removed
            report["notes"].append(
                f"{removed} row(s) removed due to missing required values (Date and/or Revenue)."
            )
        work = work[mask_valid].copy()

    # ---- Duplicate handling (exact duplicates only; reported, not silent) ----
    duplicate_detail = detect_duplicates(work)
    dup_mask = work.duplicated(keep="first")
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        report["duplicates_handled"] = dup_count
        report["notes"].append(f"{dup_count} exact duplicate row(s) removed.")
        work = work[~dup_mask].copy()
    duplicate_detail["removed"] = dup_count
    duplicate_detail["remaining"] = int(work.duplicated(keep="first").sum())
    report["duplicate_detail"] = duplicate_detail

    # ---- Outlier detection: reported only, never removed ----
    outliers = detect_outliers_iqr(work)
    report["outliers"] = outliers
    if outliers:
        cols = ", ".join(outliers.keys())
        report["notes"].append(
            f"Statistical outliers detected in: {cols}. These are flagged for review, not removed — "
            f"a large value may be a legitimate transaction rather than an error."
        )

    # ---- Derived fields ----
    if "Date" in work.columns:
        work["Year"] = work["Date"].dt.year
        work["Month"] = work["Date"].dt.to_period("M").dt.to_timestamp()
        work["MonthLabel"] = work["Date"].dt.strftime("%b %Y")
        work["Quarter"] = work["Date"].dt.to_period("Q").astype(str)
        work["Weekday"] = work["Date"].dt.day_name()

    if "Profit" not in work.columns and "Revenue" in work.columns and "Cost" in work.columns:
        work["Profit"] = work["Revenue"] - work["Cost"]

    if "Margin" not in work.columns and "Profit" in work.columns and "Revenue" in work.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            work["Margin"] = np.where(work["Revenue"] != 0, work["Profit"] / work["Revenue"] * 100, np.nan)

    report["rows_repaired"] = report["missing_values_handled"] + report["invalid_records_flagged"] - report["rows_removed"]
    report["rows_repaired"] = max(report["rows_repaired"], 0)
    report["final_row_count"] = int(len(work))

    # ---- Structured cleaning log (Issue / Detected / Fixed / Remaining / Status) ----
    remaining_numeric_na = {col: int(work[col].isna().sum()) for col in numeric_issues if col in work.columns}
    report["numeric_conversion_issues"] = numeric_issues
    report["cleaning_log"] = build_cleaning_log(
        duplicate_detail=duplicate_detail,
        missing_by_column=missing_by_column,
        invalid_dates=invalid_dates,
        numeric_issues=numeric_issues,
        remaining_numeric_na=remaining_numeric_na,
        category_consistency=consistency_map,
        category_fixed=category_fixed,
        business_flags=business_flags,
        outliers=outliers,
        rows_removed_missing_required=rows_removed_missing_required,
    )

    work = work.reset_index(drop=True)
    return work, report