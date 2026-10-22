import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import html as html_lib

import data_loader
import data_cleaner
import data_validator
import analytics as an
import forecasting as fc
import anomaly_detection as ad
import insights as ins
import visualizations as viz
import reports as rpt
import style as stl


_original_st_markdown = st.markdown


def _inaiba_markdown(body="", *args, **kwargs):
    if kwargs.get("unsafe_allow_html") and isinstance(body, str):
        cleaned = textwrap.dedent(body).strip()

        # Native st.html() is the most reliable renderer for dashboard
        # fragments such as KPI cards, headers, badges and alerts.
        # Keep <style> blocks on st.markdown so CSS injection remains
        # compatible across Streamlit releases.
        if "<style" not in cleaned.lower():
            html_renderer = getattr(st, "html", None)
            if html_renderer is not None:
                return html_renderer(cleaned)

        return _original_st_markdown(cleaned, *args, **kwargs)

    return _original_st_markdown(body, *args, **kwargs)


st.markdown = _inaiba_markdown

stl.configure_page()
stl.inject_global_css()
stl.inject_enterprise_overrides()


_original_st_markdown(
    """
    <style>
        /* Streamlit Material icons must retain their icon fonts. */
        .material-icons {
            font-family: "Material Icons" !important;
            font-feature-settings: "liga" !important;
            -webkit-font-feature-settings: "liga" !important;
        }
        .material-icons-outlined {
            font-family: "Material Icons Outlined" !important;
            font-feature-settings: "liga" !important;
            -webkit-font-feature-settings: "liga" !important;
        }
        .material-symbols-rounded {
            font-family: "Material Symbols Rounded" !important;
            font-feature-settings: "liga" !important;
            -webkit-font-feature-settings: "liga" !important;
        }
        .material-symbols-outlined {
            font-family: "Material Symbols Outlined" !important;
            font-feature-settings: "liga" !important;
            -webkit-font-feature-settings: "liga" !important;
        }

        /* Never let dashboard HTML inherit code-block presentation. */
        .inaiba-kpi,
        .inaiba-card,
        .inaiba-insight,
        .inaiba-quality-card,
        .inaiba-forecast-card,
        .inaiba-header-meta,
        .inaiba-page-title,
        .inaiba-page-desc,
        .inaiba-section-title {
            white-space: normal !important;
            overflow-wrap: anywhere;
        }

        /* File uploader controls stay visually native and readable. */
        [data-testid="stFileUploader"] button {
            font-family: "Inter", "Segoe UI", Arial, sans-serif !important;
        }
        [data-testid="stFileUploader"] .material-icons,
        [data-testid="stFileUploader"] .material-icons-outlined,
        [data-testid="stFileUploader"] .material-symbols-rounded,
        [data-testid="stFileUploader"] .material-symbols-outlined {
            font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
            font-feature-settings: "liga" !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Visual theme: all CSS now lives in style.py (inject_global_css).

DEFAULTS = {
    "raw_df": None,
    "dataset_name": None,
    "column_mapping": None,
    "mapping_confirmed": False,
    "cleaned_df": None,
    "cleaning_report": None,
    "quality_report": None,
    "active_filters": {},
    "filters_applied": False,
    "filter_version": 0,
    "nav": "Start",
    "landing_action": None,
}


for key, value in DEFAULTS.items():

    if key not in st.session_state:

        if isinstance(value, dict):
            st.session_state[key] = value.copy()

        else:
            st.session_state[key] = value


# NAVIGATION

NAV_ITEMS = [
    "Executive Overview",
    "Sales Performance",
    "Products & Categories",
    "Regions / Branches",
    "Forecasting",
    "Forecast Evaluation",
    "Anomalies & Risks",
    "Business Insights",
    "Data Quality",
    "Reports & Downloads",
]

# FORMATTING HELPERS

def is_missing(value):

    if value is None:
        return True

    try:
        result = pd.isna(value)

        if isinstance(result, (bool, np.bool_)):
            return bool(result)

    except Exception:
        pass

    return False


def fmt_currency(value):

    if is_missing(value):
        return "—"

    try:
        number = float(value)

        if not np.isfinite(number):
            return "—"

        return f"₹{number:,.0f}"

    except (TypeError, ValueError):
        return "—"


def fmt_currency_2(value):

    if is_missing(value):
        return "—"

    try:
        number = float(value)

        if not np.isfinite(number):
            return "—"

        return f"₹{number:,.2f}"

    except (TypeError, ValueError):
        return "—"


def fmt_pct(value, decimals=1):

    if is_missing(value):
        return "—"

    try:
        number = float(value)

        if not np.isfinite(number):
            return "—"

        return f"{number:+.{decimals}f}%"

    except (TypeError, ValueError):
        return "—"


def safe_number(value, default=0.0):

    try:

        number = float(value)

        if np.isfinite(number):
            return number

    except (TypeError, ValueError):
        pass

    return default


def delta_direction(value):

    number = safe_number(value, 0)

    if number > 0:
        return "up"

    if number < 0:
        return "down"

    return "flat"


def safe_text(value, default="—"):

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

    except Exception:
        pass

    text = str(value).strip()

    return text if text else default

PAGE_DESCRIPTIONS = {
    "Executive Overview": "A concise management view of revenue, volume, mix, growth and business concentration.",
    "Sales Performance": "Track revenue, orders, profitability and growth across the business.",
    "Products & Categories": "Understand product, category and sub-category contribution and profitability.",
    "Regions / Branches": "Compare regional performance, branch contribution and geographic trends.",
    "Forecasting": "Understand expected future sales and identify upcoming planning opportunities.",
    "Forecast Evaluation": "Compare forecasting models using consistent validation metrics.",
    "Anomalies & Risks": "Identify unusual sales behaviour and potential business risks.",
    "Business Insights": "Turn the strongest patterns in your sales data into clear business actions.",
    "Data Quality": "Review completeness, validity and reliability of the current dataset.",
    "Reports & Downloads": "Export cleaned data, analysis, forecasts and management-ready reports.",
}


def page_title(title, description=""):
    """Render the compact enterprise page header used across every dashboard page."""
    kicker = str(title).upper()
    safe_title = html_lib.escape(str(title))
    safe_description = html_lib.escape(str(description or PAGE_DESCRIPTIONS.get(title, "")))
    st.markdown(
        f'''
        <section class="inaiba-page-hero">
            <div class="inaiba-page-kicker">{html_lib.escape(kicker)}</div>
            <div class="inaiba-page-heading-row">
                <div>
                    <h1>{safe_title}</h1>
                    <p>{safe_description}</p>
                </div>
            </div>
        </section>
        ''',
        unsafe_allow_html=True,
    )


def section_title(title):
    """Render a compact section heading without changing page logic."""
    st.markdown(
        f'''
        <div class="inaiba-section-heading">
            <span>{html_lib.escape(str(title))}</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def kpi_row(items):
    """Render consistent lightweight KPI cards while preserving existing values."""
    if not items:
        return

    columns = st.columns(len(items), gap="small")
    for column, item in zip(columns, items):
        with column:
            label = html_lib.escape(str(item.get("label", "")))
            value = html_lib.escape(str(item.get("value", "—")))
            delta = item.get("delta")
            delta_text = "" if delta in (None, "") else html_lib.escape(str(delta))
            direction = delta_direction(delta) if delta not in (None, "") else "flat"
            arrow = "↑" if direction == "up" else ("↓" if direction == "down" else "•")
            delta_class = f"delta-{direction}"

            st.markdown(
                f'''
                <div class="inaiba-kpi-card">
                    <div class="inaiba-kpi-label">{label}</div>
                    <div class="inaiba-kpi-value">{value}</div>
                    {f'<div class="inaiba-kpi-delta {delta_class}"><span>{arrow}</span> {delta_text}<small>vs selected period</small></div>' if delta_text else '<div class="inaiba-kpi-delta delta-flat"><span>•</span> Current snapshot</div>'}
                </div>
                ''',
                unsafe_allow_html=True,
            )


def alert_box(message, level="watch"):
    level = str(level).lower()
    if level in {"critical", "danger", "error"}:
        level = "critical"
    elif level in {"moderate", "warning"}:
        level = "moderate"
    elif level in {"good", "success"}:
        level = "good"
    else:
        level = "watch"
    stl.alert_box(message, level)


def safe_style_fig(fig, title=None):
    if fig is None:
        return None
    try:
    
        fig = stl.style_fig(fig, title)
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C7D2EC"),
            colorway=stl.CHART_PALETTE,
            height=390,
            margin=dict(l=50, r=25, t=65, b=50),
            legend=dict(orientation="h", y=1.08, x=0),
            hovermode="x unified",
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(132,160,255,0.12)")
    except Exception:
        pass
    return fig


def safe_plot(fig, title=None):

    if fig is None:
        return False

    try:

        fig = safe_style_fig(
            fig,
            title,
        )

        try:
            chart_surface = st.container(border=True)
        except TypeError:
            chart_surface = st.container()

        with chart_surface:
            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        return True

    except Exception as exc:

        st.warning(
            "The chart could not be rendered."
        )

        st.caption(
            f"Technical details: {exc}"
        )

        return False


def safe_dataframe(
    df,
    height=420,
):
    """
    Safely render a pandas DataFrame in Streamlit.

    Handles:
    - None / empty data
    - Non-DataFrame input
    - Duplicate column names
    - NaN / infinite numeric values
    - Datetime columns
    - Period columns
    - Invalid height values
    - Streamlit dataframe rendering errors
    """

    # ------------------------------------------------------------
    # 1. Validate input
    # ------------------------------------------------------------
    if df is None:
        st.info("No data available.")
        return False

    # Convert compatible objects to DataFrame
    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            st.info("No displayable data available.")
            return False

    # Empty DataFrame
    if df.empty:
        st.info("No records available.")
        return False

    # ------------------------------------------------------------
    # 2. Create independent display copy
    # ------------------------------------------------------------
    display = df.copy()

    # ------------------------------------------------------------
    # 3. Remove duplicate column names
    # ------------------------------------------------------------
    try:
        display = display.loc[
            :,
            ~display.columns.duplicated(),
        ]
    except Exception:
        pass

    # ------------------------------------------------------------
    # 4. Clean column names
    # ------------------------------------------------------------
    try:
        display.columns = [
            str(column).strip()
            for column in display.columns
        ]
    except Exception:
        pass

    # ------------------------------------------------------------
    # 5. Replace invalid numeric values
    # ------------------------------------------------------------
    try:
        numeric_columns = display.select_dtypes(
            include=[np.number]
        ).columns

        for column in numeric_columns:
            display[column] = display[column].replace(
                [np.inf, -np.inf],
                np.nan,
            )
    except Exception:
        pass

    # ------------------------------------------------------------
    # 6. Safely convert datetime / Period columns
    # ------------------------------------------------------------
    for column in display.columns:

        try:
            series = display[column]

            # Datetime columns
            if pd.api.types.is_datetime64_any_dtype(series):

                display[column] = series.dt.strftime(
                    "%b %Y"
                )

            # Period columns
            elif isinstance(
                series.dtype,
                pd.PeriodDtype,
            ):

                display[column] = series.astype(str)

            # Object columns containing Period values
            elif series.dtype == "object":

                non_null = series.dropna()

                if not non_null.empty:

                    sample_value = non_null.iloc[0]

                    if isinstance(
                        sample_value,
                        pd.Period,
                    ):
                        display[column] = (
                            series.astype(str)
                        )

        except Exception:
            # Never allow formatting of one column
            # to break the complete table.
            continue

    # ------------------------------------------------------------
    # 7. Make height safe
    # ------------------------------------------------------------
    # Streamlit does NOT accept height=None.
    #
    # Valid values are:
    # - positive integer
    # - "stretch"
    # - "content"
    #
    valid_height = height

    if valid_height is None:
        valid_height = 420

    elif isinstance(valid_height, (int, np.integer)):

        if valid_height <= 0:
            valid_height = 420

    elif valid_height not in (
        "stretch",
        "content",
    ):

        valid_height = 420

    # ------------------------------------------------------------
    # 8. Render dataframe
    # ------------------------------------------------------------
    try:

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=valid_height,
        )

        return True

    except Exception as exc:

        # --------------------------------------------------------
        # 9. Emergency fallback
        # --------------------------------------------------------
        # If the configured height causes an issue for any reason,
        # try rendering without explicitly passing height.
        try:

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
            )

            return True

        except Exception as fallback_exc:

            st.error(
                "The table could not be rendered."
            )

            st.caption(
                f"Technical details: {fallback_exc}"
            )

            return False

# ============================================================
# COLUMN HELPERS
# ============================================================

def find_column(df, candidates):

    if df is None:
        return None

    normalized = {}

    for column in df.columns:

        key = str(column).strip().lower()

        normalized[key] = column

    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    return None


def ensure_date_column(df):

    if df is None:
        return pd.DataFrame()

    result = df.copy()

    if "Date" in result.columns:

        result["Date"] = pd.to_datetime(
            result["Date"],
            errors="coerce",
        )

    if (
        "Month" not in result.columns
        and "Date" in result.columns
    ):

        result["Month"] = (
            result["Date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

    return result


# ============================================================
# HEADER
# ============================================================

def render_app_header():
    """Compact enterprise shell header; dataset values come from existing session state."""
    df = st.session_state.get("cleaned_df")

    dataset_name = st.session_state.get("dataset_name") or "No dataset loaded"
    safe_dataset = html_lib.escape(str(dataset_name))

    rows = len(df) if isinstance(df, pd.DataFrame) else 0
    period_label = "Awaiting dataset"
    if isinstance(df, pd.DataFrame) and not df.empty and "Date" in df.columns:
        dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
        if not dates.empty:
            period_label = f"{dates.min():%d %b %Y} – {dates.max():%d %b %Y}"

    status_label = "Ready" if isinstance(df, pd.DataFrame) and not df.empty else "Awaiting upload"

    st.markdown(
        f'''
        <div class="inaiba-shell-header">
            <div class="inaiba-shell-brand">
                <span class="inaiba-logo-full" role="img" aria-label="INAIBA"></span>
                <div class="inaiba-shell-context">
                    <div class="inaiba-shell-eyebrow">INAIBA SALES INTELLIGENCE</div>
                    <div class="inaiba-shell-product">Enterprise analytics workspace</div>
                </div>
            </div>
            <div class="inaiba-shell-meta">
                <div class="inaiba-meta-item">
                    <span>Dataset</span>
                    <strong title="{safe_dataset}">{safe_dataset}</strong>
                </div>
                <div class="inaiba-meta-item">
                    <span>Period</span>
                    <strong>{html_lib.escape(period_label)}</strong>
                </div>
                <div class="inaiba-meta-item">
                    <span>Rows</span>
                    <strong>{rows:,}</strong>
                </div>
                <div class="inaiba-status-pill"><i></i>{html_lib.escape(status_label)}</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


# ============================================================
# ICON SIDEBAR + TOP NAVIGATION
# ============================================================

# ============================================================

NAV_LABELS = {
    "Forecasting": "Sales Forecasting",
}

NAV_ICONS = {
    "Executive Overview": ("home", "Overview"),
    "Sales Performance": ("analytics", "Sales Performance"),
    "Products & Categories": ("category", "Products & Categories"),
    "Regions / Branches": ("public", "Regions & Branches"),
    "Forecasting": ("show_chart", "Sales Forecast"),
    "Forecast Evaluation": ("fact_check", "Forecast Evaluation"),
    "Anomalies & Risks": ("warning", "Anomalies & Risk"),
    "Business Insights": ("lightbulb", "Business Insights"),
    "Data Quality": ("verified", "Data Quality"),
    "Reports & Downloads": ("download", "Reports & Downloads"),
}


def reset_to_start():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value.copy() if isinstance(value, dict) else value


# ============================================================
# UPLOAD FLOW
# ============================================================

def render_landing_page():
    """Premium, compact INAIBA landing page with one functional uploader."""

    action = st.session_state.get("landing_action")

    st.markdown('<div class="inaiba-home">', unsafe_allow_html=True)

    # HERO
    st.markdown(
        """
        <section class="inaiba-hero">
            <div class="inaiba-kicker">INAIBA SALES INTELLIGENCE</div>
            <h1>From sales data to <span>business clarity.</span></h1>
            <div class="inaiba-hero-copy">
                One simple starting point for understanding performance,
                discovering risks and forecasting what comes next.
            </div>
            <div class="inaiba-pills">
                <span class="inaiba-pill">Sales Analytics</span>
                <span class="inaiba-pill">Forecasting</span>
                <span class="inaiba-pill">Anomaly Detection</span>
                <span class="inaiba-pill">Business Insights</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if action == "forecast":
        st.info("Upload your sales dataset to activate Sales Forecasting.")

    # NATIVE STREAMLIT COLUMNS — unlike the previous version, the uploader
    # is actually inside the column layout instead of being mixed into raw HTML.
    left, right = st.columns([1.55, 0.9], gap="medium")

    with left:
        st.markdown(
            """
            <div class="inaiba-card">
                <div class="inaiba-label">GET STARTED</div>
                <h2>Upload your sales data</h2>
                <p>
                    Add one historical sales file. INAIBA will detect the
                    available fields and take you to column mapping.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Choose your sales dataset",
            type=["csv", "xlsx", "xls"],
            key="inaiba_main_uploader",
            label_visibility="collapsed",
            help="Supported formats: CSV, XLSX and XLS.",
        )

        st.markdown(
            """
            <div class="inaiba-format">
                Supported: CSV · XLSX · XLS &nbsp;•&nbsp; One file at a time
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="inaiba-card inaiba-card-blue">
                <div class="inaiba-label">WHAT HAPPENS NEXT</div>
                <h2>One upload. Full intelligence.</h2>
                <p>
                    Your dataset becomes the foundation for the complete
                    INAIBA workspace.
                </p>

                <div class="inaiba-benefits">
                    <div class="inaiba-benefit">
                        <div class="inaiba-benefit-icon">01</div>
                        <div><b>Map your data</b><span>INAIBA detects your sales columns.</span></div>
                    </div>
                    <div class="inaiba-benefit">
                        <div class="inaiba-benefit-icon">02</div>
                        <div><b>Understand performance</b><span>Explore revenue, profit, products and regions.</span></div>
                    </div>
                    <div class="inaiba-benefit">
                        <div class="inaiba-benefit-icon">03</div>
                        <div><b>Forecast & act</b><span>Find trends, risks and future opportunities.</span></div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # FEATURES
    st.markdown(
        '<div class="inaiba-section-title">A smarter view of your sales</div>',
        unsafe_allow_html=True,
    )

    feature_cols = st.columns(4, gap="small")
    features = [
        ("↗", "Sales Performance", "Revenue, profit, orders and growth."),
        ("⌁", "Forecasting", "Estimate future sales performance."),
        ("!", "Risk Detection", "Spot unusual patterns and anomalies."),
        ("✦", "Business Insights", "Turn patterns into clear actions."),
    ]

    for col, (mark, title, desc) in zip(feature_cols, features):
        with col:
            st.markdown(
                f"""
                <div class="inaiba-feature">
                    <div class="inaiba-feature-mark">{mark}</div>
                    <b>{title}</b>
                    <span>{desc}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="inaiba-bottom">
            <div class="inaiba-bottom-lead">
                <span class="inaiba-logo-mark" role="img" aria-label="INAIBA"></span>
                <div>
                    <b>Ready when you are.</b>
                    <span>Upload your dataset above and begin with a clean, decision-ready workspace.</span>
                </div>
            </div>
            <div class="inaiba-ready">WORKSPACE READY</div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # FILE PROCESSING — EXISTING DATA PIPELINE PRESERVED
    # ========================================================
    if uploaded is None:
        return

    try:
        raw, err = data_loader.load_raw_file(uploaded)
    except Exception as exc:
        st.error("The uploaded file could not be read.")
        st.caption(f"Technical details: {exc}")
        return

    if err:
        st.error(err)
        return

    st.session_state.raw_df = raw
    st.session_state.dataset_name = uploaded.name

    try:
        st.session_state.column_mapping = data_loader.detect_column_mapping(raw)
    except Exception as exc:
        st.error("Column detection could not be completed.")
        st.caption(f"Technical details: {exc}")
        return

    st.rerun()

def render_upload_flow():
    """Existing upload/mapping workflow retained for compatibility."""
    page_title(
        "Get Started",
        "Upload historical sales data to activate INAIBA's executive dashboards, forecasting, anomaly detection and business insights.",
    )

    # The landing page owns the only file uploader.  Once a file is loaded,
    # this step continues directly to column mapping instead of showing
    # a second uploader.  Use the upload action in the dashboard navigation
    # to return to the landing page and choose another file.


    # --------------------------------------------------------
    # COLUMN MAPPING
    # --------------------------------------------------------

    if (
        st.session_state.raw_df is not None
        and not st.session_state.mapping_confirmed
    ):

        raw = st.session_state.raw_df

        section_title(
            "Column Mapping"
        )

        try:

            confidence = (
                data_loader.mapping_confidence(
                    st.session_state.column_mapping
                )
            )

            st.info(
                f"Detection confidence: {confidence}"
            )

            final_mapping = (
                data_loader.render_mapping_editor(
                    raw,
                    st.session_state.column_mapping,
                )
            )

        except Exception as exc:

            st.error(
                "Column mapping could not be displayed."
            )

            st.caption(
                f"Technical details: {exc}"
            )

            return

        missing_required = [
            field
            for field in data_loader.REQUIRED_FIELDS
            if not final_mapping.get(field)
        ]

        if missing_required:

            st.warning(
                "Required field(s) not mapped: "
                + ", ".join(missing_required)
                + ". Revenue and Date are needed to proceed."
            )

        if st.button(
            "Confirm Mapping & Continue",
            disabled=bool(missing_required),
            type="primary",
        ):

            try:

                st.session_state.column_mapping = (
                    final_mapping
                )

                mapped = (
                    data_loader.apply_mapping(
                        raw,
                        final_mapping,
                    )
                )

                cleaned, report = (
                    data_cleaner.clean_dataset(
                        mapped
                    )
                )

                quality = (
                    data_validator.assess_quality(
                        mapped,
                        cleaned,
                        report,
                    )
                )

                cleaned = ensure_date_column(
                    cleaned
                )

                st.session_state.cleaned_df = (
                    cleaned
                )

                st.session_state.cleaning_report = (
                    report
                )

                st.session_state.quality_report = (
                    quality
                )

                st.session_state.mapping_confirmed = (
                    True
                )

                target_page = (
                    "Forecasting"
                    if st.session_state.get("landing_action") == "forecast"
                    else "Executive Overview"
                )
                st.session_state.nav = target_page
                st.session_state.landing_action = None
                st.rerun()

            except Exception as exc:

                st.error(
                    "The dataset could not be cleaned "
                    "and validated."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

        return

    # --------------------------------------------------------
    # CLEANING SUMMARY
    # --------------------------------------------------------

    if st.session_state.cleaned_df is not None:

        report = (
            st.session_state.cleaning_report
        )

        if not isinstance(report, dict):
            report = {}

        section_title(
            "Cleaning Summary"
        )

        kpi_row([
            {
                "label": "Rows Processed",
                "value": (
                    f"{safe_number(report.get('rows_processed'), 0):,.0f}"
                ),
            },
            {
                "label": "Rows Removed",
                "value": (
                    f"{safe_number(report.get('rows_removed'), 0):,.0f}"
                ),
            },
            {
                "label": "Duplicates Removed",
                "value": (
                    f"{safe_number(report.get('duplicates_handled'), 0):,.0f}"
                ),
            },
            {
                "label": "Final Row Count",
                "value": (
                    f"{safe_number(report.get('final_row_count'), 0):,.0f}"
                ),
            },
        ])

        notes = report.get(
            "notes",
            [],
        )

        if notes:

            with st.expander(
                "Cleaning Notes"
            ):

                for note in notes:
                    st.write(
                        str(note)
                    )

        st.success(
            "Data is ready. Use the navigation above to explore INAIBA."
        )

        target_page = (
            "Forecasting"
            if st.session_state.get("landing_action") == "forecast"
            else "Executive Overview"
        )
        continue_label = (
            "Continue to Sales Forecasting"
            if target_page == "Forecasting"
            else "Continue to Executive Overview"
        )
        if st.button(continue_label, type="primary"):
            st.session_state.nav = target_page
            st.session_state.landing_action = None
            st.rerun()


# ============================================================
# STOP BEFORE DASHBOARD
# ============================================================

if st.session_state.cleaned_df is None:

    if st.session_state.raw_df is None:
        render_landing_page()
    else:
        render_upload_flow()

    st.stop()


# ============================================================
# DASHBOARD SHELL — shown only after data is ready
# ============================================================

# Header and horizontal navigation are intentionally hidden on the opening
# upload screen and column-mapping screen. They appear only in the workspace.
current_nav = st.session_state.nav if st.session_state.nav in NAV_ITEMS else NAV_ITEMS[0]
has_dataset = st.session_state.cleaned_df is not None

render_app_header()

# Navigation is presented as a compact horizontal bar under the header.
# No Streamlit sidebar is used anywhere in the application.
nav_items = [
    ("Executive Overview", "Overview"),
    ("Sales Performance", "Sales Performance"),
    ("Products & Categories", "Products & Categories"),
    ("Regions / Branches", "Regions & Branches"),
    ("Forecasting", "Sales Forecast"),
    ("Forecast Evaluation", "Forecast Evaluation"),
    ("Anomalies & Risks", "Anomalies & Risks"),
    ("Business Insights", "Business Insights"),
    ("Data Quality", "Data Quality"),
    ("Reports & Downloads", "Reports & Downloads"),
]

with st.container(key="inaiba-horizontal-nav"):
    nav_columns = st.columns(5, gap="small")
    for index, (item, label) in enumerate(nav_items):
        icon_name = NAV_ICONS[item][0]
        active = current_nav == item and has_dataset
        with nav_columns[index % 5]:
            clicked = st.button(
                label,
                key=f"horizontal_nav_{item}",
                icon=f":material/{icon_name}:",
                help=label,
                disabled=not has_dataset,
                type="primary" if active else "secondary",
                use_container_width=True,
            )
            if clicked:
                st.session_state.nav = item
                st.session_state.landing_action = None
                st.rerun()

if has_dataset:
    with st.container(key="inaiba-horizontal-nav-actions"):
        action_cols = st.columns([1, 5])
        with action_cols[0]:
            if st.button(
                "Upload different dataset",
                key="horizontal_upload_reset",
                icon=":material/upload_file:",
                help="Upload a different dataset",
                type="secondary",
                use_container_width=True,
            ):
                reset_to_start()
                st.rerun()


# ============================================================
# GLOBAL FILTERS
# ============================================================

full_df = ensure_date_column(
    st.session_state.cleaned_df
)


def render_global_filters(df):
    """Compact enterprise filter toolbar using the existing filter/session-state workflow."""
    if df is None or df.empty:
        return df

    active = dict(st.session_state.get("active_filters", {}))
    filter_version = st.session_state.get("filter_version", 0)

    available_dimensions = [
        c for c in [
            "Category", "Region", "State", "Branch", "City",
            "Product", "Segment", "Customer"
        ] if c in df.columns
    ]

    active_count = sum(
        bool(v) for k, v in active.items() if k != "date_range"
    ) + (1 if active.get("date_range") else 0)

    with st.container():
        st.markdown(
            f'''
            <div class="inaiba-filter-header">
                <div>
                    <span class="inaiba-filter-kicker">FILTERS</span>
                    <strong>Refine the intelligence workspace</strong>
                </div>
                <span class="inaiba-filter-count">{active_count} active</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        with st.form("global_filters_form", clear_on_submit=False):
            widget_cols = st.columns(4, gap="small")

            date_value = None
            if "Date" in df.columns:
                dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
                if not dates.empty:
                    min_date, max_date = dates.min().date(), dates.max().date()
                    saved = active.get("date_range")
                    if isinstance(saved, (tuple, list)) and len(saved) == 2:
                        try:
                            default_date = (
                                pd.to_datetime(saved[0]).date(),
                                pd.to_datetime(saved[1]).date(),
                            )
                        except Exception:
                            default_date = (min_date, max_date)
                    else:
                        default_date = (min_date, max_date)

                    with widget_cols[0]:
                        date_value = st.date_input(
                            "Date Range",
                            value=default_date,
                            min_value=min_date,
                            max_value=max_date,
                            key=f"filter_date_{filter_version}",
                        )

            selected = {}

            for idx, dimension in enumerate(available_dimensions):
                col = widget_cols[(idx + 1) % 4]
                options = sorted(
                    df[dimension].dropna().astype(str).unique().tolist()
                )
                saved = [
                    str(x) for x in active.get(dimension, [])
                    if str(x) in options
                ]
                with col:
                    selected[dimension] = st.multiselect(
                        dimension,
                        options,
                        default=saved,
                        key=f"filter_{dimension.lower().replace(' ', '_')}_{filter_version}",
                    )

            b1, b2, b3 = st.columns([1.0, 0.75, 2.2], gap="small")
            with b1:
                apply_clicked = st.form_submit_button(
                    "Apply Filters",
                    type="primary",
                    use_container_width=True,
                )
            with b2:
                reset_clicked = st.form_submit_button(
                    "Reset",
                    use_container_width=True,
                )
            with b3:
                st.caption(
                    f"{active_count} active filter(s)"
                    if active_count else "No filters applied"
                )

        if reset_clicked:
            st.session_state.active_filters = {}
            st.session_state.filters_applied = False
            st.session_state.filter_version = st.session_state.get("filter_version", 0) + 1
            st.rerun()

        if apply_clicked:
            new_filters = {"date_range": date_value} if date_value else {}
            for dimension, values in selected.items():
                if values:
                    new_filters[dimension] = values
            st.session_state.active_filters = new_filters
            st.session_state.filters_applied = True
            st.rerun()

    filtered = df.copy()
    active = st.session_state.get("active_filters", {})

    if active.get("date_range") and "Date" in filtered.columns:
        try:
            start_date, end_date = active["date_range"]
            dates = pd.to_datetime(filtered["Date"], errors="coerce")
            filtered = filtered[
                (dates.dt.date >= pd.to_datetime(start_date).date())
                & (dates.dt.date <= pd.to_datetime(end_date).date())
            ]
        except Exception:
            pass

    for dimension, values in active.items():
        if dimension == "date_range" or not values or dimension not in filtered.columns:
            continue
        filtered = filtered[
            filtered[dimension].astype(str).isin([str(v) for v in values])
        ]

    return filtered


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

filtered_df = render_global_filters(full_df)

if filtered_df is None:
    filtered_df = full_df


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

def render_executive_overview(df):
    """
    Advanced, dependency-light Executive Overview.

    Exactly 8 charts:
        1. Monthly Revenue Trend
        2. Revenue Growth Momentum
        3. Revenue by Category
        4. Revenue by Region
        5. Top 10 Products by Revenue
        6. Revenue Mix by Branch / City
        7. Quantity vs Revenue
        8. Monthly Profit Trend / Top Customers

    The function is designed to be defensive:
    - Does not assume a specific date column name.
    - Does not rely on `_date` surviving groupby operations.
    - Handles missing optional business columns.
    - Keeps the page usable with different datasets.
    """

    # ========================================================
    # PAGE HEADER
    # ========================================================

    page_title(
        "Executive Overview",
        "A management view of revenue, volume, mix, growth and business concentration."
    )

    # ========================================================
    # DATA AVAILABILITY
    # ========================================================

    if df is None or df.empty:
        st.info("No records are available for the current filters.")
        return

    # Work on a copy so this page never modifies the original
    # dataframe stored in session state.
    df = df.copy()

    # ========================================================
    # STANDARDIZE DATE
    # ========================================================

    try:
        df = ensure_date_column(df)
    except Exception:
        # If the helper fails, continue and perform local
        # date detection below.
        pass

    # --------------------------------------------------------
    # Detect date column.
    #
    # Prefer the standardized "_date" created by
    # ensure_date_column(), but support normal dataset names.
    # --------------------------------------------------------

    date_candidates = [
        "_date",
        "Date",
        "Order Date",
        "Order_Date",
        "order_date",
        "Transaction Date",
        "Transaction_Date",
        "Invoice Date",
        "Invoice_Date",
        "Created Date",
        "Created_Date",
    ]

    date_column = None

    for candidate in date_candidates:
        if candidate in df.columns:
            date_column = candidate
            break

    # --------------------------------------------------------
    # Create a guaranteed datetime _date column.
    # --------------------------------------------------------

    if date_column is not None:

        df["_date"] = pd.to_datetime(
            df[date_column],
            errors="coerce"
        )

    # ========================================================
    # DETECT BUSINESS COLUMNS
    # ========================================================

    revenue_col = find_column(
        df,
        [
            "Revenue",
            "Sales",
            "Revenue Amount",
            "Sales Amount"
        ]
    )

    quantity_col = find_column(
        df,
        [
            "Quantity",
            "Units",
            "Qty",
            "Order Quantity"
        ]
    )

    profit_col = find_column(
        df,
        [
            "Profit",
            "Net Profit",
            "Gross Profit"
        ]
    )

    order_col = find_column(
        df,
        [
            "Order ID",
            "OrderID",
            "Order_Id",
            "Invoice",
            "Invoice ID",
            "Transaction ID",
            "Transaction_ID",
            "ID"
        ]
    )

    customer_col = find_column(
        df,
        [
            "Customer",
            "Customer Name",
            "Customer ID",
            "Customer_ID",
            "Client"
        ]
    )

    # ========================================================
    # REVENUE VALIDATION
    # ========================================================

    if revenue_col is None:

        st.error(
            "A Revenue or Sales column is required "
            "for the Executive Overview."
        )

        st.dataframe(
            df.head(100),
            use_container_width=True,
            hide_index=True
        )

        return

    # ========================================================
    # NUMERIC SERIES
    # ========================================================

    revenue = pd.to_numeric(
        df[revenue_col],
        errors="coerce"
    ).fillna(0)

    if quantity_col:

        quantity = pd.to_numeric(
            df[quantity_col],
            errors="coerce"
        ).fillna(0)

    else:

        quantity = pd.Series(
            0.0,
            index=df.index
        )

    if profit_col:

        profit = pd.to_numeric(
            df[profit_col],
            errors="coerce"
        ).fillna(0)

    else:

        profit = pd.Series(
            0.0,
            index=df.index
        )

    # ========================================================
    # EXECUTIVE KPIs
    # ========================================================

    total_revenue = float(
        revenue.sum()
    )

    total_profit = (
        float(profit.sum())
        if profit_col
        else None
    )

    total_quantity = (
        float(quantity.sum())
        if quantity_col
        else None
    )

    if order_col:

        order_count = int(
            df[order_col]
            .dropna()
            .nunique()
        )

    else:

        order_count = len(df)

    if (
        total_profit is not None
        and total_revenue != 0
    ):

        margin = (
            total_profit
            / total_revenue
            * 100
        )

    else:

        margin = None

    # ========================================================
    # KPI DISPLAY
    # ========================================================

    kpi_row(
        [
            {
                "label": "Revenue",
                "value": fmt_currency(
                    total_revenue
                ),
            },
            {
                "label": "Orders / Records",
                "value": f"{order_count:,}",
            },
            {
                "label": "Units",
                "value": (
                    f"{total_quantity:,.0f}"
                    if quantity_col
                    else "—"
                ),
            },
            {
                "label": "Profit",
                "value": (
                    fmt_currency(total_profit)
                    if total_profit is not None
                    else "—"
                ),
            },
            {
                "label": "Profit Margin",
                "value": (
                    f"{margin:.1f}%"
                    if margin is not None
                    else "—"
                ),
            },
        ]
    )

    # ========================================================
    # MONTHLY DATA
    # ========================================================

    monthly = pd.DataFrame()

    if "_date" in df.columns:

        temp = df.copy()

        temp["_revenue"] = revenue
        temp["_quantity"] = quantity

        if profit_col:
            temp["_profit"] = profit

        # Remove invalid dates
        temp = temp.dropna(
            subset=["_date"]
        ).copy()

        if not temp.empty:

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Create Month BEFORE groupby.
            #
            # This prevents the previous KeyError:
            # KeyError: '_date'
            #
            # We never expect `_date` to survive aggregation.
            # ------------------------------------------------

            temp["Month"] = (
                temp["_date"]
                .dt.to_period("M")
                .dt.to_timestamp()
            )

            # ------------------------------------------------
            # Monthly revenue
            # ------------------------------------------------

            monthly = (
                temp
                .groupby("Month", as_index=False)
                .agg(
                    Revenue=(
                        "_revenue",
                        "sum"
                    ),
                    Units=(
                        "_quantity",
                        "sum"
                    ),
                    Records=(
                        "_revenue",
                        "size"
                    ),
                )
            )

            # ------------------------------------------------
            # Monthly profit
            # ------------------------------------------------

            if profit_col:

                monthly_profit = (
                    temp
                    .groupby("Month")["_profit"]
                    .sum()
                    .rename("Profit")
                    .reset_index()
                )

                monthly = monthly.merge(
                    monthly_profit,
                    on="Month",
                    how="left"
                )

            # ------------------------------------------------
            # Growth
            # ------------------------------------------------

            monthly = (
                monthly
                .sort_values("Month")
                .reset_index(drop=True)
            )

            monthly["Growth"] = (
                monthly["Revenue"]
                .pct_change()
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .fillna(0)
                * 100
            )

            # ------------------------------------------------
            # Profit margin
            # ------------------------------------------------

            if "Profit" in monthly.columns:

                monthly["Profit Margin"] = np.where(
                    monthly["Revenue"] != 0,
                    (
                        monthly["Profit"]
                        / monthly["Revenue"]
                    ) * 100,
                    0
                )

    # ========================================================
    # REUSABLE REVENUE GROUP FUNCTION
    # ========================================================

    def revenue_group(
        column,
        top_n=10
    ):

        if (
            column is None
            or column not in df.columns
        ):
            return pd.DataFrame()

        grouped_source = pd.DataFrame(
            {
                column: (
                    df[column]
                    .fillna("Unknown")
                    .astype(str)
                    .str.strip()
                ),
                "Revenue": revenue,
            }
        )

        grouped_source[column] = (
            grouped_source[column]
            .replace("", "Unknown")
        )

        result = (
            grouped_source
            .groupby(
                column,
                as_index=False
            )["Revenue"]
            .sum()
            .sort_values(
                "Revenue",
                ascending=False
            )
            .head(top_n)
        )

        return result

    # ========================================================
    # SAFE CHART RENDERER
    # ========================================================

    def show(fig, title):

        if fig is not None:

            safe_plot(
                fig,
                title
            )

    # ========================================================
    # CHART 1
    # MONTHLY REVENUE TREND
    # ========================================================

    c1, c2 = st.columns(2)

    with c1:

        if not monthly.empty:

            fig = px.line(
                monthly,
                x="Month",
                y="Revenue",
                markers=True,
                title="1. Monthly Revenue Trend"
            )

            fig.update_yaxes(
                tickprefix="₹",
                separatethousands=True
            )

            fig.update_layout(
                hovermode="x unified"
            )

            show(
                fig,
                "1. Monthly Revenue Trend"
            )

        else:

            st.info(
                "Chart 1: Valid date data "
                "is not available."
            )

    # ========================================================
    # CHART 2
    # REVENUE GROWTH
    # ========================================================

    with c2:

        if not monthly.empty:

            fig = px.line(
                monthly,
                x="Month",
                y="Growth",
                markers=True,
                title="2. Revenue Growth Momentum"
            )

            fig.update_yaxes(
                ticksuffix="%"
            )

            fig.update_layout(
                hovermode="x unified"
            )

            show(
                fig,
                "2. Revenue Growth Momentum"
            )

        else:

            st.info(
                "Chart 2: Valid date data "
                "is not available."
            )

    # ========================================================
    # CHART 3
    # REVENUE BY CATEGORY
    # ========================================================

    c3, c4 = st.columns(2)

    with c3:

        data = revenue_group(
            "Category"
        )

        if not data.empty:

            fig = px.bar(
                data,
                x="Category",
                y="Revenue",
                title="3. Revenue by Category",
                text_auto=".2s"
            )

            fig.update_yaxes(
                tickprefix="₹"
            )

            show(
                fig,
                "3. Revenue by Category"
            )

        else:

            st.info(
                "Chart 3: Category data "
                "is not available."
            )

    # ========================================================
    # CHART 4
    # REVENUE BY REGION
    # ========================================================

    with c4:

        data = revenue_group(
            "Region"
        )

        if not data.empty:

            fig = px.bar(
                data,
                x="Region",
                y="Revenue",
                title="4. Revenue by Region",
                text_auto=".2s"
            )

            fig.update_yaxes(
                tickprefix="₹"
            )

            show(
                fig,
                "4. Revenue by Region"
            )

        else:

            st.info(
                "Chart 4: Region data "
                "is not available."
            )

    # ========================================================
    # CHART 5
    # TOP PRODUCTS
    # ========================================================

    c5, c6 = st.columns(2)

    with c5:

        data = revenue_group(
            "Product",
            10
        )

        if data.empty:

            # Some Superstore datasets use
            # Product Name instead of Product.
            data = revenue_group(
                "Product Name",
                10
            )

            product_dimension = (
                "Product Name"
                if "Product Name" in df.columns
                else "Product"
            )

        else:

            product_dimension = "Product"

        if not data.empty:

            data = data.sort_values(
                "Revenue",
                ascending=True
            )

            fig = px.bar(
                data,
                x="Revenue",
                y=product_dimension,
                orientation="h",
                title="5. Top 10 Products by Revenue",
                text_auto=".2s"
            )

            fig.update_xaxes(
                tickprefix="₹"
            )

            show(
                fig,
                "5. Top 10 Products by Revenue"
            )

        else:

            st.info(
                "Chart 5: Product data "
                "is not available."
            )

    # ========================================================
    # CHART 6
    # REVENUE MIX
    # ========================================================

    with c6:

        if "Branch" in df.columns:

            dimension = "Branch"

        elif "City" in df.columns:

            dimension = "City"

        elif "Region" in df.columns:

            dimension = "Region"

        else:

            dimension = None

        data = (
            revenue_group(
                dimension,
                10
            )
            if dimension
            else pd.DataFrame()
        )

        if not data.empty:

            fig = px.pie(
                data,
                names=dimension,
                values="Revenue",
                hole=0.48,
                title=(
                    f"6. Revenue Mix by "
                    f"{dimension}"
                )
            )

            show(
                fig,
                f"6. Revenue Mix by {dimension}"
            )

        else:

            st.info(
                "Chart 6: Branch, City or "
                "Region data is not available."
            )

    # ========================================================
    # CHART 7
    # QUANTITY VS REVENUE
    # ========================================================

    c7, c8 = st.columns(2)

    with c7:

        if quantity_col:

            scatter = pd.DataFrame(
                {
                    "Quantity": quantity,
                    "Revenue": revenue,
                }
            )

            scatter = (
                scatter
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .dropna()
            )

            if not scatter.empty:

                fig = px.scatter(
                    scatter,
                    x="Quantity",
                    y="Revenue",
                    title="7. Quantity vs Revenue",
                    opacity=0.65
                )

                fig.update_yaxes(
                    tickprefix="₹"
                )

                show(
                    fig,
                    "7. Quantity vs Revenue"
                )

            else:

                st.info(
                    "Chart 7: No valid numeric "
                    "observations."
                )

        else:

            st.info(
                "Chart 7: Quantity data "
                "is not available."
            )

    # ========================================================
    # CHART 8
    # MONTHLY PROFIT / CUSTOMER REVENUE
    # ========================================================

    with c8:

        if (
            profit_col
            and not monthly.empty
            and "Profit" in monthly.columns
        ):

            fig = px.bar(
                monthly,
                x="Month",
                y="Profit",
                title="8. Monthly Profit Trend"
            )

            fig.update_yaxes(
                tickprefix="₹"
            )

            show(
                fig,
                "8. Monthly Profit Trend"
            )

        else:

            # ------------------------------------------------
            # Fallback:
            # Customer revenue concentration
            # ------------------------------------------------

            if customer_col:

                data = revenue_group(
                    customer_col,
                    10
                )

                if not data.empty:

                    data = data.sort_values(
                        "Revenue",
                        ascending=True
                    )

                    fig = px.bar(
                        data,
                        x="Revenue",
                        y=customer_col,
                        orientation="h",
                        title="8. Top Customers by Revenue",
                        text_auto=".2s"
                    )

                    fig.update_xaxes(
                        tickprefix="₹"
                    )

                    show(
                        fig,
                        "8. Top Customers by Revenue"
                    )

                else:

                    st.info(
                        "Chart 8: Customer "
                        "data is not available."
                    )

            else:

                st.info(
                    "Chart 8: Profit or Customer "
                    "data is not available."
                )

    # ========================================================
    # EXECUTIVE DATA SNAPSHOT
    # ========================================================

    st.divider()

    section_title(
        "Executive Data Snapshot"
    )

    # --------------------------------------------------------
    # Build a clean preview column list.
    # --------------------------------------------------------

    preferred_columns = [
        date_column,
        "Date",
        "Order Date",
        "Product",
        "Product Name",
        "Category",
        "Region",
        "Branch",
        "City",
        revenue_col,
        quantity_col,
        profit_col,
    ]

    summary_cols = []

    for column in preferred_columns:

        if (
            column
            and column in df.columns
            and column not in summary_cols
        ):

            summary_cols.append(column)

    if summary_cols:

        st.dataframe(
            df[summary_cols].tail(100),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.dataframe(
            df.tail(100),
            use_container_width=True,
            hide_index=True
        )
        
def render_sales_performance(df):

    page_title(
        "Sales Performance",
        "Historical sales performance, growth patterns and period-level trends.",
    )

    df = ensure_date_column(df)

    try:
        monthly = an.monthly_revenue(df)
    except Exception:
        monthly = pd.DataFrame()

    try:
        growth = an.revenue_growth_pct(df)
    except Exception:
        growth = None

    kpi_row([
        {
            "label": "Revenue",
            "value": fmt_currency(
                an.total_revenue(df)
            ),
        },
        {
            "label": "Growth",
            "value": (
                fmt_pct(growth)
                if growth is not None
                else "—"
            ),
        },
        {
            "label": "Orders",
            "value": (
                f"{safe_number(an.total_orders(df)):,.0f}"
            ),
        },
        {
            "label": "Average Order Value",
            "value": fmt_currency(
                an.average_order_value(df)
            ),
        },
        {
            "label": "Monthly Average",
            "value": fmt_currency(
                an.average_monthly_revenue(df)
            ),
        },
    ])

    # --------------------------------------------------------
    # SALES TRENDS
    # --------------------------------------------------------

    section_title(
        "Sales Trends"
    )

    c1, c2 = st.columns(2)

    with c1:

        if not monthly.empty:

            try:

                fig = viz.monthly_trend_chart(
                    monthly,
                    "Monthly Sales Trend",
                )

                safe_plot(
                    fig,
                    "Monthly Sales Trend",
                )

            except Exception as exc:

                st.warning(
                    "Monthly sales chart is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

        try:
            weekly = an.weekly_revenue(df)
        except Exception:
            weekly = pd.DataFrame()

        if (
            weekly is not None
            and not weekly.empty
            and len(weekly) > 3
        ):

            try:

                weekly_chart_data = (
                    weekly.rename(
                        columns={
                            "Week": "Month"
                        }
                    )
                )

                fig = (
                    viz.monthly_trend_chart(
                        weekly_chart_data,
                        "Weekly Sales Trend",
                    )
                )

                safe_plot(
                    fig,
                    "Weekly Sales Trend",
                )

            except Exception:
                pass

    with c2:

        if len(monthly) > 1:

            try:

                fig = viz.growth_chart(
                    monthly,
                    "Month-over-Month Growth",
                )

                safe_plot(
                    fig,
                    "Month-over-Month Growth",
                )

            except Exception as exc:

                st.warning(
                    "Growth chart is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

        try:
            yoy = an.yoy_growth(df)
        except Exception:
            yoy = pd.DataFrame()

        if yoy is not None and len(yoy) > 1:

            try:

                yoy_data = yoy.rename(
                    columns={
                        "Year": "Month"
                    }
                )

                fig = viz.growth_chart(
                    yoy_data,
                    "Year-over-Year Growth",
                )

                safe_plot(
                    fig,
                    "Year-over-Year Growth",
                )

            except Exception:
                pass

    # --------------------------------------------------------
    # QUARTERLY PERFORMANCE
    # --------------------------------------------------------

    try:
        quarterly = an.quarterly_performance(df)
    except Exception:
        quarterly = pd.DataFrame()

    if (
        quarterly is not None
        and not quarterly.empty
    ):

        section_title(
            "Quarterly Performance"
        )

        try:

            quarterly_chart = (
                quarterly.rename(
                    columns={
                        "Quarter": "Month"
                    }
                )
            )

            fig = (
                viz.monthly_trend_chart(
                    quarterly_chart,
                    "Quarterly Revenue",
                )
            )

            safe_plot(
                fig,
                "Quarterly Revenue",
            )

        except Exception as exc:

            st.warning(
                "Quarterly chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    if (
        "Target" in df.columns
        and not monthly.empty
    ):

        section_title(
            "Revenue vs Target"
        )

        try:

            monthly_target = (
                df.groupby("Month")[
                    "Target"
                ]
                .sum()
                .reset_index()
            )

            merged = monthly.merge(
                monthly_target,
                on="Month",
                how="left",
            )

            fig = viz.actual_vs_target_chart(
                merged
            )

            safe_plot(
                fig,
                "Revenue vs Target",
            )

        except Exception as exc:

            st.warning(
                "Revenue vs Target chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # MONTHLY TABLE
    # --------------------------------------------------------

    section_title(
        "Monthly Performance Table"
    )

    if monthly.empty:

        st.info(
            "No date information available "
            "to build the monthly performance table."
        )

        return

    try:

        display = monthly.copy()

        if "Month" in display.columns:

            display["MonthLabel"] = (
                pd.to_datetime(
                    display["Month"],
                    errors="coerce",
                )
                .dt.strftime("%b %Y")
            )

        else:

            display["MonthLabel"] = (
                display.index.astype(str)
            )

        required = [
            "MonthLabel",
            "Revenue",
            "Growth %",
            "Orders",
            "AOV",
        ]

        for column in required:

            if column not in display.columns:

                display[column] = np.nan

        table = display[
            required
        ].rename(
            columns={
                "MonthLabel": "Month",
                "AOV": "Average Order Value",
            }
        )

        table["Revenue"] = (
            pd.to_numeric(
                table["Revenue"],
                errors="coerce",
            )
            .map(fmt_currency)
        )

        table["Average Order Value"] = (
            pd.to_numeric(
                table[
                    "Average Order Value"
                ],
                errors="coerce",
            )
            .map(fmt_currency)
        )

        table["Growth %"] = (
            pd.to_numeric(
                table["Growth %"],
                errors="coerce",
            )
            .map(
                lambda value:
                fmt_pct(value)
                if pd.notna(value)
                else "—"
            )
        )

        safe_dataframe(table)

    except Exception as exc:

        st.error(
            "Monthly performance table could not be created."
        )

        st.caption(
            f"Technical details: {exc}"
        )

        return

    # --------------------------------------------------------
    # MONTH DRILL-DOWN
    # --------------------------------------------------------

    month_labels = (
        display[
            "MonthLabel"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )

    if not month_labels:
        return

    selected_month = st.selectbox(
        "Drill into a month",
        options=month_labels[::-1],
    )

    try:

        month_value = display[
            display["MonthLabel"]
            == selected_month
        ]["Month"].iloc[0]

        month_value = pd.to_datetime(
            month_value
        )

        dates = pd.to_datetime(
            df["Date"],
            errors="coerce",
        )

        drill = df[
            dates.dt.to_period("M")
            == month_value.to_period("M")
        ]

        with st.expander(
            f"Records for {selected_month} "
            f"({len(drill):,} rows)"
        ):

            safe_dataframe(
                drill,
                height=450,
            )

    except Exception as exc:

        st.info(
            "Monthly drill-down is unavailable."
        )


# ============================================================
# PRODUCTS & MARKETS
# ============================================================

def render_products_categories(df):

    page_title(
        "Products & Categories",
        "Revenue contribution, profitability and hierarchy across products, categories and sub-categories.",
    )

    df = ensure_date_column(df)

    dimensions = [
        dimension
        for dimension in [
            "Product",
            "Category",
            "Sub-Category",
        ]
        if dimension in df.columns
    ]

    if not dimensions:

        st.info(
            "No product, category or sub-category "
            "columns were detected."
        )

        return

    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------

    snapshot = []

    for dimension in dimensions:

        try:

            top = an.top_performer(
                df,
                dimension,
            )

        except Exception:

            top = None

        snapshot.append({
            "label": f"Top {dimension}",
            "value": safe_text(top),
        })

    highest_growth = None

    for dimension in dimensions:

        try:

            fastest = an.fastest_growing(
                df,
                dimension,
            )

        except Exception:

            fastest = None

        if fastest:

            highest_growth = (
                f"{safe_text(fastest)} "
                f"({dimension})"
            )

            break

    snapshot.append({
        "label": "Highest Growth Segment",
        "value": safe_text(
            highest_growth
        ),
    })

    kpi_row(
        snapshot[:5]
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tabs = st.tabs(
        dimensions
    )

    for tab, dimension in zip(
        tabs,
        dimensions,
    ):

        with tab:

            try:

                performance = (
                    an.performance_by(
                        df,
                        dimension,
                    )
                )

            except Exception as exc:

                st.warning(
                    f"{dimension} analysis is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

                continue

            if (
                performance is None
                or performance.empty
            ):

                st.info(
                    f"No data available for {dimension}."
                )

                continue

            c1, c2 = st.columns(2)

            with c1:

                try:

                    fig = viz.bar_by_dimension(
                        performance,
                        dimension,
                        title=(
                            f"Revenue by {dimension}"
                        ),
                    )

                    safe_plot(
                        fig,
                        f"Revenue by {dimension}",
                    )

                except Exception as exc:

                    st.warning(
                        "Revenue contribution chart is unavailable."
                    )

                    st.caption(
                        f"Technical details: {exc}"
                    )

            with c2:

                try:

                    fig = viz.contribution_pie(
                        performance,
                        dimension,
                        title=(
                            f"{dimension} Contribution %"
                        ),
                    )

                    safe_plot(
                        fig,
                        f"{dimension} Contribution %",
                    )

                except Exception as exc:

                    st.warning(
                        "Contribution chart is unavailable."
                    )

                    st.caption(
                        f"Technical details: {exc}"
                    )

            # ------------------------------------------------
            # TOP 5 TREND
            # ------------------------------------------------

            if (
                "Month" in df.columns
                and "Revenue" in df.columns
            ):

                try:

                    trend_data = (
                        df.groupby(
                            [
                                "Month",
                                dimension,
                            ]
                        )["Revenue"]
                        .sum()
                        .reset_index()
                    )

                    top_entities = (
                        performance
                        .head(5)[dimension]
                        .tolist()
                    )

                    trend_data = trend_data[
                        trend_data[
                            dimension
                        ].isin(
                            top_entities
                        )
                    ]

                    if not trend_data.empty:

                        fig = go.Figure()

                        for entity in top_entities:

                            subset = (
                                trend_data[
                                    trend_data[
                                        dimension
                                    ]
                                    == entity
                                ]
                            )

                            if subset.empty:
                                continue

                            fig.add_trace(
                                go.Scatter(
                                    x=subset[
                                        "Month"
                                    ],
                                    y=subset[
                                        "Revenue"
                                    ],
                                    mode=(
                                        "lines+markers"
                                    ),
                                    name=str(
                                        entity
                                    ),
                                )
                            )

                        safe_plot(
                            fig,
                            f"{dimension} Trend — Top 5",
                        )

                except Exception:
                    pass

            # ------------------------------------------------
            # RANKED TABLE
            # ------------------------------------------------

            st.write(
                f"Ranked {dimension} Performance"
            )

            table = performance.copy()

            for column in [
                "Revenue",
                "AOV",
            ]:

                if column in table.columns:

                    table[column] = (
                        pd.to_numeric(
                            table[column],
                            errors="coerce",
                        )
                        .map(fmt_currency)
                    )

            if "Contribution %" in table.columns:

                table["Contribution %"] = (
                    pd.to_numeric(
                        table[
                            "Contribution %"
                        ],
                        errors="coerce",
                    )
                    .map(
                        lambda value:
                        f"{value:.1f}%"
                        if pd.notna(value)
                        else "—"
                    )
                )

            if "Growth %" in table.columns:

                table["Growth %"] = (
                    pd.to_numeric(
                        table["Growth %"],
                        errors="coerce",
                    )
                    .map(
                        lambda value:
                        fmt_pct(value)
                        if pd.notna(value)
                        else "—"
                    )
                )

            safe_dataframe(table)

    # --------------------------------------------------------
    # CATEGORY → SUB-CATEGORY → PRODUCT HIERARCHY
    # --------------------------------------------------------

    if (
        "Category" in df.columns
        and "Sub-Category" in df.columns
    ):

        section_title(
            "Category → Sub-Category → Product Drill-down"
        )

        categories = sorted(
            df["Category"]
            .dropna()
            .unique()
            .tolist(),
            key=lambda x: str(x),
        )

        if categories:

            selected_category = st.selectbox(
                "Select Category",
                categories,
            )

            category_df = df[
                df["Category"]
                == selected_category
            ]

            subcategories = sorted(
                category_df[
                    "Sub-Category"
                ]
                .dropna()
                .unique()
                .tolist(),
                key=lambda x: str(x),
            )

            if subcategories:

                selected_subcategory = st.selectbox(
                    "Select Sub-Category",
                    subcategories,
                )

                subcategory_df = (
                    category_df[
                        category_df[
                            "Sub-Category"
                        ]
                        == selected_subcategory
                    ]
                )

                if "Product" in subcategory_df.columns:

                    try:

                        product_performance = (
                            an.performance_by(
                                subcategory_df,
                                "Product",
                            )
                        )

                        safe_dataframe(
                            product_performance
                        )

                    except Exception as exc:

                        st.warning(
                            "Product drill-down is unavailable."
                        )

                        st.caption(
                            f"Technical details: {exc}"
                        )

    # --------------------------------------------------------
    # PRODUCT PROFITABILITY (SCATTER)
    # --------------------------------------------------------

    if (
        "Product" in df.columns
        and "Revenue" in df.columns
        and "Profit" in df.columns
    ):

        section_title(
            "Product Profitability — Revenue vs Profit"
        )

        try:

            product_performance = an.performance_by(
                df,
                "Product",
            )

            if (
                product_performance is not None
                and not product_performance.empty
            ):

                scatter_data = product_performance.copy()

                margin_col = None
                for candidate in ["Margin %", "Profit Margin", "Margin"]:
                    if candidate in scatter_data.columns:
                        margin_col = candidate
                        break

                fig = px.scatter(
                    scatter_data,
                    x="Revenue",
                    y="Profit" if "Profit" in scatter_data.columns else scatter_data.columns[-1],
                    size="Revenue",
                    color=margin_col if margin_col else None,
                    hover_name="Product",
                    title="Product Revenue vs Profit",
                )

                safe_plot(
                    fig,
                    "Product Revenue vs Profit",
                )

            else:

                st.info(
                    "No product profitability data is available."
                )

        except Exception as exc:

            st.warning(
                "Product profitability chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # CATEGORY × PRODUCT HEATMAP
    # --------------------------------------------------------

    if (
        "Product" in df.columns
        and "Category" in df.columns
    ):

        section_title(
            "Product × Category Heatmap"
        )

        try:

            pivot = None

            if "Revenue" in df.columns:

                pivot = (
                    df.pivot_table(
                        index="Product",
                        columns="Category",
                        values="Revenue",
                        aggfunc="sum",
                    )
                    .fillna(0)
                )

            if (
                pivot is not None
                and not pivot.empty
            ):

                safe_plot(
                    viz.heatmap_chart(
                        pivot.iloc[
                            :15,
                            :12,
                        ]
                    ),
                    "Product × Category Revenue",
                )

            else:

                st.info(
                    "No product-category matrix is available."
                )

        except Exception as exc:

            st.warning(
                "Product-category heatmap is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )


# ============================================================
# REGIONS / BRANCHES
# ============================================================

def render_regions_branches(df):

    page_title(
        "Regions / Branches",
        "Regional revenue, profitability, growth and geographic market structure.",
    )

    df = ensure_date_column(df)

    if "Branch" in df.columns:
        location_dimensions = [
            dimension
            for dimension in ["Region", "Branch", "City"]
            if dimension in df.columns
        ]
    else:
        location_dimensions = [
            dimension
            for dimension in ["Region", "State", "City"]
            if dimension in df.columns
        ]

    if not location_dimensions:

        st.info(
            "No Region, Branch, State or City columns "
            "were detected in this dataset."
        )

        return

    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------

    snapshot = []

    for dimension in location_dimensions:

        try:

            top = an.top_performer(
                df,
                dimension,
            )

        except Exception:

            top = None

        snapshot.append({
            "label": f"Top {dimension}",
            "value": safe_text(top),
        })

    highest_growth = None

    for dimension in location_dimensions:

        try:

            fastest = an.fastest_growing(
                df,
                dimension,
            )

        except Exception:

            fastest = None

        if fastest:

            highest_growth = (
                f"{safe_text(fastest)} "
                f"({dimension})"
            )

            break

    snapshot.append({
        "label": "Highest Growth Area",
        "value": safe_text(
            highest_growth
        ),
    })

    kpi_row(
        snapshot[:5]
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tabs = st.tabs(
        location_dimensions
    )

    for tab, dimension in zip(
        tabs,
        location_dimensions,
    ):

        with tab:

            try:

                performance = (
                    an.performance_by(
                        df,
                        dimension,
                    )
                )

            except Exception as exc:

                st.warning(
                    f"{dimension} analysis is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

                continue

            if (
                performance is None
                or performance.empty
            ):

                st.info(
                    f"No data available for {dimension}."
                )

                continue

            c1, c2 = st.columns(2)

            with c1:

                try:

                    fig = viz.bar_by_dimension(
                        performance,
                        dimension,
                        title=(
                            f"Revenue by {dimension}"
                        ),
                    )

                    safe_plot(
                        fig,
                        f"Revenue by {dimension}",
                    )

                except Exception as exc:

                    st.warning(
                        "Revenue contribution chart is unavailable."
                    )

                    st.caption(
                        f"Technical details: {exc}"
                    )

            with c2:

                try:

                    fig = viz.contribution_pie(
                        performance,
                        dimension,
                        title=(
                            f"{dimension} Contribution %"
                        ),
                    )

                    safe_plot(
                        fig,
                        f"{dimension} Contribution %",
                    )

                except Exception as exc:

                    st.warning(
                        "Contribution chart is unavailable."
                    )

                    st.caption(
                        f"Technical details: {exc}"
                    )

            # ------------------------------------------------
            # TOP 5 TREND
            # ------------------------------------------------

            if (
                "Month" in df.columns
                and "Revenue" in df.columns
            ):

                try:

                    trend_data = (
                        df.groupby(
                            [
                                "Month",
                                dimension,
                            ]
                        )["Revenue"]
                        .sum()
                        .reset_index()
                    )

                    top_entities = (
                        performance
                        .head(5)[dimension]
                        .tolist()
                    )

                    trend_data = trend_data[
                        trend_data[
                            dimension
                        ].isin(
                            top_entities
                        )
                    ]

                    if not trend_data.empty:

                        fig = go.Figure()

                        for entity in top_entities:

                            subset = (
                                trend_data[
                                    trend_data[
                                        dimension
                                    ]
                                    == entity
                                ]
                            )

                            if subset.empty:
                                continue

                            fig.add_trace(
                                go.Scatter(
                                    x=subset[
                                        "Month"
                                    ],
                                    y=subset[
                                        "Revenue"
                                    ],
                                    mode=(
                                        "lines+markers"
                                    ),
                                    name=str(
                                        entity
                                    ),
                                )
                            )

                        safe_plot(
                            fig,
                            f"{dimension} Trend — Top 5",
                        )

                except Exception:
                    pass

            # ------------------------------------------------
            # RANKED TABLE
            # ------------------------------------------------

            st.write(
                f"Ranked {dimension} Performance"
            )

            table = performance.copy()

            for column in [
                "Revenue",
                "AOV",
            ]:

                if column in table.columns:

                    table[column] = (
                        pd.to_numeric(
                            table[column],
                            errors="coerce",
                        )
                        .map(fmt_currency)
                    )

            if "Contribution %" in table.columns:

                table["Contribution %"] = (
                    pd.to_numeric(
                        table[
                            "Contribution %"
                        ],
                        errors="coerce",
                    )
                    .map(
                        lambda value:
                        f"{value:.1f}%"
                        if pd.notna(value)
                        else "—"
                    )
                )

            if "Growth %" in table.columns:

                table["Growth %"] = (
                    pd.to_numeric(
                        table["Growth %"],
                        errors="coerce",
                    )
                    .map(
                        lambda value:
                        fmt_pct(value)
                        if pd.notna(value)
                        else "—"
                    )
                )

            safe_dataframe(table)

    # --------------------------------------------------------
    # REGION → BRANCH/CITY DRILL-DOWN
    # --------------------------------------------------------

    drill_child = "Branch" if "Branch" in df.columns else ("City" if "City" in df.columns else None)

    if (
        "Region" in df.columns
        and drill_child is not None
    ):

        section_title(
            f"Region → {drill_child} → Product Drill-down"
        )

        regions = sorted(
            df["Region"]
            .dropna()
            .unique()
            .tolist(),
            key=lambda x: str(x),
        )

        if regions:

            selected_region = st.selectbox(
                "Select Region",
                regions,
            )

            region_df = df[
                df["Region"]
                == selected_region
            ]

            children = sorted(
                region_df[
                    drill_child
                ]
                .dropna()
                .unique()
                .tolist(),
                key=lambda x: str(x),
            )

            if children:

                selected_child = st.selectbox(
                    f"Select {drill_child}",
                    children,
                )

                child_df = (
                    region_df[
                        region_df[
                            drill_child
                        ]
                        == selected_child
                    ]
                )

                if "Product" in child_df.columns:

                    try:

                        product_performance = (
                            an.performance_by(
                                child_df,
                                "Product",
                            )
                        )

                        safe_dataframe(
                            product_performance
                        )

                    except Exception as exc:

                        st.warning(
                            "Product drill-down is unavailable."
                        )

                        st.caption(
                            f"Technical details: {exc}"
                        )

    # --------------------------------------------------------
    # PRODUCT × REGION HEATMAP
    # --------------------------------------------------------

    if (
        "Product" in df.columns
        and "Region" in df.columns
    ):

        section_title(
            "Product × Region Heatmap"
        )

        try:

            matrix = (
                an.product_region_matrix(
                    df
                )
            )

            if (
                matrix is not None
                and not matrix.empty
            ):

                safe_plot(
                    viz.heatmap_chart(
                        matrix.iloc[
                            :15,
                            :12,
                        ]
                    ),
                    "Product × Region Revenue",
                )

            else:

                st.info(
                    "No product-region matrix is available."
                )

        except Exception as exc:

            st.warning(
                "Product-region heatmap is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # REGIONAL GROWTH TREND
    # --------------------------------------------------------

    if (
        "Region" in df.columns
        and "Month" in df.columns
        and "Revenue" in df.columns
    ):

        section_title(
            "Regional Revenue Trend"
        )

        try:

            trend_data = (
                df.groupby(["Month", "Region"])["Revenue"]
                .sum()
                .reset_index()
            )

            if not trend_data.empty:

                fig = px.line(
                    trend_data,
                    x="Month",
                    y="Revenue",
                    color="Region",
                    markers=True,
                    title="Revenue Trend by Region",
                )

                safe_plot(
                    fig,
                    "Revenue Trend by Region",
                )

        except Exception as exc:

            st.warning(
                "Regional trend chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # GEOGRAPHIC RISK — LOW MARGIN / DECLINING REGIONS
    # --------------------------------------------------------

    if "Region" in df.columns:

        section_title(
            "Geographic Risk — Margin & Growth by Region"
        )

        try:

            region_performance = an.performance_by(
                df,
                "Region",
            )

            if (
                region_performance is not None
                and not region_performance.empty
            ):

                margin_col = None
                for candidate in ["Margin %", "Profit Margin", "Margin"]:
                    if candidate in region_performance.columns:
                        margin_col = candidate
                        break

                growth_col = "Growth %" if "Growth %" in region_performance.columns else None

                if margin_col and growth_col:

                    risk_data = region_performance.copy()

                    fig = px.scatter(
                        risk_data,
                        x=growth_col,
                        y=margin_col,
                        size="Revenue" if "Revenue" in risk_data.columns else None,
                        hover_name="Region",
                        title="Regional Risk — Growth vs Margin",
                    )

                    safe_plot(
                        fig,
                        "Regional Risk — Growth vs Margin",
                    )

                else:

                    st.info(
                        "Margin and growth figures are required "
                        "for the geographic risk view."
                    )

            else:

                st.info(
                    "No regional performance data is available."
                )

        except Exception as exc:

            st.warning(
                "Geographic risk chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )


# ============================================================
# FORECAST & PLANNING
# ============================================================

# ============================================================
# FORECAST & PLANNING
# ============================================================

def render_forecasting(df):

    page_title(
        "Forecasting",
        "Historical patterns, forecasted revenue, model validation and planning signals.",
    )

    df = ensure_date_column(df)

    # --------------------------------------------------------
    # MONTHLY DATA
    # --------------------------------------------------------

    try:
        monthly = an.monthly_revenue(df)
    except Exception:
        monthly = pd.DataFrame()

    try:

        sufficient, message = (
            data_validator.sufficient_for_forecasting(
                df
            )
        )

    except Exception:

        sufficient = False
        message = (
            "Forecast validation could not be completed."
        )

    horizon = st.select_slider(
        "Forecast Horizon",
        options=[
            3,
            6,
            12,
        ],
        value=3,
        format_func=lambda x:
        f"{x} Months",
    )

    if not sufficient:

        st.warning(
            message
        )

    if (
        monthly is None
        or monthly.empty
        or len(monthly) < 2
    ):

        st.warning(
            "Insufficient historical data for reliable forecasting."
        )

        return

    # --------------------------------------------------------
    # FORECAST ENGINE
    # --------------------------------------------------------

    try:

        result = fc.generate_forecast(
            monthly,
            horizon=horizon,
        )

    except Exception as exc:

        st.error(
            "Forecast generation could not be completed."
        )

        st.caption(
            f"Technical details: {exc}"
        )

        return

    if not isinstance(
        result,
        dict,
    ):

        st.error(
            "Forecast engine returned an invalid result."
        )

        return

    if not result.get(
        "sufficient_data"
    ):

        st.warning(
            result.get(
                "message",
                "Insufficient historical data.",
            )
        )

        return

    if result.get(
        "reliability_note"
    ):

        st.info(
            result["reliability_note"]
        )

    forecast_table = (
        result.get(
            "forecast_table"
        )
    )

    if forecast_table is None:

        st.error(
            "Forecast table was not generated."
        )

        return

    if not isinstance(
        forecast_table,
        pd.DataFrame,
    ):

        try:

            forecast_table = pd.DataFrame(
                forecast_table
            )

        except Exception:

            st.error(
                "Forecast table has an invalid structure."
            )

            return

    # --------------------------------------------------------
    # SELECTED MODEL / METRICS
    # --------------------------------------------------------

    selected_model = result.get(
        "selected_model"
    )

    model_comparison = result.get(
        "model_comparison",
        {},
    )

    if not isinstance(
        model_comparison,
        dict,
    ):

        model_comparison = {}

    mape = None

    if (
        result.get("model_validated")
        and selected_model in model_comparison
    ):

        selected_metrics = (
            model_comparison.get(
                selected_model,
                {},
            )
        )

        if isinstance(
            selected_metrics,
            dict,
        ):

            mape = selected_metrics.get(
                "MAPE"
            )

            try:

                if (
                    mape is not None
                    and not np.isfinite(
                        float(mape)
                    )
                ):

                    mape = None

            except (
                TypeError,
                ValueError,
            ):

                mape = None

    uncertainty = (
        f"±{float(mape):.1f}%"
        if mape is not None
        else "Not established"
    )

    expected_growth = (
        result.get(
            "expected_growth_next_month"
        )
    )

    # --------------------------------------------------------
    # HORIZON TOTAL
    # --------------------------------------------------------

    forecast_total = 0.0

    try:

        if "Forecast" in forecast_table.columns:

            forecast_values = pd.to_numeric(
                forecast_table[
                    "Forecast"
                ],
                errors="coerce",
            )

            forecast_total = (
                forecast_values
                .replace(
                    [np.inf, -np.inf],
                    np.nan,
                )
                .fillna(0)
                .sum()
            )

        elif (
            horizon == 3
            and result.get(
                "three_month_forecast"
            ) is not None
        ):

            forecast_total = safe_number(
                result.get(
                    "three_month_forecast"
                )
            )

    except Exception:

        forecast_total = 0.0

    # --------------------------------------------------------
    # KPI SUMMARY
    # --------------------------------------------------------

    kpi_row([
        {
            "label": "Next Month Forecast",
            "value": fmt_currency(
                result.get(
                    "next_month_forecast"
                )
            ),
        },
        {
            "label": f"{horizon}-Month Forecast",
            "value": fmt_currency(
                forecast_total
            ),
        },
        {
            "label": "Expected Growth",
            "value": (
                fmt_pct(
                    expected_growth
                )
                if expected_growth is not None
                else "—"
            ),
        },
        {
            "label": "Forecast Uncertainty",
            "value": uncertainty,
        },
        {
            "label": "Selected Model",
            "value": safe_text(
                selected_model,
                "Auto Selected",
            ),
        },
    ])

    # --------------------------------------------------------
    # FORECAST CHART
    # --------------------------------------------------------

    section_title(
        "Forecast Chart"
    )

    try:

        forecast_fig = viz.forecast_chart(
            monthly,
            forecast_table,
        )

        if forecast_fig is not None:

            safe_plot(
                forecast_fig,
                "Sales Forecast",
            )

        else:

            st.info(
                "Forecast chart is unavailable "
                "for the selected data."
            )

    except Exception as exc:

        st.warning(
            "The forecast chart could not be rendered."
        )

        st.caption(
            f"Technical details: {exc}"
        )

    st.caption(
        "Historical actual sales are shown as the actual series; "
        "future periods represent model-generated estimates."
    )

    # --------------------------------------------------------
    # FORECAST TABLE
    # --------------------------------------------------------

    section_title(
        "Forecast Table"
    )

    try:

        display = forecast_table.copy()

        # Remove duplicate columns
        display = display.loc[
            :,
            ~display.columns.duplicated()
        ]

        # Numeric safety
        numeric_columns = (
            display
            .select_dtypes(
                include=[np.number]
            )
            .columns
        )

        for column in numeric_columns:

            display[column] = (
                display[column]
                .replace(
                    [np.inf, -np.inf],
                    np.nan,
                )
            )

        # Date / period
        for column in display.columns:

            try:

                if pd.api.types.is_datetime64_any_dtype(
                    display[column]
                ):

                    display[column] = (
                        display[column]
                        .dt.strftime("%b %Y")
                    )

                elif isinstance(
                    display[column].dtype,
                    pd.PeriodDtype,
                ):

                    display[column] = (
                        display[column]
                        .astype(str)
                    )

            except Exception:
                pass

        if "MonthLabel" in display.columns:

            display = display.rename(
                columns={
                    "MonthLabel": "Month"
                }
            )

        # Currency
        for column in [
            "Forecast",
            "Lower Bound",
            "Upper Bound",
            "Actual",
            "Predicted",
        ]:

            if column in display.columns:

                values = pd.to_numeric(
                    display[column],
                    errors="coerce",
                )

                display[column] = (
                    values.map(
                        lambda value:
                        fmt_currency(value)
                        if pd.notna(value)
                        else "—"
                    )
                )

        # Percentage
        if (
            "Expected Growth %"
            in display.columns
        ):

            values = pd.to_numeric(
                display[
                    "Expected Growth %"
                ],
                errors="coerce",
            )

            display[
                "Expected Growth %"
            ] = values.map(
                lambda value:
                fmt_pct(value)
                if pd.notna(value)
                else "—"
            )

        # Final object safety
        for column in display.columns:

            if display[column].dtype == "object":

                display[column] = (
                    display[column]
                    .apply(
                        lambda value:
                        safe_text(value)
                    )
                )

        safe_dataframe(
            display,
            height=min(
                420,
                100 + len(display) * 38,
            ),
        )

    except Exception as exc:

        st.error(
            "The forecast table could not be rendered."
        )

        st.caption(
            f"Technical details: {exc}"
        )

    # --------------------------------------------------------
    # MODEL ACCURACY
    # --------------------------------------------------------

    section_title(
        "Model Selection & Accuracy"
    )

    if result.get(
        "model_validated"
    ):

        rows = []

        for name, metrics in (
            model_comparison.items()
        ):

            if not isinstance(
                metrics,
                dict,
            ):
                continue

            mae = metrics.get(
                "MAE"
            )

            rmse = metrics.get(
                "RMSE"
            )

            model_mape = metrics.get(
                "MAPE"
            )

            mae_value = (
                fmt_currency(mae)
                if mae is not None
                else "—"
            )

            rmse_value = (
                fmt_currency(rmse)
                if rmse is not None
                else "—"
            )

            try:

                mape_value = (
                    f"{float(model_mape):.1f}%"
                    if (
                        model_mape is not None
                        and np.isfinite(
                            float(model_mape)
                        )
                    )
                    else "—"
                )

            except (
                TypeError,
                ValueError,
            ):

                mape_value = "—"

            rows.append({
                "Model": str(name),
                "Selected": (
                    "Yes"
                    if name == selected_model
                    else ""
                ),
                "MAE": mae_value,
                "RMSE": rmse_value,
                "MAPE": mape_value,
            })

        if rows:

            comparison = pd.DataFrame(
                rows
            )

            comparison["_sort"] = (
                comparison["Selected"]
                .eq("Yes")
                .astype(int)
            )

            comparison = (
                comparison
                .sort_values(
                    "_sort",
                    ascending=False,
                )
                .drop(
                    columns="_sort"
                )
                .reset_index(
                    drop=True
                )
            )

            safe_dataframe(
                comparison
            )

        else:

            st.info(
                "Model comparison metrics are not available."
            )

        st.caption(
            f"Selected Model: "
            f"{safe_text(selected_model, 'Auto Selected')} | "
            f"Horizon: {horizon} months | "
            f"History: "
            f"{safe_text(result.get('history_months'))} months | "
            "Selection is based on historical holdout validation."
        )

    else:

        st.warning(
            "Historical data is insufficient to validate "
            "forecast model accuracy. Treat this forecast "
            "as indicative rather than statistically established."
        )

    # --------------------------------------------------------
    # FORECAST EXPLANATION
    # --------------------------------------------------------

    section_title(
        "Forecast Explanation"
    )

    explanation = []

    try:

        recent_growth = (
            an.revenue_growth_pct(df)
        )

    except Exception:

        recent_growth = None

    if recent_growth is not None:

        explanation.append(
            "Recent month-over-month revenue trend: "
            f"{safe_number(recent_growth):+.1f}%."
        )

    # --------------------------------------------------------
    # TOP BUSINESS DRIVER
    # --------------------------------------------------------

    for dimension in [
        "Product",
        "Category",
    ]:

        if dimension not in df.columns:
            continue

        try:

            top = an.top_performer(
                df,
                dimension,
            )

            performance = an.performance_by(
                df,
                dimension,
            )

        except Exception:

            continue

        if (
            top
            and performance is not None
            and not performance.empty
        ):

            row = performance.iloc[0]

            contribution = row.get(
                "Contribution %",
                np.nan,
            )

            growth_value = row.get(
                "Growth %",
                np.nan,
            )

            contribution_text = (
                f"{safe_number(contribution):.1f}%"
                if pd.notna(
                    contribution
                )
                else "—"
            )

            growth_text = (
                f"{safe_number(growth_value):+.1f}%"
                if pd.notna(
                    growth_value
                )
                else None
            )

            if growth_text:

                explanation.append(
                    f"{safe_text(top)} contributed "
                    f"{contribution_text} of recent revenue "
                    f"with {growth_text} growth."
                )

            else:

                explanation.append(
                    f"{safe_text(top)} contributed "
                    f"{contribution_text} of recent revenue."
                )

            break

    # --------------------------------------------------------
    # SEASONALITY
    # --------------------------------------------------------

    history_months = safe_number(
        result.get(
            "history_months",
            0,
        ),
        0,
    )

    try:

        seasonal_threshold = (
            fc.MIN_MONTHS_FOR_SEASONAL
        )

    except Exception:

        seasonal_threshold = 12

    if (
        history_months
        >= seasonal_threshold
    ):

        explanation.append(
            "Sufficient history is available "
            "to evaluate seasonal patterns."
        )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    if explanation:

        for item in explanation:
            st.write(
                f"• {item}"
            )

    else:

        st.info(
            "No additional forecast explanation signals "
            "could be established from the available data."
        )

    st.caption(
        "Forecast explanations are based on measurable "
        "historical evidence."
    )


# ============================================================
# FORECAST MODEL EVALUATION
# ============================================================

def render_forecast_evaluation(df):
    """Present the model-comparison results already produced by forecasting.py."""
    page_title(
        "Forecast Model Evaluation",
        "Compare the forecasting models already evaluated by INAIBA using consistent validation metrics.",
    )

    if df is None or df.empty:
        st.info("No dataset is available for forecast evaluation.")
        return

    try:
        monthly = an.monthly_revenue(df)
    except Exception:
        monthly = pd.DataFrame()

    if monthly is None or monthly.empty or len(monthly) < 2:
        st.info("At least two historical periods are required to evaluate forecast models.")
        return

    try:
        result = fc.generate_forecast(monthly, horizon=3)
    except Exception as exc:
        st.warning("Forecast evaluation could not be generated from the current dataset.")
        st.caption(f"Technical details: {exc}")
        return

    comparison = result.get("model_comparison", {})
    selected_model = result.get("selected_model")

    if not isinstance(comparison, dict) or not comparison:
        st.info("The current dataset does not have enough history to produce comparable validation results.")
        return

    rows = []
    for model, metrics in comparison.items():
        if not isinstance(metrics, dict):
            continue
        rows.append({
            "Model": model,
            "MAE": metrics.get("MAE"),
            "RMSE": metrics.get("RMSE"),
            "R²": metrics.get("R2"),
            "MAPE": metrics.get("MAPE"),
            "Status": "Selected" if model == selected_model else "Evaluated",
        })

    table = pd.DataFrame(rows)
    if table.empty:
        st.info("No comparable model evaluation results are available.")
        return

    def _mean_metric(name):
        vals = pd.to_numeric(table[name], errors="coerce")
        return vals.mean() if vals.notna().any() else None

    kpi_row([
        {"label": "Models Evaluated", "value": f"{len(table):,}"},
        {"label": "Selected Model", "value": safe_text(selected_model, "—")},
        {"label": "Average MAE", "value": fmt_currency_2(_mean_metric("MAE"))},
        {"label": "Average RMSE", "value": fmt_currency_2(_mean_metric("RMSE"))},
        {"label": "Average MAPE", "value": fmt_pct(_mean_metric("MAPE"))},
    ])

    section_title("Model Comparison")
    display = table.copy()
    for col in ["MAE", "RMSE"]:
        display[col] = pd.to_numeric(display[col], errors="coerce").map(
            lambda x: f"{x:,.2f}" if pd.notna(x) else "—"
        )
    display["R²"] = pd.to_numeric(display["R²"], errors="coerce").map(
        lambda x: f"{x:.3f}" if pd.notna(x) else "—"
    )
    display["MAPE"] = pd.to_numeric(display["MAPE"], errors="coerce").map(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    safe_dataframe(display, height=min(420, 90 + len(display) * 42))

    chart_cols = st.columns(2, gap="large")
    with chart_cols[0]:
        section_title("MAE Comparison")
        fig = px.bar(table, x="Model", y="MAE", text_auto=".2f")
        fig.update_layout(showlegend=False)
        safe_plot(fig, "MAE comparison")
    with chart_cols[1]:
        section_title("RMSE Comparison")
        fig = px.bar(table, x="Model", y="RMSE", text_auto=".2f")
        fig.update_layout(showlegend=False)
        safe_plot(fig, "RMSE comparison")

    chart_cols = st.columns(2, gap="large")
    with chart_cols[0]:
        section_title("R² Comparison")
        fig = px.bar(table, x="Model", y="R²", text_auto=".3f")
        fig.update_layout(showlegend=False)
        safe_plot(fig, "R2 comparison")
    with chart_cols[1]:
        section_title("MAPE Comparison")
        fig = px.bar(table, x="Model", y="MAPE", text_auto=".1f")
        fig.update_layout(showlegend=False)
        safe_plot(fig, "MAPE comparison")

    section_title("Validation Context")
    note = result.get("reliability_note")
    if note:
        st.info(note)
    else:
        st.caption(
            "Metrics are produced by INAIBA's existing holdout validation and model-selection workflow."
        )


# ============================================================
# RISKS & ANOMALIES
# ============================================================
def render_anomalies_risks(df):
    """
    INAIBA - Anomalies & Risks

    Provides:
    - Monthly revenue anomaly detection
    - Dimension-level anomaly detection
    - Revenue anomaly visualization
    - Anomaly detail table
    - Individual transaction outliers
    - Risk interpretation

    Designed to safely handle:
    - DatetimeIndex
    - PeriodIndex
    - Date / Month / Period columns
    - Missing anomaly columns
    - Empty datasets
    """

    # ============================================================
    # PAGE HEADER
    # ============================================================

    page_title(
        "Anomalies & Risks",
        "Unusual revenue movements, transaction outliers and areas requiring attention.",
    )

    # ============================================================
    # VALIDATE DATA
    # ============================================================

    if df is None:
        st.info("No dataset is available for anomaly analysis.")
        return

    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            st.error("The current dataset could not be processed.")
            return

    if df.empty:
        st.info("No records are available for anomaly analysis.")
        return

    # Work on an independent copy
    df = df.copy()

    # ============================================================
    # STANDARDIZE DATE COLUMN
    # ============================================================

    try:
        df = ensure_date_column(df)
    except Exception:
        pass

    # ============================================================
    # MONTHLY REVENUE
    # ============================================================

    try:

        monthly = an.monthly_revenue(df)

        if monthly is None:
            monthly = pd.DataFrame()

        elif not isinstance(monthly, pd.DataFrame):
            monthly = pd.DataFrame(monthly)

    except Exception:
        monthly = pd.DataFrame()

    # ============================================================
    # NORMALIZE MONTHLY DATA
    # 
    # IMPORTANT:
    # anomaly_scatter() expects a Period column.
    # We create it safely regardless of whether the source
    # contains Date, Month, Period or a datetime/period index.
    # ============================================================

    if not monthly.empty:

        monthly = monthly.copy()

        # Remove duplicate columns
        monthly = monthly.loc[
            :,
            ~monthly.columns.duplicated(),
        ]

        # --------------------------------------------------------
        # Create Period column if missing
        # --------------------------------------------------------

        if "Period" not in monthly.columns:

            period_created = False

            # Option 1: Month column
            if "Month" in monthly.columns:

                try:

                    month_values = monthly["Month"]

                    if isinstance(
                        month_values.dtype,
                        pd.PeriodDtype,
                    ):

                        monthly["Period"] = month_values

                    else:

                        parsed = pd.to_datetime(
                            month_values,
                            errors="coerce",
                        )

                        monthly["Period"] = (
                            parsed.dt.to_period("M")
                        )

                    period_created = True

                except Exception:
                    pass

            # Option 2: Date column
            if (
                not period_created
                and "Date" in monthly.columns
            ):

                try:

                    parsed = pd.to_datetime(
                        monthly["Date"],
                        errors="coerce",
                    )

                    monthly["Period"] = (
                        parsed.dt.to_period("M")
                    )

                    period_created = True

                except Exception:
                    pass

            # Option 3: _date column
            if (
                not period_created
                and "_date" in monthly.columns
            ):

                try:

                    parsed = pd.to_datetime(
                        monthly["_date"],
                        errors="coerce",
                    )

                    monthly["Period"] = (
                        parsed.dt.to_period("M")
                    )

                    period_created = True

                except Exception:
                    pass

            # Option 4: Order Date
            if (
                not period_created
                and "Order Date" in monthly.columns
            ):

                try:

                    parsed = pd.to_datetime(
                        monthly["Order Date"],
                        errors="coerce",
                    )

                    monthly["Period"] = (
                        parsed.dt.to_period("M")
                    )

                    period_created = True

                except Exception:
                    pass

            # Option 5: DatetimeIndex
            if (
                not period_created
                and isinstance(
                    monthly.index,
                    pd.DatetimeIndex,
                )
            ):

                try:

                    monthly["Period"] = (
                        monthly.index
                        .to_period("M")
                    )

                    period_created = True

                except Exception:
                    pass

            # Option 6: PeriodIndex
            if (
                not period_created
                and isinstance(
                    monthly.index,
                    pd.PeriodIndex,
                )
            ):

                try:

                    monthly["Period"] = (
                        monthly.index
                    )

                    period_created = True

                except Exception:
                    pass

            # Option 7: Generic index
            if (
                not period_created
                and len(monthly.index) > 0
            ):

                try:

                    parsed = pd.to_datetime(
                        monthly.index,
                        errors="coerce",
                    )

                    monthly["Period"] = (
                        pd.Series(
                            parsed,
                            index=monthly.index,
                        )
                        .dt.to_period("M")
                        .values
                    )

                    period_created = True

                except Exception:
                    pass

        # --------------------------------------------------------
        # Normalize Period
        # --------------------------------------------------------

        if "Period" in monthly.columns:

            try:

                # If already Period dtype
                if isinstance(
                    monthly["Period"].dtype,
                    pd.PeriodDtype,
                ):

                    pass

                else:

                    parsed = pd.to_datetime(
                        monthly["Period"],
                        errors="coerce",
                    )

                    monthly["Period"] = (
                        parsed.dt.to_period("M")
                    )

            except Exception:
                pass

        # --------------------------------------------------------
        # Remove invalid periods
        # --------------------------------------------------------

        if "Period" in monthly.columns:

            try:

                monthly = monthly[
                    monthly["Period"].notna()
                ].copy()

            except Exception:
                pass

        # --------------------------------------------------------
        # Sort chronologically
        # --------------------------------------------------------

        if (
            "Period" in monthly.columns
            and not monthly.empty
        ):

            try:
                monthly = monthly.sort_values(
                    "Period"
                ).reset_index(drop=True)
            except Exception:
                pass

    # ============================================================
    # MONTHLY ANOMALY DETECTION
    # ============================================================

    monthly_anomalies = pd.DataFrame()

    if not monthly.empty:

        try:

            monthly_anomalies = (
                ad.detect_monthly_anomalies(
                    monthly
                )
            )

            if monthly_anomalies is None:
                monthly_anomalies = pd.DataFrame()

            elif not isinstance(
                monthly_anomalies,
                pd.DataFrame,
            ):

                monthly_anomalies = pd.DataFrame(
                    monthly_anomalies
                )

        except Exception:

            monthly_anomalies = pd.DataFrame()

    # ============================================================
    # NORMALIZE ANOMALY PERIOD
    # ============================================================

    if not monthly_anomalies.empty:

        monthly_anomalies = (
            monthly_anomalies.copy()
        )

        monthly_anomalies = monthly_anomalies.loc[
            :,
            ~monthly_anomalies.columns.duplicated(),
        ]

        # Create Period when anomaly detector did not return it
        if "Period" not in monthly_anomalies.columns:

            created = False

            if "Month" in monthly_anomalies.columns:

                try:

                    parsed = pd.to_datetime(
                        monthly_anomalies["Month"],
                        errors="coerce",
                    )

                    monthly_anomalies["Period"] = (
                        parsed.dt.to_period("M")
                    )

                    created = True

                except Exception:
                    pass

            if (
                not created
                and "Date" in monthly_anomalies.columns
            ):

                try:

                    parsed = pd.to_datetime(
                        monthly_anomalies["Date"],
                        errors="coerce",
                    )

                    monthly_anomalies["Period"] = (
                        parsed.dt.to_period("M")
                    )

                    created = True

                except Exception:
                    pass

            if (
                not created
                and isinstance(
                    monthly_anomalies.index,
                    pd.PeriodIndex,
                )
            ):

                try:

                    monthly_anomalies["Period"] = (
                        monthly_anomalies.index
                    )

                    created = True

                except Exception:
                    pass

            if (
                not created
                and isinstance(
                    monthly_anomalies.index,
                    pd.DatetimeIndex,
                )
            ):

                try:

                    monthly_anomalies["Period"] = (
                        monthly_anomalies.index
                        .to_period("M")
                    )

                    created = True

                except Exception:
                    pass

        # Normalize Period
        if "Period" in monthly_anomalies.columns:

            try:

                if not isinstance(
                    monthly_anomalies["Period"].dtype,
                    pd.PeriodDtype,
                ):

                    parsed = pd.to_datetime(
                        monthly_anomalies["Period"],
                        errors="coerce",
                    )

                    monthly_anomalies["Period"] = (
                        parsed.dt.to_period("M")
                    )

            except Exception:
                pass

    # ============================================================
    # DIMENSION ANOMALIES
    # ============================================================

    dimension_anomalies = {}

    for dimension in [
        "Product",
        "Product Name",
        "Category",
        "Region",
        "Branch",
        "City",
    ]:

        # Avoid processing both Product and Product Name
        # when both refer to the same business dimension.
        if dimension not in df.columns:
            continue

        try:

            detected = (
                ad.detect_dimension_anomalies(
                    df,
                    dimension,
                )
            )

            if detected is None:
                detected = pd.DataFrame()

            elif not isinstance(
                detected,
                pd.DataFrame,
            ):

                detected = pd.DataFrame(
                    detected
                )

            dimension_anomalies[
                dimension
            ] = detected

        except Exception:

            dimension_anomalies[
                dimension
            ] = pd.DataFrame()

    # ============================================================
    # SUMMARY
    # ============================================================

    try:

        summary = ad.anomaly_alert_summary(
            monthly_anomalies,
            dimension_anomalies,
        )

    except Exception:

        summary = {
            "Critical": 0,
            "Moderate": 0,
            "Watch": 0,
        }

    if not isinstance(
        summary,
        dict,
    ):

        summary = {}

    # ============================================================
    # KPI SUMMARY
    # ============================================================

    kpi_row([
        {
            "label": "Critical",
            "value": str(
                summary.get(
                    "Critical",
                    0,
                )
            ),
        },
        {
            "label": "Moderate",
            "value": str(
                summary.get(
                    "Moderate",
                    0,
                )
            ),
        },
        {
            "label": "Watch",
            "value": str(
                summary.get(
                    "Watch",
                    0,
                )
            ),
        },
    ])

    # ============================================================
    # REVENUE TREND WITH ANOMALIES
    # ============================================================

    if (
        not monthly.empty
        and not monthly_anomalies.empty
        and "Period" in monthly.columns
    ):

        section_title(
            "Revenue Trend with Anomalies"
        )

        try:

            fig = viz.anomaly_scatter(
                monthly,
                monthly_anomalies,
            )

            if fig is not None:

                safe_plot(
                    fig,
                    "Revenue Anomaly Detection",
                )

            else:

                st.info(
                    "No anomaly chart is available for the current data."
                )

        except Exception as exc:

            # ----------------------------------------------------
            # Fallback chart
            # ----------------------------------------------------

            try:

                chart_data = monthly.copy()

                if "Revenue" in chart_data.columns:

                    chart_data["Revenue"] = (
                        pd.to_numeric(
                            chart_data["Revenue"],
                            errors="coerce",
                        )
                    )

                    chart_data = chart_data.dropna(
                        subset=[
                            "Period",
                            "Revenue",
                        ]
                    )

                    if not chart_data.empty:

                        fig = px.line(
                            chart_data,
                            x="Period",
                            y="Revenue",
                            markers=True,
                            title=(
                                "Revenue Trend with Anomalies"
                            ),
                        )

                        fig.update_yaxes(
                            tickprefix="₹",
                            separatethousands=True,
                        )

                        safe_plot(
                            fig,
                            "Revenue Trend with Anomalies",
                        )

                    else:

                        st.info(
                            "There is insufficient valid revenue data "
                            "to display the anomaly trend."
                        )

                else:

                    st.info(
                        "Revenue data is not available "
                        "for the anomaly trend."
                    )

            except Exception as fallback_exc:

                st.warning(
                    "The anomaly trend chart could not be rendered."
                )

                st.caption(
                    f"Technical details: {fallback_exc}"
                )

    elif not monthly.empty:

        section_title(
            "Revenue Trend with Anomalies"
        )

        st.info(
            "Monthly anomaly periods could not be prepared "
            "from the available date information."
        )

    # ============================================================
    # ANOMALY DETAILS
    # ============================================================

    section_title(
        "Anomaly Details"
    )

    tables = []

    # ------------------------------------------------------------
    # Monthly anomalies
    # ------------------------------------------------------------

    if not monthly_anomalies.empty:

        table = monthly_anomalies.copy()

        if "Scope" not in table.columns:

            table.insert(
                0,
                "Scope",
                "Overall Revenue",
            )

        if "Entity" not in table.columns:

            table["Entity"] = (
                "Overall Revenue"
            )

        tables.append(table)

    # ------------------------------------------------------------
    # Dimension anomalies
    # ------------------------------------------------------------

    for dimension, table in (
        dimension_anomalies.items()
    ):

        if (
            table is None
            or table.empty
        ):
            continue

        current = table.copy()

        if "Scope" not in current.columns:

            current.insert(
                0,
                "Scope",
                dimension,
            )

        if "Entity" not in current.columns:

            if dimension in current.columns:

                current = current.rename(
                    columns={
                        dimension: "Entity"
                    }
                )

            else:

                current[
                    "Entity"
                ] = "—"

        tables.append(
            current
        )

    # ============================================================
    # NO ANOMALIES
    # ============================================================

    if not tables:

        st.success(
            "No significant anomalies were detected "
            "across the available revenue and business dimensions."
        )

    else:

        # --------------------------------------------------------
        # Standard table schema
        # --------------------------------------------------------

        combined_columns = [
            "Scope",
            "Entity",
            "Period",
            "Revenue",
            "Expected Value",
            "Percentage Deviation",
            "Severity",
            "Explanation",
        ]

        normalized = []

        for table in tables:

            current = table.copy()

            # Remove duplicate columns
            current = current.loc[
                :,
                ~current.columns.duplicated(),
            ]

            # Scope
            if "Scope" not in current.columns:

                current["Scope"] = "—"

            # Entity
            if "Entity" not in current.columns:

                current["Entity"] = "—"

            # Period
            if "Period" not in current.columns:

                current["Period"] = "—"

            # Remaining columns
            for column in [
                "Revenue",
                "Expected Value",
                "Percentage Deviation",
                "Severity",
                "Explanation",
            ]:

                if column not in current.columns:

                    current[column] = np.nan

            normalized.append(
                current[
                    combined_columns
                ].copy()
            )

        # --------------------------------------------------------
        # Combine
        # --------------------------------------------------------

        try:

            combined = pd.concat(
                normalized,
                ignore_index=True,
            )

        except Exception as exc:

            st.error(
                "Anomaly records could not be combined."
            )

            st.caption(
                f"Technical details: {exc}"
            )

            combined = pd.DataFrame(
                columns=combined_columns
            )

        # ========================================================
        # CLEAN NUMERIC FIELDS
        # ========================================================

        for column in [
            "Revenue",
            "Expected Value",
            "Percentage Deviation",
        ]:

            if column in combined.columns:

                combined[column] = (
                    pd.to_numeric(
                        combined[column],
                        errors="coerce",
                    )
                    .replace(
                        [np.inf, -np.inf],
                        np.nan,
                    )
                )

        # ========================================================
        # CLEAN PERIOD
        # ========================================================

        if "Period" in combined.columns:

            try:

                if isinstance(
                    combined["Period"].dtype,
                    pd.PeriodDtype,
                ):

                    combined["Period"] = (
                        combined["Period"]
                        .astype(str)
                    )

                elif pd.api.types.is_datetime64_any_dtype(
                    combined["Period"]
                ):

                    combined["Period"] = (
                        combined["Period"]
                        .dt.strftime("%b %Y")
                    )

                else:

                    # Safely handle mixed Period / datetime / string
                    def format_period(value):

                        if pd.isna(value):
                            return "—"

                        if isinstance(
                            value,
                            pd.Period,
                        ):
                            return value.strftime(
                                "%b %Y"
                            )

                        try:

                            parsed = pd.to_datetime(
                                value,
                                errors="coerce",
                            )

                            if pd.notna(parsed):
                                return parsed.strftime(
                                    "%b %Y"
                                )

                        except Exception:
                            pass

                        return str(value)

                    combined["Period"] = (
                        combined["Period"]
                        .map(format_period)
                    )

            except Exception:

                combined["Period"] = (
                    combined["Period"]
                    .astype(str)
                    .replace(
                        {
                            "nan": "—",
                            "NaT": "—",
                            "None": "—",
                        }
                    )
                )

        # ========================================================
        # FILTERS
        # ========================================================

        c1, c2 = st.columns(2)

        severity_options = [
            "Critical",
            "Moderate",
            "Watch",
        ]

        if "Severity" in combined.columns:

            available_severities = [
                value
                for value in severity_options
                if value
                in combined[
                    "Severity"
                ]
                .astype(str)
                .unique()
            ]

        else:

            available_severities = []

        with c1:

            severity_filter = st.multiselect(
                "Severity",
                severity_options,
                default=available_severities,
                key="anomaly_severity_filter",
            )

        if "Scope" in combined.columns:

            scope_options = sorted(
                combined[
                    "Scope"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

        else:

            scope_options = []

        with c2:

            scope_filter = st.multiselect(
                "Scope",
                scope_options,
                default=scope_options,
                key="anomaly_scope_filter",
            )

        # ========================================================
        # APPLY FILTERS
        # ========================================================

        view = combined.copy()

        if severity_filter:

            view = view[
                view[
                    "Severity"
                ]
                .astype(str)
                .isin(
                    severity_filter
                )
            ]

        else:

            view = view.iloc[0:0]

        if scope_filter:

            view = view[
                view[
                    "Scope"
                ]
                .astype(str)
                .isin(
                    scope_filter
                )
            ]

        else:

            view = view.iloc[0:0]

        # ========================================================
        # DISPLAY
        # ========================================================

        if view.empty:

            st.info(
                "No anomalies match the selected filters."
            )

        else:

            display = view.copy()

            # Currency formatting
            for column in [
                "Revenue",
                "Expected Value",
            ]:

                if column in display.columns:

                    display[column] = (
                        display[column]
                        .map(
                            lambda value:
                            fmt_currency(value)
                            if pd.notna(value)
                            else "—"
                        )
                    )

            # Percentage formatting
            if (
                "Percentage Deviation"
                in display.columns
            ):

                display[
                    "Percentage Deviation"
                ] = (
                    display[
                        "Percentage Deviation"
                    ]
                    .map(
                        lambda value:
                        fmt_pct(value)
                        if pd.notna(value)
                        else "—"
                    )
                )

            # Safe table rendering
            safe_dataframe(
                display,
                height=min(
                    520,
                    max(
                        260,
                        100 + len(display) * 38,
                    ),
                ),
            )

    # ============================================================
    # UNUSUAL ORDER VALUES
    # ============================================================

    if "Revenue" in df.columns:

        section_title(
            "Unusual Order Values"
        )

        try:

            outliers = (
                ad.detect_iqr_outliers(
                    df,
                    "Revenue",
                )
            )

            if outliers is None:
                outliers = pd.DataFrame()

            elif not isinstance(
                outliers,
                pd.DataFrame,
            ):

                outliers = pd.DataFrame(
                    outliers
                )

        except Exception:

            outliers = pd.DataFrame()

        if (
            outliers is not None
            and not outliers.empty
        ):

            st.caption(
                f"{len(outliers):,} record(s) fall "
                "outside the normal IQR range."
            )

            safe_dataframe(
                outliers,
                height=min(
                    450,
                    max(
                        260,
                        100 + len(outliers) * 38,
                    ),
                ),
            )

        else:

            st.caption(
                "No unusual individual transaction "
                "values were detected."
            )

    # ============================================================
    # RISK INTERPRETATION
    # ============================================================

    section_title(
        "Risk Interpretation"
    )

    try:

        critical_count = int(
            safe_number(
                summary.get(
                    "Critical",
                    0,
                )
            )
        )

    except Exception:

        critical_count = 0

    try:

        moderate_count = int(
            safe_number(
                summary.get(
                    "Moderate",
                    0,
                )
            )
        )

    except Exception:

        moderate_count = 0

    try:

        watch_count = int(
            safe_number(
                summary.get(
                    "Watch",
                    0,
                )
            )
        )

    except Exception:

        watch_count = 0

    total_alerts = (
        critical_count
        + moderate_count
        + watch_count
    )

    # ------------------------------------------------------------
    # Risk message
    # ------------------------------------------------------------

    if critical_count > 0:

        alert_box(
            f"{critical_count} critical anomaly signal(s) "
            "require immediate review of the affected "
            "periods or business dimensions.",
            "critical",
        )

    elif moderate_count > 0:

        alert_box(
            f"{moderate_count} moderate anomaly signal(s) "
            "indicate revenue behaviour that should be reviewed.",
            "moderate",
        )

    elif watch_count > 0:

        alert_box(
            f"{watch_count} watch-level anomaly signal(s) "
            "were identified. Monitor these areas for persistence.",
            "watch",
        )

    else:

        alert_box(
            "No material anomaly signals were identified "
            "in the available historical data.",
            "good",
        )

    st.caption(
        f"Total anomaly signals identified: "
        f"{total_alerts:,}. Signals are statistical indicators "
        "and should be reviewed alongside operational context."
    )

# ============================================================
# BUSINESS INSIGHTS
# ============================================================

def render_business_insights(df):

    page_title(
        "Business Insights",
        "Evidence-based observations explaining the main growth, decline and trend patterns in sales.",
    )

    # --------------------------------------------------------
    # BUILD INSIGHTS
    # --------------------------------------------------------

    try:

        all_insights = (
            ins.build_all_insights(df)
        )

    except Exception as exc:

        st.error(
            "Business insights could not be generated."
        )

        st.caption(
            f"Technical details: {exc}"
        )

        return

    if not isinstance(
        all_insights,
        dict,
    ):

        all_insights = {}

    growth_drivers = all_insights.get(
        "growth_drivers",
        [],
    )

    decline_drivers = all_insights.get(
        "decline_drivers",
        [],
    )

    trend_insights = all_insights.get(
        "trend_insights",
        [],
    )

    if not isinstance(
        growth_drivers,
        list,
    ):
        growth_drivers = []

    if not isinstance(
        decline_drivers,
        list,
    ):
        decline_drivers = []

    if not isinstance(
        trend_insights,
        list,
    ):
        trend_insights = []

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_insights = (
        len(growth_drivers)
        + len(decline_drivers)
        + len(trend_insights)
    )

    kpi_row([
        {
            "label": "Growth Signals",
            "value": (
                f"{len(growth_drivers):,}"
            ),
        },
        {
            "label": "Decline Signals",
            "value": (
                f"{len(decline_drivers):,}"
            ),
        },
        {
            "label": "Trend Signals",
            "value": (
                f"{len(trend_insights):,}"
            ),
        },
        {
            "label": "Total Insights",
            "value": (
                f"{total_insights:,}"
            ),
        },
    ])

    # --------------------------------------------------------
    # ACTIONABLE RECOMMENDATIONS
    # --------------------------------------------------------

    section_title(
        "Actionable Recommendations"
    )

    recommendations = []

    for item in decline_drivers:

        if not isinstance(
            item,
            dict,
        ):
            continue

        observation = safe_text(
            item.get(
                "observation"
            ),
            "Review declining sales activity",
        )

        evidence = safe_text(
            item.get(
                "supporting_data"
            ),
            "Historical sales indicate a negative trend.",
        )

        implication = safe_text(
            item.get(
                "implication"
            ),
            "",
        )

        recommendation = (
            implication
            if implication != "—"
            else observation
        )

        recommendations.append({
            "Recommendation": recommendation,
            "Supporting Evidence": evidence,
            "Priority": "High",
        })

    for item in growth_drivers:

        if not isinstance(
            item,
            dict,
        ):
            continue

        observation = safe_text(
            item.get(
                "observation"
            ),
            "Strengthen the identified growth driver",
        )

        evidence = safe_text(
            item.get(
                "supporting_data"
            ),
            "Historical sales indicate positive performance.",
        )

        implication = safe_text(
            item.get(
                "implication"
            ),
            "",
        )

        recommendation = (
            implication
            if implication != "—"
            else observation
        )

        recommendations.append({
            "Recommendation": recommendation,
            "Supporting Evidence": evidence,
            "Priority": "Medium",
        })

    for item in trend_insights:

        if not isinstance(
            item,
            dict,
        ):
            continue

        observation = safe_text(
            item.get(
                "observation"
            ),
            "Monitor the identified sales trend",
        )

        evidence = safe_text(
            item.get(
                "supporting_data"
            ),
            "Historical sales show a measurable trend.",
        )

        implication = safe_text(
            item.get(
                "implication"
            ),
            "",
        )

        recommendation = (
            implication
            if implication != "—"
            else observation
        )

        recommendations.append({
            "Recommendation": recommendation,
            "Supporting Evidence": evidence,
            "Priority": "Medium",
        })

    if recommendations:

        recommendation_df = pd.DataFrame(
            recommendations
        )

        priority_order = {
            "High": 0,
            "Medium": 1,
            "Low": 2,
        }

        recommendation_df["_sort"] = (
            recommendation_df[
                "Priority"
            ]
            .map(
                priority_order
            )
            .fillna(3)
        )

        recommendation_df = (
            recommendation_df
            .sort_values(
                "_sort"
            )
            .drop(
                columns="_sort"
            )
            .reset_index(
                drop=True
            )
        )

        safe_dataframe(
            recommendation_df,
            height=min(
                500,
                100 + len(
                    recommendation_df
                ) * 55,
            ),
        )

    else:

        st.info(
            "No actionable recommendations could be "
            "established from the available sales data."
        )

    # --------------------------------------------------------
    # DETAIL
    # --------------------------------------------------------

    section_title(
        "Insight Detail"
    )

    if decline_drivers:

        st.markdown(
            "#### Decline Drivers"
        )

        for item in decline_drivers:

            if not isinstance(
                item,
                dict,
            ):
                continue

            observation = safe_text(
                item.get(
                    "observation"
                ),
                "Declining sales signal",
            )

            evidence = safe_text(
                item.get(
                    "supporting_data"
                ),
                "",
            )

            implication = safe_text(
                item.get(
                    "implication"
                ),
                "",
            )

            with st.container(
                border=True
            ):

                st.write(
                    observation
                )

                if evidence != "—":
                    st.caption(
                        evidence
                    )

                if implication != "—":
                    st.warning(
                        implication
                    )

    if growth_drivers:

        st.markdown(
            "#### Growth Drivers"
        )

        for item in growth_drivers:

            if not isinstance(
                item,
                dict,
            ):
                continue

            observation = safe_text(
                item.get(
                    "observation"
                ),
                "Positive growth signal",
            )

            evidence = safe_text(
                item.get(
                    "supporting_data"
                ),
                "",
            )

            implication = safe_text(
                item.get(
                    "implication"
                ),
                "",
            )

            with st.container(
                border=True
            ):

                st.write(
                    observation
                )

                if evidence != "—":
                    st.caption(
                        evidence
                    )

                if implication != "—":
                    st.info(
                        implication
                    )

    if trend_insights:

        st.markdown(
            "#### Trend Insights"
        )

        for item in trend_insights:

            if not isinstance(
                item,
                dict,
            ):
                continue

            observation = safe_text(
                item.get(
                    "observation"
                ),
                "Notable sales trend",
            )

            evidence = safe_text(
                item.get(
                    "supporting_data"
                ),
                "",
            )

            implication = safe_text(
                item.get(
                    "implication"
                ),
                "",
            )

            with st.container(
                border=True
            ):

                st.write(
                    observation
                )

                if evidence != "—":
                    st.caption(
                        evidence
                    )

                if implication != "—":
                    st.info(
                        implication
                    )

    # --------------------------------------------------------
    # MANAGEMENT FOCUS
    # --------------------------------------------------------

    section_title(
        "Management Focus"
    )

    if decline_drivers:

        alert_box(
            f"{len(decline_drivers)} decline signal(s) "
            "have been identified. Review the affected "
            "products, categories, branches or regions "
            "before making planning decisions.",
            "critical",
        )

    elif growth_drivers:

        alert_box(
            f"{len(growth_drivers)} positive growth signal(s) "
            "were identified. These areas can be monitored "
            "for continued contribution to overall sales.",
            "good",
        )

    else:

        alert_box(
            "No material management signals were identified "
            "from the current dataset.",
            "watch",
        )

    st.caption(
        "Recommendations are generated from measurable "
        "historical sales patterns and should be evaluated "
        "alongside operational and market context."
    )
# ============================================================
# DATA QUALITY
# ============================================================

def render_data_quality(df):

    page_title(
        "Data Quality",
        "Assess completeness, validity, consistency and overall dataset reliability.",
    )

    if df is None or df.empty:

        st.info(
            "No dataset is available for quality assessment."
        )

        return

    # --------------------------------------------------------
    # BASIC METRICS
    # --------------------------------------------------------

    total_rows = len(df)
    total_columns = len(df.columns)

    missing_cells = int(
        df.isna()
        .sum()
        .sum()
    )

    total_cells = (
        total_rows
        * total_columns
    )

    fallback_completeness = (
        (
            (
                total_cells
                - missing_cells
            )
            / total_cells
        )
        * 100
        if total_cells > 0
        else 0
    )

    duplicate_rows = int(
        df.duplicated().sum()
    )

    # --------------------------------------------------------
    # VALIDATOR-BASED QUALITY REPORT (data_validator.py)
    # --------------------------------------------------------

    quality_report = st.session_state.get(
        "quality_report"
    )

    if not isinstance(quality_report, dict):
        quality_report = {}

    completeness_pct = safe_number(
        quality_report.get("completeness_pct"),
        fallback_completeness,
    )

    error_rate_pct = safe_number(
        quality_report.get("error_rate_pct"),
        0.0,
    )

    validity_pct = max(
        0.0,
        100.0 - error_rate_pct,
    )

    duplicate_records = int(
        safe_number(
            quality_report.get("duplicate_records"),
            duplicate_rows,
        )
    )

    consistency_pct = (
        max(
            0.0,
            100.0
            - (
                (duplicate_records / total_rows) * 100
                if total_rows > 0
                else 0
            ),
        )
    )

    invalid_dates = int(
        safe_number(quality_report.get("invalid_dates"), 0)
    )

    invalid_numeric_values = int(
        safe_number(quality_report.get("invalid_numeric_values"), 0)
    )

    uniqueness_pct = (
        max(
            0.0,
            100.0
            - (
                ((invalid_dates + invalid_numeric_values) / total_rows) * 100
                if total_rows > 0
                else 0
            ),
        )
    )

    reliability_status = safe_text(
        quality_report.get("reliability_status"),
        "Not Assessed",
    )

    # --------------------------------------------------------
    # OUTLIER HEALTH (anomaly_detection.py)
    # --------------------------------------------------------

    outlier_ratio = 0.0

    revenue_col = find_column(
        df,
        ["Revenue", "Sales", "Revenue Amount", "Sales Amount"],
    )

    if revenue_col:

        try:

            outliers_df = ad.detect_iqr_outliers(
                df,
                revenue_col,
            )

            if (
                outliers_df is not None
                and not outliers_df.empty
                and total_rows > 0
            ):

                outlier_ratio = (
                    len(outliers_df) / total_rows
                )

        except Exception:
            outliers_df = pd.DataFrame()

    else:
        outliers_df = pd.DataFrame()

    outlier_health_pct = max(
        0.0,
        100.0 - (outlier_ratio * 100),
    )

    # --------------------------------------------------------
    # FORECAST READINESS (data_validator.py)
    # --------------------------------------------------------

    try:

        forecast_ready, forecast_message = (
            data_validator.sufficient_for_forecasting(
                df
            )
        )

    except Exception:

        forecast_ready = False
        forecast_message = (
            "Forecast readiness could not be assessed."
        )

    # --------------------------------------------------------
    # QUALITY SCORE (weighted composite)
    # --------------------------------------------------------

    quality_score = (
        (completeness_pct * 0.30)
        + (validity_pct * 0.25)
        + (consistency_pct * 0.20)
        + (uniqueness_pct * 0.15)
        + (outlier_health_pct * 0.10)
    )

    usability_pct = (
        quality_score
        if forecast_ready
        else quality_score * 0.85
    )

    # --------------------------------------------------------
    # KPI ROW
    # --------------------------------------------------------

    kpi_row([
        {
            "label": "Quality Score",
            "value": f"{quality_score:.1f}%",
        },
        {
            "label": "Completeness",
            "value": f"{completeness_pct:.1f}%",
        },
        {
            "label": "Validity",
            "value": f"{validity_pct:.1f}%",
        },
        {
            "label": "Consistency",
            "value": f"{consistency_pct:.1f}%",
        },
        {
            "label": "Reliability",
            "value": reliability_status,
        },
    ])

    kpi_row([
        {
            "label": "Uniqueness",
            "value": f"{uniqueness_pct:.1f}%",
        },
        {
            "label": "Outlier Health",
            "value": f"{outlier_health_pct:.1f}%",
        },
        {
            "label": "Usability",
            "value": f"{usability_pct:.1f}%",
        },
        {
            "label": "Forecast Readiness",
            "value": "Ready" if forecast_ready else "Not Ready",
        },
        {
            "label": "Duplicate Rows",
            "value": f"{duplicate_rows:,}",
        },
    ])

    if not forecast_ready:

        alert_box(
            forecast_message,
            "watch",
        )

    # --------------------------------------------------------
    # QUALITY RADAR + GAUGE
    # --------------------------------------------------------

    section_title(
        "Quality Dimensions"
    )

    chart_c1, chart_c2 = st.columns(2)

    with chart_c1:

        try:

            radar_categories = [
                "Completeness",
                "Validity",
                "Consistency",
                "Uniqueness",
                "Outlier Health",
            ]

            radar_values = [
                completeness_pct,
                validity_pct,
                consistency_pct,
                uniqueness_pct,
                outlier_health_pct,
            ]

            fig = go.Figure()

            fig.add_trace(
                go.Scatterpolar(
                    r=radar_values + [radar_values[0]],
                    theta=radar_categories + [radar_categories[0]],
                    fill="toself",
                    name="Quality",
                )
            )

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                    )
                ),
                showlegend=False,
            )

            safe_plot(
                fig,
                "Data Quality Radar",
            )

        except Exception as exc:

            st.warning(
                "Quality radar chart is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    with chart_c2:

        try:

            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=quality_score,
                    title={"text": "Overall Quality Score"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "steps": [
                            {"range": [0, 60], "color": "rgba(248,113,113,0.38)"},
                            {"range": [60, 85], "color": "rgba(251,191,36,0.34)"},
                            {"range": [85, 100], "color": "rgba(52,211,153,0.34)"},
                        ],
                    },
                )
            )

            safe_plot(
                fig,
                "Overall Quality Score",
            )

        except Exception as exc:

            st.warning(
                "Quality gauge is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    # --------------------------------------------------------
    # COLUMN QUALITY TABLE
    # --------------------------------------------------------

    section_title(
        "Column Quality"
    )

    quality_rows = []

    for column in df.columns:

        missing = int(
            df[column]
            .isna()
            .sum()
        )

        missing_pct = (
            (
                missing
                / total_rows
            )
            * 100
            if total_rows > 0
            else 0
        )

        unique = int(
            df[column]
            .nunique(
                dropna=True
            )
        )

        quality_rows.append({
            "Column": str(column),
            "Data Type": str(
                df[column].dtype
            ),
            "Missing Values": missing,
            "Missing %": missing_pct,
            "Unique Values": unique,
        })

    quality_table = pd.DataFrame(
        quality_rows
    )

    if not quality_table.empty:

        chart_c3, chart_c4 = st.columns(2)

        with chart_c3:

            try:

                missing_chart_data = quality_table[
                    quality_table["Missing Values"] > 0
                ].sort_values(
                    "Missing Values",
                    ascending=False,
                )

                if not missing_chart_data.empty:

                    fig = px.bar(
                        missing_chart_data,
                        x="Column",
                        y="Missing Values",
                        title="Missing Values by Column",
                    )

                    safe_plot(
                        fig,
                        "Missing Values by Column",
                    )

                else:

                    st.info(
                        "No missing values were detected "
                        "in any column."
                    )

            except Exception as exc:

                st.warning(
                    "Missing values chart is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

        with chart_c4:

            try:

                dtype_counts = (
                    df.dtypes
                    .astype(str)
                    .value_counts()
                    .reset_index()
                )

                dtype_counts.columns = [
                    "Data Type",
                    "Column Count",
                ]

                fig = px.pie(
                    dtype_counts,
                    names="Data Type",
                    values="Column Count",
                    title="Data Type Distribution",
                )

                safe_plot(
                    fig,
                    "Data Type Distribution",
                )

            except Exception as exc:

                st.warning(
                    "Data type distribution chart is unavailable."
                )

                st.caption(
                    f"Technical details: {exc}"
                )

        display_table = quality_table.copy()

        display_table[
            "Missing %"
        ] = (
            display_table[
                "Missing %"
            ]
            .map(
                lambda value:
                f"{value:.1f}%"
            )
        )

        safe_dataframe(
            display_table
        )

    else:

        st.info(
            "No column-level quality data is available."
        )

    # --------------------------------------------------------
    # OUTLIER VISUALIZATION
    # --------------------------------------------------------

    section_title(
        "Outlier Detection"
    )

    if (
        outliers_df is not None
        and not outliers_df.empty
    ):

        st.caption(
            f"{len(outliers_df):,} record(s) fall outside "
            f"the normal IQR range for {revenue_col}."
        )

        try:

            fig = px.box(
                df,
                y=revenue_col,
                points="outliers",
                title=f"{revenue_col} Distribution & Outliers",
            )

            safe_plot(
                fig,
                f"{revenue_col} Distribution & Outliers",
            )

        except Exception as exc:

            st.warning(
                "Outlier visualization is unavailable."
            )

            st.caption(
                f"Technical details: {exc}"
            )

    else:

        st.info(
            "No significant outliers were detected, "
            "or no revenue column is available."
        )

    # --------------------------------------------------------
    # CLEANING SUMMARY (data_cleaner.py)
    # --------------------------------------------------------

    section_title(
        "Cleaning Summary"
    )

    report = (
        st.session_state.get(
            "cleaning_report"
        )
    )

    if isinstance(
        report,
        dict,
    ):

        cleaning_summary_rows = [
            {"Metric": "Rows Processed", "Value": safe_number(report.get("rows_processed"), 0)},
            {"Metric": "Rows Removed", "Value": safe_number(report.get("rows_removed"), 0)},
            {"Metric": "Rows Repaired", "Value": safe_number(report.get("rows_repaired"), 0)},
            {"Metric": "Missing Values Handled", "Value": safe_number(report.get("missing_values_handled"), 0)},
            {"Metric": "Duplicates Handled", "Value": safe_number(report.get("duplicates_handled"), 0)},
            {"Metric": "Invalid Records Flagged", "Value": safe_number(report.get("invalid_records_flagged"), 0)},
            {"Metric": "Final Row Count", "Value": safe_number(report.get("final_row_count"), total_rows)},
        ]

        cleaning_summary_table = pd.DataFrame(
            cleaning_summary_rows
        )

        cleaning_summary_table["Value"] = (
            cleaning_summary_table["Value"]
            .map(lambda value: f"{value:,.0f}")
        )

        safe_dataframe(
            cleaning_summary_table
        )

        notes = report.get(
            "notes",
            [],
        )

        if notes:

            with st.expander(
                "Cleaning Notes"
            ):

                for note in notes:
                    st.write(
                        str(note)
                    )

    else:

        st.info(
            "No cleaning report is available for this dataset."
        )

    # --------------------------------------------------------
    # DATA PREVIEW
    # --------------------------------------------------------

    section_title(
        "Data Preview"
    )

    safe_dataframe(
        df.head(20)
    )

    # --------------------------------------------------------
    # RELIABILITY
    # --------------------------------------------------------

    section_title(
        "Reliability Assessment"
    )

    if (
        completeness_pct >= 95
        and duplicate_rows == 0
    ):

        alert_box(
            "The dataset has high structural completeness "
            "and no duplicate rows were detected.",
            "good",
        )

    elif completeness_pct >= 85:

        alert_box(
            "The dataset is broadly usable, but some missing "
            "values or structural issues should be reviewed.",
            "watch",
        )

    else:

        alert_box(
            "The dataset contains substantial missing or "
            "structural issues that may affect analysis.",
            "moderate",
        )

    st.caption(
        "Data quality indicators describe the current dataset "
        "after INAIBA's cleaning process."
    )


# ============================================================
# REPORTS & DATA
# ============================================================

# ============================================================
# REPORTS & DATA
# ============================================================

def render_reports_downloads(df):

    page_title(
        "Reports & Downloads",
        "Export cleaned data, forecasts, anomaly results and management reports.",
    )

    if df is None:

        st.info(
            "No dataset is available for reporting."
        )

        return

    # --------------------------------------------------------
    # MONTHLY
    # --------------------------------------------------------

    try:
        monthly = an.monthly_revenue(df)
    except Exception:
        monthly = pd.DataFrame()

    # --------------------------------------------------------
    # PERFORMANCE TABLES
    # --------------------------------------------------------

    performance_tables = {}

    for dimension in [
        "Product",
        "Category",
        "Region",
        "Branch",
        "City",
    ]:

        if dimension not in df.columns:
            continue

        try:

            performance = (
                an.performance_by(
                    df,
                    dimension,
                )
            )

            if (
                performance is not None
                and not performance.empty
            ):

                performance_tables[
                    dimension
                ] = performance

        except Exception:
            continue

    # --------------------------------------------------------
    # ANOMALIES
    # --------------------------------------------------------

    try:

        monthly_anomalies = (
            ad.detect_monthly_anomalies(
                monthly
            )
        )

        if monthly_anomalies is None:
            monthly_anomalies = pd.DataFrame()

    except Exception:

        monthly_anomalies = pd.DataFrame()

    # --------------------------------------------------------
    # FORECAST
    # --------------------------------------------------------

    forecast_table = None

    try:

        sufficient, _ = (
            data_validator.sufficient_for_forecasting(
                df
            )
        )

    except Exception:

        sufficient = False

    if (
        sufficient
        and not monthly.empty
        and len(monthly) >= 2
    ):

        try:

            forecast_result = (
                fc.generate_forecast(
                    monthly,
                    horizon=3,
                )
            )

            if (
                isinstance(
                    forecast_result,
                    dict,
                )
                and forecast_result.get(
                    "sufficient_data"
                )
            ):

                forecast_table = (
                    forecast_result.get(
                        "forecast_table"
                    )
                )

        except Exception:

            forecast_table = None

    # --------------------------------------------------------
    # REPORT AVAILABILITY
    # --------------------------------------------------------

    section_title(
        "Report Availability"
    )

    available_reports = [
        {
            "label": "Cleaned Dataset",
            "available": (
                df is not None
                and not df.empty
            ),
        },
        {
            "label": "Sales Performance",
            "available": (
                not monthly.empty
            ),
        },
        {
            "label": "Forecast",
            "available": (
                isinstance(
                    forecast_table,
                    pd.DataFrame,
                )
                and not forecast_table.empty
            ),
        },
        {
            "label": "Anomaly Analysis",
            "available": (
                not monthly_anomalies.empty
            ),
        },
        {
            "label": "Management Excel",
            "available": True,
        },
    ]

    available_count = sum(
        item["available"]
        for item in available_reports
    )

    kpi_row([
        {
            "label": "Available Reports",
            "value": (
                f"{available_count}/"
                f"{len(available_reports)}"
            ),
        },
        {
            "label": "Data Rows",
            "value": (
                f"{len(df):,}"
            ),
        },
        {
            "label": "Data Columns",
            "value": (
                f"{len(df.columns):,}"
            ),
        },
        {
            "label": "Forecast Status",
            "value": (
                "Available"
                if (
                    isinstance(
                        forecast_table,
                        pd.DataFrame,
                    )
                    and not forecast_table.empty
                )
                else "Unavailable"
            ),
        },
    ])

    # --------------------------------------------------------
    # DOWNLOAD CENTER
    # --------------------------------------------------------

    section_title(
        "Download Center"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        try:

            csv_data = (
                rpt.df_to_csv_bytes(
                    df
                )
            )

            st.download_button(
                "Cleaned Dataset",
                data=csv_data,
                file_name=(
                    "inaiba_cleaned_data.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )

        except Exception:

            st.button(
                "Cleaned Dataset Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with c2:

        raw_df = st.session_state.get("raw_df")

        if (
            isinstance(raw_df, pd.DataFrame)
            and not raw_df.empty
        ):

            try:

                st.download_button(
                    "Original Dataset",
                    data=(
                        rpt.df_to_csv_bytes(
                            raw_df
                        )
                    ),
                    file_name=(
                        "inaiba_original_data.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Original Dataset Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "Original Dataset Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with c3:

        if (
            isinstance(
                forecast_table,
                pd.DataFrame,
            )
            and not forecast_table.empty
        ):

            try:

                st.download_button(
                    "Forecast Dataset",
                    data=(
                        rpt.df_to_csv_bytes(
                            forecast_table
                        )
                    ),
                    file_name=(
                        "inaiba_forecast.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Forecast Download Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "Forecast Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with c4:

        if not monthly_anomalies.empty:

            try:

                st.download_button(
                    "Anomaly Report",
                    data=(
                        rpt.df_to_csv_bytes(
                            monthly_anomalies
                        )
                    ),
                    file_name=(
                        "inaiba_anomalies.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Anomaly Download Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "No Anomalies Available",
                disabled=True,
                use_container_width=True,
            )

    # --------------------------------------------------------
    # ADDITIONAL REPORTS
    # --------------------------------------------------------

    c5, c6, c7 = st.columns(3)

    with c5:

        if not monthly.empty:

            try:

                st.download_button(
                    "Sales Performance Report",
                    data=(
                        rpt.df_to_csv_bytes(
                            monthly
                        )
                    ),
                    file_name=(
                        "inaiba_sales_performance.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Performance Download Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "Performance Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with c6:

        if performance_tables:

            preferred_dimension = None

            for dimension in [
                "Product",
                "Category",
                "Branch",
                "Region",
                "City",
            ]:

                if dimension in performance_tables:

                    preferred_dimension = (
                        dimension
                    )

                    break

            if preferred_dimension is None:

                preferred_dimension = list(
                    performance_tables.keys()
                )[0]

            try:

                st.download_button(
                    (
                        "Performance Report — "
                        f"{preferred_dimension}"
                    ),
                    data=(
                        rpt.df_to_csv_bytes(
                            performance_tables[
                                preferred_dimension
                            ]
                        )
                    ),
                    file_name=(
                        "inaiba_product_market_report.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Performance Download Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "Performance Report Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with c7:

        quality_report_data = st.session_state.get(
            "quality_report"
        )

        if isinstance(quality_report_data, dict) and quality_report_data:

            try:

                quality_report_table = pd.DataFrame(
                    [
                        {"Metric": str(key), "Value": str(value)}
                        for key, value in quality_report_data.items()
                    ]
                )

                st.download_button(
                    "Data Quality Report",
                    data=(
                        rpt.df_to_csv_bytes(
                            quality_report_table
                        )
                    ),
                    file_name=(
                        "inaiba_data_quality_report.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception:

                st.button(
                    "Data Quality Report Unavailable",
                    disabled=True,
                    use_container_width=True,
                )

        else:

            st.button(
                "Data Quality Report Unavailable",
                disabled=True,
                use_container_width=True,
            )

    # --------------------------------------------------------
    # MANAGEMENT EXCEL
    # --------------------------------------------------------

    section_title(
        "Management Report"
    )

    try:

        excel_bytes = (
            rpt.build_management_excel_report(
                df,
                monthly,
                performance_tables,
                forecast_table,
                monthly_anomalies,
                st.session_state.get(
                    "quality_report",
                    {},
                ),
            )
        )

    except Exception as exc:

        excel_bytes = None

        st.warning(
            "The full Excel management report "
            "could not be generated."
        )

        st.caption(
            f"Technical details: {exc}"
        )

    if excel_bytes:

        st.download_button(
            "Download Full Management Report (Excel)",
            data=excel_bytes,
            file_name=(
                "inaiba_management_report.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=False,
        )

        st.caption(
            "The management workbook combines sales performance, "
            "business dimensions, forecasting, anomaly analysis "
            "and data-quality information."
        )

    else:

        st.caption(
            "Excel management report is currently unavailable."
        )

    # ========================================================
    # DATA PREVIEW
    # IMPORTANT: INSIDE THIS FUNCTION
    # ========================================================

    section_title(
        "Data Preview"
    )

    if df is None or df.empty:

        st.info(
            "No dataset is available for preview."
        )

    else:

        preview_rows = min(
            len(df),
            200,
        )

        st.caption(
            f"Showing the first {preview_rows:,} records "
            f"of {len(df):,} total rows."
        )

        try:

            preview = df.head(
                200
            ).copy()

            safe_dataframe(
                preview,
                height=450,
            )

        except Exception as exc:

            st.error(
                "The data preview could not be rendered."
            )

            st.caption(
                f"Technical details: {exc}"
            )


# ============================================================
# PAGE ROUTER
# ============================================================

PAGE_FUNCTIONS = {

    "Executive Overview":
        render_executive_overview,

    "Sales Performance":
        render_sales_performance,

    "Products & Categories":
        render_products_categories,

    "Regions / Branches":
        render_regions_branches,

    "Forecasting":
        render_forecasting,

    "Forecast Evaluation":
        render_forecast_evaluation,

    "Anomalies & Risks":
        render_anomalies_risks,

    "Business Insights":
        render_business_insights,

    "Data Quality":
        render_data_quality,

    "Reports & Downloads":
        render_reports_downloads,
}


# ============================================================
# RUN APPLICATION
# ============================================================

try:

    current_page = PAGE_FUNCTIONS.get(
        st.session_state.nav
    )

    if current_page is None:

        st.session_state.nav = (
            "Executive Overview"
        )

        current_page = (
           render_executive_overview
        )

    current_page(
        filtered_df
    )

except Exception as error:

    st.error(
        "This page could not be rendered due to "
        "an unexpected issue with the current dataset or filters."
    )

    with st.expander(
        "Technical Details"
    ):

        st.exception(error)