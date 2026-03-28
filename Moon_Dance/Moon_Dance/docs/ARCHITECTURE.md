# Moon_Dance 系统架构设计

## 一、总体业务架构
```mermaid
flowchart LR
    A[客户端层] --> B[接入层]
    B --> C[服务层]
    C --> D[数据层]
    
    subgraph A[客户端层]
        A1[智能坐垫设备]
        A2[桌面端GUI监控]
        A3[移动端小程序]
        A4[管理后台]
    end
    
    subgraph B[接入层]
        B1[Nginx负载均衡]
        B2[HTTPS证书管理]
        B3[流量控制/限流]
    end
    
    subgraph C[服务层]
        C1[API服务集群\n多副本水平扩展]
        C2[JWT鉴权/幂等校验]
        C3[坐姿分析核心引擎]
        C4[Celery异步任务集群]
        C5[报表生成服务]
        C6[自动扩缩容组件]
    end
    
    subgraph D[数据层]
        D1[Redis消息队列/缓存]
        D2[JSON实时日志存储]
        D3[Excel报表存储]
        D4[历史数据归档]
    end
```

---

## 二、部署架构（生产环境）
```mermaid
flowchart TD
    U[用户/设备] --> N[公网入口\n443端口]
    N --> LB[Nginx负载均衡\nSSL卸载]
    
    subgraph 服务集群
        LB --> API1[API副本1]
        LB --> API2[API副本2]
        LB --> API3[API副本N]
        
        API1 --> R[Redis消息队列]
        API2 --> R
        API3 --> R
        
        R --> W1[Celery Worker1\n数据存储/报表生成]
        R --> W2[Celery Worker2\n数据存储/报表生成]
        R --> W3[Celery WorkerN\n数据存储/报表生成]
    end
    
    subgraph 存储层
        W1 --> FS[文件存储\nNAS/对象存储]
        W2 --> FS
        W3 --> FS
        
        FS --> L[实时日志目录]
        FS --> RPT[报表输出目录]
        FS --> ARC[历史数据归档]
    end
    
    subgraph 运维监控
        AS[自动扩缩容组件] -->|监控队列长度| R
        AS -->|动态调整副本数| API1
        AS -->|动态调整副本数| W1
    end
```

---

## 三、核心数据流
```mermaid
sequenceDiagram
    participant 设备
    participant Nginx
    participant API
    participant Redis
    participant Worker
    participant 存储
    
    设备->>Nginx: HTTPS上传坐姿数据
    Nginx->>API: 负载均衡转发
    API->>API: JWT鉴权+幂等校验
    alt 新请求
        API->>Redis: 写入消息队列
        API->>设备: 返回201创建成功
        Worker->>Redis: 消费消息
        Worker->>Worker: 坐姿分析计算评分
        Worker->>存储: 写入实时日志
        Worker->>存储: 定时生成日报表
    else 重复请求
        API->>设备: 返回200已处理
    end
```

---

## 架构设计说明
1. **高可用性**：API和Worker都支持水平扩展，无单点故障，自动扩缩容根据压力动态调整资源
2. **高性能**：异步解耦上传和计算逻辑，峰值流量通过Redis队列削峰填谷
3. **安全性**：全链路HTTPS、JWT鉴权、幂等校验、生产环境密钥强制校验
4. **可扩展性**：分层设计，各模块解耦，新增功能只需要在对应层添加即可
5. **可维护性**：Docker容器化部署，支持一键启停集群，日志统一存储