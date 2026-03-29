# 消息队列架构说明

本文件只讲异步处理和消息队列，不再重复整体系统架构。整体关系请先看 `ARCHITECTURE.md`。

## 一、先说结论

Moon_Dance 当前有两套异步处理通道：

1. **默认部署通道：Celery + Redis**
   - 对应 API 上传链路
   - 当前 `docker-compose.yml` 默认启动这一套
   - 入口文件是 `src/core/worker.py`

2. **扩展通道：Redis Stream + 自定义 Worker**
   - 对应桌面模拟器可选直连 MQ 链路
   - 需要手动启动 `scripts/mq_manager.py`
   - 对应 `src/core/mq_client.py` 和 `src/mq_workers/*`

因此，不能再把项目简单描述成“只有 Redis Stream 架构”，否则会和当前实际部署方式不一致。

## 二、两套 MQ 的边界

| 方案 | 入口 | Redis 角色 | 消费者 | 当前定位 |
|------|------|------------|--------|----------|
| Celery + Redis | Flask API | Broker / 任务队列 | `src/core/worker.py` | 默认生产链路 |
| Redis Stream | 设备模拟器 `MQClient` | Stream 存储与消费者组 | `src/mq_workers/*` | 本地演示、扩展验证 |

## 三、Celery + Redis 链路

### 3.1 处理流程

```text
客户端 -> Flask API -> Redis -> Celery Worker -> 数据落盘 / 报表处理
```

### 3.2 主要职责

- API 接口先完成 JWT 与请求合法性校验
- 上传成功后立即投递异步任务，避免接口长时间阻塞
- Worker 负责真正的数据整理、日志写入和状态更新

### 3.3 适合它的原因

- 与当前 Docker 编排一致
- 对外接口更稳定
- 更适合做集中式 API 接入
- 可以基于队列长度做 Worker 扩容

## 四、Redis Stream 链路

### 4.1 处理流程

```text
设备模拟器 -> upstream_data -> validator_worker
         -> validated_data -> writer_worker / logger_worker
         -> dead_letter
```

### 4.2 队列定义

| 队列名称 | 用途 |
|----------|------|
| upstream_data | 模拟器发送的原始数据 |
| validated_data | 校验通过后可继续处理的数据 |
| dead_letter | 处理失败或无法恢复的消息 |

### 4.3 相关模块

| 模块 | 代码位置 | 职责 |
|------|----------|------|
| MQ 客户端 | `src/core/mq_client.py` | 构造消息、发送消息、本地缓存、失败重传 |
| 校验节点 | `src/mq_workers/validator_worker.py` | 校验数据并转发到 `validated_data` |
| 写入节点 | `src/mq_workers/writer_worker.py` | 消费已校验数据并写入结果 |
| 日志节点 | `src/mq_workers/logger_worker.py` | 记录统计与运行信息 |
| 节点管理 | `scripts/mq_manager.py` | 启停和查看 Worker 状态 |

## 五、消息格式

Redis Stream 直连链路中的消息以统一 JSON 结构组织：

```json
{
  "msg_id": "uuid字符串",
  "device_id": "device_001",
  "timestamp": 1700000000000,
  "data": {
    "sensors": {
      "left_force_n": 300.0,
      "right_force_n": 280.0
    },
    "analysis": {
      "deviation_ratio": 0.034
    }
  },
  "retry_count": 0,
  "create_time": 1700000000
}
```

| 字段 | 说明 |
|------|------|
| `msg_id` | 全局唯一消息 ID，用于去重和追踪 |
| `device_id` | 设备标识 |
| `timestamp` | 采样时间戳，毫秒 |
| `data.sensors` | 原始传感器数据 |
| `data.analysis` | 分析结果摘要 |
| `retry_count` | 当前重试次数 |
| `create_time` | 消息创建时间，秒级时间戳 |

## 六、客户端可靠性策略

`src/core/mq_client.py` 为 Redis Stream 链路提供了本地可靠性能力：

- 发送失败时落到本地 pending 缓存
- 后台线程自动扫描并重试
- 重试次数过多时转入本地死信目录
- 通过 `msg_id` 保证消息可以被追踪和去重

本地缓存目录逻辑如下：

```text
client_cache/
├── pending/
├── dead_letter/
└── send_success/
```

## 七、为什么要保留两套异步模型

保留两套异步模型不是重复建设，而是因为它们解决的问题不同：

- **Celery + Redis**
  - 更适合标准 API 服务
  - 更适合容器化部署
  - 更适合作为当前主交付链路

- **Redis Stream + 自定义 Worker**
  - 更适合精细化控制每个处理阶段
  - 更适合演示消息分流、死信、消费者组
  - 更适合继续拆分为更细粒度服务

## 八、当前建议

如果目标是理解“现在系统实际怎么跑”，优先看：

1. `src/api/routes.py`
2. `src/api/auth.py`
3. `src/core/worker.py`
4. `deploy/docker-compose.yml`

如果目标是理解“模拟器直连 MQ 怎么工作”，再看：

1. `src/core/device_simulator.py`
2. `src/core/mq_client.py`
3. `src/mq_workers/*`
4. `scripts/mq_manager.py`
