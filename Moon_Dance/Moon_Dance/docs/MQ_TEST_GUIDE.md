# MQ架构测试操作指南
本文档包含完整的MQ架构测试步骤，从环境准备到功能验证的全流程操作说明。

---

## 一、环境准备
### 1. 安装依赖
```bash
# 安装所有依赖
pip install -r requirements.txt
```

### 2. 启动Redis服务
```bash
# Windows启动（需要先安装Redis）
redis-server --daemonize yes

# 验证Redis是否正常运行
redis-cli ping
# 返回 PONG 表示正常
```

---

## 二、启动MQ服务节点
使用提供的管理脚本启动服务节点：

### 1. 查看节点状态
```bash
python scripts/mq_manager.py status
```

### 2. 启动服务节点
```bash
# 启动3个数据验证节点（根据压力可调整副本数）
python scripts/mq_manager.py start validator 3

# 启动2个数据写入节点
python scripts/mq_manager.py start writer 2

# 启动1个日志统计节点
python scripts/mq_manager.py start logger
```

### 3. 验证启动成功
```bash
python scripts/mq_manager.py status
```
输出示例：
```
======================================================================
模块名称          副本ID    PID      状态      
======================================================================
validator        1        1234     运行中    
validator        2        1235     运行中    
validator        3        1236     运行中    
writer           1        1237     运行中    
writer           2        1238     运行中    
logger           1        1239     运行中    
======================================================================
总运行节点数: 6
======================================================================
```

---

## 三、运行测试
### 1. 运行设备模拟器（发送测试数据）
```bash
# 无头模式启动模拟器，自动生成数据并发送到MQ
python main.py --no-gui --device-count 5 --duration 60
```
参数说明：
- `--device-count 5`：模拟5台设备同时发送数据
- `--duration 60`：运行60秒后自动停止

### 2. 观察运行输出
正常输出会显示：
```
[MQ] 消息发送成功 550e8400-e29b-41d4-a716-446655440000
[设备01] 重传结果：成功0条，失败0条，待发送0条
[validator_worker_1] 消息处理成功 1689324567890-0
[writer_worker_1] 数据写入成功 550e8400-e29b-41d4-a716-446655440000 (设备: device_001)
```

---

## 四、功能验证
### 1. 验证数据写入
```bash
# 查看实时日志是否有数据写入
ls ../data/realtime_logs/
# 应该看到形如 device_001_20260328.jsonl 的设备日志文件

# 查看日志内容
tail -n 10 ../data/realtime_logs/device_001_*.jsonl
```

### 2. 验证重传机制（可选）
```bash
# 1. 停止Redis服务模拟网络故障
redis-cli shutdown

# 2. 运行模拟器，此时消息会发送失败进入本地待重传队列
python main.py --no-gui --device-count 2 --duration 10

# 3. 重新启动Redis
redis-server --daemonize yes

# 4. 观察客户端会自动重传失败的消息
# 输出会显示 [MQ] 重试发送消息 xxx
```

### 3. 查看统计日志
```bash
# 查看日志统计输出
cat ../logs/statistics.log
# 会显示每分钟的流量统计报表，包含总消息数、设备数等信息
```

### 4. 查看节点日志
```bash
# 查看验证节点日志
cat ../logs/validator_worker_1.log

# 查看写入节点日志
cat ../logs/writer_worker_1.log

# 查看日志统计节点日志
cat ../logs/logger_worker.log
```

---

## 五、停止服务
```bash
# 停止所有MQ节点
python scripts/mq_manager.py stop all

# 停止Redis服务
redis-cli shutdown
```

---

## 六、常见问题排查
| 问题 | 排查方法 |
|------|----------|
| 消息发送失败 | 1. 检查Redis是否运行 2. 检查REDIS_URL配置是否正确 |
| 数据没有写入文件 | 1. 检查writer节点是否运行 2. 查看writer节点日志是否有报错 3. 检查validated_data队列是否有消息堆积 |
| 重传不生效 | 1. 检查客户端pending目录是否有待发送文件 2. 查看客户端输出是否有重试日志 |
| 节点启动失败 | 1. 查看对应节点日志文件 2. 检查端口是否被占用 3. 检查依赖是否完整安装 |
