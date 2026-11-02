---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: f67ee163a87ef462dc0fdbc04c8fed0b_a9b634d0cc6911f1898e525400248c00
    ReservedCode1: 7++daOfvTfAk8+EI3yIEZpwbpGSzHANRBBJLueCUUYaKeGzKifFdblVz+Y8n0AqEbyASpc10/u6BresjFs1jeRfTx58JiljuF6AsB7JHE7mlmdENPkwQ4iDsP5RK1oTU19ujX/etiTg6ENXKTe4Do3SgaAce6lmM2OnvYXMf6QM3st1Rhxiv8wtOMsU=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: f67ee163a87ef462dc0fdbc04c8fed0b_a9b634d0cc6911f1898e525400248c00
    ReservedCode2: 7++daOfvTfAk8+EI3yIEZpwbpGSzHANRBBJLueCUUYaKeGzKifFdblVz+Y8n0AqEbyASpc10/u6BresjFs1jeRfTx58JiljuF6AsB7JHE7mlmdENPkwQ4iDsP5RK1oTU19ujX/etiTg6ENXKTe4Do3SgaAce6lmM2OnvYXMf6QM3st1Rhxiv8wtOMsU=
---



# 虎扑式综合交流平台（AI 违规审核版）

基于 FastAPI + SQLite + JWT 的可运行骨架，以弹幕违规识别服务为基础，对**帖子全文 / 评论 / 弹幕 / 视频标题与描述**做统一违规审核与处置（高危拦截、中危折叠、低危提示），并配套信用分体系、违规记录、违规热词榜与审核工作台。

## 目录结构

```
系统/
├── start.bat / stop.bat     # 一键启动 / 停止脚本（识别服务 8000 + 平台 8080）
├── tests/
│   └── test_smoke.py        # pytest 冒烟测试（临时库，不污染 data/hupu.db）
├── backend/                 # FastAPI 后端（端口 8080）
│   ├── main.py              # 入口：注册路由 / CORS / 静态挂载 / /api/health / logging 配置
│   ├── config.py            # M6 集中配置：端口/识别服务地址/词典路径/数据库路径/日志轮转
│   ├── db.py                # SQLite 连接 + 建表（users/videos/posts/comments/danmaku/violations/post_likes/follows）+ 默认 admin + 系统操作者
│   ├── models.py            # 信用分规则、内容状态枚举、六分类标签映射
│   ├── auth.py              # 注册/登录/JWT 签发校验、get_current_user / require_admin 依赖
│   ├── audit/               # 违规审核管线
│   │   ├── rules.py         # 词典快判（badword_variants.json）
│   │   ├── engine.py        # 调用识别服务 http://127.0.0.1:8000/predict（超时容错 + 延迟采样）
│   │   └── pipeline.py      # 审核管线：词典命中即拦 → 未命中调模型 → 定级处置 + 信用分联动 + 审计日志
│   └── routers/             # 接口路由
│       ├── auth.py          # /api/auth/register /login /me
│       ├── videos.py        # /api/videos 上传/列表/详情/文件流
│       ├── posts.py         # /api/posts 发帖/列表/详情/评论/点赞/关注/预检/活跃用户榜
│       ├── danmaku.py       # /api/danmaku 发送/批量/拉取
│       ├── admin.py         # /api/admin 拦截记录/统计/审核处置/审计日志（仅管理员）
│       ├── banned_words.py  # /api/banned-words/top 违规热词榜 Top10 + 平台健康度
│       ├── live.py / me.py  # 直播 / 个人中心
│       └── appeals.py       # 申诉
├── static/                  # 原生 HTML/JS 前端（暗色风格，Chart.js）
│   ├── common.css / common.js
│   ├── index.html           # 主界面：导航+板块条、信息流（最新/精华）、帖子热榜、违规热词榜、平台健康度、活跃用户榜、底部拦截滚动条
│   ├── video.html           # 视频播放 + 弹幕层 + 违规弹幕拦截演示
│   ├── post.html            # 帖子详情 + 评论流 + 违规评论折叠显示
│   ├── publish.html         # 发帖 + 视频上传 + 编辑时实时预检
│   ├── admin.html           # 审核工作台：违规队列、六类分布柱状图、拦截趋势折线图
│   ├── audit_logs.html      # 审计日志列表（筛选/分页）
│   └── login.html           # 登录 / 注册
├── data/                    # SQLite 数据库文件（自动创建）
├── uploads/                 # 上传的视频文件（自动创建）
└── README.md
```

## 启动步骤

### 一键启动（推荐）

双击项目根目录 `start.bat`，依次启动识别服务（serve.py:8000）与平台（uvicorn main:app:8080），浏览器访问 `http://127.0.0.1:8080`。
停止：双击 `stop.bat`（按端口 8000/8080 结束进程）。

### 1. 启动识别服务（端口 8000）

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\training
D:\rgzn\1\envs\torch_gpu\python.exe serve.py
```

确认 `http://127.0.0.1:8000/health` 返回 ok。
> 若识别服务未启动，平台审核管线自动容错降级：词典命中仍可拦截，未命中时按低危放行，不影响平台运行。

### 2. 启动平台后端（端口 8080）

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\系统\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8080
```

### 3. 打开前端

浏览器访问 `http://127.0.0.1:8080`，默认管理员账号 `admin / admin123`。

## 配置项（backend/config.py）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| PLATFORM_PORT | 8080 | 平台后端端口 |
| AUDIT_SERVICE_URL | http://127.0.0.1:8000 | 识别服务基础地址 |
| AUDIT_SERVICE_TIMEOUT | 5 | 识别服务调用超时（秒） |
| BADWORD_DICT | training/badword_variants.json | 违规词词典路径 |
| HUPU_DB_PATH | data/hupu.db | 数据库路径（测试可指向临时库） |
| PLATFORM_LOG_DIR | backend/logs | 日志目录（platform.log 按天轮转） |
| PLATFORM_LOG_BACKUP_DAYS | 7 | 日志保留天数 |

## 日志与审计

- 运行日志：`backend/logs/platform.log`，控制台 + 文件双输出，按天轮转保留 7 天；关键审核动作（拦截/折叠/存疑上报/人工处置）均写入。
- 审计日志：`audit_log` 表记录模型拦截、词典拦截、存疑上报、人工 ban/clear、封禁、申诉处理等关键节点，管理端通过 `GET /api/admin/audit-logs`（分页 + 操作者/类型筛选）查看，前端页面 `audit_logs.html`。

## 测试（冒烟）

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\系统
pip install pytest httpx
python -m pytest tests/test_smoke.py -v
```

冒烟测试使用 `HUPU_DB_PATH` 指向临时 SQLite 库，覆盖注册登录、发帖拦截（词典）、存疑上报、审核处置 4 条最小链路，不污染 `data/hupu.db`。

## 启动步骤

### 1. 启动识别服务（端口 8000）

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\training
D:\rgzn\1\envs\torch_gpu\python.exe serve.py
```

确认 `http://127.0.0.1:8000/health` 返回 ok。
> 若识别服务未启动，平台审核管线自动容错降级：词典命中仍可拦截，未命中时按低危放行，不影响平台运行。

### 2. 启动平台后端（端口 8080）

```bash
cd C:\Users\swerey.SWEREY\PycharmProjects\系统\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8080
```

### 3. 打开前端

浏览器访问 `http://127.0.0.1:8080`，默认管理员账号 `admin / admin123`。

## 依赖说明

- 已具备：fastapi、uvicorn、pydantic、jinja2（如需模板）、python-multipart、PyJWT
- 缺失时安装：

```bash
pip install fastapi uvicorn python-multipart pyjwt
```

- 前端 Chart.js 使用 CDN（需联网），离线环境可替换为本地 chart.umd.min.js。

## 审核管线（audit/pipeline.py）

| 层级 | 说明 | 处置 |
|---|---|---|
| 词典快判（rules.py） | 命中 badword_variants.json（辱骂暴力/歧视煽动/色情低俗/敏感言论） | 立即定级，不调模型 |
| 模型识别（engine.py） | 调 `http://127.0.0.1:8000/predict` 六分类 | 服务异常自动降级兜底 |
| 定级处置 | 高危敏感言论/色情低俗 → 拦截；中危辱骂暴力/歧视煽动 → 折叠；低危广告引流 → 提示 | 拦截/折叠/提示 |
| 信用分联动 | 高危 -8、中危 -4、低危 -1；连续违规降级 | 每次违规写入 violations 记录 |
| 违规热词榜 | 统计最近被拦截次数 Top10 | `/api/banned-words/top` 实时返回 |

## 主要接口速览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/register | 注册（返回 JWT） |
| POST | /api/auth/login | 登录（返回 JWT + 用户信息） |
| GET | /api/posts?tab=latest\|hot&category= | 帖子列表（含审核状态） |
| POST | /api/posts | 发帖（全文审核） |
| GET | /api/posts/{id} | 帖子详情 + 评论 |
| POST | /api/posts/{id}/comments | 发评论（审核） |
| POST | /api/posts/{id}/like | 点赞 |
| POST | /api/posts/user/{uid}/follow | 关注/取消关注 |
| POST | /api/posts/precheck | 文本实时预检（发帖页用） |
| GET | /api/posts/users/active | 活跃用户榜 |
| POST | /api/videos/upload | 视频上传（multipart，标题/描述审核） |
| GET | /api/videos | 视频列表 |
| GET | /api/videos/{id} | 视频详情（含审核状态） |
| GET | /api/videos/file/{id} | 视频文件流 |
| POST | /api/danmaku | 发送弹幕（审核，blocked 拦截） |
| POST | /api/danmaku/batch | 批量发送（演示用） |
| GET | /api/danmaku?video_id= | 拉取弹幕 |
| GET | /api/banned-words/top | 违规热词榜 Top10 + 今日拦截量/拦截率/平均延迟 |
| GET | /api/admin/violations | 违规记录分页（管理员） |
| GET | /api/admin/stats | 六类分布 / 近 7 天趋势（管理员） |
| GET | /api/health | 平台健康检查 |

## 演示路径

1. 首页信息流：发帖/上传视频后自动出现在首页（最新/精华可切换，支持板块筛选与搜索）。
2. 弹幕拦截：video.html 点「演示：批量违规弹幕」或手动输入违规词，高危弹幕显示「已拦截」红色标记、中危弹幕折叠为黄色删除线。
3. 评论折叠：post.html 发表含违规词评论，高危直接拦截、中危折叠显示并扣信用分。
4. 发帖预检：publish.html 输入内容时实时提示违规词并预判处置。
5. 审核工作台：admin.html 查看违规队列、六类分布柱状图、近 7 天拦截趋势折线图（需 admin 登录）。
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
