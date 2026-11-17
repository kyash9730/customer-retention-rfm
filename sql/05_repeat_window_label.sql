-- Illustrative label query for a 90-day repeat-purchase model.
-- Uses the final observed date to define the horizon, so it changes with the data.
WITH last_day AS (
    SELECT date(MAX(order_date)) AS max_date FROM customer_orders
), snapshot AS (
    SELECT date(max_date, '-89 day') AS snapshot_date, max_date FROM last_day
), previous_orders AS (
    SELECT o.customer_id, COUNT(DISTINCT o.invoice_no) AS prior_frequency,
           SUM(o.order_value) AS prior_value, MAX(date(o.order_date)) AS last_prior_order
    FROM customer_orders o, snapshot s
    WHERE date(o.order_date) < s.snapshot_date
    GROUP BY o.customer_id
), next_orders AS (
    SELECT o.customer_id, COUNT(DISTINCT o.invoice_no) AS next_orders_90d,
           SUM(o.order_value) AS next_value_90d
    FROM customer_orders o, snapshot s
    WHERE date(o.order_date) >= s.snapshot_date AND date(o.order_date) <= s.max_date
    GROUP BY o.customer_id
)
SELECT p.customer_id, p.prior_frequency, p.prior_value,
       CAST(julianday(s.snapshot_date) - julianday(p.last_prior_order) AS INTEGER) AS recency_days,
       CASE WHEN COALESCE(n.next_orders_90d, 0) > 0 THEN 1 ELSE 0 END AS repeat_next_90d,
       COALESCE(n.next_orders_90d, 0) AS next_orders_90d,
       COALESCE(n.next_value_90d, 0) AS next_value_90d
FROM previous_orders p CROSS JOIN snapshot s
LEFT JOIN next_orders n USING (customer_id);
