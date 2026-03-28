# Moon_Dance API 文档

## 基础信息
- **通信协议**：HTTPS
- **请求格式**：JSON
- **响应格式**：JSON
- **默认端口**：443
- **鉴权方式**：JWT Bearer Token（登录接口除外）

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
- 403：未授权或Token无效

---

### 4. 兼容上传接口（旧版本）
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
