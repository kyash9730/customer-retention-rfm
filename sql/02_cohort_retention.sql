-- Calendar-month cohort retention. A later cohort has fewer observable months.
WITH orders AS (
    SELECT customer_id, invoice_no, date(order_date) AS order_date,
           substr(date(order_date), 1, 7) AS order_month
    FROM customer_orders
), first_month AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM orders GROUP BY customer_id
), activity AS (
    SELECT o.customer_id, f.cohort_month, o.order_month,
           (CAST(substr(o.order_month,1,4) AS INTEGER) - CAST(substr(f.cohort_month,1,4) AS INTEGER))*12
             + CAST(substr(o.order_month,6,2) AS INTEGER) - CAST(substr(f.cohort_month,6,2) AS INTEGER) AS cohort_age_month
    FROM orders o JOIN first_month f USING (customer_id)
), monthly_active AS (
    SELECT cohort_month, cohort_age_month, COUNT(DISTINCT customer_id) AS active_customers
    FROM activity GROUP BY cohort_month, cohort_age_month
), cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM first_month GROUP BY cohort_month
)
SELECT a.cohort_month, a.cohort_age_month, a.active_customers, s.cohort_size,
       ROUND(100.0 * a.active_customers / NULLIF(s.cohort_size, 0), 2) AS retention_pct
FROM monthly_active a JOIN cohort_size s USING (cohort_month)
ORDER BY a.cohort_month, a.cohort_age_month;
