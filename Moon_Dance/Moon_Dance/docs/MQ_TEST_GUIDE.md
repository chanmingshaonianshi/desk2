# MQ 测试操作指南

本文档只保留测试步骤，不再重复架构背景。先读 `ARCHITECTURE.md` 和 `MQ_ARCHITECTURE.md`，再按这里操作。

## 一、先分清要测哪条链路

项目里有两条异步链路，测试方法不同：

| 链路 | 适用场景 | 推荐程度 |
|------|----------|----------|
| Celery + Redis | 验证当前默认部署链路 | 高 |
| Redis Stream + 自定义 Worker | 验证模拟器直连 MQ、重传、死信 | 中 |

## 二、通用准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Redis

```bash
redis-server
```

验证：

```bash
redis-cli ping
```

返回 `PONG` 表示 Redis 可用。

## 三、测试 Celery + Redis 主链路

这条链路对应当前默认 API 架构。

### 1. 启动 API

```bash
python main_api.py --host 0.0.0.0 --port 8000 --no-ssl
```

### 2. 启动 Celery Worker

```bash
celery -A src.core.worker worker --loglevel=info --concurrency=4
```

### 3. 发送测试数据

可以使用现有 API 文档中的上传接口，或者运行模拟器，让它自动调用 API。

### 4. 验证结果

重点看：

- API 是否快速返回
- Worker 是否成功消费任务
- 数据目录下是否生成实时日志或报表

## 四、测试 Redis Stream 扩展链路

这条链路对应 `src/core/mq_client.py` 与 `src/mq_workers/*`。

### 1. 查看节点状态

```bash
python scripts/mq_manager.py status
```

### 2. 启动 Worker 节点

```bash
python scripts/mq_manager.py start validator 3
python scripts/mq_manager.py start writer 2
python scripts/mq_manager.py start logger
```

### 3. 再次确认节点启动成功

```bash
python scripts/mq_manager.py status
```

### 4. 运行设备模拟器

```bash
python main.py --no-gui --device-count 5 --duration 60
```

期望现象：

- 模拟器打印消息发送成功
- validator 节点开始校验消息
- writer 节点写入结果
- logger 节点记录统计信息

## 五、验证重点

### 1. 验证实时文件输出

确认运行后生成了实时数据文件，而不是只看到队列消息。

### 2. 验证重传

可以临时关闭 Redis，再运行模拟器，观察失败消息是否进入本地 pending 缓存；Redis 恢复后再观察是否自动重传。

### 3. 验证死信

如果某类消息持续处理失败，应该进入 `dead_letter` 或本地死信目录，而不是直接丢失。

### 4. 验证节点日志

检查 validator、writer、logger 的日志，确认每个阶段都真的执行过。

## 六、停止服务

停止 Redis Stream Worker：

```bash
python scripts/mq_manager.py stop all
```

停止 Redis：

```bash
redis-cli shutdown
```

如果你启动了 API 和 Celery，也需要分别停止对应进程。

## 七、排查建议

| 问题 | 优先检查 |
|------|----------|
| API 可访问但没有落盘 | Celery Worker 是否启动、Redis 是否连通 |
| 模拟器发消息但 Worker 不消费 | `mq_manager.py status`、Redis Stream 队列是否堆积 |
| 重传不生效 | 本地 pending 目录是否有文件、后台重试线程是否运行 |
| 节点启动失败 | 依赖是否安装完整、Redis 地址是否正确、日志中是否有导入错误 |
