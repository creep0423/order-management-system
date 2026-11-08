# Order Management System 项目计划

## 1. 项目状态概览

- 项目：Order Management System
- 当前里程碑：**Phase 6 Batch J2 契约已冻结（D-032～D-035）/ 真实包装数据未验证**
- 下一入口：**Task 049 — Batch J2 Production Packaging Implementation**
- 架构：Modular Monolith
- 当前数据源：JSON files
- 当前数据基线：2 orders、9 SKUs、9 order lines、31 units、3 tracking groups

### Phase 状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 0 | COMPLETE | 需求、数据、文档与架构基线 |
| Phase 0.1 | COMPLETE | 初始需求和题目材料确认 |
| Phase 0.2 | COMPLETE | 订单、SKU 与物流数据准备 |
| Phase 0.3 | COMPLETE | JSON 解析、统计、引用完整性和数据质量只读审查 |
| Phase 0.4 | COMPLETE | 项目规范、架构、技术决策、两轮文档审查及 API 契约冻结 |
| Phase 1 | COMPLETE | 项目初始化 |
| Phase 2 | COMPLETE | 后端数据层和领域模型 |
| Phase 3 | COMPLETE | 价格计算和订单业务服务 |
| Phase 4 | COMPLETE | FastAPI 接口开发 |
| Phase 5 | COMPLETE | React 前端开发：只读订单列表、搜索筛选、订单详情、金额拆分、Shipping Quote 降级状态及错误恢复 |
| Phase 6 | IN_PROGRESS | Batch I Tracking 已 Checkpoint `6ccdc5f`（`PARTIALLY_COMPLETE`，真实 Provider 验证 BLOCKED）；Batch J1 Package Estimation 已独立复审通过并 Checkpoint `3c3675e`（`COMPLETE`，synthetic-only）；Batch J2 契约已冻结（Task 048：DEC-1～DEC-4 → D-032～D-035，`BATCH_J2_CONTRACT: COMPLETE`）；Batch J2 实施与 Batch K 未开始；DEC-5/DEC-6 `DEFERRED`；真实配置/Provider/包装数据验证仍 BLOCKED |
| Phase 7 | NOT_STARTED | 测试、优化和最终交付 |

Phase 0 至 Phase 5 已完成并关闭。Phase 6 已进入 Batch I，实现状态与生产可用性必须分开记录；Phase 7 尚未开始。

## 2. Phase 0：需求确认和数据准备

### 开发目标

建立可追溯的需求、数据和架构基线，在创建业务代码前明确冻结规则、已知冲突、安全边界与未决问题。

### 主要任务

- Phase 0.1：确认订单详情、物流追踪和运费估算的目标范围；
- Phase 0.2：准备订单、原始 SKU、标准化 SKU 和物流映射数据；
- Phase 0.3：验证 JSON 可解析性、数量统计、SKU 匹配、物流引用和数据质量；
- Phase 0.4：建立 `AGENTS.md`、架构文档、决策记录和完整项目计划；
- 记录 HTML v2 与原始 PDF 的 GST 口径冲突；
- 记录第二笔订单编号冲突；
- 将未知事项标为 Open Question，不补造业务数据。

### 交付物

- `backend/data/orders.json`
- `backend/data/skus_raw.json`
- `backend/data/skus.json`
- `backend/data/tracking.json`
- `DATA_QUALITY_REPORT.md`
- `README_PHASE0.md`
- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/PROJECT_PLAN.md`

### Phase 0.4 最终交付成果

- `AGENTS.md`：项目协作规范、冻结业务规则、数据与安全边界、开发及 Codex 工作流程；
- `docs/ARCHITECTURE.md`：模块化单体、分层职责、Pricing/Tracking/Shipping 设计、数据流及降级边界；
- `docs/DECISIONS.md`：D-001 至 D-013 技术与业务决策记录；
- `docs/PROJECT_PLAN.md`：Phase 0 至 Phase 7 的目标、任务、交付物、验收标准、依赖和阶段状态。

### 验收标准

- 4 个 JSON 文件均可解析；
- 数据统计为 2 orders、9 unique SKUs、9 order lines、31 units、3 tracking groups；
- SKU 和 tracking group 引用闭合；
- 已知缺失描述、异常 ETA 和截断描述得到记录且未被编造修复；
- 19 条冻结业务规则进入项目规范和架构边界；
- D-001 至 D-013 完整记录内容、原因、影响、状态和未决问题；
- Decimal 金额计算与舍入链路已冻结：Ex-GST Unit Price 不提前舍入，Line Subtotal、GST Amount、Shipment Fee 和 Order Total 按指定时点使用 `ROUND_HALF_UP` 量化；
- Money API 已冻结为两位小数 Decimal String 与固定 `AUD`，Pydantic 显式序列化且前端保持 string、不重新计算金额；
- TrackingResult 与 ShippingQuoteResult 已冻结为独立状态，一方失败不传播到另一方；
- `available`、`unavailable`、`unsupported` 状态语义以及 TNT 未实现时的 `CARRIER_NOT_IMPLEMENTED` 已冻结；
- HTML v2 GST 规则及其 `DRAFT FOR REVIEW` caveat、原始 PDF GST 口径冲突均已记录且未声称正式获批；
- 第二笔订单采用 `PO-20251203-00046`，同时保留原始 PDF 订单编号冲突记录；
- 客户数据日志保护、公开仓库前脱敏、后端环境变量凭证管理、`.env` 排除和前端禁用凭证均已形成规范；
- 未解决事项继续保留在 Open Questions，不因 Phase 0.4 完成而视为已解决；
- 规划不引入微服务、消息队列、Redis 或数据库；
- Phase 0.4 文档初始化、两轮只读审查及 Codex Task 004 修订已完成，Phase 0 已整体关闭。

### 前置依赖

- 已提供的更新版 HTML v2 需求；
- 原始 PDF 冲突记录；
- 当前 JSON 数据包；
- 用户确认的冻结业务规则。

## 3. Phase 1：项目初始化

### 子阶段状态

| 子阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.1 | COMPLETE | Git Repository Initialization & Security |
| Phase 1.2 | COMPLETE | FastAPI Backend Initialization |
| Phase 1.3 | COMPLETE | React Frontend Initialization |
| Phase 1.4 | COMPLETE | Frontend-Backend Integration |
| Phase 1.5 | COMPLETE | Project Integration & Final Acceptance |

### Phase 1 最终交付成果

- 建立本地 Git 安全基线与敏感文件忽略规则，业务 JSON 保持未提交且可验证；
- 建立 Python 3.13、FastAPI、Pydantic、pytest 与 Ruff 后端工程，提供经过 schema 验证的 `GET /health`；
- 建立 React、TypeScript strict、Vite 与 Oxlint 前端工程，生产构建包含 `tsc -b` 类型检查；
- 配置仅允许 `http://localhost:5173` 与 `http://127.0.0.1:5173` 的最小 CORS 边界；
- 建立原生 fetch API Service、健康响应验证与支持请求取消的 `checking`、`connected`、`disconnected` 状态 Hook；
- 后端 pytest、Ruff、格式检查、pip check，以及前端生产构建和 lint 均通过；
- 未实现 Phase 2 之后的订单、商品、Pricing、Tracking 或 Shipping 业务，未引入数据库、Redis、消息队列或微服务。

### Phase 1.5 最终验收证据

- Codex 自动化验收：后端健康接口、OpenAPI、CORS、前端页面、实际前端 Health Service 在线请求及后端关闭失败路径均通过；
- 用户提供的人工浏览器验收证据：用户报告后端启动时页面显示 `connected`、后端关闭时显示 `disconnected`、后端恢复后再次显示 `connected`，三个场景全部通过；
- 上述浏览器结果由用户提供，Codex 未声称自行完成真实浏览器验证。

### 开发目标

创建最小、可运行、可测试的 Python/FastAPI 后端与 React/TypeScript/Vite 前端骨架，不提前实现业务功能。

### 主要任务

- 确认 Python 3.13 与 Node.js/npm 的可用版本；
- 初始化后端包结构和测试结构；
- 初始化 React + TypeScript + Vite 前端；
- 建立最小配置加载、开发命令和基础健康检查；
- 建立 `.gitignore`，确保 `.env`、缓存和构建产物不进入版本控制；
- 提供不含真实凭证的环境变量说明；
- 建立格式化、静态检查和测试命令，具体工具需在实施前确认。

### 交付物

- 可启动的最小 FastAPI 应用；
- 可启动的最小 React 应用；
- 后端与前端目录结构；
- 基础测试与开发说明；
- 安全的环境变量示例或配置说明（不含真实值）。

### 验收标准

- 后端和前端分别能够在本地启动；
- 后端最小健康检查通过；
- 前端最小页面可加载；
- 测试命令可运行且基础测试通过；
- 未实现或复制 Phase 2 以后的业务逻辑；
- 未提交 `.env`、凭证或客户数据日志。

### 前置依赖

- Phase 0 完成并获得确认；
- 确认允许安装的依赖和包管理工具；
- 确认运行环境与端口约定。

## 4. Phase 2：后端数据层和领域模型

### Phase 2 最终交付成果

- 建立与 JSON envelope 对应的严格 Pydantic 2 数据源模型，以及与 API schema 分离的不可变领域模型；
- 使用 `Decimal` 解析 RRP、重量、尺寸、体积等十进制字符串，并拒绝 `float`、非有限值和非法格式；
- 建立只读 Order、Product/SKU、Tracking Repository，以及统一的 `RepositoryCollection` 数据访问入口；
- 集中处理 UTF-8 JSON 加载、文件缺失、JSON 解析、Pydantic 校验、重复标识和悬空引用错误；
- Repository 以模块路径定位数据并在初始化时缓存，不依赖当前工作目录，不读取或修改 `skus_raw.json`；
- 保留描述缺失、截断描述状态、`nullDays` 和 `0Days` 的真实语义边界，未引入默认值或业务解释；
- 使用安全合成 fixture 完成模型与 Repository 单元测试，并对本地四个 JSON 完成只读集成验证。

### Phase 2 独立代码审查修复

- Domain Model 的 Decimal 字段改为严格、有限、非负 `Decimal`，订单数量改为严格正整数，拒绝隐式类型转换；
- 标准化商品描述拒绝原始缺失标记 `"."`、空字符串和纯空白，继续严格区分 `available`、`missing` 与 `partial_needs_requery`；
- `DataValidationError` 基于 Pydantic 结构化 errors 提供脱敏的 source、record、field 和 error type，不公开 input、ctx、msg 或原始异常；
- `tracking.json` Source 根映射转换为只读映射，Repository 返回 tuple 与不可变嵌套 Domain Model；
- 使用受控文件访问 Mock 证明 Repository 运行时只读取 `orders.json`、`skus.json` 和 `tracking.json`，不依赖 `skus_raw.json`；
- 更新 `AGENTS.md` 与 `docs/ARCHITECTURE.md` 的当前阶段、实际目录、模型职责、Repository 链路和 Phase 3 开发入口；冻结业务规则与决策记录未改变。
- 对 Customer、ShippingAddress、Order 及对应 Source Model 的敏感字段，以及 Tracking Domain/Source 的追踪编号设置 repr 隐藏；`model_dump` 与 Repository 转换仍保留完整字段；
- 为保持 `MappingProxyType` 的 `TrackingFileSource` 增加显式 root serializer，恢复普通字典 dump、JSON 序列化和 round-trip，并保证序列化副本与内部只读映射隔离。

### Phase 2 最终验收证据

- pytest：92 passed；其中 Health API 与 CORS 既有回归测试 8 passed；
- Ruff lint：通过；Ruff format check：通过；pip check：无依赖冲突；
- 当前基线正确加载 2 orders、9 order lines、31 units、9 products 和 3 tracking groups；
- SKU 与 tracking group 引用全部闭合，标准化与原始 SKU 集合及关键溯源字段一致；
- 文件缺失、非法 JSON、数据校验失败、重复订单/SKU/JSON key、缺失 SKU/物流分组引用均有确定且不泄露数据内容的失败行为；
- 四个业务 JSON 在实现和测试前后的 SHA-256 保持一致；
- 未实现 Service、Pricing/GST、外部物流、Shipping Quote、订单业务 API 或数据写入能力。

### 开发目标

以可验证的 Repository 和 Pydantic/领域模型安全加载当前 JSON 数据，并建立后续业务服务依赖的稳定数据边界。

### 主要任务

- 定义订单、订单行、商品和物流分组的数据源模型；
- 定义与 API schema 分离的领域模型；
- 实现 Order、SKU 和 Tracking Repository；
- 加载 `orders.json`、`skus.json` 和 `tracking.json`；
- 确保运行时不直接使用或修改 `skus_raw.json`；
- 校验 JSON、必需字段、唯一 SKU、正整数 quantity、SKU 引用和物流分组引用；
- 定义数据加载异常和数据完整性异常；
- 编写 Repository 和模型测试。

### 交付物

- 后端领域模型与数据源模型；
- JSON Repository 实现；
- 数据验证和异常类型；
- Repository 单元测试。

### 验收标准

- 当前 2 笔订单、9 个 SKU 和 3 个物流分组能够正确加载；
- 所有订单行均能匹配标准化 SKU 和物流分组；
- 对重复 SKU、无效 JSON、缺失 SKU、缺失物流分组和非法 quantity 有确定的失败行为；
- 测试不修改原始数据文件；
- 日志和测试输出不包含客户手机号、邮箱或地址。

### 前置依赖

- Phase 1 后端骨架完成；
- Phase 0 数据基线保持有效；
- 领域模型字段和 Decimal 解析边界获得确认。

## 5. Phase 3：价格计算和订单业务服务

### Phase 3 最终交付成果

- 建立无 I/O、无跨订单状态的 Pricing Service，完整实现 D-004 的 Ex-GST、逐行 `ROUND_HALF_UP`、订单小计、GST、Shipment Fee 标准化与订单总额规则；
- Pricing Service 使用独立的动态精度 Decimal Context，内部除法明确采用 `ROUND_HALF_EVEN` 和 32 位保护位，计算结果不受调用者 precision、rounding、flags 或 traps 影响，且不修改调用者 Context；
- 建立 Order Service，通过现有只读 Repository 接口查询单笔订单、关联标准化商品并生成不可变订单业务结果；
- 新增不可变的 `LinePricingResult`、`PricingResult`、`OrderResultItem` 与 `OrderResult` 领域模型，所有金额保持 `Decimal`，未提前实现 Phase 4 Money API schema；
- 建立非敏感 Service 异常，分类处理非法金额、非法数量、订单不存在、商品不存在和关联不一致；
- 新增 36 项 Service 单元及集成测试，覆盖单/多商品、多数量、半分舍入、逐行舍入差异、Decimal 与 float 差异、零值、非法输入、关联异常、订单隔离、外部 Context 隔离及高精度大金额；
- 未实现 API endpoint、前端订单页、Tracking/Shipping Service 或外部物流集成，未增加依赖。

### Phase 3 最终验收证据

- pytest：128 passed（原有 92 项继续通过，新增 36 项通过；Health API 与 CORS 回归保持通过）；
- Ruff lint：通过；Ruff format check：通过；pip check：无依赖冲突；
- 当前两笔真实数据订单均可独立生成定价结果，合计 9 条订单明细，不共享或污染金额状态；
- `orders.json`、`skus.json`、`skus_raw.json` 与 `tracking.json` 的实现前后 SHA-256 保持一致，四个文件继续被 Git 忽略；
- 更新版 HTML v2 仅作为当前 D-004 实现依据，仍为 `DRAFT FOR REVIEW`，未描述为正式批准；Shipment Fee GST 仍保持 Open Question。

### 开发目标

实现可重复、可审计的 Decimal 定价逻辑和单笔订单业务编排。

### 主要任务

- 实现 Pricing Service；
- 使用 `Decimal` 解析 RRP，确保任何货币路径都不使用或经过 `float`；
- 实现 `Ex-GST Unit Price = RRP / Decimal('1.10')`，不提前舍入；
- 实现 `Line Subtotal = (Ex-GST Unit Price × Quantity).quantize(Decimal('0.01'), ROUND_HALF_UP)`；
- 实现 Order Subtotal 汇总已舍入的 Line Subtotal；
- 实现 `GST Amount = (Order Subtotal × Decimal('0.10')).quantize(Decimal('0.01'), ROUND_HALF_UP)`；
- 将 Shipment Fee 在进入总额前使用 `ROUND_HALF_UP` 标准化为两位小数；
- 实现 `Order Total = (Order Subtotal + GST Amount + Shipment Fee).quantize(Decimal('0.01'), ROUND_HALF_UP)`；
- 分离内部计算值与展示值；
- 实现 Order Service，组合订单行和标准化 SKU；
- 保证每笔订单独立计算；
- 接受明确的 Shipment Fee 输入，并支持 `A$0.00` 降级值；不实现仍属 Open Question 的运费 GST 计算；
- 编写边界、精度和回归测试。

### 交付物

- Pricing Service；
- Order Service；
- Money/PricingResult 等领域结构；
- 完整价格计算测试。

### 验收标准

- 所有货币路径均使用 `Decimal`，测试能够证明没有 `float` 中间值；
- Ex-GST Unit Price 未提前舍入；
- Line Subtotal、GST Amount、Shipment Fee 和 Order Total 均在冻结时点使用 `Decimal('0.01')` 与 `ROUND_HALF_UP`；
- 订单小计只由已舍入的商品行金额汇总；
- Order Total 使用已舍入 GST Amount 和已标准化 Shipment Fee，并在最终求和后再次量化到两位小数；
- 未擅自增加 Shipment Fee 的 GST 计算；
- 不同订单不会合并计算；
- 测试覆盖半分边界、多个商品行、quantity 大于 1、零运费和非零运费；
- 文档与代码明确 HTML v2 为当前依据但仍是 `DRAFT FOR REVIEW`。

### 前置依赖

- Phase 2 Repository 和领域模型完成；
- D-001、D-004、D-011 保持有效；
- Service 输出保持 Decimal，API Money 的显式序列化在 Phase 4 实现。

## 6. Phase 4：FastAPI 接口开发

### Phase 4 最终交付成果

- 建立 API v1 的 `GET /api/v1/orders` 与 `GET /api/v1/orders/{order_number}`，保留既有 `GET /health` 和最小 CORS 边界；
- 建立独立 Router、Pydantic Schema、Mapper、Dependency 与统一异常处理模块，API 不直接读取 JSON、不返回 Domain/Source Model、不执行价格计算；
- 建立 `{"data": ...}` 成功 envelope，以及覆盖订单不存在、请求校验、数据源错误和未知错误的稳定安全错误 envelope；
- 实现 D-011 Money Schema，以严格 Decimal 和显式 serializer 输出两位小数字符串及固定 `AUD`，覆盖零值、半分、大额与低外部 Decimal Context；
- 使用 FastAPI lifespan 统一初始化一次 RepositoryCollection 与 OrderService，通过 `dependency_overrides` 支持合成 Service 测试；
- OpenAPI 1.0.0 文档包含 Health、订单列表、订单详情、Money Decimal String 和 404/422/500 错误模型，不包含运行时客户或追踪数据示例；
- 新增 24 项 API 测试和 1 项 Order Service 列表测试；Tracking/Shipping 外部结果未伪造，D-012/D-013 契约留待对应能力实现时接入。
- 完成 Task 021 独立审查整改：新增 D-015 初始 Shipping Quote unsupported 契约，Order Service 生成 UTC 状态结果并将零值 applied fee 传入 Pricing Service；API 详情和列表不再把零值表达为免费运输；Money serializer 将所有负零规范化为 `"0.00"`。
- 完成 Task 022 契约不变量强化：`ShippingQuoteResult` 强制零运费并规范化为 `Decimal("0.00")`，`OrderResult` 增加纵深校验，`ShippingQuoteResponse` 增加独立的 D-015 契约校验。

### Phase 4 最终验收证据

- pytest：167 passed（Phase 4 初始实现 153 项与 Task 021 新增 14 项均通过；Health 与 CORS 回归保持通过）；
- Ruff lint：通过；Ruff format check：通过；pip check：无依赖冲突；
- 合成数据覆盖列表、空列表、多订单、详情、多 SKU、Money、404、422、数据源 500、未知 500、敏感标记不泄露和架构边界；
- 真实应用 lifespan 集成验证一次初始化的 Service 可连续服务两个 API endpoint，并读取当前两笔订单基线；
- 四个业务 JSON 的实现前后 SHA-256 保持一致，未新增依赖、数据库、缓存、消息队列、认证或外部物流调用。
- Task 021 覆盖 unsupported 状态、reason code、UTC checked_at、quoted/applied fee、Order Total 关联、列表状态、OpenAPI、Tracking 独立性、正负零规范化以及非法金额拒绝；前端 build 与 lint 保持通过。
- Task 022 覆盖 UTC aware `checked_at`、`quoted_fee=null`、零值 `applied_fee` 及非零运费拒绝边界；本地完整 pytest：180 passed。

### 开发目标

将订单、价格和后续物流能力通过稳定、经过验证的 HTTP API 提供给前端。

### 主要任务

- 确认 API 版本、endpoint 命名和错误响应 schema；
- 定义 Pydantic request/response schemas；
- 定义 Money schema：`{"amount":"123.45","currency":"AUD"}`，并为 Pydantic `Decimal` 实现显式 serializer；
- 实现订单列表或查询范围内的必要接口；
- 实现单笔订单详情和定价接口；
- 建立依赖注入，将 route 与 Service/Repository 解耦；
- 映射 not found、数据完整性错误、外部不可用和内部错误；
- 配置必要且最小的 CORS；
- 添加 API tests，验证 schema、状态码和敏感信息边界。

### 交付物

- FastAPI routes；
- Pydantic API schemas；
- 统一错误处理；
- API 测试和接口说明。

### 验收标准

- API route 不直接读取 JSON 或实现价格公式；
- 所有 Money 均序列化为两位小数十进制字符串和固定 `AUD`，Decimal 序列化不经过 `float`；
- 单笔订单响应包含正确商品行、金额和物流分组关联；
- 数据缺失、功能未实现和查询不可用状态结构明确；
- API 响应、错误和日志不泄露凭证或非必要客户数据；
- 自动化 API 测试通过。

### 前置依赖

- Phase 3 完成；
- D-011、D-012、D-013 保持有效，API endpoint、envelope 与错误 schema 由 D-014 确认；
- 确认前端实际需要的客户字段最小集合。

## 7. Phase 5：React 前端开发

当前状态：**COMPLETE**。

当前实现范围包括：基于现有 API 的订单列表、订单号和公司搜索、订单状态筛选、订单详情、客户与收货地址、商品明细、后端权威金额展示、D-015 Shipping Quote unsupported 降级说明，以及 loading、empty、not found、backend disconnected、API error 和 retry 状态。前端保持只读，不实现订单写入、真实 Tracking 或真实 Shipping Quote；`tracking_group_id` 仅作为内部物流分组显示，不表示承运商轨迹。

Task 023 Review Remediation 已完成独立审查提出的五项 Medium 修复：Shipping Quote 文案保持 `unsupported` 语义；SPA 使用 namespaced history state 区分列表进入、应用内返回和直接详情入口；前端运行时校验完整执行 D-015 的 UTC 时间、空报价和零值 applied fee 不变量；列表与详情路由切换后聚焦主标题；横向滚动表格提供可聚焦、命名的键盘区域。同步完成测试 strict 配置、全局 mock 清理、重复业务键处理、无引用 Phase 1 示例清理和 StrictMode 恢复。

Task 023 自动化证据：Frontend Vitest 4 files / 34 tests passed，测试 TypeScript strict check、production build 和 Oxlint 均通过，`npm ls` 依赖树有效且 `npm audit` 为 0 vulnerabilities；Backend pytest 180 tests passed（1 条既有 Starlette/httpx deprecation warning），Ruff check、Ruff format check 和 pip check 均通过。

Task 025 Final Documentation and Verification 已修复 Task 024 独立审查发现的 README 合规项：保留 `README_PHASE0.md` 的历史数据包用途并补充当前 Phase 5 状态，重写 `frontend/README.md` 的功能、技术栈、真实运行与验证命令，并在两份 README 中完整记录 D-015 的 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`、UTC `checked_at`、空 `quoted_fee` 和零值 `applied_fee` 降级语义。同步增加应用内进入详情后以相同 URL 和 history state 重挂载的导航测试，并使用真实 Tab 导航验证两个横向表格区域可聚焦。Frontend Vitest 4 files / 35 tests、应用与测试 TypeScript strict check、production build、Oxlint、`npm ls` 和 `npm audit` 均通过；Backend pytest 180 tests、Ruff check、Ruff format check 和 pip check 均通过。

Phase 5 最终审查闭环：Task 023 为 PASS；Task 024 为 PASS_WITH_NOTES，其 README 合规项由 Task 025 完成闭环；Task 025 为 PASS；Task 026 为 PASS_WITH_NOTES，未发现 Critical、High 或 Medium 问题，唯一 Low 备注为 `ARCHITECTURE.md` 页首阶段状态过期，已在本次 Checkpoint 前修正。Task 026 独立复验通过 Frontend Vitest 4 files / 35 tests、应用与测试 TypeScript strict check、production build、Oxlint、`npm ls`、`npm audit`，以及 Backend pytest 180 tests、Ruff check、Ruff format check 和 pip check；未执行真实浏览器自动化，因此不将真实浏览器验收描述为已通过。Phase 5 现为 `COMPLETE`，Phase 6 与 Phase 7 保持 `NOT_STARTED`。

### 开发目标

实现清晰、类型安全、支持降级状态的订单详情、价格拆分和物流展示界面。

### 主要任务

- 建立类型安全的 API client；
- 将 Money `amount` 建模为 `string`，不得转换为 JavaScript `number`；
- 实现订单选择或导航；
- 实现订单详情和商品行组件；
- 展示 Ex-GST、行小计、订单小计、GST、运费和总额；
- 实现相互独立的 Tracking 与 Shipping Quote 状态区域；
- 对描述缺失、ETA 缺失、物流不可用和报价不可用提供降级 UI；
- 使用中性商品占位图；
- 实现 loading、empty、error 状态；
- 编写组件和关键交互测试。

### 交付物

- React 订单管理界面；
- TypeScript API 类型；
- 降级与错误状态组件；
- 前端测试。

### 验收标准

- 订单金额按 API 的两位小数 string 展示，并只添加 `A$` 前缀；
- 前端不把 Money amount 转为 JavaScript `number`，不重新计算商品行、GST、运费或订单总额；
- Tracking 失败不隐藏成功的 Shipping Quote，Shipping Quote 失败也不隐藏成功的 Tracking；
- 不显示虚构描述、ETA、物流或报价；
- `A$0.00` 降级运费带有明确限制说明；
- 前端包和浏览器请求中不存在物流 API 凭证；
- 客户数据不输出到 console；
- 核心页面和状态测试通过。

### 前置依赖

- Phase 4 API schema 稳定；
- UX 所需字段与最小客户信息展示范围确认；
- 缺失数据、`unavailable` 和 `unsupported` 的用户文案确认。

## 8. Phase 6：物流查询和运费估算

### Batch I Task 037～042 实施状态（2026-11-08）

以 Contract Checkpoint `30544ad226bae79795c47028383a99e16581646b` 为基线完成了：

- Task 037：审计现有 Domain/Repository/Service/API/Frontend、Tracking Group 关系、D-015 与 D-030 协调发布范围；确认当前 3 个 group 中两个只有 `StarTrack / Australia Post` 合并文本，且不存在批准的 Mapping/Release/凭证；
- Task 038：实现不可变 `TrackingRequest`、`TrackingResult`、`TrackingEvent`、`ProviderTrackingResult`、`TrackingDiagnostic`、`TrackingProviderError`、`ProviderConfiguration`/credential 模型、Provider Protocol、Tracking Service 与只读 configuration release reader；
- Task 039：按官方 Track Items 契约实现 Australia Post/StarTrack Adapter、可注入 HTTP transport、Basic Auth/account header、HTTPS/timeout/response-size 边界、每批 10 个 ID、10 requests/minute 单进程 guard、稳定错误分类与 AP/ST raw-status 映射；未执行真实网络调用；
- Task 040：将列表改为独立 `OrderSummaryResult` 与 D-030 `not_requested / Total before shipping`，详情改为 `OrderDetailResult` 并支持注入 Tracking Service；同步 API Schema/Mapper/OpenAPI、TypeScript/runtime validator 与 Tracking UI；Shipping Quote 继续保持 D-015，不修改 Pricing 公式或业务 JSON；
- Task 042：依据用户批准的方案 A 新增 D-031，允许 `TrackingResult.provider` 仅在 `unavailable / CARRIER_MAPPING_UNRESOLVED` 时为 null；修复 Domain 矩阵、Tracking Service Mapping preflight（缺失/不唯一/无 Active Release 均返回每组一个 provider-null 结果且零外呼）、OrderService 每组结果与默认 FastAPI Tracking 注入；将 Provider/Account/Product/Mapping/Release 五种 Revision ID 改为独立不可变校验并新增 append-only `TrackingConfigurationCatalog`；在 `OrderSummaryResult` 强制 D-030 金额公式；把状态归一化改为仅使用匹配 Provider 表，TNT/未知 Provider 固定 `unknown`；同步 API `TrackingResponse`/OpenAPI Mapping unresolved 示例、TypeScript 类型/运行时校验与 TrackingPanel 文案。

Task 041 独立审查判定 `FAIL`：0 Critical、1 High（T041-H01 Mapping unresolved 公开投影缺陷）、2 Medium（T041-M01 Revision 不可变性、T041-M02 D-030 Summary 金额不变量）、1 Low（T041-L01 Provider 状态映射分支）。Task 042 已关闭全部四项，详见 `docs/PHASE6_CONTRACT.md` 第 1.1、8.1、8.4、9.4、9.6、13 节与 `docs/DECISIONS.md` D-031。

Task 042 离线自动化结果：Backend `pytest` 全量 `286 passed`（1 条既有 Starlette/httpx deprecation warning）；Ruff check 与 format check 通过；`pip check` 无损坏依赖。Frontend `4 files / 49 tests passed`；应用与测试 TypeScript strict、production build、Oxlint、`npm ls --depth=0`、`npm audit --audit-level=high` 均通过。真实 Provider、testbed 和 production 均未验证。

当前外部阻塞：

1. 未提供真实 Provider/Account/Product/Mapping Revision、批准的 Active Configuration Release、凭证、账号权限、timeout 治理值与受控环境授权；
2. 未提供项目现有 tracking group 的明确 AP/ST Mapping；不得从合并 carrier 文本或 tracking number 形状猜测；
3. 真实 Provider testbed 与 production 验证仍为 `BLOCKED`；不得因为离线实现与测试全部通过而标记为真实 Provider 集成完成。

`BATCH_I_STATUS: PARTIALLY_COMPLETE`。该状态不授权 Packaging、真实 Shipping Quote、PAC、Quote History、跨请求 cache、数据库或 TNT 实现。下一入口为 Task 043 独立复审与 Git Checkpoint；Task 042 本身不创建 Checkpoint。

### Task 043 独立复审与 Batch I Git Checkpoint（2026-11-08）

Task 043 以只读独立复审方式重新验证了 Task 037～040 的实现与 Task 042 的全部整改，结论为 `BATCH_I_REVIEW_PASS`：0 Critical、0 High、0 Medium、7 Low（全部非阻断，记录见本节末），并已创建 Batch I Git Checkpoint。

- Checkpoint commit：`6ccdc5f5300daa3aa92da97f7ae923596c605a11`（`feat: checkpoint batch I tracking foundation`）
- Parent：`30544ad226bae79795c47028383a99e16581646b`（Phase 6 Contract Checkpoint）
- 提交范围：39 files changed、5047 insertions(+)、121 deletions(-)，全部属于 Batch I；未使用 `git add -A`/`git add .`，逐文件显式暂存并核对 staged 清单与 `git diff --cached --check`；未 push、未修改 Remote
- 数据完整性：四个业务 JSON 的 SHA-256 复审前后一致——orders `8305fba3856a14a2e9e7ff4798f2e2da14278423bc63293608ef7f56a558ddeb`、skus `fa71b78879b6cfeea98460487ad048f44e0458dba9b06391066382fb15f0f942`、skus_raw `44b0db54c736891e23478f9bf412984d9e5006d9d0a1d286671b7128134ac3c5`、tracking `4d79e67c730f3c5dbfbd1ec66dd9e29e5b394fec0467634af55631ff4859c316`；这些 JSON 属本地未版本化数据（`.gitignore` 覆盖），未进入提交

Task 043 实际执行的自动化门禁（非估算，均为本次运行结果）：

| 门禁 | 命令 | 结果 |
|---|---|---|
| Backend 全量测试 | `.\.venv\Scripts\python.exe -m pytest -q` | `286 passed`，1 条既有 Starlette/httpx deprecation warning |
| Ruff lint | `.\.venv\Scripts\ruff.exe check backend` | `All checks passed!` |
| Ruff format check | `.\.venv\Scripts\ruff.exe format --check backend` | `46 files already formatted` |
| Python 依赖完整性 | `.\.venv\Scripts\python.exe -m pip check` | `No broken requirements found.` |
| Frontend 全量测试 | `npm.cmd run test --prefix frontend` | `4 files / 49 tests passed` |
| 测试 TS strict | `npm.cmd run typecheck:test --prefix frontend` | 通过（exit 0） |
| 应用 TS strict + build | `npm.cmd run build --prefix frontend` | 通过；`tsc -b` + Vite 36 modules，`dist` JS 246.01 kB |
| Oxlint | `npm.cmd run lint --prefix frontend` | `0 warnings and 0 errors`（30 files，116 rules） |
| npm 依赖完整性 | `npm.cmd ls --prefix frontend --depth=0` | 14 个声明依赖全部满足范围，无 extraneous |
| npm audit | `npm.cmd audit --prefix frontend --audit-level=low` | `found 0 vulnerabilities` |
| Git 空白/冲突标记 | `git diff --check`、`git diff --cached --check` | 均通过 |
| Markdown 检查 | 代码围栏配对 + 相对链接可达 | 全部通过 |
| OpenAPI/Pydantic 一致性 | 生成 OpenAPI 并与 `TrackingResponse` 等模型比对 | `required` 与模型字段完全一致；`provider` 为 `enum \| null`；D-031 示例存在且通过运行时 schema 校验 |
| D 编号唯一性 | `docs/DECISIONS.md` 标题与全文引用 | D-001～D-031 各唯一、无缺号、无更高编号被引用 |
| 敏感信息扫描 | 代码/测试/文档中的凭证、Authorization/Bearer、真实 tracking number、客户 PII | 未发现命中 |
| 端到端投影探测 | 真实应用 + 真实业务数据的独立脚本 | 2 笔订单、3 个 tracking group，全部返回 `provider=null` / `unavailable` / `CARRIER_MAPPING_UNRESOLVED`，D-030 恒等式成立，D-015 报价未变 |

Task 042 整改回归结论（D-031 与四项 T041 问题）：

- T041-H01：D-031 唯一合法组合 `provider=null + unavailable + CARRIER_MAPPING_UNRESOLVED` 在 Domain、Tracking Service、API Mapper、API Schema、OpenAPI、TypeScript 类型、Runtime Validator 与 TrackingPanel 八处一致；反向约束（该 reason 不得搭配具体 Provider、其他 unavailable/unsupported 必须保留 Provider）在同层一并拒绝；无 Active Release、零个 Mapping、多个 Mapping 三种失败均为每组一个结果、零 Provider 请求，且空数组只表示订单没有唯一 Tracking Group。
- T041-M01：五种 Revision ID（Provider/Account/Product/Mapping/Release）各自独立决定完整内容，同 ID 同内容幂等、不同内容拒绝，跨 Release 与“更换其他关联 Revision ID”均无法绕过；`TrackingConfigurationCatalog` 为真实 append-only，无公共更新/删除入口。
- T041-M02：`OrderSummaryResult` 在 Domain 强制 `order_total = order_subtotal + gst_amount`、`shipment_fee == Decimal("0.00")`、拒绝 float，并拒绝总额偏大/偏小与 GST 不一致；详情继续按真实 `applied_fee` 使用原 Pricing 规则，不套用列表公式。
- T041-L01：Australia Post 只用 AP 状态表、StarTrack 只用 ST 状态表、TNT 与未识别 Provider 固定 `unknown`，raw status 始终保留，事件 description 不参与状态推断。

Task 043 记录的非阻断 Low（均不影响 Batch I 正确性，未为它们改动已冻结的实现）：

1. `backend/models/domain.py` 保留 `OrderResult = OrderDetailResult` 兼容别名，名称已不再区分列表/详情，仅由注释说明；
2. `backend/integrations/credentials.py` 从 `backend.integrations.tracking` 导入私有 `_provider_error`，并从 `backend.models.tracking` 直接导入异常，而非包级导出；
3. `OrderService._tracking_results` 以 `getattr(..., "tracking", None)` 加 `cast` 解析 Tracking Reader，绕过了已声明的 Protocol 类型检查；
4. Tracking Service 的 `provider.provider is not config.provider` 分支缺少直接单元测试（行为经代码与配置不变量覆盖）；
5. 默认应用“不得外呼”的测试仅 monkeypatch `HttpxTrackingTransport.get`，若改用其它 HTTP 客户端路径则不会命中该断言（由空 registry 作为纵深防御）；
6. Domain 只强制 D-030 恒等式与零运费，不重算 `gst_amount = order_subtotal × 10%`，以免在 Domain 复制已冻结的 Pricing 规则；GST 比率正确性仍由 Pricing Service 与其测试保证；
7. `AGENTS.md` §6.2 因追加 D-031 规则，原第 14～21 条顺延为第 15～22 条，语义未变但外部按序号引用需重新对齐。

最终状态区分（三者不得混为一谈）：

- 离线实现：`PASS`，独立复审 `BATCH_I_REVIEW_PASS`；
- Git Checkpoint：已创建 `6ccdc5f`（parent `30544ad`），工作区与暂存区干净，未 push；
- 真实 Provider 验证：`BLOCKED`，未完成；Phase 6 仍为 `IN_PROGRESS`，不得标记 `COMPLETE`；Batch J/K 尚未开始。

### Task 044 外部集成就绪性审计（2026-11-08）

Task 044 以只读审计方式完成 Phase 6 外部集成条件、Packaging 业务输入、Provider 配置治理与 Batch J/K 实施条件评估，结论为 `AUDIT_COMPLETE_WITH_BATCH_J_SPLIT`，详见 `docs/PHASE6_EXTERNAL_READINESS_AUDIT.md`。本次审计未实现功能、未新增依赖、未修改业务 JSON/API/OpenAPI/冻结契约，也未执行任何真实 Provider 请求或 Get Accounts。

核心结论：

- Batch I 真实 Provider 验证仍为 `BLOCKED_EXTERNAL_INPUT`：缺 Provider/Account/Product/Mapping Revision、获批 Active Release、服务端凭证与账号权限、Get Accounts 回执、testbed 授权，以及 3 个 tracking group 的显式 Provider 归属（其中 2 组仍为合并 carrier 文本）。
- Packaging 数据为 Batch J 硬约束：9 个 SKU 仅有商品重量/尺寸/体积/体积毛重，**无任何包装规格**（无包装三维、包装后重量、材料、皮重、capacity、方向/易碎/堆叠/危险品）。商品数据不得充当包装数据。
- **可独立完成的工程工作**：Package 领域模型、数量守恒、provenance、ruleset 外壳与只读 Reader、fail-closed 路径、Package API 投影与前端展示、Shipping Quote 的机制层（三状态联合、金额链、all-or-nothing、capability preflight）——均可用 synthetic fixtures 离线实现。
- **必须等待真实业务输入的工作**：真实包装规格与材料目录、获批 ruleset、Provider 配置与凭证、Contract Price、GST/cubing/精度证据、配置治理角色与激活/rollback 权限。

Batch J/K 就绪判定：

| 判定 | 结果 |
|---|---|
| Batch J Contract Ready（整体） | `NO`（`PackingPolicy` 字段级 schema、方向/易碎/堆叠约束承载字段、具体分配算法、材料选择策略四项未批准） |
| Batch J Contract Ready（J1 限定范围） | `YES` |
| Batch J Offline Implementation Ready | `YES`（限 J1 + synthetic fixtures，须遵守 8 条合成数据规则） |
| Batch J Production Data Ready | `NO` |
| Batch K Readiness | `BLOCKED`（依赖 J1/J2 完成 + testbed 授权 + 运维参数） |

新增待批准业务决策需求：DEC-1 `PackingPolicy` 字段级 schema、DEC-2 方向/易碎/堆叠/危险品约束位置、DEC-3 生产级分配算法、DEC-4 材料选择策略，另加配置治理角色/审批/激活/回滚主体。本任务不批准上述决策。

下一入口：经用户明确授权后执行 **Batch J1**（Package 领域 + synthetic ruleset + 守恒 + provenance + API/前端投影），与真实包装数据获取、DEC-1～DEC-4 澄清并行推进。Batch J/K 不因本次审计自动开始；Batch I 离线实现状态与 Checkpoint `6ccdc5f` 不变；Phase 6 仍为 `IN_PROGRESS`。

### Task 045 Batch J1 离线实现（2026-11-08）

Task 045 在 Batch I Checkpoint `6ccdc5f` 与 Task 044 审计结论之上，完成 Phase 6 Batch J1 的完整离线实现（Package Estimation），并打通 Backend → API → OpenAPI → Frontend 纵向链路。本任务不创建 Commit，暂存区保持为空，等待 Task 046 独立复审与 Checkpoint。

实现范围：

- **Package Domain**：`Package`、`PackageItem`、`PackageItemReference`、`PackageDimensions`、`PackageWeight`、`PackageProvenance`、`PackageEstimationResult`、`PackageEstimationDiagnostic`；不可变、`extra="forbid"`、Decimal-only，尺寸 `_mm`/`_mm3`、重量 `_g`，Provider 派生的体积/计费重量在无证据时为 `null`。
- **Packaging Rules**：`PackagingRuleSet`/`SkuPackagingSpec`/`PackageMaterialSpec`/`PackingPolicy` 只读版本化模型；按 ID 与版本不可变、UTC 生效窗口、SKU/材料/策略唯一性、材料引用完整性；`PackagingRuleSetReader` + `StaticPackagingRuleSetReader`。
- **Package Estimation Service**：`estimate(order, products, rules)` 与 `estimate_for_order(order, products)`；顺序 first-fit（packed unit 体积 + 毛重）确定性分配；支持拆分与多 SKU 混装；数量守恒与 split 策略校验；provenance 记录 ruleset ID/version/source_revision 与不可逆输入指纹；仅使用 `PACKAGE_RULES_NOT_CONFIGURED` 与 `PACKAGE_DATA_INCOMPLETE` 两个公共 reason code。
- **禁止商品数据充当包装数据**：估算链路完全不读取 `weight_g`/`dimensions_mm`/`volume_mm3`/`volumetric_gross_weight_kg`/`max_storage_per_container`；`products` 只用于 SKU 关联一致性校验。
- **OrderService 集成与隔离**：订单详情返回 `package_estimation`（含 `packages`），列表不调用估算；估算失败或异常只降级包装区域，不影响 Tracking、D-015 Shipping Quote 与 Pricing。
- **默认运行时 fail closed**：`build_package_estimation_service()` 注入无 ruleset 的 reader，所有订单详情返回 `unavailable / PACKAGE_RULES_NOT_CONFIGURED` 且 `packages=[]`，绝不使用 synthetic fixtures。
- **API/OpenAPI**：`PackageEstimationResponse` + `PackageResponse`（字段严格按契约 §9.3，不含 material_id、策略、容量或 diagnostics）；尺寸与重量以十进制字符串输出；路径、envelope、ErrorResponse、Money 与既有 Tracking 验证强度均未改变。
- **Frontend**：Package 类型、严格 runtime validator（含 available/unavailable 矩阵、重复 package ID、rules 来源必须带 ruleset、数量必须为正整数）、`PackagePanel` 展示多 Package 尺寸重量与 provenance、区分"规则未配置"与"数据不完整"、标注 synthetic 规则；列表页行为不变。

Synthetic 边界：所有合成规格/材料/ruleset 仅存在于 `backend/tests/packaging_fixtures.py`，未被 `backend.main` 导入；`PackingPolicy` 仅为最小 synthetic 形态；`PackagingRuleSet.synthetic_only` 为 `Literal[True]`，非 synthetic ruleset 无法构造。DEC-1～DEC-4 未被擅自批准。

实际门禁结果：Backend `pytest` 385 passed（1 条既有 Starlette/httpx warning）；Ruff check 与 format check 通过；`pip check` 无损坏依赖。Frontend `4 files / 75 tests passed`；应用与测试 TypeScript strict、production build、Oxlint（0 warnings / 0 errors）、`npm ls --depth=0`、`npm audit --audit-level=high`（0 vulnerabilities）均通过。业务 JSON SHA-256 未改变。

仍未解决：DEC-1（`PackingPolicy` 完整 schema）、DEC-2（方向/易碎/堆叠/危险品约束位置）、DEC-3（生产级装箱算法）、DEC-4（材料选择策略）未批准；真实包装规格、材料目录、容量/皮重、获批 ruleset 全部缺失；真实 Shipping Quote 未实现。Batch J2/K 未开始，Phase 6 仍为 `IN_PROGRESS`。

`BATCH_J1_STATUS: OFFLINE_IMPLEMENTATION_COMPLETE_AWAITING_REVIEW`。下一入口为 Task 046 独立复审与 Git Checkpoint；复审通过前不得创建 Batch J1 Checkpoint，不得开始 Batch J2 或 Batch K。

### Task 046 Batch J1 独立复审与 Git Checkpoint（2026-11-08）

Task 046 以独立复审方式重新验证 Task 045 的实现（不采信其自报 PASS），先用真实模型做了对抗性探测，再据结果整改并重建门禁。结论：`BATCH_J1_REVIEW: PASS`、`TASK_046_FINAL_STATUS: PASS`、`BATCH_J1_GIT_CHECKPOINT: CREATED`。复审发现 2 High / 3 Medium / 2 Low，其中 6 项已整改、1 项 Low 保留。

发现与整改（均不改变 D-001～D-031 业务语义，未新增 D 编号）：

| 编号 | 级别 | 问题（已用真实模型复现） | 整改 |
|---|---|---|---|
| F-01 | High | `OrderDetailResult` 未独立校验 Package↔Order 关系与数量守恒：可构造引用不存在订单行（line_index=99）、SKU 与订单行不符、数量不足、属于其他订单的 Package 并通过校验；数量守恒仅由 Estimation Service 自证 | Domain 新增独立校验：Package 必须属于本订单、行索引必须存在、SKU 必须与被引用订单行一致、逐行数量必须等于订单数量，`unavailable` 时禁止携带 Package |
| F-02 | High | `PackageEstimationService` 未校验 `synthetic_only`：以 `model_construct` 构造的"生产" ruleset 会被执行并报告 `synthetic_ruleset=false`，绕过 J1 合成隔离 | Service 增加纵深防御，拒绝非 synthetic ruleset 与非 synthetic policy，fail closed 为 `PACKAGE_RULES_NOT_CONFIGURED` |
| F-03 | Medium | `OrderDetailResult.package_estimation` 为可选，存在"详情无估算结果"的中间状态，与契约 §4.1"每次详情都有一次估算结果"不符 | 改为必填字段，`packages`/`package_estimation` 一致性成为无条件不变量 |
| F-04 | Medium | `PackageEstimationResult.synthetic_ruleset` 有默认 `False`，省略即静默宣称生产数据 | 改为无默认必填字段 |
| F-05 | Medium | API 与前端未交叉校验 Package ruleset 与估算 ruleset 一致，也未校验 Package item 的 `order_number` 属于本订单 | 后端 `PackageEstimationResponse`/`OrderDetailResponse` 与前端 Runtime Validator 同步增加两项交叉校验 |
| F-06 | Low | OrderService 兜底 `except Exception` 丢弃异常类型，缺陷不可观测 | 内部诊断记录异常类名（`repr=False`，仍不进入公共 API） |
| F-07 | Low（保留，不阻断） | 容量不足与 split 策略冲突统一映射为 `PACKAGE_DATA_INCOMPLETE` | 契约未提供容量/策略专属公共 reason code，且禁止新增枚举；前端文案已同时覆盖"数据不完整或无法满足包装规则"，记录为 J2 决策候选 |

整改后同一对抗探测全部被阻断（4 项 Domain 校验、1 项 Service 隔离、1 项必填字段），并新增 12 个 Backend 与 2 个 Frontend 回归测试锁定。

Task 046 实际执行门禁：Backend `pytest` **397 passed**（1 条既有 Starlette/httpx warning）；Ruff check 通过、format check `56 files already formatted`；`pip check` 无损坏依赖。Frontend `4 files / 77 tests passed`；应用与测试 TypeScript strict、production build、Oxlint（0 warnings / 0 errors）、`npm ls --depth=0`、`npm audit --audit-level=high`（0 vulnerabilities）均通过。`git diff --check`、Markdown、D 编号唯一性、OpenAPI/Pydantic 一致性、敏感信息扫描与业务 JSON SHA-256 全部通过。三个独立端到端探测（Batch I D-030/D-031、J1 默认 fail-closed、对抗性不变量）全部通过。

Git Checkpoint：

- Commit：`3c3675e4cb2deb47bba81346f4d1bc0c6ae290db`（`feat: complete phase 6 batch j1 package estimation`）
- Parent：`0683c678383e8bec1db73c6fbd1eec184cc725ab`
- 范围：30 files changed、+5241 / −18（26 个 Task 045 实现/测试文件 + 3 份 Task 046 文档 + 1 份 Task 044 遗留审计记录）；逐文件显式暂存，未使用 `git add -A`/`git add .`；`git diff --cached --check` 通过；工作区与暂存区均为空；未 push、未配置 remote；未提交业务 JSON、构建产物或缓存

最终状态（三者严格区分）：离线实现 ✅ 完成并通过复审；Git Checkpoint ✅ 已创建；真实包装数据验证 ❌ 未进行；真实 Shipping Quote ❌ 未实现；Batch J 整体 ❌ 未完成；Phase 6 ❌ 仍为 `IN_PROGRESS`。DEC-1～DEC-4 继续保持未批准。

### Task 047 Batch J2 决策准备（2026-11-08）

Task 047 以 Batch J1 Checkpoint `3c3675e` 为冻结基线，一次性完成 Batch J2 开发前的业务决策准备，并输出 `docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md`。本任务为 Decision Preparation / Planning：**未实现任何功能、未修改冻结实现、未调用真实 Provider、未创建 Commit**。

基线核实：执行时 HEAD 为 `537e165`（`docs: record batch j1 independent review and checkpoint`），Branch `main`，工作区与暂存区干净，无 Remote / Tag / Stash；`3c3675e` 是 HEAD 的祖先，`3c3675e..HEAD` 仅含 `docs/PROJECT_PLAN.md` 的 +31/−3 文档记录，实现代码与冻结基线完全一致。

决策推荐（**全部 `PROPOSED — AWAITING_USER_APPROVAL`，本任务未批准任何一项**）：

| 决策 | 主题 | 唯一推荐方案 | 状态 |
|---|---|---|---|
| DEC-1 | `PackingPolicy` schema | 结构化封闭 schema：`scope`(sku/handling_class/general) + 显式 match 字段 + 封闭 `allocation_strategy`/`material_selection` 枚举 + 拆分/混装/上限字段；零匹配即 fail closed，无隐式默认策略 | `PROPOSED` |
| DEC-2 | 包装约束模型 | 三处归属 + 派生视图：SKU 侧 `handling` 事实、材料侧能力上限、policy 侧收紧；运行时派生 `EffectiveConstraintView`，不新增顶层约束实体 | `PROPOSED` |
| DEC-3 | 生产级装箱算法 | 分阶段确定性启发式 + Best-Fit Decreasing（Stage 0～6、显式排序键、无回溯/无求解器、整单 fail closed）；明确不等于 J1 synthetic 顺序 first-fit，也不承诺最优 3D 装箱 | `PROPOSED` |
| DEC-4 | 材料选择 | F1～F8 硬过滤 + 两种封闭排序策略（`smallest_inner_volume` / `priority_order`）+ 8 条禁止 fallback（含禁止合成材料、禁止跨 SKU 借用白名单、禁止「最接近尺寸」猜测） | `PROPOSED` |
| DEC-5 | 配置治理 | 复用 Revision/Release 治理语义、独立实现 Packaging 治理；5 角色职责分离 + 原子激活 + rollback 即重新激活 + append-only 审计；不引入数据库/Redis | `PROPOSED` |
| DEC-6 | 多进程全局限流 | 短期唯一可行：显式单进程部署约束（每 provider/account 同时仅一个进程）+ 启动断言 + 运维手册 + 禁止多 worker/多实例；不新增基础设施、不引入 Redis | `PROPOSED` |

真实数据核查结论：9/9 SKU 具备**商品**物理数据（`weight_g`、`dimensions_mm`、`volume_mm3`、`volumetric_gross_weight_kg`、`max_storage_per_container`），**0/9** 具备任何包装数据，包装材料目录 **0 条**，获批 ruleset **0 份**。`Product Dimensions ≠ Package Dimensions`、`Product Weight ≠ Package Weight` 的边界继续强制。已输出 DM-01～DM-20 缺失清单、四份数据模板（SKU 包装规格 / 材料目录 / ruleset+policy / Release 与审计）与 12 条验收标准。Task 044 的 Australia Post / StarTrack 账号规则与 Provider 配置证据缺口原样保留，本次零真实请求。

Batch J2 实施计划拆为 J2-A（契约增补，需批准）→ J2-B（Rules schema/Reader）→ J2-C（生产算法）/ J2-D（材料选择）→ J2-E（OrderService/API/OpenAPI/Frontend/Runtime Validation）→ J2-F（配置治理）→ J2-H（回归/性能/安全门禁），J2-G（真实数据接入与生产启用验证）当前 `BLOCKED`。可离线推进的部分必须继续遵守 synthetic 隔离与「不得以合成验证冒充生产验证」。

`TASK_047_FINAL_STATUS: DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL`。未新增正式 D 编号（D 编号范围仍为 D-001～D-031），未修改 `docs/DECISIONS.md`、`docs/PHASE6_CONTRACT.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、Backend/Frontend 实现、API/OpenAPI、业务 JSON 或依赖；四个业务 JSON SHA-256 与 Task 046 记录一致。文档结构（51 个表格逐行一致、30 个代码围栏成对）、18 处仓库路径引用、决策编号唯一性、`git diff --check`、敏感信息扫描（凭证/PII/tracking number）均通过；未运行全量测试或构建（任务说明不需要）。Batch I 仍为 `PARTIALLY_COMPLETE`，Phase 6 仍为 `IN_PROGRESS`。

### Task 048 DEC-1～DEC-4 正式化与 Batch J2 契约增补（2026-11-08）

Task 048 依据用户对 Task 047 决策包的批准，将 DEC-1～DEC-4 转化为正式、可执行、无歧义的 Phase 6 契约。本任务为**纯文档契约更新**：未修改任何 Backend/Frontend 代码、API/OpenAPI、TypeScript、业务 JSON、依赖或锁文件，未调用真实 Provider，未创建 Commit。

批准与编号：

| 提案 | 主题 | 结果 | 正式决策 |
|---|---|---|---|
| DEC-1 | Structured `PackingPolicy` Schema | `APPROVED` | D-032 |
| DEC-2 | Constraint Ownership & `EffectiveConstraintView` | `APPROVED` | D-033 |
| DEC-3 | Deterministic Best-Fit Decreasing Packing Algorithm | `APPROVED` | D-034 |
| DEC-4 | Packaging Material Selection Strategy | `APPROVED` | D-035 |
| DEC-5 | Packaging Configuration Governance | `DEFERRED / NOT_APPROVED` | 未形成 D 决策 |
| DEC-6 | Multi-process Global Rate Limiting | `DEFERRED / NOT_APPROVED` | 未形成 D 决策 |

契约落地（`docs/PHASE6_CONTRACT.md`）：

- §5.4 `PackingPolicy` 正式字段级 schema：15 个字段、scope 三层匹配、封闭枚举、加载期校验清单、拆分/混装语义、零匹配 fail closed、AP-1.1～AP-1.7 映射；
- §5.5 约束归属：SKU handling 事实 / 材料能力上限 / policy 只收紧，逐项约束表、材料与 SKU 新增字段、`EffectiveConstraintView` 合并公式、禁止事项、商品事实隔离、AP-2.1～AP-2.10 映射；
- §5.6 生产级确定性装箱算法：Stage 0～6 输入/输出/失败、显式排序键与 tie-breaker、方向枚举、容积预筛与几何、重量与皮重、拆分混装七步裁决、上限、复杂度与性能预算、确定性禁止项、整单 fail-closed、AP-3.1～AP-3.6 映射；
- §5.7 材料选择：候选集、F1～F8 硬过滤、两种排序策略与完整 tie-break、冲突处理、零候选、8 条禁止 fallback、AP-4.1～AP-4.4 映射；
- §5.8 Synthetic-only 与 Production Ruleset 边界：J1 隔离保留、生产 ruleset 准入条件、J2 必须新增的门禁、禁止绕过方式、DEC-5/DEC-6 暂缓影响；
- §13.2 包装必测项增补（policy/约束/算法/材料/边界五组）；§15.1 冻结矩阵新增 D-032～D-035；§15.2 前置输入更新；§16.1～§16.3 实施边界与 readiness 更新。

其他文档：

- `docs/DECISIONS.md`：新增 D-032～D-035（`APPROVED / FROZEN`）；Open Questions 标注 DEC-5/DEC-6 暂缓；追加 Task 048 记录；
- `docs/PHASE6_INTEGRATION_PLAN.md`：新增 §5.3 批准矩阵、§11 Batch J2 批次映射（J2-B～J2-E 可实施、J2-F 未授权、J2-G 阻塞于真实数据、J2-H 门禁）、§12 前置与暂缓更新、§14.3/§14.4 状态、§15 Task 048 记录；
- `docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md`：DEC-1～DEC-4 更新为 `APPROVED`（→D-032～D-035），DEC-5/DEC-6 更新为 `DEFERRED / NOT_APPROVED`，新增 §17 批准与正式化记录；
- `docs/PHASE6_EXTERNAL_READINESS_AUDIT.md`：§17 追加 Task 048 状态（最小更新）；
- `AGENTS.md`：同步阶段状态与下一入口，新增冻结规则 23～24（包装决策边界 + J1 合成隔离）。

边界保持不变：未新增公共 reason code（仍只用 `PACKAGE_RULES_NOT_CONFIGURED` / `PACKAGE_DATA_INCOMPLETE`）；Money Decimal String、Tracking/Quote 隔离、D-030 金额恒等式、D-031 provider-null 投影、`PackageResponse` 字段集合、J1 synthetic 隔离与默认 fail-closed 装配全部不变；D-001～D-031 的原文与语义均未修改。真实包装数据（DM-01～DM-18）、真实材料目录与获批 ruleset 仍全部缺失。

`TASK_048_FINAL_STATUS: PASS`；`BATCH_J2_CONTRACT: COMPLETE`、`BATCH_J2_IMPLEMENTATION: NOT_STARTED`、`DEC_1_TO_4_APPROVED__DEC_5_6_DEFERRED`。Batch I 的**离线实现**为 `COMPLETE`（`BATCH_I_REVIEW_PASS`，Checkpoint `6ccdc5f`），真实 Provider 验证为 `BLOCKED`（既有 `BATCH_I_STATUS: PARTIALLY_COMPLETE` token 保持不变，本任务不改写冻结状态）；Batch J1 为 `COMPLETE`（synthetic-only），Batch K 与 Phase 7 未开始，Phase 6 仍为 `IN_PROGRESS`。下一入口：**Task 049 — Batch J2 Production Packaging Implementation**。

### Task 049-R 考核对齐交付（2026-11-08）

按用户指令，以原始《IT Coding Assessment》任务书为唯一验收基准收敛交付范围：**Batch J2 生产级 Packaging（Best-Fit Decreasing、F1～F8 材料选择、EffectiveConstraintView、配置治理）暂停，DEC-5/DEC-6 维持暂缓，Batch K 不启动**。D-001～D-035 全部保持冻结，Batch I / J1 已实现部分未改动。

本任务实际变更（均为考核对齐的必要修正，无架构扩张）：

- 新增根目录中文 `README.md`：功能、架构、依赖与启动、数据格式、GST/金额规则、Tracking 实现与限制、Shipment Fee 处理、图片占位符与合理假设、环境变量与凭证安全、测试门禁、已知限制、考核对照；
- 前端商品表新增 `RRP (incl. GST)` 列，明确 RRP 语义；商品图片占位符补充 `role="img"`/`aria-label`；ETA 不再回显 `nullDays`（无值时显示 `ETA unavailable`，`0Days` 按原值展示不解释）；`partial_needs_requery` 描述增加"可能被截断，需重新查询"标注；
- 新增后端真实数据验收测试 `backend/tests/test_assessment_acceptance.py`：两笔订单独立重算比对、列表 D-030 恒等式、详情金额链、Tracking/Quote/Package 三者降级与隔离、商品缺失值如实透传；
- `frontend/README.md` 增加中文主 README 指引。

门禁结果：Backend pytest `401 passed`、Ruff check/format 通过、`pip check` 无损坏依赖；Frontend Vitest `4 files / 81 tests passed`、测试与应用 TypeScript strict、production build、Oxlint（0 warnings / 0 errors）、`npm ls`、`npm audit`（0 vulnerabilities）均通过；headless Chrome 实际渲染列表页、两笔订单详情页与 404 页面并核对文案。四个业务 JSON SHA-256 未变。

`TASK_049_R_FINAL_STATUS: PASS`。Batch J2 Contract 仍为 `COMPLETE`，Batch J2 Implementation 为 `PAUSED`（未开始即暂停），Batch I 离线实现完成、真实 Provider 验证 `BLOCKED`，Batch J1 `COMPLETE`（synthetic-only），Batch K 与 Phase 7 `NOT_STARTED`，Phase 6 仍为 `IN_PROGRESS`。下一入口为最终独立验收。

### Planning 状态

Task 028 已于 2026-11-07 完成现状审计、Australia Post / StarTrack 官方资料调研、候选领域/API/前端契约、安全与可靠性设计、测试策略及三批纵向实施计划，详见 `docs/PHASE6_INTEGRATION_PLAN.md`。其历史规划结论已由后续 Task 029 和 Task 030 Decision Approval 关闭。

Task 029 已于 2026-11-07 完成并验收为 `PASS`：D-016 冻结 Tracking Group 与实际 Package 的关系为 `unknown`；D-017 冻结真实集成 `unavailable` 为 `zero_fallback`；D-018 冻结必要报价单元部分失败为 `all_or_nothing`；D-019 冻结 Package Data Source 为 `rules`。`docs/DECISIONS.md`、`docs/PHASE6_INTEGRATION_PLAN.md`、`docs/ARCHITECTURE.md` 与本计划已同步；D-012 和 D-015 保持原文与原义。

Task 030 Decision Approval 已于 2026-11-07 完成并验收为 `PASS`：OD-01～OD-10 全部按推荐方案批准，分别形成 D-020～D-029，冻结 Package cardinality、只读版本化 rules、含 GST total cost、显式 Provider mapping、公共 reason code、详情触发 Quote、无历史/cache、Contract Price、Tracking normalized/raw/unknown 和 Provider Decimal precision。

Task 031 已于 2026-11-08 完成严格只读独立审查并判定为 `FAIL`：发现 0 Critical、0 High、6 Medium 和 3 Low，因此未授权 Contract Checkpoint 或 Phase 6 Batch I。

Task 032 已于 2026-11-08 完成文档契约整改并自验为 `PASS`：关闭 GST 权威冲突、补齐 `ShippingQuoteResult.shipping_gst`、冻结独立 `OrderSummaryResult`/`OrderDetailResult`、定义 Provider/Account/Product/Mapping Readers、冻结 Provider 金额到 D-004/API Money 的完整转换链、定义混合 Provider Capability Preflight 和唯一 reason mapping，并清理三项 Low。整改没有新增或改变 D-012、D-015～D-029 的业务语义，没有修改代码/API 实现。

Task 033 已于 2026-11-08 完成严格只读独立复审并判定为 `FAIL`：发现 0 Critical、0 High、2 Medium 和 2 Low。T033-M01 指出列表 `order_total` 的 `not_requested` 金额语义尚未正式批准；T033-M02 指出版本化 Provider 配置缺少确定的 Revision 解析；T033-L01/L02 分别指出 `total` 字段名错误和配置 rollback/pinning/in-flight 治理输入缺口。

Task 034 已于 2026-11-08 完成业务决策与契约整改并自验为 `PASS`：新增 D-030，冻结列表 `order_total = order_subtotal + gst_amount`、公开 `quote_request_state=not_requested`、`Total before shipping` 和 `Shipping quote not requested` 展示语义；将 Provider/Account/Product/Mapping 配置细化为 Stable ID 与不可变 Revision ID，Mapping Revision 显式引用目标 Revision，由唯一 Active Configuration Release 确定性解析；补齐原子 activation、rollback、request-level version pinning、在途请求和配置 provenance；修正 `total` 字段名。Task 034 只修改六份项目文档，没有修改代码、API 实现、业务 JSON 或依赖。

上述 Task 028～034 状态保留为历史规划记录。Task 037～040 的 Batch I 实施、Task 041 独立审查（`FAIL`：1 High、2 Medium、1 Low）与 Task 042 整改（D-031、T041 四项关闭）记录见上文 Batch I 小节。当前实施以已冻结的 Contract Checkpoint `30544ad226bae79795c47028383a99e16581646b` 为基线，Batch I 状态以前述 `PARTIALLY_COMPLETE` 记录为准；Phase 6 为 `IN_PROGRESS`，Phase 7 仍为 `NOT_STARTED`，契约关卡为 `CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW`。具体 ruleset 数据、Provider/Account/Product/Mapping Revision、获批准 Configuration Release、配置治理权限、账号权限及 Provider/Product GST/重量/精度证据继续属于外部实施输入。

### 开发目标

在可靠的 Integration 边界内实现真实物流查询和运费估算，并保证外部服务失败时不伪造结果。

### 主要任务

- 确认 Australia Post / StarTrack 的 API、认证、sandbox、配额和超时；
- 从环境变量安全读取凭证；
- 实现统一 Integration interface；
- 优先实现 Australia Post / StarTrack 真实查询；
- 实现独立的 TrackingResult 与 ShippingQuoteResult，以及 `available`、`unavailable`、`unsupported` 路径；
- 按 D-031 为每个唯一 Tracking Group 产生一个结果；Mapping 无法解析时返回 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED` 且零 Provider 请求，其他结果必须具有具体 Provider；
- 确保 Tracking 和 Shipping Quote 任一失败不会传播或覆盖另一结果；
- 按 D-016～D-030 实现独立 Package/报价单元、rules 包装估算、zero fallback、all-or-nothing、GST application、不可变 Revision/Configuration Release、稳定 reason、detail-only Quote、列表 Total before shipping、无 cache/history、Contract Price 和 Decimal 边界；不得重新打开 applied Shipment Fee 两位小数标准化规则；
- 实现 Shipping Service 和报价聚合；
- D-015 的未实现路径继续返回 `unsupported`、`quoted_fee=null` 和零值 `applied_fee`；真实集成的 `unavailable` 路径按 D-017 返回独立 reason code、`quoted_fee=null` 和零值 `applied_fee`，不得复用 `SHIPPING_QUOTE_NOT_IMPLEMENTED`；
- 在 README 记录降级原因和限制；
- 保持 TNT 为 Bonus；适配器尚未实现时返回 `unsupported` 和 `CARRIER_NOT_IMPLEMENTED`；
- 使用 stub/fake 覆盖外部失败测试，真实调用只在授权和安全环境中验证。

### 交付物

- `docs/PHASE6_CONTRACT.md`：Task 030 冻结决策、Task 032/034/042 整改后的可执行契约、D-020～D-031 映射与实施前置输入；
- Carrier Integration clients；
- Tracking Service；
- Shipping Service；
- 环境变量配置说明；
- 成功、失败、超时和无效响应测试；
- README 中的运费降级限制说明。

### 验收标准

- 追踪编号只通过 `tracking.json` 关联，不散落硬编码；
- 凭证只存在于后端环境变量，不进入前端、日志或 Git；
- Australia Post / StarTrack 有真实查询路径或有证据的不可用说明；
- 已实现适配器发生超时、认证失败或无效响应时返回 `unavailable`；尚未实现时返回 `unsupported`；
- TrackingResult 与 ShippingQuoteResult 均包含 `status`、`reason_code`、`checked_at` 和各自数据，且一方失败不影响另一方；按 D-031 `TrackingResult.provider` 仅在 `unavailable / CARRIER_MAPPING_UNRESOLVED` 时为 null，其余结果必须有具体 Provider，且每个唯一 Tracking Group 恰好一个结果；
- 不编造物流状态、更新时间或报价；
- D-015 未实现路径保持 `quoted_fee=null`、`applied_fee.amount="0.00"` 并与真实零运费区分；真实集成失败路径按 D-017 保持相同降级金额但使用独立 unavailable reason code；
- 任一必要报价单元失败时按 D-018 将订单级报价降级为 `unavailable`，且不把部分成功金额当作完整订单运费；
- OrderItem/PackageItem 按 D-020 数量守恒，Package 不与 Tracking Group 绑定；
- 按 D-022 不重复加入 shipping GST；按 D-023 使用 Active Configuration Release 精确引用不可变 Mapping/Provider/Account/Product Revision，不发生 latest 或 Provider/Account/Product fallback；按 D-027 不发生 PAC fallback；
- 列表按 D-025 不调用 Quote Provider并表达 `quote_request_state=not_requested`，详情才请求报价；按 D-030 列表 `order_total = order_subtotal + gst_amount` 并展示为 Total before shipping；
- Configuration Release activation/rollback 原子且可审计，一次请求固定同一 Release，切换不影响在途请求；配置治理不扩张为 D-026 禁止的 Quote History 或跨请求 cache；
- 按 D-026 不持久化历史或跨请求缓存，按 D-028 同时保留 raw/normalized Tracking status，按 D-029 拒绝无精度依据的报价；
- 列表使用独立 `OrderSummaryResult` 且不得调用详情；详情使用 `OrderDetailResult` 并保持 `shipping_quote.applied_fee == pricing.shipment_fee`；
- 所有必要 Quote Unit 在网络调用前通过 Capability Preflight；未实现 Adapter 为 unsupported，已实现但 mapping/config 不可用为 unavailable，预检失败不发部分请求；
- Provider 原始金额、单元验证金额、精确聚合、D-004 两位标准化和 API Money 的边界可追溯，`shipping_gst` 只有完整原始证据时展示且不进入 Pricing；
- TNT 未实现时固定返回 `unsupported` 和 `CARRIER_NOT_IMPLEMENTED`，不会被宣称为已完成。

### 前置依赖

- Phase 4 API 与 Phase 5 UI 当前只实现 D-015；实施时必须协调扩展 `not_requested/requested` 与三种结果状态，不能单边发布；
- 获得合法 API 凭证及允许访问的测试环境；
- D-016～D-031 业务规则已冻结，并提供实际 ruleset、Revision/Release mapping、治理权限和 Provider/Product 证据；
- Task 042 整改通过 Task 043 独立复审与 Git Checkpoint；
- 用户明确授权真实外部 API 测试。

## 9. Phase 7：测试、优化和最终交付

### 开发目标

完成端到端验证、安全与隐私检查、交付文档和可复现运行说明。

### 主要任务

- 运行 Backend、Frontend、API 与端到端测试；
- 对冻结业务规则建立最终回归测试；
- 验证两笔订单的独立计算和全部物流分组；
- 测试外部服务不可用、缺失描述、异常 ETA 和报价降级；
- 审查日志、前端构建和 Git 变更中的客户数据与凭证；
- 在公开 GitHub 前替换或脱敏客户数据；
- 完善 README、架构、决策和限制说明；
- 检查可访问性、错误提示和基础性能；
- 记录未实现的 TNT Bonus 或其他限制。

### 交付物

- 完整测试报告；
- 最终 README 和运行说明；
- 更新后的架构与决策文档；
- 安全与隐私检查结果；
- 可交付的前后端应用；
- 已知限制与 Open Questions 清单。

### 验收标准

- 所有必需自动化测试通过；
- 两笔订单价格结果符合 Decimal、GST 和舍入规则；
- 物流失败和报价失败均明确降级且无虚构数据；
- 未泄露手机号、邮箱、地址或 API 凭证；
- 公开交付版本的客户数据已按确认方案处理；
- 文档不把 HTML v2 描述为已正式批准；
- 文档不把未完成的 TNT Bonus 或不可用外部 API 描述为已实现；
- 安装、启动、测试和限制说明可复现。

### 前置依赖

- Phase 1 至 Phase 6 的核心范围完成；
- 最终交付范围和 TNT Bonus 状态确认；
- 公开数据脱敏策略确认；
- 获得执行最终发布或推送操作的明确授权。

## 10. 跨阶段 Open Questions

1. HTML v2 的 GST 规则是否会获得出题方正式批准？
2. 原始 PDF 的第二笔订单编号冲突如何在最终交付中呈现？
3. `0Days` ETA 的业务含义是什么？
4. Australia Post / StarTrack 的真实 Provider/Account/Product/Mapping Revision、获批准 Configuration Release、治理权限、凭证权限和测试环境验证结果是什么？
5. D-021 ruleset 的具体 SKU specs、材料、capacity、tare 等**数据**是什么？（装箱算法、材料选择策略与约束归属已由 Task 048 形成 D-032～D-035 冻结；数据仍缺失，见 `docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md` §10）
6. 各 Provider/Product 的 GST、体积/计费重量、金额精度和舍入证据是什么？
7. TNT Bonus 是否会在后续获得实现授权并进入最终交付？
8. 公开 GitHub 前采用完全替换还是字段级脱敏客户数据？
9. 当前 JSON 是否长期只读；未来是否会增加订单编辑需求？
