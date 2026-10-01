-- 02 | Seller activation funnel by onboarding channel
-- Business question: where do new sellers drop off, and which channel brings sellers who actually sell?
-- Stages: registered -> listed -> first order -> activated (5+ non-cancelled orders within 30 days of first order).
-- Techniques: CTEs, correlated subquery avoided with a pre-aggregated join, conditional aggregation.

WITH early_orders AS (
    SELECT
        s.seller_id,
        COUNT(*) AS orders_first_30d
    FROM dim_seller s
    JOIN fact_orders o
      ON o.seller_id = s.seller_id
     AND o.order_status <> 'Cancelled'
     AND o.order_date BETWEEN s.first_order_date AND date(s.first_order_date, '+30 day')
    GROUP BY s.seller_id
),
funnel AS (
    SELECT
        s.onboarding_channel,
        COUNT(*)                                                           AS registered,
        SUM(CASE WHEN s.first_listing_date IS NOT NULL THEN 1 ELSE 0 END)  AS listed,
        SUM(CASE WHEN s.first_order_date   IS NOT NULL THEN 1 ELSE 0 END)  AS first_order,
        SUM(CASE WHEN COALESCE(e.orders_first_30d, 0) >= 5 THEN 1 ELSE 0 END) AS activated
    FROM dim_seller s
    LEFT JOIN early_orders e ON e.seller_id = s.seller_id
    GROUP BY s.onboarding_channel
)
SELECT
    onboarding_channel,
    registered,
    listed,
    first_order,
    activated,
    ROUND(100.0 * listed      / registered, 1) AS pct_listed,
    ROUND(100.0 * first_order / listed,     1) AS pct_listed_to_first_order,
    ROUND(100.0 * activated   / registered, 1) AS pct_registered_to_activated
FROM funnel

UNION ALL

SELECT
    'All channels',
    SUM(registered), SUM(listed), SUM(first_order), SUM(activated),
    ROUND(100.0 * SUM(listed)      / SUM(registered), 1),
    ROUND(100.0 * SUM(first_order) / SUM(listed),     1),
    ROUND(100.0 * SUM(activated)   / SUM(registered), 1)
FROM funnel
ORDER BY pct_registered_to_activated DESC;
