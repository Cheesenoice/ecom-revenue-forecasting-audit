"""
Step 4: Report Charts for LaTeX Appendix
==========================================
Generates publication-quality figures for the Part 3 technical report.

Charts:
  1. feature_importance_top20.png  — LightGBM gain importance (Top 20)
  2. walkforward_cv_timeline.png   — Walk-forward validation splits
  3. pipeline_architecture.png     — 3-step pipeline flowchart
  4. monthly_revenue_shape.png     — Monthly seasonality pattern

Usage: python src/step4_report_charts.py
Output: output/charts/
"""

import sys, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, OUTPUT_DIR, RANDOM_SEED

warnings.filterwarnings("ignore")
np.random.seed(RANDOM_SEED)

CHART_DIR = OUTPUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# ─── Style ──────────────────────────────────────────────────────────────────
DARK_BG    = "#0D1117"
CARD_BG    = "#161B22"
ACCENT1    = "#58A6FF"   # Blue
ACCENT2    = "#F78166"   # Orange
ACCENT3    = "#3FB950"   # Green
ACCENT4    = "#D2A8FF"   # Purple
ACCENT5    = "#FF7B72"   # Red
GOLD       = "#FFC83D"
TEXT_COLOR  = "#E6EDF3"
GRID_COLOR  = "#30363D"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": CARD_BG,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "text.color": TEXT_COLOR,
    "xtick.color": TEXT_COLOR,
    "ytick.color": TEXT_COLOR,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.3,
    "font.size": 11,
    "font.family": "sans-serif",
})

DPI = 160


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FEATURE IMPORTANCE (Top 20)
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("STEP 4 - GENERATING REPORT CHARTS")
print("=" * 60)

print("\n[4.1] Feature Importance (Top 20)...")

imp_df = pd.read_csv(OUTPUT_DIR / "feature_importance.csv")
top20 = imp_df.head(20).iloc[::-1]  # Reverse for horizontal bar

# Color by category
def get_color(feat):
    if "tet" in feat.lower():
        return ACCENT5
    elif "promo" in feat.lower() or "discount" in feat.lower() or "stackable" in feat.lower():
        return ACCENT4
    elif "sin_" in feat or "cos_" in feat:
        return ACCENT1
    else:
        return ACCENT3

colors = [get_color(f) for f in top20["feature"]]

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(range(len(top20)), top20["importance"], color=colors, height=0.7, edgecolor="none")

ax.set_yticks(range(len(top20)))
ax.set_yticklabels([f.replace("_", " ") for f in top20["feature"]], fontsize=9)
ax.set_xlabel("LightGBM Gain Importance", fontsize=12, fontweight="bold")
ax.set_title("Top-20 Feature Importance\nRevenue Forecasting Model", fontsize=14, fontweight="bold", pad=15)
ax.grid(axis="x", alpha=0.2)

# Value labels
for bar, val in zip(bars, top20["importance"]):
    ax.text(val + 500, bar.get_y() + bar.get_height()/2,
            f"{val:,.0f}", va="center", fontsize=8, color=TEXT_COLOR)

# Legend
legend_items = [
    mpatches.Patch(color=ACCENT3, label="Calendar / Temporal"),
    mpatches.Patch(color=ACCENT1, label="Cyclical Encoding"),
    mpatches.Patch(color=ACCENT5, label="Tet Features"),
    mpatches.Patch(color=ACCENT4, label="Promotion Features"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=9,
          facecolor=CARD_BG, edgecolor=GRID_COLOR, framealpha=0.9)

plt.tight_layout()
plt.savefig(CHART_DIR / "feature_importance_top20.png", dpi=DPI, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("  [OK] feature_importance_top20.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. WALK-FORWARD CV TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4.2] Walk-Forward CV Timeline...")

fig, ax = plt.subplots(figsize=(12, 4))

# Define periods
years = list(range(2013, 2025))
year_labels = [str(y) for y in years]

# Background: regime zones
ax.axvspan(2013, 2019, alpha=0.08, color=ACCENT3, zorder=0)
ax.axvspan(2019, 2022, alpha=0.08, color=ACCENT5, zorder=0)
ax.axvspan(2023, 2025, alpha=0.08, color=ACCENT1, zorder=0)

# Regime labels
ax.text(2016, 3.8, "Pre-COVID\n(Training Data)", ha="center", fontsize=10,
        color=ACCENT3, fontweight="bold", alpha=0.8)
ax.text(2020.5, 3.8, "COVID\n(Excluded)", ha="center", fontsize=10,
        color=ACCENT5, fontweight="bold", alpha=0.8)
ax.text(2024, 3.8, "Test\nPeriod", ha="center", fontsize=10,
        color=ACCENT1, fontweight="bold", alpha=0.8)

# Fold bars
fold_data = [
    ("Fold 1", 2013, 2017, 2017, 2018, ACCENT1),
    ("Fold 2", 2013, 2018, 2018, 2018.5, ACCENT4),
    ("Fold 3", 2013, 2018.5, 2018.5, 2019, GOLD),
]

for i, (name, tr_start, tr_end, val_start, val_end, color) in enumerate(fold_data):
    y = 2.5 - i * 0.8
    # Train bar
    ax.barh(y, tr_end - tr_start, left=tr_start, height=0.5,
            color=color, alpha=0.4, edgecolor=color, linewidth=1.5)
    ax.text((tr_start + tr_end)/2, y, "Train", ha="center", va="center",
            fontsize=8, fontweight="bold", color=TEXT_COLOR)
    # Val bar
    ax.barh(y, val_end - val_start, left=val_start, height=0.5,
            color=color, alpha=0.9, edgecolor="white", linewidth=1.5)
    ax.text((val_start + val_end)/2, y, "Val", ha="center", va="center",
            fontsize=8, fontweight="bold", color=DARK_BG)
    # Label
    ax.text(tr_start - 0.15, y, name, ha="right", va="center", fontsize=10,
            fontweight="bold", color=color)

# Test period arrow
ax.annotate("", xy=(2024.5, 0.4), xytext=(2023, 0.4),
            arrowprops=dict(arrowstyle="->", color=ACCENT1, lw=2.5))
ax.text(2023.75, 0.65, "548 days forecast", ha="center", fontsize=9,
        color=ACCENT1, fontweight="bold")

ax.set_xlim(2012.5, 2025)
ax.set_ylim(-0.2, 4.2)
ax.set_xticks(years)
ax.set_xticklabels(year_labels, fontsize=9)
ax.set_yticks([])
ax.set_title("Walk-Forward Cross-Validation Strategy\nTemporal Splits on Pre-COVID Data Only",
             fontsize=13, fontweight="bold", pad=15)
ax.grid(axis="x", alpha=0.15)

plt.tight_layout()
plt.savefig(CHART_DIR / "walkforward_cv_timeline.png", dpi=DPI, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("  [OK] walkforward_cv_timeline.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PIPELINE ARCHITECTURE FLOWCHART
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4.3] Pipeline Architecture...")

fig, ax = plt.subplots(figsize=(14, 5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 5)
ax.axis("off")

def draw_box(ax, x, y, w, h, text, color, fontsize=10, subtext=None):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                         facecolor=color, edgecolor="white", linewidth=1.5, alpha=0.85)
    ax.add_patch(box)
    if subtext:
        ax.text(x + w/2, y + h*0.62, text, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color="white")
        ax.text(x + w/2, y + h*0.30, subtext, ha="center", va="center",
                fontsize=fontsize-2, color="white", alpha=0.8)
    else:
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color="white")

def draw_arrow(ax, x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color="white", lw=2, mutation_scale=15))

# Data sources
draw_box(ax, 0.3, 3.5, 2.2, 1.2, "Raw Data", "#1F6FEB",
         subtext="sales.csv\npromotions.csv")

# Step 1
draw_box(ax, 3.5, 3.5, 2.5, 1.2, "Step 1", ACCENT3,
         subtext="Feature Engineering\n55 features")
draw_arrow(ax, 2.5, 4.1, 3.5, 4.1)

# Step 2
draw_box(ax, 7.0, 3.5, 2.5, 1.2, "Step 2", ACCENT4,
         subtext="Model Training\nLGB + XGB Ensemble")
draw_arrow(ax, 6.0, 4.1, 7.0, 4.1)

# Step 3
draw_box(ax, 10.5, 3.5, 2.5, 1.2, "Step 3", ACCENT5,
         subtext="Post-Processing\nBlend + Calibrate")
draw_arrow(ax, 9.5, 4.1, 10.5, 4.1)

# Feature families (below Step 1)
for i, (name, color) in enumerate([
    ("Temporal\n~35 feat", ACCENT1),
    ("Tet\n~5 feat", ACCENT5),
    ("Promo\n~15 feat", ACCENT4),
]):
    x = 3.5 + i * 0.85
    draw_box(ax, x, 1.8, 0.8, 0.9, name, color, fontsize=7)
draw_arrow(ax, 4.75, 3.5, 4.75, 2.7)

# Model details (below Step 2)
for i, (name, color) in enumerate([
    ("LightGBM\n65.5%", ACCENT1),
    ("XGBoost\n34.5%", ACCENT2),
]):
    x = 7.2 + i * 1.2
    draw_box(ax, x, 1.8, 1.0, 0.9, name, color, fontsize=8)
draw_arrow(ax, 8.25, 3.5, 8.25, 2.7)

# Post-process details (below Step 3)
for i, (name, color) in enumerate([
    ("ML+SS\n50/50", ACCENT1),
    ("Monthly\nCalibrate", GOLD),
]):
    x = 10.5 + i * 1.3
    draw_box(ax, x, 1.8, 1.1, 0.9, name, color, fontsize=8)
draw_arrow(ax, 11.75, 3.5, 11.75, 2.7)

# Walk-forward CV (below models)
draw_box(ax, 7.0, 0.3, 2.5, 1.0, "Walk-Forward CV", "#30363D",
         subtext="3 Folds (2017-2018)")
draw_arrow(ax, 8.25, 1.8, 8.25, 1.3)

# Output
draw_box(ax, 10.5, 0.3, 2.5, 1.0, "submission.csv", "#1F6FEB",
         subtext="548 days\nRevenue + COGS")
draw_arrow(ax, 11.75, 1.8, 11.75, 1.3)

ax.set_title("Reproducible 3-Step Forecasting Pipeline\npython run_all.py (~3 min, CPU only)",
             fontsize=14, fontweight="bold", pad=15, color=TEXT_COLOR)

plt.tight_layout()
plt.savefig(CHART_DIR / "pipeline_architecture.png", dpi=DPI, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("  [OK] pipeline_architecture.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MONTHLY REVENUE SHAPE (Pre-COVID vs Forecast)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4.4] Monthly Revenue Shape...")

df_sales = pd.read_csv(DATA_DIR / "sales.csv", parse_dates=["Date"])
df_sub   = pd.read_csv(OUTPUT_DIR / "submission.csv", parse_dates=["Date"])

# Pre-COVID monthly shape
pre_covid = df_sales[(df_sales["Date"] >= "2013-01-01") & (df_sales["Date"] <= "2018-12-31")]
monthly_pre = pre_covid.groupby(pre_covid["Date"].dt.month)["Revenue"].mean()
monthly_pre_norm = monthly_pre / monthly_pre.mean()

# Forecast monthly shape
monthly_fc = df_sub.groupby(df_sub["Date"].dt.month)["Revenue"].mean()
monthly_fc_norm = monthly_fc / monthly_fc.mean()

fig, ax = plt.subplots(figsize=(10, 5))

months = range(1, 13)
month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ax.bar([m - 0.2 for m in months], monthly_pre_norm.values, width=0.35,
       color=ACCENT1, alpha=0.8, label="Pre-COVID (2013-2018)", edgecolor="none")
ax.bar([m + 0.2 for m in months], monthly_fc_norm.reindex(months).fillna(0).values, width=0.35,
       color=ACCENT2, alpha=0.8, label="Forecast (2023-2024)", edgecolor="none")

ax.axhline(y=1.0, color=TEXT_COLOR, linestyle="--", alpha=0.3, linewidth=1)
ax.text(12.5, 1.02, "Mean", fontsize=8, color=TEXT_COLOR, alpha=0.5)

ax.set_xticks(list(months))
ax.set_xticklabels(month_names, fontsize=10)
ax.set_ylabel("Relative Revenue Index\n(1.0 = monthly mean)", fontsize=11)
ax.set_title("Monthly Revenue Seasonality: Pre-COVID vs Forecast\nQ2 Peak (1.5x) → Q4 Trough (0.6x)",
             fontsize=13, fontweight="bold", pad=15)
ax.legend(fontsize=10, loc="upper right", facecolor=CARD_BG, edgecolor=GRID_COLOR)
ax.grid(axis="y", alpha=0.2)
ax.set_xlim(0.4, 12.8)

# Annotate key months
for m, v in zip(months, monthly_pre_norm.values):
    if v > 1.3 or v < 0.7:
        ax.text(m - 0.2, v + 0.03, f"{v:.2f}", ha="center", fontsize=7,
                color=ACCENT1, fontweight="bold")

plt.tight_layout()
plt.savefig(CHART_DIR / "monthly_revenue_shape.png", dpi=DPI, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("  [OK] monthly_revenue_shape.png")


# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[OK] STEP 4 COMPLETE - 4 charts saved to {CHART_DIR}")
print(f"  1. feature_importance_top20.png")
print(f"  2. walkforward_cv_timeline.png")
print(f"  3. pipeline_architecture.png")
print(f"  4. monthly_revenue_shape.png")
