"""按钻孔分层划分 train/val/test：每个钻孔内打乱后再按比例切分。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

RW1 = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path, nargs="?", default=RW1 / "dataset.jsonl")
    ap.add_argument("--train", type=float, default=0.7)
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--out-dir", type=Path, default=RW1 / "splits")
    args = ap.parse_args()

    if abs(args.train + args.val + args.test - 1.0) > 1e-6:
        print("train+val+test 须为 1", file=sys.stderr)
        sys.exit(1)

    if not args.jsonl.is_file():
        print("缺少", args.jsonl, file=sys.stderr)
        sys.exit(1)

    by_hole: dict[str, list[str]] = defaultdict(list)
    for line in args.jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        rel = o.get("image_path")
        hole = o.get("drill_hole")
        if isinstance(rel, str) and isinstance(hole, str):
            by_hole[hole].append(rel)

    rnd = random.Random(args.seed)
    splits = {"train": [], "val": [], "test": []}

    for hole in sorted(by_hole.keys()):
        paths = by_hole[hole][:]
        rnd.shuffle(paths)
        n = len(paths)
        if n == 0:
            continue
        n_train = int(n * args.train)
        n_val = int(n * args.val)
        n_test = n - n_train - n_val
        i = 0
        t_paths = paths[i : i + n_train]
        i += n_train
        v_paths = paths[i : i + n_val]
        i += n_val
        te_paths = paths[i:]
        splits["train"].extend([(hole, p) for p in t_paths])
        splits["val"].extend([(hole, p) for p in v_paths])
        splits["test"].extend([(hole, p) for p in te_paths])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        out = args.out_dir / f"{name}.txt"
        out.write_text(
            "\n".join(f"{h}\t{p}" for h, p in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        print(f"{name}: {len(rows)} -> {out}")


if __name__ == "__main__":
    main()
