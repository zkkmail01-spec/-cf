# 微信云开发云托管部署手册

本项目由原生微信小程序、FastAPI 云托管服务、PostgreSQL 和云存储组成。小程序不需要、也不应保存 AppSecret。

## 1. 准备资源

1. 在微信公众平台创建小程序，获取 AppID。
2. 在微信开发者工具中开通云开发，记录云环境 ID。
3. 在同一云环境开通云托管，创建一个服务，例如 `family-menu-api`。
4. 创建 PostgreSQL 数据库，仅通过云托管秘密或环境变量传入连接串。
5. 在云存储中配置小程序用户可上传菜品图片；服务端只保存 `fileID`。

## 2. 填写小程序配置

1. 将根目录 `project.config.json` 中的 `appid` 替换为真实 AppID。
2. 编辑 `miniprogram/config/env.js`：
   - `CLOUDBASE_ENV_ID` 填云环境 ID。
   - `CLOUDRUN_SERVICE_NAME` 填云托管服务名。
3. 不要在小程序源码、`project.config.json` 或分享链接中写入 AppSecret、数据库密码或自行伪造的 `openid`。

身份头只能来自可信云托管入口。生产服务必须禁止公网直连容器端口，仅允许同一云环境的 `callContainer`/云托管网关到达，并在发布后用直连 URL 验证无法携带自行伪造的 `x-wx-openid` 访问。如必须开放公网 API，必须在网关层增加可验证的身份凭证，不能直接信任请求头。

小程序通过 `wx.cloud.callContainer` 调用 `/api/v1`，并在 `X-WX-SERVICE` 头中指定服务名。云托管会注入可信的微信身份头。

## 3. 构建和部署 FastAPI

云托管构建上下文选择 `backend`，Dockerfile 路径为 `backend/Dockerfile`。容器监听 80 端口，健康检查为 `GET /health`。

在云托管中配置：

| 变量 | 值 |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | 从云托管秘密注入的 `postgresql+asyncpg://...` |
| `ALLOW_MOCK_IDENTITY` | `false` |
| `API_PREFIX` | `/api/v1` |

生产环境不接受本地模拟身份。不要在镜像、构建参数或代码库中固化数据库密码。

## 4. 执行数据库迁移

迁移是显式发布步骤，不放在每个 Web 实例的启动命令中，避免多实例同时迁移。使用与生产服务相同的环境变量运行：

```sh
cd backend
alembic -c alembic.ini upgrade head
```

迁移成功后再扩容或切换 Web 服务流量。

## 5. 本地联调

Docker Compose 仅供本机联调，API 只绑定 `127.0.0.1:8000`，PostgreSQL 使用隔离的 Compose 网络且不暴露数据库端口。启动后手动迁移：

```sh
docker compose up -d db
docker compose run --rm api alembic -c alembic.ini upgrade head
docker compose up -d api
```

健康检查：`http://127.0.0.1:8000/health`。

如需本地非微信身份联调，只能在 `APP_ENV=local` 时显式设置 `ALLOW_MOCK_IDENTITY=true`。不得将该开关用于云托管。

## 6. 演示数据

首先完成迁移，再在 `backend` 目录运行：

```sh
python -m scripts.seed_demo
```

脚本会创建一个厨师长、一个成员、4 个分类和 6 道菜，重复运行不会重复插入。演示身份只用于本地体验。

## 7. 发布前验收

1. 用厨师长身份创建家庭、分类、菜品和食材，并上传一张菜品图片。
2. 生成邀请，用另一个微信体验成员打开分享卡并加入。
3. 两个成员为同一日午餐点同一道菜，确认只有一个菜品且显示两位点菜人。
4. 分别检查首页、菜谱、记录、采购和我的，并验证早、中、晚三餐切换。
5. 在常见 iPhone 和 Android 模拟窗口下检查安全区、字体缩放和主按钮的 `88rpx` 最小高度。
6. 验证断网后点菜草稿保留，恢复网络后可重试且不会重复点菜。
7. 使用第二个家庭验证无法读取第一个家庭的菜品、记录和采购清单。

当前代码仓使用占位 AppID、云环境 ID 和服务名，因此真实微信联网、分享卡、云存储和手机尺寸验收需在填入用户资源后于微信开发者工具中手动执行。
