# Methodology

## Why synthetic data

Real marketplace data is private. This project simulates a seller programme on a Bharat-focused online marketplace so the full analytics workflow (SQL, Python, Power BI) can be shown end to end and rerun by anyone. The findings describe the simulation, not any real company. What the project demonstrates is the method: how the questions are framed, how the metrics are defined, and how the numbers are checked.

## Behaviours built into the simulation

These are the assumptions behind the data. They are set in `python/generate_data.py` and are the first thing to challenge when reading the results.

| Area | Assumption |
|---|---|
| Launch | The seller programme launches on 1 Jan 2025. Sellers register between January and early December |
| Funnel | 74 to 95% of sellers list products depending on channel, about 74% of listers get a first order, GST-registered sellers do better |
| Seller size | Order volume per seller follows a heavy-tailed lognormal, which produces a Pareto-like GMV split |
| Survival | Monthly chance of going inactive is lowest for Field sales (5%) and Referral (7%), highest for Social / ads (15%), and 25% higher without GST |
| Seasonality | Orders are 1.55x in October and November, 0.85x in January, slightly higher on weekends |
| Customers | 12% Tier 1, 33% Tier 2, 55% Tier 3 (about 88% outside the top 8 cities) |
| Payment | COD share is 34% in Tier 1, 52% in Tier 2, 66% in Tier 3 |
| Prices | Category medians scaled so average order value lands near Rs 285. Lower in smaller cities |
| Delivery | Gamma-distributed days, slower in Tier 3 and with Partner courier 2 |
| RTO | Logistic model: COD, Tier 3, delivery of 7+ days, price above Rs 450, discount of 55%+ and low seller quality raise RTO risk. Category sets the baseline |
| Shipping cost | Forward leg Rs 44 (in-house), Rs 58 and Rs 68 (partners), plus a tier adjustment. RTO and Returned orders cost 1.75x and 1.85x |

Because the RTO drivers are built into the simulation, the regression in `python/analysis.py` recovers them by design. In real data the same code would be used to discover which drivers matter.

## Metric definitions

- **GMV**: sum of `order_value` over all orders, whatever the final status.
- **Delivered GMV**: GMV of orders with status `Delivered`.
- **Shipped orders**: all orders except `Cancelled`.
- **RTO %** and **Return %**: measured on shipped orders. **Cancel %**: on all orders.
- **Activated seller**: has 5 or more non-cancelled orders within 30 days of the first order.
- **Retained seller (cohort view)**: has at least one non-cancelled order in the month. Cohort = month of first order.
- **Active seller (monthly)**: has at least one order, of any status, in the month.
- **Seller segments**: rules are in the header of `sql/analysis/09_seller_health_segments.sql`.
- **Shipping % of GMV**: total shipping cost including reverse legs divided by total GMV.

## Validation

- `load_db.py` runs `PRAGMA foreign_key_check` and expects zero violations.
- Order, GMV and seller totals are checked across SQL, Python and Power BI. `powerbi/reconciliation_checks.csv` lists the reference values.
- The generator is seeded, so reruns give identical files.

## SQL dialect notes

Queries are written for SQLite 3.25+. To port to PostgreSQL: replace `strftime('%Y-%m-01', d)` with `date_trunc('month', d)::date`, `date(d, '+30 day')` with `d + INTERVAL '30 day'`, and the month arithmetic in query 03 with `EXTRACT(YEAR FROM ...) * 12 + EXTRACT(MONTH FROM ...)`. For MySQL 8: `DATE_FORMAT(d, '%Y-%m-01')`, `DATE_ADD(d, INTERVAL 30 DAY)`, and `TIMESTAMPDIFF(MONTH, ...)`.

## Limitations

- One year of data and a simple demand model, with no price elasticity, competitor effects or customer-level repeat behaviour.
- Seller quality and RTO risk are generated rather than observed, so causal claims need real experiments.
- The prepaid what-if assumes buyers who switch to prepaid behave like existing prepaid buyers in the same tier, which is optimistic.
