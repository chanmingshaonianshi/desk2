# Moon Dance Web Admin

这是智能坐垫 Web 管理端的标准 Vue 3 前端工程，使用 Vite、Element Plus 和 ECharts 开发。

页面定位已经调整为面向坐垫售卖方的运营与售后管理后台：首页关注设备活跃率、离线待跟进、异常设备和地区设备使用情况；健康评分、压力曲线等细节数据放在数据分析页，用于售后复盘和产品体验分析。

## 本地开发

```bash
npm install
npm run dev
```

开发服务器会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 构建部署

```bash
npm run build
```

构建产物输出到 `../web_admin`，由 Flask 的 `/admin/` 路由托管。

当前仓库中的 `../web_admin` 目录已经提供一份可直接部署的 Vue + Element Plus 静态页面，便于服务器在未安装 Node.js 的情况下继续通过 `/admin/` 访问。
