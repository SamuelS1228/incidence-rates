import re
from typing import List

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Incidence Survival Curves", layout="wide")

MILEAGE_COLUMNS = [
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

PRODUCT_CATEGORY_COL = "Product Category"


def clean_column_name(col) -> str:
    return re.sub(r"\s+", " ", str(col).strip())


def normalize_text(value) -> str:
    return clean_column_name(value).lower()


def read_file(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)

    st.error("Please upload a .csv or .xlsx file.")
    st.stop()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_column_name(c) for c in df.columns]

    rename_map = {}

    for col in df.columns:
        if normalize_text(col) == normalize_text(PRODUCT_CATEGORY_COL):
            rename_map[col] = PRODUCT_CATEGORY_COL

        for mileage_col in MILEAGE_COLUMNS:
            if normalize_text(col) == normalize_text(mileage_col):
                rename_map[col] = mileage_col

    return df.rename(columns=rename_map)


def to_rate(value):
    if pd.isna(value):
        return 0.0

    text = str(value).strip().replace(",", "")

    if text == "":
        return 0.0

    try:
        if text.endswith("%"):
            return float(text.replace("%", "")) / 100

        number = float(text)

        # Treat whole-number values as percentages.
        # Example: 4 becomes 4%.
        if number > 1:
            return number / 100

        return number

    except ValueError:
        return 0.0


def mileage_x_value(mileage_col: str) -> int:
    numbers = re.findall(r"\d[\d,]*", mileage_col)
    numbers = [int(n.replace(",", "")) for n in numbers]

    if not numbers:
        return 0

    if "under" in mileage_col.lower():
        return numbers[0]

    if "and over" in mileage_col.lower():
        return numbers[0]

    return numbers[-1]


def build_incidence_long(df: pd.DataFrame, mileage_cols: List[str]) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        product_category = row[PRODUCT_CATEGORY_COL]

        for col in mileage_cols:
            incidence = to_rate(row[col])
            incidence = max(0.0, min(float(incidence), 1.0))

            rows.append(
                {
                    "Product Category": product_category,
                    "Mileage": mileage_x_value(col),
                    "Mileage Band": col,
                    "Incidence Rate": incidence,
                }
            )

    return pd.DataFrame(rows)


def build_survival_from_incidence(incidence_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for product_category, group in incidence_df.groupby("Product Category", sort=False):
        group = group.sort_values("Mileage")

        survival = 1.0

        rows.append(
            {
                "Product Category": product_category,
                "Mileage": 0,
                "Mileage Band": "Start",
                "Incidence Rate": 0.0,
                "Survival Rate": 1.0,
                "Cumulative Failure Rate": 0.0,
            }
        )

        for _, row in group.iterrows():
            incidence = row["Incidence Rate"]
            survival = survival * (1 - incidence)

            rows.append(
                {
                    "Product Category": product_category,
                    "Mileage": row["Mileage"],
                    "Mileage Band": row["Mileage Band"],
                    "Incidence Rate": incidence,
                    "Survival Rate": survival,
                    "Cumulative Failure Rate": 1 - survival,
                }
            )

    return pd.DataFrame(rows)


def add_overall_average(incidence_df: pd.DataFrame) -> pd.DataFrame:
    avg_df = (
        incidence_df
        .groupby(["Mileage", "Mileage Band"], as_index=False)["Incidence Rate"]
        .mean()
        .sort_values("Mileage")
    )

    avg_df["Product Category"] = "Overall Average"

    return pd.concat([incidence_df, avg_df], ignore_index=True)


st.title("Incidence Rate Survival Curves")

st.write(
    "Upload an incidence-rate file to plot survival curves by product category. "
    "Use the sidebar to select categories and optionally aggregate them into an overall average."
)

with st.expander("Expected file format", expanded=False):
    st.write("Required column: `Product Category`")
    st.write("The app uses matching mileage-bin columns and ignores `weighted Incidence`, `Not Answer`, and other non-mileage fields.")
    st.write("Supported values: `0.04`, `4%`, or `4`.")

uploaded_file = st.file_uploader("Upload incidence file", type=["csv", "xlsx"])

if uploaded_file is None:
    st.info("Upload a CSV or XLSX file to start.")
    st.stop()

df_raw = read_file(uploaded_file)
df = standardize_columns(df_raw)

if PRODUCT_CATEGORY_COL not in df.columns:
    st.error("Missing required column: Product Category")
    st.write("Columns found:")
    st.write(list(df.columns))
    st.stop()

mileage_cols_found = [col for col in MILEAGE_COLUMNS if col in df.columns]

if not mileage_cols_found:
    st.error("No mileage-bin columns were found.")
    st.write("Columns found:")
    st.write(list(df.columns))
    st.stop()

df = df[[PRODUCT_CATEGORY_COL] + mileage_cols_found].copy()
df[PRODUCT_CATEGORY_COL] = df[PRODUCT_CATEGORY_COL].astype(str).str.strip()
df = df[(df[PRODUCT_CATEGORY_COL] != "") & (df[PRODUCT_CATEGORY_COL].str.lower() != "nan")]

product_categories = sorted(df[PRODUCT_CATEGORY_COL].unique().tolist())

st.sidebar.header("Controls")

selected_categories = st.sidebar.multiselect(
    "Product categories",
    options=product_categories,
    default=product_categories[: min(10, len(product_categories))]
)

chart_measure = st.sidebar.selectbox(
    "Metric to plot",
    ["Survival Rate", "Incidence Rate", "Cumulative Failure Rate"],
    index=0
)

aggregation_mode = st.sidebar.radio(
    "Aggregation",
    [
        "Show selected categories",
        "Show selected categories + overall average",
        "Show overall average only",
    ],
    index=0
)

show_data = st.sidebar.checkbox("Show output data", value=False)

if not selected_categories:
    st.warning("Select at least one product category.")
    st.stop()

filtered_df = df[df[PRODUCT_CATEGORY_COL].isin(selected_categories)].copy()

incidence_long = build_incidence_long(filtered_df, mileage_cols_found)

if aggregation_mode in [
    "Show selected categories + overall average",
    "Show overall average only",
]:
    incidence_long = add_overall_average(incidence_long)

survival_df = build_survival_from_incidence(incidence_long)

if aggregation_mode == "Show overall average only":
    plot_df = survival_df[survival_df["Product Category"] == "Overall Average"].copy()
else:
    plot_df = survival_df.copy()

chart_df = (
    plot_df
    .pivot_table(
        index="Mileage",
        columns="Product Category",
        values=chart_measure,
        aggfunc="first"
    )
    .sort_index()
)

st.subheader(chart_measure)
st.line_chart(chart_df, height=600)

metric_col_1, metric_col_2, metric_col_3 = st.columns(3)

metric_col_1.metric("Selected Categories", len(selected_categories))
metric_col_2.metric("Mileage Bins Used", len(mileage_cols_found))

if "Overall Average" in plot_df["Product Category"].unique():
    final_avg_survival = (
        plot_df[plot_df["Product Category"] == "Overall Average"]
        .sort_values("Mileage")
        ["Survival Rate"]
        .iloc[-1]
    )
    metric_col_3.metric("Overall Avg Final Survival", f"{final_avg_survival:.1%}")
else:
    final_min_survival = (
        plot_df
        .sort_values("Mileage")
        .groupby("Product Category")["Survival Rate"]
        .last()
        .min()
    )
    metric_col_3.metric("Lowest Final Survival", f"{final_min_survival:.1%}")

st.download_button(
    "Download plotted data",
    data=plot_df.to_csv(index=False).encode("utf-8"),
    file_name="survival_curve_output.csv",
    mime="text/csv"
)

if show_data:
    st.subheader("Output Data")
    st.dataframe(plot_df, use_container_width=True)
