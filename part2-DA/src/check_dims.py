from PIL import Image
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA     = BASE_DIR / "data"
OUT      = BASE_DIR / "charts"
OUT.mkdir(parents=True, exist_ok=True)

charts_dir = BASE_DIR / "charts"
charts = sorted([c for c in os.listdir(charts_dir) if c.endswith('.png')])

for c in charts:
    img = Image.open(os.path.join(charts_dir, c))
    w, h = img.size
    ratio = w / h
    shape = "SQUARE" if 0.8 < ratio < 1.25 else ("WIDE" if ratio >= 1.25 else "TALL")
    print(f"{c:42s}  {w:5d}x{h:<5d}  ratio={ratio:.2f}  [{shape}]")
