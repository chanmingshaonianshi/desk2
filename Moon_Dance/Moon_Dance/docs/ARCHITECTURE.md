# 项目架构说明

本文件聚焦于“模块职责与扩展方式”。运行与使用说明请以 `docs/README.txt` 为准。

## 目录结构
```
Moon_Dance/
├── main.py                 # 模拟器入口（无头模式：--no-gui）
├── main_api.py             # 后端 API 入口（HTTPS + JWT + 幂等上传）
├── certs/                  # HTTPS 证书目录（自动生成）
├── data/                   # 数据落盘目录
├── src/                    # 源代码目录
│   ├── api/                # 后端 API（auth/routes）
│   ├── config/             # 配置层（settings.py）
│   ├── core/               # 核心逻辑层（坐姿分析/数据生成/报表生成等）
│   ├── ui/                 # UI 层
│   └── utils/              # 工具层
└── docs/                   # 文档目录（README.txt 为整合版说明）
```

## 模块职责
1. **config层**：集中管理所有配置项（颜色、尺寸、阈值等），修改配置无需修改业务代码
2. **core层**：包含核心业务逻辑，与UI完全解耦，可独立测试和复用
3. **ui层**：负责所有界面相关逻辑，仅调用core和utils层的接口，不包含业务计算
4. **utils层**：通用工具函数，可被任意层调用
5. **main.py / main_api.py**：分别作为模拟器入口与后端 API 入口

## 扩展方式
- 新增功能：按职责添加到对应层，避免跨层调用
- 修改UI：仅修改ui层代码
- 调整算法：仅修改core层代码
- 修改配置：仅修改config/settings.py
