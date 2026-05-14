# 岩芯碎裂标注与训练（RW1）

约定见 [ANNOTATION_SPEC.md](ANNOTATION_SPEC.md)。

## 1. 启动标注工具

```bash
cd RW1/annotator
pip install -r requirements.txt
python server.py
```

浏览器打开 `http://127.0.0.1:5050`。标注保存为图片同目录下的 `<文件名>.annotation.json`。

## 2. 数据盘点（可选）

```bash
pip install Pillow
python RW1/scripts/inventory.py
```

生成 `RW1/inventory_stats.json`。

## 3. 合并与校验

```bash
python RW1/scripts/merge_annotations.py
python RW1/scripts/validate_dataset.py RW1/dataset.jsonl
```

## 4. 划分数据集

```bash
python RW1/scripts/split_by_hole.py RW1/dataset.jsonl
```

输出 `RW1/splits/train.txt` 等。

## 5. 基线训练

```bash
pip install -r RW1/training/requirements.txt
python RW1/training/train_baseline.py --exclude-uncertain --epochs 15
```

首次运行会下载 MobileNet 预训练权重；权重保存到 `RW1/training/baseline_weights.pt`。
