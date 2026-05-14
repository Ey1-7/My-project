"""扫描 RW1 下「图片上」「图片下」，输出扩展名与分辨率统计。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

RW1 = Path(__file__).resolve().parent.parent
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SKIP_DIRS = {"annotator", "scripts", "training", "splits", "__pycache__"}


def main() -> None:
    report: dict = {"rw1_root": str(RW1), "folders": {}}
    subdirs = sorted(
        [
            p
            for p in RW1.iterdir()
            if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")
        ]
    )
    for d in subdirs:
        sub = d.name
        folder_stat = {"path": sub, "count": 0, "extensions": Counter(), "sizes": [], "errors": []}
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext not in IMAGE_EXT:
                continue
            folder_stat["extensions"][ext] += 1
            folder_stat["count"] += 1
            if _HAS_PIL:
                try:
                    with PILImage.open(f) as im:
                        folder_stat["sizes"].append({"w": im.width, "h": im.height, "file": f.name})
                except OSError as e:
                    folder_stat["errors"].append(f"{f.name}: {e}")
        folder_stat["extensions"] = dict(folder_stat["extensions"])
        if folder_stat["sizes"]:
            ws = [x["w"] for x in folder_stat["sizes"]]
            hs = [x["h"] for x in folder_stat["sizes"]]
            folder_stat["width_range"] = [min(ws), max(ws)]
            folder_stat["height_range"] = [min(hs), max(hs)]
        del folder_stat["sizes"]
        report["folders"][sub] = folder_stat

    out_json = RW1 / "inventory_stats.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_json.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
