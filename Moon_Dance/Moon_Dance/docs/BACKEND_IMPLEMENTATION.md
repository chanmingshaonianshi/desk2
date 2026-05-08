# Moon_Dance 后端实现说明

本文件面向课程答辩、老师提问和项目讲解，重点说明“当前功能是怎么做出来的”。

## 1. 后端实现思路总览

当前后端不是把所有逻辑写在一个文件里，而是按“接入层 -> 业务层 -> 存储层 -> 运维层”拆开实现。

实现目标主要有四个：

1. 能接收本地模拟器或外部客户端上传的数据
2. 能把上传过程异步化，避免接口卡顿
3. 能提供小程序注册、登录、实时状态、统计和排行榜
4. 能支持消息队列扩展、模块独立启停和后续扩容

## 2. 功能一：本地模拟器怎么做出来的

### 2.1 入口文件

- `main.py`
  - 支持 GUI 模式和 `--no-gui` 模式
- `simulator_client.py`
  - 作为简化入口，方便直接运行上传演示

### 2.2 数据生成

核心文件：

- `src/core/device_simulator.py`
- `src/core/posture_analyzer.py`
- `src/core/pressure_surface.py`

实现方式：

1. `DeviceSimulator.measure()` 先生成左右压力值
2. 调用 `posture_analyzer.py` 计算偏差率和姿态结果
3. 调用 `pressure_surface.py` 生成 32x32 压力矩阵
4. 组装成统一上传结构：
   - `device_id`
   - `request_id`
   - `sensors`
   - `analysis`
   - `matrix_snapshot`

这样做的好处是：

- 算法和上传分离
- 后续换数据来源时不用重写接口层

## 3. 功能二：上传接口怎么做出来的

### 3.1 Flask 接口入口

核心文件：

- `main_api.py`
- `src/api/routes.py`
- `src/api/auth.py`

实现方式：

1. `main_api.py` 创建 Flask 应用
2. 注册 `auth_bp`、`api_bp`、`miniapp_bp`
3. `src/api/routes.py` 暴露上传接口：
   - `/api/v1/upload`
   - `/api/v2/ingest`
   - `/api/upload_data`

### 3.2 为什么分成三个上传接口

- `/api/v1/upload`
  - 作为当前推荐上传接口
  - 使用 JWT Bearer Token
- `/api/v2/ingest`
  - 为统一 API Key 鉴权预留
  - 设备共用 `X-API-Key`
- `/api/upload_data`
  - 兼容旧版本调用方式

这样做是为了：

- 保证新旧脚本都还能运行
- 同时支持 JWT 和 API Key 两类接入

### 3.3 幂等是怎么实现的

核心文件：

- `src/api/routes.py`
- `src/utils/json_db.py`

实现方式：

1. 每个上传请求必须带 `request_id`
2. 后端先读取 `processed_ids.json`
3. 如果 `request_id` 已存在，直接返回，不重复处理
4. 如果不存在，就写入日志并投递异步任务
5. 处理完成后标记为已处理

这样可以解决：

- 网络重试导致重复入库
- 客户端超时重发导致重复统计

## 4. 功能三：为什么要做异步处理

如果上传接口一收到请求就同步写所有数据，问题会很多：

1. 接口响应慢
2. 一旦写库或写文件卡住，请求就超时
3. 高并发时容易堵塞

所以现在采用：

```text
Flask API -> Redis -> Celery Worker
```

核心文件：

- `src/core/worker.py`
- `deploy/docker-compose.yml`

实现方式：

1. API 层做参数校验和鉴权
2. API 层只负责把任务丢给 Celery
3. Worker 在后台异步处理：
   - 整理记录
   - 写 `upload_log.jsonl`
   - 写 `realtime_log.jsonl`
   - 写 MongoDB
   - 更新幂等状态

这样后端接口可以更快返回 `202 Accepted`。

## 5. 功能四：表格监控怎么做出来的

核心文件：

- `src/core/live_monitor.py`

实现方式：

1. 监控脚本读取 `upload_log.jsonl` 或 `realtime_log.jsonl`
2. 把最近的记录整理成终端表格
3. 同时统计字段名、类型、样例和值出现频率
4. 支持 `--follow` 持续刷新

这部分是为了满足演示要求：

- 本地上传后，云端能看到表格化传输结果
- 能展示“最近传了什么数据、字段长什么样”

## 6. 功能五：报表怎么做出来的

核心文件：

- `src/core/report_manager.py`
- `src/utils/excel_exporter.py`

实现方式：

1. 模拟器运行时收集一段时间的数据
2. `report_manager.py` 负责批量组织每个设备的数据
3. `excel_exporter.py` 导出为 Excel 可打开的文件
4. 报表输出到 `data/reports/`

这样实现后：

- 可以本地演示
- 可以做批量设备报表
- 可以保留历史结果

## 7. 功能六：小程序后端怎么做出来的

### 7.1 为什么单独做 `miniapp_routes.py`

因为小程序和设备上传不是一类接口：

- 上传接口是“高频写入”
- 小程序接口是“用户查询 + 设置 + 登录”

所以单独拆成：

- `src/api/routes.py`
- `src/api/miniapp_routes.py`

这样职责更清晰。

### 7.2 小程序当前有哪些功能

核心接口：

- `POST /api/miniapp/user/register`
- `POST /api/miniapp/user/login`
- `GET /api/miniapp/device/<device_id>/realtime`
- `GET /api/miniapp/user/<user_id>/stats`
- `GET /api/miniapp/leaderboard`
- `PUT /api/miniapp/user/<user_id>/settings`

### 7.3 为什么小程序要用双数据库

因为两类数据特点完全不同：

1. MongoDB 适合原始实时数据
2. MySQL 适合用户、设置、统计和排行榜

当前分工：

- `src/utils/mongo_db.py`
  - 原始压力明细
  - 实时状态查询基础
- `src/utils/mysql_db.py`
  - 用户
  - `password_hash`
  - 设置项
  - 每日统计
  - 排行榜

### 7.4 小程序鉴权是怎么做的

核心文件：

- `src/api/auth.py`
- `src/api/miniapp_routes.py`
- `src/utils/mysql_db.py`

当前做法是双重保险：

1. `X-API-Key: myh`
2. `Authorization: Bearer <miniapp_token>`

实现步骤：

1. 注册接口写入 `openid` 和 `password`
2. 后端用 `generate_password_hash()` 保存密码哈希
3. 登录接口校验密码
4. 登录成功后签发专用小程序 token
5. 业务接口统一要求 API Key + Bearer Token
6. `stats` 和 `settings` 再校验当前 token 用户是否与 URL 中用户一致

这样做能同时防止：

- 没带 API Key 的非法请求
- 冒用别人用户 ID 的请求

## 8. 功能七：消息队列模式怎么做出来的

### 8.1 主链路 MQ

当前主链路的队列模式是：

```text
Flask -> Redis -> Celery Worker
```

作用：

- 解耦上传接口和后端处理
- 支持并发
- 支持容器扩容

### 8.2 扩展链路 MQ

另外还做了一条 Redis Stream 链路：

- `src/core/mq_client.py`
- `src/mq_workers/validator_worker.py`
- `src/mq_workers/writer_worker.py`
- `src/mq_workers/logger_worker.py`

流程：

```text
模拟器 -> upstream_data -> validator -> validated_data -> writer/logger
```

这部分的意义是：

- 证明系统支持面向消息队列模式
- 证明模块能单独启停
- 证明相同功能节点可以开多个副本

### 8.3 独立启停怎么实现

核心文件：

- `scripts/mq_manager.py`

做法：

1. 用 `subprocess.Popen` 启动独立进程
2. 把 PID 写到临时目录
3. 通过 `start/status/stop` 管理 validator、writer、logger

所以老师如果问“模块能不能单独启动”，答案是能。

## 9. 功能八：扩容怎么做出来的

核心文件：

- `src/core/dynamic_scaler.py`
- `scripts/auto_scaler.py`

实现方式：

1. 定时读取 Redis 的队列积压量
2. 定时读取任务完成速率
3. 如果积压太高或 QPS 过高，就扩容 Worker
4. 如果长时间空闲，就缩容

所以系统不只是静态部署，还保留了扩缩容能力。

## 10. 功能九：为什么说现在后端是模块化的

因为当前代码已经按责任拆开：

- 鉴权：`src/api/auth.py`
- 上传接口：`src/api/routes.py`
- 小程序接口：`src/api/miniapp_routes.py`
- 模拟器：`src/core/device_simulator.py`
- 异步 Worker：`src/core/worker.py`
- MQ 节点：`src/mq_workers/*`
- MySQL：`src/utils/mysql_db.py`
- MongoDB：`src/utils/mongo_db.py`
- 日志监控：`src/core/live_monitor.py`
- 部署：`deploy/docker-compose.yml`

这意味着后续继续加功能时，不需要把所有代码堆到一个地方。

## 11. 课程答辩时可以怎么概括

可以这样说：

> 我们的后端采用了分层和模块化设计。上传主链路用 Flask 接口接收数据，通过 Redis 和 Celery 做异步处理，再写入日志、MongoDB 和报表文件；小程序部分单独拆成用户与查询接口，使用 MySQL 管理用户和统计，使用 MongoDB 查询实时设备数据，并增加了 API Key 和用户 Token 的双重鉴权；另外还保留了基于 Redis Stream 的扩展消息队列链路，用于验证模块独立启停和多副本扩展能力。

## 12. 后续维护规则

以后只要代码改动涉及下列内容，就必须同步更新文档：

1. 新增或删除接口
2. 鉴权方式变化
3. 数据流变化
4. 数据库结构变化
5. Docker 部署结构变化
6. MQ 节点职责变化
7. 报表或监控输出变化

最低要求是同步更新：

- `docs/ARCHITECTURE.md`
- `docs/BACKEND_IMPLEMENTATION.md`
- `DOCUMENT_INDEX.md`
- 对应接口文档
