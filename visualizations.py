"""
INAIBA - Visualizations Module
Centralized Plotly chart builders for the INAIBA sales intelligence dashboard.

This module contains chart-generation logic only. It has no Streamlit page,
navigation, upload, or application-state code.

Design goals:
- Reusable Plotly figures with consistent enterprise styling.
- Safe handling of empty data and missing columns.
- Professional blue visual language.
- Readable labels and sensible number formatting.
- No statsmodels/trendline dependency.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from style import COLORS, CHART_PALETTE, style_fig


# =====================================================================
# DESIGN SYSTEM / HELPERS
# =====================================================================

def _color(name: str, fallback: str) -> str:
    """Read a project color safely, with a stable fallback."""
    return COLORS.get(name, fallback)


BLUE = _color("PRIMARY", "#2563EB")
BLUE_DARK = _color("PRIMARY_DARK", "#1E3A8A")
BLUE_LIGHT = _color("PRIMARY_LIGHT", "#EFF6FF")
BLUE_ACCENT = _color("ACCENT", "#3B82F6")
SUCCESS = _color("SUCCESS", "#15803D")
DANGER = _color("DANGER", "#DC2626")
WARNING = _color("WARNING", "#D97706")
INFO = _color("INFO", "#2563EB")
MUTED = _color("MUTED", "#64748B")
BORDER = _color("BORDER", "#E2E8F0")
TEXT = _color("TEXT_DARK", "#172033")

# Use the project's palette where available, but never require it to have
# a particular length.
PALETTE = list(CHART_PALETTE) if CHART_PALETTE else [
    BLUE, BLUE_ACCENT, "#60A5FA", "#1D4ED8", "#0EA5E9", "#0284C7"
]

TRANSPARENT = "rgba(0,0,0,0)"
BLUE_FILL = "rgba(79,140,255,0.14)"
BLUE_BAND = "rgba(79,140,255,0.18)"


def _currency(v: Any) -> str:
    """Format a number as Indian rupee currency."""
    try:
        if pd.isna(v):
            return "₹0"
        return f"₹{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _number(v: Any) -> str:
    """Format a numeric value compactly where appropriate."""
    try:
        if pd.isna(v):
            return "0"
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _percent(v: Any) -> str:
    """Format a percentage."""
    try:
        if pd.isna(v):
            return "0.0%"
        return f"{float(v):.1f}%"
    except (TypeError, ValueError):
        return str(v)


def _safe_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a defensive dataframe copy."""
    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()


def _has_columns(df: pd.DataFrame, columns: Sequence[str]) -> bool:
    return not df.empty and all(col in df.columns for col in columns)


def _empty_figure(title: str, message: str = "No data available") -> go.Figure:
    """Create a meaningful, non-crashing empty chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=13, color=MUTED),
    )
    return _finish(fig, title)


def _finish(fig: go.Figure, title: str, *, height: Optional[int] = None) -> go.Figure:
    """Apply consistent light enterprise chart styling."""
    fig.update_layout(
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            font=dict(size=17, color=TEXT),
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=PALETTE,
        font=dict(color=TEXT, size=12),
        margin=dict(l=56, r=28, t=62, b=48),
        hoverlabel=dict(
            bgcolor="#0E1A45",
            bordercolor=BORDER,
            font=dict(color=TEXT),
        ),
        legend=dict(
            bgcolor="rgba(10,19,50,0.6)",
            bordercolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=BORDER,
        tickfont=dict(color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(132,160,255,0.12)",
        zeroline=False,
        linecolor=BORDER,
        tickfont=dict(color=MUTED),
    )
    if height is not None:
        fig.update_layout(height=height)

    # Keep the project's centralized styling when available.
    try:
        return style_fig(fig, title)
    except Exception:
        return fig


def _clean_xy(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    numeric_y: bool = True,
) -> pd.DataFrame:
    """Select, clean and sort data for two-column charts."""
    if not _has_columns(df, [x, y]):
        return pd.DataFrame(columns=[x, y])

    out = df[[x, y]].copy()
    if numeric_y:
        out[y] = pd.to_numeric(out[y], errors="coerce")
    out = out.dropna(subset=[x, y])
    return out


def _short_label(value: Any, max_chars: int = 32) -> str:
    """Keep long category labels readable without changing the source data."""
    text = str(value)
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def _labels(values: Sequence[Any], max_chars: int = 32) -> list[str]:
    return [_short_label(v, max_chars) for v in values]


def _numeric_series(values: Any) -> pd.Series:
    return pd.to_numeric(pd.Series(values), errors="coerce")


def _normalize_0_100(series: Any) -> pd.Series:
    """Min-max normalize a numeric series to 0-100."""
    s = _numeric_series(series).astype(float)
    if s.empty:
        return s
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.full(len(s), 50.0), index=s.index)
    return ((s - lo) / (hi - lo) * 100).clip(0, 100)


def _format_value(value_col: str, value: Any) -> str:
    """Choose a hover number format from a column name."""
    name = str(value_col).lower()
    if any(token in name for token in ("margin", "growth", "rate", "percent", "%")):
        return _percent(value)
    if any(token in name for token in ("revenue", "sales", "profit", "target", "forecast", "value", "discount")):
        return _currency(value)
    return _number(value)


def _value_hover(value_col: str) -> str:
    """Plotly hover formatter for common metric types."""
    name = str(value_col).lower()
    if any(token in name for token in ("margin", "growth", "rate", "percent", "%")):
        return "%{x:.1f}%"
    if any(token in name for token in ("revenue", "sales", "profit", "target", "forecast", "value")):
        return "₹%{x:,.0f}"
    return "%{x:,.0f}"


def _add_zero_line(fig: go.Figure) -> None:
    fig.add_hline(y=0, line_color=BORDER, line_width=1)


# =====================================================================
# CORE / GENERIC CHART BUILDERS
# =====================================================================

def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Trend",
    *,
    name: Optional[str] = None,
    y_format: str = "number",
    color: Optional[str] = None,
    markers: bool = True,
) -> go.Figure:
    """Reusable line chart for time or ordered trends."""
    data = _clean_xy(df, x_col, y_col)
    if data.empty:
        return _empty_figure(title)

    mode = "lines+markers" if markers else "lines"
    line_color = color or BLUE
    hover = (
        f"%{{x}}<br>{name or y_col}: ₹%{{y:,.0f}}<extra></extra>"
        if y_format == "currency"
        else f"%{{x}}<br>{name or y_col}: %{{y:.1f}}%<extra></extra>"
        if y_format == "percent"
        else f"%{{x}}<br>{name or y_col}: %{{y:,.0f}}<extra></extra>"
    )
    fig = go.Figure(go.Scatter(
        x=data[x_col],
        y=data[y_col],
        mode=mode,
        name=name or y_col,
        line=dict(color=line_color, width=3),
        marker=dict(size=6, color=line_color),
        hovertemplate=hover,
    ))
    return _finish(fig, title)


def area_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Trend",
    *,
    name: Optional[str] = None,
    color: Optional[str] = None,
    y_format: str = "currency",
) -> go.Figure:
    """Reusable filled area trend chart."""
    data = _clean_xy(df, x_col, y_col)
    if data.empty:
        return _empty_figure(title)

    line_color = color or BLUE
    if y_format == "currency":
        hover = f"%{{x}}<br>{name or y_col}: ₹%{{y:,.0f}}<extra></extra>"
    elif y_format == "percent":
        hover = f"%{{x}}<br>{name or y_col}: %{{y:.1f}}%<extra></extra>"
    else:
        hover = f"%{{x}}<br>{name or y_col}: %{{y:,.0f}}<extra></extra>"

    fig = go.Figure(go.Scatter(
        x=data[x_col],
        y=data[y_col],
        mode="lines+markers",
        name=name or y_col,
        line=dict(color=line_color, width=3),
        marker=dict(size=5, color=line_color),
        fill="tozeroy",
        fillcolor=BLUE_FILL,
        hovertemplate=hover,
    ))
    return _finish(fig, title)


def bar_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Comparison",
    *,
    top_n: Optional[int] = None,
    horizontal: bool = False,
    color: Optional[str] = None,
) -> go.Figure:
    """Reusable categorical bar chart."""
    data = _clean_xy(df, category_col, value_col)
    if data.empty:
        return _empty_figure(title)

    data = data.groupby(category_col, as_index=False)[value_col].sum()
    data = data.sort_values(value_col, ascending=False)
    if top_n:
        data = data.head(top_n)

    if horizontal:
        data = data.sort_values(value_col)
        labels = _labels(data[category_col])
        fig = go.Figure(go.Bar(
            x=data[value_col],
            y=labels,
            orientation="h",
            marker_color=color or BLUE,
            hovertemplate=(
                "%{y}<br>" + _value_hover(value_col) + "<extra></extra>"
            ),
        ))
    else:
        labels = _labels(data[category_col])
        fig = go.Figure(go.Bar(
            x=labels,
            y=data[value_col],
            marker_color=color or BLUE,
            hovertemplate=(
                "%{x}<br>%{y:,.0f}<extra></extra>"
            ),
        ))
        fig.update_xaxes(tickangle=-35)

    return _finish(fig, title)


def horizontal_ranked_bar(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Top Rankings",
    *,
    top_n: int = 10,
    color: Optional[str] = None,
) -> go.Figure:
    """Horizontal ranked bar, intended for long labels and top-N lists."""
    return bar_chart(
        df,
        category_col,
        value_col,
        title,
        top_n=top_n,
        horizontal=True,
        color=color,
    )


def diverging_bar(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Positive vs Negative Change",
) -> go.Figure:
    """Bar chart with positive/negative values visually separated."""
    data = _clean_xy(df, category_col, value_col)
    if data.empty:
        return _empty_figure(title)

    data = data.groupby(category_col, as_index=False)[value_col].sum()
    data = data.sort_values(value_col)
    labels = _labels(data[category_col])
    colors = [SUCCESS if v >= 0 else DANGER for v in data[value_col]]

    fig = go.Figure(go.Bar(
        x=data[value_col],
        y=labels,
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}<br>Change: %{x:.1f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=BORDER, line_width=1)
    return _finish(fig, title)


def lollipop_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Rate / Margin Ranking",
    *,
    top_n: int = 10,
) -> go.Figure:
    """Dot-and-stem ranking chart for margins, rates and percentages."""
    data = _clean_xy(df, category_col, value_col)
    if data.empty:
        return _empty_figure(title)

    data = data.groupby(category_col, as_index=False)[value_col].mean()
    data = data.nlargest(top_n, value_col).sort_values(value_col)
    y = _labels(data[category_col])

    fig = go.Figure()
    for label, value in zip(y, data[value_col]):
        fig.add_trace(go.Scatter(
            x=[0, value],
            y=[label, label],
            mode="lines",
            line=dict(color="#CBD5E1", width=2),
            showlegend=False,
            hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=data[value_col],
        y=y,
        mode="markers",
        marker=dict(size=11, color=BLUE, line=dict(color="#0A1233", width=1)),
        name=value_col,
        hovertemplate="%{y}<br>Value: %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(ticksuffix="%")
    return _finish(fig, title)


def scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Relationship",
    *,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    labels: Optional[Mapping[str, str]] = None,
) -> go.Figure:
    """Reusable scatter plot. No OLS/statsmodels dependency."""
    required = [x_col, y_col]
    if color_col:
        required.append(color_col)
    if size_col:
        required.append(size_col)
    if not _has_columns(df, required):
        return _empty_figure(title)

    data = df[required].copy()
    data[x_col] = pd.to_numeric(data[x_col], errors="coerce")
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    if size_col:
        data[size_col] = pd.to_numeric(data[size_col], errors="coerce")
    data = data.dropna(subset=[x_col, y_col])

    if data.empty:
        return _empty_figure(title)

    fig = go.Figure()
    if color_col:
        groups = data[color_col].astype(str).fillna("Unknown")
        for i, group in enumerate(groups.unique()):
            part = data.loc[groups == group]
            marker = dict(
                color=PALETTE[i % len(PALETTE)],
                size=8,
                opacity=0.78,
                line=dict(color="#0A1233", width=1),
            )
            if size_col:
                sizes = part[size_col].abs().fillna(0)
                if sizes.max() > 0:
                    marker["size"] = 8 + 22 * (sizes / sizes.max())
            fig.add_trace(go.Scatter(
                x=part[x_col],
                y=part[y_col],
                mode="markers",
                name=_short_label(group),
                marker=marker,
                customdata=part[[color_col]].values,
                hovertemplate=(
                    f"{x_col}: %{{x:,.2f}}<br>"
                    f"{y_col}: %{{y:,.2f}}<br>"
                    f"{color_col}: %{{customdata[0]}}<extra></extra>"
                ),
            ))
    else:
        marker = dict(
            color=BLUE,
            size=9,
            opacity=0.75,
            line=dict(color="#0A1233", width=1),
        )
        if size_col:
            sizes = data[size_col].abs().fillna(0)
            if sizes.max() > 0:
                marker["size"] = 8 + 22 * (sizes / sizes.max())
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode="markers",
            marker=marker,
            hovertemplate=(
                f"{x_col}: %{{x:,.2f}}<br>"
                f"{y_col}: %{{y:,.2f}}<extra></extra>"
            ),
        ))

    if labels:
        fig.update_layout(xaxis_title=labels.get(x_col, x_col), yaxis_title=labels.get(y_col, y_col))
    return _finish(fig, title)


def bubble_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    size_col: str,
    title: str = "Bubble Analysis",
    *,
    color_col: Optional[str] = None,
) -> go.Figure:
    """Bubble chart: x + y relationship with a third numeric dimension."""
    return scatter_chart(
        df,
        x_col,
        y_col,
        title,
        color_col=color_col,
        size_col=size_col,
    )


def donut_chart(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str = "Contribution",
    *,
    top_n: int = 8,
) -> go.Figure:
    """Donut contribution chart."""
    data = _clean_xy(df, label_col, value_col)
    if data.empty:
        return _empty_figure(title)

    data = data.groupby(label_col, as_index=False)[value_col].sum()
    data = data.nlargest(top_n, value_col)
    fig = go.Figure(go.Pie(
        labels=_labels(data[label_col], 28),
        values=data[value_col],
        hole=0.58,
        sort=False,
        marker=dict(colors=[PALETTE[i % len(PALETTE)] for i in range(len(data))]),
        textinfo="percent",
        hovertemplate="%{label}<br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    return _finish(fig, title)


def treemap_chart(
    df: pd.DataFrame,
    path: Sequence[str],
    value_col: str,
    title: str = "Contribution Treemap",
) -> go.Figure:
    """Hierarchical contribution treemap."""
    required = list(path) + [value_col]
    if not _has_columns(df, required):
        return _empty_figure(title)

    data = df[required].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[value_col])
    for col in path:
        data[col] = data[col].fillna("Unknown").astype(str)

    if data.empty:
        return _empty_figure(title)

    data = data.groupby(list(path), as_index=False)[value_col].sum()
    fig = go.Figure(go.Treemap(
        ids=data[path].astype(str).agg(" / ".join, axis=1),
        labels=data[path[-1]].map(lambda x: _short_label(x, 30)),
        parents=(
            data[path[:-1]].astype(str).agg(" / ".join, axis=1)
            if len(path) > 1
            else [""] * len(data)
        ),
        values=data[value_col],
        branchvalues="total",
        marker=dict(colors=[PALETTE[i % len(PALETTE)] for i in range(len(data))]),
        hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>",
    ))
    return _finish(fig, title)


def sunburst_chart(
    df: pd.DataFrame,
    path: Sequence[str],
    value_col: str,
    title: str = "Hierarchy",
) -> go.Figure:
    """Hierarchical category/subcategory sunburst."""
    required = list(path) + [value_col]
    if not _has_columns(df, required):
        return _empty_figure(title)

    data = df[required].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[value_col])
    for col in path:
        data[col] = data[col].fillna("Unknown").astype(str)

    if data.empty:
        return _empty_figure(title)

    data = data.groupby(list(path), as_index=False)[value_col].sum()
    fig = go.Figure(go.Sunburst(
        labels=data[path[-1]].map(lambda x: _short_label(x, 28)),
        parents=(
            data[path[:-1]].astype(str).agg(" / ".join, axis=1)
            if len(path) > 1
            else [""] * len(data)
        ),
        values=data[value_col],
        branchvalues="total",
        marker=dict(colors=[PALETTE[i % len(PALETTE)] for i in range(len(data))]),
        hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>",
    ))
    return _finish(fig, title)


def heatmap(
    matrix: pd.DataFrame,
    title: str = "Heatmap",
    *,
    value_format: str = "number",
) -> go.Figure:
    """Heatmap for two-dimensional business patterns."""
    if not isinstance(matrix, pd.DataFrame) or matrix.empty:
        return _empty_figure(title)

    data = matrix.copy()
    data = data.apply(pd.to_numeric, errors="coerce")
    if data.empty:
        return _empty_figure(title)

    hover_format = "₹%{z:,.0f}" if value_format == "currency" else "%{z:,.1f}%" if value_format == "percent" else "%{z:,.0f}"
    fig = go.Figure(go.Heatmap(
        z=data.values,
        x=[_short_label(v, 24) for v in data.columns],
        y=[_short_label(v, 24) for v in data.index],
        colorscale=[
            [0, "#0F1C45"],
            [0.5, "#3B6FE0"],
            [1, "#22D3EE"],
        ],
        colorbar=dict(title="Value"),
        hovertemplate="%{y} / %{x}<br>" + hover_format + "<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-35)
    return _finish(fig, title)


def box_plot(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Distribution by Category",
    *,
    top_n: int = 10,
) -> go.Figure:
    """Box plot for distributions and outliers."""
    if not _has_columns(df, [category_col, value_col]):
        return _empty_figure(title)

    data = df[[category_col, value_col]].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[category_col, value_col])
    if data.empty:
        return _empty_figure(title)

    top = data.groupby(category_col)[value_col].sum().nlargest(top_n).index
    data = data[data[category_col].isin(top)]
    order = list(top)

    fig = go.Figure()
    for i, category in enumerate(order):
        part = data[data[category_col] == category]
        fig.add_trace(go.Box(
            y=part[value_col],
            name=_short_label(category),
            marker_color=PALETTE[i % len(PALETTE)],
            boxmean=True,
            hovertemplate="%{y:,.2f}<extra></extra>",
        ))
    fig.update_xaxes(tickangle=-35)
    return _finish(fig, title)


def violin_plot(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Distribution Profile",
    *,
    top_n: int = 8,
) -> go.Figure:
    """Violin plot for distribution shape and density."""
    if not _has_columns(df, [category_col, value_col]):
        return _empty_figure(title)

    data = df[[category_col, value_col]].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[category_col, value_col])
    if data.empty:
        return _empty_figure(title)

    top = data.groupby(category_col)[value_col].sum().nlargest(top_n).index
    data = data[data[category_col].isin(top)]

    fig = go.Figure()
    for i, category in enumerate(top):
        part = data[data[category_col] == category]
        fig.add_trace(go.Violin(
            y=part[value_col],
            name=_short_label(category),
            box_visible=True,
            meanline_visible=True,
            line_color=PALETTE[i % len(PALETTE)],
            fillcolor=BLUE_LIGHT,
            opacity=0.8,
        ))
    fig.update_xaxes(tickangle=-35)
    return _finish(fig, title)


def histogram(
    df: pd.DataFrame,
    value_col: str,
    title: str = "Distribution",
    *,
    bins: int = 30,
) -> go.Figure:
    """Histogram for frequency distributions."""
    if not _has_columns(df, [value_col]):
        return _empty_figure(title)

    values = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if values.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Histogram(
        x=values,
        nbinsx=max(5, bins),
        marker_color=BLUE,
        opacity=0.82,
        hovertemplate="Range: %{x}<br>Count: %{y}<extra></extra>",
    ))
    return _finish(fig, title)


def radar_chart(
    df: pd.DataFrame,
    category_col: str,
    metric_cols: Sequence[str],
    title: str = "Normalized Profile",
    *,
    max_categories: int = 5,
) -> go.Figure:
    """
    Radar chart with every metric normalized independently to 0-100.

    This prevents raw metrics with incompatible units/scales from being
    compared directly.
    """
    required = [category_col] + list(metric_cols)
    if not _has_columns(df, required):
        return _empty_figure(title)

    data = df[required].copy()
    for col in metric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=list(metric_cols), how="all")
    if data.empty:
        return _empty_figure(title)

    # Aggregate multiple rows per category before normalization.
    data = data.groupby(category_col, as_index=False)[list(metric_cols)].mean()
    data = data.head(max_categories)

    # Normalize each metric independently across categories.
    normalized = pd.DataFrame({category_col: data[category_col]})
    for col in metric_cols:
        normalized[col] = _normalize_0_100(data[col])

    fig = go.Figure()
    for i, row in normalized.iterrows():
        values = [float(row[col]) if pd.notna(row[col]) else 0 for col in metric_cols]
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=list(metric_cols) + [metric_cols[0]],
            fill="toself",
            name=_short_label(row[category_col], 22),
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            opacity=0.55,
        ))

    fig.update_polars(
        radialaxis=dict(
            visible=True,
            range=[0, 100],
            tickvals=[0, 25, 50, 75, 100],
            gridcolor="#E5E7EB",
        ),
        angularaxis=dict(gridcolor="#E5E7EB"),
    )
    return _finish(fig, title)


def waterfall_chart(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str = "Change Bridge",
) -> go.Figure:
    """Waterfall chart for explaining movement from one value to another."""
    if not _has_columns(df, [label_col, value_col]):
        return _empty_figure(title)

    data = df[[label_col, value_col]].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[value_col])
    if data.empty:
        return _empty_figure(title)

    measures = ["relative"] * len(data)
    fig = go.Figure(go.Waterfall(
        x=_labels(data[label_col], 28),
        y=data[value_col],
        measure=measures,
        connector=dict(line=dict(color=BORDER)),
        increasing=dict(marker_color=SUCCESS),
        decreasing=dict(marker_color=DANGER),
        totals=dict(marker_color=BLUE),
        hovertemplate="%{x}<br>Change: ₹%{y:,.0f}<extra></extra>",
    ))
    return _finish(fig, title)


def gauge_chart(
    value: float,
    title: str = "Performance Score",
    *,
    min_value: float = 0,
    max_value: float = 100,
    suffix: str = "%",
) -> go.Figure:
    """Gauge for target attainment, data quality or score metrics."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = min_value

    numeric = float(np.clip(numeric, min_value, max_value))
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=numeric,
        number=dict(suffix=suffix, font=dict(size=28, color=TEXT)),
        gauge=dict(
            axis=dict(range=[min_value, max_value], tickcolor=MUTED),
            bar=dict(color=BLUE),
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER,
            steps=[
                {"range": [min_value, min_value + (max_value - min_value) * 0.5], "color": "rgba(132,160,255,0.08)"},
                {"range": [min_value + (max_value - min_value) * 0.5, max_value], "color": BLUE_LIGHT},
            ],
        ),
    ))
    return _finish(fig, title, height=300)


# =====================================================================
# EXECUTIVE OVERVIEW
# =====================================================================

def monthly_revenue_chart(monthly_df: pd.DataFrame, title: str = "Monthly Revenue") -> go.Figure:
    return area_chart(monthly_df, "Month", "Revenue", title, y_format="currency")


def monthly_profit_chart(monthly_df: pd.DataFrame, title: str = "Monthly Profit") -> go.Figure:
    return line_chart(monthly_df, "Month", "Profit", title, y_format="currency", color=SUCCESS)


def revenue_by_category_chart(df: pd.DataFrame, title: str = "Revenue by Category") -> go.Figure:
    return horizontal_ranked_bar(df, "Category", "Revenue", title, top_n=10)


def profit_margin_by_category_chart(
    df: pd.DataFrame,
    title: str = "Profit Margin by Category",
) -> go.Figure:
    margin_col = "Profit Margin" if "Profit Margin" in df.columns else "Margin"
    return lollipop_chart(df, "Category", margin_col, title, top_n=10)


def revenue_by_region_chart(df: pd.DataFrame, title: str = "Revenue by Region") -> go.Figure:
    return horizontal_ranked_bar(df, "Region", "Revenue", title, top_n=10)


def revenue_by_segment_chart(df: pd.DataFrame, title: str = "Revenue by Segment") -> go.Figure:
    return bar_chart(df, "Segment", "Revenue", title, top_n=10)


def top_products_chart(df: pd.DataFrame, title: str = "Top Products") -> go.Figure:
    return horizontal_ranked_bar(df, "Product", "Revenue", title, top_n=10)


def sales_vs_profit_chart(df: pd.DataFrame, title: str = "Sales vs Profit") -> go.Figure:
    return scatter_chart(df, "Revenue", "Profit", title)


# =====================================================================
# SALES PERFORMANCE
# =====================================================================

def revenue_trend_chart(monthly_df: pd.DataFrame, title: str = "Revenue Trend") -> go.Figure:
    return monthly_revenue_chart(monthly_df, title)


def profit_trend_chart(monthly_df: pd.DataFrame, title: str = "Profit Trend") -> go.Figure:
    return monthly_profit_chart(monthly_df, title)


def growth_waterfall_chart(
    df: pd.DataFrame,
    label_col: str = "Month",
    value_col: str = "Growth",
    title: str = "Growth Waterfall",
) -> go.Figure:
    return waterfall_chart(df, label_col, value_col, title)


def seasonality_heatmap(
    matrix: pd.DataFrame,
    title: str = "Seasonality Heatmap",
) -> go.Figure:
    return heatmap(matrix, title, value_format="currency")


def category_comparison_chart(
    df: pd.DataFrame,
    title: str = "Category Comparison",
) -> go.Figure:
    return horizontal_ranked_bar(df, "Category", "Revenue", title, top_n=10)


def discount_scatter_chart(
    df: pd.DataFrame,
    title: str = "Discount vs Revenue",
) -> go.Figure:
    return scatter_chart(df, "Discount", "Revenue", title)


def order_distribution_chart(
    df: pd.DataFrame,
    value_col: str = "Order Value",
    title: str = "Order Value Distribution",
) -> go.Figure:
    return histogram(df, value_col, title)


def segment_radar_chart(
    df: pd.DataFrame,
    title: str = "Segment Profile",
) -> go.Figure:
    metrics = [c for c in ["Revenue", "Profit", "Orders", "Quantity", "Profit Margin"] if c in df.columns]
    return radar_chart(df, "Segment", metrics, title)


# =====================================================================
# PRODUCTS & CATEGORIES
# =====================================================================

def category_revenue_chart(df: pd.DataFrame, title: str = "Category Revenue") -> go.Figure:
    return horizontal_ranked_bar(df, "Category", "Revenue", title, top_n=10)


def category_profit_chart(df: pd.DataFrame, title: str = "Category Profit") -> go.Figure:
    return horizontal_ranked_bar(df, "Category", "Profit", title, top_n=10)


def category_margin_chart(df: pd.DataFrame, title: str = "Category Margin") -> go.Figure:
    margin_col = "Profit Margin" if "Profit Margin" in df.columns else "Margin"
    return lollipop_chart(df, "Category", margin_col, title, top_n=10)


def category_radar_chart(
    df: pd.DataFrame,
    title: str = "Category Profile",
) -> go.Figure:
    metrics = [c for c in ["Revenue", "Profit", "Orders", "Quantity", "Profit Margin"] if c in df.columns]
    return radar_chart(df, "Category", metrics, title)


def product_treemap_chart(
    df: pd.DataFrame,
    title: str = "Product Contribution",
) -> go.Figure:
    return treemap_chart(df, ["Category", "Product"], "Revenue", title)


def product_ranking_chart(
    df: pd.DataFrame,
    title: str = "Product Ranking",
) -> go.Figure:
    return horizontal_ranked_bar(df, "Product", "Revenue", title, top_n=10)


def product_profitability_scatter(
    df: pd.DataFrame,
    title: str = "Product Profitability",
) -> go.Figure:
    return scatter_chart(df, "Revenue", "Profit", title, color_col="Category" if "Category" in df.columns else None)


def category_subcategory_sunburst(
    df: pd.DataFrame,
    title: str = "Category to Subcategory",
) -> go.Figure:
    return sunburst_chart(df, ["Category", "Subcategory"], "Revenue", title)


def product_distribution_chart(
    df: pd.DataFrame,
    value_col: str = "Revenue",
    title: str = "Product Distribution",
) -> go.Figure:
    return histogram(df, value_col, title)


# =====================================================================
# REGIONS
# =====================================================================

def regional_revenue_chart(df: pd.DataFrame, title: str = "Regional Revenue") -> go.Figure:
    return horizontal_ranked_bar(df, "Region", "Revenue", title, top_n=10)


def regional_profit_chart(df: pd.DataFrame, title: str = "Regional Profit") -> go.Figure:
    return horizontal_ranked_bar(df, "Region", "Profit", title, top_n=10)


def regional_margin_chart(df: pd.DataFrame, title: str = "Regional Margin") -> go.Figure:
    margin_col = "Profit Margin" if "Profit Margin" in df.columns else "Margin"
    return lollipop_chart(df, "Region", margin_col, title, top_n=10)


def regional_treemap_chart(
    df: pd.DataFrame,
    title: str = "Regional Contribution",
) -> go.Figure:
    path = ["Region", "City"] if "City" in df.columns else ["Region"]
    return treemap_chart(df, path, "Revenue", title)


def regional_radar_chart(
    df: pd.DataFrame,
    title: str = "Regional Profile",
) -> go.Figure:
    metrics = [c for c in ["Revenue", "Profit", "Orders", "Quantity", "Profit Margin"] if c in df.columns]
    return radar_chart(df, "Region", metrics, title)


def regional_trend_chart(
    df: pd.DataFrame,
    region_col: str = "Region",
    value_col: str = "Revenue",
    title: str = "Regional Trend",
) -> go.Figure:
    if not _has_columns(df, ["Month", region_col, value_col]):
        return _empty_figure(title)

    data = df[["Month", region_col, value_col]].copy()
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=["Month", region_col, value_col])
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure()
    for i, region in enumerate(data[region_col].astype(str).unique()):
        part = data[data[region_col].astype(str) == region]
        part = part.groupby("Month", as_index=False)[value_col].sum().sort_values("Month")
        fig.add_trace(go.Scatter(
            x=part["Month"],
            y=part[value_col],
            mode="lines+markers",
            name=_short_label(region),
            line=dict(color=PALETTE[i % len(PALETTE)], width=2.5),
            marker=dict(size=5),
            hovertemplate=f"{region}<br>%{{x}}<br>₹%{{y:,.0f}}<extra></extra>",
        ))
    return _finish(fig, title)


def regional_scatter_chart(
    df: pd.DataFrame,
    title: str = "Regional Revenue vs Profit",
) -> go.Figure:
    return scatter_chart(df, "Revenue", "Profit", title, color_col="Region" if "Region" in df.columns else None)


def regional_heatmap_chart(
    matrix: pd.DataFrame,
    title: str = "Regional Heatmap",
) -> go.Figure:
    return heatmap(matrix, title, value_format="currency")


# =====================================================================
# FORECASTING
# =====================================================================

def historical_forecast_chart(
    monthly_df: pd.DataFrame,
    forecast_table: pd.DataFrame,
    title: str = "Historical Revenue and Forecast",
) -> go.Figure:
    """Historical actuals followed by a forecast series."""
    if not _has_columns(monthly_df, ["Month", "Revenue"]):
        return _empty_figure(title)

    actual = monthly_df[["Month", "Revenue"]].copy()
    actual["Revenue"] = pd.to_numeric(actual["Revenue"], errors="coerce")
    actual = actual.dropna(subset=["Month", "Revenue"])

    fig = go.Figure()
    if not actual.empty:
        fig.add_trace(go.Scatter(
            x=actual["Month"],
            y=actual["Revenue"],
            mode="lines+markers",
            name="Historical Actual",
            line=dict(color=BLUE, width=3),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Actual: ₹%{y:,.0f}<extra></extra>",
        ))

    if isinstance(forecast_table, pd.DataFrame) and not forecast_table.empty and _has_columns(forecast_table, ["Month", "Forecast"]):
        fc = forecast_table[["Month", "Forecast"]].copy()
        fc["Forecast"] = pd.to_numeric(fc["Forecast"], errors="coerce")
        fc = fc.dropna(subset=["Month", "Forecast"])

        if not fc.empty:
            bridge_x = ([actual["Month"].iloc[-1]] if not actual.empty else []) + list(fc["Month"])
            bridge_y = ([actual["Revenue"].iloc[-1]] if not actual.empty else []) + list(fc["Forecast"])
            fig.add_trace(go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines+markers",
                name="Forecast",
                line=dict(color=BLUE_ACCENT, width=3, dash="dash"),
                marker=dict(size=6),
                hovertemplate="%{x}<br>Forecast: ₹%{y:,.0f}<extra></extra>",
            ))

    return _finish(fig, title)


def forecast_confidence_band(
    forecast_table: pd.DataFrame,
    title: str = "Forecast Confidence Band",
) -> go.Figure:
    """Forecast line with a lower/upper confidence interval."""
    required = ["Month", "Forecast", "Lower Bound", "Upper Bound"]
    if not _has_columns(forecast_table, required):
        return _empty_figure(title)

    data = forecast_table[required].copy()
    for col in required[1:]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=required)
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(data["Month"]) + list(data["Month"])[::-1],
        y=list(data["Upper Bound"]) + list(data["Lower Bound"])[::-1],
        fill="toself",
        fillcolor=BLUE_BAND,
        line=dict(color=TRANSPARENT),
        name="Confidence Range",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=data["Month"],
        y=data["Forecast"],
        mode="lines+markers",
        name="Forecast",
        line=dict(color=BLUE, width=3),
        marker=dict(size=7),
        hovertemplate="%{x}<br>Forecast: ₹%{y:,.0f}<extra></extra>",
    ))
    return _finish(fig, title)


def model_accuracy_chart(
    df: pd.DataFrame,
    model_col: str = "Model",
    metric_col: str = "MAPE",
    title: str = "Model Accuracy",
) -> go.Figure:
    return horizontal_ranked_bar(
        df,
        model_col,
        metric_col,
        title,
        top_n=10,
        color=BLUE_ACCENT,
    )


def model_radar_chart(
    df: pd.DataFrame,
    model_col: str = "Model",
    title: str = "Model Performance Profile",
) -> go.Figure:
    metrics = [c for c in ["Accuracy", "MAPE", "MAE", "R2", "Stability"] if c in df.columns]
    if not metrics:
        return _empty_figure(title)
    return radar_chart(df, model_col, metrics, title)


def forecast_waterfall_chart(
    df: pd.DataFrame,
    label_col: str = "Month",
    value_col: str = "Forecast",
    title: str = "Forecast Movement",
) -> go.Figure:
    return waterfall_chart(df, label_col, value_col, title)


def monthly_forecast_chart(
    forecast_table: pd.DataFrame,
    title: str = "Monthly Forecast",
) -> go.Figure:
    if not _has_columns(forecast_table, ["Month", "Forecast"]):
        return _empty_figure(title)
    return line_chart(
        forecast_table,
        "Month",
        "Forecast",
        title,
        name="Forecast",
        y_format="currency",
        color=BLUE_ACCENT,
    )


def actual_vs_predicted_chart(
    df: pd.DataFrame,
    actual_col: str = "Actual",
    predicted_col: str = "Predicted",
    title: str = "Actual vs Predicted",
) -> go.Figure:
    required = [actual_col, predicted_col]
    if not _has_columns(df, required):
        return _empty_figure(title)

    data = df[required].copy()
    data[actual_col] = pd.to_numeric(data[actual_col], errors="coerce")
    data[predicted_col] = pd.to_numeric(data[predicted_col], errors="coerce")
    data = data.dropna()
    if data.empty:
        return _empty_figure(title)

    lo = float(min(data[actual_col].min(), data[predicted_col].min()))
    hi = float(max(data[actual_col].max(), data[predicted_col].max()))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[actual_col],
        y=data[predicted_col],
        mode="markers",
        name="Observations",
        marker=dict(color=BLUE, size=9, opacity=0.75),
        hovertemplate="Actual: ₹%{x:,.0f}<br>Predicted: ₹%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[lo, hi],
        y=[lo, hi],
        mode="lines",
        name="Perfect Fit",
        line=dict(color=MUTED, dash="dash", width=2),
        hoverinfo="skip",
    ))
    fig.update_xaxes(title=actual_col)
    fig.update_yaxes(title=predicted_col)
    return _finish(fig, title)


def forecast_error_distribution(
    df: pd.DataFrame,
    error_col: str = "Error",
    title: str = "Forecast Error Distribution",
) -> go.Figure:
    return histogram(df, error_col, title)


# =====================================================================
# ANOMALIES & RISK
# =====================================================================

def anomaly_timeline_chart(
    monthly_df: pd.DataFrame,
    anomalies: pd.DataFrame,
    title: str = "Anomaly Timeline",
) -> go.Figure:
    return anomaly_scatter(monthly_df, anomalies, title)


def severity_donut_chart(
    df: pd.DataFrame,
    severity_col: str = "Severity",
    title: str = "Anomaly Severity",
) -> go.Figure:
    if not _has_columns(df, [severity_col]):
        return _empty_figure(title)

    data = df[[severity_col]].copy()
    data[severity_col] = data[severity_col].fillna("Unknown").astype(str)
    counts = data[severity_col].value_counts().rename_axis(severity_col).reset_index(name="Count")

    fig = go.Figure(go.Pie(
        labels=counts[severity_col],
        values=counts["Count"],
        hole=0.58,
        marker=dict(colors=[PALETTE[i % len(PALETTE)] for i in range(len(counts))]),
        textinfo="percent",
        hovertemplate="%{label}<br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    return _finish(fig, title)


def anomaly_heatmap_chart(
    matrix: pd.DataFrame,
    title: str = "Anomaly Heatmap",
) -> go.Figure:
    return heatmap(matrix, title, value_format="number")


def anomaly_distribution_chart(
    df: pd.DataFrame,
    value_col: str = "Revenue",
    title: str = "Anomaly Distribution",
) -> go.Figure:
    return histogram(df, value_col, title)


def profit_anomaly_scatter(
    df: pd.DataFrame,
    title: str = "Profit Anomaly Analysis",
) -> go.Figure:
    return scatter_chart(
        df,
        "Revenue",
        "Profit",
        title,
        color_col="Severity" if "Severity" in df.columns else None,
        size_col="Anomaly Score" if "Anomaly Score" in df.columns else None,
    )


def discount_risk_scatter(
    df: pd.DataFrame,
    title: str = "Discount Risk Analysis",
) -> go.Figure:
    return scatter_chart(
        df,
        "Discount",
        "Profit",
        title,
        color_col="Severity" if "Severity" in df.columns else None,
        size_col="Revenue" if "Revenue" in df.columns else None,
    )


def risk_radar_chart(
    df: pd.DataFrame,
    category_col: str = "Category",
    title: str = "Risk Profile",
) -> go.Figure:
    metrics = [c for c in ["Anomaly Score", "Discount", "Profit Loss", "Risk Score"] if c in df.columns]
    if not metrics:
        return _empty_figure(title)
    return radar_chart(df, category_col, metrics, title)


def risk_treemap_chart(
    df: pd.DataFrame,
    title: str = "Risk Contribution",
) -> go.Figure:
    if "Severity" in df.columns and "Category" in df.columns:
        return treemap_chart(df, ["Severity", "Category"], "Revenue", title)
    if "Category" in df.columns:
        return treemap_chart(df, ["Category"], "Revenue", title)
    return _empty_figure(title)


# =====================================================================
# PRESERVED / BACKWARD-COMPATIBLE PROJECT FUNCTIONS
# =====================================================================

def monthly_trend_chart(
    monthly_df: pd.DataFrame,
    title: str = "Monthly Revenue Trend",
) -> go.Figure:
    """Backward-compatible monthly revenue trend."""
    return monthly_revenue_chart(monthly_df, title)


def growth_chart(
    monthly_df: pd.DataFrame,
    title: str = "Month-over-Month Growth",
) -> go.Figure:
    """Backward-compatible growth chart."""
    if not _has_columns(monthly_df, ["Month", "Growth %"]):
        return _empty_figure(title)

    data = monthly_df[["Month", "Growth %"]].copy()
    data["Growth %"] = pd.to_numeric(data["Growth %"], errors="coerce").fillna(0)
    data = data.dropna(subset=["Month"])

    colors = [SUCCESS if v >= 0 else DANGER for v in data["Growth %"]]
    fig = go.Figure(go.Bar(
        x=data["Month"],
        y=data["Growth %"],
        marker_color=colors,
        hovertemplate="%{x}<br>Growth: %{y:.1f}%<extra></extra>",
    ))
    _add_zero_line(fig)
    fig.update_yaxes(ticksuffix="%")
    return _finish(fig, title)


def contribution_pie(
    perf_df: pd.DataFrame,
    dim: str,
    title: Optional[str] = None,
) -> go.Figure:
    """Backward-compatible revenue contribution donut."""
    return donut_chart(
        perf_df,
        dim,
        "Revenue",
        title or f"Revenue Contribution by {dim}",
        top_n=8,
    )


def bar_by_dimension(
    perf_df: pd.DataFrame,
    dim: str,
    value_col: str = "Revenue",
    title: Optional[str] = None,
    top_n: int = 10,
) -> go.Figure:
    """Backward-compatible horizontal ranking chart."""
    return horizontal_ranked_bar(
        perf_df,
        dim,
        value_col,
        title or f"{value_col} by {dim}",
        top_n=top_n,
    )


def actual_vs_target_chart(
    monthly_df: pd.DataFrame,
    target_col: str = "Target",
    title: str = "Actual vs Target",
) -> go.Figure:
    """Backward-compatible actual-versus-target chart."""
    if not _has_columns(monthly_df, ["Month", "Revenue"]):
        return _empty_figure(title)

    data = monthly_df[["Month", "Revenue"] + ([target_col] if target_col in monthly_df.columns else [])].copy()
    data["Revenue"] = pd.to_numeric(data["Revenue"], errors="coerce")
    data = data.dropna(subset=["Month", "Revenue"])

    fig = go.Figure(go.Bar(
        x=data["Month"],
        y=data["Revenue"],
        name="Actual",
        marker_color=BLUE,
        hovertemplate="%{x}<br>Actual: ₹%{y:,.0f}<extra></extra>",
    ))
    if target_col in data.columns:
        data[target_col] = pd.to_numeric(data[target_col], errors="coerce")
        fig.add_trace(go.Scatter(
            x=data["Month"],
            y=data[target_col],
            name="Target",
            mode="lines+markers",
            line=dict(color=DANGER, dash="dash", width=2.5),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Target: ₹%{y:,.0f}<extra></extra>",
        ))
    return _finish(fig, title)


def forecast_chart(
    monthly_df: pd.DataFrame,
    forecast_table: pd.DataFrame,
    title: str = "Sales Forecast",
) -> go.Figure:
    """Backward-compatible historical + forecast chart with bounds."""
    if not _has_columns(monthly_df, ["Month", "Revenue"]):
        return _empty_figure(title)

    actual = monthly_df[["Month", "Revenue"]].copy()
    actual["Revenue"] = pd.to_numeric(actual["Revenue"], errors="coerce")
    actual = actual.dropna(subset=["Month", "Revenue"])

    fig = go.Figure()
    if not actual.empty:
        fig.add_trace(go.Scatter(
            x=actual["Month"],
            y=actual["Revenue"],
            mode="lines+markers",
            name="Historical Actual",
            line=dict(color=BLUE, width=3),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Actual: ₹%{y:,.0f}<extra></extra>",
        ))

    if (
        isinstance(forecast_table, pd.DataFrame)
        and not forecast_table.empty
        and _has_columns(forecast_table, ["Month", "Forecast"])
    ):
        fc = forecast_table.copy()
        fc["Forecast"] = pd.to_numeric(fc["Forecast"], errors="coerce")
        fc = fc.dropna(subset=["Month", "Forecast"])

        if not fc.empty:
            bridge_x = ([actual["Month"].iloc[-1]] if not actual.empty else []) + list(fc["Month"])
            bridge_y = ([actual["Revenue"].iloc[-1]] if not actual.empty else []) + list(fc["Forecast"])
            fig.add_trace(go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines+markers",
                name="Forecast",
                line=dict(color=BLUE_ACCENT, width=3, dash="dash"),
                marker=dict(size=6),
                hovertemplate="%{x}<br>Forecast: ₹%{y:,.0f}<extra></extra>",
            ))

            if {"Lower Bound", "Upper Bound"}.issubset(fc.columns):
                fc["Lower Bound"] = pd.to_numeric(fc["Lower Bound"], errors="coerce")
                fc["Upper Bound"] = pd.to_numeric(fc["Upper Bound"], errors="coerce")
                band = fc.dropna(subset=["Lower Bound", "Upper Bound"])
                if not band.empty:
                    fig.add_trace(go.Scatter(
                        x=list(band["Month"]) + list(band["Month"])[::-1],
                        y=list(band["Upper Bound"]) + list(band["Lower Bound"])[::-1],
                        fill="toself",
                        fillcolor=BLUE_BAND,
                        line=dict(color=TRANSPARENT),
                        name="Forecast Range",
                        hoverinfo="skip",
                    ))

    return _finish(fig, title)


def heatmap_chart(
    matrix: pd.DataFrame,
    title: str = "Product x Region Revenue Heatmap",
) -> go.Figure:
    """Backward-compatible heatmap."""
    return heatmap(matrix, title, value_format="currency")


def scenario_comparison_chart(
    scenario_values: Mapping[str, Any],
    title: str = "Scenario Comparison",
) -> go.Figure:
    """Backward-compatible scenario comparison chart."""
    if not scenario_values:
        return _empty_figure(title)

    names = list(scenario_values.keys())
    values = pd.to_numeric(pd.Series(list(scenario_values.values())), errors="coerce").fillna(0)
    fig = go.Figure(go.Bar(
        x=[_short_label(v) for v in names],
        y=values,
        marker_color=[PALETTE[i % len(PALETTE)] for i in range(len(names))],
        hovertemplate="%{x}<br>Value: ₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-25)
    return _finish(fig, title)


def anomaly_scatter(
    monthly_df: pd.DataFrame,
    anomalies: pd.DataFrame,
    title: str = "Revenue with Anomalies Highlighted",
) -> go.Figure:
    """
    Robust backward-compatible anomaly timeline.

    Accepts monthly/anomaly data where the date information may be stored as:
    - Month
    - Period
    - Date
    - _date
    - Order Date
    - DatetimeIndex
    - PeriodIndex
    - generic index containing date values

    The function always normalizes the plotting date to a real datetime
    column before passing it to Plotly.
    """

    # ==============================================================
    # INTERNAL DATE NORMALIZER
    # ==============================================================

    def _extract_date(
        frame: pd.DataFrame,
        candidates: list,
    ):
        """
        Find and normalize a date source from columns or index.
        Returns a pandas Series of datetime values or None.
        """

        if not isinstance(frame, pd.DataFrame):
            return None

        # ----------------------------------------------------------
        # 1. Look for known date columns
        # ----------------------------------------------------------

        for column in candidates:
            if column in frame.columns:
                try:
                    dates = pd.to_datetime(
                        frame[column],
                        errors="coerce",
                    )

                    if dates.notna().any():
                        return dates

                except Exception:
                    continue

        # ----------------------------------------------------------
        # 2. Try datetime / period index
        # ----------------------------------------------------------

        try:
            if isinstance(
                frame.index,
                (
                    pd.DatetimeIndex,
                    pd.PeriodIndex,
                ),
            ):
                dates = pd.to_datetime(
                    frame.index,
                    errors="coerce",
                )

                if dates.notna().any():
                    return pd.Series(
                        dates,
                        index=frame.index,
                    )

        except Exception:
            pass

        # ----------------------------------------------------------
        # 3. Last fallback: try generic index
        # ----------------------------------------------------------

        try:
            dates = pd.to_datetime(
                frame.index,
                errors="coerce",
            )

            if dates.notna().any():
                return pd.Series(
                    dates,
                    index=frame.index,
                )

        except Exception:
            pass

        return None

    # ==============================================================
    # 1. VALIDATE MONTHLY DATA
    # ==============================================================

    if not isinstance(
        monthly_df,
        pd.DataFrame,
    ):
        return _empty_figure(title)

    if monthly_df.empty:
        return _empty_figure(title)

    monthly = monthly_df.copy()

    # Remove duplicate columns safely
    try:
        monthly = monthly.loc[
            :,
            ~monthly.columns.duplicated(),
        ]
    except Exception:
        pass

    # ==============================================================
    # 2. FIND REVENUE COLUMN
    # ==============================================================

    revenue_column = None

    for column in [
        "Revenue",
        "Sales",
        "Amount",
        "Total Sales",
        "Actual Revenue",
    ]:
        if column in monthly.columns:
            revenue_column = column
            break

    if revenue_column is None:
        return _empty_figure(title)

    # ==============================================================
    # 3. FIND MONTH / DATE
    # ==============================================================

    monthly_dates = _extract_date(
        monthly,
        [
            "Month",
            "Period",
            "Date",
            "_date",
            "Order Date",
            "Order_Date",
            "Timestamp",
        ],
    )

    if monthly_dates is None:
        return _empty_figure(title)

    # ==============================================================
    # 4. BUILD STANDARD MONTHLY DATA
    # ==============================================================

    data = pd.DataFrame(
        {
            "Month": pd.to_datetime(
                monthly_dates,
                errors="coerce",
            ),
            "Revenue": pd.to_numeric(
                monthly[revenue_column],
                errors="coerce",
            ),
        }
    )

    data = data.dropna(
        subset=[
            "Month",
            "Revenue",
        ]
    )

    if data.empty:
        return _empty_figure(title)

    # ==============================================================
    # 5. NORMALIZE MONTHS
    # ==============================================================

    try:
        data["Month"] = (
            data["Month"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )
    except Exception:
        pass

    # If duplicate months exist, aggregate them
    data = (
        data
        .groupby(
            "Month",
            as_index=False,
        )["Revenue"]
        .sum()
        .sort_values("Month")
        .reset_index(drop=True)
    )

    # ==============================================================
    # 6. CREATE MAIN REVENUE TREND
    # ==============================================================

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=data["Month"],
            y=data["Revenue"],
            mode="lines+markers",
            name="Revenue",
            line=dict(
                color=BLUE,
                width=3,
            ),
            marker=dict(
                size=6,
            ),
            hovertemplate=(
                "%{x|%b %Y}"
                "<br>Revenue: ₹%{y:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    # ==============================================================
    # 7. VALIDATE ANOMALIES
    # ==============================================================

    if not isinstance(
        anomalies,
        pd.DataFrame,
    ):
        return _finish(
            fig,
            title,
        )

    if anomalies.empty:
        return _finish(
            fig,
            title,
        )

    anomaly_source = anomalies.copy()

    # Remove duplicate columns
    try:
        anomaly_source = anomaly_source.loc[
            :,
            ~anomaly_source.columns.duplicated(),
        ]
    except Exception:
        pass

    # ==============================================================
    # 8. FIND ANOMALY DATE
    # ==============================================================

    anomaly_dates = _extract_date(
        anomaly_source,
        [
            "Period",
            "Month",
            "Date",
            "_date",
            "Order Date",
            "Order_Date",
            "Timestamp",
        ],
    )

    if anomaly_dates is None:
        return _finish(
            fig,
            title,
        )

    # ==============================================================
    # 9. FIND ANOMALY REVENUE
    # ==============================================================

    anomaly_revenue_column = None

    for column in [
        "Revenue",
        "Sales",
        "Amount",
        "Total Sales",
        "Actual Revenue",
    ]:
        if column in anomaly_source.columns:
            anomaly_revenue_column = column
            break

    if anomaly_revenue_column is None:
        return _finish(
            fig,
            title,
        )

    # ==============================================================
    # 10. BUILD STANDARD ANOMALY DATA
    # ==============================================================

    anom = pd.DataFrame(
        {
            "Month": pd.to_datetime(
                anomaly_dates,
                errors="coerce",
            ),
            "Revenue": pd.to_numeric(
                anomaly_source[
                    anomaly_revenue_column
                ],
                errors="coerce",
            ),
        }
    )

    # ==============================================================
    # 11. PRESERVE OPTIONAL ANOMALY INFORMATION
    # ==============================================================

    optional_columns = [
        "Severity",
        "Anomaly Score",
        "Deviation %",
        "Percentage Deviation",
        "Expected Revenue",
        "Expected Value",
        "Reason",
        "Explanation",
    ]

    for column in optional_columns:
        if column in anomaly_source.columns:
            try:
                anom[column] = anomaly_source[
                    column
                ].values
            except Exception:
                pass

    # ==============================================================
    # 12. CLEAN ANOMALIES
    # ==============================================================

    anom = anom.dropna(
        subset=[
            "Month",
            "Revenue",
        ]
    )

    if anom.empty:
        return _finish(
            fig,
            title,
        )

    try:
        anom["Month"] = (
            anom["Month"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )
    except Exception:
        pass

    anom = (
        anom
        .sort_values("Month")
        .reset_index(drop=True)
    )

    # ==============================================================
    # 13. BUILD ANOMALY HOVER TEXT
    # ==============================================================

    hover_text = []

    for _, row in anom.iterrows():

        try:
            month_text = row["Month"].strftime(
                "%b %Y"
            )
        except Exception:
            month_text = str(
                row["Month"]
            )

        text_parts = [
            month_text,
            f"Anomaly Revenue: ₹{row['Revenue']:,.0f}",
        ]

        # Severity
        if (
            "Severity" in anom.columns
            and pd.notna(row["Severity"])
        ):
            text_parts.append(
                f"Severity: {row['Severity']}"
            )

        # Anomaly Score
        if (
            "Anomaly Score" in anom.columns
            and pd.notna(row["Anomaly Score"])
        ):
            try:
                text_parts.append(
                    "Anomaly Score: "
                    f"{float(row['Anomaly Score']):.2f}"
                )
            except Exception:
                pass

        # Percentage Deviation
        if (
            "Percentage Deviation"
            in anom.columns
            and pd.notna(
                row["Percentage Deviation"]
            )
        ):
            try:
                text_parts.append(
                    "Deviation: "
                    f"{float(row['Percentage Deviation']):.1f}%"
                )
            except Exception:
                pass

        elif (
            "Deviation %" in anom.columns
            and pd.notna(row["Deviation %"])
        ):
            try:
                text_parts.append(
                    "Deviation: "
                    f"{float(row['Deviation %']):.1f}%"
                )
            except Exception:
                pass

        # Expected revenue
        if (
            "Expected Revenue"
            in anom.columns
            and pd.notna(
                row["Expected Revenue"]
            )
        ):
            try:
                text_parts.append(
                    "Expected: "
                    f"₹{float(row['Expected Revenue']):,.0f}"
                )
            except Exception:
                pass

        elif (
            "Expected Value"
            in anom.columns
            and pd.notna(
                row["Expected Value"]
            )
        ):
            try:
                text_parts.append(
                    "Expected: "
                    f"₹{float(row['Expected Value']):,.0f}"
                )
            except Exception:
                pass

        # Explanation
        if (
            "Reason" in anom.columns
            and pd.notna(row["Reason"])
        ):
            text_parts.append(
                f"Reason: {row['Reason']}"
            )

        elif (
            "Explanation" in anom.columns
            and pd.notna(row["Explanation"])
        ):
            text_parts.append(
                f"Explanation: {row['Explanation']}"
            )

        hover_text.append(
            "<br>".join(text_parts)
        )

    # ==============================================================
    # 14. ADD ANOMALY MARKERS
    # ==============================================================

    fig.add_trace(
        go.Scatter(
            x=anom["Month"],
            y=anom["Revenue"],
            mode="markers",
            name="Anomaly",
            marker=dict(
                color=DANGER,
                size=13,
                symbol="x",
                line=dict(
                    width=2,
                ),
            ),
            text=hover_text,
            hovertemplate=(
                "%{text}"
                "<extra></extra>"
            ),
        )
    )

    # ==============================================================
    # 15. ANOMALY COUNT
    # ==============================================================

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=1,
        y=1.08,
        text=(
            f"{len(anom):,} anomalies detected"
        ),
        showarrow=False,
        xanchor="right",
        font=dict(
            size=12,
            color=DANGER,
        ),
    )

    # ==============================================================
    # 16. FINAL CHART FORMATTING
    # ==============================================================

    fig = _finish(
        fig,
        title,
    )

    fig.update_xaxes(
        title_text="Month",
        tickformat="%b %Y",
    )

    fig.update_yaxes(
        title_text="Revenue",
        tickprefix="₹",
        separatethousands=True,
    )

    return fig


# =====================================================================
# ADDITIONAL ALIASES FOR COMMON BUSINESS WORDING
# =====================================================================

def forecast_confidence_chart(
    forecast_table: pd.DataFrame,
    title: str = "Forecast Confidence Band",
) -> go.Figure:
    """Convenience name for the confidence-band visualization."""
    return forecast_confidence_band(forecast_table, title)


def actual_forecast_chart(
    monthly_df: pd.DataFrame,
    forecast_table: pd.DataFrame,
    title: str = "Actual vs Forecast",
) -> go.Figure:
    """Convenience name for the historical + forecast visualization."""
    return historical_forecast_chart(monthly_df, forecast_table, title)



# =====================================================================
# INAIBA PRO VISUAL SYSTEM
# =====================================================================
# These overrides sit on top of the existing public chart API.  They keep
# every existing function name/data contract intact while upgrading the
# presentation layer across the dashboard.

PRO_BG = "rgba(0,0,0,0)"
PRO_SURFACE = "#0F1C45"
PRO_GRID = "rgba(132,160,255,0.12)"
PRO_TEXT = "#E6ECFF"
PRO_MUTED = "#8FA0C8"
PRO_BORDER = "rgba(132,160,255,0.28)"
PRO_BLUE = "#4F8CFF"
PRO_BLUE_2 = "#22D3EE"
PRO_BLUE_3 = "#A78BFA"
PRO_BLUE_4 = "#7DD3FC"
PRO_GREEN = "#34D399"
PRO_AMBER = "#FBBF24"
PRO_RED = "#F87171"
PRO_PALETTE = [PRO_BLUE, PRO_BLUE_2, PRO_BLUE_3, "#34D399", "#FBBF24", "#F472B6", "#60A5FA", "#818CF8"]


def _pro_axis_title(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else ""


def _pro_hover_currency(label: str) -> str:
    return f"<b>%{{x}}</b><br>{label}: ₹%{{y:,.0f}}<extra></extra>"


def _pro_hover_number(label: str) -> str:
    return f"<b>%{{x}}</b><br>{label}: %{{y:,.0f}}<extra></extra>"


def _pro_finish(fig: go.Figure, title: str, *, height: Optional[int] = None) -> go.Figure:
    """Premium enterprise Plotly shell used by every visualization."""
    # Let the project's style module contribute first, then enforce the
    # dashboard-level design tokens after it so all charts remain consistent.
    try:
        fig = style_fig(fig, title)
    except Exception:
        pass

    fig.update_layout(
        template="plotly_dark",
        colorway=PRO_PALETTE,
        paper_bgcolor=PRO_BG,
        plot_bgcolor=PRO_BG,
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size=12, color=PRO_TEXT),
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            y=0.98,
            yanchor="top",
            font=dict(size=16, color=PRO_TEXT, family="Inter, sans-serif"),
        ),
        margin=dict(l=52, r=26, t=58, b=46),
        hovermode="x unified" if len(fig.data) > 1 else "closest",
        hoverlabel=dict(
            bgcolor="#0E1A45",
            bordercolor=PRO_BORDER,
            font=dict(color=PRO_TEXT, size=12, family="Inter, sans-serif"),
            namelength=-1,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=11, color=PRO_MUTED),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        separators=",.",
        uirevision="inaiba-pro",
        hoverdistance=30,
    )

    fig.update_xaxes(
        showline=False,
        zeroline=False,
        showgrid=False,
        tickfont=dict(size=11, color=PRO_MUTED),
        title_font=dict(size=11, color=PRO_MUTED),
        automargin=True,
        ticks="",
    )
    fig.update_yaxes(
        showline=False,
        zeroline=False,
        showgrid=True,
        gridcolor=PRO_GRID,
        gridwidth=1,
        tickfont=dict(size=11, color=PRO_MUTED),
        title_font=dict(size=11, color=PRO_MUTED),
        automargin=True,
        ticks="",
    )

    fig.update_traces(
        selector=lambda trace: trace.type in {"scatter", "bar", "area"},
        hoverlabel=dict(namelength=-1),
    )

    # Improve responsiveness when rendered inside Streamlit columns.
    fig.update_layout(autosize=True)
    if height is not None:
        fig.update_layout(height=height)
    return fig


def _finish(fig: go.Figure, title: str, *, height: Optional[int] = None) -> go.Figure:
    return _pro_finish(fig, title, height=height)


def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Trend",
    *,
    name: Optional[str] = None,
    y_format: str = "number",
    color: Optional[str] = None,
    markers: bool = True,
) -> go.Figure:
    data = _clean_xy(df, x_col, y_col)
    if data.empty:
        return _empty_figure(title)

    line_color = color or PRO_BLUE_2
    label = name or _pro_axis_title(y_col)
    mode = "lines+markers" if markers else "lines"
    hover = _pro_hover_currency(label) if y_format == "currency" else (
        f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>" if y_format == "percent"
        else _pro_hover_number(label)
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col], mode=mode, name=label,
        line=dict(color=line_color, width=3, shape="spline"),
        marker=dict(size=7, color=line_color, line=dict(color="#0A1233", width=2)),
        hovertemplate=hover,
    ))
    # Small latest-point emphasis without cluttering the series.
    if markers and len(data) > 0:
        latest = data.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[latest[x_col]], y=[latest[y_col]], mode="markers",
            marker=dict(size=10, color=line_color, line=dict(color="#0A1233", width=3)),
            showlegend=False,
            hovertemplate=hover,
        ))
    return _finish(fig, title)


def area_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Trend",
    *,
    name: Optional[str] = None,
    color: Optional[str] = None,
    y_format: str = "currency",
) -> go.Figure:
    data = _clean_xy(df, x_col, y_col)
    if data.empty:
        return _empty_figure(title)
    line_color = color or PRO_BLUE_2
    label = name or _pro_axis_title(y_col)
    hover = _pro_hover_currency(label) if y_format == "currency" else (
        f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>" if y_format == "percent"
        else _pro_hover_number(label)
    )
    fig = go.Figure(go.Scatter(
        x=data[x_col], y=data[y_col], mode="lines",
        name=label,
        line=dict(color=line_color, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(79,140,255,0.14)",
        hovertemplate=hover,
    ))
    return _finish(fig, title)


def bar_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str = "Comparison",
    *,
    top_n: Optional[int] = None,
    horizontal: bool = False,
    color: Optional[str] = None,
) -> go.Figure:
    data = _clean_xy(df, category_col, value_col)
    if data.empty:
        return _empty_figure(title)
    data = data.groupby(category_col, as_index=False)[value_col].sum().sort_values(value_col, ascending=False)
    if top_n:
        data = data.head(top_n)

    labels = _labels(data[category_col], 36)
    bar_color = color or PRO_BLUE_2
    # A subtle rank ramp gives large lists a more analytical feel without
    # turning the dashboard into a rainbow of colors.
    if color is None:
        colors = [PRO_BLUE if i == 0 else PRO_BLUE_2 if i < 3 else "#6F9BF0" for i in range(len(data))]
    else:
        colors = bar_color

    if horizontal:
        data = data.assign(_label=labels).sort_values(value_col, ascending=True)
        if isinstance(colors, list):
            colors = list(reversed(colors))
        fig = go.Figure(go.Bar(
            x=data[value_col], y=data["_label"], orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=data[value_col], textposition="outside",
            texttemplate="%{text:,.0f}",
            textfont=dict(size=10, color=PRO_MUTED),
            hovertemplate="<b>%{y}</b><br>" + _value_hover(value_col) + "<extra></extra>",
        ))
        fig.update_xaxes(showgrid=True, gridcolor=PRO_GRID)
    else:
        fig = go.Figure(go.Bar(
            x=labels, y=data[value_col],
            marker=dict(color=colors, line=dict(width=0)),
            text=data[value_col], textposition="outside",
            texttemplate="%{text:,.0f}",
            textfont=dict(size=10, color=PRO_MUTED),
            hovertemplate="<b>%{x}</b><br>" + _value_hover(value_col) + "<extra></extra>",
        ))
        fig.update_xaxes(tickangle=-28)
    fig.update_layout(bargap=0.34)
    return _finish(fig, title)


def scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Relationship",
    *,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    labels: Optional[Mapping[str, str]] = None,
) -> go.Figure:
    required = [x_col, y_col] + ([color_col] if color_col else []) + ([size_col] if size_col else [])
    if not _has_columns(df, required):
        return _empty_figure(title)
    data = df[required].copy()
    data[x_col] = pd.to_numeric(data[x_col], errors="coerce")
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    if size_col:
        data[size_col] = pd.to_numeric(data[size_col], errors="coerce")
    data = data.dropna(subset=[x_col, y_col])
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure()
    if color_col:
        groups = data[color_col].fillna("Unknown").astype(str)
        for i, group in enumerate(groups.unique()):
            part = data.loc[groups == group]
            marker = dict(
                color=PRO_PALETTE[i % len(PRO_PALETTE)], size=9, opacity=0.82,
                line=dict(color="#0A1233", width=1.5),
            )
            if size_col:
                sizes = part[size_col].abs().fillna(0)
                if sizes.max() > 0:
                    marker["size"] = 8 + 24 * (sizes / sizes.max())
            fig.add_trace(go.Scatter(
                x=part[x_col], y=part[y_col], mode="markers", name=_short_label(group),
                marker=marker,
                hovertemplate=(f"<b>{_pro_axis_title(x_col)}</b>: %{{x:,.2f}}<br>"
                               f"<b>{_pro_axis_title(y_col)}</b>: %{{y:,.2f}}<br>"
                               f"<b>{_pro_axis_title(color_col)}</b>: %{{fullData.name}}<extra></extra>"),
            ))
    else:
        marker = dict(color=PRO_BLUE_2, size=9, opacity=0.78, line=dict(color="#0A1233", width=1.5))
        if size_col:
            sizes = data[size_col].abs().fillna(0)
            if sizes.max() > 0:
                marker["size"] = 8 + 24 * (sizes / sizes.max())
        fig.add_trace(go.Scatter(
            x=data[x_col], y=data[y_col], mode="markers", name=_pro_axis_title(y_col),
            marker=marker,
            hovertemplate=f"<b>{_pro_axis_title(x_col)}</b>: %{{x:,.2f}}<br><b>{_pro_axis_title(y_col)}</b>: %{{y:,.2f}}<extra></extra>",
        ))

    if labels:
        fig.update_xaxes(title_text=labels.get(x_col, _pro_axis_title(x_col)))
        fig.update_yaxes(title_text=labels.get(y_col, _pro_axis_title(y_col)))
    return _finish(fig, title)


def donut_chart(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str = "Contribution",
    *,
    top_n: int = 8,
) -> go.Figure:
    data = _clean_xy(df, label_col, value_col)
    if data.empty:
        return _empty_figure(title)
    data = data.groupby(label_col, as_index=False)[value_col].sum().nlargest(top_n, value_col)
    total = data[value_col].sum()
    fig = go.Figure(go.Pie(
        labels=_labels(data[label_col], 28), values=data[value_col], hole=0.66,
        sort=False,
        marker=dict(colors=[PRO_PALETTE[i % len(PRO_PALETTE)] for i in range(len(data))], line=dict(color="#0A1233", width=2)),
        textinfo="percent", textfont=dict(size=11, color=PRO_TEXT),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       text=f"<b>₹{total:,.0f}</b><br><span style='font-size:10px;color:{PRO_MUTED}'>Total</span>",
                       font=dict(size=15, color=PRO_TEXT))
    fig.update_layout(showlegend=True)
    return _finish(fig, title)


def heatmap(
    matrix: pd.DataFrame,
    title: str = "Heatmap",
    *,
    value_format: str = "number",
) -> go.Figure:
    if not isinstance(matrix, pd.DataFrame) or matrix.empty:
        return _empty_figure(title)
    data = matrix.apply(pd.to_numeric, errors="coerce")
    if data.empty:
        return _empty_figure(title)
    hover_format = "₹%{z:,.0f}" if value_format == "currency" else "%{z:,.1f}%" if value_format == "percent" else "%{z:,.0f}"
    fig = go.Figure(go.Heatmap(
        z=data.values,
        x=[_short_label(v, 24) for v in data.columns],
        y=[_short_label(v, 24) for v in data.index],
        colorscale=[[0, "#0F1C45"], [0.45, "#2F5FD0"], [0.75, "#4F8CFF"], [1, "#22D3EE"]],
        xgap=2, ygap=2,
        colorbar=dict(title="", thickness=10, len=0.75, outlinewidth=0, tickfont=dict(color=PRO_MUTED, size=10)),
        hovertemplate="<b>%{y}</b> / %{x}<br>" + hover_format + "<extra></extra>",
    ))
    fig.update_xaxes(tickangle=-35)
    return _finish(fig, title)


def _pro_table_style(df: pd.DataFrame):
    """Return a polished pandas Styler for callers that render dataframe tables."""
    if not isinstance(df, pd.DataFrame):
        return df
    return (
        df.style
        .set_properties(**{
            "font-family": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            "font-size": "12px",
            "color": PRO_TEXT,
            "border-color": PRO_BORDER,
        })
        .set_table_styles([
            {"selector": "th", "props": [("background", "#101D47"), ("color", PRO_TEXT), ("font-weight", "600"), ("border-bottom", f"1px solid {PRO_BORDER}"), ("padding", "10px 12px")]},
            {"selector": "td", "props": [("padding", "9px 12px"), ("border-bottom", f"1px solid rgba(132,160,255,0.10)")]},
            {"selector": "tbody tr:hover", "props": [("background", "rgba(79,140,255,0.10)")]},
        ])
    )


__all__ = [
    # Core
    "line_chart",
    "area_chart",
    "bar_chart",
    "horizontal_ranked_bar",
    "diverging_bar",
    "lollipop_chart",
    "scatter_chart",
    "bubble_chart",
    "donut_chart",
    "treemap_chart",
    "sunburst_chart",
    "heatmap",
    "box_plot",
    "violin_plot",
    "histogram",
    "radar_chart",
    "waterfall_chart",
    "gauge_chart",
    # Executive
    "monthly_revenue_chart",
    "monthly_profit_chart",
    "revenue_by_category_chart",
    "profit_margin_by_category_chart",
    "revenue_by_region_chart",
    "revenue_by_segment_chart",
    "top_products_chart",
    "sales_vs_profit_chart",
    # Performance
    "revenue_trend_chart",
    "profit_trend_chart",
    "growth_waterfall_chart",
    "seasonality_heatmap",
    "category_comparison_chart",
    "discount_scatter_chart",
    "order_distribution_chart",
    "segment_radar_chart",
    # Products
    "category_revenue_chart",
    "category_profit_chart",
    "category_margin_chart",
    "category_radar_chart",
    "product_treemap_chart",
    "product_ranking_chart",
    "product_profitability_scatter",
    "category_subcategory_sunburst",
    "product_distribution_chart",
    # Regions
    "regional_revenue_chart",
    "regional_profit_chart",
    "regional_margin_chart",
    "regional_treemap_chart",
    "regional_radar_chart",
    "regional_trend_chart",
    "regional_scatter_chart",
    "regional_heatmap_chart",
    # Forecasting
    "historical_forecast_chart",
    "forecast_confidence_band",
    "model_accuracy_chart",
    "model_radar_chart",
    "forecast_waterfall_chart",
    "monthly_forecast_chart",
    "actual_vs_predicted_chart",
    "forecast_error_distribution",
    # Anomalies
    "anomaly_timeline_chart",
    "severity_donut_chart",
    "anomaly_heatmap_chart",
    "anomaly_distribution_chart",
    "profit_anomaly_scatter",
    "discount_risk_scatter",
    "risk_radar_chart",
    "risk_treemap_chart",
    # Existing project API
    "monthly_trend_chart",
    "growth_chart",
    "contribution_pie",
    "bar_by_dimension",
    "actual_vs_target_chart",
    "forecast_chart",
    "heatmap_chart",
    "scenario_comparison_chart",
    "anomaly_scatter",
    # Convenience
    "forecast_confidence_chart",
    "actual_forecast_chart",
]
