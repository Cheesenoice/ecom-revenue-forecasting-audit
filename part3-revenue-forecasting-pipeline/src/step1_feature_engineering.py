"""
Step 1: Feature Engineering
============================
Đọc raw CSV → Tạo date spine → Sinh temporal + Tet + promo features
→ Xuất train_features.parquet + test_features.parquet

Chạy: python src/step1_feature_engineering.py
Thời gian: ~20 giây
"""

import sys, os, random, json, warnings
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Thêm src vào path để import config ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    RANDOM_SEED, DATA_DIR, OUTPUT_DIR, TRAIN_START, TRAIN_END,
    TEST_START, TEST_END, TET_DATES, SYNTHETIC_PROMOS,
)

warnings.filterwarnings("ignore")
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD RAW DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 1 - FEATURE ENGINEERING")
print("=" * 70)


def load_csv(name: str) -> pd.DataFrame:
    """Load một file CSV từ DATA_DIR, tự động parse date columns."""
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy {path}. Hãy copy raw CSVs vào thư mục data/")
    df = pd.read_csv(path, low_memory=False)
    for col in df.columns:
        if any(kw in col.lower() for kw in ["date", "snapshot"]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    print(f"  [OK] {name}: {df.shape}")
    return df


print("\n[1.1] Loading raw data...")
df_sales = load_csv("sales")
df_promo = load_csv("promotions")
df_sub   = load_csv("sample_submission")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. BUILD MASTER DATE SPINE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1.2] Building master date spine...")
all_dates = pd.date_range(TRAIN_START, TEST_END, freq="D")
df_master = pd.DataFrame({"Date": all_dates})
df_master["is_test"] = (df_master["Date"] >= TEST_START).astype(int)

# Merge target (Revenue, COGS)
df_sales["Date"] = pd.to_datetime(df_sales["Date"])
df_master = df_master.merge(df_sales[["Date", "Revenue", "COGS"]], on="Date", how="left")

assert df_master["Date"].nunique() == len(df_master), "Có ngày trùng lặp!"
n_train = (df_master["is_test"] == 0).sum()
n_test  = (df_master["is_test"] == 1).sum()
print(f"  Spine: {df_master.shape} | Train: {n_train} | Test: {n_test}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. TEMPORAL FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1.3] Temporal features...")


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo ~30 features dựa trên ngày, tháng, mùa, lễ Việt Nam."""
    df = df.copy()
    d = df["Date"]

    # --- Basic ---
    df["year"]          = d.dt.year
    df["month"]         = d.dt.month
    df["day"]           = d.dt.day
    df["day_of_week"]   = d.dt.dayofweek          # 0=Mon, 6=Sun
    df["day_of_year"]   = d.dt.dayofyear
    df["week_of_year"]  = d.dt.isocalendar().week.astype(int)
    df["quarter"]       = d.dt.quarter
    df["is_weekend"]    = (d.dt.dayofweek >= 5).astype(int)
    df["is_month_end"]  = d.dt.is_month_end.astype(int)
    df["is_month_start"]= d.dt.is_month_start.astype(int)
    df["days_in_month"] = d.dt.days_in_month

    # --- Cyclical encoding (sin/cos) ---
    df["sin_doy"]   = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["cos_doy"]   = np.cos(2 * np.pi * df["day_of_year"] / 365.25)
    df["sin_dow"]   = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["cos_dow"]   = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12)

    # --- Payday week (ngày lương VN: 15 và cuối tháng) ---
    df["is_payday_week"] = (
        ((df["day"] >= 13) & (df["day"] <= 17)) |
        (df["is_month_end"] == 1) |
        (df["day"] >= 28)
    ).astype(int)

    # --- Double Day sales (9/9, 10/10, 11/11, 12/12) ---
    df["is_double_day"] = (
        ((df["month"] == 9)  & (df["day"] == 9))  |
        ((df["month"] == 10) & (df["day"] == 10)) |
        ((df["month"] == 11) & (df["day"] == 11)) |
        ((df["month"] == 12) & (df["day"] == 12))
    ).astype(int)

    # --- Vietnam special days ---
    df["is_womens_day_intl"] = ((df["month"] == 3)  & (df["day"] == 8)).astype(int)
    df["is_womens_day_vn"]   = ((df["month"] == 10) & (df["day"] == 20)).astype(int)
    df["is_national_day"]    = ((df["month"] == 9)  & (df["day"] == 2)).astype(int)
    df["is_liberation_day"]  = ((df["month"] == 4)  & (df["day"] == 30)).astype(int)
    df["is_labor_day"]       = ((df["month"] == 5)  & (df["day"] == 1)).astype(int)

    # --- Interaction features ---
    df["month_x_dow"]    = df["month"] * 10 + df["day_of_week"]
    df["dom_position"]   = pd.cut(df["day"], bins=[0, 5, 25, 32], labels=[0, 1, 2]).astype(int)
    df["week_of_month"]  = (df["day"] - 1) // 7 + 1
    df["is_first3"]      = (df["day"] <= 3).astype(int)
    df["is_last3"]       = (df["day"] >= df["days_in_month"] - 2).astype(int)
    df["is_rainy_season"]     = df["month"].isin([5, 6, 7, 8, 9, 10]).astype(int)
    df["is_back_to_school"]   = df["month"].isin([8, 9]).astype(int)
    df["is_yearend_shopping"] = df["month"].isin([11, 12]).astype(int)
    df["is_tet_season"]       = df["month"].isin([1, 2]).astype(int)

    return df


df_master = add_temporal_features(df_master)
print(f"  Temporal features: {df_master.shape[1]} columns")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. TẾT FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1.4] Tet features...")


def add_tet_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo features liên quan đến Tết Nguyên Đán:
    - is_tet_approach  : 21 ngày trước Tết (nhu cầu tăng mạnh)
    - is_tet_holiday   : 7 ngày Tết (DIP - doanh thu giảm)
    - is_tet_recovery  : 14 ngày sau Tết (phục hồi)
    - tet_proximity    : Gaussian proximity (càng gần Tết → càng cao)
    """
    df = df.copy()
    df["is_tet_approach"] = 0
    df["is_tet_holiday"]  = 0
    df["is_tet_recovery"] = 0
    df["days_to_tet"]     = 999

    for year, tet_str in TET_DATES.items():
        tet = pd.Timestamp(tet_str)
        mask_approach = (df["Date"] >= tet - pd.Timedelta(days=21)) & (df["Date"] < tet)
        mask_holiday  = (df["Date"] >= tet) & (df["Date"] < tet + pd.Timedelta(days=7))
        mask_recovery = (df["Date"] >= tet + pd.Timedelta(days=7)) & (df["Date"] < tet + pd.Timedelta(days=21))

        df.loc[mask_approach, "is_tet_approach"] = 1
        df.loc[mask_holiday,  "is_tet_holiday"]  = 1
        df.loc[mask_recovery, "is_tet_recovery"] = 1

        diff = (tet - df["Date"]).dt.days
        df["days_to_tet"] = np.where(
            np.abs(diff) < np.abs(df["days_to_tet"]), diff, df["days_to_tet"]
        )

    df["days_to_tet_clipped"] = df["days_to_tet"].clip(-60, 60)
    df["tet_proximity"] = np.exp(-np.abs(df["days_to_tet_clipped"]) / 15)
    return df


df_master = add_tet_features(df_master)
print(f"  Tet approach days: {df_master['is_tet_approach'].sum()}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. PROMOTION CALENDAR FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1.5] Promotion calendar features...")

# Build synthetic promo DataFrame
syn_rows = []
for row in SYNTHETIC_PROMOS:
    syn_rows.append({
        "promo_name": row[0], "start_date": pd.Timestamp(row[1]),
        "end_date": pd.Timestamp(row[2]), "promo_type": row[3],
        "discount_value": row[4], "applicable_category": row[5],
        "promo_channel": row[6], "stackable_flag": row[7],
    })
df_syn = pd.DataFrame(syn_rows)

# Standardise real promo table
df_promo_std = df_promo.copy()
df_promo_std["applicable_category"] = df_promo_std["applicable_category"].fillna("All")

# Merge real + synthetic
PROMO_COLS = ["promo_name", "start_date", "end_date", "promo_type",
              "discount_value", "applicable_category", "promo_channel", "stackable_flag"]
df_all_promos = pd.concat([
    df_promo_std[PROMO_COLS],
    df_syn[PROMO_COLS],
], ignore_index=True)

# Campaign type classification
CAMPAIGN_MAP = {
    "Spring Sale": "spring", "Mid-Year Sale": "midyear", "Fall Launch": "fall",
    "Year-End Sale": "yearend", "Urban Blowout": "urban", "Rural Special": "rural",
}


def get_campaign_type(name):
    for k, v in CAMPAIGN_MAP.items():
        if k in name:
            return v
    return "other"


df_all_promos["campaign_type"] = df_all_promos["promo_name"].apply(get_campaign_type)


def build_promo_features(df_spine: pd.DataFrame, df_promos: pd.DataFrame) -> pd.DataFrame:
    """
    Với mỗi ngày, tính:
    - is_in_any_promo, n_active_promos, max_discount_pct
    - Per-campaign binary flags (promo_spring, promo_midyear, ...)
    - days_to_next_promo_start, days_to_promo_end (urgency)
    """
    df = df_spine.copy()
    df["is_in_any_promo"]      = 0
    df["n_active_promos"]      = 0
    df["max_discount_pct"]     = 0.0
    df["is_stackable_active"]  = 0
    df["is_all_channel_promo"] = 0
    df["days_to_promo_end"]    = 999
    df["days_since_promo_start"] = 999

    for ct in CAMPAIGN_MAP.values():
        df[f"promo_{ct}"] = 0

    for _, promo in df_promos.iterrows():
        start, end = promo["start_date"], promo["end_date"]
        dtype, dval = promo["promo_type"], float(promo["discount_value"])
        stack, chan  = int(promo["stackable_flag"]), str(promo["promo_channel"])
        ctype = promo["campaign_type"]
        disc_pct = min(dval / 20000 * 100, 50) if dtype == "fixed" else dval

        mask = (df["Date"] >= start) & (df["Date"] <= end)
        df.loc[mask, "is_in_any_promo"]    = 1
        df.loc[mask, "n_active_promos"]   += 1
        df.loc[mask, "max_discount_pct"]   = df.loc[mask, "max_discount_pct"].clip(lower=disc_pct)
        if stack:
            df.loc[mask, "is_stackable_active"] = 1
        if "all" in chan.lower():
            df.loc[mask, "is_all_channel_promo"] = 1
        if ctype in CAMPAIGN_MAP.values():
            df.loc[mask, f"promo_{ctype}"] = 1

        end_diff = (end - df.loc[mask, "Date"]).dt.days
        df.loc[mask, "days_to_promo_end"] = np.minimum(
            df.loc[mask, "days_to_promo_end"].values, end_diff.values
        )
        start_diff = (df.loc[mask, "Date"] - start).dt.days
        df.loc[mask, "days_since_promo_start"] = np.minimum(
            df.loc[mask, "days_since_promo_start"].values, start_diff.values
        )

    # days_to_next_promo_start
    df["days_to_next_promo_start"] = 999
    for _, promo in df_promos.iterrows():
        diff = (promo["start_date"] - df["Date"]).dt.days
        future_mask = diff >= 0
        df.loc[future_mask, "days_to_next_promo_start"] = np.minimum(
            df.loc[future_mask, "days_to_next_promo_start"].values, diff[future_mask].values
        )

    # Clip & log transform
    df["days_to_promo_end"]        = df["days_to_promo_end"].clip(0, 60)
    df["days_since_promo_start"]   = df["days_since_promo_start"].clip(0, 60)
    df["days_to_next_promo_start"] = df["days_to_next_promo_start"].clip(0, 90)
    df["log_days_to_promo_end"]        = np.log1p(df["days_to_promo_end"])
    df["log_days_to_next_promo_start"] = np.log1p(df["days_to_next_promo_start"])
    return df


df_master = build_promo_features(df_master, df_all_promos)
print(f"  Promo days 2023+: {df_master.loc[df_master['Date'] >= '2023-01-01', 'is_in_any_promo'].sum()}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. FINAL ASSEMBLY & SAVE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1.6] Final assembly...")

EXCLUDE_COLS = ["Date", "Revenue", "COGS", "is_test", "year", "days_to_tet"]
FEATURE_COLS = [c for c in df_master.columns if c not in EXCLUDE_COLS]

# Separate train / test
df_train = df_master[df_master["is_test"] == 0].copy()
df_test  = df_master[df_master["is_test"] == 1].copy()

# Fill NaN
for col in FEATURE_COLS:
    fill_val = df_train[col].median()
    df_train[col] = df_train[col].fillna(fill_val)
    df_test[col]  = df_test[col].fillna(fill_val)

print(f"  Train: {len(df_train)} rows | Test: {len(df_test)} rows")
print(f"  Features: {len(FEATURE_COLS)}")

# Save
df_train.to_parquet(OUTPUT_DIR / "train_features.parquet", index=False)
df_test.to_parquet(OUTPUT_DIR / "test_features.parquet",   index=False)
json.dump(FEATURE_COLS, open(OUTPUT_DIR / "feature_cols.json", "w"), indent=2)

# QA Assertions
assert len(df_test) == 548, f"Test set should be 548 rows, got {len(df_test)}"
assert df_train["Revenue"].isna().sum() == 0, "NaN in train Revenue!"
for col in FEATURE_COLS:
    assert df_train[col].isna().sum() == 0, f"NaN in train[{col}]!"
    assert df_test[col].isna().sum()  == 0, f"NaN in test[{col}]!"

print("\n[OK] STEP 1 COMPLETE - Feature matrix saved to output/")
print(f"   train_features.parquet : {df_train.shape}")
print(f"   test_features.parquet  : {df_test.shape}")
print(f"   feature_cols.json      : {len(FEATURE_COLS)} features")
