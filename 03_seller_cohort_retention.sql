-- 03 | Seller cohort retention
-- Business question: of the sellers who got their first order in month M, how many are still selling N months later?
-- Output is long format (cohort, month offset, retention %), ready to pivot into a heatmap.
-- Techniques: cohort CTEs, month-index arithmetic, COUNT DISTINCT.

WITH cohort AS (
    SELECT seller_id, strftime('%Y-%m-01', first_order_date) AS cohort_month
    FROM dim_seller
    WHERE first_order_date IS NOT NULL
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS sellers FROM cohort GROUP BY cohort_month
),
activity AS (
    SELECT DISTINCT seller_id, strftime('%Y-%m-01', order_date) AS active_month
    FROM fact_orders
    WHERE order_status <> 'Cancelled'
),
offsets AS (
    SELECT
        c.cohort_month,
        a.seller_id,
        (CAST(strftime('%Y', a.active_month) AS INTEGER) * 12 + CAST(strftime('%m', a.active_month) AS INTEGER))
      - (CAST(strftime('%Y', c.cohort_month) AS INTEGER) * 12 + CAST(strftime('%m', c.cohort_month) AS INTEGER))
        AS months_since_first_order
    FROM cohort c
    JOIN activity a ON a.seller_id = c.seller_id
)
SELECT
    o.cohort_month,
    s.sellers                                   AS cohort_sellers,
    o.months_since_first_order,
    COUNT(DISTINCT o.seller_id)                 AS active_sellers,
    ROUND(100.0 * COUNT(DISTINCT o.seller_id) / s.sellers, 1) AS retention_pct
FROM offsets o
JOIN cohort_size s ON s.cohort_month = o.cohort_month
WHERE o.months_since_first_order BETWEEN 0 AND 6
GROUP BY o.cohort_month, s.sellers, o.months_since_first_order
ORDER BY o.cohort_month, o.months_since_first_order;
