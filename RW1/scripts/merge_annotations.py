"""合并侧车 JSON 为 dataset.jsonl（相对 RW1 根目录）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

RW1 = Path(__file__).resolve().parent.parent
SUBDIRS = ["图片上", "图片下"]
SUFFIX = ".annotation.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=RW1 / "dataset.jsonl",
        help="输出 jsonl 路径",
    )
    args = ap.parse_args()

    lines: list[str] = []
    for sub in SUBDIRS:
        d = RW1 / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.name.endswith(SUFFIX):
                continue
            ann = f.with_name(f.name + SUFFIX)
            if not ann.is_file():
                continue
            data = json.loads(ann.read_text(encoding="utf-8"))
            lines.append(json.dumps(data, ensure_ascii=False))

    args.output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"写入 {args.output}，共 {len(lines)} 条")


if __name__ == "__main__":
    main()
