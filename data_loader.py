"""
INAIBA - Data Loader
Handles file ingestion, column-name cleanup, and best-effort business
column detection / mapping.

This module is deliberately scoped to *loading*: it reads a CSV/Excel
file safely, tidies up the raw column names, and proposes a mapping
from canonical business fields (Date, Revenue, Product, ...) to
whatever the file actually calls them. It exposes a couple of
never-raise helpers (`safe_to_datetime`, `clean_numeric_series`) for
sniffing/validating column content, but the actual type conversion of
the working dataset is left to data_cleaner.py, which needs the raw
mapped values to do that job.
"""

import re
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# Canonical field -> list of accepted raw-name fragments
# (lowercased, normalized to snake_case)
#
# These are common business-report naming patterns, not a fixed
# schema — detection also falls back to sniffing column content, so
# a file that doesn't use any of these words can still be mapped.
# ------------------------------------------------------------------

COLUMN_SYNONYMS = {
    "Date": [
        "date", "sales_date", "transaction_date", "order_date",
        "invoice_date", "orderdate", "ship_date", "shipdate",
    ],
    "Revenue": [
        "revenue", "sales", "amount", "sales_amount", "total_sales",
        "total_revenue", "net_sales", "salesvalue", "sale_amount",
        "grand_total", "sales_value",
    ],
    "Profit": [
        "profit", "net_profit", "gross_profit", "total_profit",
    ],
    "Quantity": [
        "quantity", "qty", "units", "unit_sold", "units_sold",
        "order_quantity",
    ],
    "OrderID": [
        "order_id", "orderid", "invoice_id", "invoice_no",
        "transaction_id", "order_no", "order_number",
    ],
    "CustomerID": [
        "customer_id", "customerid", "client_id", "cust_id",
        "buyer_id",
    ],
    "Customer": [
        "customer", "customer_name", "client", "buyer",
        "client_name", "account_name",
    ],
    "Product": [
        "product", "product_name", "item", "item_name", "sku_name",
        "productname",
    ],
    "Category": [
        "category", "product_category", "product_type",
    ],
    "Sub-Category": [
        "sub_category", "subcategory", "sub_cat",
        "product_subcategory", "subcat",
    ],
    "Region": [
        "region", "area", "territory", "zone", "sales_region",
    ],
    "Branch": [
        "branch", "location", "outlet", "store",
    ],
    "State": [
        "state", "province",
    ],
    "City": [
        "city", "town",
    ],
    "Segment": [
        "segment", "customer_segment", "market_segment",
    ],
    "Discount": [
        "discount", "discount_pct", "discount_percentage", "disc",
        "discount_rate",
    ],
    "Price": [
        "price", "unit_price", "sale_price",
    ],
    "Cost": [
        "cost", "unit_cost", "total_cost", "cogs",
    ],
    "Margin": [
        "margin", "profit_margin", "margin_pct",
    ],
    "Target": [
        "target", "goal", "sales_target", "quota",
    ],
}

# Fields that must be detected for the dataset to be usable at all.
REQUIRED_FIELDS = ["Date", "Revenue"]

# Fields that aren't strictly required but meaningfully improve the
# analysis if present.
RECOMMENDED_FIELDS = ["Quantity", "Product", "Category", "Region"]

# Fields expected to hold numeric values, used by the content-sniffing
# fallback pass and available for callers that want to know which
# mapped columns are safe to run clean_numeric_series() on.
NUMERIC_FIELDS = [
    "Revenue", "Profit", "Quantity", "Price", "Cost", "Margin",
    "Target", "Discount",
]

# Fields treated as categorical "dimensions" for grouping/breakdown,
# as opposed to metrics, dates, or identifiers.
DIMENSION_FIELDS = [
    "Product", "Category", "Sub-Category", "Region", "State", "City",
    "Segment", "Branch", "Customer",
]


# ============================================================
# COLUMN NAME NORMALIZATION
# ============================================================

def _normalize(name: str) -> str:
    """Normalize a column name for matching purposes only (does not
    change the actual DataFrame column names)."""
    text = str(name).strip().lower()
    text = re.sub(r"[\s\-\.]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _clean_label(label) -> str:
    """Tidy a column name for display/use: trims stray whitespace and
    collapses repeated internal spaces, without altering casing or
    wording so the original business meaning is preserved."""
    text = str(label).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else "Column"


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a copy of df with cleaned column names: whitespace trimmed,
    repeated spaces collapsed. Any names that collide after cleaning
    (e.g. "Sales" and "Sales ") are disambiguated with a suffix so no
    column is silently dropped or overwritten.
    """
    cleaned = [_clean_label(c) for c in df.columns]

    seen = {}
    final_names = []
    for name in cleaned:
        key = name.lower()
        if key not in seen:
            seen[key] = 1
            final_names.append(name)
        else:
            seen[key] += 1
            final_names.append(f"{name} ({seen[key]})")

    out = df.copy()
    out.columns = final_names
    return out


# ============================================================
# FILE LOADING
# ============================================================

def load_raw_file(uploaded_file):
    """
    Read an uploaded CSV/Excel file into a raw DataFrame.

    Supports .csv, .xlsx, and .xls. If the extension is missing or
    unrecognized, both readers are tried before giving up. Never
    raises to the UI: always returns (DataFrame, None) on success or
    (None, error_message) on failure.
    """
    if uploaded_file is None:
        return None, "No file was provided."

    name = getattr(uploaded_file, "name", "") or ""
    name_lower = name.lower()

    is_csv = name_lower.endswith(".csv")
    is_excel = name_lower.endswith((".xlsx", ".xls"))

    raw = None
    last_error = None

    try:
        if is_csv:
            raw = pd.read_csv(uploaded_file)

        elif is_excel:
            raw = pd.read_excel(uploaded_file)

        else:
            # Unknown/missing extension: sniff by trying CSV then
            # Excel, rather than assuming.
            try:
                uploaded_file.seek(0)
            except Exception:
                pass

            try:
                raw = pd.read_csv(uploaded_file)
            except Exception as csv_err:
                last_error = csv_err
                raw = None

                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass

                try:
                    raw = pd.read_excel(uploaded_file)
                except Exception as excel_err:
                    last_error = excel_err
                    raw = None

    except pd.errors.EmptyDataError:
        return None, "The uploaded file appears to be empty."

    except pd.errors.ParserError:
        return None, (
            "The CSV file could not be parsed. Please check that it "
            "is a valid, well-formed CSV export."
        )

    except UnicodeDecodeError:
        return None, (
            "The file's text encoding could not be read. Please "
            "re-save it as UTF-8 CSV or a standard Excel file."
        )

    except ValueError as e:
        # Common failure mode for corrupted/unsupported Excel files.
        return None, f"The Excel file could not be read. ({e})"

    except Exception as e:
        return None, (
            "The file could not be read. Please upload a valid CSV "
            f"or Excel file. ({type(e).__name__})"
        )

    if raw is None:
        detail = f" ({type(last_error).__name__})" if last_error else ""
        return None, (
            "Unsupported file type. Please upload a CSV or Excel "
            f"(.xlsx/.xls) file.{detail}"
        )

    if raw.shape[1] == 0:
        return None, "The uploaded file has no columns."

    if raw.shape[0] == 0:
        return None, "The uploaded file appears to be empty."

    raw = clean_columns(raw)

    return raw, None


# ============================================================
# CONTENT SNIFFING (safe, never raises)
# ============================================================

_CURRENCY_CHARS = re.compile(r"[₹$€£¥%,\s]")
_PAREN_NEGATIVE = re.compile(r"^\((.*)\)$")


def _numeric_success_ratio(series: pd.Series, sample_size: int = 200) -> float:
    """Fraction of non-null values that look like clean numbers once
    currency symbols, thousands separators, percent signs, and stray
    whitespace are stripped out. Used only to help detect likely
    numeric columns — never mutates the source data."""
    if series is None or series.empty:
        return 0.0

    sample = series.dropna()
    if sample.empty:
        return 0.0

    if len(sample) > sample_size:
        sample = sample.sample(sample_size, random_state=0)

    if pd.api.types.is_numeric_dtype(sample):
        return 1.0

    try:
        cleaned = sample.astype(str).str.strip()
        cleaned = cleaned.str.replace(_CURRENCY_CHARS, "", regex=True)
        cleaned = cleaned.str.replace(_PAREN_NEGATIVE, r"-\1", regex=True)
        parsed = pd.to_numeric(cleaned, errors="coerce")
    except Exception:
        return 0.0

    return float(parsed.notna().sum()) / float(len(sample))


def _date_success_ratio(series: pd.Series, sample_size: int = 200) -> float:
    """Fraction of non-null values that parse as valid dates. Used
    only to help detect likely date columns — never mutates the
    source data."""
    if series is None or series.empty:
        return 0.0

    sample = series.dropna()
    if sample.empty:
        return 0.0

    if len(sample) > sample_size:
        sample = sample.sample(sample_size, random_state=0)

    try:
        parsed = pd.to_datetime(sample, errors="coerce")
    except Exception:
        return 0.0

    return float(parsed.notna().sum()) / float(len(sample))


def safe_to_datetime(series: pd.Series) -> pd.Series:
    """
    Best-effort, never-raising conversion of a column to datetime.
    Values that cannot be parsed become NaT instead of crashing the
    app. Intended for validation/preview use; data_cleaner.py owns
    the authoritative conversion of the working dataset.
    """
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.Series([pd.NaT] * len(series), index=series.index)


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """
    Best-effort, never-raising conversion of a column to numeric.
    Tolerates currency symbols, thousands separators, percent signs,
    stray whitespace, and parenthesised negatives (e.g. "(1,234.50)").
    Values that still don't look numeric become NaN rather than
    raising or silently mangling a text column.
    """
    if series is None:
        return series

    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)

    try:
        cleaned = series.astype(str).str.strip()
        cleaned = cleaned.str.replace(_CURRENCY_CHARS, "", regex=True)
        cleaned = cleaned.str.replace(_PAREN_NEGATIVE, r"-\1", regex=True)
        return pd.to_numeric(cleaned, errors="coerce")
    except Exception:
        return pd.Series([float("nan")] * len(series), index=series.index)


# ============================================================
# COLUMN MAPPING DETECTION
# ============================================================

def detect_column_mapping(raw: pd.DataFrame) -> dict:
    """
    Returns dict: canonical_field -> detected raw column name (or
    None). Detection runs in three passes, each only considering raw
    columns not already claimed by an earlier match, so the same
    column is never assigned to two different fields:

      1. Exact normalized name match (e.g. "Order Date" -> Date).
      2. Substring name match, as a looser fallback.
      3. Content sniffing (dates/numbers), for columns whose name
         gave no hint at all — this is what lets the detector work
         on files that don't use any recognizable naming convention.

    Low-confidence matches are still returned for user review via
    render_mapping_editor / mapping_confidence.
    """
    normalized_cols = {col: _normalize(col) for col in raw.columns}
    mapping = {canonical: None for canonical in COLUMN_SYNONYMS}
    used_columns = set()

    # Pass 1: exact normalized match.
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        for raw_col, norm in normalized_cols.items():
            if raw_col in used_columns:
                continue
            if norm in synonyms:
                mapping[canonical] = raw_col
                used_columns.add(raw_col)
                break

    # Pass 2: substring match fallback.
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        if mapping[canonical] is not None:
            continue
        for raw_col, norm in normalized_cols.items():
            if raw_col in used_columns:
                continue
            if any(syn in norm for syn in synonyms):
                mapping[canonical] = raw_col
                used_columns.add(raw_col)
                break

    # Pass 3: content sniffing for anything still unresolved.
    remaining_cols = [c for c in raw.columns if c not in used_columns]

    if remaining_cols:
        if mapping.get("Date") is None:
            best_col, best_ratio = None, 0.0
            for raw_col in remaining_cols:
                ratio = _date_success_ratio(raw[raw_col])
                if ratio > best_ratio:
                    best_col, best_ratio = raw_col, ratio
            if best_col is not None and best_ratio >= 0.8:
                mapping["Date"] = best_col
                used_columns.add(best_col)
                remaining_cols = [c for c in remaining_cols if c != best_col]

        for canonical in NUMERIC_FIELDS:
            if mapping.get(canonical) is not None or not remaining_cols:
                continue
            best_col, best_ratio = None, 0.0
            for raw_col in remaining_cols:
                ratio = _numeric_success_ratio(raw[raw_col])
                if ratio > best_ratio:
                    best_col, best_ratio = raw_col, ratio
            if best_col is not None and best_ratio >= 0.85:
                mapping[canonical] = best_col
                used_columns.add(best_col)
                remaining_cols = [c for c in remaining_cols if c != best_col]

    return mapping


def mapping_confidence(mapping: dict) -> str:
    """Simple qualitative confidence label based on required fields detected."""
    missing_required = [f for f in REQUIRED_FIELDS if not mapping.get(f)]
    if not missing_required:
        return "High"
    if "Revenue" in missing_required:
        return "Low"
    return "Medium"


def validate_mapping(mapping: dict) -> dict:
    """
    Returns a small, never-raising validation report:

        {
            "is_valid": bool,
            "missing_required": [...],
            "missing_recommended": [...],
        }

    is_valid is False only when a REQUIRED_FIELDS entry (Date or
    Revenue) is missing; missing recommended fields are surfaced as
    warnings rather than failures.
    """
    missing_required = [f for f in REQUIRED_FIELDS if not mapping.get(f)]
    missing_recommended = [
        f for f in RECOMMENDED_FIELDS
        if f not in REQUIRED_FIELDS and not mapping.get(f)
    ]

    return {
        "is_valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }


def apply_mapping(raw: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Build a standardized DataFrame using only the mapped canonical columns that were found."""
    df = pd.DataFrame(index=raw.index)
    for canonical, raw_col in mapping.items():
        if raw_col is not None and raw_col in raw.columns:
            df[canonical] = raw[raw_col]
    return df


# ============================================================
# DATASET METADATA
# ============================================================

def get_dataset_metadata(
    df: pd.DataFrame,
    mapping: dict,
    filename: str = None,
) -> dict:
    """
    Read-only summary of what was loaded and detected. Does not
    mutate df or mapping.
    """
    dimensions = [f for f in DIMENSION_FIELDS if mapping.get(f)]

    return {
        "filename": filename,
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": list(df.columns),
        "detected_date_column": mapping.get("Date"),
        "detected_revenue_column": mapping.get("Revenue"),
        "detected_profit_column": mapping.get("Profit"),
        "detected_quantity_column": mapping.get("Quantity"),
        "detected_dimensions": dimensions,
    }


# ============================================================
# MAPPING REVIEW UI
# ============================================================

def render_mapping_editor(raw: pd.DataFrame, mapping: dict) -> dict:
    """Streamlit UI letting the user confirm/correct the detected mapping. Returns final mapping."""
    st.caption("Review the automatically detected column mapping. Correct any field below if needed.")
    cols_available = ["(Not in dataset)"] + list(raw.columns)
    final_mapping = {}

    field_cols = st.columns(3)
    for i, canonical in enumerate(COLUMN_SYNONYMS.keys()):
        detected = mapping.get(canonical)
        default_index = cols_available.index(detected) if detected in cols_available else 0
        with field_cols[i % 3]:
            choice = st.selectbox(
                canonical,
                options=cols_available,
                index=default_index,
                key=f"mapcol_{canonical}",
            )
        final_mapping[canonical] = None if choice == "(Not in dataset)" else choice

    return final_mapping