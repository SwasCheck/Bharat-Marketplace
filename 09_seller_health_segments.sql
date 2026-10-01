-- 09 | Seller health segments (as of the last day in the data)
-- Business question: which sellers are growing, which are slipping, and who has gone quiet?
-- Rules (on non-cancelled orders):
--   Dormant   : had orders before, none in the last 30 days
--   At risk   : last-30-day orders fell by 50%+ versus the prior 30 days (prior period had 10+ orders)
--   Star      : 100+ orders in the last 60 days and RTO under 15%
--   Growing   : last-30-day orders above the prior 30 days
--   Stable    : everyone else with recent orders
-- Techniques: date-window conditional aggregation, CASE segmentation.

WITH bounds AS (
    SELECT MAX(order_date) AS as_of FROM fact_orders
),
seller_window AS (
    SELECT
        o.seller_id,
        SUM(CASE WHEN o.order_date >  date(b.as_of, '-30 day') THEN 1 ELSE 0 END) AS orders_last_30,
        SUM(CASE WHEN o.order_date >  date(b.as_of, '-60 day')
                  AND o.order_date <= date(b.as_of, '-30 day') THEN 1 ELSE 0 END) AS orders_prior_30,
        SUM(CASE WHEN o.order_date >  date(b.as_of, '-60 day')
                  AND o.order_status = 'RTO' THEN 1 ELSE 0 END)                  AS rto_last_60,
        SUM(CASE WHEN o.order_date >  date(b.as_of, '-60 day') THEN 1 ELSE 0 END) AS orders_last_60,
        COUNT(*) AS lifetime_orders
    FROM fact_orders o
    CROSS JOIN bounds b
    WHERE o.order_status <> 'Cancelled'
    GROUP BY o.seller_id
),
segmented AS (
    SELECT
        seller_id,
        orders_last_30,
        orders_prior_30,
        lifetime_orders,
        CASE
            WHEN orders_last_30 = 0                                              THEN 'Dormant'
            WHEN orders_prior_30 >= 10 AND orders_last_30 <= 0.5 * orders_prior_30 THEN 'At risk'
            WHEN orders_last_60 >= 100 AND 1.0 * rto_last_60 / orders_last_60 < 0.15 THEN 'Star'
            WHEN orders_last_30 > orders_prior_30                                THEN 'Growing'
            ELSE 'Stable'
        END AS segment
    FROM seller_window
)
SELECT
    segment,
    COUNT(*)                                        AS sellers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_sellers,
    SUM(orders_last_30)                             AS orders_last_30,
    ROUND(AVG(lifetime_orders), 1)                  AS avg_lifetime_orders
FROM segmented
GROUP BY segment
ORDER BY sellers DESC;
