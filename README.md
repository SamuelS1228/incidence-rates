# Incidence Rate Survival Curve App

A lightweight Streamlit app for plotting survival curves from mileage-based incidence rates.

## Why this version is faster

This version avoids heavier charting dependencies like Plotly and uses Streamlit's built-in `st.line_chart`.

## Files

- `app.py`
- `requirements.txt`
- `sample_incidence_template.csv`

## Input File

Upload a `.csv` or `.xlsx` file with one row per product category.

Required:

```text
Product Category
```

Supported mileage columns:

```text
Under 5,000
5,000 To 9,999
10,000 To 14,999
15,000 To 19,999
20,000 To 24,999
25,000 To 29,999
30,000 To 34,999
35,000 To 39,999
40,000 To 44,999
45,000 To 49,999
50,000 To 59,999
60,000 To 69,999
70,000 To 79,999
80,000 To 89,999
90,000 To 99,999
100,000 To 124,999
125,000 To 149,999
150,000 To 174,999
175,000 To 199,999
200,000 To 249,999
250,000 To 299,999
300,000 And Over
```

Ignored columns:

```text
weighted Incidence
Not Answer
```

## Features

- Upload CSV or XLSX
- Filter product categories
- Plot:
  - Survival Rate
  - Incidence Rate
  - Cumulative Failure Rate
- Aggregate selected categories into:
  - selected categories only
  - selected categories plus overall average
  - overall average only
- Download plotted output

## Survival Curve Logic

Each mileage-bin value is treated as interval incidence.

```text
Survival Rate = Previous Survival Rate × (1 - Incidence Rate)
```

The overall average is calculated by averaging interval incidence rates across the selected product categories, then building a survival curve from those average interval rates.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Create a GitHub repo.
2. Upload the files from this ZIP.
3. Create a Streamlit Cloud app from the repo.
4. Set the main file path to:

```text
app.py
```
