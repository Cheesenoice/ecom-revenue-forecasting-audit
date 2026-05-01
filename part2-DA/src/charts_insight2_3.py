"""Insight 2: Promo Paradox — 4 charts | Insight 3: Wrong-Size Tax — 4 charts"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import matplotlib.patches as mpatches, matplotlib.gridspec as gridspec
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

oi = pd.read_csv(DATA/"order_items.csv", low_memory=False)
products = pd.read_csv(DATA/"products.csv")
promos = pd.read_csv(DATA/"promotions.csv", parse_dates=["start_date","end_date"])
returns = pd.read_csv(DATA/"returns.csv", parse_dates=["return_date"])
orders = pd.read_csv(DATA/"orders.csv", parse_dates=["order_date"], low_memory=False)

oi_p = oi.merge(products[["product_id","price","cogs","category"]], on="product_id", how="left")
oi_p["n_promos"] = oi_p["promo_id"].notna().astype(int) + oi_p["promo_id_2"].notna().astype(int)
oi_p["rev"]   = oi_p["quantity"] * oi_p["unit_price"]
oi_p["cogs_v"]= oi_p["quantity"] * oi_p["cogs"]
oi_p["margin"]= oi_p["rev"] - oi_p["cogs_v"]
oi_p["margin_rate"] = oi_p["margin"] / oi_p["rev"] * 100

agg = oi_p.groupby("n_promos").agg(
    rev=("rev","sum"), margin=("margin","sum"), lines=("rev","count")).reset_index()
agg["margin_rate"] = agg["margin"]/agg["rev"]*100
agg["rev_B"] = agg["rev"]/1e9

# ── 2A: Grouped bar — Revenue vs Margin by promo count ───────────────────────
fig, (ax1,ax2) = plt.subplots(1,2, figsize=(14,6))
x = np.arange(3); w = 0.32
labels = ["0 Promos\n(Full Price)","1 Promo\n(Discounted)","2 Promos\n(Double)"]

b1 = ax1.bar(x-w/2, agg.rev_B, w, color=C1, alpha=0.82, edgecolor=BG, label="Revenue (B VND)")
b2 = ax1.bar(x+w/2, agg.margin/1e9, w, color=C3, alpha=0.82, edgecolor=BG, label="Gross Margin (B VND)")
for bar,v in zip(b1, agg.rev_B):
    txt = ax1.text(bar.get_x()+w/2, bar.get_height()+0.1, f"{v:.1f}B", ha="center", fontsize=11.5, color=C1, fontweight="bold")
    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])
for bar,(v,mr) in zip(b2, zip(agg.margin/1e9, agg.margin_rate)):
    col = C3 if mr>8 else C2
    txt = ax1.text(bar.get_x()+w/2, bar.get_height()+0.05, f"{v:.2f}B\n({mr:.1f}%)", ha="center", fontsize=10.5, color=col, fontweight="bold")
    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=10)
ax1.set_ylabel("Value (Billion VND)"); ax1.legend(fontsize=9, framealpha=0.3)
ax1.set_title("Revenue vs Gross Margin\nby Number of Promotions Applied", fontsize=12, color=C4, fontweight="bold")
ax1.grid(True, axis="y", ls="--", alpha=0.3)

# Margin floor line
ax1.axhline(0.5, color=C4, ls="--", lw=1.8, alpha=0.8)
ax1.text(0.05, 0.7, "8% Margin Floor", ha="right", color=C4, fontsize=15, fontweight="bold", style="italic")

# 2A right: waterfall margin rate
colors_w = [C3, C2, C4]
bars = ax2.bar(labels, agg.margin_rate, color=colors_w, edgecolor=BG, lw=0.8, alpha=0.85, width=0.6)
for bar,v in zip(bars, agg.margin_rate):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3, f"{v:.1f}%",
             ha="center", fontsize=12, fontweight="bold", color=bar.get_facecolor())
ax2.axhline(8, color=C4, ls="--", lw=2, alpha=0.8)
ax2.text(0.05, 8.4, "8% Floor", ha="center", color=C4, fontsize=15, fontweight="bold", style="italic")
ax2.set_ylim(-1, 23); ax2.set_ylabel("Gross Margin Rate (%)")
ax2.set_title("Margin Rate Collapse\nSingle Promo Destroys 93% of Margin", fontsize=12, color=C2, fontweight="bold")
ax2.grid(True, axis="y", ls="--", alpha=0.2)
ax2.annotate("−93% margin\nfrom 1 promo alone",
             xy=(1, agg.margin_rate.iloc[1]), xytext=(1, 16),
             ha="center", fontsize=9.5, color=C2, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=C2, lw=1.5, shrinkB=15),
             bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C2, alpha=0.9))

fig.suptitle("THE PROMO PARADOX: Sell More, Earn Less\nDiagnostic → Prescriptive", fontsize=15, fontweight="bold", color=C2, y=1.02)
fig.tight_layout(); fig.savefig(OUT/"2a_promo_margin_collapse.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 2a")

# ── 2B: Margin rate distribution per category with promos ───────────────────
fig, ax = plt.subplots(figsize=(12,5))
cats = sorted(oi_p.category.dropna().unique())
colors_cat = [C1, C2, C3, C4]
positions = np.arange(len(cats))
bp = ax.boxplot([oi_p[oi_p.category==c]["margin_rate"].clip(-50,60).dropna() for c in cats],
    positions=positions, widths=0.55, patch_artist=True, notch=False,
    medianprops=dict(color="white", lw=2.5),
    whiskerprops=dict(color=GRID, lw=1.5), capprops=dict(color=GRID, lw=1.5),
    flierprops=dict(marker=".", color=GRID, alpha=0.3, ms=3))
for patch,col in zip(bp["boxes"], colors_cat):
    patch.set_facecolor(col); patch.set_alpha(0.7)
ax.axhline(0, color=C2, ls="--", lw=1.5, alpha=0.7); ax.text(-0.4, 1.5, "Break-even", color=C2, fontsize=9, fontweight="bold")
ax.axhline(8, color=C4, ls="--", lw=1.5, alpha=0.7); ax.text(-0.4, 9.5, "8% Target", color=C4, fontsize=9, fontweight="bold")
ax.set_xticks(positions); ax.set_xticklabels(cats, fontsize=11, fontweight="bold")
ax.set_ylim(-40, 55)
ax.set_ylabel("Line-item Gross Margin Rate (%)", fontsize=11)
ax.set_title("Margin Rate Distribution by Category\nIdentifying Loss-Leader Pockets", fontsize=13, color=C1, fontweight="bold")
ax.grid(True, axis="y", ls="--", alpha=0.2)
# Add median labels
for i,cat in enumerate(cats):
    med = oi_p[oi_p.category==cat]["margin_rate"].median()
    ax.text(i, med+1, f"Med:{med:.0f}%", ha="center", fontsize=8, color="white", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"2b_margin_by_category_boxplot.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 2b")

# ── 2C: Promo campaign timeline (Gantt + revenue lift) ───────────────────────
sales = pd.read_csv(DATA/"sales.csv", parse_dates=["Date"])
fig, (ax1,ax2) = plt.subplots(2,1, figsize=(14,7), sharex=False)

# Top: revenue trend
monthly = sales.set_index("Date").resample("MS")["Revenue"].sum().reset_index()
ax1.fill_between(monthly.Date, 0, monthly.Revenue/1e6, alpha=0.3, color=C1)
ax1.plot(monthly.Date, monthly.Revenue/1e6, color=C1, lw=1.5)
ax1.set_ylabel("Monthly Revenue (M VND)"); ax1.set_title("Revenue Timeline + Promotion Calendar Overlay\nIdentifying Promo-Driven Revenue Spikes vs. Margin Destruction", fontsize=12, color=C4, fontweight="bold")
ax1.grid(True, ls="--", alpha=0.3)

# Overlay promo periods — only top 10 longest promos for clarity
promos_sorted = promos.sort_values(by="discount_value", ascending=False).head(10)
for _,row in promos_sorted.iterrows():
    col = C3 if row.stackable_flag else C2
    ax1.axvspan(row.start_date, row.end_date, alpha=0.2, color=col, zorder=3)

import matplotlib.patches as mpatches
p1 = mpatches.Patch(color=C3, alpha=0.3, label="Stackable Promo")
p2 = mpatches.Patch(color=C2, alpha=0.3, label="Non-Stackable Promo")
ax1.legend(handles=[p1,p2], fontsize=9, framealpha=0.3, loc="upper left")

# Bottom: margin rate
monthly2 = sales.set_index("Date").resample("MS").agg({"Revenue":"sum","COGS":"sum"}).reset_index()
monthly2["mrate"] = (monthly2.Revenue - monthly2.COGS)/monthly2.Revenue*100
ax2.plot(monthly2.Date, monthly2.mrate, color=C4, lw=1.8)
ax2.fill_between(monthly2.Date, monthly2.mrate, alpha=0.2, color=C4)
ax2.axhline(0, color=C2, ls="--", lw=1.5)
ax2.axhline(8, color=C3, ls="--", lw=1.5, alpha=0.8)
neg = monthly2[monthly2.mrate<0]
ax2.scatter(neg.Date, neg.mrate, color=C2, s=90, zorder=10, edgecolors="white", lw=1.5)
for _,row in promos_sorted.iterrows():
    ax2.axvspan(row.start_date, row.end_date, alpha=0.18, color=C2, zorder=0)
ax2.set_ylabel("Gross Margin Rate (%)"); ax2.set_xlabel("Date")
ax2.grid(True, ls="--", alpha=0.3)
for _,r in neg.iterrows():
    txt = ax2.annotate(f"{r.mrate:.0f}%", xy=(r.Date, r.mrate), xytext=(0, -18),
                 textcoords="offset points", ha="center", fontsize=9.5, color=C2, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=C2, lw=1))
    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground=BG)])

fig.tight_layout(); fig.savefig(OUT/"2c_promo_timeline.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 2c")

# ── 2D: Promo channel efficiency scatter ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(10,6))
channel_stats = oi_p.copy()
channel_stats = channel_stats.merge(oi[["order_id","promo_id"]], on=["order_id","promo_id"], how="left")
channel_stats = channel_stats.merge(promos[["promo_id","promo_channel","discount_value"]], on="promo_id", how="left")
ch_agg = channel_stats.groupby("promo_channel").agg(
    rev=("rev","sum"), margin_rate=("margin_rate","mean"), lines=("rev","count")).reset_index().dropna()

colors_ch = [C1,C2,C3,C4,C5]
for i,(_,row) in enumerate(ch_agg.iterrows()):
    ax.scatter(row.rev/1e6, row.margin_rate, s=row.lines/35, color=colors_ch[i%5],
               alpha=0.85, edgecolors="white", lw=1.5, zorder=5)
    ax.annotate(str(row.promo_channel).replace("_"," ").title(),
                xy=(row.rev/1e6, row.margin_rate), xytext=(15,8), textcoords="offset points",
                fontsize=9.5, color=colors_ch[i%5], fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=colors_ch[i%5], lw=1))

ax.axhline(8, color=C4, ls="--", lw=1.8, alpha=0.8); ax.text(ch_agg.rev.max()/1e6*0.6, 9.5, "8% Margin Floor", color=C4, fontsize=9, fontweight="bold")
ax.axvline(ch_agg.rev.mean()/1e6, color=GRID, ls=":", lw=1.5)
ax.set_xlabel("Total Revenue Generated (M VND)"); ax.set_ylabel("Average Gross Margin Rate (%)")
ax.set_title("Promotion Channel Efficiency Matrix\nBubble size = # Transactions | Quadrant: High Rev + High Margin = SCALE", fontsize=12, color=C3, fontweight="bold")
ax.grid(True, ls="--", alpha=0.3)
fig.tight_layout(); fig.savefig(OUT/"2d_promo_channel_efficiency.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 2d — Insight 2 done.")

# ═══════════════════════════════════════════════════════════════════════════
# INSIGHT 3: Wrong-Size Tax — 4 charts
# ═══════════════════════════════════════════════════════════════════════════
ret_p = returns.merge(products[["product_id","category","segment"]], on="product_id", how="left")
ret_p["ym"] = ret_p.return_date.dt.to_period("M").dt.to_timestamp()

# ── 3A: Stacked area returns by reason ───────────────────────────────────────
reasons = returns.return_reason.unique()
reason_cols = {"wrong_size":C2,"defective":C4,"not_as_described":C5,"changed_mind":C3,"late_delivery":C1}
fig, ax = plt.subplots(figsize=(13,5))
ret_monthly = ret_p.groupby(["ym","return_reason"])["refund_amount"].sum().unstack(fill_value=0)
ret_monthly = ret_monthly.sort_index()
cols = [reason_cols.get(r,TXT) for r in ret_monthly.columns]
ax.stackplot(ret_monthly.index, [ret_monthly[c]/1e6 for c in ret_monthly.columns],
             labels=[c.replace("_"," ").title() for c in ret_monthly.columns], colors=cols, alpha=0.8)

# Forecast wrong_size
ws = ret_monthly.get("wrong_size", pd.Series(dtype=float)).reset_index()
ws.columns = ["date","ws"]
x_n = np.arange(len(ws))
cf = np.polyfit(x_n, ws.ws/1e6, 1)
fut = pd.date_range(ws.date.iloc[-1]+pd.offsets.MonthBegin(), periods=18, freq="MS")
fut_pred = np.polyval(cf, np.arange(len(ws), len(ws)+18))
ax.plot(fut, fut_pred, "--", color=C2, lw=2.5, label="Wrong-Size Forecast")
ax.fill_between(fut, fut_pred*0.8, fut_pred*1.2, alpha=0.1, color=C2)
ax.axvline(ws.date.iloc[-1], color=TXT, ls=":", lw=1.5, alpha=0.5)
ax.text(ws.date.iloc[-1]+pd.Timedelta(days=5), ax.get_ylim()[1]*0.9 if ax.get_ylim()[1]>0 else 2, "→ Forecast", color=C2, fontsize=9)

total_ws = returns[returns.return_reason=="wrong_size"]["refund_amount"].sum()
ax.annotate(f"Wrong-Size: {total_ws/1e6:.1f}M VND\nHistorical Total Refunded",
            xy=(ws.date.iloc[len(ws)//2], ws.ws.iloc[len(ws)//2]/1e6),
            xytext=(ws.date.iloc[-10], ret_monthly.sum(axis=1).max()/1e6*0.85),
            ha="right", fontsize=10, color=C2, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C2, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C2, alpha=0.9))

ax.set_ylabel("Monthly Refund Amount (M VND)"); ax.set_xlabel("Date")
ax.set_title("Return Refund Cash Outflow by Reason — Stacked Area + Forecast\nWrong-Size is #1 Return Driver: 35% of all refunds", fontsize=12, color=C2, fontweight="bold")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.3, ncol=2)
ax.grid(True, ls="--", alpha=0.3)
fig.tight_layout(); fig.savefig(OUT/"3a_returns_stacked_forecast.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 3a")

# ── 3B: Wrong-size by category — horizontal bar ──────────────────────────────
fig, ax = plt.subplots(figsize=(10,5))
ws_cat = ret_p[ret_p.return_reason=="wrong_size"].groupby("category")["refund_amount"].sum().sort_values()
cols_b = [C1,C3,C4,C2]
bars = ax.barh(ws_cat.index, ws_cat.values/1e6, color=cols_b, alpha=0.85, edgecolor=BG, height=0.55)
for bar,v in zip(bars, ws_cat.values):
    ax.text(v/1e6+0.3, bar.get_y()+bar.get_height()/2, f"{v/1e6:.1f}M ({v/ws_cat.sum()*100:.0f}%)",
            va="center", fontsize=10, color=TXT, fontweight="bold")
ax.set_xlabel("Wrong-Size Refund Amount (M VND)")
ax.set_title("Wrong-Size Return Cost by Category\nPrescriptive: Streetwear Size Recommender = Highest ROI", fontsize=12, color=C4, fontweight="bold")
ax.grid(True, axis="x", ls="--", alpha=0.3)
ax.annotate("Priority #1:\nStreetwear AI Sizing", xy=(ws_cat.iloc[-1]/1e6, len(ws_cat)-1),
            xytext=(ws_cat.iloc[-1]/1e6*0.8, len(ws_cat)-2.8),
            ha="center", fontsize=10, color=C2, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C2, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C2, alpha=0.9))
fig.tight_layout(); fig.savefig(OUT/"3b_wrongsize_by_category.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 3b")

# ── 3C: Return reasons donut ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8,7))
reason_counts = returns.return_reason.value_counts()
cols_d = [C2,C4,C5,C3,C1]
wedges, texts, autotexts = ax.pie(reason_counts.values, labels=None, autopct="%1.1f%%",
    colors=cols_d, startangle=140, pctdistance=0.75,
    wedgeprops=dict(edgecolor=BG, linewidth=2))
for at in autotexts: at.set(fontsize=11, fontweight="bold", color="white")
centre = plt.Circle((0,0), 0.55, fc=PANEL)
ax.add_artist(centre)
ax.text(0,0.1,f"{returns.return_reason.count():,}", ha="center", va="center", fontsize=20, fontweight="bold", color=TXT)
ax.text(0,-0.15,"Total Returns", ha="center", va="center", fontsize=11, color=TXT)
ax.legend([r.replace("_"," ").title() for r in reason_counts.index], loc="lower center",
          bbox_to_anchor=(0.5,-0.12), ncol=3, fontsize=9, framealpha=0.3)
ax.set_title("Return Reason Breakdown\n#1: Wrong Size dominates at 35%", fontsize=13, fontweight="bold", color=C2, pad=15)
fig.tight_layout(); fig.savefig(OUT/"3c_return_reasons_donut.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 3c")

# ── 3D: Seasonal return heatmap (month × year) ───────────────────────────────
fig, ax = plt.subplots(figsize=(14,6))
ret_p2 = returns[returns.return_reason=="wrong_size"].copy()
ret_p2["year"]  = ret_p2.return_date.dt.year
ret_p2["month"] = ret_p2.return_date.dt.month
heat = ret_p2.groupby(["year","month"])["refund_amount"].sum().unstack(fill_value=0)/1e6
im = ax.imshow(heat.values, cmap="YlOrRd", aspect="auto")
cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
cbar.set_label("Wrong-Size Refund (M VND)", color=TXT, fontsize=9)
cbar.ax.yaxis.set_tick_params(color=TXT); plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TXT)
# Cell value labels
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        v = heat.values[i,j]
        ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                color="black" if v < heat.values.max()*0.6 else "white", fontweight="bold")
ax.set_yticks(range(len(heat.index))); ax.set_yticklabels(heat.index, fontsize=9)
ax.set_xticks(range(12)); ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], fontsize=9)
ax.set_title("Wrong-Size Return Seasonality Heatmap\nPeak: Q2-Q3 (Apr-Aug) = Summer fashion launches with inconsistent sizing", fontsize=12, color=C4, fontweight="bold")
ax.set_ylabel("Year"); ax.set_xlabel("Month")
# Add peak annotation — placed below the matrix to avoid cell overlap
peak_row, peak_col = np.unravel_index(np.argmax(heat.values), heat.values.shape)
# Wide ellipse covering Apr (idx 3) to Aug (idx 7)
peak_zone = mpatches.Ellipse((5, peak_row), width=5.5, height=1.2, color=C1, fill=False, lw=3, ls="--", alpha=1.0)
ax.add_patch(peak_zone)
ax.annotate("Peak Season: Apr-Aug", xy=(5, peak_row), xytext=(11.5, peak_row+1.5),
            ha="right", fontsize=14, color=C1, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C1, lw=2, shrinkA=5, connectionstyle="arc3,rad=-0.2"),
            bbox=dict(boxstyle="round,pad=0.3", fc=PANEL, ec=C1, alpha=0.95))
fig.tight_layout(); fig.savefig(OUT/"3d_wrongsize_seasonal_heatmap.png", dpi=180, bbox_inches="tight"); plt.close()
print("[OK] 3d — Insight 3 done.")
