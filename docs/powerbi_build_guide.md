# Building the dashboard in Power BI Desktop

Power BI Desktop is free but Windows-only. Expect about 2-3 hours. If you are on a Mac, Tableau Public or Looker Studio can use the same CSV and the same layout.

**Data file:** `outputs/powerbi_dataset.csv` (7,043 rows: cleaned data plus `churn_risk` and `risk_band`).
Use `outputs/retention_target_list.csv` for page 2.

## 1. Load and prepare

1. Home → Get data → Text/CSV → `powerbi_dataset.csv` → Transform data.
2. Check types: `churn_flag` whole number; `MonthlyCharges`, `TotalCharges`, `churn_risk` decimal; everything else text.
3. Rename the table to `telco`.
4. Power BI sorts text alphabetically, which breaks `risk_band` (High, Low, Medium). Add a calculated column, then Column tools → Sort by column:

```DAX
risk_band_sort = SWITCH(telco[risk_band], "Low", 1, "Medium", 2, "High", 3)
```

`tenure_band` already sorts correctly. For `charge_tier`, add a similar sort column if you use it.

## 2. Measures

```DAX
Customers = COUNTROWS(telco)
Churned = CALCULATE([Customers], telco[churn_flag] = 1)
Churn Rate = DIVIDE([Churned], [Customers])
Overall Churn Rate = CALCULATE([Churn Rate], ALL(telco))
MRR Lost = CALCULATE(SUM(telco[MonthlyCharges]), telco[churn_flag] = 1)
% MRR Lost = DIVIDE([MRR Lost], SUM(telco[MonthlyCharges]))
Avg Churn Risk = AVERAGE(telco[churn_risk])
Active High-Risk = CALCULATE([Customers], telco[churn_flag] = 0, telco[risk_band] = "High")
Active High-Risk MRR = CALCULATE(SUM(telco[MonthlyCharges]), telco[churn_flag] = 0, telco[risk_band] = "High")
```

`% MRR Lost` here means churners' monthly charges divided by all customers' summed monthly charges, matching the 30.5% in the README.

## 3. Page 1: "Why customers leave"

| Area | Visual | Fields |
|------|--------|--------|
| Top row | 4 Cards | `Customers`, `Churn Rate`, `MRR Lost`, `Active High-Risk` |
| Left | Clustered bar | Axis `Contract`; Values `Churn Rate` |
| Middle | Clustered column | Axis `tenure_band`; Values `Churn Rate` |
| Right | Clustered bar | Axis `PaymentMethod`; Values `Churn Rate` |
| Bottom left | Matrix | Rows `InternetService`; Columns `TechSupport`; Values `Churn Rate` (conditional-format the cells light to dark) |
| Bottom middle | Clustered column | Axis `risk_band` (sorted by `risk_band_sort`); Values `Churn Rate` |
| Side | 3 Slicers | `Contract`, `InternetService`, `tenure_band` |

Design rules that make it look professional:
- One accent colour for the highest bar and grey for the rest (Format → Visual → Bars → Colors → "fx" conditional formatting, or colour the single data point).
- Turn on data labels, turn off gridlines, and keep titles as plain sentences that state the finding ("Month-to-month customers churn at 42.7%").
- Put a reference line at `Overall Churn Rate` (Analytics pane → Constant line, or Average line).

## 4. Page 2: "Who to call first"

1. Table visual from `retention_target_list.csv`: `customerID`, `Contract`, `InternetService`, `tenure`, `MonthlyCharges`, `churn_risk`, `expected_monthly_loss`.
2. Sort by `expected_monthly_loss` descending; add a data-bar format on that column.
3. Add a Top N filter (Top 50) and a card with `Active High-Risk MRR`.
4. Label it clearly as illustrative (see the README limitations).

## 5. Publish

- Save the `.pbix` into a `powerbi/` folder in the repo.
- Export each page as an image (File → Export → PDF, or screenshot) and put them in the README in place of `dashboard_preview.png`.
- Publishing to the web makes the report public to anyone with the link, so check there is nothing sensitive in the data first (this dataset is a public sample, so it is fine).
