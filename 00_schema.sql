-- Star schema for the marketplace analytics project.
-- Dialect: SQLite 3.25+ (window functions). Notes for PostgreSQL / MySQL are in docs/methodology.md.

DROP VIEW  IF EXISTS v_orders;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_city;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_city (
    city_id     INTEGER PRIMARY KEY,
    city_name   TEXT NOT NULL,
    state       TEXT NOT NULL,
    tier        INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    tier_label  TEXT NOT NULL
);

CREATE TABLE dim_category (
    category_id   INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL
);

CREATE TABLE dim_customer (
    customer_id        INTEGER PRIMARY KEY,
    city_id            INTEGER NOT NULL REFERENCES dim_city (city_id),
    acquisition_source TEXT NOT NULL,
    signup_date        DATE NOT NULL
);

CREATE TABLE dim_seller (
    seller_id           INTEGER PRIMARY KEY,
    city_id             INTEGER NOT NULL REFERENCES dim_city (city_id),
    primary_category_id INTEGER NOT NULL REFERENCES dim_category (category_id),
    onboarding_channel  TEXT NOT NULL,
    has_gst             INTEGER NOT NULL CHECK (has_gst IN (0, 1)),
    registration_date   DATE NOT NULL,
    first_listing_date  DATE,
    num_listings        INTEGER NOT NULL,
    first_order_date    DATE
);

CREATE TABLE dim_date (
    date_key       DATE PRIMARY KEY,
    year           INTEGER NOT NULL,
    month          INTEGER NOT NULL,
    month_start    DATE NOT NULL,
    month_name     TEXT NOT NULL,
    week_of_year   INTEGER NOT NULL,
    day_of_week    INTEGER NOT NULL,
    is_weekend     INTEGER NOT NULL,
    is_festive     INTEGER NOT NULL
);

CREATE TABLE fact_orders (
    order_id       TEXT PRIMARY KEY,
    order_date     DATE NOT NULL REFERENCES dim_date (date_key),
    customer_id    INTEGER NOT NULL REFERENCES dim_customer (customer_id),
    seller_id      INTEGER NOT NULL REFERENCES dim_seller (seller_id),
    category_id    INTEGER NOT NULL REFERENCES dim_category (category_id),
    city_id        INTEGER NOT NULL REFERENCES dim_city (city_id),
    payment_mode   TEXT NOT NULL CHECK (payment_mode IN ('COD', 'Prepaid')),
    courier        TEXT NOT NULL,
    unit_price     REAL NOT NULL,
    mrp            REAL NOT NULL,
    discount_pct   REAL NOT NULL,
    quantity       INTEGER NOT NULL,
    order_value    REAL NOT NULL,
    order_status   TEXT NOT NULL CHECK (order_status IN ('Delivered', 'RTO', 'Cancelled', 'Returned')),
    delivery_days  INTEGER NOT NULL,
    delivered_date DATE,
    shipping_cost  REAL NOT NULL,
    rating         REAL
);

CREATE INDEX ix_orders_date     ON fact_orders (order_date);
CREATE INDEX ix_orders_seller   ON fact_orders (seller_id);
CREATE INDEX ix_orders_customer ON fact_orders (customer_id);

-- One flat, analysis-friendly view. Most queries start here.
CREATE VIEW v_orders AS
SELECT
    o.order_id,
    o.order_date,
    strftime('%Y-%m-01', o.order_date) AS order_month,
    o.customer_id,
    o.seller_id,
    c.category_name,
    ci.city_name,
    ci.tier,
    ci.tier_label,
    o.payment_mode,
    o.courier,
    o.unit_price,
    o.discount_pct,
    o.quantity,
    o.order_value,
    o.order_status,
    o.delivery_days,
    o.shipping_cost,
    o.rating,
    CASE WHEN o.order_status = 'Delivered' THEN o.order_value ELSE 0 END AS delivered_gmv
FROM fact_orders o
JOIN dim_category c  ON c.category_id = o.category_id
JOIN dim_city     ci ON ci.city_id    = o.city_id;
