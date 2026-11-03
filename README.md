# SomeWhere 社区（直播弹幕多维度违规内容轻量化实时识别系统）

虎扑式综合交流社区平台，以**自主训练的弹幕违规识别模型**为核心，对帖子全文 / 评论 / 弹幕 / 视频标题与描述 / 直播弹幕进行统一的多维度违规审核与处置。后端采用 FastAPI + SQLite + JWT（HS256），前端为原生 HTML/CSS/JS；识别模型为 `bert-base-chinese` 微调的六分类模型（自主训练，**不依赖第三方商用 AI 服务**），OCR 使用**自部署 RapidOCR**（`rapidocr_onnxruntime`），支持 ONNX int8 量化轻量部署（CPU 推理）。

- 平台地址：`http://127.0.0.1:8080`
- 识别服务：`http://127.0.0.1:8000`（`/health`、`/predict`、`/ocr`）
- 数据库：`data/hupu.db`（SQLite，启动自动建表）

## 核心功能

| 功能 | 说明 |
|---|---|
| 多维度违规审核 | 六分类标签：正常 / 色情低俗 / 辱骂暴力 / 广告引流 / 敏感言论 / 歧视煽动；审核链路：违规词变体词典快判（谐音/拼音/数字替换/去标点）→ 模型识别 → 本地规则降级兜底 |
| 四类处置 | 高危（色情低俗/敏感言论）→ **拦截不展示**（blocked）；中危（辱骂暴力/歧视煽动）→ **折叠显示**（folded）；低危（广告引流）→ **提示展示**（warned）；管理员确认 → **封禁**（banned） |
| 存疑队列人工审核 | 模型置信度不足的内容先放行展示、同步进入审核队列（review_queue），超时（24 小时）自动折叠（`audit/pipeline.py::auto_fold_expired`）；管理端 `review_queue.html` 处理 |
| 信用分体系 | 高危扣 5 分、中危扣 3 分、低危扣 1 分；每发布 1 条通过审核的内容恢复 1 分（每日上限 3 分、满分 100）；个人中心 `me.py` 查看流水 |
| 违规记录与审计 | `violations` 表记录每次违规（含来源：帖子/评论/视频评论/弹幕/视频/直播）；`audit_log` 记录模型拦截、词典拦截、存疑上报、人工处置等关键节点 |
| 违规热词榜 | `/api/banned-words/top` 实时返回被拦次数 Top10、今日拦截量/拦截率/平均延迟；进程内 TTL 缓存 + 定时刷新，可切换 Redis 后端 |
| 审核工作台 | `admin.html`：违规队列、六类分布柱状图、近 7 天拦截趋势、违规记录分页、用户封禁、审计日志、违规词管理、直播间管理 |
| 视频与弹幕 | 视频上传（标题/描述审核）、视频审核流（pending/approved/rejected）、播放页弹幕层 + 违规弹幕拦截演示 |
| 直播弹幕实时识别 | 直播间 CRUD / 开播 / 停播 / 治理（踢出 kick / 禁言 mute）；WebSocket `/api/live/{room_id}/ws` 实时弹幕审核；WebSocket `/api/live/{room_id}/video/ws` 进行 MJPEG 视频帧转发（主播截帧推流 → 观众渲染），配合 RapidOCR 屏幕 OCR 识别画面内容 |
| 举报与申诉 | 用户一键举报（弹幕/评论/视频/帖子/直播弹幕），举报次数作为人工审核加权信号；用户可对处置结果申诉，管理端复核 |
| 管理后台 | 用户管理、视频审核、存疑队列、违规记录、统计、审计日志、违规词库、首页轮播图管理 |

审核范围覆盖：帖子全文、评论、视频标题与描述、点播弹幕、直播弹幕。

## 技术栈

- **后端**：Python 3.11、FastAPI、Uvicorn、SQLite（标准库 sqlite3，WAL）、PyJWT（HS256，7 天有效期，密钥 `data/jwt_secret.txt` 持久化）、Pydantic、Redis（可选，热词榜缓存）
- **识别服务**：PyTorch（GPU 优先）、transformers（`bert-base-chinese` 微调）、ONNX Runtime（int8 量化 CPU 轻量部署，`SERVE_BACKEND=onnx`）、RapidOCR（`rapidocr_onnxruntime`，自部署）、OpenCV
- **前端**：原生 HTML/CSS/JS（暗色风格）、Chart.js（CDN）、Service Worker（`sw.js`）
- **部署**：Docker / Docker Compose（backend + recognizer + redis 三容器编排，见 `README-DOCKER.md`）

## 目录结构

```
系统/
├── README.md                    # 项目说明（本文件）
├── README-DOCKER.md             # Docker 化部署说明
├── Dockerfile                   # 平台后端镜像
├── Dockerfile.recognizer        # 识别服务镜像（权重经 volume 挂载，不打包进镜像）
├── docker-compose.yml           # 一键编排 backend + recognizer + redis
├── .gitignore / .dockerignore
├── start_all.bat                # 一键启动：先起识别服务(8000)再起平台(8080)
├── start.bat                    # 启动脚本（识别服务 + 平台）
├── stop.bat / stop_all.bat      # 停止脚本（按监听端口 8000/8080 结束进程）
│
├── backend/                     # 平台后端（FastAPI，端口 8080）
│   ├── main.py                  # 入口：路由注册/CORS/静态挂载/健康检查/JSON 结构化日志
│   ├── config.py                # 集中配置（端口/识别服务地址/词典/数据库/日志，env 可覆盖）
│   ├── db.py                    # SQLite 连接与建表（users/videos/posts/comments/danmaku/video_comments/violations/post_likes/follows/review_queue/live_rooms/live_messages/carousel_items/appeals/credit_log/audit_log/live_bans/banned_words/reports）+ 默认 admin
│   ├── models.py                # 信用分规则、内容状态枚举、六分类标签与风险等级映射
│   ├── auth.py                  # 注册/登录/JWT(HS256) 签发校验、get_current_user / require_admin
│   ├── seed_data.py / seed_rich.py   # 种子数据（用户/帖子/视频/直播间，已有数据时跳过）
│   ├── audit_logs.py
│   ├── audit/                   # 违规审核管线
│   │   ├── rules.py             # 违规词变体词典快判 + 本地特征正则降级
│   │   ├── engine.py            # 调用识别服务 /predict（线程局部长连接、超时容错、延迟采样）
│   │   └── pipeline.py          # 审核管线：词典命中即定级 → 模型识别 → 存疑上报/信用分/审计
│   ├── routers/                 # 12 个路由模块（全部挂载于 /api 前缀）
│   │   ├── auth.py              # /api/auth/register | login | me
│   │   ├── posts.py             # 帖子/评论/点赞/关注/实时预检/活跃用户榜
│   │   ├── videos.py            # 视频上传/列表/详情/评论/文件流
│   │   ├── danmaku.py           # 弹幕发送/批量/拉取（异步审核：先展示后处置）
│   │   ├── live.py              # 直播间 CRUD/开停播/禁言/踢出 + WS 弹幕 + WS MJPEG 帧转发
│   │   ├── admin.py             # 视频审核/存疑队列/用户管理/违规记录/统计/审计日志/违规词/直播间/申诉复核
│   │   ├── banned_words.py      # 违规热词榜 /api/banned-words/top
│   │   ├── appeals.py           # 申诉提交 / 我的申诉列表
│   │   ├── reports.py           # 举报提交 / 管理端举报处置
│   │   ├── carousel.py          # 首页轮播图（含管理端维护）
│   │   ├── users.py             # 他人主页公开资料/帖子/视频
│   │   └── me.py                # 个人中心信用分与流水
│   └── requirements.txt
│
├── recognizer/                  # 弹幕违规识别服务（FastAPI，端口 8000）
│   ├── serve.py                 # 服务入口：/predict 六分类、/ocr（RapidOCR）、/health；PyTorch/ONNX 双后端
│   ├── config.py                # 模型配置（bert-base-chinese，MAX_LEN=128，6 类标签映射，训练超参）
│   ├── badword_variants.json    # 违规词变体词典（谐音/拼音/数字替换）
│   ├── augment_data.py          # 训练数据增强
│   ├── bench_predict.py         # 推理延迟基准
│   ├── eval_compare.py / eval_compare_extra.py   # 模型横向对比评估
│   ├── export_onnx.py           # ONNX 导出（fp32 / int8 量化）
│   ├── screen_ocr_tool.py       # 屏幕选区 OCR 工具
│   ├── test_ocr_pipeline.py     # OCR 管线自检
│   ├── requirements.txt
│   ├── static/                  # 识别服务可视化演示页（index.html / screen.html）
│   └── outputs/                 # 训练产出（不入库，见注意事项）
│       ├── bert_baseline / bert_improved / bert_improved_aug / bilstm / textcnn   # 各模型 checkpoint
│       ├── onnx/                # model_fp32.onnx / model_int8.onnx（轻量 CPU 后端）
│       └── eval / summary       # 评估结果与汇总
│
├── static/                      # 前端静态资源（原生 HTML/JS/CSS，?v= 版本化）
│   ├── index.html               # 主页：信息流（最新/精华）、帖子热榜、违规热词榜、平台健康度、活跃用户榜、底部拦截滚动条
│   ├── live_list.html / live_room.html     # 直播列表 / 直播间（弹幕实时识别 + 视频帧渲染）
│   ├── video.html / video_list.html / video_review.html   # 视频播放/列表/审核
│   ├── post.html / publish.html            # 帖子详情 / 发布 + 实时预检
│   ├── review_queue.html / admin.html      # 存疑审核队列 / 审核工作台（统计图表）
│   ├── audit_logs.html          # 审计日志列表（筛选/分页）
│   ├── user_manage.html / user_page.html / profile.html   # 用户管理 / 他人主页 / 个人中心
│   ├── login.html               # 登录/注册
│   ├── common.css / common.js / ui.js / api.js / icons.js
│   └── sw.js                    # Service Worker
│
├── datasets/                    # 训练数据集（不入库）
│   ├── processed_v2/            # train/dev/test/all/train_aug.jsonl、类别分布图、README
│   ├── csv/ raw_data/ scripts/ configs/
├── data/                        # 运行时数据（不入库）
│   ├── hupu.db                  # SQLite 数据库（平台数据）
│   ├── jwt_secret.txt           # JWT 密钥（自动生成，不入库）
│   └── *.log                    # 平台/识别服务运行日志
├── uploads/                     # 用户上传（视频/封面，不入库）
├── tests/
│   └── test_smoke.py            # pytest 冒烟测试（临时库，不污染 data/hupu.db）
├── scripts/
│   └── bump_version.py          # 前端 ?v= 版本号自动升级脚本
└── logs/ / temp/ / workspace/   # 运行日志与临时目录
```

## 启动步骤

### 方式一：一键启动（推荐）

双击项目根目录 `start_all.bat`：

1. 先启动弹幕违规识别服务（`recognizer/serve.py`，端口 8000，使用 `torch_gpu` 环境 `D:\rgzn\1\envs\torch_gpu\python.exe`）；
2. 再启动平台后端（`backend/main.py`，端口 8080，单 worker，Windows 固定单 worker 启动）；
3. 浏览器访问 `http://127.0.0.1:8080`。

`start.bat` 同样可一键启动两服务（按 `SERVE_PORT=8000` / `PLATFORM_PORT=8080` 配置，端口可改，需与 `backend/config.py` 保持一致）。

### 停止服务

双击 `stop.bat`（或 `stop_all.bat`）：按监听端口结束占用 8000（识别）与 8080（平台）的进程，不影响其他程序。

### 方式二：Docker 部署

```bash
docker compose up -d --build
```

平台 `http://localhost:8080`，识别服务 `http://localhost:8000/docs`。详细见 `README-DOCKER.md`。

### 环境要求

- 识别服务依赖 `recognizer/requirements.txt`（torch、transformers、onnxruntime、rapidocr_onnxruntime、opencv 等），并需在 `recognizer/outputs/` 下存在已微调模型权重（见注意事项）；
- 平台后端依赖 `backend/requirements.txt`（fastapi、uvicorn、PyJWT、Pillow、python-multipart 等）；
- 前端 Chart.js 使用 CDN（需联网），离线环境可替换为本地文件。

## 测试账号

| 账号 | 密码 | 角色 | 说明 |
|---|---|---|---|
| admin | admin123 | 管理员 | `backend/db.py` 启动时自动创建，信用分 100 |
| shuishui / awei / yingmi / dianmao / wanjia | 123456 | 普通用户 | `backend/seed_data.py` 种子用户 |

登录入口：`http://127.0.0.1:8080/login.html`。

## 配置项（backend/config.py，均可用环境变量覆盖）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| PLATFORM_PORT | 8080 | 平台后端端口 |
| AUDIT_SERVICE_URL | http://127.0.0.1:8000 | 识别服务基础地址 |
| AUDIT_SERVICE_TIMEOUT | 5 | 识别服务调用超时（秒） |
| BADWORD_DICT | recognizer/badword_variants.json | 违规词变体词典路径 |
| HUPU_DB_PATH | data/hupu.db | SQLite 数据库路径（测试可指向临时库） |
| PLATFORM_LOG_DIR | backend/logs | 日志目录（platform.log 按天轮转） |
| PLATFORM_LOG_BACKUP_DAYS | 7 | 日志保留天数 |
| PLATFORM_WORKERS | 2 | uvicorn worker 数（Windows 下固定单 worker） |
| PLATFORM_LOG_JSON | 1 | 文件日志输出 JSON 结构化 |
| PLATFORM_REDIS_ENABLED / PLATFORM_REDIS_URL | 0 / redis://127.0.0.1:6379/0 | 是否启用 Redis 热词榜缓存 |

## 测试

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\系统
pip install pytest httpx
python -m pytest tests/test_smoke.py -v
```

冒烟测试使用 `HUPU_DB_PATH` 指向临时 SQLite 库，覆盖注册登录、发帖词典拦截、存疑上报、审核处置、上传防护等链路，不污染 `data/hupu.db`。

## 注意事项

1. **识别权重不入库**：`recognizer/outputs/`（模型 checkpoint 与 ONNX 产物）与 `*.safetensors / *.onnx / *.pt / *.pth / *.ckpt / *.bin` 均被 `.gitignore` 排除，不入 Git 仓库。`recognizer/serve.py` 启动时从 `recognizer/outputs/bert_improved/checkpoint-*` 自动加载最优 checkpoint（`SERVE_BACKEND=onnx` 时加载 `recognizer/outputs/onnx/model_int8.onnx`），本地或部署环境需自行准备权重文件。
2. **敏感信息不入库**：`.gitignore` 排除 `data/jwt_secret.txt`、`data/*.db`、`data/*.log`、`*.pem`、`*.key`；JWT 密钥首次启动自动生成于 `data/jwt_secret.txt`（重启不失效）。
3. **数据集与用户上传不入库**：`datasets/`、`uploads/`、`temp/`、`logs/`、`workspace/`、`__pycache__/`、`.pytest_cache/`、`.idea/`、`.vscode/` 均在 `.gitignore` 排除范围。
4. **前端改版需升 `?v=` 版本号**：`static/` 下 CSS/JS 引用带 `?v=YYYYMMDD`，改动前端后执行 `python scripts/bump_version.py [版本号]`（不传则用当天日期）统一替换，避免浏览器缓存旧资源；主后端对版本化静态资源返回长缓存（7 天），HTML 页面 no-cache。
5. **识别服务不可用时平台自动降级**：审核管线调用识别服务失败时自动容错，词典命中仍可拦截，未命中按低危放行，平台不因识别服务故障崩溃（`/api/health` 可查看识别服务在线状态）。
6. **Windows 单 worker**：`main.py` 在 Windows 上固定单 worker 启动（多 worker 会因 socket 重复 listen 触发 WinError 10022），需提升并发时可多实例 + 前置负载均衡。
7. **模型离线加载**：识别服务 tokenizer/checkpoint 使用 `local_files_only=True` 加载，需本机已缓存 `bert-base-chinese` 与微调权重；Docker 镜像默认 `TRANSFORMERS_OFFLINE=1`。
