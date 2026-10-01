-- 06 | Logistics cost per order by city tier and courier
-- Business question: how much of each order's value does shipping consume, and where is it worst?
-- Shipping cost includes the reverse leg on RTO and returned orders, so it measures real cost to serve.
-- Techniques: ratio metrics, grouping sets emulated with UNION ALL.

WITH cost AS (
    SELECT
        tier_label,
        courier,
        COUNT(*)                                        AS orders,
        AVG(order_value)                                AS aov,
        AVG(shipping_cost)                              AS ship_cost_per_order,
        SUM(shipping_cost)                              AS total_ship_cost,
        SUM(order_value)                                AS gmv,
        SUM(CASE WHEN order_status IN ('RTO','Returned') THEN shipping_cost ELSE 0 END) AS reverse_leg_cost
    FROM v_orders
    GROUP BY tier_label, courier
)
SELECT
    tier_label,
    courier,
    orders,
    ROUND(aov, 1)                                       AS aov,
    ROUND(ship_cost_per_order, 1)                       AS ship_cost_per_order,
    ROUND(100.0 * total_ship_cost / gmv, 1)             AS ship_cost_pct_of_gmv,
    ROUND(100.0 * reverse_leg_cost / total_ship_cost, 1) AS pct_cost_from_rto_and_returns
FROM cost

UNION ALL

SELECT
    tier_label,
    'All couriers',
    SUM(orders),
    ROUND(SUM(aov * orders) / SUM(orders), 1),
    ROUND(SUM(total_ship_cost) / SUM(orders), 1),
    ROUND(100.0 * SUM(total_ship_cost) / SUM(gmv), 1),
    ROUND(100.0 * SUM(reverse_leg_cost) / SUM(total_ship_cost), 1)
FROM cost
GROUP BY tier_label

ORDER BY tier_label, courier;
