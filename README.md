# 江西物流一张网 · 可运行演示平台

前端：原生JavaScript + 响应式CSS。后端：FastAPI。数据库：SQLite。浏览器通过后端API加载、创建和流转业务，不是纯静态页面。

## 启动

Python 3.12环境：

```
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

管理账号 `admin`，企业账号 `enterprise`，初始演示密码均为 `Demo@2026!`。部署前设置 `DEMO_ADMIN_PASSWORD` 和 `DEMO_ENTERPRISE_PASSWORD` 可替换初始账号密码。密码只在数据库首次初始化时读取，已有数据库需另行执行受控重置。

## Render部署

将目录内容推送到GitHub仓库，在Render新建Blueprint，选择仓库中的render.yaml。或创建Python Web Service，build命令为 `pip install -r requirements.txt`，start命令为 `uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers`，健康检查 `/health`。

默认free计划不含持久盘，重启或重部署可能丢失新业务数据并恢复演示种子。保留业务数据需选择支持磁盘的付费实例并挂载 `/var/data`，设置 `DATA_DIR=/var/data`。本项目没有自行开通付费资源。后续多实例生产环境应迁移PostgreSQL。

高德地图：在Render环境设置 `AMAP_WEB_KEY`（Web端JS API Key）、`AMAP_SECURITY_CODE`（安全密钥），控制台配置实际onrender.com域名白名单。JS Key为浏览器可见凭证；不得使用服务端Web服务密钥代替。无Key时明确展示模拟网络示意图。

## 业务范围

包含管理/企业登录、隔离数据、运行看板、需求发布、参考报价、资源登记审核、联运估算、运单分段事件、模拟单据打印及PDF另存、政策演示自测、预警状态流转、接口模拟监控、工单处理、CSV导出、审计及53项PRD能力索引。

全部数据、政策、轨迹、价格、时效和单据为模拟。运输求解为演示成本估算，不是完整路网优化器。接口监控使用种子数据，没有实际连接政府、铁路、港口或企业生产系统。53项目录是需求索引，非全部已实现的生产功能。

公开部署的演示站请勿上传真实个人信息或商业数据。当前账号为展示用途，不具备生产账号管理、密码找回、第三方认证、精细字段授权、审计防篡改等完整生产保障。投产须单独实施对应PRD并完成安全与业务验收。

## API

`/docs`提供OpenAPI。核心接口：`/api/login`、`/api/me`、`/api/data/{kind}`、`/api/quotes`、`/api/plans`、`/api/export/{kind}`、`/api/audit`。Cookie使用HttpOnly、SameSite=Strict，HTTPS请求设置Secure；密码PBKDF2散列；状态变更校验版本和业务状态，操作留审计记录。
