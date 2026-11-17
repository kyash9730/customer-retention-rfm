-- Customer-level RFM segmentation using SQLite window functions.
-- Historic value is observed spend in the data window, not profit or future CLV.
WITH order_totals AS (
    SELECT customer_id, invoice_no, MIN(date(invoice_date)) AS order_date,
           SUM(line_value) AS order_value
    FROM clean_sales_lines
    WHERE customer_id <> ''
    GROUP BY customer_id, invoice_no
), customer_base AS (
    SELECT customer_id,
           CAST(julianday(date((SELECT MAX(order_date) FROM order_totals), '+1 day')) - julianday(MAX(order_date)) AS INTEGER) AS recency_days,
           COUNT(DISTINCT invoice_no) AS frequency,
           SUM(order_value) AS historic_value_gbp
    FROM order_totals
    GROUP BY customer_id
), scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY historic_value_gbp ASC) AS m_score
    FROM customer_base
)
SELECT *,
    r_score + f_score + m_score AS rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN f_score >= 4 AND r_score >= 3 THEN 'Loyal Regulars'
        WHEN r_score >= 4 AND f_score >= 2 THEN 'Potential Loyalists'
        WHEN r_score >= 4 AND f_score = 1 THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score = 2 THEN 'Need Attention'
        WHEN r_score <= 2 AND f_score = 1 THEN 'Hibernating'
        ELSE 'Developing'
    END AS segment
FROM scored;
