# Order Management System 架构与业务决策记录

## 1. 使用说明

本文记录 Phase 0.4 已知的关键决策、依据、影响和未决问题。除非用户明确授权并同步更新业务规则、架构文档与测试，否则已接受的决策不得由实现人员自行改变。

状态定义：

- **Accepted**：已作为当前实现依据；
- **Accepted with caveat**：当前采用，但存在必须保留的外部冲突或限制；
- **Proposed**：尚未批准，不得据此冻结实现；
- **Superseded**：已被后续决策替代。

## D-001：GST 计算采用更新版 HTML v2

- **决策内容**：当前实现采用更新版 HTML v2 的 GST 口径：RRP 已含 GST；Ex-GST Unit Price 为 `RRP / 1.10`；行小计、订单小计、GST 和订单总额按冻结公式计算。
- **选择原因**：HTML v2 是当前收到的更新版需求，且明确给出了计算口径。
- **影响范围**：Pricing Service、金额 API schema、前端金额展示、单元测试、验收样例和 README 限制说明。
- **当前状态**：**Accepted with caveat**。原始 PDF 存在 GST 口径冲突；HTML v2 标注为 `DRAFT FOR REVIEW`。本决策是当前工程实现依据，不代表出题方已正式批准。
- **尚待确认的问题**：出题方是否正式批准 HTML v2；最终交付是否需要同时展示或解释原始 PDF 口径。

## D-002：第二笔订单采用 PO-20251203-00046

- **决策内容**：系统当前使用 `PO-20251203-00046` 作为第二笔订单的订单号。
- **选择原因**：该编号来自当前采用的更新版 HTML v2 与已审查的数据文件。
- **影响范围**：订单 Repository、订单查询 API、前端路由和展示、测试数据、交付说明。
- **当前状态**：**Accepted with caveat**。必须记录原始 PDF 中存在订单编号冲突，不得把冲突描述为已经由出题方解决。
- **尚待确认的问题**：原始 PDF 的冲突编号应如何保留在最终审计说明中；出题方是否会正式确认最终编号。

## D-003：采用 JSON 作为当前数据源

- **决策内容**：Phase 0 至当前计划范围内使用 `orders.json`、`skus.json` 和 `tracking.json` 作为运行时数据源，不引入数据库。
- **选择原因**：当前数据量小、需求集中在读取和计算，JSON 足以支持最小可交付系统；数据库会增加不必要的初始化和迁移成本。
- **影响范围**：Repository 实现、启动时校验、并发写入能力、部署打包和测试夹具。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：数据是否只读；后续是否需要订单编辑能力；若需要写入，何时重新评估数据库与并发控制。

## D-004：使用 Decimal 进行货币计算

- **决策内容**：所有 AUD 金额全程使用 Python `Decimal`，禁止使用或经过 `float`。`Ex-GST Unit Price = RRP / Decimal('1.10')` 且不提前舍入；`Line Subtotal = (Ex-GST Unit Price × Quantity).quantize(Decimal('0.01'), ROUND_HALF_UP)`；Order Subtotal 为已舍入 Line Subtotal 之和；`GST Amount = (Order Subtotal × Decimal('0.10')).quantize(Decimal('0.01'), ROUND_HALF_UP)`；Shipment Fee 进入总额前按 `ROUND_HALF_UP` 标准化到两位小数；`Order Total = (Order Subtotal + GST Amount + Shipment Fee).quantize(Decimal('0.01'), ROUND_HALF_UP)`。
- **选择原因**：避免二进制浮点误差，并精确实现冻结的税务与舍入规则。
- **影响范围**：Pydantic 模型、Pricing Service、API 序列化、测试断言和前端金额解析/展示。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：Shipment Fee 是否含 GST，以及运费 GST 应如何处理。当前不得擅自增加运费 GST 计算。

## D-005：采用模块化单体架构

- **决策内容**：后端作为单一 FastAPI 应用，内部划分 API、Service、Repository 与 Integration Layer；不拆分微服务。
- **选择原因**：当前规模和团队需求不需要分布式系统，模块化单体能保留边界清晰度并降低开发、测试与部署复杂度。
- **影响范围**：目录结构、依赖方向、测试策略、部署方式和模块所有权。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：无当前阻塞问题；只有在出现经过验证的独立部署或扩展需求后才重新评估。

## D-006：TNT 属于 Bonus

- **决策内容**：Australia Post / StarTrack 的真实查询优先实现；TNT 集成属于 Bonus，不作为核心功能完成的前置条件。
- **选择原因**：题目明确区分优先级，先保证核心承运商路径可靠可验证。
- **影响范围**：Integration Layer 实现顺序、Phase 6 范围、测试和最终验收说明。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：TNT Bonus 是否会在后续获得实现授权并进入最终交付；在适配器尚未实现期间，状态已冻结为 `unsupported`，原因码为 `CARRIER_NOT_IMPLEMENTED`。

## D-007：物流结果不得伪造

- **决策内容**：已实现的外部物流适配器在 API 不可访问、超时、认证失败或返回无效结果时，返回明确的 `unavailable` 状态；尚未实现的功能或适配器使用 `unsupported`。任何失败或未实现状态都不得生成或推测物流状态、更新时间、事件、位置或报价。
- **选择原因**：物流数据具有事实属性，伪造会误导用户并破坏系统可信度。
- **影响范围**：Tracking Service、Shipping Service、Integration clients、API 错误模型、前端降级 UI 和测试。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：除已冻结的 `CARRIER_NOT_IMPLEMENTED` 外，其余稳定原因码、用户可见文案和重试策略。

## D-008：原始数据和标准化数据分离

- **决策内容**：`skus_raw.json` 保留源数据，不由业务运行修改；`skus.json` 作为标准化商品数据源。清洗和运行时读取职责分离。
- **选择原因**：保留可追溯性，防止标准化过程破坏源记录，并使业务层只依赖稳定字段。
- **影响范围**：Repository 数据源选择、数据质量流程、测试、变更审计和未来重新标准化。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：未来重新查询或修订 SKU 时的审批、版本和生成流程。

## D-009：客户数据脱敏和凭证安全

- **决策内容**：客户手机号、邮箱和地址不得写入普通应用日志；API 凭证仅通过后端环境变量读取；`.env` 不提交；凭证不得暴露给前端；公开 GitHub 前替换或脱敏客户数据。
- **选择原因**：降低个人信息和凭证泄露风险，保持公开交付安全。
- **影响范围**：日志、错误处理、配置管理、前端构建、测试数据、Git 工作流和发布检查。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：公开版本使用完全合成客户数据还是字段级脱敏；日志平台和数据保留策略；凭证轮换责任。

## D-010：商品缺失数据的处理方式

- **决策内容**：商品描述或 ETA 缺失时返回明确的空值/不可用状态并在前端优雅降级；允许使用中性商品占位图；不得编造描述、ETA 或真实商品图片。
- **选择原因**：当前数据已知存在缺失描述、异常 ETA 和截断描述，系统必须在不制造事实的前提下保持可用。
- **影响范围**：Repository validation、领域模型、API schema、前端组件、测试和数据质量说明。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：`0Days` ETA 的业务语义；`HALGEO15` 完整描述的批准来源；缺失文案的最终产品措辞。

## D-011：Money API 使用 Decimal String

- **决策内容**：所有 API 金额冻结为 `{"amount":"123.45","currency":"AUD"}`。`amount` 是恰好两位小数的十进制字符串，`currency` 固定为 `AUD`。Pydantic `Decimal` 通过显式 serializer 输出该结构且不得经过 `float`；TypeScript 使用 `string`，前端不得转换为 JavaScript `number` 或重新计算订单金额，只负责添加 `A$` 展示前缀。
- **选择原因**：在 Python、JSON 和 TypeScript 边界保持十进制精度，避免 JSON number 和 JavaScript number 引入二进制浮点误差，并确保前后端只有一个权威计算来源。
- **影响范围**：Pydantic schemas、serializer、API 文档、TypeScript types、前端金额组件、契约测试和端到端测试。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：无金额表示问题；API v1 endpoint、外层响应 envelope 和统一错误 schema 已由 D-014 确认。

## D-012：Tracking 与 Shipping 状态独立

- **决策内容**：Tracking 查询和 Shipping Quote 查询必须分别返回 `TrackingResult` 与 `ShippingQuoteResult`，二者均包含 `status`、`reason_code`、`checked_at` 和各自数据。任一查询失败不得导致另一查询失败或覆盖另一查询的成功结果；Order Service 只组合结果，不传播无关失败。`ShippingQuoteResult` 包含 `quoted_fee` 与 `applied_fee`；无有效报价时 `quoted_fee=null`，`applied_fee` 的 API 值为 `{"amount":"0.00","currency":"AUD"}`，状态仍为 `unavailable` 或 `unsupported`。
- **选择原因**：物流轨迹与运费报价是两个独立外部能力，具有不同的可用性、失败原因和数据生命周期；隔离失败可以避免不必要的级联降级。
- **影响范围**：Order Service、Tracking Service、Shipping Service、领域模型、API schema、前端状态组件和测试矩阵。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：各结果的承运商数据字段、除已冻结项外的 reason code 列表，以及 `checked_at` 的最终时间格式。

## D-013：统一状态语义

- **决策内容**：`available` 表示功能已实现且本次查询成功并通过验证；`unavailable` 表示功能或适配器已实现但本次查询失败；`unsupported` 表示功能或适配器尚未实现。TNT 适配器尚未实现时固定返回 `status="unsupported"`、`reason_code="CARRIER_NOT_IMPLEMENTED"`。
- **选择原因**：区分临时查询失败与尚未实现，避免前端、日志、测试和用户文案将未实现功能误报为运行故障或成功结果。
- **影响范围**：TrackingResult、ShippingQuoteResult、Integration clients、API schema、前端文案、监控分类和测试。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：除 `CARRIER_NOT_IMPLEMENTED` 外的完整 reason code 枚举、用户可见文案和是否允许用户触发重试。

## D-014：订单 API v1 与统一响应契约

- **决策内容**：只读订单 API 采用 `GET /api/v1/orders` 与 `GET /api/v1/orders/{order_number}`，成功响应统一为 `{"data": ...}`；错误响应统一为 `{"error":{"code":"ORDER_NOT_FOUND","message":"Order not found."}}` 形态，并使用稳定的 `ORDER_NOT_FOUND`、`REQUEST_VALIDATION_ERROR`、`DATA_SOURCE_ERROR`、`INTERNAL_SERVER_ERROR` 错误码。Money 继续遵循 D-011。Router 仅负责 HTTP 适配，通过 Dependency 获取应用级 Order Service，并由 Mapper 将 Service Result 转换为 API Schema。
- **选择原因**：版本化路径为前端提供稳定边界，统一 envelope 和安全错误码简化客户端处理；明确 Router/Mapper/Service/Repository 分层可防止文件结构、Domain Model、原始异常或价格公式穿透 HTTP 边界。
- **影响范围**：FastAPI application、Order routes、API schemas、Mapper、Dependency Injection、异常处理、OpenAPI、API tests 和 Phase 5 前端 client。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：未来 TrackingResult 与 ShippingQuoteResult 的承运商数据字段和 reason code 枚举仍按 D-012、D-013 在后续阶段确认；当前不提供创建、修改、删除、分页、搜索或排序接口。

## D-015：Initial Shipping Quote Unsupported Contract

- **决策内容**：在 Shipping Quote Integration 尚未实现期间，Order Service 为每次订单查询生成独立的 `ShippingQuoteResult`，固定使用 `status="unsupported"`、`reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED"`、运行时 UTC aware `checked_at`、`quoted_fee=null` 与 `applied_fee=Decimal("0.00")`。Pricing Service 使用该 `applied_fee` 计算 Order Total。API 详情返回完整 `shipping_quote`；列表至少返回 `shipping_quote_status` 与 `shipping_quote_reason_code`。API 不在 pricing 结构中重复暴露 shipment fee。
- **选择原因**：零运费计算值本身无法区分真实免费运输与报价能力尚未实现；显式状态、原因、检查时间以及 quoted/applied fee 分离可防止前端把降级零值误报为已确认的免费报价，同时不伪造承运商数据。
- **影响范围**：Order Service、OrderResult、ShippingQuoteResult、Pricing Service 输入编排、API schemas、Mapper、订单列表与详情、OpenAPI、前端展示语义和测试。
- **当前状态**：**Accepted**。
- **尚待确认的问题**：真实 Shipping Quote Integration 的承运商接口、认证、包装、计费重量、报价聚合、失败 reason code、报价有效期及运费 GST 处理仍待后续确认；本决策不实现 TrackingResult，也不改变 D-012 的结果独立性。

## D-016：Tracking Group 与实际包裹关系保持 Unknown

- **决策内容**：当前 `TrackingGroup` 只表示订单内部物流分组，不视为 Package ID，也不假设一个 Tracking Group 对应一个物理包裹、一个 shipment 或一个独立运费报价单元。实际包裹数量、包装规格及其与 Tracking Group 的映射关系等待真实业务数据确认。
- **选择原因**：现有 `tracking.json` 只提供 group、carrier 和 tracking number 的本地关联，没有物理包裹或装箱证据。把内部关联直接解释为包裹会制造未经确认的物流与报价事实。
- **影响范围**：Tracking Service 可继续按 Tracking Group 关联追踪查询；Shipping Quote Service、Package/PackageItem 领域模型、报价单元划分和装箱规则不得从 Tracking Group 直接推导。
- **当前状态**：**Accepted**。Task 029 选择值为 `unknown`。
- **尚待确认的问题**：Package、PackageItem 与 OrderItem 的关系；实际包裹数据将来如何关联 Tracking Group；单个报价请求与订单级报价的领域模型关系。

## D-017：Shipping Quote Unavailable 使用 Zero Fallback

- **决策内容**：当 Shipping Quote 能力已经实现并进入真实调用流程，但本次因接口异常、超时、权限或其他原因无法获得有效报价时，使用 `status="unavailable"`、独立且非 `SHIPPING_QUOTE_NOT_IMPLEMENTED` 的 reason code、`quoted_fee=null` 和 `applied_fee=Decimal("0.00")`。订单总额继续使用现有公式 `Order Subtotal + GST Amount + Applied Fee`，且仍遵循 D-004 的运费两位小数标准化与最终舍入规则。A$0.00 只是业务降级金额，不是承运商零报价或免费运输。
- **选择原因**：保持订单在外部报价失败时仍可按既有 Pricing Service 产生明确的降级总额，同时依靠 `unavailable`、reason code 和 quoted/applied fee 分离避免把零值误报为真实报价。
- **影响范围**：未来 ShippingQuoteResult 的 `unavailable` 分支、Shipping Quote Service、Order Service 编排、API Mapper、前端降级文案和状态测试；本决策不要求修改 Pricing Service 公式。
- **当前状态**：**Accepted**。Task 029 选择值为 `zero_fallback`。
- **尚待确认的问题**：Task 030 已提出 `unavailable` reason code、API 联合结构及用户文案候选契约；完整枚举与公开投影仍需业务批准。

## D-018：多个必要报价单元采用 All-or-Nothing

- **决策内容**：订单级运费必须基于全部必要报价单元的有效报价。任一必要报价单元失败时，整个订单的 Shipping Quote 为 `unavailable`，订单级 `quoted_fee=null`、`applied_fee=Decimal("0.00")`；不得把部分成功金额作为完整订单运费。已成功的部分结果可以保留为内部诊断事实，但不得伪装成订单级完整报价。
- **选择原因**：部分金额不能证明订单全部运输需求的成本；全有或全无可防止订单总额遗漏部分运费并被误认为完整报价。
- **影响范围**：Shipping Quote Service 聚合、订单级与单元级报价领域关系、诊断模型、API 投影边界、前端降级状态和部分失败测试。
- **当前状态**：**Accepted**。Task 029 选择值为 `all_or_nothing`。
- **尚待确认的问题**：Task 030 已提出必要报价单元、单元结果、安全诊断及全部成功聚合的候选契约；其业务选择与公开/持久化边界仍需批准。

## D-019：Package Data Source 采用可追溯 Rules

- **决策内容**：在没有真实装箱数据时，使用 SKU 包装规格映射与确定性装箱规则估算 Package。SKU 原始重量、长宽高和体积只作为规则输入，不直接等同于实际包裹重量、尺寸或包装体积；不得凭空推断包裹数量、包装材料重量或承运商计费重量。规则必须可配置、可追溯、可测试。未来获得真实装箱数据时，真实数据优先于规则估算；数据不足以可靠生成报价时进入明确的 `unavailable` 降级流程。
- **选择原因**：当前 Product 数据描述商品而非装箱结果；确定性规则能提供可审计的估算边界，同时避免把来源字段误报为真实包裹事实。
- **影响范围**：Package/PackageItem 候选领域模型、包装规则配置与版本、Shipping Quote Service 的请求准备、数据充分性校验、测试夹具和诊断信息。
- **当前状态**：**Accepted**。Task 029 选择值为 `rules`。
- **尚待确认的问题**：Task 030 已提出包装规则 schema/version、Package/PackageItem/OrderItem 和重量模型候选契约；SKU 规格来源、装箱参数、皮重及 Provider 计费规则仍需业务批准。

## D-020：Package 拆分与混装由 Ruleset 控制

- **状态**：**ACCEPTED**。
- **决策背景**：D-016 已确认 Tracking Group 不能作为 Package，D-019 已确认缺少真实装箱数据时使用可追溯 rules，但 OrderItem 与 PackageItem 的 cardinality 尚未冻结。
- **正式决策内容**：领域模型允许一个 OrderItem 分配到多个 Package、一个 Package 包含多个 SKU，以及同一 SKU 分配到多个 Package；具体拆分、混装、兼容性、容量、重量和尺寸限制由生效的 Packaging Ruleset 控制。
- **选择理由**：模型需要表达真实装箱关系，同时不能在缺少业务数据时硬编码某一种装箱算法；把限制放入版本化 ruleset 可保持模型稳定并允许规则演进。
- **影响范围**：`Package`、`PackageItem`、Package Estimation Service、包装规则、数量守恒校验、测试和未来 Package API 投影。
- **必须遵守的约束**：Package 不是 Tracking Group，不得从 Tracking Group 推断 Package；每个 OrderItem 在所有 PackageItem 中的分配数量之和必须严格等于原数量，不得遗漏、重复、超额或跨订单分配。
- **对 Phase 6 实施的影响**：Package 模型和数量守恒可直接实现；具体装箱算法、材料兼容矩阵和容量参数仍必须来自获批 ruleset 数据，不能由本决策臆造。

## D-021：Packaging Rules 使用独立只读版本化配置

- **状态**：**ACCEPTED**。
- **决策背景**：D-019 要求规则可配置、可追溯、可测试，但规则与商品主数据的边界、版本不可变性和读取职责尚未正式确定。
- **正式决策内容**：SKU 包装规格、包装材料、包装策略和兼容规则采用独立于商品主数据的只读版本化配置；每个已发布 ruleset 具有稳定的 Ruleset ID 和 Version，发布后不得原地修改，每次估算必须在 `PackageProvenance` 中记录所用版本；`PackagingRulesReader` 只读获取规则。
- **选择理由**：独立版本可避免修改业务 JSON 或覆盖历史语义，并使相同输入与规则版本的估算可复现、可审计。
- **影响范围**：Packaging Rules schema、只读 loader/reader、Package Estimation Service、provenance、测试夹具和发布流程。
- **必须遵守的约束**：不修改 `orders.json`、`skus.json`、`skus_raw.json` 或 `tracking.json` 承载包装规则；不得原地改变已发布版本；本决策不指定数据库、Redis、管理后台或具体存储路径。
- **对 Phase 6 实施的影响**：可实现规则模型、版本校验和只读 Reader；实际规格、材料、算法参数及配置载体必须在实施批次中以授权数据确定。

## D-022：Provider 含 GST Total Cost 作为 Applied Fee

- **状态**：**ACCEPTED**。
- **决策背景**：现有商品 GST 由 Phase 3 Pricing Service 按 D-004 计算；Shipping Quote Provider 可能返回含 GST 总额及独立 GST 字段，需要避免重复计税。
- **正式决策内容**：仅在 Provider/Product 的官方文档或合同明确确认 `total_cost` 含 GST 时，以该金额作为成功报价的 `quoted_fee` 和最终 `applied_fee`；`shipping_gst` 作为只读信息保留，不再加入订单总额。Australia Post Get Shipment Price 已有 `total_cost` 含 GST、并返回 GST 信息的调研依据。
- **选择理由**：采用 Provider 已确认的最终总额可避免二次增加 GST，同时不改变 Phase 3 商品 GST 公式和计算顺序。
- **影响范围**：Quote Provider mapper、ShippingQuoteResult、Quote aggregation、Pricing Service 输入、API Money 字段和前端税额展示。
- **必须遵守的约束**：不得把 Australia Post 的税务语义推广到其他 Provider；每个 Provider/Product 必须有明确依据；`shipping_gst` 只读且不得重复加入 `applied_fee`；缺少税务口径时返回 `unavailable`，不得生成正式报价。
- **对 Phase 6 实施的影响**：Pricing Service 仍只接收已含适用运费税的 `applied_fee`，不修改商品 GST；每个 Adapter 必须在启用前提供字段语义证据和契约测试。

## D-023：Provider、Account 与 Product 使用显式 Mapping

- **状态**：**ACCEPTED**。
- **决策背景**：当前 tracking 数据包含合并 carrier 文本，不能证明实际 Provider、账户或报价产品；真实 API 又受账户产品权限约束。
- **正式决策内容**：Provider、Account 和 Product 分别建模并通过显式配置映射；使用官方 Get Accounts 或等价受控能力验证账户与产品；不得从合并 carrier 字段或 tracking number 猜测 Provider，也不得静默切换 Provider、Account 或 Product。
- **选择理由**：显式映射能避免把错误账户、产品或承运商当成有效业务事实，并保留各 Provider Adapter 的协议差异。
- **影响范围**：Provider registry/configuration、Tracking/Quote request、账户能力验证、Adapter 选择、错误映射、测试和部署配置。
- **必须遵守的约束**：Provider 配置与业务订单数据分离；认证信息只存在服务端安全配置，不进入前端、日志、API 或普通 model dump；没有有效映射时返回安全 `unavailable`，不 fallback。
- **对 Phase 6 实施的影响**：Provider protocols 和显式 registry 可实现；真实调用必须等待获授权的账户、产品映射和凭证配置。
- **Task 034 技术契约细化**：稳定 `provider_id/account_id/product_id/mapping_id` 只用于逻辑身份；每个配置记录必须另有不可变 Revision ID。Mapping Revision 必须显式引用准确的 Provider、Account、Product Revision，由请求开始时捕获的唯一 Active Configuration Release 决定性解析；禁止按 `latest`、最高版本、创建时间或任意 active 记录推断版本。该细化落实本决策的显式 mapping 和可追溯要求，不改变 Provider、Account、Product 的业务选择。

## D-024：公共 Reason Code 稳定且 Provider 诊断仅内部可见

- **状态**：**ACCEPTED**。
- **决策背景**：D-013 已冻结结果状态语义，但真实 Provider 的错误码和响应形式不稳定且可能包含敏感信息，不能直接形成公共 API 契约。
- **正式决策内容**：采用 `PHASE6_CONTRACT.md` 中冻结的小型公共 Shipping/Tracking Reason Code 枚举；Provider 原始错误码、HTTP 状态和安全摘要只保存在内部 `ProviderDiagnostic` / `TrackingDiagnostic` 中，由 Adapter/Service 映射为稳定公共 code。
- **选择理由**：稳定枚举便于 API、前端和测试长期兼容，内部诊断仍保留排障所需事实而不暴露 Provider 耦合或敏感 payload。
- **影响范围**：Domain enum、Integration error taxonomy、Service mapping、OpenAPI、前端文案、日志与测试。
- **必须遵守的约束**：不得公开 Provider 原始响应、异常文本、凭证或敏感诊断；未知错误映射到安全稳定 code；不得混淆 `unsupported`、`unavailable`、`available`，真实调用失败不得复用 `SHIPPING_QUOTE_NOT_IMPLEMENTED`。
- **对 Phase 6 实施的影响**：公共 enum 和内部诊断结构已可按冻结契约实现；新增公共 code 需要新决策或兼容性审查，不能由单个 Adapter 临时扩张。

## D-025：订单详情触发报价，订单列表保持 Not Requested

- **状态**：**ACCEPTED**。
- **决策背景**：订单列表逐笔实时调用 Provider 会形成 N+1 外部请求、放大延迟和配额风险；现有 API 又必须保留原路径和 D-015 未实现语义。
- **正式决策内容**：首批只有订单详情流程允许触发 Shipping Quote；`GET /api/v1/orders` 不调用 Provider、不逐订单报价，其调用状态为 `not_requested`。`not_requested` 是 Quote Request State，不是 Provider 结果状态；详情中实际尝试后才产生 `available` 或 `unavailable`，能力尚未实现时仍使用 D-015 的 `unsupported`。
- **选择理由**：详情按需调用可控制配额、延迟和失败面，同时无需新增 endpoint 或改变既有 API 路径。
- **影响范围**：Order Service list/detail 编排、API schema 扩展、Phase 5 前端 validator、Provider 调用预算及测试。
- **必须遵守的约束**：列表刷新不得触发 Provider N+1；`not_requested` 不得伪装成报价结果或携带 Provider reason/金额；不得新增未经批准的 API endpoint；D-015 只表示尚未实现，不表示未请求或真实调用失败。
- **对 Phase 6 实施的影响**：未来协调发布时列表需表达独立 request state，详情按获批结果联合结构扩展；本决策不修改本任务中的 API 代码。

## D-026：首批不持久化报价历史且不跨请求缓存

- **状态**：**ACCEPTED**。
- **决策背景**：当前模块化单体没有数据库或缓存基础设施，Provider 也未给出可安全假设的统一报价有效期。
- **正式决策内容**：Phase 6 首批不建立报价历史、不持久化部分成功结果、不引入跨请求缓存；每次详情报价以本次 Provider 响应为准，仅保留请求内去重、关联标识、安全诊断、ruleset version 和报价来源追溯。
- **选择理由**：避免把旧报价伪装成实时结果，也避免在缺少有效期依据时引入错误缓存语义和超范围基础设施。
- **影响范围**：Quote lifecycle、retry/dedup、observability、部署拓扑和未来持久化扩展点。
- **必须遵守的约束**：不新增数据库表、Redis 或进程间缓存；不得跨请求复用部分成功金额；仍须遵守 Provider 频率、并发、timeout 和安全审计限制。
- **对 Phase 6 实施的影响**：首批采用 request-scoped lifecycle；任何历史、缓存、TTL 或跨请求复用都需要后续独立决策。

## D-027：首批 Shipping Quote 仅使用已验证 Contract Price

- **状态**：**ACCEPTED**。
- **决策背景**：Contract Price 与 PAC 零售价是不同报价产品和价格语义，静默 fallback 会把不同来源价格误报为同一业务报价。
- **正式决策内容**：首批核心报价只使用经账户与产品验证的 Contract Price；PAC 是未获本任务批准的独立产品，Contract Price 失败时不得自动切换 PAC、其他 Product、Account 或 Provider；testbed 价格不得作为真实合同价。
- **选择理由**：显式产品来源可确保报价可解释、可审计，并避免失败时悄然改变商业价格语义。
- **影响范围**：Quote source、Provider/Product mapping、Get Accounts 验证、失败 reason、API 展示和受控环境测试。
- **必须遵守的约束**：`quote_source` 必须明确为 contract；PAC 接入需新业务批准；禁止任何静默 fallback；testbed 只证明协议行为，不证明生产价格。
- **对 Phase 6 实施的影响**：Contract Price Adapter 可在账户条件具备后实现；PAC 不进入首批实现范围。

## D-028：Tracking 同时保留 Normalized、Raw 与 Unknown Status

- **状态**：**ACCEPTED**。
- **决策背景**：前端需要稳定的跨 Provider 状态，但只保留标准化状态会丢失 Provider 事实，只暴露 raw status 又会造成前端强耦合。
- **正式决策内容**：TrackingResult/Event 同时保留小型 `NormalizedTrackingStatus` 与 Provider raw status；无法识别或无法映射的值必须归类为 `unknown`，并保留安全 raw 值供后续改进映射。
- **选择理由**：双轨状态既提供稳定 UI 语义，也保留可追溯的 Provider 事实，避免将未知状态猜成已送达或运输中。
- **影响范围**：Tracking Provider mapper、Domain、API、前端 timeline、状态映射配置和测试。
- **必须遵守的约束**：不得根据描述文本猜测确定状态；标准化不得删除 raw status；Tracking 继续独立于 Shipping Quote，Tracking Group 继续不等于 Package。
- **对 Phase 6 实施的影响**：冻结枚举、`unknown` fallback 和 raw 字段可实现；具体 Provider raw-to-normalized 映射须由真实文档/响应证据支持。

## D-029：Provider 运费金额严格遵循明确精度与舍入规则

- **状态**：**ACCEPTED**。
- **决策背景**：Provider/Product/合同可能具有不同金额精度和转换要求，字段长度或通用货币习惯不足以授权系统自行舍入。
- **正式决策内容**：运费报价全链路使用 Decimal，并按明确的 Provider、Product 和合同规则执行精度验证或转换；保留必要的原始金额字符串与币种事实。缺少规则或输入超出已确认精度时拒绝正式报价，通过安全 `unavailable` 与内部诊断表达。
- **选择理由**：拒绝猜测可避免静默改变承运商金额，并与项目现有 Decimal/no-float 安全边界一致。
- **影响范围**：Provider response/request mapper、Quote aggregation、Money validation、reason mapping、测试和受控环境验证。
- **必须遵守的约束**：禁止 float；不得擅用通用 `ROUND_HALF_UP`、`ROUND_UP` 或字段长度推断 Provider 规则；不得修改 Phase 3 商品定价和 D-004 Shipment Fee 进入订单总额前的既有标准化规则。
- **对 Phase 6 实施的影响**：Decimal 管线和拒绝路径可实现；每个启用的 Provider/Product 必须先具备精度与舍入证据。

## D-030：List Order Total Before Shipping When Quote Is Not Requested

- **状态**：**ACCEPTED / FROZEN**。
- **决策背景**：D-025 已冻结订单列表不调用 Shipping Quote Provider、列表请求状态为 `not_requested`、详情才触发真实报价，但没有定义列表 `order_total` 的业务含义。若继续只显示“Order total”，用户可能误认为该金额已包含运费或是最终应付金额。
- **正式决策内容**：`GET /api/v1/orders` 保留现有 `order_total` 字段；当 `quote_request_state="not_requested"` 时，其金额固定为 `order_subtotal + gst_amount`，即商品 Ex-GST 小计与商品 GST 之和。该金额包含商品 GST，但不包含真实运费、不包含尚未请求的 Shipping Quote，也不代表最终含运输费用的应付金额。列表不产生 `ShippingQuoteResult`、`quoted_fee` 或 Provider 调用。
- **API 与前端语义**：Phase 6 列表 API 必须公开 `quote_request_state="not_requested"`。列表金额标签冻结为 `Total before shipping`，状态说明为 `Shipping quote not requested`；可使用自然语言等价表达，但不得继续把该金额单独标注为完整 `Order total`。
- **禁止解释**：列表 `order_total` 不得解释为已完成报价、A$0.00 运费、免费运输、D-017 unavailable fallback 或 D-015 unsupported fallback。用于 Pricing 的内部 `Decimal("0.00")` 只为保持 D-004 计算接口和现有字段兼容，不是 Shipping Quote 金额。
- **详情独立性**：详情继续使用 `quote_request_state="requested"` 和必填 `ShippingQuoteResult`；available 使用 D-022/D-029 验证后的含 GST Provider total，unavailable 使用 D-017 zero fallback，unsupported 使用 D-015 占位。列表与详情金额允许且预期不同，不构成数据不一致。
- **影响范围**：OrderSummaryResult、Order Service 列表编排、Phase 6 Summary API schema/OpenAPI、前端类型/runtime validator、列表标签与测试；不改变 API 路径、成功/错误 envelope、`order_total` 字段名或 Money Decimal String。
- **当前状态说明**：本决策只冻结 Phase 6 协调发布契约；Task 034 不修改现有 Backend、Frontend、API Schema 或 OpenAPI 实现。

## D-031 — Tracking Mapping Resolution Failure Projection

- **状态**：**APPROVED / FROZEN**。
- **决策背景**：D-023/D-024 要求无法唯一解析有效 Provider Mapping 时返回 `CARRIER_MAPPING_UNRESOLVED`，且禁止根据 carrier 展示文本、Tracking Group ID 或 tracking number 形状猜测 Provider；同一 `TrackingResult` 又要求非空具体 Provider。缺少映射时不存在可如实投影的 Provider enum 值，Task 037～040 因此只能返回空 `tracking_results`，既违反“每个唯一 Tracking Group 一个结果”，也用空数组掩盖了 Mapping 错误。Task 041 独立审查把该公开投影缺陷列为 T041-H01（High）。用户已批准方案 A：允许 `TrackingResult.provider` 条件为空。
- **正式决策内容**：当 Tracking Service 无法为一个唯一 Tracking Group 唯一解析出有效 Provider Mapping 时，允许公开 `TrackingResult` 的 `provider` 字段为空。
- **唯一允许的 provider=null 组合**：

  ```json
  {
    "provider": null,
    "status": "unavailable",
    "reason_code": "CARRIER_MAPPING_UNRESOLVED",
    "events": [],
    "raw_status": null
  }
  ```

  其中 `raw_status` 对应公开契约的 `provider_status`；该组合同时要求 `current_status=null`、`latest_event_at=null`。
- **必须同时满足的约束**：

  1. `provider=null` 只能与 `status=unavailable`、`reason_code=CARRIER_MAPPING_UNRESOLVED` 同时出现；反向也成立，该 reason code 只能与 `provider=null` 组合。
  2. 所有其他 `TrackingResult` 必须具有具体 Provider（`australia_post`、`startrack` 或已定义的 `tnt`）。
  3. 不得增加虚构的 `UNKNOWN` Provider，也不得为 `provider=null` 发明新 enum 值。
  4. 不得根据 carrier 展示文本、Tracking Group ID 或 tracking number 形状推断 Provider。
  5. 不得通过空结果数组隐藏 Mapping 错误。
  6. 每个唯一 Tracking Group 必须有一个公开结果。
  7. Mapping 解析失败时不允许发出 Provider 请求。
  8. Mapping failure 必须与 Shipping Quote 失败相互隔离。
  9. Provider 内部诊断、原始错误和凭证不得进入公开 API。
  10. Mapping unresolved 是真实的 `unavailable`，不是 `not_requested` 或 `unsupported`。
- **补充边界**：
  - 没有可用 Active Release，导致无法解析适用 Mapping 时，按照本决策的 Mapping Unresolved 规则处理。
  - 没有适用 Mapping 或存在多个适用 Mapping 时，返回 `CARRIER_MAPPING_UNRESOLVED`。
  - 已确定 Provider，但 Account/Product Revision 配置无效时，继续使用现有配置错误分类（如 `PROVIDER_CONFIGURATION_MISSING`），不得错误地使用 Mapping Unresolved，也不得丢弃已确定的 Provider。
  - 所有 Reason Code 必须继续遵循 D-024；本决策不新增公共 reason code。
  - Tracking 与 Shipping Quote 继续遵循 D-012；本决策不授权真实 Provider 调用、testbed 验证或 Shipping Quote 实现。
- **影响范围**：`TrackingResult` Domain 模型、Tracking Service Mapping preflight、Order Service 编排、默认应用 Tracking 注入、API `TrackingResponse`/OpenAPI、TypeScript 类型与运行时校验、TrackingPanel 文案、Domain/Service/API/Frontend 测试与相关文档。
- **对 Phase 6 实施的影响**：Tracking 纵向切片可以在没有已批准 Mapping/Release 的环境中如实返回“每组一个 provider-null unavailable”，同时保持零 Provider 请求。真实 Provider/Account/Product/Mapping/Release、凭证与 testbed 验证仍是外部实施输入，本决策不改变 `PROVIDER_CONFIGURATION_MISSING`、`CARRIER_NOT_IMPLEMENTED` 或 Shipping Quote 的 D-015/D-017 语义。
- **当前状态说明**：Task 042 已按本决策完成 Domain 不变量、Service、Order Service、默认应用注入、API/OpenAPI、前端类型/运行时校验/UI 与离线测试整改；真实 Provider 验证仍为 BLOCKED，Batch I 仍为 `PARTIALLY_COMPLETE`。

## D-032：PackingPolicy 采用结构化封闭 Schema

- **状态**：**APPROVED / FROZEN**（Task 048；用户批准 Task 047 的 DEC-1。字段级正式契约见 `docs/PHASE6_CONTRACT.md` §5.4）
- **决策背景**：D-020 冻结了「拆分与混装由 ruleset 控制」，D-021 冻结了「rules 独立、只读、版本化」，但契约 §5.1 只用散文描述 `match criteria` / `allocation strategy` / `material selection strategy` / `split-mix constraints`，没有字段级 schema 与封闭枚举。Task 044 审计 C-J1 指出：这种状态会使实现者自行发明策略词汇，事实上创造新契约，且无法审计或测试「规则是否符合契约」。
- **正式决策内容**：`PackingPolicy` 采用结构化、封闭、无隐式默认的策略模型。
  - 字段集合：`policy_id`、`priority`、`scope`、scope 专属匹配字段（`sku` / `handling_class`）、`allocation_strategy`、`material_selection`、`allow_split`、`max_units_per_package`、`max_packages_per_order`、`allow_mixed_sku`、`max_skus_per_package`、`fragile_mixing`、`max_package_gross_weight_g`、`max_package_outer_dimensions_mm`；除显式允许 `null` 者外无默认值，缺省即加载失败。
  - 封闭枚举：`scope ∈ {sku, handling_class, general}`、`allocation_strategy ∈ {sequential_first_fit, best_fit_decreasing}`、`material_selection ∈ {smallest_inner_volume, priority_order}`、`fragile_mixing ∈ {allow, single_sku_only, alone_only}`。
  - 匹配与优先级：rules 内 `sku` > `handling_class` > `general`；同层按 `priority` 升序、再按 `policy_id` 字典序决胜；必须恰好解析出一个 policy。
  - 冲突与缺失：同 scope 同 `sku` 同 `priority` 的重复策略在**加载期拒绝**；零匹配 policy 时 fail closed，禁止隐式默认策略；若业务需要兜底，必须在 ruleset 中显式声明 `general` policy。
  - 收紧原则：policy 的重量、外尺寸、拆分与混装字段只能收紧 SKU/材料的硬约束；任何放宽在 ruleset 加载期拒绝。
- **选择理由**：结构化封闭 schema 使策略可审计、可测试、可演进（新增枚举值需新决策），与契约 §5.2 已冻结的优先级边界一致，且不引入自由 DSL、表达式引擎或外部求解器依赖。
- **影响范围**：`backend/models/packaging_rules.py` 的 `PackingPolicy`/`PackagingRuleSet` 校验、`PackagingRuleSetReader`、Package Estimation Service、ruleset 校验测试、J2-B/J2-C/J2-D/J2-E 实施范围。
- **必须遵守的约束**：不允许自由字符串策略；不允许隐式默认策略；零匹配必须 fail closed；不允许模糊匹配、按创建时间或文件名选择；不允许通过 fallback 使用未经批准规则；不新增公共 reason code（继续受 D-024 约束）。
- **对 Phase 6 实施的影响**：J1 已冻结的 synthetic 最小 policy 形态继续作为回归对照保留，但任何生产 ruleset 必须使用本决策 schema。字段级实现属 Batch J2-B，本决策不修改代码、数据或 API。

## D-033：包装约束归属与 EffectiveConstraintView 合并规则

- **状态**：**APPROVED / FROZEN**（Task 048；用户批准 Task 047 的 DEC-2。正式契约见 `docs/PHASE6_CONTRACT.md` §5.5）
- **决策背景**：七类包装约束（Orientation、Fragile、Stackability、Hazardous Goods、Weight Limit、Dimension Limit、Material Compatibility）的事实来源不同：部分属于物品事实，部分属于容器能力，部分属于业务策略。契约 §5.1 的 `SkuPackagingSpec` 与 `PackageMaterialSpec` 没有承载字段，导致这些约束无法表达；若全部塞入任一侧，则约束可被策略悄然放宽或出现多重事实来源。
- **正式决策内容**：约束采用**三处归属 + 运行时派生视图**：
  1. `SkuPackagingSpec.handling` 记录物品自身的 handling facts：`orientation_policy ∈ {any, upright_only, fixed}`、`fragility ∈ {none, fragile, very_fragile}`、`stacking {stackable, max_stack_units, max_top_load_g}`、`hazardous` + `hazard_class_ref`（指向已批准分类目录的 opaque 引用）。
  2. `PackageMaterialSpec` 记录材料自身的能力与上限：`inner_dimensions_mm`、`outer_dimensions_mm`、`tare_weight_g`、`max_gross_weight_g`、`material_type`、`availability_status ∈ {active, retired}`、`hazmat_approved`、`cushioned`、`orientation_supported ∈ {any, upright_only}`、`selection_priority`。
  3. `PackingPolicy` 只能进一步收紧：`max_package_gross_weight_g`、`max_package_outer_dimensions_mm`、`fragile_mixing` 及拆分/混装限制。
  - 三类输入在估算时派生 `EffectiveConstraintView`，取最严值：毛重上限取材料与 policy 的较小值；外尺寸上限按分量取较小值；方向能力取材料能力与 SKU 策略的最严交集；混装许可为 policy 允许 ∧ 无危险品冲突 ∧ 易碎规则满足。
  - Material Compatibility 采用 **AND 语义**：SKU 侧白名单 ∧ 材料侧能力字段；交集为空即 fail closed。
  - `EffectiveConstraintView` 是**派生对象**：不持久化、不进入 `PackageProvenance`、不进入 API，也不作为新的公共 API 实体。不新增第四个持久化领域实体。
  - 商品事实与包装事实严格区分：`Product` 的重量/尺寸/体积/体积毛重/仓储容量不得作为任何约束输入（D-019、契约 §4.4/§16.2）。
- **选择理由**：事实唯一、硬约束不可被放宽、算法有单一读取点，provenance 仍只由 ruleset ID/version 决定；避免第四事实来源与交叉引用爆炸。
- **影响范围**：`SkuPackagingSpec`、`PackageMaterialSpec`、`PackingPolicy` schema、ruleset 加载期交叉校验（含逐边尺寸关系）、候选材料过滤、混装裁决、J2-B/J2-C/J2-E 测试矩阵。
- **必须遵守的约束**：禁止覆盖、放宽或隐式忽略任何硬约束；禁止工程自行发明危险品代码/法规分类（只能引用已批准目录）；禁止把 commodity 物理数据转为包装约束；禁止为 `EffectiveConstraintView` 增加持久化或 API 投影；`PackageResponse` 字段集合不变（契约 §9.3）。
- **对 Phase 6 实施的影响**：J2 可实现 schema、加载校验与派生视图；真实方向/易碎/堆叠/危险品取值仍属外部业务输入（DM-04～DM-07），本决策不提供任何数据。

## D-034：生产级装箱算法采用分阶段确定性启发式 + Best-Fit Decreasing

- **状态**：**APPROVED / FROZEN**（Task 048；用户批准 Task 047 的 DEC-3。正式契约见 `docs/PHASE6_CONTRACT.md` §5.6）
- **决策背景**：D-020 只批准了「模型允许拆分/混装、具体 rules 可限制」，未批准任何具体分配算法；J1 只实现 synthetic-only 的顺序 first-fit。没有获批算法，生产装箱行为不可定义，也无法审计或回归。
- **正式决策内容**：生产级估算采用 **分阶段确定性启发式 + Best-Fit Decreasing 放置**，固定七个阶段：
  - Stage 0 Preflight（批准状态、policy 唯一匹配、spec/材料齐全）；
  - Stage 1 Unit 展开（订单行按 quantity 展开，不合并、不丢行）；
  - Stage 2 确定性排序（`-packed_unit_volume_mm3`, `-unit_weight_g`, `sku`, `line_index`）；
  - Stage 3 候选材料过滤（D-035 的 F1～F8 + D-033 能力 + 方向可行性）；
  - Stage 4 Best-Fit 放置（选装入后剩余容积最小的已开 Package，否则按 D-035 选材开新 Package）；
  - Stage 5 拆分与混装裁决（policy 字段 + 危险品/易碎规则）；
  - Stage 6 数量守恒、ID 唯一、非空 items、材料合法、上限与 provenance 校验。
  - 空间：内腔容积作必要条件预筛 + 轴对齐方向枚举（≤6 排列，受 `orientation_policy` 限制）的三边可行检查；**不承诺**数学意义上的最优 3D 装箱，不做非轴对齐放置、不做精确 3D 装载几何；不做重量分布/重心建模。
  - 重量：每次加入前 `item_weight_sum + unit_weight + tare` 与有效毛重上限比较。
  - 性能边界：单订单 unit 硬上限 500、单 ruleset 材料硬上限 200、方向枚举 ≤6、复杂度 `O(U × (M + P))`、无回溯。
  - 失败：任一 phase 失败即整单 `unavailable`，公共 reason code 仍只用 `PACKAGE_RULES_NOT_CONFIGURED`/`PACKAGE_DATA_INCOMPLETE`。
- **选择理由**：目标可解释、可复现、可审计的报价输入，而非装载率最优；FFD/Best-Fit 易实现确定性决胜；精确 3D BPP 为 NP-hard，约束求解器会引入未批准依赖与不可预测运行时间。
- **影响范围**：Package Estimation Service 算法本体、ruleset `allocation_strategy` 语义、确定性快照测试、性能门禁、J2-C 实施范围与验收。
- **必须遵守的约束**：禁止回溯搜索、无界搜索、外部求解器、随机排序、不确定性 tie-breaker；禁止部分成功后返回部分 Package 集合；禁止把 J1 的 `sequential_first_fit` 冒充生产算法；禁止通过放宽 `synthetic_only` 激活生产行为。
- **对 Phase 6 实施的影响**：`best_fit_decreasing` 与 `sequential_first_fit` 是两种不同枚举值，J1 只实现后者。生产激活额外要求真实规则数据到位（J2-G 仍 `BLOCKED`）。

## D-035：包装材料选择采用 F1～F8 硬过滤与两种封闭策略

- **状态**：**APPROVED / FROZEN**（Task 048；用户批准 Task 047 的 DEC-4。正式契约见 `docs/PHASE6_CONTRACT.md` §5.7）
- **决策背景**：契约 §5.1 只写「material selection strategy」，未枚举候选集、过滤顺序、排序键与禁止行为；J1 仅实现 `SMALLEST_VOLUME_FIT` 单一 synthetic 策略。缺少确定性规则会使材料选择不可审计，并存在静默 fallback 的风险。
- **正式决策内容**：材料候选只能来自当前生效 ruleset 的 `materials`，并依次通过八项硬过滤：F1 兼容性白名单、F2 可用状态、F3 危险品许可、F4 易碎缓冲、F5 方向能力、F6 容量（轴对齐三边可行）、F7 单位容量毛重（含皮重）、F8 业务外尺寸上限。过滤后的候选按 policy 声明的封闭策略排序：
  - `smallest_inner_volume`：(内腔体积, 外体积, 皮重, `material_id`) 升序；
  - `priority_order`：(`selection_priority`, 内腔体积, 外体积, 皮重, `material_id`) 升序。
  - 末位恒为 `material_id` 字典序。零候选即 fail closed。一个 Package 只使用一种材料且材料必须来自本 ruleset。
  - 八项禁止 fallback 逐项保留：① 白名单外选材；② ruleset 外材料（含硬编码目录）；③ synthetic/测试材料进入非测试路径；④「最接近尺寸」或模糊匹配；⑤ 容量不足后放大材料再放宽重量/方向；⑥ 跨 SKU 借用白名单；⑦ `allow_split=false` 时换材料实现事实拆分；⑧ 一个 Package 混用多种材料。
- **选择理由**：硬过滤先消除不可行候选，再由显式排序键决出唯一结果，使选择可复现、可解释；两种策略都是封闭枚举，避免「成本最优」等未批准目标。
- **影响范围**：材料候选过滤、排序、冲突处理、ruleset 加载校验（policy 上限不得宽于材料硬上限）、J2-C/J2-D 测试与验收。
- **必须遵守的约束**：不得绕过硬过滤；不得因某材料不可用而自动改用未经规则批准的材料；不得使用合成材料；`availability_status=retired` 不进入候选；不新增公共 reason code。
- **对 Phase 6 实施的影响**：材料目录内容仍全部缺失（DM-09～DM-14），J2-D 只能实现机制并用 synthetic fixtures 验证行为，不得表述为真实材料可用性验证。

## 2. 关联但尚未形成新决策的 Open Questions

D-001～D-035 中“尚待确认的问题”保留其被接受时的历史上下文；其中与 OD-01～OD-10 对应的事项已由 D-020～D-029 向前解决。列表金额语义另由 D-030 正式解决，Tracking Mapping 失败的公开投影由 D-031 正式解决；包装策略、约束归属、生产装箱算法与材料选择由 D-032～D-035 正式解决（Task 048）。这些历史描述不应再解释为当前 Pending，也不得回写或覆盖旧决策原文。

**仍为 `DEFERRED / NOT_APPROVED` 的两项提案**（Task 047 编号，非正式 D 决策，不得作为已冻结业务决策实施）：

- **DEC-5 Packaging 配置治理**：治理角色、审批、原子激活、rollback 与审计主体尚未批准；对应实施批次 J2-F 不在当前授权范围。
- **DEC-6 多进程全局限流**：单进程部署约束、共享存储限流或独立 Egress Gateway 尚未批准；当前仍以「单进程内存限流」为唯一实现，真实多进程部署被禁止。

以下问题仍未确认：

- 具体 SKU 包装规格、材料目录、装箱参数、皮重和 capacity 参数是什么？（算法与策略已由 D-032～D-035 冻结，数据仍未提供）
- 各已批准 Provider/Product 的体积重量、计费重量、输入精度和舍入规则由哪些官方文档或合同证明？
- 真实 Provider/Account/Product mapping、账号权限、认证配置和受控环境验证结果是什么？
- Provider raw Tracking Status 到 D-028 标准状态的逐项映射是什么？
- 当前 JSON 是否永久只读；如未来支持业务写入，应以新决策重新评估持久化方案。

### Task 030 Decision Approval 与契约状态

OD-01～OD-10 已按推荐方案获得明确批准并分别形成 D-020～D-029；Task 034 又正式批准列表金额语义并形成 D-030；Task 042 依据用户批准的方案 A 正式新增 D-031。`docs/PHASE6_CONTRACT.md` 已把对应模型、Service、状态、金额、Provider、Tracking、configuration lifecycle 和 API 边界更新为冻结契约。

Task 030 Decision Approval 没有修改 D-012、D-015～D-019。Task 031 独立审查发现契约文档存在 6 项 Medium 和 3 项 Low；Task 032 完成第一轮技术整改。Task 033 复审识别列表金额语义和配置 Revision 解析缺口；Task 034 已通过 D-030 和不可变 Revision/Configuration Release 契约完成整改。Task 037～040 实现 Batch I Tracking 基础后，Task 041 独立审查判定 `FAIL`，发现 1 项 High（T041-H01 Mapping unresolved 公开投影缺陷）、2 项 Medium（T041-M01 Revision 不可变性、T041-M02 D-030 Summary 金额不变量）和 1 项 Low（T041-L01 Provider 状态映射分支）。

Task 042 已按 D-031 完成 T041-H01 全链路整改，并关闭 T041-M01（五种 Revision ID 独立不可变）、T041-M02（`OrderSummaryResult` 金额不变量）和 T041-L01（AP/StarTrack/TNT/未知 Provider 显式分支）。整改没有修改 D-012～D-030 的原有业务语义，也没有开始 Packaging、Shipping Quote、PAC 或其他 Batch J/K 功能。当前契约关卡状态为 `CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW`；Phase 6 为 `IN_PROGRESS`，Batch I 为 `PARTIALLY_COMPLETE`，真实 Provider 验证仍为 `BLOCKED`。下一入口为 Task 043 独立复审，本任务不创建 Git Checkpoint。

### Task 048 Batch J2 决策正式化与契约增补

Task 047 的决策包（`docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md`）提出 DEC-1～DEC-6 六项待批准提案；用户随后书面批准 **DEC-1～DEC-4**，并明确 **DEC-5、DEC-6 暂缓**。Task 048 按批准的 Task 047 原始定义将四项提案转化为正式决策：

| 正式决策 | 来源提案 | 主题 | 状态 |
|---|---|---|---|
| D-032 | DEC-1 | PackingPolicy 结构化封闭 Schema | `APPROVED / FROZEN` |
| D-033 | DEC-2 | 包装约束归属与 `EffectiveConstraintView` 合并规则 | `APPROVED / FROZEN` |
| D-034 | DEC-3 | 生产级确定性装箱算法（分阶段启发式 + Best-Fit Decreasing） | `APPROVED / FROZEN` |
| D-035 | DEC-4 | 包装材料选择（F1～F8 硬过滤 + 两种封闭策略） | `APPROVED / FROZEN` |

本次新增**没有**修改 D-001～D-031 的任何原文或语义：D-019 仍为 Package 数据来源规则、D-020 仍冻结拆分/混装模型与数量守恒、D-021 仍冻结 rules 独立只读版本化、D-024 的公共 reason code 集合不变（未新增枚举）、D-026 仍禁止 Quote History 与跨请求缓存、D-012/D-015/D-030/D-031 不变。

DEC-5（Packaging 配置治理）与 DEC-6（多进程全局限流）继续为 `DEFERRED / NOT_APPROVED`，不构成正式 D 决策；J2-F 与生产多进程部署不在当前授权范围。字段级、阶段级与策略级的正式契约见 `docs/PHASE6_CONTRACT.md` §5.4～§5.8。Phase 6 仍为 `IN_PROGRESS`；Batch J2 Contract 已完成，Batch J2 实施未开始，真实包装数据与真实 Provider 验证仍为 `BLOCKED`。
