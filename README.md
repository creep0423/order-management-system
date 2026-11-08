# 订单管理系统（Order Management System）

一个只读的企业级订单管理示例应用：后端用 FastAPI 读取并校验本地 JSON 数据，按冻结的 `Decimal` 规则计算金额，通过版本化 API 提供给 React 前端展示。本项目按 `IT Coding Assessment` 的要求交付：**订单详情、商品与金额拆分、物流追踪状态、运费降级说明**四项核心能力完整可运行，不包含订单写入、真实承运商调用或真实运费报价。

> 说明：本文档为项目主 README（中文）。历史数据包说明见 `README_PHASE0.md`，前端子目录补充说明见 `frontend/README.md`；`docs/` 下记录架构、决策与 Phase 6 契约。

---

## 1. 功能范围

### 1.1 已实现（本次交付验收范围）

| 能力 | 说明 |
|---|---|
| 订单列表 | `GET /api/v1/orders`，显示订单号、订单日期、公司、状态、商品行数、件数、金额；支持按订单号/公司搜索、按状态筛选、清空筛选 |
| 订单详情 | `GET /api/v1/orders/{order_number}`，展示订单基本信息、客户、收货地址、商品明细、金额汇总、物流分组状态、包装估算状态 |
| 商品信息 | 商品名称、SKU、描述（缺失时明确显示不可用）、规格、ETA（无值时明确显示不可用）、中性图片占位符 |
| 金额拆分 | RRP（含 GST）、未税单价、行小计、订单小计、GST、运费、订单总额，全部为 AUD 两位小数字符串 |
| 多订单独立处理 | 每笔订单独立读取、独立计价，不共享或合并金额状态 |
| 物流状态 | 每个唯一物流分组一个结果；无已批准映射时如实返回 `unavailable`，不伪造承运商、事件或 ETA |
| 运费降级 | 运费能力未实现期间固定 `unsupported`，`quoted_fee=null`、`applied_fee=A$0.00`，并在界面与本文档说明其含义 |
| 界面状态 | 加载、空数据、搜索无结果、订单不存在、后端不可用、API 错误与重试均独立处理 |

### 1.2 明确未实现（不伪造）

- 真实承运商物流查询（无凭证、无映射、无 testbed 授权）。
- 真实运费报价（Shipping Quote Integration 未实现，保持 `unsupported`）。
- 生产级包装规则/装箱算法（Batch J2 已暂停；当前无任何真实包装规格与材料数据）。
- 订单创建、修改、删除、分页与认证。

---

## 2. 技术栈与架构

| 层 | 技术 |
|---|---|
| Backend | Python 3.13、FastAPI、Pydantic 2、`Decimal`、pytest、Ruff |
| Frontend | React 19、TypeScript 7（strict）、Vite 8、Vitest + Testing Library、Oxlint |
| Data | 只读 JSON 文件（`backend/data/`），无数据库、无 Redis、无消息队列 |

采用 **模块化单体（Modular Monolith）**，单进程部署，依赖方向为 `API -> Service -> Repository / Integration`：

```text
order-management-system/
├── README.md                  # 本文档
├── AGENTS.md                  # 项目协作规范与冻结业务规则
├── pyproject.toml             # 后端依赖与 pytest/ruff 配置
├── backend/
│   ├── main.py                # FastAPI 应用入口（lifespan 初始化数据边界）
│   ├── api/                   # 路由、Schema、Mapper、错误映射、依赖注入
│   ├── models/                # 不可变领域模型（订单、商品、Package、Tracking）
│   ├── repositories/          # 只读 JSON Repository 与引用完整性校验
│   ├── services/              # 订单编排、Decimal 计价、Tracking、Package 估算
│   ├── integrations/          # 承运商 Adapter、限流器、环境变量凭证读取
│   ├── data/                  # 业务 JSON（本地数据，不提交版本库）
│   └── tests/                 # 401 后端测试（含真实数据验收测试）
├── frontend/
│   ├── src/                   # React 页面、组件、类型、运行时校验、API 客户端
│   └── tests/                 # Vitest 测试（81）
├── docs/                      # 架构、决策 D-001～D-035、Phase 6 契约与计划
├── DATA_QUALITY_REPORT.md     # 数据来源与已知质量问题
└── README_PHASE0.md           # Phase 0 数据包历史说明
```

关键设计：

- **Repository 只读**：加载时校验 JSON 可解析性、必填字段、SKU 唯一性、订单 SKU 引用与物流分组引用；不修改数据文件。
- **Domain 与 API 分离**：领域模型不直接作为 HTTP 响应，Mapper 负责投影。
- **金额唯一权威**：金额只在后端计算，前端只展示 API 返回的字符串，不做任何重新计算。
- **能力隔离**：物流、运费、包装估算三者互不影响；任一失败只降级自身区域。

---

## 3. 环境依赖

- Python **3.13.x**（`pyproject.toml` 约束 `>=3.13,<3.14`）
- Node.js **24.x** 与 npm **11.x**（当前验证环境：Node 24.19.0 / npm 11.17.0）
- 操作系统：Windows PowerShell 示例命令（其他平台把 `.\\.venv\\Scripts\\` 换成 `.venv/bin/` 即可）

### 3.1 安装步骤

仓库根目录已包含虚拟环境 `.venv`；如需重建：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm.cmd install --prefix frontend
```

---

## 4. 前后端启动方法

打开两个终端，均在**仓库根目录**执行：

```powershell
# 终端 1：后端（默认 http://127.0.0.1:8000）
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload

# 终端 2：前端（默认 http://localhost:5173）
npm.cmd run dev --prefix frontend
```

- 浏览器打开 `http://localhost:5173`。
- 后端默认监听 `127.0.0.1:8000`；前端默认请求该地址。
- 如需其他后端地址，可设置前端环境变量 `VITE_API_BASE_URL`（例如 `http://127.0.0.1:8000`），**该变量只能包含 API 地址，不能包含凭证**。
- 后端 CORS 仅允许 `http://localhost:5173` 与 `http://127.0.0.1:5173` 两个来源。
- API 文档：`http://127.0.0.1:8000/docs`（OpenAPI）。

### 4.1 生产构建（前端）

```powershell
npm.cmd run build --prefix frontend   # tsc -b + vite build，产物在 frontend/dist
```

---

## 5. 数据格式

所有业务数据位于 `backend/data/`，为**只读**本地文件；`skus_raw.json` 只用于溯源，不参与运行时读取。

### 5.1 `orders.json`

```json
{
  "schema_version": "1.0",
  "currency": "AUD",
  "orders": [
    {
      "order_no": "PO-XXXXXXXX-XXXXX",
      "order_date": "YYYY-MM-DD",
      "status": "COMPLETED",
      "company": "<公司名称>",
      "customer": { "name": "<姓名>", "phone": "<电话>", "email": "<邮箱>" },
      "shipping_address": {
        "line1": "<地址行>", "suburb": "<区>", "state": "<州>",
        "postcode": "<邮编>", "country": "Australia"
      },
      "items": [
        { "sku": "<SKU>", "quantity": 3, "tracking_group_id": "TRACK_1" }
      ]
    }
  ]
}
```

### 5.2 `skus.json`（标准化商品数据）

`products[]` 每条记录的关键字段：

| 字段 | 说明 |
|---|---|
| `sku` | 商品唯一标识，与订单行 `sku` 关联 |
| `product_name` | 商品名称 |
| `description` / `description_status` | 描述与状态：`available`、`missing`、`partial_needs_requery` |
| `rrp_aud_incl_gst` | RRP（**含 GST**），十进制字符串 |
| `size`、`barcode`、`spu` | 规格、条码、SPU |
| `eta_days` / `eta_raw` | 预计到货天数与原始文本（`0Days`、`nullDays` 等按原值保留） |
| `weight_g`、`dimensions_mm`、`volume_mm3` 等 | **商品**物理数据（不是包装数据） |

### 5.3 `tracking.json`（物流分组关联）

```json
{
  "TRACK_1": { "carrier": "<承运商展示文本>", "tracking_number": "<运单号>" }
}
```

物流分组是**订单内部关联标识**，不是包裹 ID、不是承运商轨迹，也不能用来推断真实承运商。

### 5.4 `skus_raw.json`

保留查询网站的原始字段（含空白、异常值与来源元数据），仅供数据质量追溯。

**当前数据基线**：2 笔订单、9 个唯一 SKU、9 条订单明细、31 件商品、3 个物流分组。

---

## 6. GST 与金额计算规则

全部金额使用 Python `Decimal`，任何环节都不使用或经过 `float`；API 输出为恰好两位小数的字符串，币种固定 `AUD`。

```text
Ex-GST Unit Price = RRP / 1.10                              # 保留内部精度，不提前舍入
Line Subtotal     = (Ex-GST Unit Price × Quantity).quantize(0.01, ROUND_HALF_UP)
Order Subtotal    = Σ 已舍入的 Line Subtotal
GST Amount        = (Order Subtotal × 0.10).quantize(0.01, ROUND_HALF_UP)
Shipment Fee      = 进入总额前 quantize(0.01, ROUND_HALF_UP)  # 当前为 0.00 降级值
Order Total       = (Order Subtotal + GST Amount + Shipment Fee).quantize(0.01, ROUND_HALF_UP)
```

示例（合成数值）：RRP `A$110.00`、数量 2 → 未税单价 `A$100.00`、行小计 `A$200.00`；订单小计 `A$200.00`、GST `A$20.00`、运费 `A$0.00`、订单总额 `A$220.00`。

前端只做展示：`amount` 始终是字符串，仅添加 `A$` 前缀，绝不转换为 JavaScript `number`，也不重算任何金额。

### 6.1 列表与详情的金额差异（D-030）

- **列表** `quote_request_state = "not_requested"`，`order_total = order_subtotal + gst_amount`，标签为 `Total before shipping`，表示**未请求运费**、不含真实运费。
- **详情** `quote_request_state = "requested"`，`order_total` 使用本次 `shipping_quote.applied_fee` 参与计算（当前为 `A$0.00` 降级值）。

两者金额允许且预期不同，不是数据错误。

### 6.2 GST 口径说明

当前实现采用更新版 HTML v2 的 GST 规则；该文档标注 `DRAFT FOR REVIEW`，且原始 PDF 存在 GST 口径冲突。系统按当前工程依据实现，**不代表已获出题方正式批准**；运费是否含 GST 仍属未决问题，因此运费部分不做任何 GST 反推或补算。

---

## 7. API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/orders` | 订单列表（独立 `OrderSummaryResult`，不触发任何外部调用） |
| GET | `/api/v1/orders/{order_number}` | 订单详情（含 `tracking_results`、`shipping_quote`、`package_estimation`） |

- 成功响应统一为 `{"data": ...}`。
- 错误响应统一为 `{"error": {"code": "...", "message": "..."}}`，错误码：`ORDER_NOT_FOUND`、`REQUEST_VALIDATION_ERROR`、`DATA_SOURCE_ERROR`、`INTERNAL_SERVER_ERROR`。
- 金额结构固定为 `{"amount": "123.45", "currency": "AUD"}`。
- 错误响应与日志不包含客户手机号、邮箱、地址、凭证或原始 JSON。

示例（合成数据）：

```json
{
  "data": {
    "order_number": "PO-XXXXXXXX-XXXXX",
    "items": [
      {
        "sku": "SKU-EXAMPLE",
        "quantity": 2,
        "tracking_group_id": "TRACK_1",
        "unit_price_incl_gst": { "amount": "110.00", "currency": "AUD" },
        "unit_price_ex_gst": { "amount": "100.00", "currency": "AUD" },
        "line_subtotal": { "amount": "200.00", "currency": "AUD" }
      }
    ],
    "pricing": {
      "order_subtotal": { "amount": "200.00", "currency": "AUD" },
      "gst_amount": { "amount": "20.00", "currency": "AUD" },
      "order_total": { "amount": "220.00", "currency": "AUD" }
    },
    "shipping_quote": {
      "status": "unsupported",
      "reason_code": "SHIPPING_QUOTE_NOT_IMPLEMENTED",
      "checked_at": "2026-01-01T00:00:00Z",
      "quoted_fee": null,
      "applied_fee": { "amount": "0.00", "currency": "AUD" }
    },
    "tracking_results": [
      {
        "tracking_group_id": "TRACK_1",
        "provider": null,
        "status": "unavailable",
        "reason_code": "CARRIER_MAPPING_UNRESOLVED",
        "checked_at": "2026-01-01T00:00:00Z",
        "provider_status": null,
        "current_status": null,
        "latest_event_at": null,
        "events": []
      }
    ],
    "package_estimation": {
      "status": "unavailable",
      "reason_code": "PACKAGE_RULES_NOT_CONFIGURED",
      "checked_at": "2026-01-01T00:00:00Z",
      "source": null,
      "ruleset_id": null,
      "ruleset_version": null,
      "synthetic_ruleset": false,
      "packages": []
    }
  }
}
```

金额与尺寸字段均为字符串，请勿用浮点解析。

---

## 8. Tracking API 的实现情况与限制

**已实现（离线、可测试）**：

- `TrackingService` 与不可变 `TrackingResult` / `TrackingEvent` / `ProviderTrackingResult` 领域模型。
- Australia Post / StarTrack 的 Track Items Adapter 与协议实现（分批、超时、响应体上限、稳定错误分类、状态映射），使用可注入的 HTTP transport，**测试中不发起真实网络请求**。
- 版本化 Provider/Account/Product/Mapping Revision 与 Configuration Release 只读目录（同 ID 内容不可变）。
- 每个唯一物流分组恰好一个结果；单个分组失败不影响其他分组，也不影响订单金额与详情主体。
- 原始承运商状态与标准化状态同时保留；无法识别的状态归一化为 `unknown`，不猜测。

**当前限制（不伪造）**：

- 没有已批准的 Provider/Account/Product/Mapping Revision、Configuration Release、凭证与账号权限，因此默认运行环境对每个物流分组返回 `provider=null`、`status="unavailable"`、`reason_code="CARRIER_MAPPING_UNRESOLVED"`，并且**不发出任何外部请求**。
- TNT 适配器未实现（Bonus 项），按契约返回 `unsupported` / `CARRIER_NOT_IMPLEMENTED`。
- 真实承运商连通性、testbed 与生产调用仍需账号、凭证与授权，属 `BLOCKED` 外部输入；离线测试通过不等于真实集成完成。

---

## 9. Shipment Fee 的处理方式

当前阶段运费能力**未实现**，采用冻结的 D-015 语义：

| 字段 | 值 |
|---|---|
| `status` | `"unsupported"` |
| `reason_code` | `"SHIPPING_QUOTE_NOT_IMPLEMENTED"` |
| `quoted_fee` | `null` |
| `applied_fee` | `{"amount":"0.00","currency":"AUD"}` |
| `checked_at` | 运行时 UTC 时间，仅表示本次系统检查时间 |

界面必须显示 `A$0.00` 并同时说明：**这不是承运商报价，也不代表免费运输**。订单总额按 `订单小计 + GST + A$0.00` 计算，因此当前展示的是"未计真实运费"的金额。

### 9.1 运费估算的设计思路（未来实现方向）

1. 依据版本化包装规则把订单行转换为包裹（Package），并记录规则版本与输入指纹；
2. 按已批准的 Provider/Account/Product/Mapping Revision 调用承运商报价接口（Contract Price，不做 PAC 或其他静默 fallback）；
3. 仅在 Provider/Product/合同明确确认金额含 GST 时，将其作为 `applied_fee` 进入订单总额；`shipping_gst` 只读展示，不重复计税；
4. 任一必要报价单元失败时整单降级为 `unavailable`，`applied_fee` 归零，绝不把部分金额当完整运费。

### 9.2 现阶段未实现的原因

- 无真实包装规格、包装材料目录与获批 Packaging Ruleset（仅商品物理数据，不能替代包装数据）；
- 无承运商账号、凭证、映射与 testbed 授权；
- 无各 Provider/Product 的 GST、体积重量、金额精度与舍入证据。

因此本阶段不做生产级装箱算法、物流计价引擎或复杂规则管理系统，而是保持明确、可解释的降级。

---

## 10. 图片占位符与其他合理假设

- **商品图片**：使用中性占位符（渐变方块 + 商品名称首字母，`role="img"`、`aria-label="Product image placeholder"`），不从网络获取图片，也不编造真实商品图。
- **缺失描述**：`description` 为空时显示 `Description unavailable`；`description_status="partial_needs_requery"` 时额外标注"来源描述可能被截断，需重新查询"，不补全、不猜测。
- **ETA**：`eta_days` 为空时显示 `ETA unavailable`，不回显 `nullDays` 等原始标记；有值时按原始文本展示（如 `0Days` 原样显示，不解释为当天送达）。
- **物流分组**：只作为内部关联标识展示，不代表承运商轨迹或包裹。
- **订单编号**：第二笔订单采用 `PO-20251203-00046`；原始 PDF 存在编号冲突，已在文档中保留该冲突记录。
- **数据来源**：SKU 数据来自指定查询网站的人工查询结果并保存为本地 JSON，系统**不做**实时抓取或外部数据 API 集成。

---

## 11. 环境变量与凭证安全

- 当前运行**不需要**任何凭证；系统在无凭证、无映射时安全降级。
- 未来的承运商凭证只能由后端从环境变量读取（通过受控的 `CredentialEnvironmentBinding` 指定变量名，仓库中不提供真实变量名或值），前端、README、日志、API 响应与 Git 中都不得出现密钥。
- 代码中使用 `SecretStr` 且 `repr=False`；错误信息只包含稳定错误码与安全摘要。
- 客户手机号、邮箱、地址不写入普通应用日志、测试快照或前端遥测；界面仅为完成业务展示而读取。
- `.env` 已被 `.gitignore` 排除；未经授权不得创建包含真实值的示例文件。
- 发布到公开仓库前必须替换或脱敏客户数据，并复核 Git 历史与构建产物。

---

## 12. 测试与质量门禁

后端（仓库根目录执行）：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
.\.venv\Scripts\python.exe -m pip check
```

前端：

```powershell
npm.cmd run test --prefix frontend
npm.cmd run typecheck:test --prefix frontend
npm.cmd run build --prefix frontend
npm.cmd run lint --prefix frontend
npm.cmd ls --prefix frontend --depth=0
npm.cmd audit --prefix frontend --audit-level=high
```

`npm.cmd run check --prefix frontend` 会依次执行测试、测试类型检查、生产构建与 lint。

覆盖重点：

- 金额链路：Ex-GST 不提前舍入、行小计/订单小计/GST/总额逐项舍入、全链路无 `float`、半进位边界；
- 真实数据验收：两笔订单独立计算并与独立重算结果逐行比对；
- 数据层：非法 JSON、重复 SKU、缺失 SKU/物流分组引用、非法数量；
- 物流与运费：`available`/`unavailable`/`unsupported` 矩阵、超时与异常响应、互不影响；
- 包装估算：无规则时 fail-closed、数量守恒、合成隔离；
- 前端：金额保持字符串、不重算、状态矩阵、缺失数据降级与无障碍。

---

## 13. 已知限制与未决事项

| 项 | 状态 |
|---|---|
| 真实承运商调用与 testbed 验证 | `BLOCKED`（缺账号/凭证/映射/授权） |
| 真实运费报价 | 未实现（`unsupported`，`A$0.00` 降级） |
| 生产包装规则与装箱算法 | 暂停（无真实包装数据；相关决策暂缓） |
| TNT 适配器 | 未实现（Bonus，不阻塞交付） |
| `0Days` ETA 业务语义 | 未决（按原值展示，不做解释） |
| HTML v2 GST 规则 | `DRAFT FOR REVIEW`，且原始 PDF 存在口径冲突 |
| 第二笔订单编号冲突 | 已采用 `PO-20251203-00046`，冲突记录保留 |
| 订单写入/分页/认证 | 不在本次范围 |

---

## 14. 与考核要求的对照

| 考核要求 | 实现与验证方式 |
|---|---|
| 订单数据读取与多订单独立处理 | JSON Repository + `OrderService`；两笔订单逐单计价，验收测试独立重算比对 |
| SKU 与商品信息匹配 | 订单行 `sku` → 商品记录；缺失引用时安全报错 |
| 商品名称、描述、RRP、数量、图片占位符 | 详情页商品列展示名称/描述/规格/ETA，RRP 列与中性占位图 |
| 未税单价、行小计、订单小计、GST、总额 | 全部由后端 `Decimal` 计算，界面按 API 值展示 |
| AUD 两位小数展示 | Money 固定两位小数字符串，前端仅加 `A$` 前缀 |
| 缺失/异常数据处理 | 缺失描述与 ETA 明确降级；非法数据返回稳定错误码 |
| 订单详情与列表展示 | 列表（搜索/筛选）+ 详情（客户、地址、商品、金额、物流、包装状态） |
| Tracking 独立与错误隔离 | 每个物流分组独立结果；无映射时 `unavailable` 且零外呼；不影响金额与详情 |
| Shipment Fee `A$0.00` 方案 | `unsupported` + `quoted_fee=null` + `applied_fee=0.00`，界面与本文档说明 |
| 运行与测试可复现 | 本文档第 4、12 节命令；后端 pytest、Ruff、pip check 与前端 Vitest、tsc、build、Oxlint 全部通过 |

---

## 15. 相关文档

- `AGENTS.md`：协作规范、冻结业务规则、数据与安全边界。
- `docs/ARCHITECTURE.md`：分层架构、金额链路、物流与包装边界。
- `docs/DECISIONS.md`：D-001～D-035 决策记录。
- `docs/PHASE6_CONTRACT.md`：Phase 6 冻结契约（Tracking / Quote / Package / API）。
- `docs/PROJECT_PLAN.md`：阶段计划与实施记录。
- `DATA_QUALITY_REPORT.md`：数据来源、清洗规则与已知质量问题。
- `frontend/README.md`：前端子目录补充说明。
