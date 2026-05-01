"""Insight 4: Stockout Bleeding — 4 charts | Insight 5: Traffic Quality — 4 charts"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import matplotlib.patches as mpatches, matplotlib.dates as mdates
import matplotlib.patheffects as path_effects
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA     = BASE_DIR / "data"
OUT      = BASE_DIR / "charts"
OUT.mkdir(parents=True, exist_ok=True)


BG,PANEL,GRID = "#0A0F1E","#111827","#1F2937"
TXT,C1,C2,C3,C4,C5 = "#F9FAFB","#38BDF8","#F472B6","#34D399","#FBBF24","#A78BFA"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":PANEL,"axes.edgecolor":GRID,
    "axes.labelcolor":TXT,"xtick.color":TXT,"ytick.color":TXT,"text.color":TXT,
    "grid.color":GRID,"grid.alpha":0.35,"font.family":"DejaVu Sans","font.size":10})

inv   = pd.read_csv(DATA/"inventory.csv")
sales = pd.read_csv(DATA/"sales.csv", parse_dates=["Date"])
web   = pd.read_csv(DATA/"web_traffic.csv", parse_dates=["date"])
orders= pd.read_csv(DATA/"orders.csv", parse_dates=["order_date"], low_memory=False)
products = pd.read_csv(DATA/"products.csv")

# ─── Inventory monthly aggregation ───────────────────────────────────────────
inv["date"] = pd.to_datetime(inv[["year","month"]].assign(day=1))
inv_m = inv.groupby("date").agg(
    stockout_rate=("stockout_flag","mean"),
    fill_rate=("fill_rate","mean"),
    stockout_days=("stockout_days","sum"),
    units_sold=("units_sold","sum")).reset_index()

sales_m = sales.set_index("Date").resample("MS")["Revenue"].sum().reset_index()
sales_m.columns = ["date","revenue"]
inv_m = inv_m.merge(sales_m, on="date", how="left").fillna(0)
inv_m["est_lost"] = inv_m.revenue * inv_m.stockout_rate * 0.4

# ── 4A: Dual-panel realized + lost revenue ───────────────────────────────────
fig, (ax1,ax2) = plt.subplots(2,1, figsize=(14,8), gridspec_kw={"height_ratios":[1.5,1]}, sharex=True)

ax1.fill_between(inv_m.date, 0, inv_m.revenue/1e6, alpha=0.45, color=C1, label="Realized Revenue")
ax1.fill_between(inv_m.date, inv_m.revenue/1e6, (inv_m.revenue+inv_m.est_lost)/1e6,
                 alpha=0.6, color=C2, label="Lost Revenue (Stockout ~40% conv.)")

# Forecast lost revenue
x_n = np.arange(len(inv_m))
cf = np.polyfit(x_n, inv_m.est_lost/1e6, 1)
fut = pd.date_range(inv_m.date.iloc[-1]+pd.offsets.MonthBegin(), periods=18, freq="MS")
fut_pred = np.clip(np.polyval(cf, np.arange(len(inv_m), len(inv_m)+18)), 0, None)
ax1.plot(fut, fut_pred, "--", color=C4, lw=2.5, label="Stockout Loss Forecast")
ax1.fill_between(fut, fut_pred*0.7, fut_pred*1.3, alpha=0.1, color=C4)
ax1.axvline(inv_m.date.iloc[-1], color=TXT, ls=":", lw=1.5, alpha=0.5)

total_lost = inv_m.est_lost.sum()
ax1.annotate(f"Total Est. Revenue Lost\n{total_lost/1e9:.2f}B VND Historical",
             xy=(inv_m.date.iloc[20], inv_m.est_lost.iloc[20]/1e6),
             xytext=(inv_m.date.iloc[5], inv_m.revenue.max()/1e6*0.7),
             fontsize=9.5, color=C2, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C2, lw=1.5),
             bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C2, alpha=0.9))

ax1.set_ylabel("Monthly Revenue (M VND)"); ax1.legend(fontsize=9, framealpha=0.3)
ax1.set_title("Stockout Bleeding: Revenue Evaporation from Inventory Failure\nDiagnostic → Predictive → Prescriptive", fontsize=13, color=C2, fontweight="bold")
ax1.grid(True, ls="--", alpha=0.3)

ax2.plot(inv_m.date, inv_m.stockout_rate*100, color=C2, lw=2, label="Stockout Rate (%)", alpha=0.8)
ax2.plot(inv_m.date, inv_m.fill_rate*100, color=C3, lw=2.5, label="Fill Rate (%)", 
         marker='o', ms=4, markevery=2,
         path_effects=[path_effects.withStroke(linewidth=5, foreground=C3, alpha=0.15)])
ax2.axhspan(65, 75, alpha=0.12, color=C2)
ax2.text(inv_m.date.iloc[3], 73.5, "Danger Zone: Stockout > 65%", fontsize=12, color=C2, style="italic")
ax2.set_ylabel("Rate (%)"); ax2.set_xlabel("Date")
ax2.legend(fontsize=9, framealpha=0.3); ax2.grid(True, ls="--", alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout(); fig.savefig(OUT/"4a_stockout_bleeding.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 4a")

# ── 4B: Stockout rate by category heatmap ────────────────────────────────────
fig, ax = plt.subplots(figsize=(12,5))
inv_cat = inv.groupby(["category","year"])["stockout_flag"].mean().unstack(fill_value=np.nan)*100
im = ax.imshow(inv_cat.values, cmap="RdYlGn_r", vmin=62, vmax=72, aspect="auto")
cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
cbar.set_label("Stockout Rate (%)", color=TXT, fontsize=9)
cbar.ax.yaxis.set_tick_params(color=TXT); plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TXT)
ax.set_yticks(range(len(inv_cat.index))); ax.set_yticklabels(inv_cat.index, fontsize=10)
ax.set_xticks(range(len(inv_cat.columns))); ax.set_xticklabels(inv_cat.columns, rotation=45, ha="right", fontsize=9)
for i in range(inv_cat.shape[0]):
    for j in range(inv_cat.shape[1]):
        v = inv_cat.values[i,j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8.5,
                    color="black" if 50<v<80 else "white", fontweight="bold")
ax.set_title("Stockout Rate by Category × Year\nStreetwear consistently highest — Safety Buffer Needed", fontsize=12, color=C2, fontweight="bold")
ax.set_ylabel("Category"); ax.set_xlabel("Year")
# Side annotation for priority
ax.annotate("PRIORITY REGIME:\nINVENTORY BUFFER REQUIRED", xy=(10.5, 3), xytext=(11.8, 3),
            va="center", color=C2, fontweight="bold", fontsize=9,
            arrowprops=dict(arrowstyle="->", color=C2, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C2, alpha=0.9))

fig.tight_layout(); fig.savefig(OUT/"4b_stockout_by_category_heatmap.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 4b")

# ── 4C: Sell-through rate vs stockout scatter ─────────────────────────────────
fig, ax = plt.subplots(figsize=(10,6))
inv_prod = inv.groupby(["product_id","category"]).agg(
    sell_through=("sell_through_rate","mean"),
    stockout_rate=("stockout_flag","mean"),
    units_sold=("units_sold","sum")).reset_index()
cats = inv_prod.category.unique()
cols_map = dict(zip(cats, [C1,C2,C3,C4]))
for cat in cats:
    sub = inv_prod[inv_prod.category==cat].sample(min(200,len(inv_prod[inv_prod.category==cat])), random_state=42)
    ax.scatter(sub.sell_through*100, sub.stockout_rate*100, s=sub.units_sold/20+15,
               color=cols_map[cat], alpha=0.5, label=cat, edgecolors="none", lw=0.5)
ax.axvspan(70, 105, ymin=0.65, ymax=1.0, alpha=0.08, color=C2, zorder=0)
ax.axvline(70, color=C4, ls="--", lw=2, alpha=0.8); ax.text(70.5, 92, "70% ST Target", color=C4, fontsize=9, fontweight="bold")
ax.axhline(65, color=C2, ls="--", lw=2, alpha=0.8); ax.text(98, 66.5, "65% Stockout Danger Threshold", ha="right", color=C2, fontsize=10, fontweight="bold")
# Quadrant labels
ax.text(80, 80, "HIGH SELL\nHIGH STOCKOUT\n→ Replenish NOW", ha="center", fontsize=8.5,
        color=C2, fontweight="bold", bbox=dict(boxstyle="round", fc=PANEL, ec=C2, alpha=0.7))
ax.text(20, 30, "LOW SELL\nLOW STOCK\n→ Review & Discontinue", ha="center", fontsize=8.5,
        color=GRID, fontweight="bold", bbox=dict(boxstyle="round", fc=PANEL, ec=GRID, alpha=0.7))
ax.set_xlabel("Sell-Through Rate (%)"); ax.set_ylabel("Stockout Rate (%)")
ax.set_title("SKU Positioning: Sell-Through vs Stockout Rate\nBubble = Units Sold | Identify Critical Replenishment SKUs", fontsize=12, color=C1, fontweight="bold")
ax.legend(fontsize=9, framealpha=0.3); ax.grid(True, ls="--", alpha=0.3)
fig.tight_layout(); fig.savefig(OUT/"4c_sellthrough_vs_stockout.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 4c")

# ── 4D: Safety stock ROI waterfall (proper cumulative) ─────────────────────
fig, ax = plt.subplots(figsize=(10,5))
labels = ["Est. Revenue\nLost (Historical)","Recovery at\n50% Stockout Cut","Safety Stock\nInvestment (Est.)",
          "Net Revenue\nRecovered"]
v1 = total_lost/1e9
v2 = total_lost*0.5/1e9
v3 = total_lost*0.5*0.08/1e9
v4 = v2 - v3

# Bar bottoms and heights for proper waterfall
bottoms = [0, 0, v2, 0]
heights = [v1, v2, v3, v4]
cols_w  = [C2, C3, C2, C4]

for i in range(4):
    b = bottoms[i]
    h = heights[i]
    if i == 2:  # investment bar hangs from top of recovery
        b = v2 - v3
        ax.bar(i, h, bottom=b, color=cols_w[i], alpha=0.85, edgecolor=BG, width=0.55)
        txt = ax.text(i, b + h/2, f"-{v3:.2f}B\nVND", ha="center", va="center", fontsize=9.5, fontweight="bold", color="white")
        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])
    else:
        ax.bar(i, h, bottom=b, color=cols_w[i], alpha=0.85, edgecolor=BG, width=0.55)
        txt = ax.text(i, b + h/2, f"+{h:.2f}B\nVND", ha="center", va="center", fontsize=9.5, fontweight="bold", color="white")
        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

# Connector lines
for i in range(3):
    top_prev = bottoms[i] + heights[i] if i != 2 else v2
    ax.plot([i+0.3, i+0.7], [top_prev if i==0 else v4 if i==2 else v2]*2 if i!=1 else [v2, v2],
            color=GRID, ls="--", lw=1, alpha=0.5)

# ROI annotation
ax.annotate(f"ROI = {v4/v3:.1f}×", xy=(3, v4), xytext=(3, v4+0.5),
            ha="center", fontsize=12, color=C4, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C4, alpha=0.95))

ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("Value (Billion VND)")
ax.set_ylim(0, v1*1.2)
ax.set_title(f"Prescriptive ROI Waterfall: Safety Stock Investment vs Revenue Recovery\nPrescriptive: 50% Stockout Reduction = Net +{v4:.2f}B VND",
             fontsize=12, color=C4, fontweight="bold")
ax.grid(True, axis="y", ls="--", alpha=0.2)
fig.tight_layout(); fig.savefig(OUT/"4d_stockout_roi_waterfall.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 4d — Insight 4 done.")

# ═══════════════════════════════════════════════════════════════════════════
# INSIGHT 5: Traffic Quality Paradox — 4 charts
# ═══════════════════════════════════════════════════════════════════════════
web_d = web.groupby("date").agg(
    total_sessions=("sessions","sum"),
    total_visitors=("unique_visitors","sum"),
    avg_bounce=("bounce_rate","mean"),
    avg_duration=("avg_session_duration_sec","mean")).reset_index()
web_m = web_d.set_index("date").resample("MS").sum().reset_index()
web_m = web_m.merge(sales_m, on="date", how="left")
web_m["conv_proxy"] = web_m.revenue / web_m.total_sessions  # VND per session

# ── 5A: Traffic Source Quality — Horizontal grouped bar (bounce + duration + sessions) ──
fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(15,7), gridspec_kw={"width_ratios":[1,1.2]})

source_agg = web.groupby("traffic_source").agg(
    sessions=("sessions","sum"),
    visitors=("unique_visitors","sum"),
    bounce=("bounce_rate","mean"),
    duration=("avg_session_duration_sec","mean")).reset_index()
source_agg["label"] = source_agg.traffic_source.str.replace("_"," ").str.title()
source_agg = source_agg.sort_values("sessions", ascending=True)

cols_src = [C1,C2,C3,C4,C5,"#FB923C"]
y_pos = np.arange(len(source_agg))

# Left: sessions bar
bars = ax_l.barh(y_pos, source_agg.sessions/1e3, color=cols_src[:len(source_agg)], alpha=0.85, edgecolor=BG, height=0.55)
for i,(_,row) in enumerate(source_agg.iterrows()):
    ax_l.text(row.sessions/1e3+5, y_pos[i], f"{row.sessions/1e3:.0f}K", va="center", fontsize=9.5, color=TXT, fontweight="bold")
ax_l.set_yticks(y_pos); ax_l.set_yticklabels(source_agg.label, fontsize=10)
ax_l.set_xlabel("Total Sessions (K)"); ax_l.set_title("Sessions by Traffic Source\nVolume ≠ Quality", fontsize=11, color=C1, fontweight="bold")
ax_l.grid(True, axis="x", ls="--", alpha=0.3)

# Right: Bounce vs Duration scatter
import matplotlib.patheffects as path_effects

for i,(_,row) in enumerate(source_agg.iterrows()):
    b_val = row.bounce * 100 if row.bounce < 1 else row.bounce
    d_val = row.duration / 60
    size = np.sqrt(row.sessions) * 1.8 + 50
    ax_r.scatter(b_val, d_val, s=size, color=cols_src[i],
               alpha=0.55, edgecolors="white", lw=1.2, zorder=5)
    
    # Manual offsets for overlapping labels
    off_x, off_y = 12, 10
    if row.traffic_source == "paid_search": off_y = -18; off_x = -10
    if row.traffic_source == "social_media": off_y = 18
    
    txt = ax_r.annotate(row.label,
                xy=(b_val, d_val),
                xytext=(off_x, off_y), textcoords="offset points",
                fontsize=9.5, color=cols_src[i], fontweight="bold")
    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

ax_r.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
ax_r.set_xlabel("Bounce Rate — Lower is Better", fontsize=11)
ax_r.set_ylabel("Avg. Session Duration (min) — Higher is Better", fontsize=11)
ax_r.set_title("Quality Matrix: Bounce vs Engagement\nBubble = Volume | Top-left = Best Performance", fontsize=12, color=C3, fontweight="bold")
ax_r.grid(True, ls="--", alpha=0.2)

# Quadrant logic
all_b = [r.bounce*100 if r.bounce < 1 else r.bounce for _,r in source_agg.iterrows()]
all_d = [r.duration/60 for _,r in source_agg.iterrows()]
xmid, ymid = np.mean(all_b), np.mean(all_d)

ax_r.axvline(xmid, color=GRID, ls=":", lw=1.2, alpha=0.4)
ax_r.axhline(ymid, color=GRID, ls=":", lw=1.2, alpha=0.4)

# Set limits with generous padding
b_range = max(all_b) - min(all_b)
d_range = max(all_d) - min(all_d)
ax_r.set_xlim(min(all_b) - b_range*0.7, max(all_b) + b_range*0.7)
ax_r.set_ylim(min(all_d) - d_range*0.7, max(all_d) + d_range*0.7)

# Labels in extreme corners
ax_r.text(0.05, 0.92, "★ Best", transform=ax_r.transAxes, fontsize=11, color=C3, fontweight="bold")
ax_r.text(0.85, 0.05, "Worst ✗", transform=ax_r.transAxes, fontsize=11, color=C2, fontweight="bold")

fig.suptitle("Traffic Source Quality Analysis\nPrescriptive: Reallocate budget from volume to engagement", fontsize=14, color=C4, fontweight="bold")
fig.subplots_adjust(top=0.85, bottom=0.1, left=0.1, right=0.9, wspace=0.35)
fig.savefig(OUT/"5a_traffic_quality_matrix.png", dpi=140)
plt.close()
print("[OK] 5a")

# ── 5B: Revenue per session (VND efficiency) over time ───────────────────────
fig, ax = plt.subplots(figsize=(12,5))
ax2 = ax.twinx()
ax.fill_between(web_m.date, 0, web_m.total_sessions/1e3, alpha=0.25, color=C1, label="Sessions (K)")
ax.plot(web_m.date, web_m.total_sessions/1e3, color=C1, lw=1.5)
ax2.plot(web_m.date, web_m.conv_proxy, color=C4, lw=2.2, marker=".", ms=4, label="Revenue/Session (VND)")
ax2.fill_between(web_m.date, web_m.conv_proxy, alpha=0.15, color=C4)

# Trend
x_n = np.arange(len(web_m))
cf = np.polyfit(x_n[~np.isnan(web_m.conv_proxy)], web_m.conv_proxy.dropna(), 1)
ax2.plot(web_m.date, np.polyval(cf, x_n), "--", color=C2, lw=2, alpha=0.8, label="Efficiency Trend")

ax.set_ylabel("Monthly Sessions (K)", color=C1)
ax2.set_ylabel("Revenue per Session (VND)", color=C4)
ax.tick_params(axis="y", colors=C1); ax2.tick_params(axis="y", colors=C4)
lines = [mpatches.Patch(color=C1, alpha=0.5, label="Sessions"), mpatches.Patch(color=C4, label="Rev/Session"), mpatches.Patch(color=C2, label="Trend")]
ax.legend(handles=lines, fontsize=9, framealpha=0.3)
ax.set_title("Traffic Volume vs Revenue Efficiency\nMore sessions ≠ More revenue — Quality Conversion Matters", fontsize=12, color=C4, fontweight="bold")
ax.grid(True, ls="--", alpha=0.2)
fig.tight_layout(); fig.savefig(OUT/"5b_traffic_efficiency.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 5b")

# ── 5C: Acquisition channel mix (customer signup) ────────────────────────────
customers = pd.read_csv(DATA/"customers.csv", parse_dates=["signup_date"])
fig, (ax1,ax2) = plt.subplots(1,2, figsize=(13,5))

ch_mix = customers.acquisition_channel.value_counts()
cols_ch = [C1,C2,C3,C4,C5,"#FB923C"]
wedges,texts,autos = ax1.pie(ch_mix.values, labels=None, autopct="%1.1f%%",
    colors=cols_ch[:len(ch_mix)], startangle=90, pctdistance=0.78,
    wedgeprops=dict(edgecolor=BG, lw=2))
for at in autos: at.set(fontsize=10, color="white", fontweight="bold")
center = plt.Circle((0,0), 0.58, fc=PANEL)
ax1.add_artist(center)
ax1.text(0, 0.1, f"{customers.shape[0]:,}", ha="center", va="center", fontsize=18, fontweight="bold", color=TXT)
ax1.text(0,-0.18, "Total Customers", ha="center", fontsize=10, color=TXT)
ax1.legend([c.replace("_"," ").title() for c in ch_mix.index], loc="lower center",
           bbox_to_anchor=(0.5,-0.12), ncol=2, fontsize=8.5, framealpha=0.3)
ax1.set_title("Customer Acquisition Mix\nChannel Share of New Customers", fontsize=11, color=C1, fontweight="bold")

# Year-over-year channel shift
customers["year"] = customers.signup_date.dt.year
ch_year = customers.groupby(["year","acquisition_channel"]).size().unstack(fill_value=0)
ch_year_pct = ch_year.div(ch_year.sum(axis=1), axis=0)*100
ch_year_pct.plot(kind="bar", stacked=True, ax=ax2, color=cols_ch[:len(ch_year_pct.columns)], alpha=0.85, edgecolor=BG)
ax2.set_xlabel("Year"); ax2.set_ylabel("Share of New Customers (%)")
ax2.set_title("Acquisition Channel Shift Over Time\nPrescriptive: Invest in highest-LTV channels", fontsize=11, color=C3, fontweight="bold")
ax2.legend(fontsize=8, framealpha=0.3, bbox_to_anchor=(1.01,1), loc="upper left")
ax2.grid(True, axis="y", ls="--", alpha=0.3); ax2.tick_params(axis="x", rotation=45)
fig.tight_layout(); fig.savefig(OUT/"5c_acquisition_channels.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 5c")

# ── 5D: Device type + order source conversion ────────────────────────────────
fig, (ax1,ax2) = plt.subplots(1,2, figsize=(13,5))
dev_agg = orders.groupby("device_type").agg(orders_n=("order_id","count")).reset_index()
cols_dev = [C1,C2,C3,C4]
dev_agg["label"] = dev_agg.device_type.str.replace("_"," ").str.title()
ax1.bar(dev_agg.label, dev_agg.orders_n, color=cols_dev[:len(dev_agg)], alpha=0.85, edgecolor=BG)
for i,(_,row) in enumerate(dev_agg.iterrows()):
    pct = row.orders_n / dev_agg.orders_n.sum() * 100
    ax1.text(i, row.orders_n+2000, f"{row.orders_n:,}\n({pct:.0f}%)", ha="center", fontsize=9.5, color=TXT, fontweight="bold")
ax1.set_ylabel("Number of Orders"); ax1.set_title("Orders by Device Type\nMobile dominance signals UX optimization priority", fontsize=11, color=C1, fontweight="bold")
ax1.set_ylim(0, dev_agg.orders_n.max()*1.25)
ax1.grid(True, axis="y", ls="--", alpha=0.2)

src_agg = orders.groupby("order_source").agg(orders_n=("order_id","count")).sort_values("orders_n", ascending=True).reset_index()
src_agg["label"] = src_agg.order_source.str.replace("_"," ").str.title()
ax2.barh(src_agg.label, src_agg.orders_n, color=[C3 if v==src_agg.orders_n.max() else C1 for v in src_agg.orders_n], alpha=0.85, edgecolor=BG)
for i,(_,row) in enumerate(src_agg.iterrows()):
    txt = ax2.text(row.orders_n+50, i, f"{row.orders_n:,}", va="center", fontsize=9.5, color=TXT, fontweight="bold")
    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])
ax2.set_xlim(0, src_agg.orders_n.max()*1.15)
ax2.set_xlabel("Number of Orders"); ax2.set_title("Orders by Source Channel\nIdentify highest-converting acquisition pathways", fontsize=11, color=C3, fontweight="bold")
ax2.grid(True, axis="x", ls="--", alpha=0.3)
fig.suptitle("Digital Channel Mix Analysis\nPrescriptive: Concentrate budget on Mobile + top-converting sources", fontsize=13, color=C4, fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"5d_device_source_orders.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 5d — Insight 5 done.")
print("\nAll Insights 4+5 charts complete!")
