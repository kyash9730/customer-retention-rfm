# Methodology and checks

## Data preparation

The source workbook has two sheets, and may use either `Invoice` or `InvoiceNo` as the invoice column. The loader standardises common column-name variations. Exact duplicate rows are removed before calculating sales. Cancellation invoices are identified by an invoice number beginning with `C`; non-positive quantities and non-positive prices are kept out of the clean purchase table. The data-quality counters are written to `outputs/metrics.json`.

Missing customer IDs are not guessed or imputed. These rows can be useful for invoice-level totals, but they are excluded from customer-level frequency, cohort, RFM and repeat-purchase work because there is no reliable way to attach them to a person.

## Customer grain

The invoice is the purchase event. Product lines are aggregated to one row per `customer_id` and `invoice_no`. Frequency counts distinct invoices. This avoids treating a large basket as several purchases merely because it has several line items.

## RFM and segments

- **Recency:** days between a customer's most recent invoice and the snapshot date.
- **Frequency:** number of distinct invoices in the observation window.
- **Monetary / historic value:** sum of quantity times unit price over retained sales lines.

The three measures are assigned quintile scores from 1 to 5. For recency, a smaller number of days gets a higher score. For frequency and monetary value, a larger number gets a higher score. The names such as `Champions`, `At Risk` and `Hibernating` are simple rules over the scores; they are not fixed truths about customers. Thresholds and labels are documented in `src/analysis.py`.

## Cohort retention

A customer's cohort month is the calendar month of their first observed purchase. Cohort age zero is the month of first purchase; age one is the following calendar month. Retention is active customers in a cohort-age month divided by the original cohort size. Later cohorts have fewer observed months, so empty cells are left empty rather than treated as zero.

## Value concentration

Customers are ordered by historic value from high to low. The cumulative curve compares cumulative customer share to cumulative historic purchase value. This helps expose concentration, but does not explain what caused it or how much is profitable after product and service costs.

## Repeat-purchase score

The latest 90-day window is held back for testing. Customer features use invoices before the snapshot. Training examples come from earlier, non-overlapping 90-day windows, and their labels finish before the test window begins. A logistic regression is evaluated on the later period. This is a historical time-based check, but it is still not proof of live campaign performance.

The project compares ROC-AUC against a simple rule based on recency and frequency. It also reports average precision, Brier score and observed repeat rate by predicted score decile. A future production version should validate on multiple rolling cut-off dates, compare against more baselines and monitor drift.

## Lifetime value

The source does not provide acquisition cost, margin by product, customer service cost or a complete observation of each customer's future. The project therefore separates:

1. observed historic customer value;
2. annualised historic value as a rough descriptive rate;
3. a fixed 90-day repeat-purchase probability; and
4. a hypothetical scenario planner that asks the analyst to supply outreach cost, order value, margin and incremental lift.

None of these is presented as a full predictive customer lifetime value model.

## Known limits

- Data covers one retailer and a historical period; it should not be assumed to describe a modern business.
- Some rows lack Customer ID, limiting the known-customer base.
- Returns and cancellations are recorded separately from positive purchase lines. Return value should be interpreted with the dataset's accounting conventions in mind.
- Customer-level historic value is not contribution profit.
- Cohort retention is a calendar-month measure and can be affected by seasonality.
- The dashboard's scenario planner is only as credible as the assumptions entered by the user.
