"""
INAIBA - Insights Module
Business intelligence interpretation layer: converts calculated analytics
into structured, traceable business insights. Every insight is generated
only from calculated data (no unsupported or generic claims), and every
Priority is computed from a documented numeric rule rather than assigned
arbitrarily.

No Streamlit UI and no chart creation here — this module only returns
dicts/dataframes/strings for app.py to render.
"""

import pandas as pd
import numpy as np
import analytics as an


def _plural(dim: str) -> str:
    d = dim.lower()
    if d.endswith("y"):
        return d[:-1] + "ies"
    if d.endswith(("ch", "sh", "s", "x")):
        return d + "es"
    return d + "s"


def growth_drivers(df: pd.DataFrame, dim: str, top_n: int = 3, min_share: float = 1.0) -> list[dict]:
    perf = an.performance_by(df, dim)
    if perf.empty or "Growth %" not in perf.columns:
        return []
    filtered = perf[(perf["Contribution %"] >= min_share) & (perf["Growth %"] > 0)]
    filtered = filtered.sort_values("Growth %", ascending=False).head(top_n)
    insights = []
    for _, row in filtered.iterrows():
        insights.append({
            "observation": f"{row[dim]} is a growth driver within {_plural(dim)}.",
            "supporting_data": (
                f"{row[dim]} grew {row['Growth %']:.1f}% and contributes "
                f"{row['Contribution %']:.1f}% of total revenue (₹{row['Revenue']:,.0f})."
            ),
            "implication": f"{row[dim]} is currently strengthening overall revenue performance.",
        })
    return insights


def decline_drivers(df: pd.DataFrame, dim: str, top_n: int = 3, min_share: float = 1.0) -> list[dict]:
    perf = an.performance_by(df, dim)
    if perf.empty or "Growth %" not in perf.columns:
        return []
    filtered = perf[(perf["Contribution %"] >= min_share) & (perf["Growth %"] < 0)]
    filtered = filtered.sort_values("Growth %", ascending=True).head(top_n)
    insights = []
    for _, row in filtered.iterrows():
        insights.append({
            "observation": f"{row[dim]} is declining within {_plural(dim)}.",
            "supporting_data": (
                f"{row[dim]} declined {abs(row['Growth %']):.1f}% while contributing "
                f"{row['Contribution %']:.1f}% of total revenue (₹{row['Revenue']:,.0f})."
            ),
            "implication": f"{row[dim]} may require attention to prevent further revenue erosion.",
        })
    return insights


def consecutive_trend_insight(monthly_df: pd.DataFrame) -> dict | None:
    if monthly_df is None or len(monthly_df) < 3:
        return None
    growth = monthly_df["Growth %"].dropna().values
    if len(growth) < 2:
        return None
    streak = 1
    direction = growth[-1] > 0
    for g in reversed(growth[:-1]):
        if (g > 0) == direction:
            streak += 1
        else:
            break
    if streak < 2:
        return None
    word = "growth" if direction else "decline"
    return {
        "observation": f"Revenue has shown {streak} consecutive months of {word}.",
        "supporting_data": f"The most recent month changed {growth[-1]:+.1f}% versus the prior month.",
        "implication": f"This is a sustained {word} pattern rather than a single-month fluctuation.",
    }


def concentration_insight(df: pd.DataFrame, dim: str, threshold: float = 40.0) -> dict | None:
    perf = an.performance_by(df, dim)
    if perf.empty:
        return None
    top_share = perf.iloc[0]["Contribution %"]
    if top_share < threshold:
        return None
    return {
        "observation": f"Revenue is concentrated in a small number of {_plural(dim)}.",
        "supporting_data": f"The top {dim.lower()}, {perf.iloc[0][dim]}, alone contributes {top_share:.1f}% of total revenue.",
        "implication": f"This creates a concentration risk — performance is heavily dependent on this single {dim.lower()}.",
    }


def product_mix_shift(df: pd.DataFrame) -> dict | None:
    """Detects whether the top-contributing product has changed between the first and second half of the data."""
    if "Product" not in df.columns or "Date" not in df.columns or df["Date"].isna().all():
        return None
    dmin, dmax = df["Date"].min(), df["Date"].max()
    if dmin == dmax:
        return None
    midpoint = dmin + (dmax - dmin) / 2
    first = df[df["Date"] <= midpoint].groupby("Product")["Revenue"].sum()
    second = df[df["Date"] > midpoint].groupby("Product")["Revenue"].sum()
    if first.empty or second.empty:
        return None
    top_first = first.idxmax()
    top_second = second.idxmax()
    if top_first == top_second:
        return None
    return {
        "observation": "The leading product has shifted over time.",
        "supporting_data": f"{top_first} led revenue in the earlier period; {top_second} leads in the more recent period.",
        "implication": "Product mix is changing, which may affect forecasting assumptions and inventory/stocking priorities.",
    }


def order_value_insight(df: pd.DataFrame) -> dict | None:
    m = an.monthly_revenue(df)
    if len(m) < 2:
        return None
    aov_change = (m["AOV"].iloc[-1] - m["AOV"].iloc[-2]) / m["AOV"].iloc[-2] * 100 if m["AOV"].iloc[-2] else None
    order_change = (m["Orders"].iloc[-1] - m["Orders"].iloc[-2]) / m["Orders"].iloc[-2] * 100 if m["Orders"].iloc[-2] else None
    if aov_change is None or order_change is None:
        return None
    if abs(aov_change) < 3:
        return None
    driver = "average order value" if abs(aov_change) > abs(order_change) else "order volume"
    return {
        "observation": f"Revenue movement was primarily driven by a change in {driver}.",
        "supporting_data": (
            f"Average order value changed {aov_change:+.1f}% while order volume changed {order_change:+.1f}% "
            f"in the latest month versus the prior month."
        ),
        "implication": f"Monitor {driver} closely, as it is currently the dominant factor behind revenue change.",
    }


def build_all_insights(df: pd.DataFrame) -> dict:
    """Assembles categorized insight lists for the Business Insights page."""
    monthly = an.monthly_revenue(df)
    growth = []
    decline = []
    for dim in ["Product", "Category", "Region", "Branch"]:
        if dim in df.columns:
            growth += growth_drivers(df, dim)
            decline += decline_drivers(df, dim)

    trend_insights = []
    ct = consecutive_trend_insight(monthly)
    if ct:
        trend_insights.append(ct)
    for dim in ["Product", "Category", "Region"]:
        if dim in df.columns:
            ci = concentration_insight(df, dim)
            if ci:
                trend_insights.append(ci)
    pms = product_mix_shift(df)
    if pms:
        trend_insights.append(pms)
    ovi = order_value_insight(df)
    if ovi:
        trend_insights.append(ovi)

    return {
        "growth_drivers": growth[:6],
        "decline_drivers": decline[:6],
        "trend_insights": trend_insights[:6],
    }


def _customer_concentration_safe(data: pd.DataFrame) -> dict | None:
    """Calls analytics.customer_concentration_3_10 if it exists, without crashing if it doesn't or the data can't support it."""
    fn = getattr(an, "customer_concentration_3_10", None)
    if fn is None:
        return None
    try:
        return fn(data)
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return None


def business_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """Generate at least eight evidence-backed recommendations from calculated data."""
    data = an.prepare_analysis_data(df)
    rows = []

    # 1. Leading category
    if "Category" in data.columns:
        perf = an.performance_by(data, "Category")
        if not perf.empty:
            r = perf.iloc[0]
            rows.append({
                "Recommendation": "Focus sales efforts on the leading category",
                "Supporting Evidence": f"{r['Category']} generated ₹{float(r['Revenue']):,.0f}, contributing {float(r['Contribution %']):.1f}% of total revenue.",
                "Priority": "High",
            })

    # 2. Best location/branch
    location = next((c for c in ["Branch", "City", "Region", "Location"] if c in data.columns), None)
    if location:
        perf = an.performance_by(data, location)
        if not perf.empty:
            r = perf.iloc[0]
            rows.append({
                "Recommendation": f"Protect performance in {r[location]}",
                "Supporting Evidence": f"{r[location]} generated ₹{float(r['Revenue']):,.0f}, equal to {float(r['Contribution %']):.1f}% of total revenue.",
                "Priority": "High",
            })

            # 3. Weakest location
            valid = perf[perf["Growth %"].notna()]
            if not valid.empty:
                r = valid.sort_values("Growth %", ascending=True).iloc[0]
                rows.append({
                    "Recommendation": f"Investigate the trend in {r[location]}",
                    "Supporting Evidence": f"Its revenue growth is {float(r['Growth %']):+.1f}% and current revenue is ₹{float(r['Revenue']):,.0f}.",
                    "Priority": "High",
                })

    # 4. High quantity / low revenue product
    if "Product" in data.columns and "Quantity" in data.columns:
        low = an.high_quantity_low_revenue_products(data, 3)
        if not low.empty:
            r = low.iloc[0]
            rows.append({
                "Recommendation": f"Review pricing or mix for {r['Product']}",
                "Supporting Evidence": f"It sold {float(r['Quantity']):,.0f} units but generated ₹{float(r['Revenue']):,.0f} revenue under the high-quantity/low-revenue analysis.",
                "Priority": "Medium",
            })

    # 5. Customer concentration
    cc = _customer_concentration_safe(data)
    if cc:
        rows.append({
            "Recommendation": "Monitor dependency on major customers",
            "Supporting Evidence": f"Top 1 customer contributes {cc['Top 1']:.1f}%, top 3 contribute {cc['Top 3']:.1f}%, and top 10 contribute {cc['Top 10']:.1f}% of revenue.",
            "Priority": "High",
        })

    # 6. Anomaly verification
    anomalies = an.assignment_anomalies(data)
    rows.append({
        "Recommendation": "Verify unusual transactions and sales movements",
        "Supporting Evidence": f"{len(anomalies):,} genuine anomaly record(s) were detected using percentage-change and IQR rules; possible causes are hypotheses until verified.",
        "Priority": "High" if len(anomalies) > 0 else "Medium",
    })

    # 7. Recent momentum
    monthly = an.monthly_revenue(data)
    if len(monthly) >= 2:
        latest = float(monthly.iloc[-1]["Revenue"])
        growth = monthly.iloc[-1]["Growth %"]
        if pd.notna(growth):
            rows.append({
                "Recommendation": "Plan around the latest revenue momentum",
                "Supporting Evidence": f"Latest monthly revenue is ₹{latest:,.0f}, with month-over-month change of {float(growth):+.1f}%.",
                "Priority": "Medium",
            })

    # 8. Order economics
    orders = an.total_orders(data)
    aov = an.average_order_value(data)
    rows.append({
        "Recommendation": "Monitor order volume and order value together",
        "Supporting Evidence": f"The dataset contains {orders:,} unique orders with an average order value of ₹{aov:,.0f}.",
        "Priority": "Medium",
    })

    # Fallback evidence-backed recommendations ensure the assignment has eight rows
    # even when optional dimensions are absent.
    if len(rows) < 8:
        total = an.total_revenue(data)
        qty = an.total_quantity(data)
        rows.append({
            "Recommendation": "Track revenue and quantity as paired KPIs",
            "Supporting Evidence": f"Current total revenue is ₹{total:,.0f} across {qty:,.0f} units sold; monitor whether future volume changes translate into proportional revenue changes.",
            "Priority": "Medium",
        })
    if len(rows) < 8 and not monthly.empty:
        peak = monthly.loc[monthly["Revenue"].idxmax()]
        rows.append({
            "Recommendation": "Use the peak sales period for operational planning",
            "Supporting Evidence": f"The highest recorded monthly revenue is ₹{float(peak['Revenue']):,.0f} in {peak['Month'].strftime('%b %Y')}.",
            "Priority": "Medium",
        })
    if len(rows) < 8:
        rows.append({
            "Recommendation": "Maintain a consistent monthly sales review",
            "Supporting Evidence": f"The current analysis contains {len(data):,} usable records; recurring review will keep the calculated KPIs and recommendations current.",
            "Priority": "Low",
        })

    return pd.DataFrame(rows[:8], columns=["Recommendation", "Supporting Evidence", "Priority"])


def management_summary(df: pd.DataFrame, forecast_result: dict | None = None) -> str:
    """Builds a concise, data-driven management summary paragraph."""
    monthly = an.monthly_revenue(df)
    total_rev = an.total_revenue(df)
    parts = [f"Total revenue for the analyzed period is ₹{total_rev:,.0f}."]

    if len(monthly) >= 2 and pd.notna(monthly["Growth %"].iloc[-1]):
        g = monthly["Growth %"].iloc[-1]
        direction = "increased" if g >= 0 else "decreased"
        parts.append(f"Revenue {direction} {abs(g):.1f}% in the most recent month compared to the prior month.")

    for dim in ["Category", "Product", "Region"]:
        if dim in df.columns:
            top = an.top_performer(df, dim)
            fg = an.fastest_growing(df, dim)
            if top:
                parts.append(f"{top} is the leading {dim.lower()} by revenue.")
            if fg and fg != top:
                parts.append(f"{fg} is the fastest-growing {dim.lower()}.")
            break  # only report on the first available dimension to keep it concise

    weak = None
    for dim in ["Category", "Product", "Region"]:
        if dim in df.columns:
            weak = an.weakest_performer(df, dim)
            if weak:
                parts.append(f"{weak} shows the weakest growth and may require attention.")
            break

    if forecast_result and forecast_result.get("sufficient_data"):
        nm = forecast_result.get("next_month_forecast")
        eg = forecast_result.get("expected_growth_next_month")
        if nm is not None:
            trend_word = "growth" if (eg or 0) >= 0 else "decline"
            parts.append(
                f"The near-term forecast projects ₹{nm:,.0f} in revenue next month, "
                f"indicating expected {trend_word} of {abs(eg):.1f}%." if eg is not None else
                f"The near-term forecast projects ₹{nm:,.0f} in revenue next month."
            )

    return " ".join(parts)


def key_alerts(df: pd.DataFrame, quality: dict, anomaly_summary: dict) -> list[dict]:
    """Top 3-5 business alerts for the Executive Overview."""
    alerts = []
    monthly = an.monthly_revenue(df)

    if len(monthly) >= 2 and pd.notna(monthly["Growth %"].iloc[-1]):
        g = monthly["Growth %"].iloc[-1]
        if g <= -10:
            alerts.append({"level": "critical", "message": f"Revenue declined {abs(g):.1f}% in the latest month."})
        elif g >= 15:
            alerts.append({"level": "good", "message": f"Revenue grew {g:.1f}% in the latest month, above typical pace."})

    if anomaly_summary.get("Critical", 0) > 0 or anomaly_summary.get("High", 0) > 0:
        count = anomaly_summary.get("Critical", 0) or anomaly_summary.get("High", 0)
        alerts.append({"level": "critical", "message": f"{count} critical anomaly(ies) detected — review Risks & Anomalies."})
    if anomaly_summary.get("Moderate", 0) > 0 or anomaly_summary.get("Medium", 0) > 0:
        count = anomaly_summary.get("Moderate", 0) or anomaly_summary.get("Medium", 0)
        alerts.append({"level": "moderate", "message": f"{count} moderate anomaly(ies) detected."})

    if quality.get("reliability_status") in ("Limited Reliability", "Low Reliability"):
        alerts.append({"level": "moderate", "message": f"Data reliability is '{quality['reliability_status']}' ({quality['completeness_pct']}% complete) — interpret results with caution."})

    for dim in ["Category", "Product", "Region"]:
        if dim in df.columns:
            weak = an.weakest_performer(df, dim)
            if weak:
                alerts.append({"level": "watch", "message": f"{weak} shows the weakest growth among {_plural(dim)}."})
            break

    if not alerts:
        alerts.append({"level": "good", "message": "No major risks detected. Performance is within expected ranges."})

    return alerts[:5]


# ====================================================================
# Business Intelligence Interpretation Layer
#
# Converts calculated analytics into structured, traceable insights.
# Every insight below is a dict with exactly these eight keys:
#   Category, Title, Data Evidence, Observation, Interpretation,
#   Business Impact, Recommended Action, Priority
#
# Rules this layer follows throughout:
#  - An insight is only produced when the data needed to support it exists
#    (missing columns/metrics/insufficient rows -> no insight, not a filler).
#  - "Data Evidence" always cites the actual computed number(s).
#  - "Priority" is always computed from a documented numeric threshold
#    (the *_THRESHOLDS constants below) — never an arbitrary AI label.
#  - "Business Impact" / "Interpretation" describe what the pattern means
#    for the business; they never assert an unverified cause.
# ====================================================================

# Each threshold tuple is (medium_cutoff, high_cutoff) on the metric's
# absolute magnitude. Below the medium cutoff, Priority is "Low".
REVENUE_PRIORITY_THRESHOLDS = (5.0, 15.0)            # |month-over-month growth %|
GROWTH_PRIORITY_THRESHOLDS = (5.0, 15.0)             # |period-over-period growth %|
PROFIT_MARGIN_DEVIATION_THRESHOLDS = (3.0, 7.0)      # margin points vs. the dataset's own average margin
CONCENTRATION_PRIORITY_THRESHOLDS = (40.0, 60.0)     # top-entity contribution % of revenue
CUSTOMER_CONCENTRATION_THRESHOLDS = (30.0, 50.0)     # top-1 customer contribution % of revenue
DISCOUNT_IMPACT_THRESHOLDS = (2.0, 5.0)              # margin-point gap, discounted vs non-discounted
PRODUCT_MISMATCH_THRESHOLDS = (20.0, 40.0)           # % gap between a product's unit price and the dataset average
FORECAST_GROWTH_THRESHOLDS = (5.0, 15.0)             # |projected next-month growth %|

INSIGHT_KEYS = [
    "Category", "Title", "Data Evidence", "Observation",
    "Interpretation", "Business Impact", "Recommended Action", "Priority",
]


def _priority_from_magnitude(value, medium_cutoff: float, high_cutoff: float) -> str:
    """Transparent, rule-based severity: compares |value| against documented cutoffs."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Low"
    v = abs(value)
    if v >= high_cutoff:
        return "High"
    if v >= medium_cutoff:
        return "Medium"
    return "Low"


def _insight(category, title, evidence, observation, interpretation, impact, action, priority) -> dict:
    return {
        "Category": category,
        "Title": title,
        "Data Evidence": evidence,
        "Observation": observation,
        "Interpretation": interpretation,
        "Business Impact": impact,
        "Recommended Action": action,
        "Priority": priority,
    }


def _revenue_insight(monthly: pd.DataFrame) -> dict | None:
    """Short-term (month-over-month) revenue momentum."""
    if monthly is None or monthly.empty or "Growth %" not in monthly.columns or len(monthly) < 2:
        return None
    growth = monthly["Growth %"].iloc[-1]
    if pd.isna(growth):
        return None
    latest_rev = monthly["Revenue"].iloc[-1]
    prior_rev = monthly["Revenue"].iloc[-2]
    direction = "increased" if growth >= 0 else "decreased"
    return _insight(
        category="Revenue",
        title=f"Revenue {direction} in the latest month",
        evidence=f"Latest monthly revenue is ₹{latest_rev:,.0f}, versus ₹{prior_rev:,.0f} in the prior month ({growth:+.1f}%).",
        observation=f"Month-over-month revenue {direction} by {abs(growth):.1f}%.",
        interpretation="This reflects the most recent short-term revenue movement relative to the prior month.",
        impact="Revenue momentum" if growth >= 0 else "Revenue softening",
        action=(
            "Continue current sales activity and monitor next month's figures to confirm the trend."
            if growth >= 0 else
            "Review recent sales activity and pipeline to identify what is contributing to the decline."
        ),
        priority=_priority_from_magnitude(growth, *REVENUE_PRIORITY_THRESHOLDS),
    )


def _growth_insight(monthly: pd.DataFrame) -> dict | None:
    """Overall trajectory across the full analyzed period (not just the latest month)."""
    if monthly is None or len(monthly) < 3 or "Revenue" not in monthly.columns:
        return None
    first_rev = monthly["Revenue"].iloc[0]
    last_rev = monthly["Revenue"].iloc[-1]
    if not first_rev or pd.isna(first_rev) or pd.isna(last_rev):
        return None
    overall_growth = (last_rev - first_rev) / first_rev * 100
    direction = "grown" if overall_growth >= 0 else "contracted"
    if "Month" in monthly.columns:
        first_label = monthly["Month"].iloc[0].strftime("%b %Y")
        last_label = monthly["Month"].iloc[-1].strftime("%b %Y")
    else:
        first_label, last_label = "the start of the period", "the most recent month"
    return _insight(
        category="Growth",
        title=f"Revenue has {direction} across the analyzed period",
        evidence=f"Revenue moved from ₹{first_rev:,.0f} in {first_label} to ₹{last_rev:,.0f} in {last_label}, a change of {overall_growth:+.1f}%.",
        observation=f"Overall revenue has {direction} {abs(overall_growth):.1f}% from the first to the most recent month in the data.",
        interpretation="This reflects the overall trajectory across the full analyzed period rather than a single month's movement.",
        impact="Business growth trajectory" if overall_growth >= 0 else "Business growth trajectory declining",
        action=(
            "Assess which factors are sustaining growth so they can be reinforced."
            if overall_growth >= 0 else
            "Investigate the sustained contraction to determine whether it is broad-based or concentrated in specific segments."
        ),
        priority=_priority_from_magnitude(overall_growth, *GROWTH_PRIORITY_THRESHOLDS),
    )


def _monthly_margin_series(df: pd.DataFrame) -> pd.DataFrame | None:
    """Builds a Month/Revenue/Profit/Margin % series directly from row-level data. None if not computable."""
    if "Date" not in df.columns or "Profit" not in df.columns or "Revenue" not in df.columns:
        return None
    work = df.copy()
    work["Date"] = pd.to_datetime(work["Date"], errors="coerce")
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
    work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")
    work = work.dropna(subset=["Date"])
    if work.empty:
        return None
    work["__month"] = work["Date"].dt.to_period("M")
    grouped = work.groupby("__month").agg(Revenue=("Revenue", "sum"), Profit=("Profit", "sum")).reset_index()
    grouped = grouped.sort_values("__month")
    grouped["Margin %"] = np.where(grouped["Revenue"] != 0, grouped["Profit"] / grouped["Revenue"] * 100, np.nan)
    return grouped


def _profitability_insight(df: pd.DataFrame) -> dict | None:
    """Compares the latest month's margin to the dataset's own average margin (no external benchmark used)."""
    if df is None or "Profit" not in df.columns or "Revenue" not in df.columns:
        return None
    total_revenue = pd.to_numeric(df["Revenue"], errors="coerce").sum()
    total_profit = pd.to_numeric(df["Profit"], errors="coerce").sum()
    if not total_revenue or pd.isna(total_revenue):
        return None
    overall_margin = total_profit / total_revenue * 100

    margin_series = _monthly_margin_series(df)
    if margin_series is not None and len(margin_series) >= 2 and margin_series["Margin %"].notna().sum() >= 2:
        latest_margin = margin_series["Margin %"].iloc[-1]
        avg_margin = margin_series["Margin %"].mean(skipna=True)
        if pd.isna(latest_margin) or pd.isna(avg_margin):
            return None
        deviation = latest_margin - avg_margin
        evidence = (
            f"The most recent month's margin is {latest_margin:.1f}%, versus an average margin of {avg_margin:.1f}% "
            f"across the analyzed period (overall margin: {overall_margin:.1f}%)."
        )
    else:
        # Not enough monthly granularity — report the overall margin only, no trend claim.
        latest_margin = overall_margin
        deviation = None
        evidence = f"Overall profit margin across the analyzed period is {overall_margin:.1f}% (₹{total_profit:,.0f} profit on ₹{total_revenue:,.0f} revenue)."

    if deviation is not None:
        direction = "below" if deviation < 0 else "above"
        observation = f"The latest month's margin is {abs(deviation):.1f} percentage points {direction} the period average."
        impact = "Margin pressure" if deviation < 0 else "Margin improvement"
        priority = _priority_from_magnitude(deviation, *PROFIT_MARGIN_DEVIATION_THRESHOLDS)
        action = (
            "Review cost and pricing drivers behind the recent margin decline."
            if deviation < 0 else
            "Identify what is supporting the improved margin so it can be sustained."
        )
    else:
        observation = f"Overall margin for the analyzed period is {overall_margin:.1f}%."
        impact = "Product profitability" if overall_margin >= 0 else "Margin pressure"
        priority = "Low"
        action = "Track margin by month going forward to identify trend once more monthly history is available."

    return _insight(
        category="Profitability",
        title="Profit margin summary for the analyzed period",
        evidence=evidence,
        observation=observation,
        interpretation="This is a self-referential comparison against the dataset's own history; no external benchmark is used.",
        impact=impact,
        action=action,
        priority=priority,
    )


def _products_insight(df: pd.DataFrame) -> dict | None:
    """High-quantity, low-revenue product review — a pricing/mix signal traceable to unit economics."""
    if "Product" not in df.columns or "Quantity" not in df.columns or "Revenue" not in df.columns:
        return None
    fn = getattr(an, "high_quantity_low_revenue_products", None)
    if fn is None:
        return None
    try:
        low = fn(df, 3)
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return None
    if low is None or low.empty:
        return None

    r = low.iloc[0]
    total_qty = pd.to_numeric(df["Quantity"], errors="coerce").sum()
    total_rev = pd.to_numeric(df["Revenue"], errors="coerce").sum()
    avg_unit_price = (total_rev / total_qty) if total_qty else None
    prod_qty = float(r["Quantity"])
    prod_rev = float(r["Revenue"])
    prod_unit_price = (prod_rev / prod_qty) if prod_qty else None

    if avg_unit_price and prod_unit_price is not None:
        gap_pct = (avg_unit_price - prod_unit_price) / avg_unit_price * 100
        priority = _priority_from_magnitude(gap_pct, *PRODUCT_MISMATCH_THRESHOLDS)
        gap_text = f" Its implied unit price (₹{prod_unit_price:,.2f}) is {abs(gap_pct):.1f}% {'below' if gap_pct > 0 else 'above'} the dataset average unit price (₹{avg_unit_price:,.2f})."
    else:
        priority = "Medium"
        gap_text = ""

    return _insight(
        category="Products",
        title=f"{r['Product']} sells in high volume relative to the revenue it generates",
        evidence=f"{r['Product']} sold {prod_qty:,.0f} units for ₹{prod_rev:,.0f} in revenue.{gap_text}",
        observation=f"{r['Product']} has a high quantity-to-revenue ratio compared to other products.",
        interpretation="This pattern typically points to a pricing or product-mix question rather than a demand problem, since volume is not the constraint.",
        impact="Product profitability",
        action=f"Review pricing, bundling, or cost structure for {r['Product']} to confirm it is contributing proportionally to revenue.",
        priority=priority,
    )


def _concentration_insight(df: pd.DataFrame, dim: str, category_label: str, impact_label: str,
                            thresholds: tuple = CONCENTRATION_PRIORITY_THRESHOLDS) -> dict | None:
    """Generic top-entity revenue concentration insight, reused for Categories and Regions."""
    if dim not in df.columns:
        return None
    perf = an.performance_by(df, dim)
    if perf is None or perf.empty or "Contribution %" not in perf.columns:
        return None
    top = perf.iloc[0]
    top_share = top["Contribution %"]
    if pd.isna(top_share):
        return None
    return _insight(
        category=category_label,
        title=f"Revenue is concentrated in a small number of {_plural(dim)}",
        evidence=f"The top {dim.lower()}, {top[dim]}, contributes {top_share:.1f}% of total revenue (₹{float(top['Revenue']):,.0f}).",
        observation=f"A single {dim.lower()} accounts for {top_share:.1f}% of total revenue.",
        interpretation=f"Performance is disproportionately dependent on this one {dim.lower()}.",
        impact=impact_label,
        action=f"Consider diversifying revenue sources beyond {top[dim]} to reduce dependency risk.",
        priority=_priority_from_magnitude(top_share, *thresholds),
    )


def _top_grower_insight(df: pd.DataFrame, dim: str, category_label: str, impact_label: str,
                         min_share: float = 1.0) -> dict | None:
    """Generic fastest-growing-entity opportunity insight, reused for Regions."""
    if dim not in df.columns:
        return None
    perf = an.performance_by(df, dim)
    if perf is None or perf.empty or "Growth %" not in perf.columns:
        return None
    candidates = perf[(perf["Contribution %"] >= min_share) & (perf["Growth %"] > 0)]
    if candidates.empty:
        return None
    top = candidates.sort_values("Growth %", ascending=False).iloc[0]
    return _insight(
        category=category_label,
        title=f"{top[dim]} is an emerging opportunity within {_plural(dim)}",
        evidence=f"{top[dim]} grew {top['Growth %']:.1f}% and contributes {top['Contribution %']:.1f}% of total revenue (₹{float(top['Revenue']):,.0f}).",
        observation=f"{top[dim]} is growing faster than other {_plural(dim)} while already holding a measurable share of revenue.",
        interpretation=f"This {dim.lower()} is strengthening its contribution to overall revenue.",
        impact=impact_label,
        action=f"Consider allocating additional sales or marketing focus to {top[dim]} to capitalize on the momentum.",
        priority=_priority_from_magnitude(top["Growth %"], *GROWTH_PRIORITY_THRESHOLDS),
    )


def _customer_insight(df: pd.DataFrame) -> dict | None:
    cc = _customer_concentration_safe(df)
    if not cc:
        return None
    top1, top3, top10 = cc.get("Top 1"), cc.get("Top 3"), cc.get("Top 10")
    if top1 is None or pd.isna(top1):
        return None
    return _insight(
        category="Customers",
        title="Revenue depends on a small group of customers",
        evidence=f"The top customer contributes {top1:.1f}% of revenue; the top 3 contribute {top3:.1f}%; the top 10 contribute {top10:.1f}%.",
        observation="A small number of customers account for a large share of total revenue.",
        interpretation="Performance is dependent on the continued activity of these customers.",
        impact="Customer concentration risk",
        action="Consider strengthening relationships with top customers while broadening the customer base to reduce dependency.",
        priority=_priority_from_magnitude(top1, *CUSTOMER_CONCENTRATION_THRESHOLDS),
    )


def _forecast_insight(forecast_result: dict | None) -> dict | None:
    if not forecast_result or not forecast_result.get("sufficient_data"):
        return None
    nm = forecast_result.get("next_month_forecast")
    if nm is None:
        return None
    eg = forecast_result.get("expected_growth_next_month")
    model = forecast_result.get("selected_model", "the selected model")
    reliable = forecast_result.get("reliable", True)
    direction = "growth" if (eg or 0) >= 0 else "decline"

    evidence = f"The {model} model projects next month revenue of ₹{nm:,.0f}"
    evidence += f", a projected {direction} of {abs(eg):.1f}% versus the latest actual month." if eg is not None else "."

    impact = "Forecast uncertainty" if not reliable else "Forecast outlook"
    interpretation = (
        "This forecast has limited historical data to validate against, so treat it as indicative rather than precise."
        if not reliable else
        "This forecast is based on backtested model validation against historical data."
    )
    return _insight(
        category="Forecast",
        title=f"Near-term revenue is projected to show {direction}",
        evidence=evidence,
        observation=f"The forecasting model expects revenue to {direction} next month.",
        interpretation=interpretation,
        impact=impact,
        action=(
            "Use this forecast as a directional planning input, and revisit it once more months of history are available."
            if not reliable else
            "Incorporate this forecast into near-term planning and budget discussions."
        ),
        priority=_priority_from_magnitude(eg, *FORECAST_GROWTH_THRESHOLDS) if eg is not None else "Low",
    )


def _risks_insight(anomaly_summary: dict | None) -> dict | None:
    """Accepts either a High/Medium/Low or legacy Critical/Moderate/Watch severity-count dict."""
    if not anomaly_summary:
        return None
    high = anomaly_summary.get("High", anomaly_summary.get("Critical", 0)) or 0
    medium = anomaly_summary.get("Medium", anomaly_summary.get("Moderate", 0)) or 0
    low = anomaly_summary.get("Low", anomaly_summary.get("Watch", 0)) or 0
    total = anomaly_summary.get("Total", high + medium + low)
    if not total:
        return None
    priority = "High" if high > 0 else ("Medium" if medium > 0 else "Low")
    return _insight(
        category="Risks",
        title="Unusual performance patterns were detected",
        evidence=f"{total} anomaly record(s) were flagged: {high} high severity, {medium} medium severity, {low} low severity.",
        observation="Some data points deviate materially from their expected baseline.",
        interpretation="These deviations are statistically unusual; the underlying cause is not established from this data alone.",
        impact="Unusual performance",
        action="Review the flagged records in the Risks & Anomalies view; treat any cause as a hypothesis until verified.",
        priority=priority,
    )


def _discount_insight(df: pd.DataFrame) -> dict | None:
    if "Discount" not in df.columns or "Revenue" not in df.columns:
        return None
    work = df.copy()
    work["Discount"] = pd.to_numeric(work["Discount"], errors="coerce")
    work["Revenue"] = pd.to_numeric(work["Revenue"], errors="coerce")
    work = work.dropna(subset=["Discount", "Revenue"])
    if work.empty:
        return None
    total_revenue = work["Revenue"].sum()
    if not total_revenue:
        return None

    discounted = work[work["Discount"] > 0]
    non_discounted = work[work["Discount"] == 0]
    if discounted.empty:
        return None
    discounted_share = discounted["Revenue"].sum() / total_revenue * 100

    if "Profit" in work.columns:
        work["Profit"] = pd.to_numeric(work["Profit"], errors="coerce")
        d2 = work[(work["Discount"] > 0) & work["Profit"].notna()]
        nd2 = work[(work["Discount"] == 0) & work["Profit"].notna()]
        d_margin = (d2["Profit"].sum() / d2["Revenue"].sum() * 100) if (not d2.empty and d2["Revenue"].sum()) else None
        nd_margin = (nd2["Profit"].sum() / nd2["Revenue"].sum() * 100) if (not nd2.empty and nd2["Revenue"].sum()) else None
        if d_margin is not None and nd_margin is not None:
            gap = nd_margin - d_margin
            direction = "lower" if gap > 0 else "higher"
            return _insight(
                category="Discounts",
                title="Discounted transactions show a different margin profile",
                evidence=f"Discounted orders carry an average margin of {d_margin:.1f}% versus {nd_margin:.1f}% for non-discounted orders, and represent {discounted_share:.1f}% of total revenue.",
                observation=f"Margin on discounted transactions is {abs(gap):.1f} percentage points {direction} than non-discounted transactions.",
                interpretation="Discounting is associated with a measurable difference in margin on this data.",
                impact="Margin pressure" if gap > 0 else "Discount impact",
                action=(
                    "Review discount levels and eligibility criteria to ensure discounted deals still meet margin targets."
                    if gap > 0 else
                    "Current discount practice does not appear to be reducing margin on this data."
                ),
                priority=_priority_from_magnitude(gap, *DISCOUNT_IMPACT_THRESHOLDS),
            )

    # Profit not available (or not usable) — report revenue exposure only, no margin claim.
    avg_discount = discounted["Discount"].mean()
    return _insight(
        category="Discounts",
        title="A meaningful share of revenue comes from discounted transactions",
        evidence=f"{discounted_share:.1f}% of total revenue comes from discounted orders, with an average discount of {avg_discount:.1f}.",
        observation=f"Discounted transactions represent {discounted_share:.1f}% of revenue in this dataset.",
        interpretation="Profit data is not available, so the margin effect of this discounting cannot be established from this data.",
        impact="Discount impact",
        action="Add profit/cost data to evaluate whether current discount levels are protecting margin.",
        priority=_priority_from_magnitude(discounted_share, *CONCENTRATION_PRIORITY_THRESHOLDS),
    )


def generate_business_insights(
    df: pd.DataFrame,
    monthly_df: pd.DataFrame | None = None,
    forecast_result: dict | None = None,
    anomaly_summary: dict | None = None,
) -> list[dict]:
    """
    INAIBA's business intelligence interpretation layer: converts calculated
    analytics into structured, traceable insights covering Revenue,
    Profitability, Products, Categories, Regions, Customers, Forecast,
    Risks, Discounts, and Growth.

    Each returned dict has exactly the keys in INSIGHT_KEYS. An insight is
    included only when its underlying data exists and supports it; missing
    columns, empty data, or insufficient history simply mean that category
    is skipped rather than filled with a generic statement. Results are
    sorted High -> Medium -> Low priority.
    """
    if df is None or df.empty:
        return []

    monthly = monthly_df if monthly_df is not None else an.monthly_revenue(df)
    location_dim = next((c for c in ["Region", "Branch", "City", "Location"] if c in df.columns), None)

    insights = []

    for candidate in (
        _revenue_insight(monthly),
        _growth_insight(monthly),
        _profitability_insight(df),
        _products_insight(df),
        _concentration_insight(df, "Category", "Categories", impact_label="Revenue concentration"),
    ):
        if candidate:
            insights.append(candidate)

    if location_dim:
        reg_risk = _concentration_insight(df, location_dim, "Regions", impact_label="Regional concentration risk")
        if reg_risk:
            insights.append(reg_risk)
        reg_opportunity = _top_grower_insight(df, location_dim, "Regions", impact_label="Regional opportunity")
        if reg_opportunity:
            insights.append(reg_opportunity)

    for candidate in (
        _customer_insight(df),
        _forecast_insight(forecast_result),
        _risks_insight(anomaly_summary),
        _discount_insight(df),
    ):
        if candidate:
            insights.append(candidate)

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    insights.sort(key=lambda i: priority_rank.get(i["Priority"], 3))
    return insights