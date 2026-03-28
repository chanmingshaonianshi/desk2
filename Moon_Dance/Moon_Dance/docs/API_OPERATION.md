# Moon_Dance API 运维文档
本文档为后端运维专用，包含API测试操作步骤、日志体系说明、问题排查指南。

---

## 1. 文档概述
- 适用范围：API服务部署、测试、运维人员
- 文档目的：规范API测试流程，明确日志查询方法，快速定位问题

---

## 2. API测试详细步骤

### 2.1 测试前环境准备
1. **启动依赖服务**：
```bash
# 启动Redis（容器部署可跳过，docker compose会自动启动）
redis-server --daemonize yes
```
2. **启动API服务**：
```bash
# 开发环境启动
python main_api.py

# 生产环境容器启动
docker compose up -d api nginx redis worker
```
3. **验证服务状态**：
```bash
# 健康检查
curl -k https://127.0.0.1/health
# 正常返回：{"ok": true}
```

---

### 2.2 自动化测试执行
**使用内置测试脚本（推荐）**：
```bash
# 运行完整API测试套件
python scripts/api_test.py
```
**测试输出说明**：
```
==================================================
Moon_Dance API 接口自动化测试
==================================================

=== 测试健康检查接口 GET /health ===
✅ 健康检查接口测试通过

=== 测试登录接口 POST /login ===
✅ 登录接口测试通过
✅ 错误密码鉴权测试通过
✅ 缺少参数校验测试通过

=== 测试上传接口 POST /api/v1/upload ===
✅ 首次上传测试通过
✅ 幂等性测试通过
✅ 参数校验测试通过
✅ 鉴权校验测试通过
✅ 旧版本兼容接口测试通过

==================================================
测试完成：3/3 个接口测试通过
==================================================
🎉 所有接口测试全部通过！
```
- 所有测试项标记✅表示通过，❌表示失败，失败会打印具体错误原因

---

### 2.3 手动接口测试（curl示例）
#### 2.3.1 登录接口测试
```bash
curl -k -X POST https://127.0.0.1/login \
  -H "Content-Type: application/json" \
  -d '{"app_id": "moon_dance_app", "app_secret": "moon_dance_secret"}'
```
**成功响应**：
```json
{"ok": true, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "Bearer", "expires_in": 3600}
```
保存返回的`token`值，用于后续接口测试：`export TOKEN="返回的token字符串"`

#### 2.3.2 数据上传接口测试
```bash
curl -k -X POST https://127.0.0.1/api/v1/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "request_id": "'$(uuidgen)'",
    "device_id": "device_001",
    "timestamp": '$(date +%s)000',
    "sensors": {"left_force_n": 300.0, "right_force_n": 280.0},
    "analysis": {"deviation_ratio": 0.034}
  }'
```
**成功响应**：
```json
{"ok": true, "message": "数据已接收，正在异步处理", "request_id": "xxxx-xxxx-xxxx-xxxx"}
```

#### 2.3.3 旧版本兼容接口测试
```bash
curl -k -X POST https://127.0.0.1/api/upload_data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "request_id": "'$(uuidgen)'",
    "device_id": "device_001",
    "timestamp": '$(date +%s)000',
    "sensors": {"left_force_n": 300.0, "right_force_n": 280.0}
  }'
```

---

### 2.4 测试结果验证
1. **业务验证**：检查`data/realtime_logs/upload_log.jsonl`中是否有刚刚上传的数据记录
2. **日志验证**：检查`logs/api_v1_upload.log`中是否有对应的请求日志
3. **幂等验证**：重复发送同一个request_id的上传请求，应该返回200状态码，不会重复写入数据

---

## 3. 日志体系详细说明

### 3.1 日志目录结构
所有日志统一存储在项目根目录外层的`logs/`目录（与Moon_Dance代码目录同级）：
```
logs/
├── health.log                 # 健康检查接口请求日志
├── login.log                  # 登录接口请求日志
├── api_v1_upload.log          # V1上传接口请求日志
├── api_upload_data.log        # 旧版本上传接口请求日志
├── celery_worker.log          # Celery异步任务日志
└── nginx/                     # Nginx访问/错误日志（容器部署才有）
    ├── access.log
    └── error.log
```

---

### 3.2 接口请求日志（每个接口单独文件）
**日志格式**：JSON格式，每行一条请求记录
**字段说明**：
| 字段名 | 类型 | 描述 |
|--------|------|------|
| timestamp | number | 请求时间戳（毫秒） |
| method | string | HTTP请求方法（GET/POST等） |
| path | string | 请求路径 |
| remote_addr | string | 客户端IP地址 |
| headers | object | 完整请求头 |
| query_params | object | URL查询参数 |
| body | object/string | 请求体内容（JSON自动解析，其他格式为原始字符串） |

**示例日志**：
```json
{
  "timestamp": 1700000000000,
  "method": "POST",
  "path": "/api/v1/upload",
  "remote_addr": "192.168.1.100",
  "headers": {"Authorization": "Bearer xxx", "Content-Type": "application/json"},
  "query_params": {},
  "body": {"request_id": "xxx", "device_id": "device_001", "sensors": {"left_force_n": 300, "right_force_n": 280}}
}
```

**常用查询命令**：
```bash
# 统计今日上传接口调用次数
grep -c "POST.*api/v1/upload" logs/api_v1_upload.log

# 查询某个设备的所有请求
grep '"device_id": "device_001"' logs/api_v1_upload.log

# 查询失败的登录请求
grep '"status": 403' logs/login.log

# 查看最近10条请求
tail -n 10 logs/api_v1_upload.log
```

---

### 3.3 业务运行日志
**存储路径**：`data/realtime_logs/`
| 文件名 | 内容说明 |
|--------|----------|
| upload_log.jsonl | 所有上传的原始数据记录，每行一条JSON |
| processed_ids.json | 已处理的幂等request_id列表，JSON数组 |
| realtime_log.jsonl | 桌面端模拟运行产生的实时日志 |

---

### 3.4 Celery异步任务日志
**存储路径**：容器部署可通过`docker compose logs worker`查看
**日志内容**：包含任务接收、处理成功/失败、重试等信息
**常用命令**：
```bash
# 查看Celery Worker实时日志
docker compose logs -f worker

# 统计处理失败的任务
docker compose logs worker | grep "ERROR" | wc -l
```

---

### 3.5 Nginx日志（容器部署）
**存储路径**：容器内`/var/log/nginx/`，可挂载到宿主机
- `access.log`：所有HTTP访问日志，包含请求时间、状态码、响应时间、客户端IP等
- `error.log`：Nginx错误日志，用于排查负载均衡、SSL证书等问题

---

## 4. 常见问题排查
| 问题现象 | 排查步骤 |
|----------|----------|
| 接口返回403 | 1. 检查Authorization头格式是否正确 2. 检查token是否过期 3. 检查app_id和app_secret是否正确 |
| 接口返回400 | 1. 检查request_id是否是合法UUID 2. 检查必填参数是否缺失 3. 检查参数格式是否正确 |
| 上传后没有数据 | 1. 检查Celery Worker是否正常运行 2. 检查Redis服务是否正常 3. 查看Celery日志是否有报错 |
| 证书不被信任 | 1. 将certs/ca.crt导入系统信任列表 2. 生产环境替换为正式CA签发的证书 |
| 接口响应慢 | 1. 查看Redis队列长度是否过长 2. 增加Celery Worker副本数 3. 检查磁盘IO是否瓶颈 |

---

## 5. 生产环境注意事项
1. 必须修改`JWT_SECRET`、`API_APP_SECRET`等默认配置为强随机字符串
2. 测试环境和生产环境配置分离，通过环境变量传入敏感信息
3. 定期清理历史日志文件，避免磁盘占满
4. 日志目录建议挂载独立磁盘分区
5. 生产环境禁止使用`--gen-certs-only`生成的自签名证书，需使用正式SSL证书
