# 阶段 0 数据包

本文档记录 Phase 0 数据包及其历史基线。当前项目已完成 Phase 5；当前前端能力、运行方式和完整验证命令见 `frontend/README.md`。

目录结构：
- `backend/data/orders.json`：两笔订单及商品行项目。
- `backend/data/skus_raw.json`：查询结果原始字段，保留源数据中的空白和异常值。
- `backend/data/skus.json`：字段标准化后的商品数据。
- `backend/data/tracking.json`：物流分组与追踪编号映射。
- `DATA_QUALITY_REPORT.md`：数据来源、清洗规则和待处理问题。

注意：
1. Phase 0 当时尚未创建业务代码；该陈述仅描述历史阶段，不代表当前项目状态。
2. `HALGEO15` 的描述疑似截断，后续需重新查询。
3. 公开 GitHub 前，应检查并脱敏客户联系方式。
4. 不要将真实 API 凭证写入 JSON、代码或 Git。

## 当前 Phase 5 状态

当前系统采用 React 19、TypeScript 7、Vite 8 和 Oxlint 前端，以及 Python 3.13、FastAPI、Pydantic 2 和 Python `Decimal` 后端。现有 Phase 5 前端通过只读 API 提供订单列表与搜索、订单状态筛选、订单详情、客户和地址及商品信息、AUD Money 字符串展示、Shipping Quote 状态、Loading/Empty/Error/Retry 状态，以及响应式和键盘可访问界面。

系统当前不提供订单写入、真实承运商物流轨迹或真实承运商报价。Tracking Group ID 只是内部订单关联标识，不是承运商轨迹。

本地开发的核心命令为：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
npm.cmd run dev --prefix frontend
```

前端测试与构建使用 `npm.cmd run test --prefix frontend`、`npm.cmd run typecheck:test --prefix frontend`、`npm.cmd run build --prefix frontend` 和 `npm.cmd run lint --prefix frontend`。后端回归使用 `.\.venv\Scripts\python.exe -m pytest -v`、`.\.venv\Scripts\ruff.exe check backend`、`.\.venv\Scripts\ruff.exe format --check backend` 和 `.\.venv\Scripts\python.exe -m pip check`。完整命令和 API 地址说明以 `frontend/README.md` 为准。

## Shipping Quote 限制（D-015）

Phase 5 尚未实现 Shipping Quote Integration。当前 API 固定返回：

- `status = "unsupported"`
- `reason_code = "SHIPPING_QUOTE_NOT_IMPLEMENTED"`
- `quoted_fee = null`
- `applied_fee = {"amount":"0.00","currency":"AUD"}`
- `checked_at` 为运行时 UTC aware datetime，只表示系统执行本次检查的时间

`applied_fee = AUD 0.00` 是当前定价流程使用的确定性降级金额，不代表承运商提供了零运费报价，也不代表运输免费。`quoted_fee = null` 明确表示当前没有真实承运商报价。

`unsupported` 表示集成尚未实现；`unavailable` 表示能力已经实现、但本次请求未能获得有效结果。两者不得混用。真实 Shipping Quote Integration 属于 Phase 6。
