"""Statistical analysis and charts built on the SQL results and the SQLite database.

Produces:
  reports/figures/*.png            charts used in the README
  reports/tables/stats_summary.json  numbers quoted in the README
  reports/tables/rto_logit_odds_ratios.csv

Run:  python python/analysis.py
"""
import json
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from config import BAD, DB_PATH, FIGURES, GREY, LIGHT, MAGENTA, PINK, PLUM, TABLES, TEAL

FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 160, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GREY, "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlecolor": PLUM, "axes.titlelocation": "left",
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / name, facecolor="white")
    plt.close(fig)
    print("saved", name)


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    summary: dict = {}

    # ---------------------------------------------------------- 1. GMV trend
    kpi = pd.read_csv(TABLES / "01_monthly_kpis.csv")
    kpi["month"] = pd.to_datetime(kpi["order_month"]).dt.strftime("%b")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    colors = [PINK if m in ("Oct", "Nov") else MAGENTA for m in kpi["month"]]
    ax.bar(kpi["month"], kpi["gmv"] / 1e5, color=colors)
    ax.set_ylabel("GMV (Rs lakh)")
    ax.set_title("Monthly GMV: steady ramp, then a festive-season step-up")
    for x, v in zip(kpi["month"], kpi["gmv"] / 1e5):
        ax.text(x, v + 1, f"{v:.0f}", ha="center", fontsize=8, color=GREY)
    ax.text(0.99, 0.95, "Pink bars = Oct and Nov (festive)", transform=ax.transAxes, ha="right", va="top", color=GREY, fontsize=8)
    save(fig, "01_gmv_trend.png")

    # ---------------------------------------------------------- 2. activation funnel
    fun = pd.read_csv(TABLES / "02_seller_activation_funnel.csv")
    fun = fun[fun["onboarding_channel"] != "All channels"].sort_values("pct_registered_to_activated")
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.barh(fun["onboarding_channel"], fun["pct_registered_to_activated"], color=MAGENTA)
    for y, v in enumerate(fun["pct_registered_to_activated"]):
        ax.text(v + 0.6, y, f"{v:.0f}%", va="center", color=GREY)
    ax.set_xlabel("Registered sellers who reach 5+ orders within 30 days of first order (%)")
    ax.set_title("Field sales and referrals activate far more sellers")
    ax.set_xlim(0, fun["pct_registered_to_activated"].max() * 1.18)
    save(fig, "02_activation_by_channel.png")
    summary["activation_all_pct"] = float(pd.read_csv(TABLES / "02_seller_activation_funnel.csv").query("onboarding_channel == 'All channels'")["pct_registered_to_activated"].iloc[0])
    summary["activation_best_channel"] = fun.iloc[-1]["onboarding_channel"]
    summary["activation_best_pct"] = float(fun.iloc[-1]["pct_registered_to_activated"])
    summary["activation_worst_channel"] = fun.iloc[0]["onboarding_channel"]
    summary["activation_worst_pct"] = float(fun.iloc[0]["pct_registered_to_activated"])

    # ---------------------------------------------------------- 3. cohort heatmap
    coh = pd.read_csv(TABLES / "03_seller_cohort_retention.csv")
    piv = coh.pivot(index="cohort_month", columns="months_since_first_order", values="retention_pct")
    piv = piv[piv.index >= "2025-02-01"]  # Jan cohort has too few sellers to read
    piv.index = pd.to_datetime(piv.index).strftime("%b %Y")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    im = ax.imshow(piv.values, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("m", [LIGHT, PINK, PLUM]), vmin=20, vmax=100, aspect="auto")
    ax.set_xticks(range(piv.shape[1]), [f"M+{c}" for c in piv.columns])
    ax.set_yticks(range(piv.shape[0]), piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 60 else PLUM)
    ax.set_title("Seller retention by first-order cohort (% still selling)")
    ax.spines[:].set_visible(False)
    save(fig, "03_cohort_retention.png")
    m3 = coh[(coh["months_since_first_order"] == 3) & (coh["cohort_month"] >= "2025-02-01") & (coh["cohort_month"] <= "2025-08-01")]
    summary["retention_m3_avg_pct"] = round(float(np.average(m3["retention_pct"], weights=m3["cohort_sellers"])), 1)

    # ---------------------------------------------------------- 4. RTO heatmap + tests
    orders = pd.read_sql_query(
        "SELECT order_status, payment_mode, tier, delivery_days, unit_price, discount_pct, category_name, courier, order_value "
        "FROM v_orders WHERE order_status <> 'Cancelled'", con)
    orders["rto"] = (orders["order_status"] == "RTO").astype(int)
    grid = orders.pivot_table(index="tier", columns="payment_mode", values="rto", aggfunc="mean") * 100
    grid.index = ["Tier 1", "Tier 2", "Tier 3"]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.imshow(grid.values, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("m", [LIGHT, PINK, PLUM]), aspect="auto")
    ax.set_xticks(range(2), grid.columns)
    ax.set_yticks(range(3), grid.index)
    for i in range(3):
        for j in range(2):
            ax.text(j, i, f"{grid.values[i, j]:.1f}%", ha="center", va="center", color="white" if grid.values[i, j] > 14 else PLUM, fontweight="bold")
    ax.set_title("RTO rate by city tier and payment mode")
    ax.spines[:].set_visible(False)
    save(fig, "04_rto_heatmap.png")
    summary["rto_overall_pct"] = round(orders["rto"].mean() * 100, 1)
    summary["rto_cod_pct"] = round(orders.loc[orders.payment_mode == "COD", "rto"].mean() * 100, 1)
    summary["rto_prepaid_pct"] = round(orders.loc[orders.payment_mode == "Prepaid", "rto"].mean() * 100, 1)
    summary["rto_t3_cod_pct"] = round(float(grid.loc["Tier 3", "COD"]), 1)
    summary["rto_t1_prepaid_pct"] = round(float(grid.loc["Tier 1", "Prepaid"]), 1)

    ct = pd.crosstab(orders["payment_mode"], orders["rto"])
    chi2, p, _, _ = stats.chi2_contingency(ct)
    summary["chi2_cod_vs_prepaid"] = {"chi2": round(float(chi2), 1), "p_value": float(p)}

    # logistic regression: odds ratios for RTO drivers
    orders["cod"] = (orders["payment_mode"] == "COD").astype(int)
    orders["tier3"] = (orders["tier"] == 3).astype(int)
    orders["tier2"] = (orders["tier"] == 2).astype(int)
    orders["slow_delivery"] = (orders["delivery_days"] >= 7).astype(int)
    orders["high_price"] = (orders["unit_price"] > 450).astype(int)
    orders["deep_discount"] = (orders["discount_pct"] >= 55).astype(int)
    model = smf.logit("rto ~ cod + tier2 + tier3 + slow_delivery + high_price + deep_discount", data=orders).fit(disp=False)
    ors = pd.DataFrame({
        "odds_ratio": np.exp(model.params), "ci_low": np.exp(model.conf_int()[0]), "ci_high": np.exp(model.conf_int()[1]),
        "p_value": model.pvalues,
    }).drop(index="Intercept").round(3)
    ors.to_csv(TABLES / "rto_logit_odds_ratios.csv")
    summary["rto_odds_ratio_cod"] = float(ors.loc["cod", "odds_ratio"])
    summary["rto_odds_ratio_tier3"] = float(ors.loc["tier3", "odds_ratio"])
    summary["rto_odds_ratio_slow"] = float(ors.loc["slow_delivery", "odds_ratio"])

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    o = ors.sort_values("odds_ratio")
    labels = {"cod": "Cash on delivery", "tier2": "Tier 2 city", "tier3": "Tier 3 town", "slow_delivery": "Delivery 7+ days",
              "high_price": "Price above Rs 450", "deep_discount": "Discount 55%+"}
    ax.errorbar(o["odds_ratio"], range(len(o)), xerr=[o["odds_ratio"] - o["ci_low"], o["ci_high"] - o["odds_ratio"]],
                fmt="o", color=MAGENTA, ecolor=GREY, capsize=3)
    ax.axvline(1, color=GREY, lw=1, ls="--")
    ax.set_yticks(range(len(o)), [labels[i] for i in o.index])
    ax.set_xlabel("Odds ratio for RTO (1 = no effect), 95% CI")
    ax.set_title("What raises the odds of an order coming back")
    save(fig, "05_rto_odds_ratios.png")

    # ---------------------------------------------------------- 5. Pareto
    conc = pd.read_csv(TABLES / "05_seller_concentration.csv")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = np.arange(0, 101, 10)
    y = np.concatenate([[0], conc["cumulative_pct_of_gmv"].to_numpy()])
    ax.plot(x, y, color=MAGENTA, lw=2.5, marker="o")
    ax.plot([0, 100], [0, 100], color=GREY, ls="--", lw=1)
    ax.set_xlabel("Share of sellers, ranked by delivered GMV (%)")
    ax.set_ylabel("Cumulative share of GMV (%)")
    ax.set_title("A small group of sellers carries most of the GMV")
    ax.annotate(f"Top 10% of sellers = {conc.loc[0, 'pct_of_gmv']:.0f}% of GMV", (10, conc.loc[0, "cumulative_pct_of_gmv"]),
                (38, 14), arrowprops=dict(arrowstyle="->", color=GREY), color=PLUM)
    save(fig, "06_seller_pareto.png")
    summary["top10_seller_share_pct"] = float(conc.loc[0, "pct_of_gmv"])
    summary["top20_seller_share_pct"] = float(conc.loc[1, "cumulative_pct_of_gmv"])

    # ---------------------------------------------------------- 6. logistics
    lg = pd.read_csv(TABLES / "06_logistics_cost_by_tier.csv")
    tier_all = lg[lg["courier"] == "All couriers"].set_index("tier_label")
    piv = lg[lg["courier"] != "All couriers"].pivot(index="tier_label", columns="courier", values="ship_cost_pct_of_gmv")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    w = 0.26
    for k, (c, col) in enumerate(zip(piv.columns, [MAGENTA, TEAL, PINK])):
        ax.bar(np.arange(3) + (k - 1) * w, piv[c], w, label=c, color=col)
    ax.set_xticks(range(3), piv.index)
    ax.set_ylabel("Shipping cost as % of GMV")
    ax.set_title("Cost to serve climbs with distance from the metros")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    ax.set_ylim(0, piv.to_numpy().max() * 1.25)
    save(fig, "07_logistics_cost.png")
    summary["ship_pct_gmv_t1"] = float(tier_all.loc["Tier 1 (top 8)", "ship_cost_pct_of_gmv"])
    summary["ship_pct_gmv_t3"] = float(tier_all.loc["Tier 3", "ship_cost_pct_of_gmv"])
    summary["ship_per_order_t1"] = float(tier_all.loc["Tier 1 (top 8)", "ship_cost_per_order"])
    summary["ship_per_order_t3"] = float(tier_all.loc["Tier 3", "ship_cost_per_order"])
    inh = lg[(lg.tier_label == "Tier 3") & (lg.courier == "In-house network")].iloc[0]
    p2 = lg[(lg.tier_label == "Tier 3") & (lg.courier == "Partner courier 2")].iloc[0]
    summary["t3_inhouse_vs_partner2_gap"] = round(float(p2.ship_cost_per_order - inh.ship_cost_per_order), 1)

    # ---------------------------------------------------------- 7. what-if: prepaid nudge
    t3_cod = orders[(orders.tier == 3) & (orders.payment_mode == "COD")]
    t3_pre = orders[(orders.tier == 3) & (orders.payment_mode == "Prepaid")]
    rto_gap = t3_cod["rto"].mean() - t3_pre["rto"].mean()
    ship_t3 = pd.read_sql_query("SELECT AVG(shipping_cost) c FROM v_orders WHERE tier = 3 AND order_status = 'RTO'", con)["c"].iloc[0]
    shift = 0.10  # 10 percentage points of Tier-3 COD orders move to prepaid
    saved = shift * len(t3_cod) * rto_gap
    summary["whatif_prepaid_shift_pts"] = 10
    summary["whatif_rto_orders_avoided"] = int(round(saved))
    summary["whatif_rto_gap_pts"] = round(rto_gap * 100, 1)
    summary["whatif_shipping_saved_rs"] = int(round(saved * ship_t3))
    avg_value = t3_cod.loc[t3_cod["rto"] == 1, "order_value"].mean()
    summary["whatif_gmv_recovered_rs"] = int(round(saved * avg_value))

    # ---------------------------------------------------------- 8. overall headline numbers
    head = pd.read_sql_query(
        "SELECT COUNT(*) orders, SUM(order_value) gmv, SUM(delivered_gmv) dgmv, AVG(order_value) aov, "
        "COUNT(DISTINCT seller_id) sellers FROM v_orders", con).iloc[0]
    summary["orders"] = int(head["orders"])
    summary["gmv_cr"] = round(head["gmv"] / 1e7, 2)
    summary["delivered_gmv_cr"] = round(head["dgmv"] / 1e7, 2)
    summary["aov"] = round(head["aov"], 0)
    summary["selling_sellers"] = int(head["sellers"])
    seg = pd.read_csv(TABLES / "09_seller_health_segments.csv").set_index("segment")["pct_of_sellers"].to_dict()
    summary["segments_pct"] = seg

    (TABLES / "stats_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=2, default=float))
    con.close()


if __name__ == "__main__":
    main()
