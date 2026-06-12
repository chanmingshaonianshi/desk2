# Moon_Dance 小程序开发文档

## 1. 文档目的

这份文档面向小程序前端同学，说明当前后端已经提供了哪些功能、页面应该如何对接、代码结构在哪些目录，以及联调时常见问题如何定位。

## 2. 当前已实现功能

- 用户注册/更新
- 用户密码登录
- `X-API-Key + Bearer Token` 双重鉴权
- 设备实时坐姿查询
- 设备历史明细查询
- 个人评分统计查询
- 每日排行榜查询
- 用户设置更新

## 3. 推荐页面结构

- 首页
  - 设备在线状态
  - 当前左右压力
  - 当前坐姿标签
  - 当前连续入座时长
- 统计页
  - 平均评分
  - 总久坐时长
  - 不良坐姿次数
  - 近 7 天评分趋势图
  - 每日详情列表
- 排行页
  - 指定日期排行榜
  - 个人排名
  - 排名前十列表
- 我的页
  - 用户基本信息
  - 当前绑定设备
  - 久坐提醒阈值
  - 是否开启提醒
  - 是否参与排行榜

## 4. 前端对应接口

### 4.0 鉴权规则（必须统一实现）

- `POST /api/miniapp/user/register`、`POST /api/miniapp/user/login`
  - 只需要：`X-API-Key: myh`
- 其余业务接口（`realtime/history/stats/leaderboard/settings`）
  - 必须同时携带：
    - `X-API-Key: myh`
    - `Authorization: Bearer <token>`

### 4.1 注册

- `POST /api/miniapp/user/register`
- 用途：首次注册、绑定设备、补设密码

### 4.2 登录

- `POST /api/miniapp/user/login`
- 用途：获取 Bearer Token 和当前用户信息

### 4.3 实时数据

- `GET /api/miniapp/device/<device_id>/realtime`
- 用途：首页轮询展示当前坐姿和左右压力

### 4.4 历史明细

- `GET /api/miniapp/device/<device_id>/history`
- 用途：画左右压力历史曲线、偏差率时间线

### 4.5 评分统计

- `GET /api/miniapp/user/<user_id>/stats`
- 用途：画健康评分趋势图、展示汇总卡片和每日详情

约束：

- `<user_id>` 必须使用登录接口返回的 `user.id`（或 openid）
- 不支持 `/api/miniapp/user/me/stats` 这类占位写法
- 若 `user_id` 与 token 所属用户不一致，会返回 403（无权访问）

### 4.6 排行榜

- `GET /api/miniapp/leaderboard`
- 用途：排行页、历史日期排行切换

### 4.7 设置更新

- `PUT /api/miniapp/user/<user_id>/settings`
- 用途：修改久坐提醒阈值、排行榜可见性等

## 5. 后端代码结构

### 5.1 小程序接口入口

- `src/api/miniapp_routes.py`
- 这里定义了小程序所有核心接口：
  - `realtime`
  - `history`
  - `stats`
  - `leaderboard`
  - `register`
  - `login`
  - `settings`

### 5.2 鉴权逻辑

- `src/api/auth.py`
- 这里定义了：
  - API Key 校验
  - 小程序 JWT 签发
  - Bearer Token 校验
  - 双重鉴权装饰器

### 5.3 用户与统计数据模型

- `src/utils/mysql_db.py`
- 这里定义了：
  - `users`
  - `user_daily_stats`

### 5.4 历史汇总任务

- `scripts/daily_aggregation.py`
- 作用：
  - 从 MongoDB `pressure_data` 读取原始明细
  - 按天聚合
  - 写入 MySQL `user_daily_stats`

### 5.5 实时原始数据来源

- `src/utils/mongo_db.py`
- `pressure_data` 集合
- 数据通常来自设备上传链路或模拟器上传链路

## 6. 页面取值建议

### 6.1 首页

读取：

- `realtime.data.sensors.left_force_n`
- `realtime.data.sensors.right_force_n`
- `realtime.data.posture_label`
- `realtime.data.continuous_seated_minutes`
- `realtime.data.is_online`

### 6.2 历史曲线页或首页扩展模块

读取：

- `history.data.records`
- 横轴：`time_label`
- 纵轴：
  - `left_force_n`
  - `right_force_n`

### 6.3 统计页

读取：

- `stats.data.summary.avg_health_score`
- `stats.data.summary.total_seated_minutes`
- `stats.data.summary.total_bad_posture_count`
- `stats.data.daily_records`

趋势图推荐：

- 横轴：`daily_records[].date`
- 纵轴：`daily_records[].health_score`

### 6.4 排行页

读取：

- `leaderboard.data.total_participants`
- `leaderboard.data.leaderboard`

列表字段推荐：

- `rank`
- `nickname`
- `health_score`
- `total_seated_minutes`
- `bad_posture_count`

## 7. 联调顺序建议

1. 先注册
2. 再登录
3. 保存 `token`
4. 拿 `user.id`
5. 访问 `realtime/history/stats/leaderboard/settings`

## 8. 常见问题

### 8.1 看得到排行榜，看不到统计

优先检查：

- 当前登录用户 id 是否和 stats 路径一致
- 是否补跑了 `daily_aggregation.py`
- 前端是否读取了 `res.data.data.daily_records`
- 是否把 `stats` 的 `user_id` 写死成了 1（应使用登录返回的 `user.id`）
- 若后端返回 `403 无权访问`，说明 token 用户与 URL 中 user_id 不一致

### 8.2 接口成功了，但页面空白

优先检查：

- 页面 JS 是否有运行时错误
- 图表组件是否还是占位组件
- 是否把 `res.data.data.xxx` 写成了 `res.data.xxx`
- `daily_records` 可能少于 7 天，前端应允许“数据不足也能画图/能显示汇总卡片”

### 8.3 history 为空但 realtime 有数据

常见原因：

- `history` 默认查最近 24 小时，而你设备最近一条数据可能早于 24 小时窗口
- 前端请求参数过大导致超时，建议先用 `hours=1&limit=50` 验证
- MongoDB 库名与环境不一致导致查询不到（以服务端 `MONGO_DB_NAME` 配置为准）

### 8.3 看到了 `gAAAAA...`

说明前端读错了上传接口的密文，不是小程序接口返回值。
小程序只应该读取 `/api/miniapp/*`。

## 9. 联调命令入口

完整的“产生日志 -> 汇总 -> 实时/历史/统计/排行榜”一键验证命令，见：

- `Moon_Dance/演示提示命令.txt`

---

# Web 管理端设计与 API 文档

## 10. 文档说明

本部分用于补充智能坐垫项目 Web 管理端的设计方案、页面功能、前后端数据流、接口调用方式、安全机制和部署方式。

Web 管理端主要面向坐垫售卖方、运营人员和售后人员，用于查看已注册硬件设备的运行状态、地域分布、设备台账、用户统计和运营分析。

对应代码位置：

| 内容 | 路径 |
| --- | --- |
| Vue 前端源码 | `Moon_Dance/Moon_Dance/web_admin_vue/` |
| 已构建静态页面 | `Moon_Dance/Moon_Dance/web_admin/` |
| 前端 API 封装 | `Moon_Dance/Moon_Dance/web_admin_vue/src/api/admin.js` |
| 后端管理接口 | `Moon_Dance/Moon_Dance/src/api/admin_routes.py` |
| Flask 入口 | `Moon_Dance/Moon_Dance/main_api.py` |
| Docker 部署配置 | `Moon_Dance/Moon_Dance/deploy/docker-compose.yml` |

## 11. Web 管理端建设目标

Web 管理端需要完成以下目标：

1. 管理员可以通过浏览器访问管理端页面。
2. 管理员可以登录系统，登录后查看设备和用户统计数据。
3. 前端通过后端 API 获取数据，而不是静态写死数据。
4. 页面包含多种数据展示形式，例如指标卡片、折线图、柱状图、中国地图热力图和表格。
5. 后端接口具备访问安全性，避免未授权访问。
6. 前后端部署到云服务器，并具备基础并发处理能力。

## 12. 用户角色与使用场景

| 角色 | 使用目的 |
| --- | --- |
| 售卖方管理人员 | 查看设备投放规模、设备活跃情况和地区使用情况 |
| 运营人员 | 分析设备使用趋势、省份活跃情况和产品投放效果 |
| 售后人员 | 查看离线设备、异常设备和待跟进设备 |

核心使用场景：

1. 查看当前注册设备数、活跃设备数、离线设备数和异常设备数。
2. 查看中国地图热力图，判断不同省份的设备使用情况。
3. 通过设备台账筛选在线、离线、异常设备。
4. 通过数据分析页查看省份设备排行、在线/离线对比和用户统计。
5. 通过浏览器开发者工具验证前端是否真正调用后端接口。

## 13. 系统总体架构

系统整体数据流如下：

```text
智能坐垫硬件
    ↓
Flask 后端 API
    ↓
MongoDB / MySQL / Redis
    ↓
Vue 3 + Element Plus 管理端
    ↓
管理员浏览器访问 /admin/
```

说明：

- 智能坐垫硬件负责采集压力、入座状态和入座时长等数据。
- Flask 后端 API 负责接收、聚合和返回数据。
- MongoDB 主要存储设备上报和压力数据。
- MySQL 主要存储用户和统计数据。
- Redis 主要用于缓存、消息队列和异步任务支持。
- Vue 3 + Element Plus 管理端负责展示设备运营和统计分析页面。
- 管理员通过 `/admin/` 页面访问 Web 管理端。

## 14. 技术选型

### 14.1 前端技术

| 技术 | 用途 |
| --- | --- |
| Vue 3 | 构建 Web 管理端单页应用 |
| Vite | 前端工程化构建工具 |
| Element Plus | 后台管理组件库，提供表单、表格、菜单、卡片、按钮等组件 |
| ECharts | 图表库，用于折线图、柱状图、地图热力图等 |
| JavaScript / HTML / CSS | 页面逻辑、结构和样式 |

### 14.2 后端技术

| 技术 | 用途 |
| --- | --- |
| Flask | 提供后端 API 接口 |
| JWT | 管理员登录后的 Token 身份认证 |
| MongoDB | 存储设备压力数据和上报记录 |
| MySQL | 存储用户和统计类数据 |
| Redis | 支持缓存和异步任务队列 |
| Celery Worker | 处理异步任务 |

### 14.3 部署技术

| 技术 | 用途 |
| --- | --- |
| Docker Compose | 统一启动 Nginx、API、数据库、Redis、Worker 等服务 |
| Nginx | 反向代理、统一公网入口和负载均衡 |
| 云服务器 | 对外提供公网访问能力 |

## 15. Web 前端页面设计

Web 管理端采用后台管理系统常见的三段式结构：

```text
左侧导航栏 + 顶部 Header + 内容主区
```

页面模块包括：

| 页面 | 功能 |
| --- | --- |
| 登录页 | 管理员输入账号、密码和 API Key 登录 |
| 运营总览 | 查看设备核心指标、地区热力图和待跟进设备 |
| 设备售后台账 | 查看设备列表、在线状态、最后上报时间和处理建议 |
| 数据分析 | 查看省份运营分析、用户统计和趋势图表 |

页面设计原则：

1. 面向售卖方和运营人员，不以个人健康数据为主。
2. 首页优先展示运营决策需要的核心指标。
3. 压力曲线、不良坐姿等细节数据不作为主要展示内容。
4. 多使用图表和表格，减少大段文字。
5. 页面风格采用商务、克制、清晰的后台管理风格。

## 16. 页面功能说明

### 16.1 运营总览页

运营总览页主要展示：

- 注册设备数
- 活跃设备数
- 离线设备数
- 异常设备数
- 中国地图热力图
- 待跟进设备列表

页面价值：

> 帮助运营人员快速判断当前设备整体运行是否正常，并识别需要重点关注的地区和设备。

### 16.2 设备售后台账页

设备售后台账页主要展示：

- 设备编号
- 所属地区
- 绑定用户
- 在线状态
- 坐姿/设备状态
- 最后上报时间
- 处理建议

支持筛选：

- 全部设备
- 在线设备
- 离线设备
- 异常设备

页面价值：

> 将原始设备数据转化为售后人员可执行的信息，帮助售后快速定位待处理设备。

### 16.3 数据分析页

数据分析页面主要展示运营管理人员关心的数据：

- 设备使用趋势
- 省份设备数量排行
- 省份在线/离线设备对比
- 省份运营明细表
- 用户统计表

页面价值：

> 帮助运营人员判断设备投放效果、地区活跃情况和后续运营方向。

## 17. 前后端数据流

前后端数据流如下：

```text
管理员打开 /admin/
    ↓
输入账号、密码、API Key
    ↓
POST /api/admin/login
    ↓
后端返回 JWT Token
    ↓
前端保存 Token 和 API Key
    ↓
前端请求 /api/admin/summary、/devices、/regions、/analytics、/users
    ↓
后端从 MongoDB / MySQL 聚合数据
    ↓
前端渲染指标卡片、图表、地图和表格
```

## 18. Web 管理端 API 设计

### 18.1 接口基础信息

| 项目 | 说明 |
| --- | --- |
| 接口前缀 | `/api/admin` |
| 请求格式 | JSON |
| 响应格式 | JSON |
| 登录接口认证 | 需要 `X-API-Key` |
| 其他接口认证 | 需要 `X-API-Key` + `Authorization: Bearer <token>` |

### 18.2 通用响应格式

成功响应：

```json
{
  "ok": true,
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "ok": false,
  "message": "错误信息",
  "data": null
}
```

### 18.3 前端请求头设计

登录接口请求头：

```http
Content-Type: application/json
X-API-Key: <api_key>
```

登录后业务接口请求头：

```http
Content-Type: application/json
X-API-Key: <api_key>
Authorization: Bearer <token>
```

说明：

- `X-API-Key` 可以理解为接口访问密钥。
- `Authorization: Bearer <token>` 是管理员登录成功后的身份凭证。
- 展示截图时建议打码 API Key 和 Token 的具体值。

## 19. Web 管理端接口列表

### 19.1 管理员登录

| 项目 | 内容 |
| --- | --- |
| 接口 | `POST /api/admin/login` |
| 说明 | 管理员登录，获取 JWT Token |
| 是否需要 Token | 否 |
| 是否需要 API Key | 是 |

请求体：

```json
{
  "username": "admin",
  "password": "admin123456"
}
```

响应数据：

```json
{
  "token": "JWT Token 字符串",
  "token_type": "Bearer",
  "expires_in": 7200,
  "admin": {
    "username": "admin"
  }
}
```

### 19.2 获取运营总览数据

| 项目 | 内容 |
| --- | --- |
| 接口 | `GET /api/admin/summary` |
| 说明 | 获取设备和用户核心统计指标 |
| 是否需要 Token | 是 |
| 是否需要 API Key | 是 |

主要字段：

| 字段 | 说明 |
| --- | --- |
| `registered_devices` | 注册设备数 |
| `online_devices` | 在线设备数 |
| `seated_devices` | 当前入座设备数 |
| `bad_posture_devices` | 异常状态设备数 |
| `registered_users` | 注册用户数 |
| `avg_deviation_ratio` | 平均压力偏差率 |
| `avg_health_score` | 平均健康评分 |
| `total_seated_minutes_30d` | 近 30 天总入座时长 |

前端用途：

> 用于运营总览页的指标卡片和核心数据展示。

### 19.3 获取设备列表

| 项目 | 内容 |
| --- | --- |
| 接口 | `GET /api/admin/devices` |
| 说明 | 获取设备台账列表 |
| 是否需要 Token | 是 |
| 是否需要 API Key | 是 |

响应结构：

```json
{
  "total": 10,
  "devices": []
}
```

设备字段：

| 字段 | 说明 |
| --- | --- |
| `device_id` | 设备编号 |
| `region` | 设备所属地区 |
| `is_online` | 是否在线 |
| `last_update_ms` | 最后上报时间 |
| `is_seated` | 是否处于入座状态 |
| `posture_status` | 状态，`normal` 或 `bad` |
| `left_force_n` | 左侧压力 |
| `right_force_n` | 右侧压力 |
| `deviation_ratio` | 左右压力偏差 |
| `user_id` | 绑定用户 ID |
| `nickname` | 用户昵称 |

前端用途：

> 用于设备售后台账表格、设备状态筛选和处理建议生成。

### 19.4 获取地区分布数据

| 项目 | 内容 |
| --- | --- |
| 接口 | `GET /api/admin/regions` |
| 说明 | 获取地区设备数量统计 |
| 是否需要 Token | 是 |
| 是否需要 API Key | 是 |

响应结构：

```json
{
  "regions": [
    {
      "name": "北京",
      "value": 10
    }
  ]
}
```

前端用途：

> 用于中国地图热力图、省份设备排行和地区运营分析。

注意：

> 当前地区数据主要用于运营分析展示，后端根据设备 ID 做地区映射，不能说成 GPS 精确定位数据。后续如需真实地区，应在设备注册信息中增加省份/城市字段。

### 19.5 获取统计分析数据

| 项目 | 内容 |
| --- | --- |
| 接口 | `GET /api/admin/analytics?days=30` |
| 说明 | 获取指定天数内的趋势统计数据 |
| 是否需要 Token | 是 |
| 是否需要 API Key | 是 |

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `days` | number | 查询天数，范围 1 到 365 |

响应结构：

```json
{
  "days": 30,
  "timeline": [],
  "pressure_points": []
}
```

`timeline` 字段：

| 字段 | 说明 |
| --- | --- |
| `date` | 日期 |
| `avg_health_score` | 平均健康评分 |
| `total_seated_minutes` | 总入座时长 |
| `bad_posture_count` | 不良坐姿次数 |
| `good_posture_ratio` | 良好坐姿比例 |

前端用途：

> 用于数据分析页中的趋势图表。当前页面会优先展示运营相关趋势和省份分析，压力曲线等细节数据不作为主要内容。

### 19.6 获取用户统计数据

| 项目 | 内容 |
| --- | --- |
| 接口 | `GET /api/admin/users` |
| 说明 | 获取用户统计列表 |
| 是否需要 Token | 是 |
| 是否需要 API Key | 是 |

响应结构：

```json
{
  "total": 10,
  "users": []
}
```

用户字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 用户 ID |
| `openid` | 小程序用户标识 |
| `nickname` | 用户昵称 |
| `device_id` | 绑定设备编号 |
| `total_score` | 总积分 |
| `sedentary_threshold_min` | 久坐提醒阈值 |
| `reminder_enabled` | 是否开启提醒 |
| `visible_in_leaderboard` | 是否展示在排行榜 |
| `updated_at` | 更新时间 |

前端用途：

> 用于数据分析页底部的用户统计表。

## 20. 前端 API 封装说明

前端接口封装文件：

```text
Moon_Dance/Moon_Dance/web_admin_vue/src/api/admin.js
```

主要功能：

1. 从浏览器本地存储读取 `adminToken` 和 `adminApiKey`。
2. 登录成功后保存 Token 和 API Key。
3. 统一封装请求头。
4. 提供 `summary`、`devices`、`regions`、`analytics`、`users` 等方法给页面调用。

核心调用关系：

```text
LoginView.vue
    ↓ loginAdmin()
/api/admin/login

App.vue
    ↓ createAdminApi()
DashboardView.vue / DeviceView.vue / AnalyticsView.vue
    ↓
/api/admin/summary
/api/admin/devices
/api/admin/regions
/api/admin/analytics
/api/admin/users
```

## 21. 后端接口安全设计

后端管理接口采用两层安全机制：

### 21.1 API Key 校验

所有管理接口均需要携带：

```http
X-API-Key: <api_key>
```

后端会判断请求头中的 `X-API-Key` 是否与配置中的 `API_KEY` 一致。

### 21.2 JWT Token 校验

管理员登录成功后，后端生成 JWT Token。

后续请求需要携带：

```http
Authorization: Bearer <token>
```

后端会校验：

- Token 是否存在
- Token 是否过期
- Token 类型是否为 `admin`
- Token 签名是否正确

如果校验失败，接口会返回 401 或 403。

## 22. 部署设计

### 22.1 前端构建

前端源码目录：

```text
Moon_Dance/Moon_Dance/web_admin_vue/
```

构建命令：

```bash
npm install
npm run build
```

构建产物输出到：

```text
Moon_Dance/Moon_Dance/web_admin/
```

Flask 托管路径：

```text
/admin/
```

### 22.2 Docker Compose 部署

部署目录：

```text
Moon_Dance/Moon_Dance/deploy/
```

启动命令：

```bash
docker compose up -d --build
```

服务组成：

| 服务 | 说明 |
| --- | --- |
| `nginx` | 反向代理，对外提供 80、443、8000 端口 |
| `api` | Flask 后端 API 服务 |
| `mongodb` | 存储设备压力和上报数据 |
| `mysql` | 存储用户和统计数据 |
| `redis` | 消息队列和缓存 |
| `worker` | Celery 异步任务处理 |

### 22.3 并发处理

当前并发处理设计包括：

1. Nginx 使用反向代理和负载均衡。
2. API 服务配置 `replicas: 3`，即 3 个后端副本。
3. Worker 使用 `--concurrency=4`，支持多个后台任务并发处理。
4. Redis 支持任务队列和缓存。

## 23. 测试与验证

### 23.1 页面访问验证

访问：

```text
http://124.220.79.133/admin/
```

或已解析域名：

```text
http://myhjmycjh.tech/admin/
```

### 23.2 登录验证

默认演示账号：

```text
用户名：admin
密码：admin123456
API Key：myh
```

公开截图或汇报材料中建议对密码、API Key 和 Token 打码。

### 23.3 前后端接口验证

打开浏览器 F12，进入 Network 面板，确认以下接口返回 200：

```text
/api/admin/login
/api/admin/summary
/api/admin/devices
/api/admin/regions
/api/admin/analytics
/api/admin/users
```

这些请求成功返回，可以说明前端页面不是静态页面，而是通过后端 API 获取数据。

### 23.4 服务器部署验证

在服务器执行：

```bash
cd ~/desk2/Moon_Dance/Moon_Dance/deploy
docker compose ps
```

需要看到：

```text
deploy-api-1
deploy-api-2
deploy-api-3
deploy-mongodb-1
deploy-mysql-1
deploy-nginx-1
deploy-redis-1
deploy-worker-1
```

### 23.5 并发配置验证

查看 API 副本：

```bash
grep -n -A 8 -B 3 "replicas" docker-compose.yml
```

查看 Worker 并发：

```bash
grep -n -A 3 -B 3 "concurrency" docker-compose.yml
```

## 24. Web 管理端总结

本 Web 管理端围绕坐垫售卖方和运营人员的实际需求进行设计，重点展示设备运营状态、设备台账、地区热度和省份分析。

系统使用 Vue 3、Element Plus 和 ECharts 构建前端页面，使用 Flask 提供后端管理接口，通过 `X-API-Key + JWT Token` 实现接口访问安全，通过 Docker Compose 和 Nginx 完成云服务器部署，并通过 API 多副本和 Worker 并发配置提供基础并发处理能力。

整体上，Web 管理端已经满足课程任务中关于 Web 前端、Web 后端、数据展示、云端部署、安全性和并发性的要求。
