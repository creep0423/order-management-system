# Order Management System 项目协作规范

## 1. 文档适用范围

本文件适用于整个 `Order Management System` 仓库。所有开发者、自动化工具与 Codex 在仓库内工作时都必须遵守本文件。若任务说明与本文件存在冲突，应停止实施、记录冲突并请求确认，不得自行改变已冻结的业务规则。

当前状态为 **Phase 0～5 — COMPLETE**、**Phase 6 — IN_PROGRESS**、**Phase 7 — NOT_STARTED**。Phase 6 分段状态：Batch I Tracking 离线实现已冻结（`PARTIALLY_COMPLETE`，Git Checkpoint `6ccdc5f5300daa3aa92da97f7ae923596c605a11`，真实 Provider 验证 `BLOCKED`）；Batch J1 Package Estimation 已通过独立复审并冻结（`COMPLETE`，synthetic-only，Checkpoint `3c3675e4cb2deb47bba81346f4d1bc0c6ae290db`）；Batch J2 **契约**已冻结（Task 048 批准 DEC-1～DEC-4 并形成 D-032～D-035，`BATCH_J2_CONTRACT: COMPLETE`），Batch J2 **实施**按 Task 049-R 指令**暂停**（`PAUSED`，未开始），交付范围以原始《IT Coding Assessment》为准；DEC-5（Packaging 配置治理）与 DEC-6（多进程全局限流）为 `DEFERRED / NOT_APPROVED`，不得作为已冻结业务决策实施。真实 Provider/账号/凭证/Mapping/Release/testbed 验证与真实包装数据仍为 `BLOCKED`，不得把离线测试通过表述为真实集成完成。下一入口为最终独立验收。当前已确认的数据基线为：2 笔订单、9 个唯一 SKU、9 条订单明细、31 件商品、3 个物流分组；9 个 SKU 只有商品物理数据，**无任何包装规格或包装材料数据**。

## 2. 项目目标

构建一个企业级但不过度设计的订单管理系统，支持：

- 订单详情展示；
- 商品价格、GST、订单合计的可靠计算；
- 按物流分组查询物流状态；
- 运费报价与不可用时的明确降级；
- 对缺失商品描述、ETA 和外部物流故障进行可解释处理；
- 在数据、日志、前端和版本控制中保护客户信息与 API 凭证。

当前范围不包含微服务、消息队列、Redis、数据库或其他未经确认的基础设施。

## 3. 技术栈

### Backend

- Python 3.13
- FastAPI
- Pydantic
- Python `Decimal`
- pytest

### Frontend

- React
- TypeScript
- Vite

### Data

- JSON 文件作为当前数据源；
- 原始数据与标准化数据分离；
- 当前不引入数据库。

## 4. 项目架构

采用 **Modular Monolith（模块化单体）**。后端逻辑按职责分层，但在单一后端应用中部署：

1. **API Layer**：HTTP 路由、输入输出模型、状态码与错误响应。
2. **Service Layer**：订单编排、价格计算、物流追踪、运费估算等业务规则。
3. **Repository Layer**：读取并验证 JSON 数据，不承载业务计算。
4. **Integration Layer**：隔离 Australia Post、StarTrack、TNT 等外部物流服务。

层级依赖方向为：`API -> Service -> Repository / Integration`。Repository 不依赖 Service，Integration 不包含订单定价规则，前端不直接读取后端数据文件或调用带凭证的物流 API。

详细设计见 `docs/ARCHITECTURE.md`。

## 5. 目录结构约定

当前后端实际结构如下。不存在 `backend/app` 包；后续模块应延续当前 `backend/` 顶层包结构，并只在对应阶段需求驱动下创建：

```text
order-management-system/
├── AGENTS.md
├── backend/
│   ├── api/
│   │   ├── routes/             # Health 与 API v1 Order routes
│   │   ├── dependencies.py     # 应用级 Service 注入
│   │   ├── errors.py           # 统一安全错误映射
│   │   ├── mappers.py          # Domain/Service -> API Schema
│   │   └── schemas.py          # API v1 Pydantic schemas
│   ├── data/
│   │   ├── orders.json
│   │   ├── skus.json
│   │   ├── skus_raw.json
│   │   └── tracking.json
│   ├── models/
│   │   ├── domain.py           # 不可变领域模型
│   │   └── source.py           # JSON Source Models
│   ├── repositories/
│   │   ├── collection.py       # 统一入口与跨文件引用校验
│   │   ├── exceptions.py       # Repository 异常与安全诊断
│   │   ├── interfaces.py       # 只读 Repository protocols
│   │   ├── loader.py           # JSON 读取及脱敏校验诊断
│   │   ├── order.py
│   │   ├── product.py
│   │   └── tracking.py
│   ├── services/
│   │   ├── exceptions.py       # Service 分类异常
│   │   ├── order.py            # 订单业务编排
│   │   └── pricing.py          # Decimal 定价规则
│   ├── tests/                  # Health、CORS、Model、Repository、Service、API tests
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       ├── services/
│       ├── types/
│       └── utils/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── PROJECT_PLAN.md
├── DATA_QUALITY_REPORT.md
└── README_PHASE0.md
```

新增目录或模块必须由具体需求驱动。不得为了“未来可能需要”提前引入微服务、消息基础设施、缓存或数据库抽象。

### 5.1 Phase 2 已实现边界

- Source Model 严格对应 `orders.json`、`skus.json` 和 `tracking.json` 的 JSON 结构，负责字符串 Decimal、日期、必填字段和缺失状态校验；
- Domain Model 与 JSON envelope、API schema 分离，使用不可变 Pydantic 模型、严格 `Decimal` 和严格正整数；
- Order、Product/SKU、Tracking Repository 只读加载并缓存经过验证的数据；
- `RepositoryCollection` 是统一数据入口，验证订单 SKU 与物流分组引用，并提供必要的关联查询；
- Repository 不读取 `skus_raw.json`，不包含 GST、定价、运费、外部 API 或写入逻辑；
- 数据校验异常仅公开数据源名、安全字段路径、记录索引和错误类型，不公开原始输入、客户信息或 Pydantic 原始错误。

### 5.2 Phase 3 已实现边界

- Pricing Service 以经过验证的 Product 和严格正整数数量为输入，使用与调用者隔离、按输入规模动态确定精度的 Decimal Context，按 D-004 逐行计算并返回不可变、Decimal-only 的 `PricingResult`；
- Order Service 依赖现有 Repository protocols，按订单号读取并关联商品，组合不可变的 `OrderResult`，不直接读取 JSON；
- Service 异常区分非法金额、非法数量、Decimal 运行时无法安全完成计算、订单不存在、商品不存在和关联不一致，错误文本不公开客户信息或原始 JSON；
- Service 不保存跨请求计算状态，每笔订单独立计算；
- Service 结果保持 Decimal 并与 API Schema 分离；Tracking 与外部物流 Integration 已在 Phase 6 Batch I 实现离线基础，真实 Provider 激活仍受外部输入阻塞。

### 5.3 Phase 4 已实现边界

- API v1 提供 `GET /api/v1/orders` 与 `GET /api/v1/orders/{order_number}`，并保留 `GET /health`；
- Router、Schema、Mapper、Dependency、Service 与 Repository 职责分离，Router 不读取 JSON、不访问文件系统、不执行价格计算，也不直接返回 Domain Model；
- 成功响应统一为 `{"data": ...}`，错误响应统一为 `{"error":{"code":"...","message":"..."}}`；
- Money 通过显式 Decimal serializer 输出两位小数字符串和固定 `AUD`，API Mapper 不重新计算业务金额；
- RepositoryCollection 与 OrderService 在 FastAPI lifespan 中初始化一次，测试可通过 `dependency_overrides` 注入合成 Service；
- Order Service 当前生成明确的初始 ShippingQuoteResult：`unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`、UTC `checked_at`、`quoted_fee=null`、`applied_fee=Decimal("0.00")`，并将 applied fee 传入 Pricing Service；
- 订单详情返回完整 `shipping_quote`，订单列表返回 `shipping_quote_status` 与 `shipping_quote_reason_code`；Phase 6 Batch I 已增加独立 `tracking_results`，按 D-031 每组一个结果且 `provider` 条件可空；不得构造追踪数据或虚假报价。

## 6. 冻结的业务规则

以下规则已冻结。除非获得明确授权并同步更新决策记录、测试和相关文档，否则不得更改。

### 6.1 订单与金额

1. 每笔订单独立计算，不得合并不同客户的订单。
2. 所有金额使用 AUD。
3. RRP 已包含 GST。
4. `Ex-GST Unit Price = RRP / Decimal('1.10')`。此步骤保留 Decimal 内部精度，不提前舍入。
5. `Line Subtotal = (Ex-GST Unit Price × Quantity).quantize(Decimal('0.01'), ROUND_HALF_UP)`。
6. `Order Subtotal = 所有已舍入 Line Subtotal 之和`。
7. `GST Amount = (Order Subtotal × Decimal('0.10')).quantize(Decimal('0.01'), ROUND_HALF_UP)`。
8. Shipment Fee 进入总额前必须使用 `ROUND_HALF_UP` 标准化到两位小数。
9. `Order Total = (Order Subtotal + GST Amount + Shipment Fee).quantize(Decimal('0.01'), ROUND_HALF_UP)`。
10. 从输入解析、内部运算到 API 序列化前的所有货币计算都必须使用 Python `Decimal`，禁止使用或经过 `float`。
11. 内部计算值与展示值分离。Ex-GST Unit Price 保留内部精度；Line Subtotal、GST Amount、Shipment Fee 和 Order Total 按上述时点舍入。商品 GST 继续只按上述公式计算。按 D-022，Shipping Quote 仅在 Provider、Product 和合同证据明确确认 `total_cost` 含 GST 时，才使用经过 D-029 验证并按 D-004 标准化的金额作为 `quoted_fee` 与 `applied_fee`；Provider 明确返回的 `shipping_gst` 只作只读展示，不进入 Pricing Service，也不得再次加入订单总额。不得从 `total_cost` 反推 `shipping_gst`，不得从商品 GST 规则推导运费 GST；缺少 Provider/Product GST 证据时必须 fail closed 为 `unavailable`。
12. 当前采用更新版 HTML v2 的 GST 规则。必须同时记录：原始 PDF 存在口径冲突，更新版 HTML 标注为 `DRAFT FOR REVIEW`。不得声称该规则已获得出题方正式批准。
13. 第二笔订单采用 `PO-20251203-00046`。必须保留原始 PDF 中订单编号存在冲突的记录。
14. 列表使用独立 `OrderSummaryResult`。按 D-030，当 `quote_request_state="not_requested"` 时必须满足 `order_total = order_subtotal + gst_amount` 且 `shipment_fee = Decimal("0.00")`，Domain 层强制该公式、拒绝 float，并禁止把该金额解释为最终含运费总额、零运费、免费运输或任何 fallback。详情继续按实际 `shipping_quote.applied_fee` 使用原 Pricing 规则，不得套用列表公式。

### 6.2 物流、运费与商品展示

15. 物流数据通过 `backend/data/tracking.json` 关联，不得在业务代码、前端代码或测试夹具中散落硬编码真实追踪编号。
16. Australia Post / StarTrack 优先实现真实查询；TNT 为 Bonus，不得阻塞核心交付。TNT 适配器尚未实现时必须返回 `status="unsupported"`、`reason_code="CARRIER_NOT_IMPLEMENTED"`。
17. 统一状态语义：`available` 表示查询成功且结果有效；`unavailable` 表示功能或适配器已实现但本次查询失败；`unsupported` 表示功能或适配器尚未实现。物流 API 无法访问、超时或返回无效结果时不得编造物流状态、更新时间、轨迹或报价。
18. Tracking 与 Shipping Quote 是相互独立的结果。Tracking 查询失败不得导致 Shipping Quote 失败，Shipping Quote 查询失败也不得覆盖或降级已经成功的 Tracking 结果；Order Service 只组合结果，不传播无关失败。
19. 无法获得有效运费报价时，Shipping Quote 保持 `unavailable` 或 `unsupported`，`quoted_fee=null`，`applied_fee` 的金额值为 `"0.00"`；前端显示 `A$0.00` 并在项目 README 中记录原因和限制，不得将其伪装成已确认的免费运输报价。
20. 商品图片允许使用中性占位图；商品描述或 ETA 缺失时必须优雅降级并明确表示不可用。不得获取或编造未经批准的商品图片、描述或 ETA。
21. Shipping Quote Integration 尚未实现期间固定返回 `status="unsupported"`、`reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED"`、`quoted_fee=null` 和零值 `applied_fee`；`checked_at` 必须是运行时 UTC aware datetime，仅表示系统检查时间。
22. 按 D-031，`TrackingResult.provider` 仅在 `status="unavailable"` 且 `reason_code="CARRIER_MAPPING_UNRESOLVED"` 时可为 `null`；其余结果必须有具体 Provider。Mapping 无法解析（无 Active Release、零个或多个适用 Mapping）时必须为每个唯一 Tracking Group 返回该 unavailable 结果，零 Provider 请求，不得返回空数组、不得虚构 Provider/事件/ETA，也不得显示为 `not requested`。已确定 Provider 的配置错误保留 Provider 与既有 reason。`tracking_results=[]` 只表示订单没有唯一 Tracking Group。
23. 包装规则按 D-032～D-035 冻结：`PackingPolicy` 使用结构化封闭 schema（scope 三层匹配、封闭枚举、拆分/混装/上限、零匹配 fail closed、policy 只能收紧）；约束按 SKU 事实 / 材料能力 / policy 收紧三处归属并由运行时 `EffectiveConstraintView` 合并；生产算法为分阶段确定性 Best-Fit Decreasing（不承诺最优 3D 装箱）；材料选择为 F1～F8 硬过滤 + 两种封闭策略 + 8 条禁止 fallback。详细字段与阶段见 `docs/PHASE6_CONTRACT.md` §5.4～§5.8。包装失败仍只用 `PACKAGE_RULES_NOT_CONFIGURED` / `PACKAGE_DATA_INCOMPLETE`，不得新增公共 reason code。
24. J1 合成隔离必须保留：不得放宽 `synthetic_only`、不得用 `model_construct` 或关闭校验绕过 Domain 校验、不得把测试 fixtures 接入生产模块、不得默认创建包装规格/材料/生产 ruleset、不得用商品物理数据替代真实包装数据，也不得因 D-032～D-035 获批而宣称真实包装数据或生产包装能力已就绪。

## 7. 数据处理规范

- `backend/data/skus_raw.json` 是原始数据，只用于溯源和质量核对。业务运行不得直接修改或以其作为商品主数据源。
- `backend/data/skus.json` 是当前标准化商品数据源。
- `backend/data/orders.json` 与 `backend/data/tracking.json` 是当前订单和物流关联数据源。
- Repository 加载数据时必须校验 JSON 可解析性、必需字段、SKU 唯一性、订单 SKU 引用和物流分组引用。
- 金额、重量、尺寸、体积等字符串数值必须在明确边界解析；解析失败时返回可诊断错误，不得静默使用猜测值。
- 标准化不得覆盖原始文件。任何清洗规则变更都必须有测试和决策依据。
- 缺失描述、异常 ETA 和待重新查询的数据状态必须保留，不得自动补全。
- 当前数据基线与已知质量问题以 `DATA_QUALITY_REPORT.md` 为准。

## 8. API 开发规范

- API 仅负责协议适配，不在路由函数中实现价格、物流或运费业务规则。
- 输入输出使用明确的 Pydantic schema，禁止直接返回未验证的原始字典。
- API 必须区分成功、业务数据缺失、外部服务不可用、功能未实现和内部错误。
- Money API 结构冻结为 `{"amount":"123.45","currency":"AUD"}`。`amount` 必须是恰好两位小数的十进制字符串，`currency` 固定为 `AUD`。
- Money serializer 必须将 `Decimal("-0")` 等所有数值零规范化为 `"0.00"`；非零负数、float、NaN 和 Infinity 仍须拒绝。
- Pydantic 模型中的 `Decimal` 必须通过显式 serializer 输出 Money JSON；不得依赖隐式转换，也不得经过 `float`。
- `TrackingResult` 与 `ShippingQuoteResult` 必须作为独立结构返回，二者均包含 `status`、`reason_code`、`checked_at` 及各自数据。`checked_at` 表示系统本次检查时间，不得冒充承运商事件更新时间。
- Phase 6 协调发布后的 `ShippingQuoteResult` 包含 `quoted_fee`、`applied_fee` 和只读 `shipping_gst`；当前 D-015 运行时模型仍只实现 quoted/applied fee，不得在本阶段伪造新字段。API 中非空费用使用 Money 结构；无有效报价时 `quoted_fee=null`、`applied_fee={"amount":"0.00","currency":"AUD"}`、`shipping_gst=null`，状态仍为 `unavailable` 或 `unsupported`。`shipping_gst` 只有在所有必要报价单元均有明确 Provider 原始 GST 证据时才可聚合展示；不得从 `total_cost` 反推，也不得进入 Pricing。
- `shipping_quote.applied_fee` 是 API 中进入 Order Total 的唯一运费金额来源；零值结合 `unsupported` 状态表示降级计算，不得解释为免费运输。
- Phase 6 协调发布后，订单列表使用独立 `OrderSummaryResult` 和公开 `quote_request_state="not_requested"`，不构造 ShippingQuoteResult、不调用详情或 Provider。按 D-030，列表 `order_total = order_subtotal + gst_amount`，包含商品 GST 但不含真实运费；UI 必须标为 `Total before shipping` 并说明 `Shipping quote not requested`，不得表达为最终含运费总额、零运费、免费运输或任何 fallback。订单详情使用 `OrderDetailResult`、`quote_request_state="requested"` 和必填 ShippingQuoteResult，且 `shipping_quote.applied_fee` 必须等于 `pricing.shipment_fee`；列表与详情金额允许且预期不同。
- Provider、Account、Product、Mapping 和 Release 必须分别使用显式、已验证的不可变 Revision；每个 Revision ID 必须独立决定其完整内容，同一 ID 相同内容可幂等读取、不同内容必须拒绝，不得用三元组或其他 ID 差异绕过；Mapping Revision 必须显式引用准确的 Provider/Account/Product Revision，Release 必须固定精确 Mapping Revision 集合。请求开始时捕获唯一 Active Configuration Release，并在整个请求内固定全部 Revision；禁止通过 stable ID、`latest`、最高版本或创建时间推断版本，切换或 rollback 不得影响在途请求。carrier 展示文本、tracking number 形状和 Tracking Group 不得选择 Quote Provider。
- Configuration Release 只能包含已审批、已验证的 Revision；每个 environment/configuration scope 同一时刻只有一个 Active Release，切换和 rollback 必须原子、可审计。Rollback 通过重新激活既有不可变 Release 完成，不得修改或删除历史 Revision。配置治理数据不属于 Quote History，也不授权跨请求 Quote Cache。
- 所有必要 Quote Unit 必须在网络调用前完成 Capability Preflight；必要 Adapter 未实现为 `unsupported / CARRIER_NOT_IMPLEMENTED`，已实现但 release/mapping/config 不可用为 `unavailable`，预检失败不得发出部分 Provider 请求。
- Provider 原始金额和单元验证金额保留内部 Decimal 证据；所有必要单元先精确聚合，再仅在订单级按 D-004 使用 `ROUND_HALF_UP` 标准化为相等的两位 `quoted_fee/applied_fee`。缺少 Provider/Product/合同精度或转换证据时必须 fail closed。
- API 状态只使用冻结语义：`available` 为成功；`unavailable` 为已实现但本次失败；`unsupported` 为尚未实现。不得用虚构的成功响应替代失败或未实现状态。
- 不得在 API 响应、错误详情或日志中泄露 API 凭证。
- 不得把客户手机号、邮箱、地址写入普通应用日志。
- API v1 路径、成功 envelope 和统一错误响应已由 D-014 确认；后续新增 endpoint 或错误码必须保持该版本与响应边界。

## 9. 前端开发规范

- 使用 React、TypeScript 与 Vite；启用严格类型检查，避免使用无理由的 `any`。
- 前端只通过后端 API 获取订单、价格、物流和报价结果，不直接读取 `backend/data`。
- 物流 API 凭证不得进入前端源代码、构建变量或浏览器请求。
- TypeScript 中 Money `amount` 必须保持为 `string`。前端不得转换为 JavaScript `number`，不得重新计算商品行、GST、运费或订单总额；只负责为 `amount` 添加 `A$` 展示前缀并按 API 值展示。
- 金额展示统一使用 AUD、两位小数和清晰的 GST/运费拆分。
- Tracking 与 Shipping Quote 的状态必须独立展示；一个结果失败不得隐藏另一个结果的成功数据。
- 按 D-031，UI 必须区分 available、unavailable、Mapping unresolved（`Tracking unavailable — carrier mapping could not be resolved.`）、unsupported、成功但无事件、raw status unknown 和订单没有 Tracking Group；不得把 Mapping failure 显示为 `Tracking not requested`，`tracking_results=[]` 只能表达没有唯一 Tracking Group，并不得展示虚构事件、ETA 或承运商。
- 对 `unavailable`、`unsupported`、缺失描述、缺失 ETA 和占位图提供清晰、不中断页面的降级 UI。
- 不得把 `A$0.00` 降级运费展示成已确认的承运商报价。
- 客户数据仅在业务必要范围内展示，不得输出到浏览器控制台或前端遥测。

## 10. 测试要求

- 新增或修改业务行为时必须新增或更新测试。
- Pricing Service 必须逐项覆盖 Ex-GST Unit Price 不提前舍入、Line Subtotal 舍入、舍入后行金额汇总、GST Amount 舍入、Shipment Fee 两位小数标准化和 Order Total 最终舍入；测试必须证明全链路未使用 `float`。
- Repository 必须覆盖 JSON 解析失败、重复 SKU、缺失 SKU 引用和缺失物流分组引用。
- Tracking/Shipping 必须分别覆盖 `available`、`unavailable`、`unsupported`、超时、异常响应和无凭证，并验证一方失败不会传播到另一方；不得依赖真实外部 API 才能运行单元测试。
- Tracking 必须覆盖 D-031 全部合法/非法 provider-null 组合、Mapping missing/ambiguous/无 Active Release、每组一个结果、Mapping failure 零 HTTP、默认应用注入且不外呼、空 Tracking Group 与 AP/StarTrack/TNT/未知 Provider 状态映射。
- Revision 不可变性必须逐类覆盖 Provider/Account/Product/Mapping/Release 的“同 ID 同内容允许、同 ID 不同内容拒绝、不同 ID/Release 合法不同”，且不得以三元组差异绕过。
- API 测试必须验证 Money 字符串格式、显式 Decimal 序列化、TrackingResult/ShippingQuoteResult schema、状态语义、错误边界和敏感数据不泄露。
- 前端测试必须验证 Money `amount` 保持 string、只添加 `A$` 前缀、不重新计算金额，并覆盖独立物流状态、加载状态和缺失数据降级。
- 缺陷修复必须尽可能先添加可复现测试。
- 测试结果必须在任务总结中报告；不能执行的测试要说明原因，不得宣称通过。

## 11. 安全规范

- 客户手机号、邮箱和地址不得写入普通应用日志、调试输出、测试快照或公开文档。
- API 凭证只能从环境变量读取，不得硬编码在代码、JSON、前端或文档中。
- `.env` 不得提交到 Git；如后续需要示例，只能提供不含真实值的 `.env.example`，且须在授权范围内创建。
- 公开 GitHub 前必须替换或脱敏客户数据，并复核 Git 历史和构建产物。
- 错误消息只暴露解决问题所需的信息，不得回显凭证、完整外部响应或个人数据。
- 不得在前端暴露物流 API 凭证。

## 12. Git 规范

- 未经明确授权不得初始化 Git、创建或移动标签、推送远程、创建 PR 或修改远程仓库设置。
- 提交应按最小逻辑单元组织，提交信息说明目的和范围。
- 只显式暂存已审核文件，不使用 `git add .` 或 `git add -A`。
- 不提交 `.env`、真实凭证、日志、缓存、构建产物或未脱敏客户数据。
- 不得使用 force push 或破坏性历史重写，除非用户明确授权并确认影响。
- 提交前运行与变更相关的测试，并检查变更范围和敏感信息。

## 13. Codex 执行工作流程

Codex 执行任何任务时必须遵循：

1. 开始任务前先解释目标、边界和预期结果。
2. 先检查相关代码、数据、文档和当前工作区状态。
3. 提出与任务范围匹配的实施计划；遇到影响业务规则的歧义时先记录为 Open Question。
4. 按最小可交付单元开发，避免无关重构和预防性架构扩张。
5. 编写或更新与变更对应的测试。
6. 执行相关测试与必要的静态检查；不伪造测试结果。
7. 汇报修改文件、测试结果、验证范围和遗留问题。
8. 未经明确授权不得修改无关模块、数据文件或基础设施。
9. 不得擅自改变冻结的业务规则；如发现冲突，停止相关实现并请求确认。

## 14. Open Questions

以下问题尚未确认，不得自行假设：

- 更新版 HTML v2 的 GST 规则是否会获得出题方正式批准？
- 原始 PDF 中第二笔订单编号冲突的另一编号及最终审计展示方式是什么？
- Australia Post / StarTrack 的实际 Provider/Account/Product/Mapping Revision、获批准 Configuration Release、凭证权限、环境和运行时调用参数是什么？
- 运费报价的包装、分组、计费重量、体积重量除数和承运商报价规则是什么？
- `0Days` ETA 的业务语义是什么？
- TNT Bonus 是否会进入最终交付范围？
- 公开仓库采用完全替换示例客户数据，还是字段级脱敏？
