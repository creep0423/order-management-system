# Order Management System 架构说明

## 1. 文档状态

- 当前阶段：Phase 0～5 — COMPLETE；Phase 6 — IN_PROGRESS；Phase 7 — NOT_STARTED
- 阶段状态：Phase 6 Batch I Tracking Foundation `PARTIALLY_COMPLETE`，离线实现已通过 Task 043 独立复审并冻结为 Git Checkpoint `6ccdc5f`；真实配置与 Provider 验证仍 BLOCKED
- 架构风格：Modular Monolith
- 实现状态：Phase 1～5 已完成；Phase 6 Batch I 已实现 Tracking Domain、AP/ST Adapter、Tracking Service、D-031 Mapping Unresolved 投影、五种 Revision ID 独立不可变校验、协调 API/Frontend 契约与离线测试；Phase 6 Batch J1 已实现 Package Domain、只读版本化 Packaging Rules、确定性 Package Estimation Service、数量守恒、provenance、协调 API/Frontend 与离线测试；真实 Provider 配置/凭证与真实包装数据仍未接入
- 数据基线：2 orders、9 SKUs、9 order lines、31 units、3 tracking groups

本文描述当前批准的最小架构边界。未明确的内容标记为 **Open Question**，不得将规划内容描述为已实现能力。

## 2. 系统整体架构

系统采用前后端分离的模块化单体。React 前端通过 HTTP API 与单一 FastAPI 后端通信；后端内部以清晰的 Layer 和业务模块组织。当前使用本地 JSON 文件，不引入数据库。

```text
┌──────────────────────────────────────────────────────────────┐
│ React + TypeScript + Vite                                   │
│ 订单详情 / 价格展示 / 物流追踪 / 运费状态 / 降级 UI          │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP/JSON
┌───────────────────────────▼──────────────────────────────────┐
│ FastAPI Modular Monolith                                    │
│                                                              │
│  API Layer                                                   │
│      │                                                       │
│  Service Layer                                               │
│  ├── Order Service                                           │
│  ├── Pricing Service                                         │
│  ├── Tracking Service                                        │
│  └── Shipping Service                                        │
│      │                         │                              │
│  Repository Layer              Integration Layer             │
│  ├── Order Repository          ├── Australia Post client     │
│  ├── SKU Repository            ├── StarTrack client          │
│  └── Tracking Repository       └── TNT client (Bonus)        │
└───────────────┬───────────────────────────────┬──────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
│ JSON Data                    │  │ External Logistics APIs    │
│ orders / skus / tracking     │  │ 不可信、可能超时或不可用    │
└──────────────────────────────┘  └────────────────────────────┘
```

架构约束：

- 保持单一后端部署单元，不拆分微服务。
- 不引入消息队列、Redis 或数据库。
- 业务规则集中在 Service Layer，不散落在 route、Repository 或前端。
- 外部 API 被视为不可靠边界，所有调用必须可超时、可失败、可降级。
- 数据文件与外部 API 的具体结构不得穿透到前端。

### 2.1 当前实际目录结构

后端当前直接使用 `backend` 作为 Python package 根，不存在 `backend/app` 中间层：

```text
backend/
├── api/
│   ├── routes/                 # Health 与 API v1 Order routes
│   ├── dependencies.py         # 应用级 Service 注入
│   ├── errors.py               # 安全错误响应映射
│   ├── mappers.py              # Service Result -> API Schema
│   └── schemas.py              # 显式 API v1 schemas
├── data/                       # 当前只读 JSON 数据源
├── models/
│   ├── source.py               # JSON Source Models
│   ├── domain.py               # 不可变 Order/Pricing Domain Models
│   ├── tracking.py             # Phase 6 Tracking Domain、配置与安全诊断
│   ├── package.py              # Batch J1 Package Domain、provenance 与诊断
│   └── packaging_rules.py      # Batch J1 只读版本化 Packaging Rules
├── repositories/
│   ├── loader.py               # 集中 JSON 读取与安全校验诊断
│   ├── exceptions.py           # 分类异常与安全诊断结构
│   ├── interfaces.py           # 只读 Repository protocols
│   ├── order.py
│   ├── product.py
│   ├── tracking.py
│   └── collection.py           # 统一入口与引用完整性校验
├── services/
│   ├── exceptions.py           # 非敏感 Service 分类异常
│   ├── pricing.py              # 纯 Decimal 定价规则
│   ├── order.py                # 列表/详情订单业务编排
│   ├── tracking.py             # Mapping pinning、批处理、去重与结果隔离
│   ├── packaging_rules.py      # 只读 Packaging Rules reader
│   ├── package_estimation.py   # 确定性 rules-based Package Estimation
│   └── README.md               # Service 层与 Batch J1 包装边界说明
├── integrations/
│   ├── credentials.py          # 环境变量凭证解析，secret 不进入版本化配置
│   └── tracking.py             # AP/ST Track Items Adapter 与有界 HTTP transport
├── tests/
└── main.py
```

后续模块应延续该顶层 package 布局，不为目录整齐额外引入 `backend/app` 包或其他抽象层。

## 3. 前后端职责划分

### 3.1 Frontend 职责

- 展示订单、商品行、GST、运费和订单总额；
- 展示物流分组及真实查询结果；
- 对加载、空值、错误和 `unavailable` 状态提供明确 UI；
- 对缺失商品描述和 ETA 优雅降级；
- 使用中性商品占位图；
- 保持 TypeScript 类型与后端 API schema 一致；
- 不执行权威价格计算，不保存物流 API 凭证，不直接读取后端 JSON。

前端可以为了交互即时显示派生信息，但后端 Service 的结果是价格和状态的权威来源。

### 3.2 Backend 职责

- 加载和验证订单、SKU 与物流映射数据；
- 按冻结规则执行 Decimal 价格计算；
- 将订单明细与标准化 SKU、物流分组组合；
- 安全调用外部物流追踪和运费报价能力；
- 将外部错误转换为稳定的领域状态；
- 确保响应和日志不泄露凭证或非必要客户数据；
- 为前端提供经过验证且结构稳定的 API 响应。

## 4. 后端分层职责

### 4.1 API Layer

当前状态：**Phase 4 只读 Order API v1 已实现并通过自动化验证**。

负责：

- 定义 FastAPI routes；
- 使用 Pydantic 验证请求和响应；
- 将 Service 结果映射为 HTTP 状态码和响应 schema；
- 将已分类异常映射为稳定、非敏感的错误响应；
- 注入 Service 依赖。

不负责：

- 读取 JSON 文件；
- 计算 GST 或订单金额；
- 拼接物流 API URL、认证头或解析承运商响应；
- 在 route 中实现降级业务规则。

当前实现细节：

- `GET /api/v1/orders` 返回不含客户隐私的订单管理摘要和 Shipping Quote 状态；`GET /api/v1/orders/{order_number}` 返回订单、客户、地址、商品、物流分组关联、价格详情与完整 `shipping_quote`；
- 成功 envelope 固定为 `{"data": ...}`；错误 envelope 固定为 `{"error":{"code":"...","message":"..."}}`；
- `schemas.py` 定义与 Domain Model 分离的不可变响应模型，Money 内部持有严格 Decimal 并通过显式 serializer 输出两位小数字符串；所有正零和负零统一输出 `"0.00"`；
- `mappers.py` 仅投影字段和包装 Money，不重新计算商品行、GST、运费或总额；
- FastAPI lifespan 初始化一次 RepositoryCollection 与 OrderService，并存放于 application state；Router 使用 `Depends` 获取 Service，测试通过 `dependency_overrides` 替换；
- 已知业务、请求校验、数据源和未知错误分别映射为稳定、非敏感的 404、422 与 500 响应，不返回 traceback、原始异常、内部路径或 Pydantic 原始错误。

### 4.2 Service Layer

当前状态：**Pricing、Order Service 及 Phase 6 Batch I Tracking Service 已实现并通过离线自动化验证；真实 Provider 未验证**。

负责：

- 执行冻结的订单和定价规则；
- 编排 Repository 与 Integration；
- 维护订单级隔离，不跨客户合并订单；
- 区分有效结果、缺失数据和外部服务不可用；
- 生成供 API Layer 使用的领域结果。

Service 不直接依赖 FastAPI request/response 对象，也不直接读取环境变量或文件路径。

当前实现细节：

- `PricingService` 是无 I/O、无跨订单状态的纯业务计算服务，输入为经过验证的 Product、严格正整数 quantity 和 Decimal shipment fee；每次调用使用独立 Decimal Context，工作精度由金额系数、指数跨度、quantity 位数和订单累加规模动态确定，并保留 32 位除法保护位；
- `OrderService` 依赖现有 `OrderReader`、`ProductReader` 接口，通过 `RepositoryCollection` 编排订单与商品关联，为 API 列表用例提供逐订单独立定价的 `list_orders`，并在报价能力未实现时构建 D-015 的 unsupported ShippingQuoteResult；
- `LinePricingResult`、`PricingResult`、`OrderResultItem`、`ShippingQuoteResult` 与 `OrderResult` 均为不可变领域模型，保留 Decimal 内部精度，不承担 Phase 4 Money JSON 序列化；`OrderSummaryResult` 在 Domain 层强制 D-030 的 `order_total = order_subtotal + gst_amount`、零 `shipment_fee` 与 Decimal-only 金额；
- 分类异常不回显订单号、SKU 值、客户信息或原始 JSON；
- Tracking Domain、Tracking Service、Australia Post/StarTrack Track Items Adapter 与前后端展示已实现；没有已批准 Mapping/Release 时，默认应用为每个唯一 Tracking Group 返回 D-031 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED` 且不发外部请求；Shipping Service 仍未实现并继续保持 D-015。

### 4.3 Repository Layer

当前状态：**Phase 2 已实现并通过自动化验证**。

负责：

- 读取 JSON 数据源；
- 将原始结构转换为明确的领域模型；
- 校验必需字段、唯一键和引用完整性；
- 提供按订单号、SKU、物流分组 ID 查询的方法；
- 对文件不存在、JSON 无效、重复 SKU 和悬空引用返回明确错误。

Repository 不负责价格计算、外部 API 调用或 UI 展示格式。

当前实现细节：

- `loader.py` 集中执行 UTF-8 JSON 读取、重复 JSON key 检测和 Pydantic Source Model 校验；
- 校验失败通过安全诊断公开 `source_name`、记录路径、字段路径和 Pydantic error type，不携带 input、ctx、msg 或原始 `ValidationError`；
- Order、Product 与 Tracking Repository 在初始化时读取一次并缓存不可变 Domain Model；
- `RepositoryCollection` 组合三个 Repository，验证 SKU 和 tracking group 引用，并提供订单到商品、订单到物流分组及商品到订单的关联查询；
- 默认数据路径由 Repository 模块位置解析，不依赖进程当前工作目录；
- `skus_raw.json` 不在 Repository 运行时读取链路中。

数据源约束：

- `orders.json`：当前订单数据源；
- `skus.json`：当前标准化商品数据源；
- `tracking.json`：当前物流分组映射源；
- `skus_raw.json`：仅用于溯源和质量核对，不作为运行时商品主数据，也不得由业务代码修改。

### 4.4 Integration Layer

当前状态：**Phase 6 Batch I 基础实现完成，生产激活受外部输入阻塞**。

负责：

- 封装承运商 endpoint、认证、请求参数和响应解析；
- 从环境变量获得凭证；
- 设置超时并捕获网络、认证、限流和格式错误；
- 将承运商特定响应转换为内部统一结果；
- 不记录凭证、完整客户数据或未经清理的外部响应。

Integration 只报告事实结果或失败原因，不生成虚构状态、时间和价格。

Batch I 的 AP/ST Adapter 使用官方 `GET /shipping/v1/track` 契约，按 Provider/Mapping 分批且每批最多 10 个 ID，使用单进程 10 requests/minute guard，不自动重放失败的 GET。HTTP transport 强制 HTTPS、有界 connect/read timeout、响应体大小限制和严格 schema 验证。请求参数、认证、account number、tracking ID 与响应正文均从 `repr` 和异常链隐藏。Adapter 可注入 transport，测试不依赖外部网络。

## 5. 核心服务设计

### 5.1 Order Service

Order Service 是订单详情用例的编排入口：

1. 按订单号读取单笔订单；
2. 逐行解析 SKU，并从 SKU Repository 获取标准化商品；
3. 缺失 SKU 时返回明确的数据完整性错误，不静默跳过；
4. 调用 Pricing Service 计算商品行和订单金额；
5. 当前 Shipping Quote Integration 尚未实现，因此生成 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`、UTC `checked_at`、空 `quoted_fee` 和零值 `applied_fee`；
6. 将 `shipping_quote.applied_fee` 传入 Pricing Service，并校验其与 PricingResult shipment fee 一致；
7. 列表使用独立 `OrderSummaryResult`，不调用 Tracking/Quote Provider；详情按唯一 `tracking_group_id` 调用 Tracking Service 并组合 `TrackingResult`，每个唯一 Tracking Group 恰好一个结果；
8. Tracking 结果与 D-015 Shipping Quote 独立组合，任一 Tracking group/Provider 失败不覆盖、降级或阻断 Shipping Quote；没有已批准 Mapping/Release 时，每个 group 返回 D-031 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED`，不返回空数组、不调用外部 Provider；只有订单没有 Tracking Group 时才允许空数组。

### 5.2 Pricing Service

Pricing Service 应保持纯业务计算，输入为经过验证的 RRP、quantity 和 shipment fee，输出包含内部计算值与展示值。

冻结公式：

```text
Ex-GST Unit Price = RRP / Decimal('1.10')
Line Subtotal = (Ex-GST Unit Price × Quantity).quantize(Decimal('0.01'), ROUND_HALF_UP)
Order Subtotal = sum(Line Subtotal)
GST Amount = (Order Subtotal × Decimal('0.10')).quantize(Decimal('0.01'), ROUND_HALF_UP)
Shipment Fee = Shipment Fee.quantize(Decimal('0.01'), ROUND_HALF_UP)
Order Total = (Order Subtotal + GST Amount + Shipment Fee).quantize(Decimal('0.01'), ROUND_HALF_UP)
```

约束：

- 所有货币值从输入到输出都使用 `Decimal`，不得经过 `float`。
- 每个计算入口使用新建的独立 Decimal Context，不读取或修改调用者 Context；内部除法使用动态精度与明确的 `ROUND_HALF_EVEN`，调用者的 precision、rounding、flags 和 traps 不影响业务结果。
- 动态精度覆盖输入 Decimal 的系数位数与指数跨度、quantity 位数和订单明细累加位数，不对金额、数量或订单行数增加未经批准的业务上限；Python Decimal 运行时无法安全完成计算时返回独立的非敏感计算异常，不将其误报为非法金额。
- RRP 为 AUD 且已含 GST。
- Ex-GST Unit Price 不提前舍入，保留 Decimal 内部精度。
- 每个 Line Subtotal 独立按两位小数、`ROUND_HALF_UP` 舍入，Order Subtotal 只汇总这些已舍入行金额。
- GST Amount 在加入总额前按两位小数、`ROUND_HALF_UP` 舍入。
- Shipment Fee 在加入总额前按两位小数、`ROUND_HALF_UP` 标准化；Order Total 在求和后再次按两位小数、`ROUND_HALF_UP` 量化。
- 内部计算值与展示格式分离，但所有 API Money `amount` 都来自已经按冻结时点量化的 Decimal 值。
- 每笔订单单独计算，不复用或合并其他订单的中间值。
- Shipment Fee 无有效报价时使用明确的降级结果，并显示 `A$0.00`；必须同时保留“报价不可用”的状态与原因，不能只返回零金额。
- 商品 GST 继续只按 D-004 公式计算。按 D-022，Shipping Quote 仅使用具有 Provider/Product/合同证据的含 GST `total_cost`；所有必要单元精确聚合后，按 D-004 在订单级以 `ROUND_HALF_UP` 标准化为两位 `quoted_fee/applied_fee`。Provider 明确返回且全单元证据完整的 `shipping_gst` 仅作只读展示，不进入 Pricing 或订单总额；不得从 `total_cost` 或商品 GST 规则反推。缺少 GST 或精度证据时 fail closed 为 `unavailable`。
- 更新版 HTML v2 是当前实现依据，但仍是 `DRAFT FOR REVIEW`，并与原始 PDF 存在口径冲突；这不是正式批准声明。

### 5.3 Tracking Service

当前状态：**基础实现和离线合成测试已完成；真实 Configuration Release、Mapping Revision、账号、凭证与受控环境验证未提供**。

Tracking Service 负责将本地物流分组与外部追踪能力组合：

1. 从 Tracking Repository 读取 `tracking_group_id` 对应的 carrier 和 tracking number；Order Service 仅在详情流程调用 Tracking，列表不读取 Tracking Provider；
2. 通过请求开始时捕获的唯一 Active Configuration Release 和显式 Mapping Revision 选择 Integration client；Mapping 必须引用准确的 Provider/Account/Product Revision，carrier 展示文本、tracking number 形状、stable ID 或 latest version 不得作为版本选择依据；
3. Australia Post / StarTrack 是核心优先范围；
4. TNT 为 Bonus；适配器尚未实现时返回 `status="unsupported"`、`reason_code="CARRIER_NOT_IMPLEMENTED"`；
5. 对成功响应进行 schema 验证后再返回；
6. 对无凭证、超时、网络错误、认证失败或无效响应返回 `unavailable`；
7. 返回独立的 `TrackingResult`，包含 `status`、`reason_code`、`checked_at` 和追踪数据；
8. 不得编造追踪状态、事件、地点或更新时间。

当前实现还满足：一次订单请求固定一个只读 Configuration Release；按 Mapping Revision 隔离 Provider/Account 配置；相同 Provider/Mapping 的请求每批最多 10 个 ID；相同 tracking ID 在单请求内去重后将真实结果恢复到各 group；HTTP 200 单项失败不会取消同批其他 group；一个 Provider 失败不会取消另一个 Provider；有效空事件返回 `available + events=[]`；事件 description 不参与状态猜测；未知 raw status 原样保留并规范化为 `unknown`；AP/StarTrack 只使用各自状态表，TNT 与未识别 Provider 统一归一化为 `unknown`。

按 D-031，Mapping 预检失败不再作为订单级异常或空数组表达：没有 Active Release、没有适用 Mapping 或多个适用 Mapping 时，Tracking Service 为每个唯一 Tracking Group 生成 `provider=null`、`status=unavailable`、`reason_code=CARRIER_MAPPING_UNRESOLVED` 的结果，事件与 raw status 均为空，且在任何 Provider 请求之前短路。Domain 与 API 同时强制该组合是 `provider=null` 的唯一合法情形；已确定 Provider 但 Account/Product Revision 配置无效时保留具体 Provider 并使用现有配置错误 reason，不得归类为 Mapping Unresolved。默认 FastAPI 应用注入一个没有批准 Release 的 Tracking Service，因此可以安全启动和处理详情请求，不伪造 Mapping、账号、凭证或 Fake Adapter，也不会产生真实外呼。

五种 Revision ID（Provider、Account、Product、Mapping、Release）分别独立决定其完整不可变内容。Release 模型校验同一 ID 的两份不同内容，发布目录 `TrackingConfigurationCatalog` 在跨 Release 注册时同样拒绝同一 ID 的内容变化；相同内容可幂等读取。`(provider_revision_id, account_revision_id, product_revision_id)` 三元组不再承担完整性校验，Active Release 指针仍是唯一允许变化的激活引用。

追踪编号只通过 `tracking.json` 和 Repository 获取，不得散落硬编码在代码中。

按 D-016，Tracking Group 只作为订单内部物流关联，不是 Package ID，也不证明一个 group 对应一个实际包裹、shipment 或运费报价单元。Tracking Service 可以使用该关联查询轨迹，但 Shipping Quote 设计不得从它直接推导包装结构。

### 5.4 Package Estimation Service（Batch J1）

负责在**不调用任何 Provider**、**不计算运费**的前提下，按 D-019～D-021 从版本化 rules 估算 Package：

```text
OrderService.get_order()
  -> PackageEstimationService.estimate_for_order(order, products)
       -> PackagingRuleSetReader.get_active(checked_at)
       -> PackageEstimationService.estimate(order, products, ruleset)
            -> SkuPackagingSpec / PackageMaterialSpec 查询
            -> 顺序 first-fit 分配（packaged unit 体积 + 毛重）
            -> 数量守恒与 split 策略校验
            -> Package / PackageProvenance 构造
  -> PackageEstimationResult -> OrderDetailResult.packages
```

必须遵守：

- **禁止把商品数据当包装数据**：`weight_g`、`dimensions_mm`、`volume_mm3`、`volumetric_gross_weight_kg`、`max_storage_per_container` 一律不参与 Package 尺寸、包装重量、容量或计费重量；包装事实只来自 ruleset（D-019、契约 §4.4）。`products` 只用于 SKU 关联一致性校验。
- **数量守恒**（D-020）：每个 OrderItem 在所有 PackageItem 中的分配数量之和必须严格等于原数量；不允许零/负数量、超分配、遗漏、重复分配、引用不存在的订单行或跨订单混入。违者返回 `unavailable`，不返回部分 Package 集合。
- **Domain 独立校验，不信任 Service**：`OrderDetailResult` 自身强制 `packages == package_estimation.packages`、每个 Package 属于本次订单、`order_item_ref.line_index` 必须存在、SKU 必须与被引用订单行一致、逐行数量必须守恒；估算为 `unavailable` 时禁止携带任何 Package。Service 内部的守恒检查只是第一道，Domain 必须能独立拒绝被篡改的投影。
- `package_estimation` 是详情的**必填**结果（契约 §4.1：每次详情都会产生一次估算结果），不存在"详情无估算结果"的中间状态。
- **纵深防御**：即使 ruleset/policy 校验被绕过（例如 `model_construct`），Service 仍拒绝非 synthetic ruleset 与非 synthetic policy，并对成功结果要求显式 `synthetic_ruleset` 标记；API 与前端还交叉校验 Package ruleset 必须与估算 ruleset 一致、Package item 必须引用本订单。
- **可追溯**（D-021）：每个 rules Package 记录 `ruleset_id`、`ruleset_version`、`source_revision`，并在 `PackageProvenance.input_fingerprint` 中保存不含 PII 的不可逆输入指纹。
- **确定性**：同一规范化输入与同一 ruleset version 必须得到相同 Package 结果；Package ID 在订单内唯一且按创建顺序稳定编号。
- **fail closed**：无 Active Ruleset → `PACKAGE_RULES_NOT_CONFIGURED`；SKU 规格、材料、容量或策略不足 → `PACKAGE_DATA_INCOMPLETE`。公共 reason code 仅这两个，更细原因只存在于内部 `PackageEstimationDiagnostic`。
- 估算失败不得抛到订单详情请求，也不得影响 Tracking、D-015 Shipping Quote 或 Pricing；OrderService 只组合结果。

#### Synthetic-only 边界

Batch J1 时没有经批准的生产包装规则，DEC-1（`PackingPolicy` 完整字段 schema）、DEC-2（方向/易碎/堆叠/危险品约束位置）、DEC-3（生产级装箱算法）、DEC-4（材料选择策略）当时均未批准。**Task 048 更新**：DEC-1～DEC-4 已获批准并形成 D-032～D-035（契约见 `docs/PHASE6_CONTRACT.md` §5.4～§5.8），但**实现尚未开始**（Batch J2 Implementation `NOT_STARTED`）、真实包装数据仍然缺失，因此下列 J1 代码现状继续有效：

- `PackingPolicy` 只是**刻意最小**的 synthetic 形态，没有 match criteria、没有方向/危险品路由（D-032 的正式 schema 属 J2-B 实现范围）；
- `PackagingRuleSet.synthetic_only` 类型为 `Literal[True]`，非 synthetic ruleset 无法构造，从结构上防止合成规则混入生产行为；该隔离在 J2 中不得放宽，生产 ruleset 必须使用独立的「已批准生产 ruleset」门禁；
- 分配策略是"packaged unit 体积 + 毛重"的顺序 first-fit，**不是**生产级三维装箱算法（生产算法为 D-034 的 Best-Fit Decreasing，属 J2-C 实现范围）；
- 合成 fixtures 只存在于 `backend/tests/packaging_fixtures.py`，`backend.main` 从不导入；
- 默认应用注入 `StaticPackagingRuleSetReader(None)`，因此每个订单详情返回 `unavailable / PACKAGE_RULES_NOT_CONFIGURED` 且 `packages=[]`，不会静默使用 synthetic fixtures。

### 5.5 Shipping Service

Shipping Service 负责获得和解释运费报价，而不是物流轨迹：

- 按单笔订单处理，不跨客户合并；
- 保留物流分组关联，但不把 Tracking Group 直接当作 Package ID 或报价单元；
- 按 D-019 使用可配置、可追溯、可测试的 SKU 包装规格映射和确定性装箱规则估算 Package；真实装箱数据可用时优先使用真实数据；
- SKU 重量、尺寸和体积只作为规则输入；数据不足以可靠生成 Package 时返回 `unavailable`，不得猜测包裹数量、包装材料重量或计费重量；
- 将承运商报价转换为 AUD `Decimal`；
- 已实现的报价适配器发生外部失败或返回无效报价时使用 `unavailable`；适配器尚未实现时使用 `unsupported`；
- 返回独立的 `ShippingQuoteResult`，包含 `status`、`reason_code`、`checked_at`、`quoted_fee`、`applied_fee` 和报价数据；
- 有效报价使用 `quoted_fee`，并将按冻结金额规则标准化后的费用写入 `applied_fee`；
- 无有效报价时 `quoted_fee=null`，`applied_fee` 的金额为 `0.00`，状态保持 `unavailable` 或 `unsupported`，同时携带非虚构的限制说明；
- 按 D-018，订单报价采用 all-or-nothing：任一必要报价单元失败时，订单级 `unavailable`、`quoted_fee=null`、`applied_fee=0.00`；部分成功金额不得作为完整订单运费；
- 按 D-020 允许 OrderItem 跨 Package 分配及 Package 多 SKU 混装，但由 D-021 版本化 ruleset 控制，且必须数量守恒；
- 按 D-022 使用 Provider/Product 明确确认的含 GST `total_cost` 作为成功报价的 `quoted_fee/applied_fee`，`shipping_gst` 只读且不得重复相加；
- 按 D-023/D-027 显式选择 Provider、Account 与 Contract Product，禁止切换到 PAC 或其他隐式 fallback；
- 按 D-024 保持公共 reason code 稳定，Provider 原始诊断只在内部可见；
- 按 D-026 不持久化历史报价、不做跨请求缓存；按 D-029 遵循明确 Provider/Product 精度规则，缺少规则即 unavailable；
- 在任何 Provider 网络调用前完成 Package、Quote Unit、Active Configuration Release、Mapping/Provider/Account/Product Revision、Adapter capability、Contract Product、GST 和精度证据预检；必要 Adapter 尚未实现时为 `unsupported / CARRIER_NOT_IMPLEMENTED`，已实现但配置不可用时为 `unavailable`，且不得发出部分请求；
- Provider 原始金额、单元 validated Decimal 和订单级 exact aggregate 仅作内部证据；D-004 `ROUND_HALF_UP` 只在全部必要单元精确聚合后的订单级 Shipment Fee 边界使用，形成相等的两位 `quoted_fee/applied_fee`；
- 在项目 README 中记录降级原因与限制。

Tracking Group/Package、Package cardinality、规则版本、报价聚合、Contract Product、GST、reason code、lifecycle、Provider 精度和列表金额边界已由 D-016～D-030 冻结。具体装箱参数、Revision/Release 内容、治理权限、账号映射值、Provider cubing/rounding 证据仍是实施输入，不得自行假设。API 边界输出的 `applied_fee` 必须遵守两位小数 Money 契约。

当前初始能力不是已实现的 Shipping Service：Order Service 仅按 D-015 生成明确的 unsupported 结果，不调用承运商或构造报价。`checked_at` 是系统评估能力状态的 UTC 时间，不是承运商报价时间；`quoted_fee=null` 表示没有有效报价，`applied_fee=0.00` 仅用于订单总额降级计算，绝不表示免费运输。

### 5.6 统一状态与结果独立性

状态语义冻结为：

- `available`：功能已实现，本次查询成功且结果通过验证；
- `unavailable`：功能或适配器已实现，但本次因超时、认证、网络、限流、无效响应或其他查询错误而失败；
- `unsupported`：功能或适配器尚未实现。

Tracking 与 Shipping Quote 分别产生独立结果。Tracking 失败不得导致 Shipping Quote 失败；Shipping Quote 失败也不得覆盖已经成功获得的 Tracking 数据。Order Service 只负责组合两个结果，不把一个结果的 `unavailable` 或 `unsupported` 传播给另一个结果。

`checked_at` 表示系统执行本次检查的时间，不等同于承运商事件时间或报价生成时间，不得用它填充或伪造外部更新时间。

D-025 的 `not_requested` 是 Quote 调用状态而不是第四种 Provider 结果状态。订单列表不调用 Quote Provider；订单详情进入评价流程后，结果仍严格使用上述 `available | unavailable | unsupported`。

`CONFIRMED`（D-031）：Tracking 的 `provider` 字段条件可空，但只有 `status=unavailable` 且 `reason_code=CARRIER_MAPPING_UNRESOLVED` 时允许为 null；该结果是真实 `unavailable`，不得显示为 `not_requested`、`unsupported` 或免费/无物流需求。其他所有 Tracking 结果必须具有具体 Provider。`tracking_results=[]` 只表示订单没有唯一 Tracking Group。

Package Estimation 是第三个独立结果，与 Tracking、Shipping Quote 并列：它的 `available | unavailable` 只影响包装区域，不得改变 Tracking 结果、D-015 报价状态或 Pricing 金额。Batch J1 的 `PackageReasonCode` 只有 `PACKAGE_RULES_NOT_CONFIGURED` 与 `PACKAGE_DATA_INCOMPLETE` 两个公共值，未新增 D-024 枚举以外的公共 code。

## 6. 数据模型边界

Phase 2 与 Phase 3 已按职责实现以下模型边界：

- 数据源模型：与三个运行时 JSON 文件及其 envelope 对应，仅用于 Repository 输入边界；字符串数值在此解析为 `Decimal`，并校验日期、quantity、描述状态和 ETA 一致性；
- 领域模型：已实现不可变的 `Order`、`OrderItem`、`Product`、`Dimensions`、`Customer`、`ShippingAddress`、`TrackingGroup`、`LinePricingResult`、`PricingResult`、`OrderResultItem`、`ShippingQuoteResult`、`OrderSummaryResult`、`OrderDetailResult`、`TrackingResult`、`TrackingEvent` 与 Provider/Account/Product/Mapping/Release Revision 配置模型；Batch J1 又新增 `Package`、`PackageItem`、`PackageItemReference`、`PackageDimensions`、`PackageWeight`、`PackageProvenance`、`PackageEstimationResult`、`PackageEstimationDiagnostic` 与 `PackagingRuleSet`/`SkuPackagingSpec`/`PackageMaterialSpec`/`PackingPolicy`；所有十进制字段只接受有限、非负 `Decimal`，quantity 为严格正整数；尺寸统一 `_mm`/`_mm3`、重量统一 `_g`，Provider 派生重量用 `_kg` 且缺证据时为 null；
- Integration 模型：已实现 AP/ST Track Items Adapter 的请求/响应边界模型、注入式 HTTP transport、凭证解析和内部安全诊断；
- API schema：已实现 Health、订单列表、订单详情、Money、Tracking、Package、成功 envelope 与统一错误响应；API schema 不复用 Source Model 或 Domain Model；
- `PricingResult` 与订单业务结果已在 Phase 3 实现；Money API schema 与 D-015 初始 ShippingQuoteResult 已在 Phase 4 实现；Batch I 已实现 `TrackingResult`、D-031 条件 nullable Provider 投影和协调 API/Frontend；Batch J1 已实现 `PackageEstimationResponse`/`PackageResponse` 投影（尺寸与重量以十进制字符串输出，避免二进制浮点）；真实 Shipping Quote Integration 仍未实现，D-012 与 D-013 的独立状态语义保持冻结。

不同边界的模型不得为了省事完全复用。尤其不能把含凭证、完整外部响应或内部文件字段的模型直接暴露给前端。

Source Model 的列表在验证时转换为 tuple；`tracking.json` 的根字典在校验后转换为只读映射。Repository 只向外返回不可变 Domain Model 和 tuple，避免缓存数据被调用方意外修改。

### 6.1 Money API 契约

所有 API 金额统一使用以下结构：

```json
{"amount":"123.45","currency":"AUD"}
```

- `amount` 是恰好两位小数的十进制字符串；
- `currency` 固定为 `AUD`；
- Pydantic 内部字段使用 `Decimal`，通过显式 serializer 输出该 JSON 结构；
- 所有数值为零的 Decimal（包括负零和不同指数表示）统一序列化为 `"0.00"`；
- 序列化过程不得经过 `float`；
- TypeScript 将 `amount` 定义为 `string`，不得转换为 JavaScript `number`；
- 前端不得重新计算订单金额，只为 `amount` 添加 `A$` 展示前缀。

### 6.2 Tracking 与 Shipping API 契约

`TrackingResult` 与 `ShippingQuoteResult` 均必须包含：

- `status`：`available | unavailable | unsupported`；
- `reason_code`：成功时可为空，失败或未实现时为稳定、非敏感的原因码；
- `checked_at`：系统本次检查时间；
- 各自独立的数据字段。

`ShippingQuoteResult` 额外包含：

- `quoted_fee`：有效承运商报价对应的 Money；无有效报价时为 `null`；
- `applied_fee`：进入订单总额的 Money；无有效报价时为 `{"amount":"0.00","currency":"AUD"}`；
- `shipping_gst`：仅由完整 Provider 原始 GST 证据聚合的只读 Money；证据不完整、unavailable 或 unsupported 时为 `null`，不得反推或进入 Pricing。

无有效报价时，零值只用于冻结规则允许的订单总额降级，不改变 `unavailable` 或 `unsupported` 状态，也不得表达为免费运输。

真实能力已实现但本次失败时按 D-017 使用 `unavailable`、独立 reason code、`quoted_fee=null` 和零值 `applied_fee`；不得复用 D-015 的 `SHIPPING_QUOTE_NOT_IMPLEMENTED`。多个必要报价单元部分失败时按 D-018 对订单级结果执行同一零值降级，部分成功金额不得进入 Order Total。

当前固定返回 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`。`checked_at` 必须为运行时 UTC aware datetime；API Mapper 将 Domain Decimal 包装为 Money，但不计算或改变报价状态。详情的 `shipping_quote.applied_fee` 是 API 唯一运费金额来源，列表通过状态和 reason code 明确零运费只是降级值。

Phase 6 Batch I 已协调发布该边界：`OrderService.list_orders()` 返回独立 `OrderSummaryResult`，不得调用详情流程、Package Estimation、Tracking 或 Quote Provider；API 返回 `quote_request_state=not_requested`、null status/reason，不返回 Quote 金额或 `checked_at`。按 D-030，列表 `order_total = order_subtotal + gst_amount`，UI 表达为 `Total before shipping` 并说明 `Shipping quote not requested`；内部 Decimal `0.00` 不是 Quote applied fee、fallback 或免费运输，Domain 层强制该公式、零 `shipment_fee` 与 Decimal-only 金额。`get_order()` 返回 `OrderDetailResult`，使用 `quote_request_state=requested` 并包含必填 ShippingQuoteResult；详情的 `shipping_quote.applied_fee` 必须等于 `pricing.shipment_fee`，详情金额继续按实际 applied fee 计算，不套用列表公式。列表与详情金额允许且预期不同。

### 6.3 Phase 6 Contract Gate

`docs/PHASE6_CONTRACT.md` 是 Phase 6 后续实施的冻结业务契约。D-020～D-029 已批准原 OD-01～OD-10，D-030 已批准列表金额语义，D-031 已批准 Tracking Mapping 失败的公开投影，并冻结以下分层：

- Package Estimation 负责从真实装箱数据或版本化 rules 生成独立 Package，不读取 Tracking 事件；
- Shipping Quote Service 负责必要报价单元、D-018 all-or-nothing 和 D-017 zero fallback，不解释 Provider 原始 payload；
- Provider Configuration Readers/Registry 独立管理 Provider、Account、Product、Mapping 的不可变 Revision；Mapping Revision 显式引用目标 Revision，由唯一 Active Configuration Release 决定性解析；Shipping Quote 不依赖 Tracking Repository 推导 Provider；
- Quote/Tracking Provider 只负责认证、请求映射、外部调用、响应验证和分类错误；
- Order Service 只组合独立 Tracking、Shipping Quote 与 Pricing 结果；Pricing Service 继续只接收 `applied_fee`；
- API Mapper 只投影已验证结果，不公开内部 unit diagnostics、规则内部细节、凭证或原始 Provider 响应。

Configuration Release 是配置版本选择的唯一入口：每个 environment/configuration scope 只有一个 Active Release，切换和 rollback 必须原子完成。一次订单请求只在开始时捕获 Release 并固定所有 Mapping/Provider/Account/Product Revision；切换或 rollback 不影响在途请求，新请求才使用新 Release。Rollback 只重新激活先前已批准的不可变 Release，不修改历史 Revision。配置 Release 和审计属于配置治理，不属于 Quote History 或跨请求 Quote Cache。

Task 030 Decision Approval 已冻结 Package cardinality、只读版本化 rules、freight GST application、Provider mapping、reason code、detail-only Quote、无 history/cache、Contract Price、Tracking status 和 Decimal precision。Task 032 已补齐第一轮技术契约；Task 034 新增 D-030，并补齐不可变 Revision、Configuration Release、原子 activation/rollback、请求级 pinning 和在途请求边界。Task 037～040 完成 Batch I Tracking 基础；Task 041 独立审查为 `FAIL`（1 High、2 Medium、1 Low）；Task 042 新增 D-031，并完成 Mapping Unresolved 全链路投影、五种 Revision ID 独立不可变、D-030 Summary 金额不变量和 Provider 状态映射分支整改。Contract Checkpoint `30544ad226bae79795c47028383a99e16581646b` 为 Batch I 实施基线。

**后续状态（Task 043～048）**：Task 043 独立复审 `BATCH_I_REVIEW_PASS` 并创建 Checkpoint `6ccdc5f`；Task 045/046 完成 Batch J1 并创建 Checkpoint `3c3675e`；Task 048 依用户批准把 DEC-1～DEC-4 正式化为 D-032～D-035，Batch J2 Contract `COMPLETE`、Batch J2 Implementation `NOT_STARTED`（下一入口 Task 049），DEC-5（Packaging 配置治理）与 DEC-6（多进程限流）仍 `DEFERRED / NOT_APPROVED`。Batch I 离线实现已冻结、真实配置与真实 Provider 验证仍 `BLOCKED`，Phase 6 仍为 `IN_PROGRESS`。

## 7. 数据流与订单处理流程

### 7.0 当前 Phase 2/3 数据读取、校验与业务计算链路

```text
orders.json / skus.json / tracking.json
    -> 集中 JSON loader（UTF-8、JSON、重复 key）
    -> Pydantic Source Models（结构、类型、缺失状态）
    -> 各文件 Repository（Source -> Domain）
    -> RepositoryCollection（SKU / tracking group 引用完整性）
    -> 不可变 Domain Models
    -> Order Service（单笔订单与商品关联）
    -> Pricing Service（逐行舍入、汇总、GST、运费与总额）
    -> 不可变 OrderResult / PricingResult
```

`skus_raw.json` 只用于独立数据质量与溯源检查，不进入上述运行时链路。

### 7.1 订单详情与价格

```text
Frontend 请求单笔订单
    -> API 校验订单号
    -> Order Service
        -> Order Repository 读取订单
        -> SKU Repository 为每个订单行匹配商品
        -> Pricing Service 按 Decimal 规则逐行计算
        -> 保留每行 tracking_group_id，供后续 Tracking Service 使用
    -> API schema 序列化
    -> Frontend 展示订单、金额和缺失数据状态
```

关键验证：

- 订单存在；
- 订单号唯一；
- quantity 为正整数；
- 每个 SKU 唯一且存在；
- 每个 tracking group 存在；
- 金额字符串能无损解析为 Decimal。

### 7.2 物流追踪

```text
Frontend 请求物流状态
    -> API
    -> Tracking Service
        -> Tracking Repository 获取 carrier/tracking number
        -> 捕获 Active Configuration Release 并按精确 Mapping Revision 预检
        -> （Mapping 不可解析：直接产生 D-031 provider-null unavailable，零 Provider 请求）
        -> 对应 Carrier Integration
        -> 验证并转换外部响应
    -> available / unavailable（含每组一个结果）
    -> Frontend 按真实状态、Mapping unresolved 或降级状态展示
```

### 7.3 包装估算（Batch J1 已实现）

```text
Frontend 请求订单详情
    -> API
    -> Order Service
        -> Package Estimation Service
            -> Packaging Rules Reader（无 Active Ruleset 时 fail closed）
            -> 校验订单行与商品关联
            -> 逐行查找 SkuPackagingSpec / 兼容材料
            -> 顺序 first-fit 分配（packed unit 体积 + 毛重）
            -> 数量守恒 / split 策略校验
            -> 构造 Package + PackageProvenance（ruleset、source_revision、fingerprint）
        -> PackageEstimationResult（available + packages，或 unavailable + 稳定 reason）
    -> Order Detail Response 中的 package_estimation
    -> Frontend 展示 Package 卡片 / 规则未配置 / 数据不完整，并标注 synthetic 规则
```

该链路不读取 Tracking Repository、不访问 Integration Layer、不计算运费；Package 数量不由 Tracking Group 数量、订单行数或商品总体积直接决定。

### 7.4 运费估算

```text
Frontend 请求运费
    -> API
    -> Shipping Service
        -> Order/SKU Repositories + Packaging Rules Reader
        -> 按已确认的规则估算 Package（不读取 Tracking Repository）
        -> 捕获 Active Configuration Release
        -> Mapping Reader 以精确 Revision 形成必要 Quote Unit
        -> Capability Preflight（Adapter、Account、Product、GST、精度；失败时零网络调用）
        -> Carrier Integration 获取报价
        -> 精确 Decimal 聚合并按 D-004 形成两位 applied fee，或生成 unsupported/unavailable 降级结果
    -> Pricing Service 将 Shipment Fee 加入订单总额
    -> Frontend 展示报价来源，或 A$0.00 + 限制说明
```

## 8. 外部物流 API 集成边界

- 所有外部调用只能发生在 Integration Layer。
- API 凭证只能来自后端环境变量。
- 前端不得持有、传递或看到承运商凭证。
- Integration client 必须具有显式 timeout。
- 外部响应必须验证后才能进入领域层。
- 单元测试使用 fake/stub client，不要求真实 API 可用。
- 真实 API 的 base URL、认证方式、sandbox、配额和重试策略未确认前，不写入假设值。
- 当前不引入消息队列、缓存或后台任务系统。若同步请求无法满足已确认的 API 限制，应新增决策记录后再调整架构。

## 9. 异常处理与降级策略

| 场景 | 后端行为 | 前端行为 |
|---|---|---|
| JSON 无法解析 | 返回配置/数据源错误并记录非敏感诊断 | 展示暂时无法加载 |
| 订单不存在 | 返回明确的 not-found 结果 | 展示订单不存在 |
| SKU 引用缺失 | 返回数据完整性错误，不跳过订单行 | 展示数据暂不可用 |
| 物流分组缺失 | 返回数据完整性错误 | 不显示虚构物流信息 |
| 商品描述缺失 | 保留 `null`/缺失状态 | 显示中性缺失提示 |
| ETA 缺失或异常 | 保留不可用状态 | 显示 ETA unavailable |
| 已实现的外部 API 超时/失败 | 对受影响的独立结果返回 `unavailable` 和非敏感原因 | 只降级对应的 Tracking 或 Shipping Quote 区域 |
| Tracking Mapping 无法解析 | 每个唯一 Tracking Group 返回 D-031 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED`，零 Provider 请求 | 显示 `Tracking unavailable — carrier mapping could not be resolved`，不显示为 not requested |
| 订单没有唯一 Tracking Group | `tracking_results=[]` | 明确说明没有可查询的 Tracking Group |
| 包装规则未配置 | `package_estimation` 返回 `unavailable / PACKAGE_RULES_NOT_CONFIGURED`，`packages=[]` | 显示"包装规则未配置"，不构造任何 Package |
| 包装数据不完整或违反容量/拆分策略 | `unavailable / PACKAGE_DATA_INCOMPLETE`，`packages=[]` | 显示"包装数据不完整"，不展示推测尺寸/重量 |
| 包装估算发生意外错误 | 该能力单独降级为 `unavailable / PACKAGE_DATA_INCOMPLETE`；订单详情仍 200，Tracking 与 Pricing 不受影响 | 只降级包装区域 |
| 合成包装规则被使用 | `synthetic_ruleset=true` | 明确标注"合成测试规则，非真实包装数据" |
| 外部响应无效 | 拒绝该响应并返回 `unavailable` | 不展示未验证内容 |
| 无有效运费报价 | `quoted_fee=null`，`applied_fee` 为 A$0.00，并保留 `unavailable` 或 `unsupported` | 同时展示 A$0.00、状态和限制说明 |
| TNT 未实现 | 返回 `unsupported` 和 `CARRIER_NOT_IMPLEMENTED` | 清晰提示功能未实现，不伪造结果 |

日志不得包含客户手机号、邮箱、地址、API 凭证或完整未经清理的外部响应。

## 10. 非目标

当前明确不做：

- 微服务拆分；
- 数据库和 ORM；
- Redis 或分布式缓存；
- 消息队列、事件总线或异步工作流平台；
- 为未来规模预建的复杂基础设施；
- 真实商品图片抓取；
- 未经确认的 TNT 核心交付承诺。

## 11. Open Questions and Implementation Inputs

- HTML v2 GST 规则何时、由谁正式确认？
- 原始 PDF 的第二笔订单编号冲突应如何在最终交付物中展示？
- 实际 Provider/Account/Contract Product/Mapping Revision、获批准 Configuration Release、治理权限、认证配置、sandbox 权限和调用参数是什么？
- D-021 ruleset 的具体 SKU specs、材料、capacity、tare、orientation 和确定性装箱算法是什么？
- 各 Provider/Product 的体积/计费重量、输入精度、舍入和 GST 口径由哪些官方文档或合同证明？
- `0Days` ETA 表示现货、当日发货还是源数据异常？
- TNT Bonus 的最终验收边界是什么？
