# Data dictionary

## Source columns

| Field | Meaning | Treatment |
|---|---|---|
| `Invoice` / `InvoiceNo` | Invoice identifier | Text; values beginning with `C` are cancellation invoices |
| `StockCode` | Product code | Used for distinct-product counts |
| `Description` | Product description | Retained for data checks and possible product analysis |
| `Quantity` | Units on the line | Non-positive lines are not counted as positive purchases |
| `InvoiceDate` | Transaction timestamp | Parsed as a date/time; used for order, recency and cohort calculations |
| `Price` / `UnitPrice` | Unit price in GBP | Multiplied by quantity to obtain line value |
| `Customer ID` / `CustomerID` | Pseudonymous customer key | Missing keys are not imputed and are excluded from customer metrics |
| `Country` | Customer market | Used for filtering and market comparisons |

## Main outputs

| File | Grain | Purpose |
|---|---|---|
| `data/processed/clean_sales_lines.csv` | One row per retained sales line | Clean transaction lines; includes line value |
| `data/processed/customer_orders.csv` | Customer + invoice | Purchase event used to count frequency |
| `outputs/customer_metrics.csv` | One row per identified customer | RFM scores, segment, recency, frequency and historic value |
| `outputs/segment_summary.csv` | One row per segment | Customer share and historic value share |
| `outputs/cohort_retention.csv` | Cohort month + cohort age + country | Calendar-month retention |
| `outputs/second_purchase_delays.csv` | One row per repeat customer | Days between first and second distinct invoice |
| `outputs/customer_value_concentration.csv` | One row per customer rank | Cumulative historic value curve |
| `outputs/repeat_model_deciles.csv` | One row per holdout score decile | Observed next-90-day repeat rate by predicted score |
| `outputs/repeat_model_customer_scores.csv` | Eligible customer in holdout/scored cohort | Repeat probability and outcome used for validation |
| `outputs/metrics.json` | One JSON document | Run metadata, quality counters and summary metrics |
| `outputs/customer_retention.sqlite` | SQLite tables | SQL analysis practice |

## RFM fields

| Field | Meaning |
|---|---|
| `recency_days` | Days since the last purchase before the snapshot |
| `frequency` | Distinct invoices in the observation window |
| `historic_value_gbp` | Sum of retained positive purchase line value in GBP |
| `r_score`, `f_score`, `m_score` | Relative quintile scores from 1 to 5 |
| `rfm_score` | Sum of the three RFM scores |
| `segment` | Business-friendly segment from documented score rules |
| `risk_score` | Relative prioritisation score using recency, frequency and historic-value ranks |
| `historical_value_at_risk_proxy_gbp` | Historic value multiplied by the relative risk score; a queue-prioritisation proxy, not forecast lost value |
