"""Export a clean star schema (CSV) for Power BI.

Power BI Desktop reads these files directly with Get Data > Text/CSV. A seller-level
summary table is added so the Seller Health page does not need heavy DAX.

Run:  python python/export_powerbi.py
"""
import sqlite3

import pandas as pd

from config import DB_PATH, PROCESSED


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)

    dim_date = pd.read_sql_query("SELECT * FROM dim_date", con)
    dim_date["month_start"] = pd.to_datetime(dim_date["month_start"])
    dim_date["month_label"] = dim_date["month_start"].dt.strftime("%b %Y")
    dim_date["day_name"] = pd.to_datetime(dim_date["date_key"]).dt.strftime("%a")
    dim_date = dim_date.rename(columns={"date_key": "Date"})
    dim_date.to_csv(PROCESSED / "DimDate.csv", index=False, date_format="%Y-%m-%d")

    pd.read_sql_query(
        "SELECT city_id AS CityID, city_name AS City, state AS State, tier AS Tier, tier_label AS TierLabel FROM dim_city", con
    ).to_csv(PROCESSED / "DimCity.csv", index=False)

    pd.read_sql_query(
        "SELECT category_id AS CategoryID, category_name AS Category FROM dim_category", con
    ).to_csv(PROCESSED / "DimCategory.csv", index=False)

    pd.read_sql_query(
        "SELECT customer_id AS CustomerID, city_id AS CityID, acquisition_source AS AcquisitionSource, signup_date AS SignupDate "
        "FROM dim_customer", con
    ).to_csv(PROCESSED / "DimCustomer.csv", index=False)

    seller = pd.read_sql_query(
        """
        SELECT s.seller_id AS SellerID, s.city_id AS CityID, s.primary_category_id AS CategoryID,
               s.onboarding_channel AS OnboardingChannel,
               CASE WHEN s.has_gst = 1 THEN 'GST registered' ELSE 'No GST' END AS GSTStatus,
               s.registration_date AS RegistrationDate, s.first_listing_date AS FirstListingDate,
               s.first_order_date AS FirstOrderDate, s.num_listings AS NumListings,
               strftime('%Y-%m-01', s.registration_date) AS RegistrationMonth,
               CASE WHEN s.first_listing_date IS NOT NULL THEN 1 ELSE 0 END AS IsListed,
               CASE WHEN s.first_order_date   IS NOT NULL THEN 1 ELSE 0 END AS HasFirstOrder,
               COALESCE(a.lifetime_orders, 0) AS LifetimeOrders,
               COALESCE(a.lifetime_delivered_gmv, 0) AS LifetimeDeliveredGMV,
               a.last_order_date AS LastOrderDate,
               CASE WHEN a.last_order_date IS NULL THEN 'Never sold'
                    WHEN a.last_order_date >= date((SELECT MAX(order_date) FROM fact_orders), '-30 day') THEN 'Active (last 30 days)'
                    ELSE 'Dormant' END AS ActivityStatus
        FROM dim_seller s
        LEFT JOIN (
            SELECT seller_id, COUNT(*) AS lifetime_orders,
                   SUM(CASE WHEN order_status = 'Delivered' THEN order_value ELSE 0 END) AS lifetime_delivered_gmv,
                   MAX(order_date) AS last_order_date
            FROM fact_orders WHERE order_status <> 'Cancelled' GROUP BY seller_id
        ) a ON a.seller_id = s.seller_id
        """, con)
    seller.to_csv(PROCESSED / "DimSeller.csv", index=False)

    fact = pd.read_sql_query(
        """
        SELECT order_id AS OrderID, order_date AS Date, customer_id AS CustomerID, seller_id AS SellerID,
               category_id AS CategoryID, city_id AS CityID, payment_mode AS PaymentMode, courier AS Courier,
               unit_price AS UnitPrice, mrp AS MRP, discount_pct AS DiscountPct, quantity AS Quantity,
               order_value AS OrderValue, order_status AS OrderStatus, delivery_days AS DeliveryDays,
               delivered_date AS DeliveredDate, shipping_cost AS ShippingCost, rating AS Rating,
               CASE
                   WHEN discount_pct < 25 THEN '1. under 25%'
                   WHEN discount_pct < 35 THEN '2. 25-35%'
                   WHEN discount_pct < 45 THEN '3. 35-45%'
                   WHEN discount_pct < 55 THEN '4. 45-55%'
                   ELSE '5. 55% and above' END AS DiscountBand,
               CASE
                   WHEN delivery_days <= 3 THEN '1-3 days'
                   WHEN delivery_days <= 5 THEN '4-5 days'
                   WHEN delivery_days <= 7 THEN '6-7 days'
                   ELSE '8+ days' END AS DeliveryBand
        FROM fact_orders
        """, con)
    fact.to_csv(PROCESSED / "FactOrders.csv", index=False)

    # Reference numbers: after building the report, the Power BI cards should match these exactly.
    chk = pd.read_sql_query(
        """
        SELECT
            COUNT(*)                                                                    AS orders,
            SUM(order_value)                                                            AS gmv,
            SUM(CASE WHEN order_status = 'Delivered' THEN order_value ELSE 0 END)       AS delivered_gmv,
            SUM(order_value) * 1.0 / COUNT(*)                                           AS aov,
            COUNT(DISTINCT seller_id)                                                   AS active_sellers,
            SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100.0
              / SUM(CASE WHEN order_status <> 'Cancelled' THEN 1 ELSE 0 END)            AS rto_pct_of_shipped,
            SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS cancel_pct,
            SUM(CASE WHEN payment_mode = 'COD' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)    AS cod_share_pct,
            SUM(shipping_cost) * 1.0 / COUNT(*)                                         AS shipping_cost_per_order,
            SUM(shipping_cost) * 100.0 / SUM(order_value)                               AS shipping_pct_of_gmv
        FROM fact_orders
        """, con).iloc[0].round(2)
    out = pd.DataFrame({"measure": chk.index, "expected_value": chk.values})
    names = {"orders": "Orders", "gmv": "GMV", "delivered_gmv": "Delivered GMV", "aov": "AOV",
             "active_sellers": "Active Sellers", "rto_pct_of_shipped": "RTO % (x100)", "cancel_pct": "Cancel % (x100)",
             "cod_share_pct": "COD Share % (x100)", "shipping_cost_per_order": "Shipping Cost per Order",
             "shipping_pct_of_gmv": "Shipping % of GMV (x100)"}
    out["power_bi_measure"] = out["measure"].map(names)
    (PROCESSED.parent.parent / "powerbi").mkdir(exist_ok=True)
    out[["power_bi_measure", "expected_value"]].to_csv(PROCESSED.parent.parent / "powerbi" / "reconciliation_checks.csv", index=False)

    for f in sorted(PROCESSED.glob("*.csv")):
        print(f"{f.name:20s} {sum(1 for _ in open(f, encoding='utf-8')) - 1:>9,} rows")
    con.close()


if __name__ == "__main__":
    main()
