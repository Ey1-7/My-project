"""整图分类基线：读取 dataset.jsonl，MobileNetV3-Small。"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

RW1 = Path(__file__).resolve().parent.parent
LABEL_TO_IDX = {"未碎裂": 0, "碎裂": 1, "不确定": 2}


class JsonlDataset(Dataset):
    def __init__(
        self,
        entries: list[tuple[str, str]],
        rw1: Path,
        tfm,
        exclude_uncertain: bool,
        binary: bool,
    ) -> None:
        self.rw1 = rw1
        self.tfm = tfm
        ann_map = _load_annotations_jsonl(rw1 / "dataset.jsonl")
        rows: list[tuple[str, str, int]] = []
        two_cls = binary or exclude_uncertain
        for hole, rel in entries:
            rec = ann_map.get(rel)
            if not rec:
                continue
            lab = rec.get("image_label")
            if lab not in LABEL_TO_IDX:
                continue
            if two_cls:
                if lab == "不确定":
                    continue
                idx = 0 if lab == "未碎裂" else 1
            else:
                idx = LABEL_TO_IDX[lab]
            rows.append((hole, rel, idx))
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        hole, rel, y = self.rows[i]
        path = self.rw1 / rel
        im = Image.open(path).convert("RGB")
        x = self.tfm(im)
        return x, y, hole


def _load_annotations_jsonl(path: Path) -> dict[str, dict]:
    m: dict[str, dict] = {}
    if not path.is_file():
        return m
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        p = o.get("image_path")
        if isinstance(p, str):
            m[p] = o
    return m


def load_split(path: Path) -> list[tuple[str, str]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rw1", type=Path, default=RW1)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--exclude-uncertain", action="store_true")
    ap.add_argument("--binary", action="store_true", help="二分类：未碎裂 vs 碎裂（排除不确定）")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    split_dir = args.rw1 / "splits"
    train_e = load_split(split_dir / "train.txt")
    val_e = load_split(split_dir / "val.txt")

    tfm_train = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.1, 0.1, 0.1, 0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    tfm_val = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_ds = JsonlDataset(train_e, args.rw1, tfm_train, args.exclude_uncertain, args.binary)
    val_ds = JsonlDataset(val_e, args.rw1, tfm_val, args.exclude_uncertain, args.binary)
    n_cls = 2 if (args.binary or args.exclude_uncertain) else 3

    if len(train_ds) == 0 or len(val_ds) == 0:
        print(
            "训练或验证集为空。请先：标注并 merge 生成 dataset.jsonl，再运行 scripts/split_by_hole.py"
        )
        return

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=False
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        w = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
        m = models.mobilenet_v3_small(weights=w)
    except Exception:
        m = models.mobilenet_v3_small(weights=True)  # type: ignore[arg-type]
    m.classifier[3] = nn.Linear(m.classifier[3].in_features, n_cls)
    m = m.to(device)

    opt = torch.optim.AdamW(m.parameters(), lr=args.lr)
    crit = nn.CrossEntropyLoss()

    for epoch in range(1, args.epochs + 1):
        m.train()
        total = 0
        correct = 0
        for x, y, _ in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = m(x)
            loss = crit(logits, y)
            loss.backward()
            opt.step()
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += y.numel()

        m.eval()
        v_correct = 0
        v_total = 0
        per_hole = {}
        with torch.no_grad():
            for x, y, holes in val_loader:
                x, y = x.to(device), y.to(device)
                logits = m(x)
                pred = logits.argmax(dim=1)
                v_correct += (pred == y).sum().item()
                v_total += y.numel()
                for i in range(y.size(0)):
                    h = holes[i]
                    per_hole.setdefault(h, [0, 0])
                    per_hole[h][1] += 1
                    if pred[i] == y[i]:
                        per_hole[h][0] += 1

        tr_acc = correct / max(1, total)
        va_acc = v_correct / max(1, v_total)
        print(f"epoch {epoch:02d}  train_acc={tr_acc:.4f}  val_acc={va_acc:.4f}")
        for h, (c, t) in sorted(per_hole.items()):
            print(f"    val [{h}] acc={c / max(1, t):.4f} (n={t})")

    out_path = args.rw1 / "training" / "baseline_weights.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": m.state_dict(), "n_cls": n_cls, "binary": args.binary}, out_path)
    print("已保存", out_path)


if __name__ == "__main__":
    main()
