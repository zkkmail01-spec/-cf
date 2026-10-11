# CloudBase 文档数据库改造规格

## 目标

保留现有 Python FastAPI 接口和微信小程序 UI，将生产存储从 PostgreSQL 切换为 CloudBase 文档数据库；本地测试继续使用内存文档仓储，不依赖真实云资源。

## 约束

- 小程序接口路径和响应结构保持不变。
- 身份仍由可信 CloudBase 云托管入口注入的 `x-wx-openid` 提供；SecretId/SecretKey 只能配置在云托管密钥中。
- 文档数据库集合按业务域拆分，不把所有家庭数据塞进单个超大文档。
- 所有写操作必须通过仓储层，服务层不能直接依赖 SQLAlchemy Session。
- CloudBase 请求使用官方 Admin API 的 TC3-HMAC-SHA256 签名。
- PostgreSQL 代码先保留，使用 `STORAGE_BACKEND=sql` 回退；`STORAGE_BACKEND=cloudbase` 才启用文档仓储。

## 集合设计

- `families`: 家庭资料和成员状态；openid 唯一由服务层检查。
- `categories`: 家庭分类。
- `dishes`: 菜品和内嵌食材快照。
- `invitations`: 邀请码哈希和使用状态。
- `meal_orders`: 日期+餐次的点菜及点菜人数组。
- `shopping_checks`: 家庭采购勾选状态。
- `idempotency_records`: 家庭、openid、幂等键和响应快照。

## 一致性策略

CloudBase 文档数据库使用单文档更新和版本字段实现乐观并发控制；冲突返回业务错误并由 API 层重试有限次数。所有幂等记录在业务写成功后同一仓储操作中保存，重复请求返回原响应。
