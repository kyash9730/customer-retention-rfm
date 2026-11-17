# Findings and business implications
> **Synthetic demo output.** The values below come from generated teaching data and are not findings about the real UCI retailer. Replace them by running the project with the original dataset before using them in a portfolio or interview.
## What the numbers say in this run
- The customer file contains **3,149 identified customers** over **2009-12-03 to 2011-12-09**.
- Identified customers placed **13,927 distinct orders** with **£1,264,733** of observed purchase value.
- **68.6%** of identified customers made at least two purchases in the window.
- The top 10% by observed historic value account for **58.7%** of identified customer value in this run.
- Among customers who returned, the median gap from first to second purchase was **33 days**. This excludes one-time customers.
- **Champions** has the highest total historic value in this run at **£618,024** (48.9% of identified customer value).

## What to do with this analysis
1. **Protect valuable, active customers without defaulting to discounts.** Test recognition, service and relevant product suggestions against a holdout group.
2. **Look for value that has gone quiet.** Combine past value and recency when prioritising a win-back list; do not treat the value-at-risk proxy as guaranteed lost revenue.
3. **Build a better second purchase habit.** Use the observed first-to-second purchase timing to choose a sensible follow-up window, then compare contacted and holdout customers.
4. **Keep the model in its lane.** The repeat score ranks the chance of a purchase in one 90-day window. It is not a lifetime-value forecast or proof that a campaign will work.

## Model check
- Status: Evaluated on the latest 90-day window; trained only on earlier non-overlapping windows
- Holdout ROC-AUC: **0.8316**; baseline heuristic ROC-AUC: **0.8083**; top-decile lift: **2.83x**.

## Limits worth saying out loud
- The source contains transaction price, not product cost or contribution margin. The work therefore reports observed purchase value, not profit.
- Customer IDs are absent on some source lines. Those lines remain in the transaction-quality file but cannot be assigned to a known customer for RFM.
- RFM segments are relative groups based on quintiles. Their definitions should be checked when a new time period or market is added.
- The fixed-window model is evaluated on held-out customers from one snapshot. A real campaign still needs a controlled test.
