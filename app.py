import io
import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


EXPECTED_CATEGORY_COL = "Product Category"
IGNORED_COLS = {"weighted incidence", "weighted incidence rate", "not answer", "not answered", "not defined"}

MILEAGE_BINS = [
    "Under 5,000",
    "5,000 To 9,999",
    "10,000 To 14,999",
    "15,000 To 19,999",
    "20,000 To 24,999",
    "25,000 To 29,999",
    "30,000 To 34,999",
    "35,000 To 39,999",
    "40,000 To 44,999",
    "45,000 To 49,999",
    "50,000 To 59,999",
    "60,000 To 69,999",
    "70,000 To 79,999",
    "80,000 To 89,999",
    "90,000 To 99,999",
    "100,000 To 124,999",
    "125,000 To 149,999",
    "150,000 To 174,999",
    "175,000 To 199,999",
    "200,000 To 249,999",
    "250,000 To 299,999",
    "300,000 And Over",
]


def normalize_col(col: str) -> str:
    """Normalize column names for more forgiving matching."""
    return re.sub(r"\s+", " ", str(col).strip())


def lower_norm(col: str) -> str:
    return normalize_col(col).lower()


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Read CSV or Excel upload."""
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file type. Upload a CSV, XLSX, or XLS file.")


def clean_incidence_value(value):
    """Convert incidence inputs to decimals. Supports 0.04, 4, and '4%'."""
    if pd.isna(value):
        return np.nan

    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if value == "":
            return np.nan
        is_percent = value.endswith("%")
        value = value.replace("%", "")
        try:
            num = float(value)
        except ValueError:
            return np.nan
        return num / 100 if is_percent else num

    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and map case-insensitive mileage bin names to expected names."""
    df = df.copy()
    df.columns = [normalize_col(c) for c in df.columns]

    col_map: Dict[str, str] = {}
    normalized_to_actual = {lower_norm(c): c for c in df.columns}

    for bin_name in MILEAGE_BINS:
        key = lower_norm(bin_name)
        if key in normalized_to_actual:
            col_map[normalized_to_actual[key]] = bin_name

    # Product Category forgiving match
    for c in df.columns:
        if lower_norm(c) == lower_norm(EXPECTED_CATEGORY_COL):
            col_map[c] = EXPECTED_CATEGORY_COL

    return df.rename(columns=col_map)


def detect_incidence_scale(df: pd.DataFrame, mileage_cols: List[str]) -> Tuple[pd.DataFrame, str]:
    """
    Convert incidence values to rates.
    If most non-null values are > 1, assume whole-percent values such as 4 = 4%.
    """
    df = df.copy()
    for col in mileage_cols:
        df[col] = df[col].apply(clean_incidence_value)

    stacked = df[mileage_cols].stack().dropna()

    if stacked.empty:
        return df, "No numeric incidence values detected."

    pct_over_one = (stacked > 1).mean()

    if pct_over_one > 0.5:
        df[mileage_cols] = df[mileage_cols] / 100
        return df, "Detected whole-number percentages. Converted values like 4 to 4%."

    return df, "Detected decimal or percent-formatted incidence rates."


def validate_input(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    errors = []
    warnings = []

    if EXPECTED_CATEGORY_COL not in df.columns:
        errors.append(f"Missing required column: '{EXPECTED_CATEGORY_COL}'.")

    available_mileage_cols = [c for c in MILEAGE_BINS if c in df.columns]
    missing_mileage_cols = [c for c in MILEAGE_BINS if c not in df.columns]

    if not available_mileage_cols:
        errors.append("No mileage-bin incidence columns were found.")

    if missing_mileage_cols:
        warnings.append(
            "Some expected mileage-bin columns are missing. The app will plot the available bins only: "
            + ", ".join(missing_mileage_cols)
        )

    return errors, warnings


def mileage_bin_x_values(mileage_cols: List[str]) -> List[int]:
    """Use the upper bound of each mileage bin as the x-axis point."""
    x_values = []
    fallback = 0

    for col in mileage_cols:
        numbers = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", col)]

        if "under" in col.lower() and numbers:
            x_values.append(numbers[0])
        elif "and over" in col.lower() and numbers:
            x_values.append(numbers[0])
        elif len(numbers) >= 2:
            x_values.append(numbers[-1])
        elif numbers:
            x_values.append(numbers[0])
        else:
            fallback += 1
            x_values.append(fallback)

    return x_values


def build_survival_curves(df: pd.DataFrame, mileage_cols: List[str]) -> pd.DataFrame:
    """
    Convert interval incidence into survival curves.

    Assumption:
    Each mileage-bin value is the conditional incidence rate for that interval.
    Survival after each bin = prior survival * (1 - interval incidence).
    """
    records = []
    x_values = mileage_bin_x_values(mileage_cols)

    for _, row in df.iterrows():
        category = row[EXPECTED_CATEGORY_COL]
        survival = 1.0

        records.append(
            {
                "Product Category": category,
                "Mileage": 0,
                "Mileage Bin": "0",
                "Survival Rate": 1.0,
                "Failure Rate": 0.0,
            }
        )

        for col, x in zip(mileage_cols, x_values):
            incidence = row[col]
            if pd.isna(incidence):
                incidence = 0

            incidence = max(0, min(float(incidence), 1))
            survival *= 1 - incidence

            records.append(
                {
                    "Product Category": category,
                    "Mileage": x,
                    "Mileage Bin": col,
                    "Survival Rate": survival,
                    "Failure Rate": 1 - survival,
                }
            )

    return pd.DataFrame(records)


def plot_survival_curves(curves_df: pd.DataFrame, selected_categories: List[str]) -> go.Figure:
    fig = go.Figure()

    filtered = curves_df[curves_df["Product Category"].isin(selected_categories)]

    for category, grp in filtered.groupby("Product Category", sort=False):
        fig.add_trace(
            go.Scatter(
                x=grp["Mileage"],
                y=grp["Survival Rate"],
                mode="lines+markers",
                name=str(category),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Mileage: %{x:,}<br>"
                    "Survival: %{y:.1%}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Survival Curves by Product Category",
        xaxis_title="Mileage",
        yaxis_title="Estimated Survival Rate",
        yaxis=dict(tickformat=".0%", range=[0, 1.02]),
        hovermode="x unified",
        legend_title="Product Category",
        height=650,
        margin=dict(l=20, r=20, t=70, b=20),
    )

    return fig


def main():
    st.set_page_config(page_title="Part Category Survival Curves", layout="wide")

    st.title("Part Category Survival Curve App")
    st.caption(
        "Upload an incidence-rate file and compare estimated survival curves across part categories."
    )

    with st.expander("Expected file structure", expanded=False):
        st.write(
            "The file should include `Product Category` plus mileage-bin incidence columns. "
            "`weighted Incidence`, `Not Answer`, and undefined/non-mileage columns are ignored."
        )
        st.code(
            "Product Category, weighted Incidence, Not Answer, Under 5,000, 5,000 To 9,999, ...",
            language="text",
        )

    uploaded_file = st.file_uploader(
        "Upload incidence-rate file",
        type=["csv", "xlsx", "xls"],
        help="CSV or Excel file with one row per product category.",
    )

    if not uploaded_file:
        st.info("Upload a file to begin.")
        return

    try:
        raw_df = read_uploaded_file(uploaded_file)
    except Exception as exc:
        st.error(str(exc))
        return

    df = standardize_columns(raw_df)
    errors, warnings = validate_input(df)

    for warning in warnings:
        st.warning(warning)

    if errors:
        for error in errors:
            st.error(error)
        st.stop()

    mileage_cols = [c for c in MILEAGE_BINS if c in df.columns]

    # Explicitly ignore weighted incidence, not answer, and non-mileage columns.
    keep_cols = [EXPECTED_CATEGORY_COL] + mileage_cols
    df = df[keep_cols].copy()

    df[EXPECTED_CATEGORY_COL] = df[EXPECTED_CATEGORY_COL].astype(str).str.strip()
    df = df[df[EXPECTED_CATEGORY_COL].ne("") & df[EXPECTED_CATEGORY_COL].ne("nan")]

    df, scale_message = detect_incidence_scale(df, mileage_cols)
    st.caption(scale_message)

    categories = sorted(df[EXPECTED_CATEGORY_COL].dropna().unique().tolist())

    if not categories:
        st.error("No product categories found after cleaning.")
        st.stop()

    with st.sidebar:
        st.header("Filters")
        default_count = min(8, len(categories))
        selected_categories = st.multiselect(
            "Product categories",
            categories,
            default=categories[:default_count],
        )

        show_failure = st.toggle("Show cumulative failure chart", value=False)
        show_data = st.toggle("Show cleaned data", value=False)

    if not selected_categories:
        st.warning("Select at least one product category.")
        return

    curves_df = build_survival_curves(df, mileage_cols)

    fig = plot_survival_curves(curves_df, selected_categories)
    st.plotly_chart(fig, use_container_width=True)

    if show_failure:
        failure_fig = go.Figure()

        filtered = curves_df[curves_df["Product Category"].isin(selected_categories)]
        for category, grp in filtered.groupby("Product Category", sort=False):
            failure_fig.add_trace(
                go.Scatter(
                    x=grp["Mileage"],
                    y=grp["Failure Rate"],
                    mode="lines+markers",
                    name=str(category),
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "Mileage: %{x:,}<br>"
                        "Cumulative failure: %{y:.1%}<extra></extra>"
                    ),
                )
            )

        failure_fig.update_layout(
            title="Cumulative Failure Curves by Product Category",
            xaxis_title="Mileage",
            yaxis_title="Estimated Cumulative Failure Rate",
            yaxis=dict(tickformat=".0%", range=[0, 1.02]),
            hovermode="x unified",
            legend_title="Product Category",
            height=650,
            margin=dict(l=20, r=20, t=70, b=20),
        )
        st.plotly_chart(failure_fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    selected_curve_data = curves_df[curves_df["Product Category"].isin(selected_categories)]
    c1.metric("Selected Categories", len(selected_categories))
    c2.metric("Mileage Bins Used", len(mileage_cols))
    c3.metric(
        "Lowest Final Survival",
        f"{selected_curve_data.groupby('Product Category')['Survival Rate'].last().min():.1%}",
    )

    download_df = selected_curve_data.copy()
    st.download_button(
        "Download survival curve data",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="survival_curve_output.csv",
        mime="text/csv",
    )

    if show_data:
        st.subheader("Cleaned Incidence Data")
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
