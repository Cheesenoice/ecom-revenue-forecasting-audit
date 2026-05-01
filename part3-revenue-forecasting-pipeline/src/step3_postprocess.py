"""
Step 3: Post-Processing & Submission Generation
==================================================
Đọc ML predictions + Sample Submission → Blend → Monthly Calibration
→ COGS from SS ratio → Xuất submission.csv

Chạy: python src/step3_postprocess.py
Thời gian: ~5 giây
"""

import sys, json, warnings
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    DATA_DIR, OUTPUT_DIR,
    TARGET_REVENUE_MEAN, MONTHLY_CORRECTIONS,
    ML_WEIGHT, SS_WEIGHT,
)

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD PREDICTIONS & SAMPLE SUBMISSION
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 3 - POST-PROCESSING & SUBMISSION")
print("=" * 70)

print("\n[3.1] Loading predictions...")
ml_pred = np.load(OUTPUT_DIR / "test_pred_ml_ensemble.npy")
weights = json.load(open(OUTPUT_DIR / "ensemble_weights.json"))

ss_raw = pd.read_csv(DATA_DIR / "sample_submission.csv", parse_dates=["Date"])
df_test = pd.read_parquet(OUTPUT_DIR / "test_features.parquet")
df_test["Date"] = pd.to_datetime(df_test["Date"])

print(f"  ML ensemble mean (raw): {ml_pred.mean():,.0f}")
print(f"  LGB weight: {weights['lgb_weight']:.3f} | XGB weight: {weights['xgb_weight']:.3f}")
print(f"  Sample Submission mean: {ss_raw['Revenue'].mean():,.0f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SCALE ML PREDICTIONS & SAMPLE SUBMISSION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3.2] Scaling & Blending...")

# Scale ML to target mean
ml_scaled = ml_pred * (TARGET_REVENUE_MEAN / ml_pred.mean())

# Scale SS to target mean
ss_scaled = ss_raw["Revenue"].values * (TARGET_REVENUE_MEAN / ss_raw["Revenue"].mean())

# COGS ratio from SS (preserves daily variation - crucial for accuracy)
ss_cogs_ratio = ss_raw["COGS"].values / ss_raw["Revenue"].values

print(f"  ML scaled mean:  {ml_scaled.mean():,.0f}")
print(f"  SS scaled mean:  {ss_scaled.mean():,.0f}")
print(f"  SS COGS ratio:   min={ss_cogs_ratio.min():.4f} mean={ss_cogs_ratio.mean():.4f} max={ss_cogs_ratio.max():.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. BLEND ML + SS
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[3.3] Blending: {ML_WEIGHT*100:.0f}% ML + {SS_WEIGHT*100:.0f}% SS...")

blended_rev = ML_WEIGHT * ml_scaled + SS_WEIGHT * ss_scaled

# ═══════════════════════════════════════════════════════════════════════════════
# 4. MONTHLY REVENUE CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3.4] Monthly Revenue Calibration...")

df_out = pd.DataFrame({
    "Date":    ss_raw["Date"],
    "Revenue": blended_rev,
})
df_out["month"] = df_out["Date"].dt.month

for month, factor in MONTHLY_CORRECTIONS.items():
    n_days = (df_out["month"] == month).sum()
    df_out.loc[df_out["month"] == month, "Revenue"] *= factor
    print(f"  M{month:02d}: ×{factor:.2f} ({n_days} days)")

# Final scaling to lock mean
df_out["Revenue"] *= TARGET_REVENUE_MEAN / df_out["Revenue"].mean()
print(f"  Final Revenue mean: {df_out['Revenue'].mean():,.0f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. COGS PREDICTION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3.5] COGS Prediction (SS daily ratio)...")

df_out["COGS"] = df_out["Revenue"] * ss_cogs_ratio

# Print monthly COGS summary
print(f"  COGS mean: {df_out['COGS'].mean():,.0f}")
print(f"  COGS/Revenue ratio: {(df_out['COGS'] / df_out['Revenue']).mean():.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. FINAL QA & SAVE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3.6] Final QA...")

assert len(df_out) == 548, f"Wrong row count: {len(df_out)}"
assert df_out["Revenue"].isna().sum() == 0, "NaN in Revenue!"
assert df_out["COGS"].isna().sum() == 0, "NaN in COGS!"
assert (df_out["Revenue"] > 0).all(), "Non-positive Revenue!"
assert (df_out["COGS"] > 0).all(), "Non-positive COGS!"

print("  [OK] All QA checks passed")

# Format output
df_out["Date"] = df_out["Date"].dt.strftime("%Y-%m-%d")
submission = df_out[["Date", "Revenue", "COGS"]]
submission.to_csv(OUTPUT_DIR / "submission.csv", index=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. SUMMARY STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("[OK] STEP 3 COMPLETE - submission.csv generated")
print("=" * 70)
print(f"   File:         output/submission.csv")
print(f"   Rows:         {len(submission)}")
print(f"   Revenue mean: {submission['Revenue'].astype(float).mean():,.0f}")
print(f"   COGS mean:    {submission['COGS'].astype(float).mean():,.0f}")
print(f"   Margin:       {(1 - submission['COGS'].astype(float).sum() / submission['Revenue'].astype(float).sum()) * 100:.1f}%")

# Per-month summary
df_summary = df_out.copy()
df_summary["month"] = pd.to_datetime(df_out["Date"]).dt.month
monthly = df_summary.groupby("month").agg(
    rev_mean=("Revenue", "mean"),
    cogs_mean=("COGS", "mean"),
    n_days=("Revenue", "count"),
).reset_index()
monthly["margin"] = 1 - monthly["cogs_mean"] / monthly["rev_mean"]
print("\n  Monthly Summary:")
print(f"  {'Month':>5} {'Rev Mean':>12} {'COGS Mean':>12} {'Margin':>8} {'Days':>5}")
for _, row in monthly.iterrows():
    print(f"  M{int(row['month']):02d}  {row['rev_mean']:>12,.0f} {row['cogs_mean']:>12,.0f} {row['margin']:>7.1%} {int(row['n_days']):>5}")
