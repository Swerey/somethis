---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: f67ee163a87ef462dc0fdbc04c8fed0b_1c153b83cde211f1b307525400393706
    ReservedCode1: A+YrIlXFEUiy35Eqjuaql6suxa3pAAcEtKtsPzw1ner/L/W2LEtS5ALs8bjFhncKP4/eaSv1UEzVES5Yaw7UkMGTayS5HRkuL1OJ/GJ/H4GUKlTkTnwQ8aamzQTRHyeSX9S3LMASRt/bxJVaJ/KHc5HErddFWiXE60+HUet2DGrt1lGkLU+Wf7jpUYE=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: f67ee163a87ef462dc0fdbc04c8fed0b_1c153b83cde211f1b307525400393706
    ReservedCode2: A+YrIlXFEUiy35Eqjuaql6suxa3pAAcEtKtsPzw1ner/L/W2LEtS5ALs8bjFhncKP4/eaSv1UEzVES5Yaw7UkMGTayS5HRkuL1OJ/GJ/H4GUKlTkTnwQ8aamzQTRHyeSX9S3LMASRt/bxJVaJ/KHc5HErddFWiXE60+HUet2DGrt1lGkLU+Wf7jpUYE=
---

# Docker 化部署说明（批次四）

## 架构

```
浏览器 ──> backend(8080) ──> recognizer(8000)  弹幕违规识别服务（BERT/OCR）
              │
              └──> redis(6379)                 热词榜缓存（可选，PLATFORM_REDIS_ENABLED=1 启用）
```

- `backend`：平台后端（FastAPI，多 worker=2，SQLite WAL）
- `recognizer`：违规识别服务（transformers + onnxruntime + RapidOCR）
- `redis`：热词榜缓存后端

## 前置条件

- Docker Engine 20.10+ / Docker Desktop
- `recognizer/outputs/` 下有已微调模型权重（serve.py 的 `OUTPUT_DIR`，默认 `recognizer/outputs`）

## 一键启动

```bash
docker compose up -d --build
```

- 平台：http://localhost:8080
- 识别服务：http://localhost:8000/docs
- 默认管理员：admin / admin123

## 数据与持久化

| 挂载卷 | 宿主目录 | 内容 |
|--------|----------|------|
| /app/data | ./data | SQLite 数据库 |
| /app/static | ./static | 前端页面 + 上传视频/封面 |
| /app/uploads | ./uploads | 上传目录（兼容保留） |
| /app/logs | ./logs | JSON 结构化日志 |
| /app/recognizer/outputs | ./recognizer/outputs | 模型权重 |

## 单独构建

```bash
docker build -t somewhere-backend -f Dockerfile .
docker build -t somewhere-recognizer -f Dockerfile.recognizer .
```

## 环境变量（backend，均可用 env 覆盖）

| 变量 | 默认（容器内） | 说明 |
|------|----------------|------|
| PLATFORM_PORT | 8080 | 后端端口 |
| AUDIT_SERVICE_URL | http://recognizer:8000 | 识别服务地址 |
| BADWORD_DICT | /app/recognizer/badword_variants.json | 违规词词典 |
| DATABASE_PATH | /app/data/hupu.db | 数据库路径 |
| PLATFORM_LOG_DIR | /app/logs | 日志目录 |
| PLATFORM_REDIS_ENABLED | 1 | 是否启用 Redis 热词缓存 |
| PLATFORM_REDIS_URL | redis://redis:6379/0 | Redis 连接串 |
| PLATFORM_WORKERS | 2 | uvicorn worker 数 |

## 注意

- recognizer 镜像默认安装 CPU 版 PyTorch；需要 GPU 推理时改 `recognizer/requirements.txt` 的 torch 为 cu 版本并给容器透传 GPU。
- 首次启动 recognizer 若离线加载模型，设置 `TRANSFORMERS_OFFLINE=1`（镜像已默认），确保模型文件在挂载的 outputs 中。
*（内容由AI生成，仅供参考）*
