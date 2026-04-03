# Moon_Dance 项目文档索引

本文档是整个项目的导航中心，完整描述代码架构、目录作用和各关键 Python 文件的职责。

---

## 📁 顶层目录结构

```
Moon_Dance(2)/Moon_Dance/          ← 项目根目录（工作区）
├── Moon_Dance/                    ← 主代码包（Python源码都在这里）
├── data/                          ← 数据输出目录（自动生成，不入版本控制）
│   ├── realtime_logs/             ← 实时日志 .jsonl 文件（每次测量追加写）
│   └── reports/                   ← 导出的 Excel 报表
├── logs/                          ← 服务运行日志（API请求日志、MQ工作节点日志）
├── tmp/                           ← 临时文件（MQ进程PID文件、MQ客户端本地缓存）
├── batch_reports/                 ← 批量报表输出（Docker模式专用）
├── DOCUMENT_INDEX.md              ← 本文件（项目文档总索引）
└── 演示提示命令.txt               ← 常用命令速查手册
```

> **注意**：`data/`、`logs/`、`tmp/` 三个目录由 `src/config/settings.py` 在启动时自动创建，无需手动建立。

---

## 📁 Moon_Dance/ 主代码包结构

```
Moon_Dance/
├── main.py                ← 客户端/模拟器入口（GUI模式 & 无头模式）
├── main_api.py            ← 服务端入口（Flask HTTPS服务器）
├── simulator_client.py    ← 简单模拟客户端启动脚本
├── requirements.txt       ← Python依赖列表
├── Dockerfile             ← 容器镜像构建文件
├── myh.pem                ← 开发用SSL证书（PEM格式）
├── certs/                 ← 运行时自动生成的TLS证书目录
├── src/                   ← 核心源码（业务逻辑）
│   ├── api/               ← HTTP接口层（鉴权 + 路由）
│   ├── core/              ← 核心业务层（模拟器、算法、MQ客户端、监控）
│   ├── mq_workers/        ← MQ工作节点（消费Redis Stream消息）
│   ├── config/            ← 全局配置
│   ├── utils/             ← 工具函数（JSON存储、Excel导出）
│   └── ui/                ← Tkinter桌面GUI界面
├── scripts/               ← 运维脚本（MQ管理、测试、打包、部署）
│   └── ops/               ← 自动扩缩容脚本
├── deploy/                ← Docker部署配置文件
└── docs/                  ← 项目文档
```

---

## 🗂️ 各子目录详细说明

### `src/api/` — HTTP 接口层

**职责**：实现所有对外 HTTP API 接口，包括身份鉴权和业务路由，是前后端数据传输的入口。

| 文件 | 作用 |
|------|------|
| `auth.py` | **身份鉴权模块** |
| `routes.py` | **API 路由与业务调度模块** |

---

### `src/core/` — 核心业务层

**职责**：实现核心算法、设备模拟、MQ消息客户端、数据监控，是系统的业务心脏。

| 文件 | 作用 |
|------|------|
| `device_simulator.py` | **设备模拟器** |
| `posture_analyzer.py` | **坐姿分析算法** |
| `pressure_surface.py` | **压力曲面生成算法** |
| `mq_client.py` | **MQ消息队列客户端** |
| `worker.py` | **Celery 异步任务处理器** |
| `live_monitor.py` | **实时日志监控工具** |
| `report_manager.py` | **报表批量生成管理器** |
| `dynamic_scaler.py` | **Docker 动态扩缩容监控模块**（新增，核心扩缩容逻辑） |

---

### `src/mq_workers/` — Redis Stream 消费工作节点

**职责**：实现 Redis Stream 扩展消息链路的消费者节点，负责验证、写入、统计三个阶段的异步处理。

| 文件 | 作用 |
|------|------|
| `base_worker.py` | **工作节点基类** |
| `validator_worker.py` | **数据验证节点** |
| `writer_worker.py` | **数据写入节点** |
| `logger_worker.py` | **日志统计节点** |

---

### `src/config/` — 全局配置

| 文件 | 作用 |
|------|------|
| `settings.py` | **全局配置与常量管理** |

---

### `src/utils/` — 工具函数库

| 文件 | 作用 |
|------|------|
| `json_db.py` | **JSON 轻量存储与幂等管理** |
| `excel_exporter.py` | **Excel 报表导出工具** |

---

### `src/ui/` — 桌面 GUI 界面（Tkinter）

| 文件 | 作用 |
|------|------|
| `main_window.py` | **主窗口（应用入口窗口）** |
| `chart_window.py` | **全天趋势图窗口** |
| `pressure_window.py` | **实时压力曲面可视化窗口** |

---

### `scripts/` — 运维与工具脚本

| 文件 | 作用 |
|------|------|
| `mq_manager.py` | **MQ节点管理脚本（启停/状态）** |
| `docker_entrypoint.py` | **Docker容器入口脚本** |
| `auto_scaler.py` | **动态扩缩容启动入口**（委托 `src/core/dynamic_scaler.py` 执行） |
| `ops/scaler.py` | **旧版扩缩容逻辑**（已保留作历史参考，核心逻辑已迁移至 `src/core/dynamic_scaler.py`） |
| `api_test.py` | **API 集成测试脚本** |
| `api_smoke_test.py` | **API 冒烟测试脚本** |
| `live_monitor.py` | **实时日志监控启动入口** |
| `package.bat` | **Windows 打包为EXE的脚本** |
| `run_docker.bat` | **Windows Docker快速启动脚本** |
| `start.sh` | **Linux 一键启动脚本** |

---

### `deploy/` — Docker 部署配置

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | **主部署编排文件（含 API_KEY 注入）** |
| `docker-compose-nginx.yml` | **带 Nginx 反向代理的编排文件** |
| `nginx.conf` | **Nginx 反向代理配置（HTTPS终止）** |
| `deploy.sh` | **生产环境自动化部署脚本** |

---

## 🔍 重要 Python 文件详解

---

### `main.py` — 客户端/模拟器总入口

**类型**：客户端启动器  
**运行方式**：
- 无参数：启动 Tkinter GUI 界面（`CushionSimulatorApp`）
- `--no-gui`：无头模式，10路并发设备模拟，支持 API 上传

**核心逻辑**：
- `_resolve_api_token()`：智能解析上传Token — 若未提供 Token 且目标是 JWT 接口，则自动调用 `/login` 换取 Token。
- `run_no_gui()`：无头模式的主循环，用 `ThreadPoolExecutor` 并发启动 N 个 `DeviceSimulator`，每轮采样后写入 JSON 日志，退出时自动并发生成全天 Excel 报表。
- `main()`：解析 CLI 参数（`--no-gui` / `--device-count` / `--api-url` / `--token` / `--insecure` / `--no-mq`），分发到 GUI 或无头模式。

---

### `main_api.py` — 服务端 Flask HTTPS 服务器

**类型**：服务端启动器  
**职责**：创建和运行 Flask 应用服务器，负责 TLS 证书管理、全局请求日志、蓝图注册。

**核心逻辑**：
- `_ensure_ca_and_server_cert()`：**自签名 TLS 证书自动生成** — 用 `pyOpenSSL` 在首次启动时自动生成自签名 CA 证书和服务端证书，支持 IP / DNS SAN，避免每次手动配置 SSL。
- `create_app()`：**Flask App 工厂函数** — 创建 Flask 实例，启用 CORS，注册 `before_request` 钩子写请求日志到 `logs/` 目录，注册 `auth_bp` 和 `api_bp` 两个蓝图，暴露 `/health` 健康检查接口。
- `main()`：解析启动参数（`--host` / `--port` / `--cn` / `--no-ssl` / `--gen-certs-only`），以 HTTPS 或 HTTP 模式启动 Flask（多线程模式 `threaded=True`）。

---

### `src/api/auth.py` — 身份鉴权模块

**类型**：Flask Blueprint + 中间件装饰器  
**职责**：提供两种独立的身份鉴权机制，保护 API 接口不被未授权访问。

**关键组件**：

| 组件 | 机制 | 说明 |
|------|------|------|
| `@auth_bp.post("/login")` | 登录接口 | 客户端以 `app_id` + `app_secret` 换取 JWT，返回 `Bearer Token` |
| `_issue_token()` | JWT 签发 | 使用 `JWT_SECRET` 和 `HS256` 算法生成含 `sub/iat/exp` 字段的 JWT，有效期默认 3600 秒 |
| `@token_required` | JWT 验证装饰器 | 检查 `Authorization: Bearer <token>` 头，`jwt.decode()` 验证签名和过期，失败返回 `403` |
| `@api_key_required` | API Key 验证装饰器 | 检查 `X-API-Key` 请求头，与 `settings.py` 中的 `API_KEY` 对比，失败返回 `401` |

**两种认证路径**：
- **JWT 路径**：`POST /login` → 获取 Token → 携带 `Authorization: Bearer <token>` 调用 `/api/v1/upload`
- **API Key 路径**：直接携带 `X-API-Key: <key>` 调用 `/api/v2/ingest`（无需登录）

---

### `src/api/routes.py` — API 路由与数据接收模块

**类型**：Flask Blueprint  
**职责**：定义所有数据上传 API 接口，进行请求参数校验、幂等去重、数据预处理，并异步分发任务。

**API 接口列表**：

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `POST /api/v1/upload` | 数据上传 | JWT Bearer Token | 主上传接口（当前推荐） |
| `POST /api/v2/ingest` | 数据摄取 | X-API-Key | API Key 上传接口 |
| `POST /api/upload_data` | 数据上传 | JWT Bearer Token | 旧版兼容接口 |

**核心逻辑**：
- `_handle_upload_request()`：统一处理所有上传请求的核心函数：
  1. 解析 JSON 请求体，提取 `request_id`（必须是合法 UUID）
  2. **幂等校验**：加载 `processed_ids.json`，若已处理则直接返回 `200`，避免重复入库
  3. 写入实时上传日志（`upload_log.jsonl`）
  4. 调用 `process_upload_data.delay()` 投递 Celery 异步任务（不阻塞响应）
  5. 标记 `request_id` 为已处理，返回 `202 Accepted`
- `_load_processed_ids()` / `_save_processed_ids()`：线程安全的幂等 ID 文件读写（`RLock` 保护）。
- `_parse_device_id()`：兼容 `device_001`（字符串格式）和整数格式的设备 ID 解析。
- `_build_upload_log_record()`：将原始 payload 标准化为含 `time`/`ratio`/`f_left`/`f_right` 字段的日志记录。

---

### `src/core/dynamic_scaler.py` — Docker 动态扩缩容监控模块（新增）

**类型**：独立监控守护进程  
**职责**：持续采集运行时负载指标，自动调整 Docker Compose 中 Celery Worker 的副本数，实现服务集群的弹性伸缩（既能扩容，也能缩容）。

**双指标扩缩容策略**：

| 指标 | 来源 | 扩容阈值 | 缩容阈值 |
|------|------|---------|----------|
| **QPS**（请求速率） | Redis `celery-task-meta-*` 键扫描，统计近20秒完成任务数 | ≥ 5 req/s | < 1 req/s |
| **Stream 积压量** | Redis `xlen(upstream_data)` | ≥ 100 条 | < 20 条 |

**决策规则**：
- **扩容**：两个指标任一达到扩容阈值，且当前副本数 < `MAX_WORKERS=5`
- **缩容**：两个指标同时低于缩容阈值，连续满足 3 轮，且距上次扩缩容超过 30 秒冷却期，且当前副本数 > `MIN_WORKERS=1`

**关键函数**：
- `get_qps(r)`：扫描 Redis 中 Celery 任务结果键，计算近期 QPS
- `get_stream_backlog(r)`：通过 `xlen` 读取 Redis Stream 消息积压量
- `scale_workers(target)`：调用 `docker compose up --scale worker=N` 调整副本数
- `monitor_and_scale()`：主监控循环，每 `CHECK_INTERVAL=5` 秒采集一次指标并执行决策

**所有阈值均支持环境变量覆盖**：
```
MIN_WORKERS, MAX_WORKERS, SCALE_STEP
QPS_WINDOW_SECONDS, SCALE_UP_QPS_THRESHOLD, SCALE_DOWN_QPS_THRESHOLD
SCALE_UP_BACKLOG_THRESHOLD, SCALE_DOWN_BACKLOG_THRESHOLD
SCALE_DOWN_COOLDOWN, CONSECUTIVE_DOWN_COUNT, CHECK_INTERVAL
```

**运行方式**：
```bash
# 作为模块运行（在 Moon_Dance/ 包根目录下执行）
python -m src.core.dynamic_scaler

# 或通过入口脚本
python scripts/auto_scaler.py
```

---

### `src/core/worker.py` — Celery 异步任务处理器

**类型**：Celery Task  
**职责**：承接 API 层投递的上传任务，在后台异步完成数据写盘、日志记录，解耦 API 响应和计算存储。

**关键设计**：
- 使用 `Celery` 连接 Redis（`broker` 和 `backend` 均为 `REDIS_URL`）
- 任务 `process_upload_data` 带 `bind=True`（可访问 `self`）和 `max_retries=3`（失败最多重试3次，指数退避）
- 任务内部：构造标准化记录 → 写实时日志 → 写上传日志 → 写设备历史记录 → 标记幂等 ID

---

### `src/core/mq_client.py` — Redis Stream MQ 客户端

**类型**：消息发送客户端  
**职责**：设备端向 Redis Stream 发布传感器数据消息，内置本地缓存和指数退避重传，保证消息不丢失。

**关键机制**：
- **三级目录本地缓存**：`pending/`（待发送）、`dead_letter/`（超过重试次数）、`success/`（成功发送）
- `send_message()`：发送到 Redis Stream（`xadd`），失败则将消息序列化到 `pending/` 目录等待重传
- `retry_pending_messages()`：由后台线程定时调用，按指数退避间隔（`2^n` 秒，最大30秒）重试待发消息
- `_move_to_dead_letter()`：超过 `max_retry=10` 次后永久归档到死信目录，不再重试

---

### `src/core/device_simulator.py` — 设备模拟器

**类型**：设备数据生成器  
**职责**：模拟智能坐垫传感器硬件，生成随机压力数据，同时通过两条路径上报数据。

**数据上报双路径**：
1. **HTTP API 路径**：`send_to_api()` — 向配置的 `api_url` 发送 POST 请求（携带 `X-API-Key` 和可选 Bearer Token）
2. **MQ 路径**：`mq_client.send_message()` — 向 Redis Stream `upstream_data` 发布消息

**关键设计**：
- `measure()`：每次调用生成一条完整测量记录（含 `device_id`, `request_id`, `sensors`, `analysis`, `matrix_snapshot` 32×32压力矩阵）
- 后台重传线程：`_start_retry_thread()` 每秒调用 `retry_pending_messages()`，保证网络抖动时消息不丢失
- `verify_ssl`：支持关闭 SSL 验证（`--insecure` 参数），开发自签名证书场景下避免请求失败

---

### `src/core/posture_analyzer.py` — 坐姿分析算法

**类型**：纯算法模块  
**职责**：核心业务算法——压力偏差计算、坐姿评级、模拟数据生成、全天评分计算。

**关键函数**：
- `calculate_ratio(f_left, f_right)`：计算左右受力偏差率 `|L-R| / (L+R)`
- `get_assessment(ratio)`：按偏差率分级 → `"坐姿端正"(≤5%)` / `"轻微歪斜"(≤10%)` / `"请注意坐姿"(>10%)`
- `calculate_daily_score(avg_deviation%)`：三段线性映射公式，将全天平均偏差率转换为 0~100 分评分，写入 Excel 报表顶部

---

### `src/core/pressure_surface.py` — 压力曲面生成算法

**类型**：纯算法模块（无 numpy 依赖）  
**职责**：基于生物力学模型生成 32×32 臀部压力分布矩阵，用于 GUI 热力图可视化。

**算法特点**：
- 以坐骨结节位置为高斯压力峰值中心，分别生成左右坐骨区的压力分布
- 模拟大腿前部压力带（随机微偏移模拟自然挪动）
- 边缘清零 + 最大值限制（≤500N），输出视觉合理的热力图数据

---

### `src/core/live_monitor.py` — 实时日志监控工具

**类型**：命令行监控工具  
**职责**：读取 `.jsonl` 日志文件，实时展示数据传输情况和 API 参数结构，支持 tail-follow 模式。

**运行方式**：
```bash
python -m src.core.live_monitor --source upload --follow
```
**输出内容**：
- **传输记录表**：时间、设备ID、左右压力、偏差率、状态、请求ID（前8位）
- **API参数表**：字段名、数据类型、最新值样本、字段出现频率（Hz）

---

### `src/mq_workers/base_worker.py` — MQ 工作节点基类

**类型**：抽象基类  
**职责**：封装所有 MQ 消费节点的通用逻辑，子类只需实现 `process_message()` 方法。

**提供的通用能力**：
- 消费者组自动创建（`xgroup_create`，已存在则跳过）
- 批量消费消息（`xreadgroup`，阻塞式长轮询）
- 消息 ACK 管理：成功处理后 `xack`，失败则投入 `dead_letter` Stream
- 优雅停止：注册 `SIGINT` / `SIGTERM` 信号处理，设置 `self.running = False` 等待当前批次处理完毕
- 结构化日志写入（同时输出控制台和独立 `.log` 文件）

---

### `src/mq_workers/validator_worker.py` — 数据验证节点

**消费队列**：`upstream_data`（设备原始上报）  
**消费者组**：`validator_group`  
**职责**：过滤不合规数据，将验证通过的消息转发到下一级队列。

**验证规则**：
1. 必填字段检查：`msg_id`, `device_id`, `timestamp`, `data`
2. `msg_id` 必须是合法 UUID
3. `data.sensors` 必须包含 `left_force_n` 和 `right_force_n`
4. 压力值必须是非负数值

**验证通过后**：将消息 `xadd` 到 `validated_data` Stream，由 writer_worker 和 logger_worker 消费。

---

### `src/mq_workers/writer_worker.py` — 数据写入节点

**消费队列**：`validated_data`（已验证数据）  
**消费者组**：`writer_group`  
**职责**：将验证通过的数据持久化到文件系统。

**写入逻辑**：
1. 追加写入统一实时日志 `realtime_log.jsonl`
2. 按设备 + 日期单独写入 `{device_id}_{YYYYMMDD}.jsonl`（每天一个文件，自动切换）
3. 支持多副本水平扩展（同一消费者组，Redis 自动分片）

---

### `src/mq_workers/logger_worker.py` — 日志统计节点

**消费队列**：`validated_data`（已验证数据）  
**消费者组**：`logger_group`  
**职责**：统计系统运行指标，每分钟输出一次流量报表。

**统计内容**：总处理消息数、在线设备数、Top 5 上报设备排行，写入 `statistics.log`。

---

### `src/config/settings.py` — 全局配置中心

**类型**：配置模块  

**职责**：集中管理所有配置常量，支持开发/生产环境差异化。

**关键配置项**：

| 配置项 | 来源 | 说明 |
|--------|------|------|
| `BASE_PATH` | 自动计算 | 代码根目录（支持打包 exe 和脚本两种模式） |
| `DATA_DIR` / `LOG_DIR` / `TEMP_DIR` | 自动计算 | 数据、日志、临时目录（代码外层，与源码分离） |
| `API_APP_ID` / `API_APP_SECRET` | 环境变量 | JWT 登录凭据（默认值仅用于开发） |
| `API_KEY` | 环境变量 | X-API-Key 鉴权值（默认 `"myh"`） |
| `JWT_SECRET` | 环境变量 | JWT 签名密钥（**生产环境必须修改**，否则启动报错） |
| `REDIS_URL` | 环境变量 | Redis 连接地址（默认 `redis://localhost:6379/0`） |
| `RATIO_NORMAL` / `RATIO_WARNING` | 代码常量 | 坐姿评估阈值（5% 正常，10% 警告） |

---

### `src/utils/json_db.py` — JSON 轻量存储与幂等管理

**类型**：数据持久化工具  
**职责**：提供无需数据库的轻量级数据落盘方案，以及请求幂等 ID 管理。

**关键函数**：
- `append_realtime_log(record, log_file_path=None)`：将记录追加写入 `.jsonl` 文件（线程安全，`RLock` 保护），支持指定自定义日志路径（上传日志 vs 实时日志）
- `append_record(device_id, record)`：读取全量 JSON → 追加记录 → 写回，用于设备历史数据存储（适合低频写入）
- `mark_request_processed(request_id)`：将幂等 ID 追加到 `processed_ids.json`，自动限制最大 10000 条防止文件膨胀
- `load_db()` / `save_db(data)`：全量读写 `history_data.json`，兼容新格式（`device_001`字符串键）和旧格式（整数键）

---

### `src/utils/excel_exporter.py` — Excel 报表导出工具

**类型**：报表生成工具  
**职责**：将坐姿数据格式化输出为 Excel（TSV + UTF-16 格式，可直接用 Excel 打开）。

**关键函数**：
- `export_daily_report(data_rows, filename, output_dir)`：生成全天报表，文件顶部自动写入 **今日坐姿评分** 和 **平均偏差率**，返回 `(True, 文件路径)` 或 `(False, 错误信息)`
- `export_history_data(history_data)`：导出历史测量记录（GUI 模式下带弹窗提示）

---

### `scripts/mq_manager.py` — MQ 节点管理脚本

**类型**：运维管理工具  
**职责**：独立管理所有 MQ 工作节点（validator / writer / logger）的生命周期。

**支持命令**：
```bash
python scripts/mq_manager.py start validator 3  # 启动3个验证节点（副本）
python scripts/mq_manager.py start writer 2     # 启动2个写入节点
python scripts/mq_manager.py start logger       # 启动日志统计节点（单实例）
python scripts/mq_manager.py status            # 查看所有节点运行状态
python scripts/mq_manager.py stop all          # 停止所有节点
```

**实现方式**：用 `subprocess.Popen` 后台启动子进程，PID 保存到 `tmp/mq_pids/` 目录，支持 Windows（`CREATE_NEW_PROCESS_GROUP`）和 Linux（`setpgrp`）双平台。

---

## 🔄 整体数据流向

### 主链路（API + Celery）

```
设备/客户端
    │ HTTP POST (Bearer JWT 或 X-API-Key)
    ▼
main_api.py (Flask HTTPS 服务器)
    │ before_request → 写请求日志 logs/*.log
    ▼
src/api/auth.py (@token_required / @api_key_required)
    │ 身份验证通过
    ▼
src/api/routes.py (_handle_upload_request)
    │ 幂等校验 → 写预日志 → 投递 Celery 任务 → 返回 202
    ▼
Redis (Celery Broker)
    ▼
src/core/worker.py (Celery 异步 Worker)
    │ 构造记录 → 写实时日志 → 写设备历史 → 标记幂等 ID
    ▼
data/realtime_logs/*.jsonl  +  data/realtime_logs/processed_ids.json
```

### 扩展链路（Redis Stream MQ）

```
src/core/device_simulator.py (设备模拟器)
    │ MQClient.send_message() → xadd
    ▼
Redis Stream: upstream_data
    ▼
src/mq_workers/validator_worker.py
    │ 格式校验 → xadd (通过) / dead_letter (失败)
    ▼
Redis Stream: validated_data
    ├─▶ src/mq_workers/writer_worker.py → data/realtime_logs/*.jsonl
    └─▶ src/mq_workers/logger_worker.py → logs/statistics.log
```

---

## 文档目录

```
docs/
├── README.txt           # 项目快速入门（启动命令、基本功能）
├── ARCHITECTURE.md      # 系统架构设计（双链路架构图、组件关系）
├── API.md               # API接口参考（参数、请求/响应示例、错误码）
├── API.html             # HTML可视化版API文档（浏览器直接打开）
├── API_OPERATION.md     # API运维指南（测试步骤、日志排查）
├── MQ_ARCHITECTURE.md   # MQ分布式架构设计（队列边界、消息格式）
├── MQ_TEST_GUIDE.md     # MQ测试操作指南
└── README_DOCKER.md     # Docker部署说明
```

---

## 当前框架速记

| 层级 | 入口文件 | 核心职责 |
|------|---------|---------|
| **服务器启动** | `main_api.py` | Flask App 创建、TLS 证书生成、蓝图注册、请求日志 |
| **鉴权层** | `src/api/auth.py` | JWT 签发验证（`/login`）、API Key 校验、`@token_required` / `@api_key_required` 装饰器 |
| **数据接口层** | `src/api/routes.py` | `/api/v1/upload`（JWT）、`/api/v2/ingest`（API Key）、幂等去重、Celery 任务投递 |
| **主异步链路** | `src/core/worker.py` | Celery + Redis 消费上传任务，异步写盘 |
| **扩展MQ客户端** | `src/core/mq_client.py` | Redis Stream 消息发布、本地缓存、指数退避重传 |
| **MQ消费节点** | `src/mq_workers/*` | validator→validated、writer→写文件、logger→统计 |
| **配置中心** | `src/config/settings.py` | 所有配置常量、环境变量读取、路径计算 |
| **数据存储** | `src/utils/json_db.py` | JSONL 追加写日志、幂等 ID 管理、历史数据读写 |
| **设备模拟器** | `src/core/device_simulator.py` | 模拟传感器数据生成，双路上报（API + MQ） |
| **客户端启动** | `main.py` | GUI 模式或无头模式，10 路并发模拟 |
| **MQ节点管理** | `scripts/mq_manager.py` | 启停 validator/writer/logger，管理副本数 |
| **动态扩缩容** | `src/core/dynamic_scaler.py` | 双指标（QPS + Stream积压量）自动扩缩 Docker Worker 副本 |
| **部署入口** | `deploy/docker-compose.yml` | Docker 编排，注入 `API_KEY` 环境变量 |
