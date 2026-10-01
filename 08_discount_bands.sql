-- 08 | Does deeper discounting change basket value or RTO?
-- Business question: are steep discounts buying volume quality, or just margin loss?
-- Techniques: CASE bucketing, conditional aggregation.

SELECT
    CASE
        WHEN discount_pct < 25 THEN '1. under 25%'
        WHEN discount_pct < 35 THEN '2. 25-35%'
        WHEN discount_pct < 45 THEN '3. 35-45%'
        WHEN discount_pct < 55 THEN '4. 45-55%'
        ELSE                        '5. 55% and above'
    END                                                              AS discount_band,
    COUNT(*)                                                         AS orders,
    ROUND(AVG(unit_price), 1)                                        AS avg_selling_price,
    ROUND(AVG(order_value), 1)                                       AS aov,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN order_status <> 'Cancelled' THEN 1 ELSE 0 END), 1) AS rto_pct,  -- of shipped orders
    ROUND(100.0 * SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN order_status <> 'Cancelled' THEN 1 ELSE 0 END), 1) AS return_pct,  -- of shipped orders
    ROUND(AVG(rating), 2)                                            AS avg_rating
FROM v_orders
GROUP BY discount_band
ORDER BY discount_band;
