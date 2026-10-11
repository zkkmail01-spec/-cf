# 微信云开发云托管部署手册

本项目由原生微信小程序、FastAPI 云托管服务、CloudBase 文档数据库和云存储组成。小程序不需要、也不应保存 AppSecret。

## 1. 准备资源

1. 在微信公众平台创建小程序，获取 AppID。
2. 在微信开发者工具中开通云开发，记录云环境 ID。
3. 在同一云环境开通云托管，创建一个服务，例如 `family-menu-api`。
4. 在 CloudBase 文档数据库中创建 `families`、`categories`、`dishes`、`invitations`、`meal_orders`、`shopping_checks`、`idempotency_records` 集合。
5. 在云存储中配置小程序用户可上传菜品图片；服务端只保存 `fileID`。

## 2. 填写小程序配置

1. 将根目录 `project.config.json` 中的 `appid` 替换为真实 AppID。
2. 编辑 `miniprogram/config/env.js`：填入云环境 ID 和云托管服务名。
3. 不要在小程序源码、`project.config.json` 或分享链接中写入 AppSecret、SecretId、SecretKey、数据库密码或自行伪造的 `openid`。

身份头只能来自可信云托管入口。生产服务必须禁止公网直连容器端口，仅允许同一云环境的 `callContainer`/云托管网关到达。不能直接信任请求头；如必须开放公网 API，必须在网关层增加可验证的身份凭证。

## 3. 构建和部署 FastAPI

云托管构建上下文选择 `backend`，Dockerfile 路径为 `Dockerfile`。容器以普通用户监听 8000 端口，CloudBase 服务端口也填写 8000，健康检查为 `GET /health`。

云托管环境变量：

| 变量 | 值 |
|---|---|
| `APP_ENV` | `production` |
| `STORAGE_BACKEND` | `cloudbase` |
| `CLOUDBASE_ENV_ID` | `zkk-20261010-d6gfxxdhfe3f8fc75` |
| `CLOUDBASE_REGION` | `ap-shanghai` |
| `TENCENTCLOUD_SECRETID` | 从云托管密钥注入 |
| `TENCENTCLOUD_SECRETKEY` | 从云托管密钥注入 |
| `ALLOW_MOCK_IDENTITY` | `false` |
| `API_PREFIX` | `/api/v1` |

SecretId 和 SecretKey 只能由云托管密钥注入，不能提交到代码仓库、Docker 镜像或小程序代码中。CloudBase 请求失败时直接返回错误，不会静默切换到内存数据；`STORAGE_BACKEND=sql` 仍可用于本地 SQLite/PostgreSQL 回退。

## 4. 本地联调

Docker Compose 仅供本机联调，API 只绑定 `127.0.0.1:8000`。启动后手动迁移：

```sh
docker compose up -d db
docker compose run --rm api alembic -c alembic.ini upgrade head
docker compose up -d api
```

健康检查：`http://127.0.0.1:8000/health`。当前 CloudBase 客户端测试使用 fake transport 验证签名和请求结构，不代表已经使用真实密钥访问云端。

## 5. 演示数据

SQL 回退模式下，在 `backend` 目录运行 `python -m scripts.seed_demo`。脚本重复运行不会重复插入。CloudBase 生产环境应使用受控的文档种子脚本，并为每次写入设置幂等键。

## 6. 发布前验收

1. 用厨师长身份创建家庭、分类、菜品和食材，并上传一张菜品图片。
2. 生成邀请，用另一个微信体验成员打开分享卡并加入。
3. 两个成员为同一日午餐点同一道菜，确认只有一个菜品且显示两位点菜人。
4. 分别检查首页、菜谱、记录、采购和我的，并验证早、中、晚三餐切换。
5. 验证第二个家庭无法读取第一个家庭的菜品、记录和采购清单。

真实微信联网、分享卡、云存储和手机尺寸验收需在微信开发者工具中执行；本地自动化测试不替代真实云端验收。
