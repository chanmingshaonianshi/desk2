# Moon_Dance API 文档

## 基础信息
- **通信协议**：HTTPS
- **请求格式**：JSON
- **响应格式**：JSON
- **默认端口**：443
- **鉴权方式**：JWT Bearer Token（登录接口除外）

## 传输加密说明

### 1. 当前模拟器默认会发送加密载荷

本地运行 `simulator_client.py` 时，默认会附带 `--encrypt` 参数，因此上传到服务端的请求体可能不是明文 JSON，而是：

```json
{
  "encrypted_payload": "gAAAAABqAEEW4Qpsl2Kvr0zyVg7fMGJOcj6wuVaIGwWFb9tabMgitWy..."
}
```

其中 `gAAAAA...` 是 **Fernet 对称加密后的密文字符串**，不是乱码，也不是前端需要展示的数据结构。

### 2. 解密发生在服务端，不发生在小程序前端

服务端在接收上传请求时，会自动判断请求体里是否存在 `encrypted_payload`：

- 如果存在：服务端先自动解密，再继续做 `request_id` 校验、日志写入和异步处理
- 如果不存在：按普通明文 JSON 直接处理

也就是说：

- **上传端可以发送加密数据**
- **服务端负责解密**
- **小程序前端不需要自己解密**

### 3. 小程序前端为什么不该看到密文

小程序前端正常应调用的是以下查询接口：

- `/api/miniapp/device/<device_id>/realtime`
- `/api/miniapp/user/<user_id>/stats`
- `/api/miniapp/leaderboard`
- `/api/miniapp/user/<user_id>/settings`

这些接口返回的应该始终是普通 JSON 业务数据，不会返回 `encrypted_payload`。

如果前端同学看到 `gAAAAA...`，通常说明发生了下面几种情况之一：

1. 前端拿到了“上传接口”的原始请求体，而不是“小程序查询接口”的响应体
2. 前端把加密上传示例误当成了要展示给用户的数据结构
3. 前端直接观察了 simulator 上传包，但没有区分“上传协议”和“查询接口”

### 4. 结论

对前端同学来说：

- **不需要解密 `gAAAAA...`**
- **不需要自己实现 Fernet 解密**
- **只需要调用后端提供的小程序业务接口，读取正常 JSON 响应即可**

---

## 接口列表

### 1. 健康检查接口
**接口地址**：`GET /health`
**鉴权要求**：不需要
**接口描述**：检查服务是否正常运行
**请求参数**：无
**响应示例**：
```json
{
  "ok": true
}
```
**响应状态码**：
- 200：服务正常

---

### 2. 登录获取Token接口
**接口地址**：`POST /login`
**鉴权要求**：不需要
**接口描述**：使用app_id和app_secret获取访问令牌
**请求参数**：
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| app_id | string | 是 | 应用ID，默认值：`moon_dance_app` |
| app_secret | string | 是 | 应用密钥，默认值：`moon_dance_secret` |
**请求示例**：
```json
{
  "app_id": "moon_dance_app",
  "app_secret": "moon_dance_secret"
}
```
**响应示例**：
```json
{
  "ok": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```
**响应状态码**：
- 200：登录成功
- 400：缺少必要参数
- 403：app_id或app_secret错误

---

### 3. 数据上传接口（V1版本）
**接口地址**：`POST /api/v1/upload`
**鉴权要求**：需要，Header中携带`Authorization: Bearer <token>`
**接口描述**：上传坐姿监测数据，异步处理
**幂等性**：支持，通过request_id去重，重复请求返回200
**加密支持**：支持。可直接上传明文 JSON，也可上传 `{ "encrypted_payload": "<Fernet密文>" }`，服务端会自动解密
**请求参数**：
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| request_id | string | 是 | 幂等请求ID，必须是合法UUID |
| device_id | string | 是 | 设备ID，格式如`device_001` |
| timestamp | number | 是 | 数据采集时间戳，毫秒级 |
| sensors | object | 是 | 传感器数据 |
| sensors.left_force_n | number | 是 | 左侧压力值（单位：牛） |
| sensors.right_force_n | number | 是 | 右侧压力值（单位：牛） |
| analysis | object | 否 | 预分析结果 |
| analysis.deviation_ratio | number | 否 | 坐姿偏差率（0-1） |
**请求示例**：
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "device_001",
  "timestamp": 1700000000000,
  "sensors": {
    "left_force_n": 300.0,
    "right_force_n": 280.0
  },
  "analysis": {
    "deviation_ratio": 0.034
  }
}
```
**响应示例**：
```json
{
  "ok": true,
  "message": "数据已接收，正在异步处理",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
**响应状态码**：
- 202：数据已接收，正在处理
- 200：重复请求，数据已处理
- 400：参数错误（缺少request_id或格式非法）
- 400：密文解密失败
- 403：未授权或Token无效

---

### 4. 数据摄取接口（V2版本）
**接口地址**：`POST /api/v2/ingest`
**鉴权要求**：需要，Header中携带 `X-API-Key: myh`
**接口描述**：统一 API Key 设备上传接口，支持异步处理
**幂等性**：支持，通过request_id去重，重复请求返回200
**加密支持**：支持。`simulator_client.py` 默认就是通过该接口发送加密载荷
**请求方式**：

方式 A，明文上传：

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "device_001",
  "timestamp": 1700000000000,
  "sensors": {
    "left_force_n": 300.0,
    "right_force_n": 280.0
  },
  "analysis": {
    "deviation_ratio": 0.034
  }
}
```

方式 B，加密上传：

```json
{
  "encrypted_payload": "gAAAAABqAEEW4Qpsl2Kvr0zyVg7fMGJOcj6wuVaIGwWFb9tabMgitWy..."
}
```

**请求头示例**：

```http
Content-Type: application/json
X-API-Key: myh
```

**响应**：同 `/api/v1/upload`

---

### 5. 兼容上传接口（旧版本）
**接口地址**：`POST /api/upload_data`
**鉴权要求**：需要
**接口描述**：与V1上传接口完全一致，仅路径不同，用于兼容旧版本客户端
**参数/响应**：同`/api/v1/upload`

---

## 错误码说明
| 状态码 | 说明 |
|--------|------|
| 200 | 成功/重复请求 |
| 202 | 已接受异步处理 |
| 400 | 请求参数错误 |
| 403 | 鉴权失败/无权限 |
| 500 | 服务内部错误 |
