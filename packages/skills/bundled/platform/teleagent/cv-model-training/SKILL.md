---
name: cv-model-training
description: YOLOv8 model training and inference API deployment in Docker containers. Covers data preparation, training configuration, inference server setup, and common pitfalls like class id mismatch and stale cache files.
name_cn: CV二开小助手
description_cn: 在Docker容器中训练YOLOv8模型并部署推理API服务，涵盖数据集准备、训练配置、推理服务搭建及常见问题排查。
AIGC:
  ContentProducer: 001191110102MAD55U9H0F10002
  ContentPropagator: 001191110102MAD55U9H0F10002
  Label: '1'
  ProduceID: 41f54c30-529c-4591-8d2c-3905a6c46d6b
  PropagateID: 41f54c30-529c-4591-8d2c-3905a6c46d6b
  ReservedCode1: f7c46992-165b-4e37-a4fa-0a41d7360c1a
  ReservedCode2: f7c46992-165b-4e37-a4fa-0a41d7360c1a
---
# CV模型训练与推理部署

## 适用场景

- 使用 Ultralytics YOLOv8 在 Docker 容器中训练自定义目标检测模型
- 将训练好的模型部署为 FastAPI 推理服务（文件上传 / Base64 接口）
- 排查训练与推理过程中的常见问题

## 环境准备

### Docker 镜像加载与启动

```bash
# 加载 ultralytics 官方镜像
docker load -i ultralytics-python.tar

# 启动容器（docker-compose.yaml 已配置 volume 挂载）
docker compose up -d

# 进入容器
docker exec -it yolo-python bash
```

### Docker Volume 自动同步

`docker-compose.yaml` 中 `volumes: - ./workspace:/workspace` 将本地目录挂载到容器。
**本地文件修改自动同步到容器内**，无需重新 build 镜像或重启容器。
在本地替换数据集后，进容器直接确认即可：

```bash
ls /workspace/data/train/images/ | wc -l
cat /workspace/config/data_custom.yaml
```

### 推理服务依赖安装

ultralytics 镜像默认不含 Web 框架，推理 API 需额外安装：

```bash
pip install uvicorn fastapi python-multipart tensorboard
```

## 目录结构

```
/workspace
├── config/     # YAML 配置文件（训练参数、数据集路径、推理参数）
├── data/       # 数据集（train/val/test，每个含 images/ 和 labels/）
├── models/     # 预训练模型权重（yolov8n.pt 等）
├── output/     # 训练输出（模型权重、曲线图、验证结果）
├── scripts/    # 训练、推理、调优 Python 脚本
└── logs/       # TensorBoard 日志
```

## 数据集准备

### YOLO 标注格式

每张图片对应一个同名 `.txt` 标注文件，每行格式：

```
class_id  center_x  center_y  width  height
```

- `class_id` 从 0 开始，**必须与 `data.yaml` 中 `names` 的类别数量一致**
- 坐标值已归一化到 0~1

### 数据集配置文件 (data.yaml)

```yaml
path: /workspace/data       # 数据集根目录（容器内绝对路径）
train: train/images         # 训练集图片目录（相对于 path）
val: val/images             # 验证集图片目录（相对于 path）
names:
  0: fire                   # 类别名，key 从 0 开始连续编号
```

> 修改类别数量时，**必须同步检查所有标注文件中的 class id**，详见下方常见问题。

## 训练

### 命令行训练

```bash
yolo detect train model=/workspace/models/yolov8n.pt \
  data=/workspace/config/data.yaml epochs=10 imgsz=640 batch=2 device=cpu
```

### 脚本训练（读取 YAML 配置）

```bash
python /workspace/scripts/train_custom.py
```

训练结果保存在 `/workspace/output/<experiment_name>/`，最佳模型为 `weights/best.pt`。

### 关键训练参数

| 参数 | 说明 | CPU 建议值 |
|------|------|-----------|
| epochs | 训练轮数 | 50~100（10 轮仅验证流程） |
| batch | 批次大小 | 2~4 |
| imgsz | 输入图片尺寸 | 640 |
| device | 训练设备 | cpu |
| workers | DataLoader 进程数 | 0（容器内避免子进程问题） |

## 推理

### 命令行推理

```bash
yolo detect predict model=/workspace/models/yolov8n.pt \
  source=image.jpg conf=0.25 device=cpu
```

### API 推理服务

```bash
# 启动推理服务（前台运行，保持终端开启）
python /workspace/scripts/infer_custom.py
```

看到 `推理服务启动: http://0.0.0.0:8000` 后，**另开一个终端**测试：

```bash
# 健康检查
curl http://localhost:8000/healthz

# 文件上传推理
curl -X POST http://localhost:8000/predict/file \
  -F "file=@/workspace/data/test/images/15.jpg"
```

### 从宿主机访问容器服务

需在 `docker-compose.yaml` 中取消端口映射注释：

```yaml
ports:
  - "8000:8000"
```

然后 `docker compose up -d` 重启容器。容器内部 curl 不需要端口映射。

### 推理结果保存

在推理配置文件中添加：

```yaml
save_result: true
save_dir: /workspace/output/infer_results
```

推理后图片（带检测框标注）会保存到指定目录，文件名加时间戳防覆盖。

## 常见问题排查

### ⚠️ IndexError: index N is out of bounds for dimension 1 with size M

**原因**：标注文件中存在 class id 超出 `data.yaml` 中定义的类别数量。例如配置了 1 个类（仅 id 0），但标注文件中有 class id 1。此错误在**验证阶段**触发，训练阶段可能正常完成第一个 epoch。

**排查**：扫描所有标注文件，统计 class id 分布：

```bash
# 容器内执行
for f in /workspace/data/*/labels/*.txt; do
  [ "$(basename $f)" = "classes.txt" ] && continue
  cut -f1 "$f"
done | sort | uniq -c
```

**修复**：

```bash
# 1. 将超出范围的 class id 改为有效值（如将 1 改为 0）
sed -i 's/^1\t/0\t/g' /workspace/data/val/labels/*.txt
sed -i 's/^1\t/0\t/g' /workspace/data/test/labels/*.txt

# 2. 删除旧缓存（必须！否则 YOLO 读取旧缓存，修复不生效）
rm -f /workspace/data/train/labels.cache
rm -f /workspace/data/val/labels.cache
```

> **关键点**：修改标注文件后必须删除 `labels.cache`，YOLO 会缓存标注扫描结果，不删缓存则修改不生效。

### ⚠️ curl: Failed to connect to localhost port 8000

**原因**：推理服务未启动，或修改了配置但未重启服务。

**修复**：

```bash
# 确保推理服务正在运行
python /workspace/scripts/infer_custom.py
```

> 模型在服务启动时一次性加载，修改配置文件后必须 Ctrl+C 停掉再重新启动。

### ⚠️ ModuleNotFoundError: No module named 'uvicorn'

**原因**：ultralytics 镜像不含 Web 框架依赖。

**修复**：

```bash
pip install uvicorn fastapi python-multipart
```

### ⚠️ 推理结果 count=0（无检测）

按以下顺序排查：

1. **确认推理服务加载的是最新模型**：检查 `infer_custom.yaml` 中 `model` 路径是否指向最新训练结果（如 `custom_train-4/weights/best.pt`）
2. **修改配置后重启服务**：Ctrl+C → 重新 `python /workspace/scripts/infer_custom.py`
3. **降低置信度阈值**：将 `conf` 从 0.25 降到 0.05 测试，如果仍为 0 则模型确实未学到
4. **检查训练精度**：查看 `output/<experiment>/results.csv` 和 `confusion_matrix.png`
5. **精度过低时增加训练**：`sed -i 's/epochs: 10/epochs: 50/' train_custom.yaml` 后重新训练

### ⚠️ 模型精度低

常见原因与改进方向：

| 原因 | 改进方法 |
|------|----------|
| 数据量太少（<50 张） | 每类至少 100~500 张标注图片 |
| 训练轮数不足 | CPU 50~100 轮，GPU 100~300 轮 |
| 缺少负样本 | 添加不含目标的图片（夕阳、路灯、烟囱等易误报场景） |
| 模型未收敛 | 查看 loss 曲线，若仍在下降则增加 epochs |
| 类别不平衡 | 确保各类样本数量均衡 |

**诊断方法**：
- `results.csv`：查看 precision、recall、mAP50、mAP50-95 逐轮变化
- `confusion_matrix.png`：查看各类别间的误判分布
- `BoxPR_curve.png`：查看 PR 曲线和 AP 值
- `val_batch0_pred.jpg`：查看验证集预测可视化

### ⚠️ 推理结果图片未保存（saved_image: null）

检查配置文件是否包含保存参数：

```yaml
save_result: true
save_dir: /workspace/output/infer_results
```

修改配置后需重启推理服务。

## 置信度阈值说明

| 阈值 | 效果 |
|------|------|
| 0.25（默认） | 宽松，检出多但误报多 |
| 0.5 | 适中，平衡检出和误报 |
| 0.7 | 严格，只保留高置信度框 |
| 1.0 | 极端，几乎不输出结果 |

取值范围 0~1，每次修改后需重启推理服务生效。

## 配置文件集中管理

所有关键参数集中在 YAML 配置文件中，脚本只负责读取配置并执行，改参数不需要改代码：

| 配置文件 | 作用 |
|----------|------|
| `config/data_custom.yaml` | 数据集路径与类别定义 |
| `config/train_custom.yaml` | 训练参数（模型、轮数、批次等） |
| `config/infer_custom.yaml` | 推理参数（模型路径、端口、置信度等） |