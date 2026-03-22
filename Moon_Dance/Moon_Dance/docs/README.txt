Moon_Dance 项目说明（整合版）

1) 项目概览
Moon_Dance 是一个 Python 模拟器项目，包含：
- 模拟器主程序（可无头运行）
- 报表导出（Excel）
- Docker 批量运行（生成多份报表）
- 后端 API（HTTPS + JWT + 幂等上传）


2) 目录结构（核心）
Moon_Dance/
  main.py
    模拟器主入口（无头模式：python main.py --no-gui）
  main_api.py
    后端 API 独立入口（HTTPS + JWT + 幂等上传）
  certs/
    HTTPS 证书目录（自动生成）
    ca.crt          本地 CA 根证书（导入信任后浏览器不再告警）
    ca.key          本地 CA 私钥
    server.crt      服务端证书
    server.key      服务端私钥
  data/
    realtime_logs/
      processed_ids.json
        幂等性去重（已处理 request_id 列表）
    reports/
      uploads/
        上传触发的示例报表输出目录
  src/
    api/
      auth.py
        /login（JWT 签发）与鉴权装饰器
      routes.py
        /api/v1/upload（带幂等校验）
    config/
      settings.py
        配置常量（含 API 配置、证书文件名、落盘路径等）
    core/
      posture_analyzer.py 等核心业务逻辑
    ui/
      图形界面相关（若使用 GUI）
    utils/
      通用工具（Excel 导出、JSON 日志等）
  docs/
    README.txt（本文件）
    README_DOCKER.md（Docker 使用说明，细节参考本文件或该文件）
    ARCHITECTURE.md（架构说明，细节参考本文件或该文件）


3) 本地运行（模拟器）
进入项目目录后运行：
- 无头模式（推荐用于服务器/容器）：
  python main.py --no-gui


4) Docker 批量运行（生成报表）
构建镜像：
  docker build -t moondance-batch:latest .

运行容器（示例）：
  mkdir batch_reports
  docker run --rm -v "${PWD}/batch_reports:/app/output" -e BATCH_COUNT=10 moondance-batch:latest

说明：
- batch_reports 为主机侧输出目录
- BATCH_COUNT 指定生成报表份数


5) 后端 API（HTTPS + JWT + 幂等上传）
5.1 启动 API 服务
在项目目录运行：
  python main_api.py

健康检查：
  https://127.0.0.1:443/health

5.2 生成证书（仅生成不启动服务）
  python main_api.py --gen-certs-only

5.3 Windows 导入 CA 证书（消除浏览器不安全告警）
以“当前用户”方式导入（无需管理员）：
  certutil -user -addstore -f ROOT "B:\python\Moon_Dance\Moon_Dance\certs\ca.crt"

注意：
- 导入后请完全退出并重启浏览器
- 若通过局域网 IP 访问（例如 https://10.243.152.164:443），建议生成证书时指定 CN：
  python main_api.py --gen-certs-only --cn 10.243.152.164

5.4 登录获取 Token
POST /login
Body(JSON):
  {
    "app_id": "...",
    "app_secret": "..."
  }
返回：
- token（Bearer）
- expires_in

5.5 上传接口（带幂等校验）
POST /api/v1/upload
Header:
  Authorization: Bearer <Token>
Body(JSON) 必须包含：
- request_id: UUID 字符串

幂等逻辑：
- 服务端会在 data/realtime_logs/processed_ids.json 中检查 request_id
- 已处理：返回 200（数据已处理），不重复写入
- 新请求：处理并落盘，返回 201


6) 常见问题
6.1 “找不到 main_api.py”
请确认你的当前目录是：
  B:\python\Moon_Dance\Moon_Dance
而不是：
  B:\python\Moon_Dance

6.2 “certutil 拒绝访问”
你在写入“本地计算机”根证书库时需要管理员权限。
推荐使用当前用户证书库（无需管理员）：
  certutil -user -addstore -f ROOT "...\certs\ca.crt"

