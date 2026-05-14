# Moon_Dance 最新架构文档

本文件是当前项目唯一的总架构说明。以后涉及架构、模块边界、数据流、部署方式的修改，都以本文件为准。

## 1. 文档维护规则

这条规则从现在开始固定执行：

1. 每次修改代码时，必须同步检查是否需要更新本文档。
2. 如果改动影响接口流程、模块职责、部署方式、数据流或数据库结构，必须同时更新：
   - `docs/ARCHITECTURE.md`
   - `docs/BACKEND_IMPLEMENTATION.md`
   - `DOCUMENT_INDEX.md`
   - 相关接口文档
3. 如果文档与代码不一致，以代码为准，并在本次提交里修正文档。

## 2. 系统定位

Moon_Dance 当前是一个“智能坐垫数据采集 + 后端异步处理 + 小程序查询 + 报表输出”的 Python 系统。

它同时包含四类能力：

1. 本地设备模拟与桌面演示
2. 云端 API 接收与异步处理
3. 小程序用户注册、登录、鉴权与数据查询
4. Redis Stream 风格的扩展 MQ 链路

## 3. 当前主架构结论

如果老师问“现在系统主要是怎么跑的”，标准答案是：

- 对外主链路：`Flask API + Redis + Celery Worker + Nginx`
- 小程序链路：`Flask + MySQL + MongoDB + 双重鉴权`
- 本地演示链路：`main.py / simulator_client.py` 驱动模拟器
- 扩展链路：`Redis Stream + validator/writer/logger`，可独立启停与扩展

也就是说，这个项目不是单一后端，而是“一条主交付链路 + 一条扩展实验链路”的双链路结构。

## 4. 整体架构图

```text
本地模拟器 / 小程序前端 / 外部客户端
                │
                ▼
        Nginx / Flask API
                │
        ┌───────┼───────────────────────┐
        │       │                       │
        ▼       ▼                       ▼
   上传接口   小程序接口            健康检查/登录
        │       │
        ▼       ▼
     Redis    MySQL + MongoDB
        │
        ▼
   Celery Worker
        │
        ▼
 JSONL 日志 / MongoDB / Excel 报表

补充链路：
设备模拟器 -> Redis Stream -> validator -> writer/logger
```

## 5. 代码分层

### 5.1 接入层

- `main_api.py`
  - 创建 Flask 应用
  - 注册蓝图
  - 统一请求日志
  - 提供 `/health`
- `src/api/auth.py`
  - 负责 JWT、API Key、小程序 token 双重鉴权
- `src/api/routes.py`
  - 负责设备上传接口
- `src/api/miniapp_routes.py`
  - 负责小程序业务接口

### 5.2 核心业务层

- `src/core/device_simulator.py`
  - 生成设备压力数据
  - 支持 HTTP 上传和 MQ 发送
- `src/core/worker.py`
  - 处理 Celery 异步任务
  - 执行日志落盘和数据整理
- `src/core/live_monitor.py`
  - 读取日志并表格化展示
- `src/core/report_manager.py`
  - 负责报表批量生成
- `src/core/dynamic_scaler.py`
  - 根据负载自动扩缩容

### 5.3 数据与工具层

- `src/utils/json_db.py`
  - JSONL 日志、幂等 ID 管理
- `src/utils/mongo_db.py`
  - 原始明细数据写入 MongoDB
- `src/utils/mysql_db.py`
  - 用户、设置、排行榜、历史统计
- `src/config/settings.py`
  - 所有路径和环境变量配置中心

### 5.4 MQ 扩展层

- `src/core/mq_client.py`
  - Redis Stream 生产者
- `src/mq_workers/base_worker.py`
  - MQ Worker 基类
- `src/mq_workers/validator_worker.py`
  - 校验消息
- `src/mq_workers/writer_worker.py`
  - 写入日志文件
- `src/mq_workers/logger_worker.py`
  - 统计运行日志
- `scripts/mq_manager.py`
  - 独立启停与查看节点状态

## 6. 四条核心业务链路

### 6.1 本地模拟上传链路

```text
main.py / simulator_client.py
    -> DeviceSimulator
    -> HTTP POST /api/v1/upload 或 /api/v2/ingest
    -> Flask API
    -> Redis
    -> Celery Worker
    -> upload_log.jsonl / realtime_log.jsonl / MongoDB / Excel 报表
```

用途：

- 本地演示
- 云端上传验证
- 表格监控与报表生成

### 6.2 云端上传主链路

```text
客户端
    -> Nginx
    -> Flask 路由
    -> 鉴权
    -> request_id 幂等校验
    -> Celery delay()
    -> Worker 异步处理
    -> 日志落盘与数据存储
```

主特点：

- 上传接口快速返回 `202`
- 实际写入逻辑在 Worker 中完成
- 通过 `request_id` 避免重复处理

### 6.3 小程序查询链路

```text
注册 -> 设置 password
登录 -> 获取 Bearer Token
业务接口 -> X-API-Key + Authorization 双重鉴权
```

数据来源分工：

- MongoDB：实时设备状态
- MySQL：用户信息、设置、排行榜、统计

当前小程序接口包括：

- `POST /api/miniapp/user/register`
- `POST /api/miniapp/user/login`
- `GET /api/miniapp/device/<device_id>/realtime`
- `GET /api/miniapp/device/<device_id>/history`
- `GET /api/miniapp/user/<user_id>/stats`
- `GET /api/miniapp/leaderboard`
- `PUT /api/miniapp/user/<user_id>/settings`

### 6.4 Redis Stream 扩展链路

```text
DeviceSimulator
    -> mq_client.py
    -> upstream_data
    -> validator_worker
    -> validated_data
    -> writer_worker / logger_worker
    -> realtime_log.jsonl / statistics.log
```

这条链路不是默认公网主链路，但仍然保留，主要用于：

- 演示消息队列架构
- 模块独立启停
- 水平扩展验证
- 后续微服务化预留

## 7. 当前鉴权架构

### 7.1 设备上传接口

- `/login`
  - 使用 `app_id + app_secret` 获取 Bearer Token
- `/api/v1/upload`
  - 使用 JWT Bearer Token
- `/api/v2/ingest`
  - 使用统一 `X-API-Key`

### 7.2 小程序接口

小程序采用双重保险：

- `X-API-Key: myh`
- `Authorization: Bearer <miniapp_token>`

实现目的：

- API Key 控制接入端
- JWT 控制具体用户身份
- `stats` 和 `settings` 再根据 `uid/openid` 做访问控制

## 8. 数据存储架构

### 8.1 JSONL

用于：

- 实时传输记录
- 上传监控表格
- 演示与快速排查

关键文件：

- `data/realtime_logs/upload_log.jsonl`
- `data/realtime_logs/realtime_log.jsonl`
- `data/realtime_logs/processed_ids.json`

### 8.2 MongoDB

用于：

- 原始压力明细数据
- 小程序实时状态查询

关键集合：

- `pressure_data`

### 8.3 MySQL

用于：

- 用户注册与密码哈希
- 用户设置
- 每日统计
- 排行榜

关键表：

- `users`
- `user_daily_stats`

## 9. 部署架构

当前 Docker 部署以 `deploy/docker-compose.yml` 为主。

默认角色：

- `nginx`
  - 入口代理
  - 负责外部访问
- `api`
  - Flask 服务
- `worker`
  - Celery 异步处理
- `redis`
  - Broker 与缓存基础设施
- `mysql`
  - 小程序用户与统计数据

部署结论：

- 公网主要走 `nginx -> api -> worker`
- Redis Stream Worker 不是默认 compose 自动启动项
- Redis Stream 功能需要按需手动启停

## 10. 模块化与扩展性说明

老师如果问“是不是模块化、能不能独立启停、能不能扩容”，可以这样回答：

1. 是模块化的
   - 鉴权、接口、异步处理、模拟器、MQ Worker、数据存储都按目录拆分
2. 可以独立启停部分模块
   - `scripts/mq_manager.py` 支持单独启动 `validator`、`writer`、`logger`
3. 可以扩容
   - Celery Worker 支持 Docker 扩缩容
   - Redis Stream Worker 支持多副本消费
4. 主链路和扩展链路解耦
   - 即使不启用 Redis Stream，主 API 链路也能正常运行

## 11. 推荐阅读顺序

第一次看项目，按这个顺序最容易理解：

1. `docs/ARCHITECTURE.md`
2. `docs/BACKEND_IMPLEMENTATION.md`
3. `DOCUMENT_INDEX.md`
4. `docs/API.md`
5. `docs/MQ_TEST_GUIDE.md`

## 12. 一句话总结

Moon_Dance 当前是一个以 `Flask + Redis + Celery` 为云端主链路、以 `MySQL + MongoDB` 支撑小程序业务、以 `Redis Stream Worker` 作为扩展消息架构的模块化后端系统。
