from __future__ import annotations

import csv
import json
import re
from pathlib import Path

RAW_DIR = Path(r"e:\作业\欧莱雅比赛项目\download_materials\skin_tone")
OUTPUT_CSV = Path(__file__).with_name("skin_tone_cleaned.csv")
OUTPUT_META = Path(__file__).with_name("skin_tone_cleaned_summary.json")


def normalize_hex(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("#", "").strip()
    if len(text) != 6:
        return None
    if not all(ch in "0123456789abcdefABCDEF" for ch in text):
        return None
    return "#" + text.upper()


def hex_to_rgb(hex_value: str) -> tuple[int, int, int]:
    hex_value = hex_value.strip().lstrip("#")
    return tuple(int(hex_value[i:i + 2], 16) for i in (0, 2, 4))


def to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_undertone(text: str | None) -> str:
    if text is None:
        return "neutral"
    s = text.lower()
    if re.search(r"\b(cool|pink|rose|blue|ivory|porcelain|cool\s+gold|neutral\s+pink|neutral\s+peach)\b", s):
        return "cool"
    if re.search(r"\b(warm|golden|peach|amber|tan|beige|honey|bronze)\b", s):
        return "warm"
    if re.search(r"\b(neutral|n)\b", s):
        return "neutral"
    if re.search(r"(?i)(?:^|[^a-z])([cw])(?=[^a-z]|$)", s):
        if "c" in s:
            return "cool"
        if "w" in s:
            return "warm"
    return "neutral"


def normalize_categories(value: str | None) -> str:
    if value is None:
        return ""
    parts = [p.strip().lower() for p in str(value).split(",")]
    clean = [p for p in parts if p and p not in {"na", "n/a", "none"}]
    return ";".join(clean)


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw skin tone directory not found: {RAW_DIR}")

    fieldnames = [
        "brand",
        "product",
        "name",
        "specific",
        "hex",
        "r",
        "g",
        "b",
        "lightness",
        "undertone",
        "categories",
        "source_dataset",
        "source_file",
    ]

    rows: list[dict] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()

    for csv_path in sorted(RAW_DIR.rglob("*.csv")):
        if csv_path.name.lower().startswith("readme"):
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                continue
            for row in reader:
                hex_value = normalize_hex(row.get("hex") or row.get("HEX") or row.get("Hex") or row.get("color_hex"))
                if not hex_value:
                    continue

                brand = (row.get("brand") or "").strip()
                product = (row.get("product") or "").strip()
                name = (row.get("name") or row.get("shade_name") or row.get("specific") or "").strip()
                specific = (row.get("specific") or row.get("numbers") or row.get("id") or "").strip()
                categories = normalize_categories(row.get("categories") or row.get("category") or row.get("category_name"))
                lightness = to_float(row.get("lightness") or row.get("lightToDark"))
                reference_text = " ".join(filter(None, [specific, name, product, categories]))
                undertone = infer_undertone(reference_text)

                r, g, b = hex_to_rgb(hex_value)
                key = (brand, product, name, specific, hex_value, csv_path.parent.name)
                if key in seen:
                    continue
                seen.add(key)

                rows.append({
                    "brand": brand,
                    "product": product,
                    "name": name,
                    "specific": specific,
                    "hex": hex_value,
                    "r": r,
                    "g": g,
                    "b": b,
                    "lightness": round(lightness, 6) if lightness is not None else "",
                    "undertone": undertone,
                    "categories": categories,
                    "source_dataset": csv_path.parent.name,
                    "source_file": csv_path.name,
                })

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "source_root": str(RAW_DIR),
        "output_csv": str(OUTPUT_CSV),
        "rows_generated": len(rows),
        "source_files_used": sorted(str(p.relative_to(RAW_DIR)) for p in RAW_DIR.rglob("*.csv") if not p.name.lower().startswith("readme")),
        "schema": fieldnames,
    }
    OUTPUT_META.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {OUTPUT_CSV}")
    print(f"Rows saved: {len(rows)}")
    print(f"Source files used: {len(summary['source_files_used'])}")


if __name__ == "__main__":
    main()
