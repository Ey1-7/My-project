"""本地标注服务：列出 RW1 下钻孔图片、读写侧车 JSON。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

RW1_ROOT = Path(__file__).resolve().parent.parent
HOLE_TO_SUBDIR = {"上钻孔": "图片上", "下钻孔": "图片下"}
SUBDIR_TO_HOLE = {v: k for k, v in HOLE_TO_SUBDIR.items()}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

app = Flask(__name__, static_folder="static", static_url_path="")


def _under_rw1(path: Path) -> bool:
    try:
        path.resolve().relative_to(RW1_ROOT.resolve())
        return True
    except ValueError:
        return False


def rel_posix(p: Path) -> str:
    return p.relative_to(RW1_ROOT).as_posix()


def list_images(hole: str) -> list[str]:
    sub = HOLE_TO_SUBDIR.get(hole)
    if not sub:
        return []
    d = RW1_ROOT / sub
    if not d.is_dir():
        return []
    out: list[str] = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXT:
            out.append(rel_posix(f))
    return out


def annotation_path_for_image(rel: str) -> Path:
    img = RW1_ROOT / rel
    return img.with_name(img.name + ".annotation.json")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/config")
def config():
    return jsonify(
        {
            "schema_version": "1.0",
            "holes": list(HOLE_TO_SUBDIR.keys()),
            "holeDirs": HOLE_TO_SUBDIR,
            "evidence": [
                {"key": "crack", "label": "裂缝/完整性破坏"},
                {"key": "block_loss", "label": "断块掉块/不连续"},
                {"key": "pulverized", "label": "碎块粉化/失形"},
            ],
            "labels": ["未碎裂", "碎裂", "不确定"],
        }
    )


@app.route("/api/images")
def images():
    hole = request.args.get("hole", "上钻孔")
    return jsonify({"images": list_images(hole)})


@app.route("/api/image")
def image():
    rel = request.args.get("path", "")
    path = (RW1_ROOT / rel).resolve()
    if not _under_rw1(path) or not path.is_file():
        return "not found", 404
    return send_file(path)


@app.route("/api/annotation", methods=["GET"])
def get_annotation():
    rel = request.args.get("path", "")
    path = annotation_path_for_image(rel)
    if not path.is_file():
        return jsonify(None)
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.route("/api/annotation", methods=["POST"])
def post_annotation():
    data = request.get_json(force=True)
    rel = data.get("image_path")
    if not rel:
        return jsonify({"error": "image_path required"}), 400
    img_path = (RW1_ROOT / rel).resolve()
    if not _under_rw1(img_path) or not img_path.is_file():
        return jsonify({"error": "bad image_path"}), 400
    first = img_path.relative_to(RW1_ROOT.resolve()).parts[0]
    hole = SUBDIR_TO_HOLE.get(first)
    if hole:
        data["drill_hole"] = hole
    data.setdefault("schema_version", "1.0")
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = annotation_path_for_image(rel)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "saved": rel_posix(out)})


def main():
    print(f"RW1_ROOT = {RW1_ROOT}")
    print("打开浏览器访问 http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
