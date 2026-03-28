# Moon_Dance 项目文档索引
本文档说明 docs 目录下所有文档的用途和内容概览。

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
| **ARCHITECTURE.md** | 系统架构设计 | 开发/架构师 | 四层分层架构说明、Mermaid架构图、部署架构、数据流 |
| **API.md** | API接口参考 | 开发/客户端对接人员 | 所有接口的参数说明、请求示例、响应示例、错误码 |
| **API.html** | 可视化API文档 | 开发/测试 | 美观的HTML格式API文档，可直接在浏览器打开查看 |
| **API_OPERATION.md** | API运维指南 | 运维/测试 | API测试步骤、日志体系说明、常见问题排查指南 |
| **MQ_ARCHITECTURE.md** | MQ架构设计 | 开发/架构师 | 消息队列架构规范、消息格式定义、重传机制、模块职责划分 |
| **MQ_TEST_GUIDE.md** | MQ测试操作指南 | 测试/运维 | MQ服务启动、测试流程、功能验证、重传测试步骤 |
| **README_DOCKER.md** | Docker部署文档 | 运维 | Docker镜像构建、容器部署、集群启动命令 |

---

## 文档阅读路径建议

### 👉 新用户入门
1. 先看 **README.txt** 了解项目基本功能和快速启动方法
2. 再看 **ARCHITECTURE.md** 理解整体架构设计

### 👉 客户端对接开发
1. 查阅 **API.md** 或 **API.html** 了解接口规范
2. 参考 **API_OPERATION.md** 进行接口测试和调试

### 👉 MQ分布式架构开发/运维
1. 先看 **MQ_ARCHITECTURE.md** 理解MQ架构设计
2. 按照 **MQ_TEST_GUIDE.md** 进行部署测试
3. 结合 **API_OPERATION.md** 进行日常运维

### 👉 生产环境部署
1. 参考 **README_DOCKER.md** 进行容器化部署
2. 结合 **API_OPERATION.md** 进行生产环境配置
