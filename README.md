# Power BI build guide

This folder holds everything needed to build the dashboard in Power BI Desktop in about an hour:

| File | What it is |
|---|---|
| `measures.dax` | 40+ DAX measures, grouped by purpose, plus the two calculated columns the cohort matrix needs |
| `marketplace_theme.json` | Plum and magenta colour theme (View > Themes > Browse for themes) |
| `reconciliation_checks.csv` | Reference numbers from SQL. Your report's cards must match these |

The `.pbix` file is not committed because it is a binary built in Power BI Desktop. After you build it, save it to this folder and add a screenshot of each page to `docs/screenshots/`.

## 1. Load the data

1. Run `python run_pipeline.py` once (or use the CSVs already in `data/processed/`).
2. In Power BI Desktop: Get data > Text/CSV, and load all six files from `data/processed/`: `FactOrders`, `DimSeller`, `DimCustomer`, `DimCity`, `DimCategory`, `DimDate`.
3. In Power Query, check the types: `Date`, `DeliveredDate`, `RegistrationDate`, `FirstListingDate`, `FirstOrderDate`, `LastOrderDate`, `SignupDate` as Date; money columns as Decimal; IDs as Whole number.

## 2. Model

Star schema, all relationships many-to-one with single-direction filtering from dimension to fact:

```
DimDate[Date]          1 --> *  FactOrders[Date]
DimSeller[SellerID]    1 --> *  FactOrders[SellerID]
DimCustomer[CustomerID]1 --> *  FactOrders[CustomerID]
DimCategory[CategoryID]1 --> *  FactOrders[CategoryID]
DimCity[CityID]        1 --> *  FactOrders[CityID]      (delivery city)
DimCity[CityID]        1 --> *  DimSeller[CityID]       (seller city, set inactive and use USERELATIONSHIP if needed)
```

Mark `DimDate` as the date table (Table tools > Mark as date table > `Date`). Sort `DimDate[month_label]` by `DimDate[month_start]`.

## 3. Measures

Create an empty table named `_Measures`, then paste measures from `measures.dax` one by one. Create the calculated columns `CohortMonth` and `MonthsSinceFirstOrder` as described in the comments.

## 4. Reconcile before you design

Build one card per row of `reconciliation_checks.csv` and confirm the numbers match. Percent measures show as a fraction in DAX, so `RTO %` of 0.182 corresponds to 18.2 in the CSV. If a number is off, fix the model before building visuals. This step is what makes the dashboard trustworthy.

## 5. Report pages

Use the theme file and a 16:9 canvas. Put the page title top left, slicers in a row across the top, KPI cards under them.

**Page 1: Executive overview**
- Cards: GMV, Orders, AOV, Active Sellers, RTO %, Shipping % of GMV
- Combo chart: GMV by `DimDate[month_label]` (columns) with GMV MoM % (line)
- Column chart: GMV by `DimCity[TierLabel]`
- Bar chart: GMV by `DimCategory[Category]`
- Slicers: month, tier, category

**Page 2: Seller health**
- Funnel: Registered Sellers, Listed Sellers, Sellers With First Order (by `OnboardingChannel` using a small-multiples or slicer)
- Matrix heatmap: cohort retention (rows `CohortMonth`, columns `MonthsSinceFirstOrder`, values `Retention %`, conditional-format background)
- Column chart: Active Sellers by `OnboardingChannel`
- Donut: `ActivityStatus` count
- Card: Top 20% Seller GMV Share, Dormant Seller %

**Page 3: Logistics and RTO**
- Matrix: `TierLabel` by `PaymentMode` with RTO % (conditional formatting)
- Clustered column: Shipping % of GMV by tier and `Courier`
- Column chart: RTO % by `DeliveryBand`
- Cards: GMV Lost to RTO, Reverse Leg Share %, Shipping Cost per Order
- Decomposition tree: RTO Orders by PaymentMode, Tier, DeliveryBand, Category

**Page 4: Category and pricing**
- Scatter: AOV (x), RTO % (y), GMV (size) by `Category`
- Column chart: RTO % by `DiscountBand`
- Table: category scorecard (GMV, AOV, RTO %, Avg Rating)

## 6. Polish checklist

- Dynamic titles using `Title GMV` and `Title RTO Card`
- Tooltips with a mini trend page
- Bookmarks for "Festive season" (Oct and Nov) and "Tier 3 only"
- Alt text on every visual
- Hide key columns and the `_Measures` helper columns from report view

## 7. Publish

File > Save as `powerbi/marketplace_dashboard.pbix`. For a shareable link, publish to Power BI Service and use Publish to web only for non-sensitive data. The data in this project is synthetic, so that is safe here.
