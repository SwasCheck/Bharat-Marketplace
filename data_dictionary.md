# Data dictionary

All data is synthetic and reproducible (`SEED = 42` in `python/config.py`). Files are in `data/raw/` (as generated) and `data/processed/` (renamed for Power BI).

## fact_orders (one row per order, 107,737 rows)

| Column | Type | Meaning |
|---|---|---|
| order_id | text | Unique order id, `ORD0000001` onward |
| order_date | date | Day the customer placed the order |
| customer_id | int | FK to dim_customer |
| seller_id | int | FK to dim_seller |
| category_id | int | FK to dim_category |
| city_id | int | Delivery city, FK to dim_city |
| payment_mode | text | `COD` (cash on delivery) or `Prepaid` |
| courier | text | `In-house network`, `Partner courier 1`, `Partner courier 2` |
| unit_price | real | Selling price per unit, Rs |
| mrp | real | Listed maximum retail price, Rs |
| discount_pct | real | `(1 - unit_price / mrp) * 100` |
| quantity | int | Units in the order (1 to 3) |
| order_value | real | `unit_price * quantity`, Rs. Counted as GMV for every status |
| order_status | text | `Delivered`, `RTO`, `Cancelled`, `Returned` |
| delivery_days | int | Days from order to delivery (or to the failed attempt for RTO) |
| delivered_date | date | Set for Delivered and Returned orders |
| shipping_cost | real | Logistics cost in Rs. Zero if cancelled. About 1.75x for RTO and 1.85x for Returned because of the reverse leg |
| rating | real | 1 to 5, only on about 30% of delivered orders |

## dim_seller (3,000 rows)

| Column | Meaning |
|---|---|
| seller_id | Primary key |
| city_id | Seller's city |
| primary_category_id | Main category sold |
| onboarding_channel | `Organic`, `Referral`, `Field sales`, `Social / ads` |
| has_gst | 1 if the seller has GST registration |
| registration_date | Joined the platform (all in 2025) |
| first_listing_date | First product listed, empty if never listed |
| num_listings | Number of products listed |
| first_order_date | First order received, empty if none |

## dim_customer (23,919 rows)

`customer_id`, `city_id`, `acquisition_source` (Organic, Paid ads, Referral, Influencer), `signup_date` (within 3 days before the first order).

## dim_city (32 rows)

`city_id`, `city_name`, `state`, `tier` (1 = top-8 metro, 2 = large city, 3 = small town), `tier_label`.

## dim_category (9 rows)

`category_id`, `category_name`.

## dim_date (365 rows)

`date_key`, `year`, `month`, `month_start`, `month_name`, `week_of_year`, `day_of_week`, `is_weekend`, `is_festive` (October and November).

## Power BI tables in data/processed

`FactOrders`, `DimSeller`, `DimCustomer`, `DimCity`, `DimCategory`, `DimDate`. Same data, PascalCase column names. `DimSeller` also carries precomputed `LifetimeOrders`, `LifetimeDeliveredGMV`, `LastOrderDate`, `ActivityStatus`. `FactOrders` adds `DiscountBand` and `DeliveryBand`.
