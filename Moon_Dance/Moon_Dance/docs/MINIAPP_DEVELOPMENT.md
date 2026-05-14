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

### 8.2 接口成功了，但页面空白

优先检查：

- 页面 JS 是否有运行时错误
- 图表组件是否还是占位组件
- 是否把 `res.data.data.xxx` 写成了 `res.data.xxx`

### 8.3 看到了 `gAAAAA...`

说明前端读错了上传接口的密文，不是小程序接口返回值。
小程序只应该读取 `/api/miniapp/*`。
