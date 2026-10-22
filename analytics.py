

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# Internal safety helpers
# ------------------------------------------------------------------

def _numeric(df: pd.DataFrame, col: str):
    """Coerced numeric Series for `col`, or None if df/col is unavailable.
    Non-numeric values become NaN rather than raising or silently
    corrupting the column."""
    if df is None or df.empty or col not in df.columns:
        return None
    return pd.to_numeric(df[col], errors="coerce")


def _ratio_or_zero(numerator, denominator) -> float:
    """numerator / denominator, or 0.0 if denominator is 0/None/NaN."""
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return 0.0
    if numerator is None or pd.isna(numerator):
        return 0.0
    return float(numerator) / float(denominator)


def _pct_change(current, previous):
    """(current - previous) / previous * 100, or None if undefined
    (no prior value, prior value is zero, or either value is missing)."""
    if previous is None or previous == 0 or pd.isna(previous):
        return None
    if current is None or pd.isna(current):
        return None
    return float((current - previous) / previous * 100)


def _period_series(df: pd.DataFrame, freq: str):
    """Safe Date -> pandas Period conversion for grouping
    (freq: 'M', 'Q', 'Y'). Returns None if Date is missing or entirely
    unparseable; invalid individual dates become NaT and are dropped
    by the caller rather than crashing the aggregation."""
    if df is None or df.empty or "Date" not in df.columns:
        return None
    parsed = pd.to_datetime(df["Date"], errors="coerce")
    if parsed.isna().all():
        return None
    return parsed.dt.to_period(freq)


def _aggregate_by(df: pd.DataFrame, key, label_name: str) -> pd.DataFrame:
    """
    Shared aggregation engine behind every time-based performance
    table (monthly / quarterly / yearly). `key` must be a Series of
    grouping labels aligned to df's index (e.g. from _period_series).

    Produces whichever of Revenue / Profit / Quantity / Orders / AOV /
    Margin % / *_Growth % columns can actually be computed from the
    columns present in df, sorted chronologically by the underlying
    key, with a clean positional index (no leftover group index).
    """
    if df is None or df.empty or key is None:
        return pd.DataFrame()

    valid = key.notna()
    if not valid.any():
        return pd.DataFrame()

    work = df.loc[valid].copy()
    work["_key"] = key.loc[valid]

    agg = {}
    if "Revenue" in work.columns:
        work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
        agg["Revenue"] = "sum"
    if "Profit" in work.columns:
        work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")
        agg["Profit"] = "sum"
    if "Quantity" in work.columns:
        work["Quantity"] = pd.to_numeric(work["Quantity"], errors="coerce")
        agg["Quantity"] = "sum"

    if not agg:
        return pd.DataFrame()

    result = work.groupby("_key").agg(agg)

    if "OrderID" in work.columns:
        result["Orders"] = work.groupby("_key")["OrderID"].nunique()
    else:
        result["Orders"] = work.groupby("_key").size()

    result = result.sort_index()

    if "Revenue" in result.columns:
        result["AOV"] = np.where(result["Orders"] > 0, result["Revenue"] / result["Orders"], 0.0)

    if "Profit" in result.columns and "Revenue" in result.columns:
        result["Margin %"] = np.where(result["Revenue"] != 0, result["Profit"] / result["Revenue"] * 100, np.nan)

    if "Revenue" in result.columns:
        result["Revenue Growth %"] = result["Revenue"].pct_change() * 100
    if "Profit" in result.columns:
        result["Profit Growth %"] = result["Profit"].pct_change() * 100
    if "Quantity" in result.columns:
        result["Quantity Growth %"] = result["Quantity"].pct_change() * 100
    result["Order Growth %"] = result["Orders"].pct_change() * 100

    result = result.reset_index().rename(columns={"_key": label_name})
    result[label_name] = result[label_name].astype(str)
    return result


def _growth_by_dimension(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    """Splits the date range into two halves and computes % growth of
    revenue per group within `dim`. Returns an empty frame (no
    "Growth %" column) if Date isn't usable."""
    if df is None or df.empty or "Date" not in df.columns or dim not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame({"Growth %": []})

    dates = pd.to_datetime(df["Date"], errors="coerce")
    if dates.isna().all():
        return pd.DataFrame({"Growth %": []})

    dmin, dmax = dates.min(), dates.max()
    if pd.isna(dmin) or pd.isna(dmax) or dmin == dmax:
        return pd.DataFrame({"Growth %": []})

    work = df.copy()
    work["_date"] = dates
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")

    midpoint = dmin + (dmax - dmin) / 2
    first_half = work[work["_date"] <= midpoint].groupby(dim)["Revenue"].sum()
    second_half = work[work["_date"] > midpoint].groupby(dim)["Revenue"].sum()

    growth = pd.DataFrame({"Prior": first_half, "Recent": second_half}).fillna(0)
    growth["Growth %"] = np.where(
        growth["Prior"] > 0,
        (growth["Recent"] - growth["Prior"]) / growth["Prior"] * 100,
        np.nan,
    )
    return growth[["Growth %"]]


# ------------------------------------------------------------------
# Core KPI functions
# ------------------------------------------------------------------

def total_revenue(df: pd.DataFrame) -> float:
    s = _numeric(df, "Revenue")
    return float(s.sum()) if s is not None else 0.0


def total_profit(df: pd.DataFrame) -> float:
    s = _numeric(df, "Profit")
    return float(s.sum()) if s is not None else 0.0


def profit_margin(df: pd.DataFrame) -> float:
    """Total profit as a percentage of total revenue. 0.0 if either
    column is missing or revenue is zero."""
    revenue = total_revenue(df)
    if not revenue:
        return 0.0
    return float(total_profit(df) / revenue * 100)


def total_orders(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    if "OrderID" in df.columns:
        return int(df["OrderID"].nunique())
    return int(len(df))


def total_quantity(df: pd.DataFrame) -> float:
    s = _numeric(df, "Quantity")
    if s is not None:
        return float(s.sum())
    return float(len(df)) if df is not None else 0.0


def average_order_value(df: pd.DataFrame) -> float:
    return _ratio_or_zero(total_revenue(df), total_orders(df))


def revenue_growth_pct(df: pd.DataFrame):
    """Latest month-over-month revenue growth %, or None if there's
    insufficient monthly history."""
    perf = monthly_performance(df)
    if len(perf) < 2 or "Revenue Growth %" not in perf.columns:
        return None
    val = perf["Revenue Growth %"].iloc[-1]
    return float(val) if pd.notna(val) else None


def profit_growth_pct(df: pd.DataFrame):
    """Latest month-over-month profit growth %, or None if there's
    insufficient monthly history or Profit isn't tracked."""
    perf = monthly_performance(df)
    if len(perf) < 2 or "Profit Growth %" not in perf.columns:
        return None
    val = perf["Profit Growth %"].iloc[-1]
    return float(val) if pd.notna(val) else None


def order_growth_pct(df: pd.DataFrame):
    """Latest month-over-month order-count growth %, or None if
    there's insufficient monthly history."""
    perf = monthly_performance(df)
    if len(perf) < 2 or "Order Growth %" not in perf.columns:
        return None
    val = perf["Order Growth %"].iloc[-1]
    return float(val) if pd.notna(val) else None


def quantity_growth_pct(df: pd.DataFrame):
    """Latest month-over-month quantity growth %, or None if there's
    insufficient monthly history or Quantity isn't tracked."""
    perf = monthly_performance(df)
    if len(perf) < 2 or "Quantity Growth %" not in perf.columns:
        return None
    val = perf["Quantity Growth %"].iloc[-1]
    return float(val) if pd.notna(val) else None


# ------------------------------------------------------------------
# Time analytics
# ------------------------------------------------------------------

def monthly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per calendar month, sorted chronologically, with whichever
    of Revenue / Profit / Quantity / Orders / AOV / Margin % / growth
    columns can be computed from the columns present. Derived
    directly from Date, so it does not depend on any pre-existing
    Month column.
    """
    key = _period_series(df, "M")
    return _aggregate_by(df, key, "Month") if key is not None else pd.DataFrame()


def quarterly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Same shape as monthly_performance, aggregated by quarter."""
    key = _period_series(df, "Q")
    return _aggregate_by(df, key, "Quarter") if key is not None else pd.DataFrame()


def yearly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Same shape as monthly_performance, aggregated by year."""
    key = _period_series(df, "Y")
    return _aggregate_by(df, key, "Year") if key is not None else pd.DataFrame()


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy-compatible monthly table: Month, Revenue, Orders, Quantity,
    AOV, Growth %. Kept for callers written against the original
    analytics.py; monthly_performance() is the richer version.
    """
    cols = ["Month", "Revenue", "Orders", "Quantity", "AOV", "Growth %"]
    perf = monthly_performance(df)
    if perf.empty or "Revenue" not in perf.columns:
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame({"Month": perf["Month"]})
    out["Revenue"] = perf["Revenue"]
    out["Orders"] = perf["Orders"] if "Orders" in perf.columns else 0
    out["Quantity"] = perf["Quantity"] if "Quantity" in perf.columns else np.nan
    out["AOV"] = perf["AOV"] if "AOV" in perf.columns else 0.0
    out["Growth %"] = perf["Revenue Growth %"] if "Revenue Growth %" in perf.columns else np.nan
    return out


def average_monthly_revenue(df: pd.DataFrame) -> float:
    m = monthly_revenue(df)
    return float(m["Revenue"].mean()) if not m.empty else 0.0


def period_comparison(df: pd.DataFrame, value_col: str = "Revenue"):
    """
    Compares the most recent month vs the prior month for a given
    numeric column (Revenue, Profit, Quantity, Orders, AOV, ...).
    Returns (current_value, previous_value, pct_change); the latter
    two are None when there isn't a prior month to compare against.
    """
    perf = monthly_performance(df)

    if perf.empty or value_col not in perf.columns:
        fallback = {
            "Revenue": total_revenue,
            "Profit": total_profit,
            "Quantity": total_quantity,
        }.get(value_col)
        return (fallback(df) if fallback else None), None, None

    if len(perf) == 1:
        val = perf[value_col].iloc[-1]
        return (float(val) if pd.notna(val) else None), None, None

    current = perf[value_col].iloc[-1]
    previous = perf[value_col].iloc[-2]
    current = float(current) if pd.notna(current) else None
    previous = float(previous) if pd.notna(previous) else None
    pct = _pct_change(current, previous)
    return current, previous, pct


def yoy_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy-compatible Year / Revenue / Growth % table, derived from Date."""
    cols = ["Year", "Revenue", "Growth %"]
    perf = yearly_performance(df)
    if perf.empty or "Revenue" not in perf.columns:
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame({"Year": perf["Year"], "Revenue": perf["Revenue"]})
    out["Growth %"] = perf["Revenue Growth %"] if "Revenue Growth %" in perf.columns else np.nan
    return out


def daily_revenue(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["Date", "Revenue"]
    if df is None or df.empty or "Date" not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame(columns=cols)

    dates = pd.to_datetime(df["Date"], errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return pd.DataFrame(columns=cols)

    work = pd.DataFrame({
        "Date": dates[valid].dt.date,
        "Revenue": pd.to_numeric(df.loc[valid, "Revenue"], errors="coerce"),
    })
    return work.groupby("Date")["Revenue"].sum().reset_index()


def weekly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["Week", "Revenue"]
    if df is None or df.empty or "Date" not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame(columns=cols)

    dates = pd.to_datetime(df["Date"], errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return pd.DataFrame(columns=cols)

    work = pd.DataFrame({
        "Week": dates[valid].dt.to_period("W").dt.start_time,
        "Revenue": pd.to_numeric(df.loc[valid, "Revenue"], errors="coerce"),
    })
    return work.groupby("Week")["Revenue"].sum().reset_index()


def year_month_comparison(df: pd.DataFrame, value_col: str = "Revenue") -> pd.DataFrame:
    """
    Pivot of value_col by Year (rows) x calendar month (columns, Jan-Dec),
    useful for year-over-year seasonality comparisons. Empty if Date
    or value_col is unavailable.
    """
    if df is None or df.empty or "Date" not in df.columns or value_col not in df.columns:
        return pd.DataFrame()

    dates = pd.to_datetime(df["Date"], errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return pd.DataFrame()

    work = pd.DataFrame({
        "Year": dates[valid].dt.year,
        "MonthName": dates[valid].dt.strftime("%b"),
        "Value": pd.to_numeric(df.loc[valid, value_col], errors="coerce"),
    })

    pivot = work.pivot_table(index="Year", columns="MonthName", values="Value", aggfunc="sum", fill_value=0)
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ordered_cols = [m for m in month_order if m in pivot.columns]
    return pivot[ordered_cols]


def seasonality_index(df: pd.DataFrame, value_col: str = "Revenue") -> pd.DataFrame:
    """
    Average value_col by calendar month across all years present,
    expressed as an index where 100 = the overall monthly average.
    Values above 100 are seasonally strong months, below 100 are weak.
    """
    cols = ["Month", f"Avg {value_col}", "Seasonality Index"]
    if df is None or df.empty or "Date" not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=cols)

    dates = pd.to_datetime(df["Date"], errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return pd.DataFrame(columns=cols)

    work = pd.DataFrame({
        "MonthNum": dates[valid].dt.month,
        "MonthName": dates[valid].dt.strftime("%b"),
        "Value": pd.to_numeric(df.loc[valid, value_col], errors="coerce"),
    })

    monthly_avg = work.groupby(["MonthNum", "MonthName"])["Value"].mean().reset_index()
    monthly_avg = monthly_avg.sort_values("MonthNum")

    overall_avg = work["Value"].mean()
    if overall_avg and pd.notna(overall_avg) and overall_avg != 0:
        monthly_avg["Seasonality Index"] = monthly_avg["Value"] / overall_avg * 100
    else:
        monthly_avg["Seasonality Index"] = np.nan

    out = monthly_avg[["MonthName", "Value", "Seasonality Index"]].rename(
        columns={"MonthName": "Month", "Value": f"Avg {value_col}"}
    ).reset_index(drop=True)
    return out


# ------------------------------------------------------------------
# Generic grouped performance (Category / Sub-Category / Product /
# Region / State / City / Segment / Branch / Customer / ...)
# ------------------------------------------------------------------

def performance_by(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    """
    Generic performance table for any dimension column. Includes
    whichever of Revenue / Profit / Margin % / Quantity / Orders /
    AOV / Contribution % / Growth % can be computed from the columns
    actually present, sorted by Revenue descending with a clean
    positional index.
    """
    if df is None or df.empty or dim not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")

    agg = {"Revenue": "sum"}
    if "Profit" in work.columns:
        work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")
        agg["Profit"] = "sum"
    if "Quantity" in work.columns:
        work["Quantity"] = pd.to_numeric(work["Quantity"], errors="coerce")
        agg["Quantity"] = "sum"

    base = work.groupby(dim).agg(agg)

    if "OrderID" in work.columns:
        base["Orders"] = work.groupby(dim)["OrderID"].nunique()
    else:
        base["Orders"] = work.groupby(dim).size()

    base["AOV"] = np.where(base["Orders"] > 0, base["Revenue"] / base["Orders"], 0.0)

    if "Profit" in base.columns:
        base["Margin %"] = np.where(base["Revenue"] != 0, base["Profit"] / base["Revenue"] * 100, np.nan)

    total = base["Revenue"].sum()
    base["Contribution %"] = np.where(total > 0, base["Revenue"] / total * 100, 0.0)

    growth = _growth_by_dimension(df, dim)
    if not growth.empty:
        base = base.merge(growth, left_index=True, right_index=True, how="left")

    base = base.reset_index().sort_values("Revenue", ascending=False).reset_index(drop=True)
    return base


def top_performer(df: pd.DataFrame, dim: str):
    perf = performance_by(df, dim)
    if perf.empty:
        return None
    return str(perf.iloc[0][dim])


def fastest_growing(df: pd.DataFrame, dim: str, min_revenue_share: float = 1.0):
    """Fastest-growing entity within a dimension, filtering out negligible-revenue noise."""
    perf = performance_by(df, dim)
    if perf.empty or "Growth %" not in perf.columns:
        return None
    filtered = perf[(perf["Contribution %"] >= min_revenue_share) & perf["Growth %"].notna()]
    if filtered.empty:
        return None
    filtered = filtered.sort_values("Growth %", ascending=False)
    return str(filtered.iloc[0][dim])


def weakest_performer(df: pd.DataFrame, dim: str, min_revenue_share: float = 1.0):
    perf = performance_by(df, dim)
    if perf.empty or "Growth %" not in perf.columns:
        return None
    filtered = perf[(perf["Contribution %"] >= min_revenue_share) & perf["Growth %"].notna()]
    if filtered.empty:
        return None
    filtered = filtered.sort_values("Growth %", ascending=True)
    return str(filtered.iloc[0][dim])


# ------------------------------------------------------------------
# Category analytics
# ------------------------------------------------------------------

def category_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "Category")


def subcategory_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "Sub-Category")


# ------------------------------------------------------------------
# Product analytics
# ------------------------------------------------------------------

def product_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "Product")


def top_products(df: pd.DataFrame, n: int = 10, by: str = "Revenue") -> pd.DataFrame:
    perf = product_performance(df)
    if perf.empty or by not in perf.columns:
        return pd.DataFrame()
    return perf.sort_values(by, ascending=False).head(n).reset_index(drop=True)


def loss_making_products(df: pd.DataFrame, n: int = None) -> pd.DataFrame:
    """Products with negative total profit, worst first. Empty if Profit isn't tracked."""
    perf = product_performance(df)
    if perf.empty or "Profit" not in perf.columns:
        return pd.DataFrame()
    losses = perf[perf["Profit"] < 0].sort_values("Profit").reset_index(drop=True)
    return losses.head(n) if n else losses


def high_revenue_low_profit_products(
    df: pd.DataFrame,
    revenue_percentile: float = 0.75,
    margin_threshold: float = 10.0,
) -> pd.DataFrame:
    """
    Products in the top `revenue_percentile` of revenue whose margin %
    is below `margin_threshold` -- big sellers that aren't actually
    profitable. Empty if Profit isn't tracked.
    """
    perf = product_performance(df)
    if perf.empty or "Margin %" not in perf.columns:
        return pd.DataFrame()
    cutoff = perf["Revenue"].quantile(revenue_percentile)
    flagged = perf[(perf["Revenue"] >= cutoff) & (perf["Margin %"] < margin_threshold)]
    return flagged.sort_values("Revenue", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------
# Regional analytics
# ------------------------------------------------------------------

def region_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "Region")


def state_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "State")


def city_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "City")


def branch_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Empty DataFrame when the dataset has no Branch column -- Branch
    is never assumed to exist."""
    if df is None or df.empty or "Branch" not in df.columns:
        return pd.DataFrame()
    return performance_by(df, "Branch")


# ------------------------------------------------------------------
# Segment analytics
# ------------------------------------------------------------------

def segment_performance(df: pd.DataFrame) -> pd.DataFrame:
    return performance_by(df, "Segment")


# ------------------------------------------------------------------
# Discount analytics
# ------------------------------------------------------------------

def discount_vs_profit(df: pd.DataFrame) -> pd.DataFrame:
    """Row-level Discount/Profit pairs (numeric, incomplete rows
    dropped) for scatter-style analysis of discounting vs profit."""
    cols = ["Discount", "Profit"]
    if df is None or df.empty or "Discount" not in df.columns or "Profit" not in df.columns:
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame({
        "Discount": pd.to_numeric(df["Discount"], errors="coerce"),
        "Profit": pd.to_numeric(df["Profit"], errors="coerce"),
    }).dropna()
    return out.reset_index(drop=True)


def discount_vs_margin(df: pd.DataFrame) -> pd.DataFrame:
    """Row-level Discount/Margin % pairs, computed from Revenue and
    Profit. Empty if Discount, Revenue, or Profit isn't tracked."""
    cols = ["Discount", "Margin %"]
    if df is None or df.empty or "Discount" not in df.columns:
        return pd.DataFrame(columns=cols)
    if "Profit" not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame(columns=cols)

    revenue = pd.to_numeric(df["Revenue"], errors="coerce")
    profit = pd.to_numeric(df["Profit"], errors="coerce")
    margin = np.where(revenue != 0, profit / revenue * 100, np.nan)

    out = pd.DataFrame({
        "Discount": pd.to_numeric(df["Discount"], errors="coerce"),
        "Margin %": margin,
    }).dropna()
    return out.reset_index(drop=True)


def discount_buckets(df: pd.DataFrame, bins=(0, 0.1, 0.2, 0.3, 0.4, 1.0)) -> pd.DataFrame:
    """
    Buckets rows by Discount range and summarizes Revenue / Profit /
    Margin % / Orders per bucket. `bins` are discount fractions
    (0-1); a Discount column already expressed as 0-100 is rescaled
    automatically.
    """
    cols = ["Discount Range", "Revenue", "Profit", "Margin %", "Orders"]
    if df is None or df.empty or "Discount" not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame(columns=cols)

    work = df.copy()
    discount = pd.to_numeric(work["Discount"], errors="coerce")
    if discount.dropna().gt(1).any():
        discount = discount / 100.0
    work["_discount"] = discount
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
    if "Profit" in work.columns:
        work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")

    work = work.dropna(subset=["_discount"])
    if work.empty:
        return pd.DataFrame(columns=cols)

    work["Discount Range"] = pd.cut(work["_discount"], bins=bins, include_lowest=True)

    agg = {"Revenue": "sum"}
    if "Profit" in work.columns:
        agg["Profit"] = "sum"

    grouped = work.groupby("Discount Range", observed=False).agg(agg)

    if "OrderID" in work.columns:
        grouped["Orders"] = work.groupby("Discount Range", observed=False)["OrderID"].nunique()
    else:
        grouped["Orders"] = work.groupby("Discount Range", observed=False).size()

    if "Profit" in grouped.columns:
        grouped["Margin %"] = np.where(grouped["Revenue"] != 0, grouped["Profit"] / grouped["Revenue"] * 100, np.nan)

    grouped = grouped.reset_index()
    grouped["Discount Range"] = grouped["Discount Range"].astype(str)
    return grouped


def discount_impact(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row each for "Discounted" and "Full Price" rows: Revenue,
    Profit, Margin %, Orders, and Avg Discount %, to gauge whether
    discounting is helping or hurting overall performance.
    """
    cols = ["Group", "Revenue", "Profit", "Margin %", "Orders", "Avg Discount %"]
    if df is None or df.empty or "Discount" not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame(columns=cols)

    work = df.copy()
    discount = pd.to_numeric(work["Discount"], errors="coerce")
    discount_pct = discount if discount.dropna().gt(1).any() else discount * 100

    work["_discounted"] = discount.fillna(0) > 0
    work["_discount_pct"] = discount_pct
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
    if "Profit" in work.columns:
        work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")

    rows = []
    for label, flag in (("Discounted", True), ("Full Price", False)):
        subset = work[work["_discounted"] == flag]
        if subset.empty:
            continue

        revenue = float(subset["Revenue"].sum())
        profit = float(subset["Profit"].sum()) if "Profit" in subset.columns else None
        margin = (profit / revenue * 100) if (profit is not None and revenue) else None

        if "OrderID" in subset.columns:
            orders = int(subset["OrderID"].nunique())
        else:
            orders = int(len(subset))

        avg_discount = float(subset["_discount_pct"].mean()) if flag else 0.0

        rows.append({
            "Group": label,
            "Revenue": revenue,
            "Profit": profit,
            "Margin %": margin,
            "Orders": orders,
            "Avg Discount %": avg_discount,
        })

    return pd.DataFrame(rows, columns=cols)


# ------------------------------------------------------------------
# Customer analytics
# ------------------------------------------------------------------

def customer_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Per-customer performance table. Empty if CustomerID isn't
    present -- customer identity is never assumed to exist."""
    if df is None or df.empty or "CustomerID" not in df.columns:
        return pd.DataFrame()
    return performance_by(df, "CustomerID")


def top_customers(df: pd.DataFrame, n: int = 10, by: str = "Revenue") -> pd.DataFrame:
    perf = customer_performance(df)
    if perf.empty or by not in perf.columns:
        return pd.DataFrame()
    return perf.sort_values(by, ascending=False).head(n).reset_index(drop=True)


def customer_concentration(df: pd.DataFrame) -> float:
    """Herfindahl-style revenue concentration (0-100) across
    customers; higher means revenue is concentrated in fewer
    customers. 0.0 if CustomerID isn't present."""
    if df is None or df.empty or "CustomerID" not in df.columns:
        return 0.0
    return concentration_index(df, "CustomerID")


# ------------------------------------------------------------------
# Contribution & concentration (generic)
# ------------------------------------------------------------------

def revenue_contribution(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    perf = performance_by(df, dim)
    if perf.empty:
        return perf
    return perf[[dim, "Revenue", "Contribution %"]]


def concentration_index(df: pd.DataFrame, dim: str) -> float:
    """Herfindahl-style concentration (0-100): higher = more revenue
    concentrated in fewer entities. 0.0 if unavailable."""
    perf = performance_by(df, dim)
    if perf.empty or "Contribution %" not in perf.columns:
        return 0.0
    shares = perf["Contribution %"] / 100
    return float((shares ** 2).sum() * 100)


def product_region_matrix(
    df: pd.DataFrame,
    product_col: str = "Product",
    region_col: str = "Region",
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if product_col not in df.columns or region_col not in df.columns or "Revenue" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
    return work.pivot_table(
        index=product_col, columns=region_col, values="Revenue", aggfunc="sum", fill_value=0
    )


# ------------------------------------------------------------------
# Target / profitability (conditional features)
# ------------------------------------------------------------------

def target_achievement(df: pd.DataFrame):
    if df is None or df.empty or "Target" not in df.columns:
        return None
    target_sum = pd.to_numeric(df["Target"], errors="coerce").sum()
    if not target_sum or pd.isna(target_sum):
        return None
    return float(total_revenue(df) / target_sum * 100)


def profitability_summary(df: pd.DataFrame):
    if df is None or df.empty or "Profit" not in df.columns:
        return None
    profit = pd.to_numeric(df["Profit"], errors="coerce")
    avg_margin = None
    if "Margin" in df.columns:
        margin = pd.to_numeric(df["Margin"], errors="coerce")
        if margin.notna().any():
            avg_margin = float(margin.mean())
    return {
        "total_profit": float(profit.sum()),
        "avg_margin": avg_margin,
    }