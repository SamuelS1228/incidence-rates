# Part Category Survival Curve Streamlit App

This app lets a user upload an incidence-rate file and plot survival curves by product category.

## What the app does

- Accepts CSV, XLSX, or XLS files
- Requires a `Product Category` column
- Uses mileage-bin incidence columns
- Ignores:
  - `weighted Incidence`
  - `Not Answer`
  - undefined / non-mileage columns
- Lets the user filter to selected product categories
- Plots estimated survival curves
- Optionally plots cumulative failure curves
- Lets the user download the transformed survival-curve output

## Survival curve logic

The app treats each mileage-bin value as an interval incidence rate.

```text
Survival after each bin = Prior survival × (1 - interval incidence)
```

Example:

If a part category has these incidence rates:

```text
Under 5,000 = 2%
5,000 To 9,999 = 3%
```

Then:

```text
Survival at 5,000 = 100% × (1 - 2%) = 98%
Survival at 9,999 = 98% × (1 - 3%) = 95.1%
```

## Expected columns

```text
Product Category
weighted Incidence
Not Answer
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

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repo.
2. Upload these files:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `sample_incidence_template.csv`
3. Go to Streamlit Community Cloud.
4. Create a new app from the GitHub repo.
5. Set the main file path to:

```text
app.py
```

## Notes

The app automatically detects common incidence formats:

- Decimal rates: `0.04`
- Percent-formatted strings: `4%`
- Whole-number percentages: `4`

Whole-number percentages are converted to decimals internally.
