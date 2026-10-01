"""Generate a synthetic, seeded dataset for a Bharat-focused online marketplace.

IMPORTANT: this data is simulated. It is not Meesho data. The generator encodes
plausible, documented behaviours (see docs/methodology.md) so that the SQL, Python
and Power BI work downstream has realistic structure to analyse:

* seller GMV follows a heavy-tailed (Pareto-like) distribution
* onboarding channel changes seller survival
* COD orders and Tier-3 deliveries have a higher RTO (return-to-origin) risk
* slower delivery raises RTO and cancellations
* festive months (Oct, Nov) lift order volume

Run:  python python/generate_data.py
"""
import numpy as np
import pandas as pd

from config import END_DATE, RAW, SEED, START_DATE

rng = np.random.default_rng(SEED)
RAW.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ dimensions
CITIES = [
    # city, state, tier (1 = top-8 metro, 2 = large city, 3 = small town)
    ("Mumbai", "Maharashtra", 1), ("Delhi", "Delhi", 1), ("Bengaluru", "Karnataka", 1),
    ("Hyderabad", "Telangana", 1), ("Chennai", "Tamil Nadu", 1), ("Kolkata", "West Bengal", 1),
    ("Pune", "Maharashtra", 1), ("Ahmedabad", "Gujarat", 1),
    ("Jaipur", "Rajasthan", 2), ("Lucknow", "Uttar Pradesh", 2), ("Indore", "Madhya Pradesh", 2),
    ("Nagpur", "Maharashtra", 2), ("Coimbatore", "Tamil Nadu", 2), ("Surat", "Gujarat", 2),
    ("Patna", "Bihar", 2), ("Bhubaneswar", "Odisha", 2), ("Ranchi", "Jharkhand", 2),
    ("Vadodara", "Gujarat", 2), ("Kochi", "Kerala", 2), ("Chandigarh", "Chandigarh", 2),
    ("Bareilly", "Uttar Pradesh", 3), ("Gorakhpur", "Uttar Pradesh", 3), ("Siliguri", "West Bengal", 3),
    ("Jhansi", "Uttar Pradesh", 3), ("Muzaffarpur", "Bihar", 3), ("Dibrugarh", "Assam", 3),
    ("Hisar", "Haryana", 3), ("Karimnagar", "Telangana", 3), ("Raichur", "Karnataka", 3),
    ("Satna", "Madhya Pradesh", 3), ("Bhilwara", "Rajasthan", 3), ("Tirunelveli", "Tamil Nadu", 3),
]
dim_city = pd.DataFrame(CITIES, columns=["city_name", "state", "tier"])
dim_city.insert(0, "city_id", np.arange(1, len(dim_city) + 1))
dim_city["tier_label"] = dim_city["tier"].map({1: "Tier 1 (top 8)", 2: "Tier 2", 3: "Tier 3"})

CATEGORIES = [
    # name, median price, price sigma, base RTO propensity
    ("Women Ethnicwear", 340, 0.50, 0.170),
    ("Men & Western Apparel", 420, 0.50, 0.150),
    ("Kids & Baby", 300, 0.50, 0.130),
    ("Home & Kitchen", 280, 0.60, 0.120),
    ("Beauty & Personal Care", 220, 0.50, 0.090),
    ("Jewellery & Accessories", 190, 0.60, 0.140),
    ("Footwear", 360, 0.45, 0.160),
    ("Electronics Accessories", 250, 0.60, 0.100),
    ("Grocery & Staples", 180, 0.50, 0.060),
]
dim_category = pd.DataFrame(CATEGORIES, columns=["category_name", "median_price", "price_sigma", "base_rto"])
dim_category.insert(0, "category_id", np.arange(1, len(dim_category) + 1))

# ------------------------------------------------------------------ sellers
N_SELLERS = 3000
seller_city_w = dim_city["tier"].map({1: 1.0, 2: 1.6, 3: 1.1}).to_numpy().copy()
seller_city_w[(dim_city["city_name"] == "Surat").to_numpy()] *= 3.0  # textile hub
seller_city_w = seller_city_w / seller_city_w.sum()

# The dataset models a seller programme that launches on 1 Jan 2025, so every seller
# registers inside the window and every cohort can be followed from day one.
reg_offsets = (rng.beta(1.5, 1.0, N_SELLERS) * 330).astype(int)  # growth skewed to later months
registration_date = pd.Timestamp(START_DATE) + pd.to_timedelta(reg_offsets, unit="D")

channels = np.array(["Organic", "Referral", "Field sales", "Social / ads"])
channel = rng.choice(channels, N_SELLERS, p=[0.40, 0.20, 0.15, 0.25])
has_gst = rng.random(N_SELLERS) < 0.55

sellers = pd.DataFrame({
    "seller_id": np.arange(1, N_SELLERS + 1),
    "city_id": rng.choice(dim_city["city_id"], N_SELLERS, p=seller_city_w),
    "primary_category_id": rng.choice(
        dim_category["category_id"], N_SELLERS, p=[0.26, 0.16, 0.08, 0.13, 0.08, 0.10, 0.07, 0.07, 0.05]
    ),
    "onboarding_channel": channel,
    "has_gst": has_gst.astype(int),
    "registration_date": registration_date,
})

# Funnel: register -> list -> first order.
p_list = np.select([channel == "Field sales", channel == "Referral"], [0.92, 0.84], default=0.74)
p_list = p_list + np.where(has_gst, 0.04, 0.0)
lists = rng.random(N_SELLERS) < p_list
list_lag = rng.exponential(4.0, N_SELLERS).astype(int)
sellers["first_listing_date"] = np.where(lists, registration_date + pd.to_timedelta(list_lag, unit="D"), pd.NaT)
sellers["first_listing_date"] = pd.to_datetime(sellers["first_listing_date"])
sellers["num_listings"] = np.where(lists, np.clip(rng.lognormal(2.8, 0.8, N_SELLERS), 1, 400).astype(int), 0)

p_order = 0.62 + np.where(has_gst, 0.06, 0.0) + np.clip(np.log1p(sellers["num_listings"]) * 0.03, 0, 0.12)
p_order = np.clip(p_order, 0, 0.9)
orders_flag = lists & (rng.random(N_SELLERS) < p_order)
order_lag = np.clip(rng.lognormal(2.0, 0.7, N_SELLERS), 1, 60).astype(int)
first_order = sellers["first_listing_date"] + pd.to_timedelta(order_lag, unit="D")
sellers["first_order_date"] = first_order.where(orders_flag & (first_order <= pd.Timestamp(END_DATE)))

# ------------------------------------------------------------------ customers
N_CUSTOMERS = 30000
cust_tier = rng.choice([1, 2, 3], N_CUSTOMERS, p=[0.12, 0.33, 0.55])  # ~88% outside top 8
cust_city = np.empty(N_CUSTOMERS, dtype=int)
for t in (1, 2, 3):
    ids = dim_city.loc[dim_city["tier"] == t, "city_id"].to_numpy()
    m = cust_tier == t
    cust_city[m] = rng.choice(ids, m.sum())
customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUSTOMERS + 1),
    "city_id": cust_city,
    "acquisition_source": rng.choice(
        ["Organic", "Paid ads", "Referral", "Influencer"], N_CUSTOMERS, p=[0.45, 0.25, 0.15, 0.15]
    ),
})
cust_weight = rng.gamma(0.9, 1.0, N_CUSTOMERS) + 0.05  # some customers reorder a lot
cust_weight = cust_weight / cust_weight.sum()

# ------------------------------------------------------------------ order generation
end = pd.Timestamp(END_DATE)
start = pd.Timestamp(START_DATE)
churn_hazard = pd.Series(
    np.select(
        [channel == "Referral", channel == "Field sales", channel == "Social / ads"],
        [0.07, 0.05, 0.15], default=0.11,
    ) * np.where(has_gst, 1.0, 1.25)
)  # monthly probability a seller goes inactive
quality = np.clip(rng.lognormal(0.0, 0.95, N_SELLERS), 0.08, 25)  # heavy tail -> Pareto-like GMV

active = sellers.index[sellers["first_order_date"].notna() & (sellers["first_order_date"] <= end)]
life_days = (rng.geometric(churn_hazard.to_numpy()[active] / 30.0)).astype(int)  # daily hazard = monthly / 30

BASE_MONTHLY_ORDERS = 10.0
rows = []
for idx, life in zip(active, life_days):
    s_start = sellers.at[idx, "first_order_date"]
    s_end = min(end, s_start + pd.Timedelta(days=int(life)))
    days = pd.date_range(max(s_start, start - pd.Timedelta(days=0)), s_end, freq="D")
    if len(days) == 0:
        continue
    age = (days - s_start).days.to_numpy()
    ramp = np.minimum(1.0, 0.35 + 0.65 * age / 60.0)
    month = days.month.to_numpy()
    season = np.where(np.isin(month, [10, 11]), 1.55, np.where(month == 1, 0.85, 1.0))
    weekend = np.where(days.dayofweek.to_numpy() >= 5, 1.08, 1.0)
    lam = BASE_MONTHLY_ORDERS / 30.0 * quality[idx] * ramp * season * weekend
    n = rng.poisson(lam)
    n[0] = max(n[0], 1)  # first-order day always has an order
    for d, k in zip(days, n):
        if k:
            rows.append((idx, d, k))

seller_idx = np.repeat([r[0] for r in rows], [r[2] for r in rows])
order_dates = np.repeat([r[1] for r in rows], [r[2] for r in rows])
n_orders = len(seller_idx)

orders = pd.DataFrame({"seller_idx": seller_idx, "order_date": pd.to_datetime(order_dates)})
orders["seller_id"] = sellers["seller_id"].to_numpy()[orders["seller_idx"]]

# category: mostly the seller's primary category
primary = sellers["primary_category_id"].to_numpy()[orders["seller_idx"]]
other = rng.choice(dim_category["category_id"], n_orders)
orders["category_id"] = np.where(rng.random(n_orders) < 0.87, primary, other)

# customer
cust_idx = rng.choice(N_CUSTOMERS, n_orders, p=cust_weight)
orders["customer_id"] = customers["customer_id"].to_numpy()[cust_idx]
orders["city_id"] = customers["city_id"].to_numpy()[cust_idx]
orders["tier"] = dim_city.set_index("city_id").loc[orders["city_id"], "tier"].to_numpy()

# payment
p_cod = np.select([orders["tier"] == 1, orders["tier"] == 2], [0.34, 0.52], default=0.66)
orders["payment_mode"] = np.where(rng.random(n_orders) < p_cod, "COD", "Prepaid")

# price, discount, quantity
cat = dim_category.set_index("category_id")
median = cat.loc[orders["category_id"], "median_price"].to_numpy()
sigma = cat.loc[orders["category_id"], "price_sigma"].to_numpy()
tier_price = np.select([orders["tier"] == 1, orders["tier"] == 2], [1.06, 0.98], default=0.90)
PRICE_SCALE = 0.72  # keeps average basket value in the low-to-mid hundreds of rupees
unit_price = np.clip(rng.lognormal(np.log(median * tier_price * PRICE_SCALE), sigma), 49, 2999).round(0)
discount = np.clip(rng.beta(5, 8, n_orders) * 0.9 + 0.12, 0.10, 0.70)
orders["unit_price"] = unit_price
orders["mrp"] = np.ceil(unit_price / (1 - discount)).astype(int)
orders["discount_pct"] = ((1 - unit_price / orders["mrp"]) * 100).round(1)
orders["quantity"] = rng.choice([1, 2, 3], n_orders, p=[0.85, 0.11, 0.04])
orders["order_value"] = (orders["unit_price"] * orders["quantity"]).astype(int)

# courier and delivery time
courier = rng.choice(["In-house network", "Partner courier 1", "Partner courier 2"], n_orders, p=[0.48, 0.32, 0.20])
orders["courier"] = courier
base_days = np.select([orders["tier"] == 1, orders["tier"] == 2], [3.0, 4.0], default=5.3)
courier_days = np.select([courier == "In-house network", courier == "Partner courier 1"], [0.0, -0.3], default=0.8)
orders["delivery_days"] = np.clip(np.round(rng.gamma(6.0, (base_days + courier_days) / 6.0)), 1, 14).astype(int)

# shipping cost: forward leg, by courier and tier
ship_base = np.select([courier == "In-house network", courier == "Partner courier 1"], [44.0, 58.0], default=68.0)
ship_tier = np.select([orders["tier"] == 1, orders["tier"] == 2], [-3.0, 0.0], default=7.0)
forward_cost = np.clip(rng.normal(ship_base + ship_tier, 6.0), 25, 120)

# outcome
logit = (
    np.log(cat.loc[orders["category_id"], "base_rto"].to_numpy() / (1 - cat.loc[orders["category_id"], "base_rto"].to_numpy()))
    - 0.45  # calibrates overall RTO to a plausible mid-teens share
    + np.where(orders["payment_mode"] == "COD", 0.95, -0.35)
    + np.where(orders["tier"] == 3, 0.30, np.where(orders["tier"] == 2, 0.10, -0.15))
    + np.where(orders["delivery_days"] >= 7, 0.55, np.where(orders["delivery_days"] >= 5, 0.20, 0.0))
    + np.where(orders["unit_price"] > 450, 0.25, 0.0)
    + np.where(orders["discount_pct"] >= 55, 0.20, 0.0)  # steep discounts attract impulse buys
    - 0.25 * np.log(quality[orders["seller_idx"].to_numpy()])
)
p_rto = 1 / (1 + np.exp(-logit))
u = rng.random(n_orders)
status = np.full(n_orders, "Delivered", dtype=object)
status[u < 0.04] = "Cancelled"
status[(u >= 0.04) & (u < 0.04 + p_rto)] = "RTO"
returned = (status == "Delivered") & (rng.random(n_orders) < np.where(orders["category_id"].isin([1, 2, 7]), 0.075, 0.035))
status[returned] = "Returned"
orders["order_status"] = status

multiplier = np.select([status == "Cancelled", status == "RTO", status == "Returned"], [0.0, 1.75, 1.85], default=1.0)
orders["shipping_cost"] = (forward_cost * multiplier).round(1)
orders["delivered_date"] = np.where(
    np.isin(status, ["Delivered", "Returned"]), orders["order_date"] + pd.to_timedelta(orders["delivery_days"], unit="D"), pd.NaT
)
orders["delivered_date"] = pd.to_datetime(orders["delivered_date"])

rating = np.clip(np.round(rng.normal(4.25 - 0.12 * np.maximum(orders["delivery_days"] - 4, 0), 0.9)), 1, 5)
has_rating = (status == "Delivered") & (rng.random(n_orders) < 0.30)
orders["rating"] = np.where(has_rating, rating, np.nan)

orders = orders.sort_values(["order_date", "seller_id"]).reset_index(drop=True)
orders.insert(0, "order_id", ["ORD" + str(i).zfill(7) for i in range(1, len(orders) + 1)])
fact_orders = orders[
    ["order_id", "order_date", "customer_id", "seller_id", "category_id", "city_id", "payment_mode", "courier",
     "unit_price", "mrp", "discount_pct", "quantity", "order_value", "order_status", "delivery_days",
     "delivered_date", "shipping_cost", "rating"]
]

# customer signup date = day of first order (minus 0-3 days)
first_order_by_cust = fact_orders.groupby("customer_id")["order_date"].min()
customers = customers[customers["customer_id"].isin(first_order_by_cust.index)].copy()
customers["signup_date"] = customers["customer_id"].map(first_order_by_cust) - pd.to_timedelta(
    rng.integers(0, 4, len(customers)), unit="D"
)

# ------------------------------------------------------------------ write
fmt = "%Y-%m-%d"
dim_city.to_csv(RAW / "dim_city.csv", index=False)
dim_category[["category_id", "category_name"]].to_csv(RAW / "dim_category.csv", index=False)
customers.to_csv(RAW / "dim_customer.csv", index=False, date_format=fmt)
sellers.to_csv(RAW / "dim_seller.csv", index=False, date_format=fmt)
fact_orders.to_csv(RAW / "fact_orders.csv", index=False, date_format=fmt)

print(f"sellers={len(sellers):,}  sellers_with_orders={fact_orders['seller_id'].nunique():,}")
print(f"customers={len(customers):,}  orders={len(fact_orders):,}")
print(f"GMV (all statuses) = Rs {fact_orders['order_value'].sum():,.0f}")
print(fact_orders["order_status"].value_counts(normalize=True).round(3).to_dict())
