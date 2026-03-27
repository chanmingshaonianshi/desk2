# 集群部署说明

## 已实现功能
✅ 3副本API集群部署，支持水平扩展
✅ Redis消息队列集成，实现上传数据缓冲
✅ Nginx负载均衡，HTTPS统一入口
✅ Celery异步任务处理，削峰填谷
✅ 自动扩容监控脚本，根据压力弹性调整副本数

## 快速启动

### 1. 生成证书
```bash
python main_api.py --gen-certs-only
```

### 2. 启动集群
```bash
docker compose up -d
```

### 3. 查看运行状态
```bash
docker compose ps
```

### 4. 启动自动扩容脚本
```bash
pip install redis
python auto_scaler.py
```

## 关键配置说明

### docker-compose.yml
- `api.replicas: 3` 默认3个API副本
- `redis` 服务作为消息队列和缓存
- `nginx` 作为统一HTTPS入口，负载均衡到多个API实例
- `worker` Celery异步任务处理节点，处理数据存储和报表生成

### 自动扩容配置(auto_scaler.py)
- 最小副本数: 3
- 最大副本数: 10
- 扩容阈值: 队列长度>1000时每次+1个副本
- 缩容阈值: 队列长度<100时每次-1个副本
- 冷却时间: 60秒（避免频繁调整）
- 检查间隔: 10秒

## 常用操作

### 手动扩容
```bash
docker compose scale api=5
```

### 查看队列长度
```bash
redis-cli LLEN celery
```

### 查看日志
```bash
# 所有服务日志
docker compose logs -f

# 仅API日志
docker compose logs -f api

# 仅Worker日志
docker compose logs -f worker
```

### 停止集群
```bash
docker compose down
```

## 架构说明
```
客户端 → Nginx(443) → 负载均衡到API副本 → Redis消息队列 → Celery Worker → 数据存储/报表生成
```
