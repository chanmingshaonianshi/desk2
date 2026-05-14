# Moon_Dance 文档索引

## 核心文档

- `Moon_Dance/docs/ARCHITECTURE.md`
  - 最新系统架构说明
- `Moon_Dance/docs/BACKEND_IMPLEMENTATION.md`
  - 后端实现原理与答辩讲解说明
- `Moon_Dance/docs/API.md`
  - 上传链路与 API 总文档
- `Moon_Dance/docs/MINIAPP_DEVELOPMENT.md`
  - 小程序功能说明、页面建议、代码结构说明
- `小程序API对接文档.txt`
  - 发给前端同学的对接文档，含接口、命令、排查建议

## 部署与演示

- `Moon_Dance/docs/README_DOCKER.md`
  - Docker 部署说明
- `Moon_Dance/docs/README.txt`
  - 项目概览与目录结构说明
- `演示提示命令.txt`
  - 演示、联调、服务器操作命令

## 当前小程序相关重点

- 实时坐姿：`GET /api/miniapp/device/<device_id>/realtime`
- 历史明细：`GET /api/miniapp/device/<device_id>/history`
- 评分统计：`GET /api/miniapp/user/<user_id>/stats`
- 排行榜：`GET /api/miniapp/leaderboard`
- 用户登录：`POST /api/miniapp/user/login`
- 用户设置：`PUT /api/miniapp/user/<user_id>/settings`
