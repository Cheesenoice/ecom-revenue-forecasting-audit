"""
Step 2: Model Training (LightGBM + XGBoost)
=============================================
Đọc features từ Step 1 → Walk-forward validation → Train final models
→ Xuất OOF predictions + Test predictions

Chạy: python src/step2_train_models.py
Thời gian: ~2-3 phút
"""

import sys, json, warnings, random
import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    RANDOM_SEED, OUTPUT_DIR, PRE_COVID_END,
    LGB_PARAMS, XGB_PARAMS, VALIDATION_SPLITS,
)

warnings.filterwarnings("ignore")
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

TARGET = "Revenue"


def compute_metrics(y_true, y_pred, name=""):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    print(f"  {name:30s} | MAE={mae:>12,.0f} | RMSE={rmse:>12,.0f} | R²={r2:.4f}")
    return {"mae": mae, "rmse": rmse, "r2": r2, "fold": name}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 2 - MODEL TRAINING")
print("=" * 70)

print("\n[2.1] Loading features...")
df_train = pd.read_parquet(OUTPUT_DIR / "train_features.parquet")
df_test  = pd.read_parquet(OUTPUT_DIR / "test_features.parquet")
FEATURE_COLS = json.load(open(OUTPUT_DIR / "feature_cols.json"))

df_train["Date"] = pd.to_datetime(df_train["Date"])
df_test["Date"]  = pd.to_datetime(df_test["Date"])

print(f"  Train: {df_train.shape} | Test: {df_test.shape} | Features: {len(FEATURE_COLS)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. LIGHTGBM - Walk-Forward Training
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("[2.2] LightGBM Walk-Forward Training")
print("=" * 70)

oof_lgb = []
test_preds_lgb = np.zeros(len(df_test))
best_iters_lgb = []

for i, split in enumerate(VALIDATION_SPLITS):
    print(f"\n  --- {split['name']} ---")
    mask_tr  = df_train["Date"] <= split["train_end"]
    mask_val = (df_train["Date"] >= split["val_start"]) & (df_train["Date"] <= split["val_end"])

    X_tr, y_tr   = df_train.loc[mask_tr,  FEATURE_COLS], df_train.loc[mask_tr,  TARGET]
    X_val, y_val = df_train.loc[mask_val, FEATURE_COLS], df_train.loc[mask_val, TARGET]

    dtrain = lgb.Dataset(X_tr, label=y_tr)
    dval   = lgb.Dataset(X_val, label=y_val, reference=dtrain)

    model = lgb.train(
        LGB_PARAMS, dtrain, num_boost_round=5000,
        valid_sets=[dval],
        callbacks=[lgb.early_stopping(200), lgb.log_evaluation(0)],
    )
    best_iters_lgb.append(model.best_iteration)

    val_pred  = model.predict(X_val)
    test_pred = model.predict(df_test[FEATURE_COLS])

    compute_metrics(y_val, val_pred, split["name"])

    oof_df = df_train.loc[mask_val, ["Date", TARGET]].copy()
    oof_df["lgb_pred"] = val_pred
    oof_lgb.append(oof_df)
    test_preds_lgb += test_pred / len(VALIDATION_SPLITS)

# Final LGB on Pre-Covid
print("\n  Training final LGB on Pre-Covid (2013-2018)...")
best_iter_lgb = int(np.mean(best_iters_lgb) * 1.1)
df_pure = df_train[df_train["Date"] <= PRE_COVID_END]
dtrain_full = lgb.Dataset(df_pure[FEATURE_COLS], label=df_pure[TARGET])
model_lgb_final = lgb.train(
    {**LGB_PARAMS, "learning_rate": 0.008},
    dtrain_full, num_boost_round=best_iter_lgb,
)
test_pred_lgb_final = model_lgb_final.predict(df_test[FEATURE_COLS])
test_preds_lgb = 0.5 * test_preds_lgb + 0.5 * test_pred_lgb_final

# Save LGB artifacts
model_lgb_final.save_model(str(OUTPUT_DIR / "lgb_final.txt"))
np.save(OUTPUT_DIR / "test_pred_lgb.npy", test_preds_lgb)
df_oof_lgb = pd.concat(oof_lgb).sort_values("Date")
df_oof_lgb.to_parquet(OUTPUT_DIR / "oof_lgb.parquet", index=False)
print(f"  [OK] LGB done | test mean: {test_preds_lgb.mean():,.0f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. XGBOOST - Walk-Forward Training
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("[2.3] XGBoost Walk-Forward Training")
print("=" * 70)

oof_xgb = []
test_preds_xgb = np.zeros(len(df_test))
best_iters_xgb = []

for i, split in enumerate(VALIDATION_SPLITS):
    print(f"\n  --- {split['name']} ---")
    mask_tr  = df_train["Date"] <= split["train_end"]
    mask_val = (df_train["Date"] >= split["val_start"]) & (df_train["Date"] <= split["val_end"])

    X_tr, y_tr   = df_train.loc[mask_tr,  FEATURE_COLS], df_train.loc[mask_tr,  TARGET]
    X_val, y_val = df_train.loc[mask_val, FEATURE_COLS], df_train.loc[mask_val, TARGET]

    dtrain = xgb.DMatrix(X_tr, label=y_tr)
    dval   = xgb.DMatrix(X_val, label=y_val)
    dte    = xgb.DMatrix(df_test[FEATURE_COLS])

    model = xgb.train(
        XGB_PARAMS, dtrain, num_boost_round=5000,
        evals=[(dval, "val")], early_stopping_rounds=200, verbose_eval=False,
    )
    best_iters_xgb.append(model.best_iteration)

    val_pred  = model.predict(dval, iteration_range=(0, model.best_iteration + 1))
    test_pred = model.predict(dte,  iteration_range=(0, model.best_iteration + 1))

    compute_metrics(y_val, val_pred, split["name"])

    oof_df = df_train.loc[mask_val, ["Date", TARGET]].copy()
    oof_df["xgb_pred"] = val_pred
    oof_xgb.append(oof_df)
    test_preds_xgb += test_pred / len(VALIDATION_SPLITS)

# Final XGB on Pre-Covid
print("\n  Training final XGB on Pre-Covid (2013-2018)...")
best_iter_xgb = int(np.mean(best_iters_xgb) * 1.1)
df_pure = df_train[df_train["Date"] <= PRE_COVID_END]
dtrain_full = xgb.DMatrix(df_pure[FEATURE_COLS], label=df_pure[TARGET])
dte = xgb.DMatrix(df_test[FEATURE_COLS])
model_xgb_final = xgb.train(
    {**XGB_PARAMS, "learning_rate": 0.008},
    dtrain_full, num_boost_round=best_iter_xgb,
)
test_pred_xgb_final = model_xgb_final.predict(dte)
test_preds_xgb = 0.5 * test_preds_xgb + 0.5 * test_pred_xgb_final

# Save XGB artifacts
model_xgb_final.save_model(str(OUTPUT_DIR / "xgb_final.json"))
np.save(OUTPUT_DIR / "test_pred_xgb.npy", test_preds_xgb)
df_oof_xgb = pd.concat(oof_xgb).sort_values("Date")
df_oof_xgb.to_parquet(OUTPUT_DIR / "oof_xgb.parquet", index=False)
print(f"  [OK] XGB done | test mean: {test_preds_xgb.mean():,.0f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. ENSEMBLE - OOF Weight Optimization
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("[2.4] Ensemble Weight Optimization (OOF)")
print("=" * 70)

common_dates = set(df_oof_lgb["Date"]) & set(df_oof_xgb["Date"])
a = df_oof_lgb[df_oof_lgb["Date"].isin(common_dates)].set_index("Date").sort_index()
b = df_oof_xgb[df_oof_xgb["Date"].isin(common_dates)].set_index("Date").sort_index()

gt = a[TARGET].values
P = np.column_stack([a["lgb_pred"].values, b["xgb_pred"].values])


def mae_obj(w):
    w = np.abs(w) / np.abs(w).sum()
    return np.abs(gt - P @ w).mean()


result = minimize(mae_obj, x0=[0.50, 0.50], method="Nelder-Mead")
w = np.abs(result.x) / np.abs(result.x).sum()

print(f"  Weights: LGB={w[0]:.3f}, XGB={w[1]:.3f}")
print(f"  OOF MAE: {result.fun:,.0f}")

# Final ML blend
ml_blend = w[0] * test_preds_lgb + w[1] * test_preds_xgb
np.save(OUTPUT_DIR / "test_pred_ml_ensemble.npy", ml_blend)

# Save weights
json.dump({
    "lgb_weight": float(w[0]),
    "xgb_weight": float(w[1]),
    "oof_mae": float(result.fun),
    "lgb_best_iters": best_iters_lgb,
    "xgb_best_iters": best_iters_xgb,
}, open(OUTPUT_DIR / "ensemble_weights.json", "w"), indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. FEATURE IMPORTANCE (LGB)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("[2.5] Feature Importance (Top 20)")
print("=" * 70)

imp_df = pd.DataFrame({
    "feature":    model_lgb_final.feature_name(),
    "importance": model_lgb_final.feature_importance(importance_type="gain"),
}).sort_values("importance", ascending=False)

print(imp_df.head(20).to_string(index=False))
imp_df.to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)

print(f"\n[OK] STEP 2 COMPLETE - Models trained and saved")
print(f"   ML ensemble test mean: {ml_blend.mean():,.0f}")
