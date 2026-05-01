"""
run_all.py — Chạy toàn bộ pipeline từ đầu đến cuối
=====================================================
Một lệnh duy nhất để tái tạo kết quả:
    python run_all.py

Thứ tự:
  Step 1: Feature Engineering  (~20 giây)
  Step 2: Model Training       (~2-3 phút)
  Step 3: Post-Processing      (~5 giây)

Output: output/submission.csv
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Fix OpenBLAS memory issue on Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

STEPS = [
    ("Step 1: Feature Engineering",  "src/step1_feature_engineering.py"),
    ("Step 2: Model Training",       "src/step2_train_models.py"),
    ("Step 3: Post-Processing",      "src/step3_postprocess.py"),
]

BASE_DIR = Path(__file__).resolve().parent


def main():
    print("+" + "-" * 68 + "+")
    print("|  DATATHON 2026 - REPRODUCIBLE PIPELINE                           |")
    print("|  VinUni Fashion E-commerce Revenue Forecasting                    |")
    print("+" + "-" * 68 + "+")

    total_start = time.time()

    for i, (name, script) in enumerate(STEPS, 1):
        print(f"\n{'-' * 70}")
        print(f"  [{i}/{len(STEPS)}] {name}")
        print(f"{'-' * 70}")

        step_start = time.time()
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / script)],
            cwd=str(BASE_DIR),
        )

        elapsed = time.time() - step_start

        if result.returncode != 0:
            print(f"\n  [FAILED] {name} (exit code {result.returncode})")
            print(f"     Check the error above and fix before re-running.")
            sys.exit(1)

        print(f"\n  [{name} completed in {elapsed:.1f}s]")

    total_elapsed = time.time() - total_start

    print("\n" + "+" + "=" * 68 + "+")
    print("|  ALL STEPS COMPLETE                                              |")
    print("+" + "=" * 68 + "+")
    print(f"\n  Total time: {total_elapsed:.1f}s")
    print(f"  Output:     output/submission.csv")
    print(f"\n  Upload output/submission.csv to Kaggle to submit.")


if __name__ == "__main__":
    main()
