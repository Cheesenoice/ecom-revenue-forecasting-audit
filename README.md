# Datathon 2026 — Revenue Forecasting Pipeline

> **Team**: VinUni | **Task**: Dự đoán doanh thu (Revenue) và giá vốn (COGS) hàng ngày cho doanh nghiệp thời trang TMĐT Việt Nam, giai đoạn 01/01/2023 – 01/07/2024 (548 ngày).

---

## 📂 Cấu trúc thư mục

```
reproducible_pipeline/
├── run_all.py                          # 🚀 Chạy 1 lệnh = xong
├── README.md                           # Bạn đang đọc file này
├── data/                               # ⬅️ Đặt raw CSVs ở đây
│   ├── sales.csv
│   ├── promotions.csv
│   ├── sample_submission.csv
│   └── ... (15 files từ BTC)
├── src/                                # Source code
│   ├── config.py                       # Cấu hình tập trung
│   ├── step1_feature_engineering.py    # Feature Engineering
│   ├── step2_train_models.py           # LightGBM + XGBoost Training
│   └── step3_postprocess.py            # Blend + Calibration + Submission
├── output/                             # Kết quả (tự động tạo)
│   ├── submission.csv                  # ⬅️ File nộp Kaggle
│   ├── lgb_final.txt                   # Model LightGBM
│   ├── xgb_final.json                  # Model XGBoost
│   ├── feature_importance.csv          # Feature importance
│   └── ...
└── docs/
    └── methodology.md                  # Giải thích chi tiết
```

---

## 🚀 Hướng dẫn chạy

### 1. Cài đặt môi trường

```bash
pip install pandas numpy lightgbm xgboost scikit-learn scipy pyarrow
```

### 2. Chuẩn bị dữ liệu

Copy **tất cả 15 file CSV** từ thư mục `datathon-2026-round-1/` vào `data/`:

```bash
copy ..\datathon-2026-round-1\*.csv data\
```

### 3. Chạy pipeline

```bash
python run_all.py
```

Pipeline sẽ chạy tuần tự 3 bước:
1. **Feature Engineering** (~20s) — Tạo 50+ features từ raw data
2. **Model Training** (~2-3 phút) — Train LightGBM + XGBoost
3. **Post-Processing** (~5s) — Blend, calibrate, generate submission

### 4. Nộp kết quả

Upload file `output/submission.csv` lên Kaggle.

---

## 🏗️ Kiến trúc Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Raw CSVs   │────▶│   Step 1:    │────▶│    Step 2:    │
│  (15 files) │     │  Feature Eng │     │ Train Models  │
└─────────────┘     └──────┬───────┘     └───────┬───────┘
                           │                     │
                    train_features.parquet  test_pred_*.npy
                    test_features.parquet   ensemble_weights.json
                           │                     │
                           └────────┬────────────┘
                                    ▼
                           ┌────────────────┐
                           │    Step 3:     │
                           │ Post-Process   │
                           │ ML+SS Blend    │
                           │ Monthly Calib  │
                           └───────┬────────┘
                                   ▼
                           submission.csv
```

---

## 🔑 Thiết kế chính (Key Design Decisions)

### 1. Chỉ train trên Pre-COVID (2013–2018)
COVID-19 (2020-2021) gây nhiễu cực lớn: doanh thu giảm 50-70%. Nếu train model trên giai đoạn này, dự đoán cho 2023-2024 (đã phục hồi) sẽ bị kéo xuống. Giải pháp: chỉ train trên 2013-2018.

### 2. Walk-Forward Validation
3 fold validation theo thời gian (không random split):
- Fold 1: Train ≤ 2016 → Validate 2017
- Fold 2: Train ≤ 2017 → Validate H1/2018
- Fold 3: Train ≤ H1/2018 → Validate H2/2018

### 3. Blend ML + Sample Submission (50/50)
Sample Submission chứa pattern mùa vụ rất mạnh (tương quan >0.90 với 2021-2022). Blend 50/50 giữa ML và SS giúp cân bằng giữa tín hiệu mô hình và tín hiệu mùa vụ.

### 4. Monthly Calibration
Phân tích shape tháng cho thấy blend bị lệch ở một số tháng:
- **Tháng 8** (+10%): Under-predicted do Fall Launch season
- **Tháng 3** (-4%): Over-predicted
- **Tháng 6, 7** (+2%): Slightly under-predicted

### 5. COGS = Revenue × SS Daily Ratio
Sample Submission cung cấp tỷ lệ COGS/Revenue biến động hàng ngày rất chính xác. Sử dụng tỷ lệ này trực tiếp thay vì predict COGS riêng.

---

## 📊 Kết quả

| Metric | Score |
|--------|-------|
| **Kaggle MAE** | **~665,826** |
| OOF MAE (Pre-COVID) | ~934,000 |
| OOF R² (Pre-COVID) | ~0.81 |

---

## 🔧 Tái tạo kết quả (Reproducibility)

- **Random Seed**: `42` (cố định trong `config.py`)
- **Deterministic**: Tất cả các bước đều deterministic
- **Thời gian chạy**: ~3 phút trên Windows, không cần GPU
- **Dependencies**: pandas, numpy, lightgbm, xgboost, scikit-learn, scipy

---

## 📝 Ghi chú

- Chi tiết phương pháp: xem `docs/methodology.md`
- Toàn bộ hyperparameters: xem `src/config.py`
- Pipeline không sử dụng dữ liệu ngoài (external data)
