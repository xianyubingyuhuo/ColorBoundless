from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

RAW_CSV = Path(r"e:\作业\欧莱雅比赛项目\download_materials\fashion_style\recommendations.csv")
OUTPUT_CSV = Path(__file__).with_name("fashion_style_cleaned.csv")
OUTPUT_META = Path(__file__).with_name("fashion_style_cleaned_summary.json")


def clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_label(value) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = text.lower()
    text = text.replace("/", " ")
    text = re.sub(r"[^a-z0-9\s\-_]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().replace(" ", "_")


def split_color_list(value) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    items = [part.strip() for part in re.split(r"[,;]|\band\b", text) if part.strip()]
    colors: list[str] = []
    for item in items:
        item = re.sub(r"[^A-Za-z0-9\s-]", "", item)
        item = re.sub(r"\s+", " ", item).strip()
        if item:
            colors.append(item.lower().replace(" ", "_"))
    return colors


def clean_row(row: dict) -> dict:
    hair = clean_text(row.get("Hair Color") or row.get("hair_color") or "")
    eye = clean_text(row.get("Eye Color") or row.get("eye_color") or "")
    skin = clean_text(row.get("Skin Tone") or row.get("skin_tone") or "")
    undertone = clean_text(row.get("Under Tone") or row.get("under_tone") or row.get("undertone") or "")
    torso = clean_text(row.get("Torso length") or row.get("torso_length") or "")
    body = clean_text(row.get("Body Proportion") or row.get("body_proportion") or "")
    recommended_colors = split_color_list(row.get("Recommended Clothing Colors") or row.get("recommended_clothing_colors") or "")
    avoid_colors = split_color_list(row.get("Avoid Clothing Colors") or row.get("avoid_clothing_colors") or "")
    fitting = clean_text(row.get("Recommended Fitting Style") or row.get("recommended_fitting_style") or "")
    material = clean_text(row.get("Recommended Materials") or row.get("recommended_materials") or "")
    pattern = clean_text(row.get("Recommended Patterns") or row.get("recommended_patterns") or "")
    jewelry = clean_text(row.get("Recommended Jewelry Metal") or row.get("recommended_jewelry_metal") or "")
    shoes = clean_text(row.get("Recommended Shoes") or row.get("recommended_shoes") or "")
    good_region = clean_text(row.get("Recommended Clothing Color Wheel Region") or row.get("recommended_color_wheel_region") or "")
    avoid_region = clean_text(row.get("Avoid Clothing Color Wheel Region") or row.get("avoid_color_wheel_region") or "")
    fabric_nature = clean_text(row.get("Fabric Nature") or row.get("fabric_nature") or "")
    do_exaggerate = clean_text(row.get("Do Exaggerate") or row.get("do_exaggerate") or "")
    dont_exaggerate = clean_text(row.get("Don't Exaggerate") or row.get("dont_exaggerate") or "")

    return {
        "hair_color": normalize_label(hair),
        "eye_color": normalize_label(eye),
        "skin_tone": normalize_label(skin),
        "undertone": normalize_label(undertone),
        "torso_length": normalize_label(torso),
        "body_proportion": normalize_label(body),
        "recommended_colors": recommended_colors,
        "avoid_colors": avoid_colors,
        "recommended_fitting_style": normalize_label(fitting),
        "recommended_materials": normalize_label(material),
        "recommended_patterns": normalize_label(pattern),
        "recommended_jewelry_metal": normalize_label(jewelry),
        "recommended_shoes": normalize_label(shoes),
        "recommended_color_wheel_region": normalize_label(good_region),
        "avoid_color_wheel_region": normalize_label(avoid_region),
        "fabric_nature": normalize_label(fabric_nature),
        "do_exaggerate": normalize_label(do_exaggerate),
        "dont_exaggerate": normalize_label(dont_exaggerate),
        "source_file": RAW_CSV.name,
    }


def main() -> None:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Raw style source not found: {RAW_CSV}")

    fieldnames = [
        "hair_color",
        "eye_color",
        "skin_tone",
        "undertone",
        "torso_length",
        "body_proportion",
        "recommended_colors",
        "avoid_colors",
        "recommended_fitting_style",
        "recommended_materials",
        "recommended_patterns",
        "recommended_jewelry_metal",
        "recommended_shoes",
        "recommended_color_wheel_region",
        "avoid_color_wheel_region",
        "fabric_nature",
        "do_exaggerate",
        "dont_exaggerate",
        "source_file",
    ]

    rows: list[dict] = []
    with RAW_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = clean_row(row)
            if not any(cleaned[k] for k in [
                "hair_color",
                "eye_color",
                "skin_tone",
                "undertone",
                "torso_length",
                "body_proportion",
            ]):
                continue
            rows.append(cleaned)

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "source_root": str(RAW_CSV),
        "output_csv": str(OUTPUT_CSV),
        "rows_generated": len(rows),
        "schema": fieldnames,
    }
    OUTPUT_META.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {OUTPUT_CSV}")
    print(f"Rows saved: {len(rows)}")


if __name__ == "__main__":
    main()
