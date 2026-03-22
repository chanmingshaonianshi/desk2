# Docker 使用说明文档

本文档介绍如何使用 Docker 批量生成“月舞坐垫”的全天压力监测报表。

## 1. 准备工作

在使用 Docker 功能之前，请确保您已经安装了 Docker Desktop。

- **Windows 用户**: 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)。
- 确保 Docker Desktop 正在运行。

## 2. 快速开始 (推荐)

我们提供了一个一键运行脚本，可以自动构建镜像并运行容器。

1.  双击运行项目根目录下的 **`run_docker.bat`** 脚本。
2.  在弹出的窗口中，输入您想要生成的报表数量（例如：`10` 代表生成 10 个人的全天数据）。如果不输入直接回车，默认为 5 份。
3.  等待运行完成。
4.  运行结束后，生成的 Excel 文件会自动保存在项目根目录下的 **`batch_reports`** 文件夹中。

## 3. 手动运行 (高级)

如果您更喜欢使用命令行手动操作，请按照以下步骤进行：

### 第一步：构建镜像

打开终端 (Terminal/PowerShell)，进入项目根目录，运行：

```bash
docker build -t moondance-batch:latest .
```

### 第二步：运行容器

运行以下命令生成报表：

```bash
# Windows (PowerShell)
mkdir batch_reports
docker run --rm -v "${PWD}/batch_reports:/app/output" -e BATCH_COUNT=10 moondance-batch:latest
```

**参数说明**:
- `-v "${PWD}/batch_reports:/app/output"`: 将主机当前目录下的 `batch_reports` 文件夹挂载到容器内的输出目录。
- `-e BATCH_COUNT=10`: 设置环境变量，指定生成 10 份报表。

## 4. 文件说明

- `Dockerfile`: 定义了 Docker 镜像的构建过程，基于 Python 3.9-slim，安装了必要的依赖。
- `docker_entrypoint.py`: 容器启动后执行的 Python 脚本，负责批量生成数据并导出 Excel。
- `run_docker.bat`: Windows 下的一键运行脚本。

## 5. 项目结构说明

项目目录结构与运行方式已整合到纯文本说明中，请以该文件为准：
- `docs/README.txt`

## 6. 注意事项

- 生成的 Excel 文件包含 **今日坐姿评分** 和 **平均偏差率**。
- Docker 模式下运行的是“无头模式” (Headless)，不会显示 GUI 界面，仅用于后台批量处理数据。
