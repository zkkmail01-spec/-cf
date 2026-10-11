# CloudBase Document Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 保留当前 FastAPI API 与小程序界面，增加可切换的 CloudBase 文档数据库生产后端。

**Architecture:** 以 `DocumentStore` 协议隔离服务层，提供内存实现用于测试和 CloudBase Admin API 实现用于生产；现有 SQLAlchemy 路径保留为回退实现。CloudBase 客户端使用官方 Node SDK 同源的 Admin API 请求、EJSON 和 TC3 签名。

**Tech Stack:** Python 3.12、FastAPI、httpx、CloudBase Admin API、TC3-HMAC-SHA256、pytest。

**Spec:** `docs/superpowers/specs/2026-10-11-cloudbase-document-db-design.md`

## Global Constraints

- 小程序接口路径和响应结构保持不变。
- SecretId/SecretKey 只通过云托管密钥注入。
- `STORAGE_BACKEND=sql` 保留现有 PostgreSQL/SQLite 路径；`cloudbase` 才启用新仓储。
- 所有 CloudBase 写请求必须有版本冲突保护或幂等键。

## Review Focus

- TC3 签名的 canonical request、JSON body 哈希和时钟偏差。
- CloudBase 返回的 EJSON 日期、数字和 `_id` 类型转换。
- 家庭范围过滤不能被请求参数中的 familyId 绕过。
- 幂等键重复和版本冲突不能产生重复点菜或半成功响应。
- CloudBase 不可用时 API 必须返回明确错误，不能静默回退到内存数据。

### Task 1: 配置与 CloudBase Admin 客户端

**Files:**
- Modify: `backend/app/core/config.py`, `backend/pyproject.toml`
- Create: `backend/app/storage/cloudbase_client.py`
- Test: `backend/tests/test_cloudbase_client.py`

- [ ] Write failing tests for configuration validation and TC3 request construction.
- [ ] Run the focused tests and observe the expected failure.
- [ ] Implement `CloudBaseConfig` and `CloudBaseAdminClient.request(action, payload)` with injectable transport.
- [ ] Add EJSON encode/decode for the values used by this project.
- [ ] Run focused tests and the full backend suite.
- [ ] Commit Task 1.

### Task 2: DocumentStore protocol and in-memory implementation

**Files:**
- Create: `backend/app/storage/protocol.py`, `backend/app/storage/memory.py`
- Test: `backend/tests/test_document_store.py`

- [ ] Define typed collection operations and optimistic version errors.
- [ ] Write failing tests for family-scoped CRUD, atomic update and conflict detection.
- [ ] Implement the memory store.
- [ ] Run focused and full backend tests.
- [ ] Commit Task 2.

### Task 3: CloudBase document repository

**Files:**
- Create: `backend/app/storage/cloudbase_store.py`
- Test: `backend/tests/test_cloudbase_store.py`

- [ ] Write failing repository contract tests against a fake CloudBase client.
- [ ] Implement collection mapping, query filters, versioned updates and idempotency records.
- [ ] Run repository tests and full backend suite.
- [ ] Commit Task 3.

### Task 4: Service adapter and backend switch

**Files:**
- Modify: `backend/app/api/deps.py`, `backend/app/db/session.py`, `backend/app/services/*.py`, `backend/app/main.py`
- Test: `backend/tests/test_storage_backend_switch.py` and existing API tests.

- [ ] Add dependency selection from `STORAGE_BACKEND` without changing route contracts.
- [ ] Port family, catalog, meal, shopping and invitation service operations to the protocol.
- [ ] Keep SQL implementation available for local regression tests.
- [ ] Run SQL and memory/document API suites.
- [ ] Commit Task 4.

### Task 5: Deployment, seed and migration documentation

**Files:**
- Modify: `backend/scripts/seed_demo.py`, `backend/Dockerfile`, `docs/deployment/cloudbase.md`, `backend/.env.example`
- Test: `backend/tests/test_cloudbase_deployment.py`

- [ ] Document required environment variables and CloudBase collection bootstrap.
- [ ] Add document seed mode with idempotent behavior.
- [ ] Verify Docker configuration and run all tests.
- [ ] Commit Task 5.
