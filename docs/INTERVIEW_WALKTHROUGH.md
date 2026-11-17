# Interview walkthrough

## A one-minute version

"I started with a common weakness in customer dashboards: reporting total revenue without showing which customer relationships are repeatable. I built a pipeline that cleans transaction-level data, aggregates it to invoice and customer grain, scores customers using RFM, tracks first-purchase cohorts and measures the time to a second purchase. I then added a 90-day repeat-purchase ranking with training on earlier windows and evaluation on a later 90-day period. The dashboard is a guided story from value concentration to retention action, with a scenario planner for testing the economics of a retention campaign. I kept historic customer value separate from profit and did not call the repeat score a lifetime-value forecast."

## Questions you should be ready to answer

**Why count invoices instead of rows?** A single invoice can contain several product lines. Counting rows would exaggerate purchase frequency for customers with large baskets.

**Why remove cancellation invoices from the positive purchase table?** The identifier prefix signals cancellation activity. Those records should be reviewed separately rather than treated as new positive purchases.

**Why not fill missing Customer IDs?** There is no defensible way to determine which customer made an anonymous transaction. Guessing would corrupt frequency, recency and value.

**How did you decide segment cut-offs?** R, F and M are scored by quintile. The segment names then use simple rules so the output can be explained to a business user. I would review the definitions with CRM stakeholders before using the segments to trigger campaigns.

**Why use cohorts?** A blended repeat rate can hide changes in customer quality. Cohorts show whether customers acquired in different months return at a similar rate and how much follow-up history is available for each group.

**What does the model predict?** At least one purchase in the latest held-back 90-day window, using transaction history available before that window. It does not predict full lifetime value and it does not identify the causal effect of a message.

**How would you improve it?** Use rolling time-based evaluation, compare a recency/frequency baseline and gradient-boosted model, calibrate probabilities, add margin and marketing-cost data, and run controlled experiments to estimate incremental lift.

## Resume bullets - use only after real-data run

- Built a customer analytics pipeline using Python, SQL and a standalone interactive dashboard to move transaction-line data to invoice-level RFM segments, cohort retention and customer-value concentration.
- Evaluated a 90-day repeat-purchase ranking on a later time window and compared it with a recency/frequency baseline; documented model limits and proposed a controlled retention test.
- Designed a scenario planner to compare contact cost, assumed conversion, contribution margin and incrementality before committing campaign budget.

Replace the method and metric wording with the actual run details. Do not include generated demo figures as business results.
