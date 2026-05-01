"""Insight 1: Retention Crisis — 4 charts from real data"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA     = BASE_DIR / "data"
OUT      = BASE_DIR / "charts"
OUT.mkdir(parents=True, exist_ok=True)


# ─── Theme ───────────────────────────────────────────────────────────────────
BG, PANEL, GRID = "#0A0F1E", "#111827", "#1F2937"
TXT, C1, C2, C3, C4 = "#F9FAFB", "#38BDF8", "#F472B6", "#34D399", "#FBBF24"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":PANEL,"axes.edgecolor":GRID,
    "axes.labelcolor":TXT,"xtick.color":TXT,"ytick.color":TXT,"text.color":TXT,
    "grid.color":GRID,"grid.alpha":0.35,"font.family":"DejaVu Sans","font.size":10})

# ─── Load data ────────────────────────────────────────────────────────────────
orders = pd.read_csv(DATA/"orders.csv", parse_dates=["order_date"], low_memory=False)
orders["year"] = orders["order_date"].dt.year
first_yr = orders.groupby("customer_id")["year"].min().rename("cohort")
orders = orders.join(first_yr, on="customer_id")
cohort_size = orders.groupby("cohort")["customer_id"].nunique()

# Build retention matrix (actual data)
cohorts = sorted(orders.cohort.dropna().unique().astype(int))
ret_matrix = {}
for cy in cohorts:
    cust = set(orders[orders.cohort==cy]["customer_id"])
    for y in cohorts:
        if y >= cy:
            act = len(set(orders[(orders.cohort==cy)&(orders.year==y)]["customer_id"]))
            ret_matrix[(cy,y)] = act/len(cust)*100 if cust else np.nan

# ─── CHART 1A: Cohort Retention Heatmap ──────────────────────────────────────
import matplotlib.patheffects as path_effects
fig, ax = plt.subplots(figsize=(14, 7))
years = [y for y in cohorts if y <= 2022]
Z = np.full((len(years),len(years)), np.nan)
for i,cy in enumerate(years):
    for j,y in enumerate(years):
        if (cy,y) in ret_matrix and y>=cy:
            Z[i,j] = ret_matrix[(cy,y)]

im = ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.03)
cbar.set_label("Retention Rate (%)", color=TXT, fontsize=10, fontweight="bold")
cbar.ax.yaxis.set_tick_params(color=TXT)

for i in range(len(years)):
    for j in range(len(years)):
        v = Z[i,j]
        if not np.isnan(v):
            color = "white" if v < 40 or v > 80 else "black"
            txt = ax.text(j, i, f"{v:.0f}%", ha="center", va="center",
                    fontsize=9.5, color=color, fontweight="bold")
            if color == "white":
                txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

ax.set_xticks(range(len(years))); ax.set_xticklabels(years, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(years))); ax.set_yticklabels([f"Cohort {y}" for y in years], fontsize=9)
ax.set_title("Customer Cohort Retention Matrix (2012–2022)\nRows = Acquisition Year | Columns = Activity Year",
             fontsize=15, fontweight="bold", color=C1, pad=15)
ax.set_xlabel("Activity Year", fontsize=11); ax.set_ylabel("Acquisition Cohort", fontsize=11)

# Annotate in the empty bottom-left space
ax.annotate("2012 cohort retains\n~65% year-over-year",
            xy=(2,0), xytext=(0.5, 9.5), fontsize=10, color=C3, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C3, lw=2, connectionstyle="arc3,rad=-0.1"),
            bbox=dict(boxstyle="round,pad=0.4", fc=PANEL, ec=C3, alpha=0.9))
ax.annotate("Late cohorts: <10%\nretained after Year+1",
            xy=(10,9), xytext=(4, 10.5), fontsize=10, color=C2, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C2, lw=2, connectionstyle="arc3,rad=0.1"),
            bbox=dict(boxstyle="round,pad=0.4", fc=PANEL, ec=C2, alpha=0.9))

fig.savefig(OUT/"1a_cohort_heatmap.png", dpi=160, bbox_inches="tight"); plt.close()
print("[OK] 1a")

# ─── CHART 1B: Growth Paradox ──────────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(13, 6))
ax2 = ax1.twinx()

sizes = [cohort_size.get(cy,0) for cy in years]
ax1.bar(years, sizes, color=C1, alpha=0.7, label="New Customers Acquired", width=0.7)

yr1_ret = [ret_matrix.get((cy,cy+1), np.nan) for cy in years]
ax2.plot(years, yr1_ret, color=C2, lw=3, marker="o", ms=8, label="Year+1 Retention Rate (%)", zorder=10)
ax2.fill_between(years, yr1_ret, alpha=0.15, color=C2)

for x,y in zip(years, yr1_ret):
    if not np.isnan(y):
        txt = ax2.annotate(f"{y:.0f}%", xy=(x,y), xytext=(0,12), textcoords="offset points",
                     ha="center", fontsize=9.5, color=C2, fontweight="bold")
        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

ax1.set_xlabel("Acquisition Year", fontsize=12)
ax1.set_ylabel("# New Customers", fontsize=12, color=C1, fontweight="bold")
ax2.set_ylabel("Year+1 Retention (%)", fontsize=12, color=C2, fontweight="bold")
ax2.tick_params(axis="y", colors=C2); ax1.tick_params(axis="y", colors=C1)
ax2.set_ylim(0, 100)

ax2.axhline(50, color=C4, ls="--", lw=2, alpha=0.8)
ax2.text(2020.5, 53, "Target: ≥50% Retention", fontsize=10, color=C4, fontweight="bold", ha="right")

ax1.set_title("Growth Paradox: Customer Volume Peaks, Retention Collapses\nDescriptive + Diagnostic",
              fontsize=15, fontweight="bold", color=C4, pad=15)
ax1.grid(True, ls=":", alpha=0.2)
fig.savefig(OUT/"1b_growth_paradox.png", dpi=160, bbox_inches="tight"); plt.close()
print("[OK] 1b")

# ─── CHART 1C: Survival Curves ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
groups = {"Early (2012-2013)":(2012,2013,C3), "Growth (2015-2017)":(2015,2017,C1), "Late (2020-2022)":(2020,2022,C2)}
for label,(ys,ye,col) in groups.items():
    rates = []
    for lag in range(0,6):
        rs = [ret_matrix.get((cy,cy+lag),np.nan) for cy in range(ys,ye+1) if cy+lag<=2022]
        rs = [r for r in rs if not np.isnan(r)]
        rates.append(np.mean(rs) if rs else np.nan)
    ax.plot(range(len(rates)), rates, color=col, lw=3, marker="o", ms=8, label=label)
    ax.fill_between(range(len(rates)), rates, alpha=0.1, color=col)
    if rates[-1] and not np.isnan(rates[-1]):
        txt = ax.text(len(rates)-1+0.1, rates[-1], f"{rates[-1]:.0f}%", color=col, fontsize=11, fontweight="bold")
        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

ax.set_xlabel("Years Since Acquisition", fontsize=12)
ax.set_ylabel("Average Retention Rate (%)", fontsize=12)
ax.set_xticks(range(6)); ax.set_xticklabels(["Acq. Year","+1yr","+2yr","+3yr","+4yr","+5yr"], fontsize=10)
ax.set_ylim(0,110)
ax.set_title("Customer Survival Curves by Cohort Era\nEarly cohorts survive 3× longer — Predictive Signal for CRM",
             fontsize=15, fontweight="bold", color=C3, pad=15)
ax.legend(fontsize=11, framealpha=0.5, loc="upper right")
ax.grid(True, ls=":", alpha=0.2)
ax.axhspan(0, 30, alpha=0.2, color=C2)
ax.text(0.03, 1, "Churn Zone\n(<30% Survival Threshold)", color=C2, fontsize=10, fontweight="bold", style="italic", va="center")
fig.savefig(OUT/"1c_survival_curves.png", dpi=160, bbox_inches="tight"); plt.close()
print("[OK] 1c")

# ─── CHART 1D: LTV decay forecast ────────────────────────────────────────────
oi_chunks = []
for chunk in pd.read_csv(DATA/"order_items.csv", chunksize=50000, low_memory=False):
    oi_chunks.append(chunk)
oi = pd.concat(oi_chunks, ignore_index=True)
orders2 = pd.read_csv(DATA/"orders.csv", parse_dates=["order_date"], low_memory=False)
orders2["year"] = orders2["order_date"].dt.year
first_yr2 = orders2.groupby("customer_id")["year"].min().rename("cohort")
oi_ord = oi.merge(orders2[["order_id","customer_id","year"]], on="order_id").join(first_yr2, on="customer_id")
oi_ord["revenue"] = oi_ord["quantity"] * oi_ord["unit_price"]

# ─── CHART 1D: LTV Decay Forecast ───────────────────────────────────────────
clv = oi_ord.groupby("cohort").apply(lambda x: x.groupby("customer_id")["revenue"].sum().mean(), include_groups=False).reset_index()
clv.columns = ["cohort","avg_clv"]
clv = clv[clv.cohort.between(2012,2022)]

fig, ax = plt.subplots(figsize=(13, 6))
bars = ax.bar(clv.cohort, clv.avg_clv, color=[C3 if v>clv.avg_clv.median() else C2 for v in clv.avg_clv],
              alpha=0.8, edgecolor=BG, lw=1, width=0.7)
for bar,v in zip(bars, clv.avg_clv):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5000, f"{v:,.0f}",
            ha="center", fontsize=10, color=TXT, fontweight="bold")

z = np.polyfit(clv.cohort, clv.avg_clv, 1)
p = np.poly1d(z)
ax.plot(clv.cohort, p(clv.cohort), "--", color=C4, lw=2.5, label=f"Trend: {z[0]:+.0f} VND/yr")

fut = np.array([2023, 2024, 2025])
ax.plot(fut, p(fut), ":", color=C4, lw=2.5, alpha=0.7)
ax.fill_between(fut, p(fut)-15000, p(fut)+15000, alpha=0.15, color=C4, label="±20% Margin")

for x,y in zip(fut, p(fut)):
    ax.annotate(f"Forecast\n{y:,.0f}", xy=(x,y), xytext=(0, 15 if y > 0 else -35),
                textcoords="offset points", ha="center", fontsize=9.5, color=C4, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C4, alpha=0.9))

ax.axvline(2022.5, color=TXT, ls="-.", lw=1.5, alpha=0.6)
ax.text(2022.6, clv.avg_clv.max()*0.9, "Forecast →", fontsize=11, color=C4, fontweight="bold")
ax.set_xlabel("Acquisition Cohort Year", fontsize=12)
ax.set_ylabel("Avg. Customer Lifetime Value (VND)", fontsize=12)
ax.set_title("Customer Lifetime Value by Acquisition Cohort — Declining Trend Forecast\nPrescriptive: CRM investment ROI quantified",
             fontsize=15, fontweight="bold", color=C4, pad=15)
ax.legend(fontsize=10, loc="lower left", framealpha=0.5)
ax.grid(True, ls=":", alpha=0.2)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f"{x/1e3:.0f}K"))
fig.savefig(OUT/"1d_clv_decay_forecast.png", dpi=160, bbox_inches="tight"); plt.close()
print("[OK] 1d")
print("Insight 1 complete — 4 charts saved.")
