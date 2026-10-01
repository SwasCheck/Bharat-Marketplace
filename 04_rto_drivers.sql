-- 04 | What drives RTO (return-to-origin)?
-- Business question: which combinations of city tier, payment mode and delivery speed lose the most orders?
-- Techniques: multi-dimension GROUP BY, CASE bucketing, ranking with RANK().

WITH base AS (
    SELECT
        tier_label,
        payment_mode,
        CASE
            WHEN delivery_days <= 3 THEN '1-3 days'
            WHEN delivery_days <= 5 THEN '4-5 days'
            WHEN delivery_days <= 7 THEN '6-7 days'
            ELSE '8+ days'
        END AS delivery_band,
        order_status,
        order_value,
        shipping_cost
    FROM v_orders
    WHERE order_status <> 'Cancelled'
),
agg AS (
    SELECT
        tier_label,
        payment_mode,
        delivery_band,
        COUNT(*)                                                       AS orders,
        SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)           AS rto_orders,
        SUM(CASE WHEN order_status = 'RTO' THEN order_value ELSE 0 END) AS gmv_lost_to_rto,
        SUM(CASE WHEN order_status = 'RTO' THEN shipping_cost ELSE 0 END) AS shipping_spent_on_rto
    FROM base
    GROUP BY tier_label, payment_mode, delivery_band
)
SELECT
    tier_label,
    payment_mode,
    delivery_band,
    orders,
    rto_orders,
    ROUND(100.0 * rto_orders / orders, 1)       AS rto_pct,
    ROUND(gmv_lost_to_rto)                      AS gmv_lost_to_rto,
    ROUND(shipping_spent_on_rto)                AS shipping_spent_on_rto,
    RANK() OVER (ORDER BY gmv_lost_to_rto DESC) AS rank_by_gmv_lost
FROM agg
WHERE orders >= 200
ORDER BY rank_by_gmv_lost;
