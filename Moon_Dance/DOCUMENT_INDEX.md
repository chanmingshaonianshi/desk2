# Moon_Dance 项目文档索引
本文档只做文档导航。整体架构统一以 `docs/ARCHITECTURE.md` 为准，其余文档分别承担接口、MQ 细节、测试和部署说明，避免重复描述同一套内容。

---

## 🚀 当前文档使用原则

1. **整体架构只看一处**：前端、后端、API、MQ、部署关系统一看 `docs/ARCHITECTURE.md`，当前是“API 主链路 + Redis Stream 扩展链路”双链路架构
2. **接口定义单独维护**：请求参数、返回结构、错误码只看 `docs/API.md`，当前上传链路同时支持 JWT 接口和 API Key 接口
3. **队列细节单独维护**：Celery/Redis 与 Redis Stream 的边界只看 `docs/MQ_ARCHITECTURE.md`，其中 validator / writer / logger 支持独立启停
4. **测试与部署分离**：操作步骤分别在 `docs/MQ_TEST_GUIDE.md` 和 `docs/README_DOCKER.md`

---

## 文档目录结构
```
docs/
├── README.txt                  # 项目快速入门说明
├── ARCHITECTURE.md             # 系统架构设计文档（含架构图）
├── API.md                      # API接口参考文档
├── API.html                    # HTML可视化版API文档
├── API_OPERATION.md            # API运维文档（测试、日志、排查）
├── MQ_ARCHITECTURE.md          # MQ分布式架构设计规范
├── MQ_TEST_GUIDE.md            # MQ架构测试操作指南
└── README_DOCKER.md            # Docker部署说明
```

---

## 文档详细说明

| 文档名称 | 用途 | 适用人群 | 核心内容 |
|---------|------|----------|----------|
| **README.txt** | 项目快速入门 | 所有用户 | 项目概览、快速启动命令、基本功能介绍 |
| **ARCHITECTURE.md** | 系统架构设计 | 开发/架构师 | 项目唯一整体架构说明，梳理前端、后端、API、MQ、部署与文件输出关系 |
| **API.md** | API接口参考 | 开发/客户端对接人员 | 所有接口的参数说明、请求示例、响应示例、错误码 |
| **API.html** | 可视化API文档 | 开发/测试 | 美观的HTML格式API文档，可直接在浏览器打开查看 |
| **API_OPERATION.md** | API运维指南 | 运维/测试 | API测试步骤、日志体系说明、常见问题排查指南 |
| **MQ_ARCHITECTURE.md** | MQ架构设计 | 开发/架构师 | 仅说明两套异步链路的边界、消息格式、重传机制和 Worker 分工 |
| **MQ_TEST_GUIDE.md** | MQ测试操作指南 | 测试/运维 | 区分 Celery 主链路与 Redis Stream 扩展链路的测试步骤 |
| **README_DOCKER.md** | Docker部署文档 | 运维 | Docker镜像构建、容器部署、集群启动命令 |

---

## 文档阅读路径建议

### 👉 新用户入门
1. 先看 **README.txt** 了解项目基本功能和启动方式
2. 再看 **ARCHITECTURE.md** 理解完整系统结构

### 👉 客户端对接开发
1. 查阅 **API.md** 或 **API.html** 了解接口规范
2. 参考 **API_OPERATION.md** 进行接口测试和调试
3. 当前推荐关注两条接入路径：`/api/v1/upload` 使用 Bearer Token，`/api/v2/ingest` 使用 `X-API-Key`

### 👉 MQ分布式架构开发/运维
1. 先看 **ARCHITECTURE.md** 确认当前主链路与扩展链路
2. 再看 **MQ_ARCHITECTURE.md** 理解队列边界
3. 按照 **MQ_TEST_GUIDE.md** 进行测试

### 👉 生产环境部署
1. 先看 **ARCHITECTURE.md** 了解部署关系
2. 再看 **README_DOCKER.md** 进行容器化部署
3. 结合 **API_OPERATION.md** 做运行排查

---

## 当前框架速记

- **服务端入口**：`Moon_Dance/main_api.py` 负责创建 Flask App、注册蓝图、写入请求日志
- **鉴权层**：`Moon_Dance/src/api/auth.py` 负责登录签发 JWT，并校验 Bearer Token 与 `X-API-Key`
- **数据接收层**：`Moon_Dance/src/api/routes.py` 负责 `/api/v1/upload` 与 `/api/v2/ingest` 的入库、幂等和异步投递
- **主异步链路**：`Moon_Dance/src/core/worker.py` 通过 Celery + Redis 处理 API 上传后的异步任务
- **扩展 MQ 链路**：`Moon_Dance/src/core/mq_client.py` 与 `Moon_Dance/src/mq_workers/*` 负责 Redis Stream 消息发送、验证、写入、日志统计
- **模块管理入口**：`Moon_Dance/scripts/mq_manager.py` 支持 validator / writer / logger 的独立启动、停止、状态查看和多副本运行
- **扩缩容入口**：`Moon_Dance/scripts/auto_scaler.py` 与 `Moon_Dance/scripts/ops/scaler.py` 负责 Celery worker 的自动扩缩容
- **客户端入口**：`Moon_Dance/simulator_client.py` 负责启动本地无头模拟，实际上传逻辑在 `Moon_Dance/src/core/device_simulator.py`
- **部署入口**：`Moon_Dance/deploy/docker-compose.yml` 负责向 `api` 容器注入 `API_KEY`
