# 岩芯「碎裂/破碎」标注与导出约定（schema v1.0）

## 阳性判定（用于人工整图结论）

- **碎裂/破碎（阳性）**：下列 **任一** 成立即可判为碎裂（可与 ROI 证据类型对应）。
  1. 岩芯完整性被破坏，出现明显裂缝。
  2. 岩芯发生断块、掉块，连续性中断。
  3. 碎块化 / 粉化，失去原有圆柱形态。
- **未碎裂（阴性）**：以上均不明显。
- **不确定**：成像不清、遮挡、边界样本 — **保留该类**，训练时可剔除或单独建模。

## ROI 与证据类型

- **整图三态标签**（必选）：`未碎裂` | `碎裂` | `不确定`。
- **ROI（可选）**：若已观察到明确证据，建议框选区域并选择证据类型，便于模型解释与后续检测类任务；无 ROI 不影响保存。
- **证据类型 `evidence`（英文枚举，便于程序处理）**：
  - `crack` — 裂缝 / 完整性破坏
  - `block_loss` — 断块、掉块、连续性中断
  - `pulverized` — 碎块化、粉化、形态丧失

## 测量

- **拖拽测距**：折线或多段，结果为 **像素长度之和 `length_px`**（相对于原图宽高）。
- **物理尺度（可选）**：若配置 `pixels_per_mm`，可由脚本换算 mm；标注文件仅存像素。

## 文件夹与钻孔对应

| 目录名（RW1 下） | `drill_hole` 取值 |
|------------------|-------------------|
| `图片上`         | `上钻孔`          |
| `图片下`         | `下钻孔`          |

## 侧车标注文件

- 与图片同目录，文件名为：`<原文件名>.annotation.json`（例：`a.jpg` → `a.jpg.annotation.json`）。

## 字段说明（`schema_version` = `1.0`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `schema_version` | string | 如 `"1.0"` |
| `image_path` | string | 相对 `RW1` 的正斜杠路径，如 `图片上/xx.jpg` |
| `drill_hole` | string | `上钻孔` 或 `下钻孔` |
| `image_label` | string | `未碎裂` \| `碎裂` \| `不确定` |
| `regions` | array | 可选。元素含 `id`, `evidence`, `geometry` |
| `geometry` | object | `type`: `rect`；`xyxy`: 原图像素坐标 `[x1,y1,x2,y2]` 整数 |
| `measurements` | array | 可选。元素含 `id`, `points`, `length_px` |
| `points` | array | `[[x,y], ...]` 原图像素坐标 |
| `notes` | string | 备注 |
| `annotator` | string | 可选 |
| `updated_at` | string | ISO8601 |

## 示例

```json
{
  "schema_version": "1.0",
  "image_path": "图片上/example.jpg",
  "drill_hole": "上钻孔",
  "image_label": "碎裂",
  "regions": [
    {
      "id": "r0",
      "evidence": "crack",
      "geometry": { "type": "rect", "xyxy": [120, 80, 400, 220] }
    }
  ],
  "measurements": [
    {
      "id": "m0",
      "points": [[100, 200], [180, 210], [200, 300]],
      "length_px": 126.4
    }
  ],
  "notes": "",
  "annotator": "",
  "updated_at": "2026-05-08T12:00:00"
}
```

## 训练划分注意

- 按 **钻孔**（`drill_hole`）分层划分 train/val/test，避免同孔同时出现在训练与测试集。
