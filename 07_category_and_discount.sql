-- 07 | Category scorecard
-- Business question: which categories carry the GMV, and how do their basket size, discount, RTO and ratings compare?
-- Techniques: share of total with a window over an aggregate.

SELECT
    category_name,
    COUNT(*)                                                         AS orders,
    ROUND(SUM(order_value))                                          AS gmv,
    ROUND(100.0 * SUM(order_value) / SUM(SUM(order_value)) OVER (), 1) AS pct_of_gmv,
    ROUND(AVG(order_value), 1)                                       AS aov,
    ROUND(AVG(discount_pct), 1)                                      AS avg_discount_pct,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN order_status <> 'Cancelled' THEN 1 ELSE 0 END), 1) AS rto_pct,  -- of shipped orders
    ROUND(AVG(rating), 2)                                            AS avg_rating
FROM v_orders
GROUP BY category_name
ORDER BY gmv DESC;
