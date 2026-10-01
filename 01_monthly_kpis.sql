-- 01 | Monthly marketplace KPIs with month-over-month growth
-- Business question: how fast is the marketplace growing, and is order quality holding up?
-- Techniques: conditional aggregation, LAG window function.

WITH monthly AS (
    SELECT
        order_month,
        COUNT(*)                                                   AS orders,
        SUM(order_value)                                           AS gmv,
        SUM(delivered_gmv)                                         AS delivered_gmv,
        COUNT(DISTINCT seller_id)                                  AS active_sellers,
        COUNT(DISTINCT customer_id)                                AS active_customers,
        SUM(CASE WHEN order_status = 'RTO'       THEN 1 ELSE 0 END) AS rto_orders,
        SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
        SUM(CASE WHEN order_status = 'Returned'  THEN 1 ELSE 0 END) AS returned_orders
    FROM v_orders
    GROUP BY order_month
)
SELECT
    order_month,
    orders,
    active_sellers,
    active_customers,
    ROUND(gmv)                                         AS gmv,
    ROUND(delivered_gmv)                               AS delivered_gmv,
    ROUND(1.0 * gmv / orders, 1)                       AS aov,
    ROUND(100.0 * rto_orders / (orders - cancelled_orders), 1)      AS rto_pct,      -- of shipped (non-cancelled) orders
    ROUND(100.0 * cancelled_orders / orders, 1)                     AS cancel_pct,   -- of all orders
    ROUND(100.0 * returned_orders / (orders - cancelled_orders), 1) AS return_pct,   -- of shipped orders
    ROUND(100.0 * (gmv - LAG(gmv) OVER (ORDER BY order_month))
          / LAG(gmv) OVER (ORDER BY order_month), 1)   AS gmv_mom_pct
FROM monthly
ORDER BY order_month;
