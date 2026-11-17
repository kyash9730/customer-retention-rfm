-- An interpretable queue to review before a retention test.
-- The risk/value product is a prioritisation proxy, not a forecast of money lost.
SELECT customer_id, country, segment, frequency, recency_days,
       historic_value_gbp, risk_score,
       historical_value_at_risk_proxy_gbp,
       recommended_action
FROM customer_metrics
WHERE segment IN ('At Risk', 'Need Attention', 'Hibernating')
ORDER BY historical_value_at_risk_proxy_gbp DESC, recency_days DESC
LIMIT 500;
