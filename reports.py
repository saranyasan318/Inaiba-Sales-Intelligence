"""
INAIBA - Reports Module
========================

Builds downloadable CSV/Excel exports and structured report dataframes for
the INAIBA Sales Intelligence & Forecasting application.

This module is responsible ONLY for:
    - Preparing report data (as pandas DataFrames / dicts)
    - Creating downloadable report files (CSV / Excel bytes)
    - Formatting report content (numbers, filenames, metadata)
    - Preparing executive, KPI, sales, product, regional, forecast,
      anomaly, business-insights and data-quality report content
    - Preparing dataset exports (original / cleaned / filtered)

It does NOT contain Streamlit page layout, navigation, or widgets, and it
does NOT duplicate business calculations already implemented in
analytics.py, forecasting.py, anomaly_detection.py, data_validator.py or
insights.py — it calls into those modules and formats their output.

Architecture:

    app.py
      -> reports.py
           -> analytics.py / forecasting.py / anomaly_detection.py /
              data_validator.py / data_cleaner.py / insights.py

Never crashes the app if a report can't be built: every public function
returns either plain data (DataFrame/bytes) for the simple, original
helpers, or a status dict (see report_status()) for the newer, richer
report builders, so app.py always has something safe to check and show.
"""

import io
import re
from datetime import datetime

import numpy as np
import pandas as pd


# ============================================================
# OPTIONAL BACKEND MODULE IMPORTS
#
# Imported defensively so that reports.py (and anything that
# imports it) never fails to load just because one backend
# module is temporarily missing or broken.
# ============================================================

try:
    import analytics as an
except Exception:
    an = None

try:
    import forecasting as fc
except Exception:
    fc = None

try:
    import anomaly_detection as ad
except Exception:
    ad = None

try:
    import insights as ins
except Exception:
    ins = None

try:
    import data_validator
except Exception:
    data_validator = None

try:
    import data_cleaner
except Exception:
    data_cleaner = None


# ============================================================
# REPORT FILE NAMES
# ============================================================

REPORT_FILENAMES = {
    "executive": "INAIBA_Executive_Report",
    "kpi": "INAIBA_KPI_Report",
    "sales_performance": "INAIBA_Sales_Performance",
    "product_category": "INAIBA_Product_Category_Report",
    "regional": "INAIBA_Regional_Report",
    "forecast": "INAIBA_Forecast_Report",
    "anomaly_risk": "INAIBA_Anomaly_Risk_Report",
    "business_insights": "INAIBA_Business_Insights",
    "data_quality": "INAIBA_Data_Quality_Report",
    "clean_dataset": "INAIBA_Clean_Dataset",
    "filtered_dataset": "INAIBA_Filtered_Dataset",
    "original_dataset": "INAIBA_Original_Dataset",
}

_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\s]+')


def _safe_filename_component(text) -> str:
    """Sanitize a string for safe use inside a filename."""

    if not text:
        return ""

    text = str(text).strip()
    text = _ILLEGAL_FILENAME_CHARS.sub("_", text)
    text = re.sub(r"_+", "_", text).strip("_")

    return text


def build_filename(report_type: str, dataset_name: str = None, extension: str = "csv") -> str:
    """Build a clean, safe filename for a given report type.

    report_type may be a key from REPORT_FILENAMES or any free-text label.
    """

    base = REPORT_FILENAMES.get(
        report_type,
        _safe_filename_component(report_type) or "INAIBA_Report",
    )

    if dataset_name:
        suffix = _safe_filename_component(dataset_name)
        if suffix:
            base = f"{base}_{suffix}"

    extension = (extension or "csv").lstrip(".")

    return f"{base}.{extension}"


# ============================================================
# STATUS / METADATA HELPERS
# ============================================================

def report_status(
    success: bool,
    report_type: str = None,
    filename: str = None,
    record_count: int = None,
    error: str = None,
    data=None,
) -> dict:
    """Standard status envelope returned by the richer report builders.

    app.py can safely check `.get("success")` and display `.get("error")`
    without needing to know the internals of each report.
    """

    return {
        "success": bool(success),
        "report_type": report_type,
        "filename": filename,
        "record_count": record_count,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "data": data,
    }


def build_report_metadata(
    df: pd.DataFrame,
    dataset_name: str = None,
    filters: dict = None,
    analysis_period: str = None,
) -> dict:
    """Build a metadata block for inclusion in report headers/sheets.

    Never fabricates values: if information is unavailable it is simply
    omitted or set to a neutral fallback.
    """

    if df is not None and isinstance(df, pd.DataFrame):
        record_count = len(df)
        column_count = len(df.columns)
    else:
        record_count = 0
        column_count = 0

    metadata = {
        "Dataset Name": dataset_name or "INAIBA Analysis",
        "Generated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Analysis Period": analysis_period or "All Available Periods",
        "Number of Records": record_count,
        "Number of Columns": column_count,
    }

    if filters:
        applied = {
            str(key): str(value)
            for key, value in filters.items()
            if value not in (None, "", [], {})
        }

        if applied:
            metadata["Applied Filters"] = "; ".join(
                f"{key}: {value}" for key, value in applied.items()
            )

    return metadata


def metadata_to_dataframe(metadata: dict) -> pd.DataFrame:
    """Turn a flat metadata dict into a two-column DataFrame for export."""

    if not metadata:
        return pd.DataFrame(columns=["Field", "Value"])

    return pd.DataFrame(
        [{"Field": key, "Value": value} for key, value in metadata.items()]
    )


def _try(func, *args, **kwargs):
    """Call func defensively.

    Returns (result, error_message). Never raises — callers decide what to
    do with a None result / non-None error, so failures are always visible
    to the caller instead of being silently swallowed.
    """

    if func is None:
        return None, "The required backend function is unavailable."

    try:
        return func(*args, **kwargs), None
    except (KeyError, ValueError, TypeError, AttributeError, IndexError, ZeroDivisionError) as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 - last resort, still captured & surfaced
        return None, str(exc)


# ============================================================
# NUMBER / DATAFRAME CLEANING
# ============================================================

def _clean_numeric(value):
    """Replace NaN/inf/-inf with None; pass through everything else."""

    if value is None:
        return None

    if isinstance(value, (int, np.integer)):
        return int(value)

    if isinstance(value, (float, np.floating)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)

    return value


def clean_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN/inf/-inf with safe blank values and drop the index.

    Preserves numeric dtypes where possible (uses pandas NA rather than
    stringifying every value) so exported numbers stay usable as numbers.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    cleaned = df.copy()

    numeric_columns = cleaned.select_dtypes(include=[np.number]).columns

    if len(numeric_columns) > 0:
        cleaned[numeric_columns] = cleaned[numeric_columns].replace(
            [np.inf, -np.inf], np.nan
        )

    cleaned = cleaned.reset_index(drop=True)

    return cleaned


def format_percentage_columns(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Format the given numeric columns as consistent 'xx.x%' strings.

    Leaves missing/invalid values as a safe blank rather than 'nan%'.
    """

    if df is None or df.empty:
        return df

    formatted = df.copy()

    for column in columns:
        if column not in formatted.columns:
            continue

        formatted[column] = pd.to_numeric(
            formatted[column], errors="coerce"
        ).map(lambda value: f"{value:.1f}%" if pd.notna(value) else "")

    return formatted


def format_currency_columns(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Format the given numeric columns as consistent currency strings."""

    if df is None or df.empty:
        return df

    formatted = df.copy()

    for column in columns:
        if column not in formatted.columns:
            continue

        formatted[column] = pd.to_numeric(
            formatted[column], errors="coerce"
        ).map(lambda value: f"${value:,.2f}" if pd.notna(value) else "")

    return formatted


# ============================================================
# CORE CSV / EXCEL EXPORT (preserved public API)
# ============================================================

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to UTF-8 CSV bytes, no index column.

    Safe on None / empty DataFrames — returns b"" rather than raising, and
    replaces NaN/inf with blank values so downstream tools never see them.
    """

    try:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return b""

        cleaned = clean_dataframe_for_export(df)

        return cleaned.to_csv(index=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeEncodeError):
        return b""
    except Exception:
        return b""


def df_to_excel_bytes(sheets: dict) -> bytes:
    """sheets: dict of sheet_name -> DataFrame.

    Tries xlsxwriter first (existing project dependency); falls back to
    openpyxl if xlsxwriter is unavailable, so Excel export degrades
    gracefully rather than breaking CSV export elsewhere in the app.
    """

    if not sheets:
        return b""

    buffer = io.BytesIO()

    for engine in ("xlsxwriter", "openpyxl"):

        buffer.seek(0)
        buffer.truncate(0)

        try:
            with pd.ExcelWriter(buffer, engine=engine) as writer:

                sheet_written = False

                for name, sheet_df in sheets.items():

                    if sheet_df is None or not isinstance(sheet_df, pd.DataFrame):
                        continue

                    if sheet_df.empty:
                        continue

                    cleaned = clean_dataframe_for_export(sheet_df)
                    safe_name = _safe_filename_component(name)[:31] or "Sheet"

                    cleaned.to_excel(writer, index=False, sheet_name=safe_name)
                    sheet_written = True

                if not sheet_written:
                    return b""

            return buffer.getvalue()

        except ImportError:
            # This engine isn't installed — try the next one.
            continue
        except (ValueError, TypeError):
            return b""
        except Exception:
            return b""

    return b""


def build_management_excel_report(
    cleaned_df,
    monthly_df,
    perf_tables: dict,
    forecast_table,
    anomalies_df,
    quality: dict,
    insights_df: pd.DataFrame = None,
    kpi_table: pd.DataFrame = None,
    dataset_name: str = None,
    filters: dict = None,
) -> bytes:
    """Build the full multi-sheet management workbook.

    Signature is backward compatible with the original six positional
    arguments — the four new arguments are optional and simply add extra
    sheets (Executive Summary, KPIs, Insights) when supplied.
    """

    sheets = {}

    metadata = build_report_metadata(cleaned_df, dataset_name=dataset_name, filters=filters)
    sheets["Executive Summary"] = metadata_to_dataframe(metadata)

    if kpi_table is not None and isinstance(kpi_table, pd.DataFrame) and not kpi_table.empty:
        sheets["KPIs"] = kpi_table

    if monthly_df is not None and isinstance(monthly_df, pd.DataFrame) and not monthly_df.empty:
        sheets["Monthly Performance"] = monthly_df

    if perf_tables:
        for name, perf_df in perf_tables.items():
            if perf_df is not None and isinstance(perf_df, pd.DataFrame) and not perf_df.empty:
                sheets[f"{name} Performance"] = perf_df

    if forecast_table is not None and isinstance(forecast_table, pd.DataFrame) and not forecast_table.empty:
        sheets["Forecast"] = forecast_table

    if anomalies_df is not None and isinstance(anomalies_df, pd.DataFrame) and not anomalies_df.empty:
        sheets["Anomalies"] = anomalies_df

    if insights_df is not None and isinstance(insights_df, pd.DataFrame) and not insights_df.empty:
        sheets["Insights"] = insights_df

    if quality:
        sheets["Data Quality"] = pd.DataFrame([quality])

    return df_to_excel_bytes(sheets)


# ============================================================
# DATASET EXPORTS
# ============================================================

def export_original_dataset(df: pd.DataFrame) -> dict:
    """Prepare the original (pre-cleaning) dataset for download."""

    return _export_dataset(df, "original_dataset")


def export_clean_dataset(df: pd.DataFrame) -> dict:
    """Prepare the cleaned dataset for download."""

    return _export_dataset(df, "clean_dataset")


def export_filtered_dataset(df: pd.DataFrame, filters: dict = None) -> dict:
    """Prepare the currently-filtered dataset for download.

    Uses exactly the dataframe passed in — never silently substitutes the
    original/unfiltered dataset.
    """

    status = _export_dataset(df, "filtered_dataset")

    if status["success"] and filters:
        status["filters"] = {
            str(key): str(value)
            for key, value in filters.items()
            if value not in (None, "", [], {})
        }

    return status


def _export_dataset(df: pd.DataFrame, report_key: str) -> dict:

    filename = build_filename(report_key, extension="csv")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type=report_key,
            filename=filename,
            record_count=0,
            error="No data is available to export.",
        )

    csv_bytes = df_to_csv_bytes(df)

    if not csv_bytes:
        return report_status(
            False,
            report_type=report_key,
            filename=filename,
            record_count=len(df),
            error="The dataset could not be converted to CSV.",
        )

    return report_status(
        True,
        report_type=report_key,
        filename=filename,
        record_count=len(df),
        data=csv_bytes,
    )


# ============================================================
# KPI REPORT
# ============================================================

def build_kpi_report(df: pd.DataFrame, previous_df: pd.DataFrame = None) -> dict:
    """Build a Metric / Current Value / Previous Value / Change / Change %
    table using analytics.py — never recalculates KPIs manually.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type="kpi",
            filename=build_filename("kpi", extension="csv"),
            record_count=0,
            error="No data is available for a KPI report.",
        )

    if an is None:
        return report_status(
            False,
            report_type="kpi",
            error="The analytics module is unavailable.",
        )

    metric_functions = {
        "Revenue": "total_revenue",
        "Average Order Value": "average_order_value",
        "Orders": "total_orders",
        "Revenue Growth %": "revenue_growth_pct",
    }

    rows = []

    for label, func_name in metric_functions.items():

        func = getattr(an, func_name, None)

        current_value, error = _try(func, df)

        previous_value = None
        if previous_df is not None and not previous_df.empty:
            previous_value, _ = _try(func, previous_df)

        current_value = _clean_numeric(current_value)
        previous_value = _clean_numeric(previous_value)

        change = None
        change_pct = None

        if current_value is not None and previous_value not in (None, 0):
            change = current_value - previous_value
            change_pct = (change / previous_value) * 100

        rows.append({
            "Metric": label,
            "Current Value": current_value if current_value is not None else "",
            "Previous Value": previous_value if previous_value is not None else "",
            "Change": _clean_numeric(change) if change is not None else "",
            "Change %": f"{change_pct:.1f}%" if change_pct is not None else "",
        })

    table = pd.DataFrame(rows)

    return report_status(
        True,
        report_type="kpi",
        filename=build_filename("kpi", extension="csv"),
        record_count=len(table),
        data=table,
    )


# ============================================================
# SALES PERFORMANCE REPORT
# ============================================================

def build_sales_performance_report(df: pd.DataFrame) -> dict:
    """Build Monthly / Category / Segment / Discount performance tables."""

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type="sales_performance",
            error="No data is available for a sales performance report.",
        )

    if an is None:
        return report_status(
            False,
            report_type="sales_performance",
            error="The analytics module is unavailable.",
        )

    sheets = {}

    monthly, error = _try(an.monthly_revenue, df)
    if isinstance(monthly, pd.DataFrame) and not monthly.empty:
        sheets["Monthly Performance"] = clean_dataframe_for_export(monthly)

    for dimension, sheet_name in [
        ("Category", "Category Performance"),
        ("Segment", "Segment Performance"),
        ("Discount", "Discount Performance"),
    ]:

        if dimension not in df.columns:
            continue

        performance, error = _try(an.performance_by, df, dimension)

        if isinstance(performance, pd.DataFrame) and not performance.empty:
            sheets[sheet_name] = clean_dataframe_for_export(performance)

    if not sheets:
        return report_status(
            False,
            report_type="sales_performance",
            error="No sales performance data could be calculated for this dataset.",
        )

    return report_status(
        True,
        report_type="sales_performance",
        filename=build_filename("sales_performance", extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values()),
        data=sheets,
    )


# ============================================================
# PRODUCT & CATEGORY REPORT
# ============================================================

def build_product_category_report(df: pd.DataFrame) -> dict:
    """Build Category / Product performance tables plus top / loss-making
    / high-revenue-low-profit product views, where the columns exist."""

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type="product_category",
            error="No data is available for a product & category report.",
        )

    if an is None:
        return report_status(
            False,
            report_type="product_category",
            error="The analytics module is unavailable.",
        )

    sheets = {}

    for dimension, sheet_name in [
        ("Category", "Category Report"),
        ("Product", "Product Report"),
    ]:

        if dimension not in df.columns:
            continue

        performance, error = _try(an.performance_by, df, dimension)

        if not isinstance(performance, pd.DataFrame) or performance.empty:
            continue

        sheets[sheet_name] = clean_dataframe_for_export(performance)

        if dimension == "Product":

            if "Revenue" in performance.columns:
                sheets["Top Products"] = clean_dataframe_for_export(
                    performance.sort_values("Revenue", ascending=False).head(10)
                )

            profit_column = next(
                (c for c in ["Profit", "Total Profit"] if c in performance.columns),
                None,
            )

            if profit_column:
                loss_making = performance[
                    pd.to_numeric(performance[profit_column], errors="coerce") < 0
                ]

                if not loss_making.empty:
                    sheets["Loss-Making Products"] = clean_dataframe_for_export(loss_making)

            margin_column = next(
                (c for c in ["Margin %", "Profit Margin", "Margin"] if c in performance.columns),
                None,
            )

            if "Revenue" in performance.columns and margin_column:
                median_revenue = pd.to_numeric(performance["Revenue"], errors="coerce").median()
                median_margin = pd.to_numeric(performance[margin_column], errors="coerce").median()

                high_rev_low_profit = performance[
                    (pd.to_numeric(performance["Revenue"], errors="coerce") >= median_revenue)
                    & (pd.to_numeric(performance[margin_column], errors="coerce") < median_margin)
                ]

                if not high_rev_low_profit.empty:
                    sheets["High-Revenue Low-Profit Products"] = clean_dataframe_for_export(
                        high_rev_low_profit
                    )

    if not sheets:
        return report_status(
            False,
            report_type="product_category",
            error="No product or category columns were detected in this dataset.",
        )

    return report_status(
        True,
        report_type="product_category",
        filename=build_filename("product_category", extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values()),
        data=sheets,
    )


# ============================================================
# REGIONAL REPORT
# ============================================================

def build_regional_report(df: pd.DataFrame) -> dict:
    """Build Region / State / City / Branch performance tables — only for
    dimensions that actually exist in the dataset."""

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type="regional",
            error="No data is available for a regional report.",
        )

    if an is None:
        return report_status(
            False,
            report_type="regional",
            error="The analytics module is unavailable.",
        )

    sheets = {}

    for dimension in ["Region", "State", "City", "Branch"]:

        if dimension not in df.columns:
            continue

        performance, error = _try(an.performance_by, df, dimension)

        if isinstance(performance, pd.DataFrame) and not performance.empty:
            sheets[f"{dimension} Performance"] = clean_dataframe_for_export(performance)

    if not sheets:
        return report_status(
            False,
            report_type="regional",
            error="No Region, State, City or Branch columns were detected in this dataset.",
        )

    return report_status(
        True,
        report_type="regional",
        filename=build_filename("regional", extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values()),
        data=sheets,
    )


# ============================================================
# FORECAST REPORT
# ============================================================

def build_forecast_report(forecast_result) -> dict:
    """Format an existing forecasting.py result into a report.

    forecast_result is whatever fc.generate_forecast(...) already returned
    — this function only formats it; it never predicts anything itself.
    """

    if not forecast_result:
        return report_status(
            False,
            report_type="forecast",
            error="No forecast has been generated yet.",
        )

    if not isinstance(forecast_result, dict):
        return report_status(
            False,
            report_type="forecast",
            error="The forecast result is not in a recognized format.",
        )

    summary = {
        "Forecast Metric": forecast_result.get("metric") or forecast_result.get("target"),
        "Forecast Horizon": forecast_result.get("horizon"),
        "Selected Model": forecast_result.get("model") or forecast_result.get("selected_model"),
        "Accuracy": forecast_result.get("accuracy"),
        "Expected Growth": forecast_result.get("growth") or forecast_result.get("expected_growth"),
    }

    summary = {key: _clean_numeric(value) if isinstance(value, (int, float, np.floating, np.integer)) else value
               for key, value in summary.items()}

    sheets = {"Forecast Summary": metadata_to_dataframe(summary)}

    forecast_table = (
        forecast_result.get("table")
        or forecast_result.get("forecast_table")
        or forecast_result.get("forecast")
    )

    if isinstance(forecast_table, pd.DataFrame) and not forecast_table.empty:
        sheets["Forecast Table"] = clean_dataframe_for_export(forecast_table)

    comparison_table = (
        forecast_result.get("model_comparison")
        or forecast_result.get("comparison")
    )

    if isinstance(comparison_table, pd.DataFrame) and not comparison_table.empty:
        sheets["Model Comparison"] = clean_dataframe_for_export(comparison_table)

    return report_status(
        True,
        report_type="forecast",
        filename=build_filename("forecast", extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values()),
        data=sheets,
    )


# ============================================================
# ANOMALY & RISK REPORT
# ============================================================

def build_anomaly_report(anomalies_df: pd.DataFrame, alert_summary: dict = None) -> dict:
    """Format existing anomaly_detection.py output into a report.

    Does not implement a second anomaly algorithm — anomalies_df and
    alert_summary must already come from anomaly_detection.py.
    """

    if anomalies_df is None or not isinstance(anomalies_df, pd.DataFrame) or anomalies_df.empty:
        return report_status(
            True,
            report_type="anomaly_risk",
            filename=build_filename("anomaly_risk", extension="xlsx"),
            record_count=0,
            data={"Anomaly Summary": metadata_to_dataframe({"Total Anomalies": 0})},
        )

    sheets = {}

    summary = alert_summary if isinstance(alert_summary, dict) else {}
    summary = dict(summary)
    summary.setdefault("Total Anomalies", len(anomalies_df))

    if "Severity" in anomalies_df.columns:
        severity_counts = anomalies_df["Severity"].value_counts().to_dict()
        for severity, count in severity_counts.items():
            summary.setdefault(f"{severity} Severity", count)

    sheets["Anomaly Summary"] = metadata_to_dataframe(summary)
    sheets["Anomaly Detail"] = clean_dataframe_for_export(anomalies_df)

    return report_status(
        True,
        report_type="anomaly_risk",
        filename=build_filename("anomaly_risk", extension="xlsx"),
        record_count=len(anomalies_df),
        data=sheets,
    )


# ============================================================
# BUSINESS INSIGHTS REPORT
# ============================================================

def build_business_insights_report(insights_data) -> dict:
    """Format existing insights.py output into an exportable table.

    insights_data must already come from insights.py (e.g.
    ins.build_all_insights(df)) — this function only formats it.
    """

    if not insights_data:
        return report_status(
            False,
            report_type="business_insights",
            error="No insights are available for this dataset.",
        )

    records = insights_data

    if isinstance(insights_data, pd.DataFrame):
        records = insights_data.to_dict(orient="records")

    if not isinstance(records, (list, tuple)):
        return report_status(
            False,
            report_type="business_insights",
            error="The insights result is not in a recognized format.",
        )

    rows = []

    for item in records:

        if not isinstance(item, dict):
            continue

        rows.append({
            "Category": item.get("category") or item.get("Category", ""),
            "Title": item.get("title") or item.get("Title", ""),
            "Evidence": item.get("evidence") or item.get("Evidence", ""),
            "Observation": item.get("observation") or item.get("Observation", ""),
            "Interpretation": item.get("interpretation") or item.get("Interpretation", ""),
            "Business Impact": item.get("business_impact") or item.get("Business Impact", ""),
            "Recommended Action": item.get("recommended_action") or item.get("Recommended Action", ""),
            "Priority": item.get("priority") or item.get("Priority", ""),
        })

    if not rows:
        return report_status(
            False,
            report_type="business_insights",
            error="No structured insights could be formatted for this dataset.",
        )

    table = pd.DataFrame(rows)

    return report_status(
        True,
        report_type="business_insights",
        filename=build_filename("business_insights", extension="xlsx"),
        record_count=len(table),
        data=table,
    )


# ============================================================
# DATA QUALITY REPORT
# ============================================================

_QUALITY_WEIGHTS = {
    "completeness": 0.30,
    "validity": 0.25,
    "consistency": 0.20,
    "uniqueness": 0.15,
    "outlier_health": 0.10,
}


def build_column_quality_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a Column / Data Type / Missing Count / Missing % / Unique
    Count table directly from a dataframe."""

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(
            columns=["Column", "Data Type", "Missing Count", "Missing %", "Unique Count"]
        )

    total_rows = len(df)
    rows = []

    for column in df.columns:

        missing = int(df[column].isna().sum())
        missing_pct = (missing / total_rows * 100) if total_rows > 0 else 0
        unique = int(df[column].nunique(dropna=True))

        rows.append({
            "Column": str(column),
            "Data Type": str(df[column].dtype),
            "Missing Count": missing,
            "Missing %": round(missing_pct, 1),
            "Unique Count": unique,
        })

    return pd.DataFrame(rows)


def _composite_quality_score(quality_report: dict) -> float:
    """Combine already-computed data_validator fields into one score.

    This is presentation-layer arithmetic on values data_validator.py
    already calculated (completeness_pct, error_rate_pct, etc.) — it does
    not re-implement any validation logic.
    """

    completeness = _clean_numeric(quality_report.get("completeness_pct")) or 0
    error_rate = _clean_numeric(quality_report.get("error_rate_pct")) or 0
    validity = max(0.0, 100.0 - error_rate)

    rows = _clean_numeric(quality_report.get("rows")) or 0
    duplicates = _clean_numeric(quality_report.get("duplicate_records")) or 0
    consistency = max(0.0, 100.0 - ((duplicates / rows) * 100 if rows else 0))

    invalid_dates = _clean_numeric(quality_report.get("invalid_dates")) or 0
    invalid_numeric = _clean_numeric(quality_report.get("invalid_numeric_values")) or 0
    uniqueness = max(0.0, 100.0 - (((invalid_dates + invalid_numeric) / rows) * 100 if rows else 0))

    outlier_health = _clean_numeric(quality_report.get("outlier_health_pct"))
    if outlier_health is None:
        outlier_health = 100.0

    return (
        completeness * _QUALITY_WEIGHTS["completeness"]
        + validity * _QUALITY_WEIGHTS["validity"]
        + consistency * _QUALITY_WEIGHTS["consistency"]
        + uniqueness * _QUALITY_WEIGHTS["uniqueness"]
        + outlier_health * _QUALITY_WEIGHTS["outlier_health"]
    )


def build_data_quality_report(
    quality_report: dict,
    column_quality_df: pd.DataFrame = None,
    cleaning_report: dict = None,
    df: pd.DataFrame = None,
) -> dict:
    """Build Quality Summary / Column Quality / Cleaning Summary sheets.

    quality_report should come from data_validator.assess_quality(); if
    column_quality_df is not supplied but df is, it is computed directly.
    Never re-implements validation or cleaning logic.
    """

    if not quality_report and (df is None or df.empty):
        return report_status(
            False,
            report_type="data_quality",
            error="No data quality information is available.",
        )

    quality_report = quality_report or {}

    score = _composite_quality_score(quality_report) if quality_report else None

    quality_summary = {
        "Quality Score": round(score, 1) if score is not None else "",
        "Status": quality_report.get("reliability_status", ""),
        "Completeness": quality_report.get("completeness_pct", ""),
        "Duplicate Records": quality_report.get("duplicate_records", ""),
        "Invalid Dates": quality_report.get("invalid_dates", ""),
        "Invalid Numeric Values": quality_report.get("invalid_numeric_values", ""),
        "Negative/Invalid Sales": quality_report.get("negative_or_invalid_sales", ""),
        "Error Rate %": quality_report.get("error_rate_pct", ""),
    }

    sheets = {"Quality Summary": metadata_to_dataframe(quality_summary)}

    if column_quality_df is None and df is not None:
        column_quality_df = build_column_quality_table(df)

    if isinstance(column_quality_df, pd.DataFrame) and not column_quality_df.empty:
        sheets["Column Quality"] = clean_dataframe_for_export(column_quality_df)

    if isinstance(cleaning_report, dict) and cleaning_report:

        cleaning_rows = [
            {
                "Issue": "Missing Values",
                "Detected": cleaning_report.get("missing_values_handled", 0),
                "Fixed": cleaning_report.get("missing_values_handled", 0),
                "Remaining": 0,
                "Status": "Resolved",
            },
            {
                "Issue": "Duplicate Records",
                "Detected": cleaning_report.get("duplicates_handled", 0),
                "Fixed": cleaning_report.get("duplicates_handled", 0),
                "Remaining": 0,
                "Status": "Resolved",
            },
            {
                "Issue": "Invalid Records",
                "Detected": cleaning_report.get("invalid_records_flagged", 0),
                "Fixed": cleaning_report.get("rows_repaired", 0),
                "Remaining": max(
                    0,
                    (cleaning_report.get("invalid_records_flagged", 0) or 0)
                    - (cleaning_report.get("rows_repaired", 0) or 0),
                ),
                "Status": (
                    "Resolved"
                    if (cleaning_report.get("invalid_records_flagged", 0) or 0)
                    <= (cleaning_report.get("rows_repaired", 0) or 0)
                    else "Partially Resolved"
                ),
            },
        ]

        sheets["Cleaning Summary"] = pd.DataFrame(cleaning_rows)

    return report_status(
        True,
        report_type="data_quality",
        filename=build_filename("data_quality", extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values()),
        data=sheets,
    )


# ============================================================
# EXECUTIVE REPORT
# ============================================================

def build_executive_report(
    df: pd.DataFrame,
    dataset_name: str = None,
    filters: dict = None,
    analysis_period: str = None,
    forecast_result: dict = None,
    anomalies_df: pd.DataFrame = None,
    alert_summary: dict = None,
    quality_report: dict = None,
    insights_data=None,
) -> dict:
    """Assemble the full Executive Report from every available section.

    Every section is optional — only what is actually available and
    calculable is included; nothing unsupported is fabricated.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return report_status(
            False,
            report_type="executive",
            error="No data is available for an executive report.",
        )

    sheets = {}

    metadata = build_report_metadata(
        df, dataset_name=dataset_name, filters=filters, analysis_period=analysis_period
    )

    if an is not None:
        for label, func_name in [
            ("Revenue", "total_revenue"),
            ("Average Order Value", "average_order_value"),
            ("Orders", "total_orders"),
            ("Revenue Growth %", "revenue_growth_pct"),
        ]:
            func = getattr(an, func_name, None)
            value, error = _try(func, df)
            value = _clean_numeric(value)
            if value is not None:
                metadata[label] = value

    sheets["Executive Summary"] = metadata_to_dataframe(metadata)

    # Business performance
    performance_status = build_sales_performance_report(df)
    if performance_status["success"]:
        sheets.update(performance_status["data"])

    product_status = build_product_category_report(df)
    if product_status["success"] and "Category Report" in product_status["data"]:
        sheets["Category Report"] = product_status["data"]["Category Report"]
    if product_status["success"] and "Product Report" in product_status["data"]:
        sheets["Product Report"] = product_status["data"]["Product Report"]

    regional_status = build_regional_report(df)
    if regional_status["success"]:
        sheets.update(regional_status["data"])

    # Business insights
    if insights_data:
        insights_status = build_business_insights_report(insights_data)
        if insights_status["success"]:
            sheets["Business Insights"] = insights_status["data"]

    # Forecast summary
    if forecast_result:
        forecast_status = build_forecast_report(forecast_result)
        if forecast_status["success"]:
            for name, sheet in forecast_status["data"].items():
                sheets[f"Forecast — {name}"] = sheet

    # Data quality
    if quality_report:
        quality_status = build_data_quality_report(quality_report, df=df)
        if quality_status["success"]:
            sheets["Data Quality Summary"] = quality_status["data"].get("Quality Summary")

    # Risks / anomalies
    if anomalies_df is not None and isinstance(anomalies_df, pd.DataFrame) and not anomalies_df.empty:
        anomaly_status = build_anomaly_report(anomalies_df, alert_summary=alert_summary)
        if anomaly_status["success"]:
            sheets["Anomaly Summary"] = anomaly_status["data"].get("Anomaly Summary")

    sheets = {name: sheet for name, sheet in sheets.items() if sheet is not None}

    return report_status(
        True,
        report_type="executive",
        filename=build_filename("executive", dataset_name=dataset_name, extension="xlsx"),
        record_count=sum(len(sheet) for sheet in sheets.values() if isinstance(sheet, pd.DataFrame)),
        data=sheets,
    )


def build_executive_excel_report(*args, **kwargs) -> bytes:
    """Convenience wrapper: build_executive_report(...) -> Excel bytes."""

    status = build_executive_report(*args, **kwargs)

    if not status["success"]:
        return b""

    return df_to_excel_bytes(status["data"])