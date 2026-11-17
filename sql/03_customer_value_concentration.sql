-- Cumulative customer value (Pareto) using window functions.
WITH customer_value AS (
    SELECT customer_id, SUM(order_value) AS historic_value_gbp
    FROM customer_orders GROUP BY customer_id
), ranked AS (
    SELECT customer_id, historic_value_gbp,
           ROW_NUMBER() OVER (ORDER BY historic_value_gbp DESC) AS customer_rank,
           COUNT(*) OVER () AS customer_count,
           SUM(historic_value_gbp) OVER (ORDER BY historic_value_gbp DESC ROWS UNBOUNDED PRECEDING) AS cumulative_value
    FROM customer_value
)
SELECT customer_id, historic_value_gbp, customer_rank,
       ROUND(100.0 * customer_rank / customer_count, 2) AS cumulative_customer_pct,
       ROUND(100.0 * cumulative_value / NULLIF(SUM(historic_value_gbp) OVER (), 0), 2) AS cumulative_value_pct
FROM ranked
ORDER BY customer_rank;
