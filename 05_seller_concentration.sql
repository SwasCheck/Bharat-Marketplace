-- 05 | Seller concentration (Pareto)
-- Business question: how dependent is GMV on a small set of sellers?
-- Techniques: NTILE, running totals with SUM() OVER, share-of-total.

WITH seller_gmv AS (
    SELECT seller_id, SUM(delivered_gmv) AS gmv, COUNT(*) AS orders
    FROM v_orders
    GROUP BY seller_id
),
ranked AS (
    SELECT
        seller_id,
        gmv,
        orders,
        NTILE(10) OVER (ORDER BY gmv DESC)                       AS decile,
        SUM(gmv) OVER (ORDER BY gmv DESC, seller_id)             AS running_gmv,
        SUM(gmv) OVER ()                                         AS total_gmv
    FROM seller_gmv
)
SELECT
    decile,
    COUNT(*)                                       AS sellers,
    ROUND(SUM(gmv))                                AS gmv,
    ROUND(100.0 * SUM(gmv) / MAX(total_gmv), 1)    AS pct_of_gmv,
    ROUND(100.0 * MAX(running_gmv) / MAX(total_gmv), 1) AS cumulative_pct_of_gmv,
    ROUND(AVG(orders), 1)                          AS avg_orders_per_seller
FROM ranked
GROUP BY decile
ORDER BY decile;
