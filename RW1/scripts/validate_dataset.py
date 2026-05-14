"""校验 dataset.jsonl 字段与本地路径。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RW1 = Path(__file__).resolve().parent.parent
SUBDIR_TO_HOLE = {"图片上": "上钻孔", "图片下": "下钻孔"}
REQUIRED = {"schema_version", "image_path", "drill_hole", "image_label"}
LABELS = {"未碎裂", "碎裂", "不确定"}
EVIDENCE = {"crack", "block_loss", "pulverized"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path, nargs="?", default=RW1 / "dataset.jsonl")
    args = ap.parse_args()
    if not args.jsonl.is_file():
        print("文件不存在:", args.jsonl)
        sys.exit(1)

    errs: list[str] = []
    n = 0
    for line_no, line in enumerate(args.jsonl.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            o = json.loads(line)
        except json.JSONDecodeError as e:
            errs.append(f"L{line_no}: JSON {e}")
            continue
        miss = REQUIRED - set(o.keys())
        if miss:
            errs.append(f"L{line_no}: 缺少字段 {miss}")
        if o.get("image_label") not in LABELS:
            errs.append(f"L{line_no}: image_label 非法 {o.get('image_label')!r}")
        rel = o.get("image_path")
        if not isinstance(rel, str):
            errs.append(f"L{line_no}: image_path 非字符串")
            continue
        parts = Path(rel).parts
        if len(parts) < 2:
            errs.append(f"L{line_no}: image_path 需含子目录: {rel}")
            continue
        sub = parts[0]
        expect_hole = SUBDIR_TO_HOLE.get(sub)
        if expect_hole and o.get("drill_hole") != expect_hole:
            errs.append(
                f"L{line_no}: drill_hole 与目录不一致: 期望 {expect_hole}, 得到 {o.get('drill_hole')!r}"
            )
        img = RW1 / rel
        if not img.is_file():
            errs.append(f"L{line_no}: 图片不存在 {img}")
        for i, r in enumerate(o.get("regions") or []):
            ev = r.get("evidence")
            if ev not in EVIDENCE:
                errs.append(f"L{line_no} region#{i}: evidence 非法 {ev!r}")
            g = r.get("geometry") or {}
            if g.get("type") != "rect" or not isinstance(g.get("xyxy"), list):
                errs.append(f"L{line_no} region#{i}: geometry 需为 rect+xyxy")
        for i, m in enumerate(o.get("measurements") or []):
            if not isinstance(m.get("points"), list):
                errs.append(f"L{line_no} m#{i}: points 需为数组")

    if errs:
        print("\n".join(errs))
        print(f"校验失败：{len(errs)} 个问题（共 {n} 条记录）")
        sys.exit(2)
    print(f"校验通过：{n} 条记录")


if __name__ == "__main__":
    main()
