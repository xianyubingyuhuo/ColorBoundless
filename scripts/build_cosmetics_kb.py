# -*- coding: utf-8 -*-
"""
build_cosmetics_kb.py
=====================
把美妆知识语料（cosmetics_kb）清洗、去重、构建成 RAG 文本索引。

输入 : data/knowledge_base/cosmetics_kb/*.jsonl   （一行一个 JSON 对象）
输出 : models/vector_store/cosmetics_kb_index.npz  （retrieval_texts + 结构化字段）
       models/vector_store/cosmetics_kb_meta.json

与 style_recommendations 管线分工一致：
    本脚本只做"校验/去重/字段入库"；
    向量化由 embed_cosmetics_kb.py（bge-small-zh → embeddings.npz）完成。

语料 schema 详见 data/knowledge_base/cosmetics_kb/README.md。

用法：
    python scripts/build_cosmetics_kb.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
KB_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "cosmetics_kb"
OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_index.npz"
OUTPUT_META = PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_meta.json"

# schema 校验
REQUIRED_FIELDS = {"id", "category", "title", "content", "tags", "source"}
VALID_CATEGORIES = {"color_theory", "technique", "style", "cvd", "product", "vocab"}
VALID_OCCASIONS = {"daily", "work", "date", "party", "night", "formal", "photo", "all"}


def load_jsonl(path: Path) -> list[dict]:
    """逐行解析 JSONL，语法错误的行直接报错（语料必须干净）"""
    entries = []
    for line_no, line in enumerate(path.open(encoding="utf-8"), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"❌ {path.name} 第 {line_no} 行 JSON 解析失败: {e}")
    return entries


def validate(entry: dict, path: Path, line_no: int) -> None:
    """schema 校验：必填字段 + 取值范围"""
    where = f"{path.name}:{line_no}"
    missing = REQUIRED_FIELDS - set(entry)
    if missing:
        raise SystemExit(f"❌ {where} 缺少必填字段: {missing}")
    if entry["category"] not in VALID_CATEGORIES:
        raise SystemExit(f"❌ {where} category 非法: {entry['category']!r}")
    bad_occ = set(entry.get("occasion", [])) - VALID_OCCASIONS
    if bad_occ:
        raise SystemExit(f"❌ {where} occasion 词汇非法: {bad_occ}（统一词汇 {sorted(VALID_OCCASIONS)}）")
    if len(entry["content"]) < 60:
        print(f"⚠️  {where} content 过短（{len(entry['content'])} 字），建议 200~600 字")


def to_retrieval_text(entry: dict) -> str:
    """拼装给 embedding 模型的检索文本：标题 + 正文 + 口语词"""
    tags = "、".join(entry.get("tags", []))
    return f"{entry['title']}\n{entry['content']}\n关键词：{tags}"


def main() -> None:
    files = sorted(KB_DIR.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"❌ 语料目录为空: {KB_DIR}\n   请先放入 .jsonl 语料（模板见同目录 seed_techniques.jsonl）")

    # ---------- [1/4] 读取 + 校验 ----------
    print(f"[1/4] 扫描语料目录: {KB_DIR}")
    all_entries: list[dict] = []
    seen_ids: set[str] = set()
    for path in files:
        for line_no, entry in enumerate(load_jsonl(path), start=1):
            validate(entry, path, line_no)
            if entry["id"] in seen_ids:
                raise SystemExit(f"❌ {path.name}:{line_no} id 重复: {entry['id']}")
            seen_ids.add(entry["id"])
            entry["_src_file"] = path.name
            entry["_line_no"] = line_no
            all_entries.append(entry)
    print(f"      文件 {len(files)} 个，共 {len(all_entries)} 条语料")

    # ---------- [2/4] 内容去重（完全相同 content 视为重复） ----------
    print("[2/4] 内容去重...")
    unique: list[dict] = []
    seen_contents: set[str] = set()
    for entry in all_entries:
        key = entry["content"].strip()
        if key in seen_contents:
            print(f"      ⏭ 跳过重复条目: {entry['id']}")
            continue
        seen_contents.add(key)
        unique.append(entry)
    print(f"      去重后 {len(unique)} 条")

    # ---------- [3/4] 拼装检索文本与字段 ----------
    print("[3/4] 拼装检索文本...")
    ids = np.array([e["id"] for e in unique], dtype=object)
    categories = np.array([e["category"] for e in unique], dtype=object)
    titles = np.array([e["title"] for e in unique], dtype=object)
    contents = np.array([e["content"] for e in unique], dtype=object)
    tags = np.array([";".join(e.get("tags", [])) for e in unique], dtype=object)
    sources = np.array([e["source"] for e in unique], dtype=object)
    occasions = np.array([";".join(e.get("occasion", [])) for e in unique], dtype=object)
    hue_families = np.array([e.get("hue_family", "") for e in unique], dtype=object)
    retrieval_texts = np.array([to_retrieval_text(e) for e in unique], dtype=object)

    cat_stat = {c: int((categories == c).sum()) for c in sorted(set(categories.tolist()))}
    print(f"      分类分布: {cat_stat}")

    # ---------- [4/4] 保存 ----------
    print(f"[4/4] 保存到: {OUTPUT_NPZ}")
    OUTPUT_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_NPZ,
        ids=ids,
        categories=categories,
        titles=titles,
        contents=contents,
        tags=tags,
        sources=sources,
        occasions=occasions,
        hue_families=hue_families,
        retrieval_texts=retrieval_texts,
    )

    meta = {
        "total_entries": len(unique),
        "source_files": [f.name for f in files],
        "category_stats": cat_stat,
        "retrieval_text_fields": ["title", "content", "tags"],
        "schema_version": 1,
        "created_by": "build_cosmetics_kb.py",
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n✅ cosmetics_kb 文本索引生成完成！")
    print(f"   条目: {len(unique)} 条  → 下一步运行 scripts/embed_cosmetics_kb.py 生成向量")


if __name__ == "__main__":
    main()

