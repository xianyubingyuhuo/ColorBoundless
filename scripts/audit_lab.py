import json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "beauty"))
print(sys.path[:2])
from lipstick.shade_library import hex2lab

for name in ["red_base.json", "purple_base.json"]:
    entries = json.load(open(PROJECT_ROOT / "data" / "knowledge_base" / "base_palette" / name, encoding="utf-8"))
    for e in entries:
        true_lab = hex2lab(e["hex"])
        saved = e["lab"]
        bad = any(abs(t - s) > 0.5 for t, s in zip(true_lab, saved))
        print("[NG]" if bad else "[OK]", name, e["palette_id"], e["hex"],
              "存:", saved, "算:", [round(x, 1) for x in true_lab])