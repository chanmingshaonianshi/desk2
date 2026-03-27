# Moon_Dance 数据服务系统 API 接口说明文档

## 1. 核心数据上传接口 (Ingest API)

本接口用于接收模拟客户端（或真实硬件设备）采集的传感器数据，并将其加入服务器的 Redis 异步消息队列。

- **接口地址**: `https://www.myhjmycjh.tech/api/v2/ingest` (外网访问) 或 `https://124.220.79.133/api/v2/ingest` (IP直连)
- **请求方式**: `POST`
- **传输频率**: 客户端默认每 `5` 秒发送一次（可通过启动参数 `-interval` 动态调整频率，支持高并发）
- **鉴权方式**: Bearer Token 安全认证 (请求头需携带 `Authorization: Bearer <token>`)
- **数据格式**: `application/json`

---

### 1.1 请求参数表 (Request Body)

当客户端向服务器发送数据时，JSON 结构中包含以下字段：

| 参数名称 | 数据类型 | 是否必填 | 描述说明 |
| :--- | :--- | :---: | :--- |
| `device_id` | String | 是 | 设备的唯一标识符，例如 "sim_device_001" |
| `timestamp` | Integer | 是 | 数据采集时的毫秒级时间戳 (Unix Timestamp) |
| `sensors` | Object | 是 | 核心物理传感器数据集合 |
| `sensors.left_force_n` | Float | 是 | 左侧传感器受力值，单位：牛顿 (N) |
| `sensors.right_force_n` | Float | 是 | 右侧传感器受力值，单位：牛顿 (N) |
| `sensors.total_force_n` | Float | 是 | 左右受力总和，单位：牛顿 (N) |
| `analysis` | Object | 是 | 客户端边缘计算（本地预分析）数据集合 |
| `analysis.deviation_ratio`| Float | 是 | 左右受力偏差率，范围 0~1，用于衡量平衡性 |

---

### 1.2 响应参数表 (Response)

#### 🟢 成功响应 (HTTP Status: 202 Accepted)
服务器已成功接收数据，通过 Token 鉴权，并成功将数据压入 Redis 队列，等待 Celery Worker 处理。

| 参数名称 | 数据类型 | 描述说明 |
| :--- | :--- | :--- |
| `status` | String | 状态标识，固定为 "success" |
| `message` | String | 处理结果提示，例如 "Data queued for processing" |
| `task_id` | String | Celery 异步任务分配的唯一 UUID |

#### 🔴 失败响应 (HTTP Status: 401 Unauthorized / 403 Forbidden)
请求未通过安全校验，被服务器 API 路由直接拦截。

| 参数名称 | 数据类型 | 描述说明 |
| :--- | :--- | :--- |
| `error` | String | 具体的错误原因，例如 "Missing Authorization header" 或 "Invalid token" |

---

## 2. 系统健康检查接口 (Health Check API)

用于监控脚本或负载均衡器（Nginx）判断后端 API 容器是否存活。

- **接口地址**: `http://api:8000/health` (仅限 Docker 内部网络访问)
- **请求方式**: `GET`
- **响应格式**: `{"ok": true}` (HTTP 200 OK)