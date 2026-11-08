# Phase 6 Contract Design and Frozen Baseline

## 1. Contract Overview

### 1.1 文档状态

- 基线日期：2026-11-07
- 基线 HEAD：`cc8209ae08b3770594f8d490097128924e6cfca8`
- Phase 0～5：`COMPLETE`
- Phase 6：`IN_PROGRESS`（Batch I 离线实现已冻结，`PARTIALLY_COMPLETE`；Batch J1 `COMPLETE`（synthetic-only）；Batch J2 Contract `COMPLETE`，Batch J2 Implementation `NOT_STARTED`）；Phase 7：`NOT_STARTED`
- 依据：D-001～D-035、当前代码与测试、`PHASE6_INTEGRATION_PLAN.md` 的官方 API 调研
- 本文性质：实现前冻结业务契约；不代表任何真实 Provider、账号、凭证、testbed 或真实包装数据验证已经完成
- Task 030 Decision Approval：`PASS`
- Task 031 独立审查：`FAIL`（0 Critical / 0 High / 6 Medium / 3 Low）
- Task 032 整改验收：`PASS`；契约状态：`CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW`
- Task 033 独立复审：`FAIL`（0 Critical / 0 High / 2 Medium / 2 Low）
- Task 034 业务决策与契约整改：D-030 已批准，T033-M01/M02/L01/L02 已整改
- Task 037～040 Batch I 实施：Tracking 基础与协调 API/Frontend 完成并离线验证
- Task 041 独立审查：`FAIL`（0 Critical / 1 High / 2 Medium / 1 Low）
- Task 042 整改：D-031 已批准，T041-H01/M01/M02/L01 已关闭
- Task 043 独立复审：`BATCH_I_REVIEW_PASS`（0 Critical / 0 High / 0 Medium / 7 Low，全部非阻断）；Batch I Git Checkpoint `6ccdc5f5300daa3aa92da97f7ae923596c605a11` 已创建（parent `30544ad226bae79795c47028383a99e16581646b`）
- Task 045 / 046：Batch J1 Package Estimation 离线实现完成，Task 046 独立复审 `PASS`（整改 F-01～F-06，F-07 保留）；Git Checkpoint `3c3675e4cb2deb47bba81346f4d1bc0c6ae290db`
- Task 047：Batch J2 决策包完成（DEC-1～DEC-6 推荐方案、真实数据缺口、J2 实施计划），状态 `DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL`
- Task 048：用户批准 DEC-1～DEC-4 并形成 D-032～D-035；DEC-5/DEC-6 明确 `DEFERRED / NOT_APPROVED`。本文新增 §5.4～§5.8 与 §13.2 的包装契约；Batch J2 Contract `COMPLETE`，Batch J2 Implementation `NOT_STARTED`，真实包装数据仍为 `BLOCKED`

本文是 Phase 6 后续实施的唯一业务契约依据。OD-01～OD-10 已分别通过 D-020～D-029 正式批准，列表金额语义已通过 D-030 正式批准，Tracking Mapping 失败的公开投影已通过 D-031 正式批准，包装策略、约束归属、生产装箱算法与材料选择已通过 D-032～D-035 正式批准；相应业务选择均为 `CONFIRMED`。尚未提供的具体配置值、真实包装数据、账号条件或外部证据属于实施前置输入，不得被误读为已实现能力，也不得阻止不依赖它们的实施批次。

### 1.2 决策分类

| 分类 | 含义 | 是否可直接实现 |
|---|---|---|
| `CONFIRMED` | 已有 Accepted 决策或冻结业务规则 | 是 |
| `DERIVED` | 可从当前实现、数据结构或官方接口规范直接推出，且不增加业务语义 | 是，但实现时仍需契约测试 |
| `PROPOSED` | 推荐的技术或业务方案，尚未获得用户批准 | 否 |
| `BLOCKED` | 缺少业务、账号或数据条件，无法安全冻结 | 否 |

### 1.3 权威顺序

1. `AGENTS.md` 的冻结规则和安全边界；
2. D-001～D-035；
3. 当前已实现的 Phase 0～5 代码和测试；
4. Task 028 官方 API 资料；
5. 本文中的 `CONFIRMED` / `DERIVED` 契约；
6. 本文中仍未冻结的技术细节或外部前置条件，不得覆盖以上内容。

发生冲突时停止相关实现，不得用 Provider 示例、UI 需要或技术便利改变已冻结规则。

### 1.4 核心结果语义

`CONFIRMED`：Shipping Quote 和 Tracking 顶层结果继续使用 D-013 的三状态：

```text
available    功能已实现，本次查询成功且结果通过验证
unavailable  功能已实现，本次查询失败或无法形成有效结果
unsupported  功能或适配器尚未实现
```

Task 030 中“quoted”表示 `status="available"` 的成功报价结果，不新增 `quoted` 状态，避免覆盖 D-013。

`CONFIRMED`：Tracking 与 Shipping Quote 按 D-012 完全独立；Package estimation 是 Shipping Quote 的输入能力，不得成为 Tracking 的事实来源。

`CONFIRMED`：D-025 新增 `QuoteRequestState = not_requested | requested`。`not_requested` 只表示本次流程没有发起 Provider Quote，不属于 `ShippingQuoteResult.status`；只有 `requested` 才能伴随 `available | unavailable | unsupported` 结果。D-015 的 `unsupported` 继续只表示能力尚未实现。

`CONFIRMED`（D-030）：为保持现有列表 `order_total` 字段，`not_requested` 列表计算向 Pricing Service 传入内部 Decimal `0.00`，形成 `order_subtotal + gst_amount` 的商品含 GST 金额。该内部零值不是 `ShippingQuoteResult.applied_fee`、zero fallback 或承运商报价；公开 `quote_request_state=not_requested` 是运费尚未请求和未计入的权威标记。前端标签必须为 `Total before shipping` 或自然语言等价表达，并同时说明 `Shipping quote not requested`；进入详情后以本次 Quote evaluation 重新形成详情权威总额。

## 2. Domain Models

### 2.1 通用类型与不变量

| 类型 | 字段/值 | 分类 | 不变量 |
|---|---|---|---|
| `ResultStatus` | `available | unavailable | unsupported` | CONFIRMED | D-013 语义，不增加第四状态 |
| `QuoteRequestState` | `not_requested | requested` | CONFIRMED | D-025 调用状态；不混入 Provider 结果状态 |
| `CarrierProvider` | `australia_post | startrack | tnt` | CONFIRMED | D-023；内部 code 与显示名称分离，实际映射必须显式配置 |
| `Currency` | `AUD` | CONFIRMED | Phase 0～5 与 Money 契约 |
| `Money` | `amount: Decimal`, `currency: AUD` | CONFIRMED | Domain 使用有限非负 Decimal；API 输出两位字符串；禁止 float |
| `UtcTimestamp` | aware datetime | CONFIRMED | API 统一 UTC；naive/non-UTC Domain 值拒绝 |
| `ReasonCode` | 稳定公共枚举 | CONFIRMED | D-024；不直接透传 Provider code/message |

所有 Domain Model 均应使用不可变、`extra="forbid"` 的 Pydantic v2 模型；敏感字段使用 `repr=False`。集合在 Domain 边界转换为 tuple，外部可变 payload 不得直接进入领域层。

`CONFIRMED`（D-031）：`CarrierProvider` 本身不变，仍只有 `australia_post | startrack | tnt` 三个已定义值；`TrackingResult.provider` 是 `CarrierProvider | None` 的条件投影，不得新增 `unknown`/`unresolved` 等虚构 Provider enum。

### 2.2 Shipping Quote 模型清单

#### `ShippingQuoteResult`

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `status` | `ResultStatus` | CONFIRMED | 三状态语义 |
| `reason_code` | `ShippingQuoteReasonCode | None` | CONFIRMED | available 为 null；失败/未实现为冻结的稳定 code |
| `checked_at` | `UtcTimestamp` | CONFIRMED | 系统检查时间，不冒充 Provider 时间 |
| `quoted_at` | `UtcTimestamp | None` | DERIVED | 仅 Provider 明确返回时填写；否则 null |
| `expires_at` | `UtcTimestamp | None` | DERIVED | 官方未提供时不得发明 |
| `quoted_fee` | `Decimal | None` | CONFIRMED | available 非空；unavailable/unsupported 为空 |
| `applied_fee` | `Decimal` | CONFIRMED | unavailable/unsupported 为规范化 `0.00` |
| `shipping_gst` | `Decimal | None` | CONFIRMED | D-022；仅来自 Provider 明确返回并有语义证据的 GST 金额；只读且不进入 Pricing |
| `currency` | `Literal["AUD"]` | CONFIRMED | 非 AUD 不换汇，结果 unavailable |
| `providers` | `tuple[CarrierProvider, ...]` | CONFIRMED | D-023；去重且稳定排序，多 Provider 订单可表示但不得 fallback |
| `quote_source` | `contract | None` | CONFIRMED | D-027；首批仅 Contract Price；PAC 未获批准 |
| `ruleset_id` | `str | None` | CONFIRMED | D-021；rules estimation 时必填 |
| `ruleset_version` | `str | None` | CONFIRMED | D-021；与 Package provenance 一致 |
| `unit_results` | `tuple[QuoteUnitResult, ...]` | CONFIRMED | D-018/D-024；仅内部诊断，不进入公共 API |

状态不变量：

- `CONFIRMED available`：所有必要报价单元成功；`quoted_fee` 为有限非负、已经按第 6.3 节完成订单级两位小数标准化的 Decimal；`applied_fee=quoted_fee`；`reason_code=null`。按 D-022，仅在每个 Provider/Product 已明确证明 `total_cost` 含 GST 时形成正式报价。
- `CONFIRMED available shipping_gst`：只有每个必要单元均明确返回 GST 金额，且每个字段都有 Provider/Product/合同语义证据时，订单级 `shipping_gst` 才为所有单元已验证 GST Decimal 的稳定顺序精确和，并按第 6.3 节形成两位只读展示金额；任一单元没有独立 GST 金额证据时，订单级 `shipping_gst=null`，不得把部分 GST 伪装为完整订单 GST，也不得从 `total_cost`、商品 GST 税率或差额反推。`shipping_gst=null` 本身不使已证明含 GST 的完整 `total_cost` 报价失败。
- `CONFIRMED unavailable`：`quoted_fee=null`、`applied_fee=Decimal("0.00")`、`shipping_gst=null`、独立 reason code；订单总额继续按 D-004 计算；零值不是免费运输。
- `CONFIRMED unsupported`：D-015 期间固定 `SHIPPING_QUOTE_NOT_IMPLEMENTED`、空 quoted fee、零 applied fee、`shipping_gst=null`；必要 Provider Adapter 尚未实现时使用 D-006/D-013 的 `CARRIER_NOT_IMPLEMENTED`。
- `CONFIRMED`：`shipping_quote.applied_fee == pricing.shipment_fee`；Pricing Service 不读取 quote diagnostics，也不判断 Provider 状态。

#### `OrderQuoteRequest`

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `order_number` | `str` | DERIVED | 单一订单，不跨客户聚合 |
| `currency` | `Literal["AUD"]` | CONFIRMED | 与订单币种一致 |
| `destination` | `QuoteDestination` | DERIVED | Provider 所需最小地址；敏感、不可记录 |
| `quote_units` | `tuple[QuoteUnitRequest, ...]` | CONFIRMED | 非空、unit ID 唯一 |
| `ruleset_id/version` | `str` | CONFIRMED | D-021；rules source 时必填 |
| `requested_at` | `UtcTimestamp` | CONFIRMED | 系统请求时间 |
| `request_fingerprint` | `str` | CONFIRMED | D-026；仅用于请求内关联/去重，不含明文 PII |

`QuoteDestination` 只携带 Provider 必需字段。姓名、电话和邮箱默认不发送；若某产品强制要求，必须新增最小披露审查。地址字段、postcode 和 request body 不得进入普通日志。

#### `QuoteDestination` 与 `ProviderOrigin`

| 模型/字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `QuoteDestination.country_code` | ISO country code | DERIVED | 来自订单地址；不得从币种猜测 |
| `QuoteDestination.postcode` | validated str | DERIVED | 来自订单地址；保持字符串，不记录日志 |
| `QuoteDestination.state/suburb` | str/null | CONFIRMED | 仅在所选 Provider/product 明确要求时发送 |
| `QuoteDestination.street_address` | str/null, `repr=False` | CONFIRMED | 报价 API 非必需时必须为 null |
| `ProviderOrigin.origin_id` | opaque config reference | CONFIRMED | D-023；安全内部 ID，不是客户地址 |
| `ProviderOrigin.country/postcode/state/suburb` | validated str | CONFIRMED | 来自批准的账号/仓库配置，不从订单或环境名猜测 |

以上模型不得包含客户姓名、电话或邮箱。Provider 需要的字段集合由 D-023 的 account/product mapping 决定；额外字段必须采用 allowlist，而不是透传完整订单地址。

#### `QuoteUnitRequest`

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `quote_unit_id` | opaque `str` | CONFIRMED | 订单内唯一，不是 Tracking Group ID |
| `provider` | `CarrierProvider` | CONFIRMED | D-023；必须由显式 mapping/config 选择 |
| `account_id` | safe config reference | CONFIRMED | D-023；只引用服务端配置，不含凭证 |
| `service_code` | `str` | CONFIRMED | D-023/D-027；来自 Get Accounts 验证的 Contract Product，不硬编码或 fallback |
| `packages` | `tuple[Package, ...]` | CONFIRMED | 非空；每个 Package 只属于一个必要单元 |
| `currency` | `Literal["AUD"]` | CONFIRMED | 不支持自动换汇 |
| `origin` | `ProviderOrigin` | CONFIRMED | 来自账号/合同配置，不从订单猜测 |

#### `QuoteUnitResult`（内部）

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `quote_unit_id` | `str` | CONFIRMED | 匹配唯一请求单元 |
| `provider` | `CarrierProvider` | CONFIRMED | 与请求一致 |
| `status` | `available | unavailable` | CONFIRMED | 单元不是公共 capability，不使用 unsupported |
| `reason_code` | enum/null | CONFIRMED | D-024；成功为空，失败为稳定 code |
| `checked_at` | UTC datetime | CONFIRMED | 系统检查时间 |
| `total_cost_incl_gst` | `Decimal | None` | DERIVED | Provider 返回的总金额 |
| `shipping_cost` | `Decimal | None` | DERIVED | Provider 字段，语义不可自行改写 |
| `gst_amount` | `Decimal | None` | DERIVED | Provider 字段；不进入现有商品 GST 公式 |
| `raw_total_cost/raw_shipping_cost/raw_gst` | `str | None` | CONFIRMED | D-029 必要原始金额证据；内部 `repr=False`，不进入 API/log |
| `raw_currency` | `str | None` | CONFIRMED | D-029；解析前的 Provider 币种事实 |
| `amount_semantics_ref` | safe document/contract reference | CONFIRMED | D-022；证明 total/GST 字段语义，不保存合同正文 |
| `precision_rule_ref` | safe document/contract reference | CONFIRMED | D-029；证明解析/舍入规则 |
| `provider_reference` | `str | None` | DERIVED | 仅真实返回时保存；merchant reference 不冒充 |
| `quoted_at/expires_at` | UTC/null | DERIVED | 仅真实返回时填写 |
| `diagnostic` | `ProviderDiagnostic | None` | CONFIRMED | D-024；内部、脱敏、`repr=False`，不进入 API |

#### `ProviderDiagnostic`（内部）

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `category` | stable internal enum | CONFIRMED | authentication/timeout/network/rate_limit/validation/provider |
| `provider_code` | `str | None` | DERIVED | 可保存真实 code，不作为公共 reason code |
| `http_status` | `int | None` | DERIVED | 不包含 headers/body |
| `retryable` | `bool` | CONFIRMED | 由分类策略决定 |
| `safe_detail` | `str | None` | CONFIRMED | 只允许无 PII/credential 的短诊断 |

`ProviderDiagnostic` 不保存 Authorization、account number、完整 request/response、地址或 tracking ID。

### 2.3 Package 模型清单

#### `PackageDimensions`

| 字段 | 类型 | 分类 | 不变量 |
|---|---|---|---|
| `length_mm` | positive finite Decimal | CONFIRMED | 包裹外部尺寸，不是 SKU 尺寸直拷 |
| `width_mm` | positive finite Decimal | CONFIRMED | 同上 |
| `height_mm` | positive finite Decimal | CONFIRMED | 同上 |
| `volume_mm3` | positive finite Decimal | DERIVED | 必须精确等于三维乘积，不提前舍入 |

#### `PackageWeight`

| 字段 | 类型 | 分类 | 不变量 |
|---|---|---|---|
| `item_weight_g` | non-negative finite Decimal | CONFIRMED | 已分配商品重量和 |
| `packaging_weight_g` | non-negative finite Decimal | CONFIRMED | 必须来自真实数据或 D-021 版本化规则；缺值即 unavailable |
| `gross_weight_g` | positive finite Decimal | DERIVED | `item_weight_g + packaging_weight_g` |
| `volumetric_weight_kg` | Decimal/null | CONFIRMED | D-029；只按 Provider/account/product 明确公式计算，无证据时为空并拒绝正式报价 |
| `chargeable_weight_kg` | Decimal/null | CONFIRMED | D-029；只按 Provider 规则/响应确定，不使用通用假设 |

#### `PackageItem`

| 字段 | 类型 | 分类 | 不变量 |
|---|---|---|---|
| `order_item_ref` | `OrderItemReference` | CONFIRMED | 当前无业务行 ID；首批由 order number + line index 构造内部确定性引用 |
| `sku` | `str` | DERIVED | 必须匹配引用的 OrderItem |
| `quantity` | strict positive int | CONFIRMED | 分配数量，不使用 Decimal/float |

`OrderItemReference` 不能假装为持久业务 ID。当前只读订单可使用 `(order_number, zero_based_line_index)` 作为内部确定性引用；若未来支持编辑或持久化，必须引入正式 order-line ID。

#### `Package`

| 字段 | 类型 | 分类 | 不变量 |
|---|---|---|---|
| `package_id` | opaque `str` | CONFIRMED | 订单内唯一；绝不等于 tracking group/number |
| `order_number` | `str` | DERIVED | 只属于一个订单 |
| `source` | `actual | rules` | CONFIRMED | D-019；真实数据优先 |
| `items` | non-empty tuple[PackageItem] | CONFIRMED | D-020；允许拆分/混装且必须数量守恒 |
| `dimensions` | PackageDimensions | CONFIRMED | 包裹外尺寸，由真实数据或版本化规则生成 |
| `weight` | PackageWeight | CONFIRMED | 含包装重量 |
| `material_id` | `str` | CONFIRMED | D-021；来自真实包装或 rules catalog，不得猜测 |
| `ruleset_id/version` | str/null | CONFIRMED | D-021；rules source 必填，actual 可空 |
| `estimated_at` | UTC/null | CONFIRMED | rules source 填写 |
| `provenance` | PackageProvenance | CONFIRMED | D-019/D-021；来源可追溯，不包含 PII |

#### `PackageProvenance`

| 字段 | 类型 | 分类 | 规则 |
|---|---|---|---|
| `source` | `actual | rules` | CONFIRMED | 与 Package source 一致 |
| `source_revision` | `str` | CONFIRMED | 真实数据 revision 或 ruleset revision |
| `ruleset_id/version` | str/null | CONFIRMED | rules 必填，actual 可空 |
| `input_fingerprint` | `str` | CONFIRMED | 规范化输入不可逆 hash，不含明文 PII |
| `generated_at` | UTC datetime | CONFIRMED | 生成/读取本次 Package 的系统时间 |

#### `PackageEstimationResult`

| 字段 | 类型 | 分类 | 不变量 |
|---|---|---|---|
| `status` | `available | unavailable` | CONFIRMED | 不增加虚假 Package |
| `reason_code` | enum/null | CONFIRMED | D-024；成功为空，失败稳定分类 |
| `checked_at` | UTC datetime | CONFIRMED | 系统评估时间 |
| `source` | `actual | rules | None` | CONFIRMED | 真实优先；失败为空 |
| `ruleset_id/version` | str/null | CONFIRMED | D-021；rules 成功时必填 |
| `packages` | tuple[Package] | CONFIRMED | 成功非空；失败为空 |
| `diagnostics` | tuple[PackageDiagnostic] | CONFIRMED | D-024；内部脱敏，不进入公共 API |

`PackageDiagnostic` 至少包含稳定 category、可选 SKU/规则安全引用、ruleset ID/version 和无 PII 的 `safe_detail`；不得保存完整 Product/Order payload。缺失规格、规则冲突、capacity 失败和数量守恒失败必须可区分，但公共 Shipping Quote 只映射为获批的稳定 reason code。

`CONFIRMED`：Package 数量由真实数据或确定性 rules 输出决定，不能由 Tracking Group 数量、订单行数或商品总体积直接决定。

`CONFIRMED`（D-020）：一个 OrderItem 可拆到多个 Package，一个 Package 可混装多个 SKU，同一 SKU 也可跨 Package 分配。以下候选比较保留为决策追溯，冻结选择为“模型允许，具体 rules 可限制”：

| 方案 | 优点 | 缺点 | 影响 |
|---|---|---|---|
| 禁止拆分且禁止混装 | 规则最简单 | 无法表达常见装箱；可能制造不可靠报价 | 简化模型但限制业务 |
| 允许拆分与混装 | 可表达真实装箱；数量守恒可验证 | 规则和测试更复杂 | PackageItem 为多对多分配 |
| **已选：模型允许，具体 rules 可限制** | 不需日后重做模型；每个 ruleset 可选择策略 | 具体算法和配置数据仍需提供 | 模型与守恒校验可实现；实际估算等待 ruleset 数据 |

### 2.4 Order Summary 与 Detail 领域结果

`CONFIRMED`（D-014/D-025）：列表和详情是两个不同用例，使用独立领域结果；不得把 `ShippingQuoteResult` 设为可空后继续复用同一个含糊的 `OrderResult`，也不得让 `list_orders()` 逐项调用详情编排。

#### `OrderSummaryResult`

| 字段 | 类型 | 规则 |
|---|---|---|
| `order` | `Order` | 单一订单 |
| `items` | `tuple[OrderResultItem, ...]` | 已关联 Product 的只读订单行 |
| `pricing` | `PricingResult` | D-030：使用内部 `Decimal("0.00")` 作为未请求运费输入；`order_total = order_subtotal + gst_amount` |
| `quote_request_state` | `Literal["not_requested"]` | D-025；不属于 Provider 结果状态 |

`OrderSummaryResult` 不包含 `shipping_quote`、Package、Quote Unit、Quote diagnostics 或 Provider 时间。其 `pricing.shipment_fee` 必须为规范化 `Decimal("0.00")`；`pricing.order_total` 按 D-030 固定等于 `order_subtotal + gst_amount`，是商品含 GST、未计真实运费的 `Total before shipping`，不是最终含运费应付金额。API 必须投影 `quote_request_state="not_requested"`、`shipping_quote_status=null`、`shipping_quote_reason_code=null`；前端必须同时表达 `Shipping quote not requested`，不得把该金额解释为报价、零运费、免费运输、unavailable fallback 或 unsupported fallback。

#### `OrderDetailResult`

| 字段 | 类型 | 规则 |
|---|---|---|
| `order` | `Order` | 单一订单 |
| `items` | `tuple[OrderResultItem, ...]` | 已关联 Product 的只读订单行 |
| `pricing` | `PricingResult` | 只接收本次 `shipping_quote.applied_fee` |
| `quote_request_state` | `Literal["requested"]` | 详情已进入 Quote evaluation；不保证一定发出网络请求 |
| `shipping_quote` | `ShippingQuoteResult` | 必填；available/unavailable/unsupported 三状态 |
| `packages` | `tuple[Package, ...]` | estimation available 时为本次 Package；失败或 unsupported 可为空 |
| `tracking_results` | `tuple[TrackingResult, ...]` | 与 Quote 独立；每个 Tracking Group 一个结果 |

`OrderDetailResult` 强制 `shipping_quote.applied_fee == pricing.shipment_fee`。`requested` 表示详情进入报价评价流程：D-015 全局能力未实现、能力预检失败或 Package/config fail-closed 均可在不发网络请求时产生对应 `unsupported`/`unavailable` 结果。

#### Service 与 Mapper 边界

```text
OrderService.list_orders() -> tuple[OrderSummaryResult, ...]
OrderService.get_order(order_number) -> OrderDetailResult
```

- 两个方法可以复用只负责读取 Order、关联 Product 和构造行结果的私有 helper，但列表不得调用详情方法，也不得触发 Package Estimation、Tracking 或 Quote Provider。
- 列表对每笔订单调用 Pricing Service 一次，输入内部 `Decimal("0.00")`；该值不是 `ShippingQuoteResult.applied_fee`、zero fallback 或承运商报价。
- 详情按第 3.6 节编排独立 Package/Quote、Tracking 和 Pricing；Pricing Service 仍只调用一次。
- API 使用独立的 `OrderSummaryResponse` 与 `OrderDetailResponse`，不要求把两个 endpoint 包装成同一个 discriminated union。两个 schema 各自通过 `quote_request_state` 固定字面量形成可判别边界；详情包含完整 `ShippingQuoteResponse`，列表只包含 null status/reason，不包含 Quote 金额或时间。
- D-014 的路径、成功 envelope、错误 envelope 和 Money 结构不变；Phase 6 rollout 必须协调更新 Backend schema、OpenAPI、Frontend types/runtime validator 和文案。

## 3. Shipping Quote Contract

### 3.1 Reason codes

以下为 D-024 冻结的完整公共集合。Provider 具体 code、HTTP status 和安全摘要只放内部 diagnostic；新增公共 code 必须经过兼容性与决策审查：

```text
SHIPPING_QUOTE_NOT_IMPLEMENTED       # D-015，已 CONFIRMED
CARRIER_NOT_IMPLEMENTED              # D-006/D-013，已 CONFIRMED
PROVIDER_CONFIGURATION_MISSING
CARRIER_MAPPING_UNRESOLVED
PACKAGE_RULES_NOT_CONFIGURED
PACKAGE_DATA_INCOMPLETE
QUOTE_UNIT_EMPTY
QUOTE_UNIT_DUPLICATE
PROVIDER_AUTHENTICATION_FAILED
PROVIDER_TIMEOUT
PROVIDER_NETWORK_ERROR
PROVIDER_RATE_LIMITED
PROVIDER_RESPONSE_INVALID
CONTRACT_PRICE_UNAVAILABLE
PRODUCT_NOT_AVAILABLE
CURRENCY_NOT_SUPPORTED
PARTIAL_QUOTE_FAILURE
PROVIDER_ERROR
```

`PARTIAL_QUOTE_FAILURE` 对应 D-018 的订单级 unavailable；任何真实调用失败均不得复用 D-015 的 `SHIPPING_QUOTE_NOT_IMPLEMENTED`。

冻结的唯一公共映射如下；表中条件不得使用其他公共 code，Provider 原始 code/message 仍只进入内部 diagnostic：

| 失败条件 | 顶层状态 | 唯一公共 reason code |
|---|---|---|
| 整个 Shipping Quote 能力代码尚未实现（D-015） | `unsupported` | `SHIPPING_QUOTE_NOT_IMPLEMENTED` |
| 已识别的任一必要 Provider Quote Adapter/能力尚未实现 | `unsupported` | `CARRIER_NOT_IMPLEMENTED` |
| 无法从批准配置唯一解析 Provider/Account/Product mapping | `unavailable` | `CARRIER_MAPPING_UNRESOLVED` |
| Active Configuration Release、Provider Revision、Account Revision、Account 验证、GST/精度语义证据缺失或失效 | `unavailable` | `PROVIDER_CONFIGURATION_MISSING` |
| Packaging Ruleset 不存在或无 active version | `unavailable` | `PACKAGE_RULES_NOT_CONFIGURED` |
| SKU/material/tare/capacity/必要 package 输入不完整 | `unavailable` | `PACKAGE_DATA_INCOMPLETE` |
| 必要 Quote Unit 集合为空 | `unavailable` | `QUOTE_UNIT_EMPTY` |
| unit ID、Package ID 重复或 Package 跨必要单元 | `unavailable` | `QUOTE_UNIT_DUPLICATE` |
| Provider 拒绝认证 | `unavailable` | `PROVIDER_AUTHENTICATION_FAILED` |
| Provider 调用超时 | `unavailable` | `PROVIDER_TIMEOUT` |
| DNS/连接/传输网络失败 | `unavailable` | `PROVIDER_NETWORK_ERROR` |
| Provider 限流 | `unavailable` | `PROVIDER_RATE_LIMITED` |
| Provider schema、币种字段或金额违反已有证据/精度规则 | `unavailable` | `PROVIDER_RESPONSE_INVALID` |
| 已验证 Contract Product 本次没有合同价格 | `unavailable` | `CONTRACT_PRICE_UNAVAILABLE` |
| 已映射 Product 不存在、未启用或 Account 无该 Product 权限 | `unavailable` | `PRODUCT_NOT_AVAILABLE` |
| Provider 返回非 AUD 且系统不支持换汇 | `unavailable` | `CURRENCY_NOT_SUPPORTED` |
| 多个必要单元进入调用阶段后任一单元失败 | `unavailable` | `PARTIAL_QUOTE_FAILURE` |
| 已实现 Provider 的其他已分类、无法更具体映射的安全错误 | `unavailable` | `PROVIDER_ERROR` |
| 所有必要单元成功 | `available` | `null` |

一个必要单元失败时，订单级 reason 保留该单元的唯一公共 reason；两个或更多必要单元进入调用阶段后只要任一失败，订单级固定为 `PARTIAL_QUOTE_FAILURE`，每个单元的具体公共 reason 和 Provider 安全诊断仅保留在内部 `unit_results`。这一定义同时覆盖“部分成功”和“全部失败”，避免根据返回顺序选择任意订单级 reason。

### 3.2 Quote Provider contract

```text
QuoteProvider.quote(unit: QuoteUnitRequest) -> QuoteUnitResult
```

- 输入只包含单一 Provider 的一个必要报价单元。
- Provider Adapter 只负责认证、request mapping、HTTP、response validation 和 provider error mapping。
- Adapter 不选择 Package、不计算订单总额、不实施 zero fallback。
- Provider 成功金额以字符串解析为 Decimal，拒绝 float、NaN、Infinity、负数和币种不符。
- Provider 原始 payload 不离开 Integration Layer。

### 3.3 Shipping Quote Service contract

```text
ShippingQuoteService.quote_order(
    order: Order,
    products: tuple[Product, ...],
    package_result: PackageEstimationResult,
) -> ShippingQuoteResult
```

Service 职责：

1. 验证 Package estimation 和 rules provenance；
2. 通过第 8.4 节显式 registry/mapping 形成必要报价单元；
3. 在任何网络调用前执行第 3.4 节 Capability Preflight；
4. 仅在所有必要单元通过预检后调用对应 QuoteProvider；
5. 执行 D-018 all-or-nothing；
6. 执行 D-017 zero fallback；
7. 按第 6.3 节形成订单级 `quoted_fee`、`applied_fee` 与只读 `shipping_gst`；
8. 返回订单级结果和安全内部 diagnostics；
9. 不修改商品 Pricing 规则。

### 3.4 Capability Preflight 与混合 Provider 聚合

Capability Preflight 是 Shipping Quote Service 的无网络前置步骤，不是 Provider 调用。执行顺序及短路结果冻结如下：

1. 全局 Shipping Quote 代码尚未实现时，直接返回 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`。
2. 验证 Package Estimation、数量守恒和 rules provenance；失败按第 3.1 节映射为 `unavailable`。
3. 形成非空、ID 唯一且覆盖每个 Package 恰好一次的必要 Quote Unit；空或重复按唯一 code 返回 `unavailable`。
4. 在请求开始时捕获第 8.4 节唯一 Active Configuration Release；在同一 `release_revision_id` 内为每个单元唯一解析 Mapping Revision，并按显式 Revision ID 加载 Provider、Account、Contract Product、origin 和环境。无 Active Release 或 Release 无效为 `PROVIDER_CONFIGURATION_MISSING`；Mapping 为零个或多个匹配时为 `CARRIER_MAPPING_UNRESOLVED`。
5. 对全部已解析 Provider Revision 查询 Adapter capability registry。任一必要 Provider 的 Quote capability 未实现时，整个订单返回 `unsupported / CARRIER_NOT_IMPLEMENTED`；此状态优先于其余 Account/Product 配置错误，且不得调用任何 Provider。
6. 验证所有 Mapping/Provider/Account/Product Revision 均属于已批准 Release、verified、环境一致，Contract Product 可用，并具备 D-022 GST 与 D-029 精度证据。任一失败按第 3.1 节唯一 code 返回 `unavailable`；不得调用任何 Provider。
7. 只有全部必要单元通过以上预检，才允许按稳定 unit ID 顺序调用 Provider。任一运行时单元失败后仍执行 D-018 all-or-nothing；实现可取消尚未发出的调用，但不得把已成功金额传入 Pricing。

预检公共 reason 按上述步骤短路；同一步骤存在多个失败时使用以下固定优先级，不按配置顺序或 Provider 返回顺序选择：`PROVIDER_CONFIGURATION_MISSING` > `PRODUCT_NOT_AVAILABLE` > `CURRENCY_NOT_SUPPORTED`。Package、unit 和 mapping 错误已由更早步骤唯一短路；一旦识别出任一必要 Adapter 未实现，第 5 步固定返回 `CARRIER_NOT_IMPLEMENTED`，不继续用下游配置错误覆盖 unsupported。每个单元的全部安全失败事实仍可进入内部 diagnostic。

预检失败时 `unit_results` 可以保留已经完成的安全验证诊断，但不得伪造 Provider 调用结果。所有失败的 `quoted_fee=null`、`applied_fee=Decimal("0.00")`、`shipping_gst=null`。Tracking 不参与预检，也不受其结果影响。

### 3.5 Quote source

`CONFIRMED`（D-027）：首批只使用经 D-023 验证的 Contract Price；PAC 未获批准，且不得成为失败 fallback。

| 方案 | 优点 | 缺点 | 影响 |
|---|---|---|---|
| Shipping and Tracking Get Shipment Price | 合同账号价格；与 Tracking API 家族一致 | 需要合格合同、产品权限和账号配置 | `quote_source=contract` |
| PAC | 接入门槛较低、零售价格 | 不是客户合同价；不能静默作为合同价 fallback | `quote_source=retail` |
| **已选：合同价为核心；PAC 只有明确业务批准后作为独立能力** | 避免误报价格来源 | 账号不可用时只能 unavailable | Contract Adapter 可实现；PAC 保持禁止 |

### 3.6 Order Service orchestration

`OrderService.list_orders()` / `get_order()` 仍是订单读取与组合入口，不新增跨订单状态，但其返回类型按第 2.4 节分别冻结为 `OrderSummaryResult` 与 `OrderDetailResult`。Phase 6 获批后的详情编排契约为：

1. 读取并关联单一订单及 Product；
2. 独立执行 Package Estimation → Shipping Quote，以及 Tracking 查询；
3. Tracking 的失败只进入对应 `TrackingResult`，不得取消或降级 Shipping Quote；Shipping Quote 的失败也不得覆盖已成功的 Tracking；
4. Pricing Service 只调用一次，并且只接收 `shipping_quote.applied_fee`，不接收 Provider payload、Package 或 diagnostics；
5. Package/Quote 的预期外部失败转换为 `unavailable` 结果，不升级为订单级 500；本地数据完整性错误仍沿用现有安全异常边界；
6. 按 D-025/D-030，`list_orders()` 使用独立 summary 编排，不调用 `get_order()`、Package Estimation、Tracking 或 Quote Provider，返回 `quote_request_state=not_requested` 且不构造 `ShippingQuoteResult`；为保持既有 `order_total` 字段，只使用内部 Decimal `0.00` 计算等于 `order_subtotal + gst_amount` 的 `Total before shipping`。详情流程才允许请求报价，能力代码尚未实现期间详情继续保持 D-015。

这不是新业务 Service；它冻结现有 Order Service 与三个独立能力之间的依赖方向。

## 4. Package Contract

### 4.1 关系与数量守恒

`CONFIRMED`：Order 总会得到一个 Package Estimation Result；`available` 必须含一个或多个 Package，`unavailable` 必须为空。只有 estimation available 时可进入 Provider quote。

`CONFIRMED`（D-020）数量守恒：对每个 OrderItem，所有 PackageItem allocation 的 quantity 之和必须等于 OrderItem.quantity；不得丢失、重复、超额或跨订单分配 SKU。

`CONFIRMED`：Tracking Group 与 Package 无 ID、数量或一对一关系；未来真实业务数据可以另外提供关联，但不能从当前字段推断。

### 4.2 Actual 与 rules source

- `CONFIRMED actual`：真实装箱数据存在且通过验证时优先；provenance 指向批准的数据源/version。
- `CONFIRMED rules`：没有真实数据时使用确定性 rules；记录 ruleset ID/version/input fingerprint/evaluated_at。
- `CONFIRMED insufficient`：缺少必要规则或输入时 PackageEstimationResult unavailable，ShippingQuoteResult 随之 unavailable/zero fallback，不构造默认 Package。

### 4.3 Package ID

`CONFIRMED`：Package ID 是本次估算结果中的 opaque、订单内唯一标识。不得包含客户 PII、tracking number 或凭证；不得向其赋予承运商 article/consignment ID 语义。

### 4.4 Package Estimation Service

```text
PackagingRulesReader.get_active(at: UtcTimestamp) -> PackagingRuleSet

PackageEstimationService.estimate(
    order: Order,
    products: tuple[Product, ...],
    rules: PackagingRuleSet,
) -> PackageEstimationResult
```

- Reader 只返回一个经过验证、不可变的 active ruleset；缺失或重叠 active version 为配置失败。
- Estimation Service 是纯确定性计算，不读取 Tracking Repository、不调用 Provider、不计算运费。
- 输入 Product 只作为 SKU mapping 的查找和估算输入；未经规则明确转换不得成为 Package dimensions/weight。
- 成功结果必须满足 Package ID 唯一、数量守恒、材料与 capacity 约束；否则返回 unavailable，不返回部分 Package 集合作为报价输入。
- actual package source 的读取接口在真实数据源获批前保持未定义，不以业务 JSON 猜测。

## 5. Packaging Rules

### 5.1 冻结的最小 ruleset schema

以下结构是 D-021 批准的最小只读版本化契约；具体字段值、装箱算法和存储技术仍不由本文臆造：

```text
PackagingRuleSet
  ruleset_id: str
  version: str
  effective_from: UTC datetime
  effective_to: UTC datetime | null
  source_revision: str
  sku_specs: tuple[SkuPackagingSpec, ...]
  materials: tuple[PackageMaterialSpec, ...]
  policies: tuple[PackingPolicy, ...]  # priority ascending, ID tie-break

SkuPackagingSpec
  sku: str
  unit_weight_g: Decimal
  packed_unit_dimensions_mm: PackageDimensions
  compatible_material_ids: tuple[str, ...]
  handling_class: str | null

PackageMaterialSpec
  material_id: str
  inner_dimensions_mm: PackageDimensions
  outer_dimensions_mm: PackageDimensions
  tare_weight_g: Decimal
  max_gross_weight_g: Decimal

PackingPolicy
  policy_id: str
  priority: int
  match criteria
  allocation strategy
  material selection strategy
  split/mix constraints
```

> **Task 048 / D-032 更新**：上列 `PackingPolicy` 的散文字段已被 §5.4 的正式字段级 schema 取代。`PackagingRuleSet` 外层、`SkuPackagingSpec` 与 `PackageMaterialSpec` 的外壳仍由 D-021 与本节冻结；这两类记录新增的约束字段见 §5.5。

### 5.2 确定性与优先级

`CONFIRMED`：rules 必须可配置、可追溯、可测试，同一规范化输入和同一 ruleset version 必须得到相同 Package 结果。

`CONFIRMED` 优先级边界：真实装箱数据 > SKU-specific policy > handling-class policy > general policy；相同 priority 使用稳定 policy ID 排序。不得存在“任意选择第一个可用箱型”的非确定行为。具体 allocation strategy 必须来自已发布 ruleset。

### 5.3 缺失与版本

- 缺失 SKU packaging spec、material、tare weight、capacity 或 required policy：`PACKAGE_DATA_INCOMPLETE`，不生成报价。
- ruleset version 必须不可变；修改任何规格或算法创建新 version，不原地改写历史语义。
- 生效时间为 UTC；同一时刻最多一个 active version。
- 历史 quote 如未来持久化，必须关联 ruleset ID/version 和 input fingerprint。

实施前置输入：具体 SKU 包装规格、材料目录、capacity、orientation 和算法仍需获授权的数据。D-020 已批准 split/mix 模型能力。**Task 048 更新**：具体分配算法已由 D-034 冻结（§5.6），材料选择已由 D-035 冻结（§5.7），policy schema 已由 D-032 冻结（§5.4）；仍缺失的只有真实规则**数据**（SKU 包装规格、材料目录、capacity/tare、获批 ruleset）与治理权限（DEC-5 暂缓）。

D-021 要求规则保存在独立、只读、版本化配置中，不修改四个业务 JSON；具体存储路径可在不引入数据库、Redis或改变业务语义的实施设计中确定。缺少可用 ruleset 时 Shipping Quote 为 unavailable，不影响 Tracking。

### 5.4 `PackingPolicy` 正式字段级 Schema（D-032）

`CONFIRMED` / `FROZEN`（D-032，Task 048）。本节取代 §5.1 中 `PackingPolicy` 的散文字段。所有字段不可变、`extra="forbid"`；除明确标注可空者外**无默认值**，缺省即 ruleset 加载失败，避免隐式语义。

#### 5.4.1 字段与类型

| 字段 | 类型 | 必填规则 | 不变量与语义 |
|---|---|---|---|
| `policy_id` | 字符串，1..200，strip 后非空 | 是 | ruleset 内唯一；同层同 `priority` 时的稳定决胜键（Unicode 码点升序） |
| `priority` | 严格整数，≥0 | 是 | 同一 `scope` 内升序优先，数值越小越优先 |
| `scope` | 封闭枚举：`sku`、`handling_class`、`general` | 是 | 匹配层级；决定 scope 专属字段的必填性 |
| `sku` | 字符串，可空 | 当且仅当 `scope=sku` | 必须存在于同一 ruleset 的 `sku_specs`；其他 scope 出现即加载失败 |
| `handling_class` | 字符串，可空 | 当且仅当 `scope=handling_class` | 必须被至少一个 `SkuPackagingSpec.handling_class` 使用，否则为不可达策略，加载期拒绝 |
| `allocation_strategy` | 封闭枚举：`sequential_first_fit`、`best_fit_decreasing` | 是 | `best_fit_decreasing` 为 D-034 生产算法；`sequential_first_fit` 仅为 J1 语义回归对照，**不得**作为生产默认（见 §5.8） |
| `material_selection` | 封闭枚举：`smallest_inner_volume`、`priority_order` | 是 | D-035 的排序策略（§5.7.3）；`priority_order` 要求 policy 覆盖范围内每个候选材料都有 `selection_priority` |
| `allow_split` | 布尔 | 是 | `false` 时一个订单行必须完整落在同一 Package |
| `max_units_per_package` | 严格整数，≥1，可空 | 是（可空） | `null` 表示不额外限制，仅受材料容量与重量约束 |
| `max_packages_per_order` | 严格整数，≥1，可空 | 是（可空） | 超出即整单 fail closed，不得继续装箱 |
| `allow_mixed_sku` | 布尔 | 是 | `false` 时一个 Package 只能含单一 SKU |
| `max_skus_per_package` | 严格整数，≥1，可空 | `allow_mixed_sku=true` 时必填且 ≥1；`false` 时必须为 `null` | 与 `allow_mixed_sku` 组合校验 |
| `fragile_mixing` | 封闭枚举：`allow`、`single_sku_only`、`alone_only` | 是 | 由 D-033 提供；仅当包内含 `fragility != none` 的物品时生效 |
| `max_package_gross_weight_g` | 正有限 Decimal（g），可空 | 是（可空） | 只能 ≤ 覆盖范围内每个材料的 `max_gross_weight_g`；违反即加载失败，不得放宽 |
| `max_package_outer_dimensions_mm` | `PackageDimensions`（mm），可空 | 是（可空） | 对覆盖范围内每个材料外尺寸**逐边**只能收紧；任一边大于材料外尺寸即加载失败 |

#### 5.4.2 匹配与优先级

```text
1. actual 真实装箱数据（存在且已验证时）优先于任何 rules 结果
2. rules 内匹配层级：scope=sku > scope=handling_class > scope=general
3. 同层级内：priority 升序 -> policy_id 字典序升序（稳定决胜）
4. 必须最终收敛为恰好 1 个 policy（多命中是正常收敛，见下；零命中即 fail closed）
```

`CONFIRMED`：**多 Policy 命中同一 SKU 是正常收敛**（分层策略按第 2、3 步取最优者），不是配置错误。**只有**「同 `scope`、同匹配键、同 `priority` 的两条 policy」才是配置错误，必须在 ruleset 加载期拒绝，禁止在运行期任选其一。

`CONFIRMED`：policy 选择**禁止**使用创建时间、文件名、发布顺序、`latest`、版本号大小、字典序之外的任何来源；也禁止模糊匹配、前缀匹配或按 SKU 文本相似度匹配。

#### 5.4.3 加载期校验清单

ruleset 加载时必须逐项校验；任一项失败即拒绝整个 ruleset（fail closed，不产生运行时估算结果）：

1. `policy_id` 在 ruleset 内唯一；
2. `scope` 在封闭枚举内，且 scope 专属字段的必填/禁止规则被满足；
3. `scope=sku` 的 `sku` 存在于同一 ruleset 的 `sku_specs`；
4. `scope=handling_class` 的 `handling_class` 至少被一个 `SkuPackagingSpec` 使用（可达性）；
5. 同 `scope` + 同匹配键 + 同 `priority` 唯一；
6. `allocation_strategy`、`material_selection`、`fragile_mixing` 在封闭枚举内；
7. `max_package_gross_weight_g` ≤ policy 覆盖范围内每个可能被选中材料的 `max_gross_weight_g`；
8. `max_package_outer_dimensions_mm` 对同一覆盖范围逐边 ≤ 材料 `outer_dimensions_mm`；
9. `allow_mixed_sku` 与 `max_skus_per_package` 组合合法；
10. `material_selection=priority_order` 时，覆盖范围内每个候选材料都有 `selection_priority`；
11. 所有数值为严格整数或 `Decimal`；拒绝 `float`、字符串数字、`NaN` 与无穷值。

**覆盖范围**定义：`scope=sku` → 该 SKU 的 `compatible_material_ids` 解析出的材料；`scope=handling_class` → 所有使用该 class 的 SKU 的 `compatible_material_ids` 解析出的材料；`scope=general` → ruleset 中全部材料。若覆盖范围为空，视为配置错误（无可选材料），加载期拒绝。

#### 5.4.4 拆分与混装字段语义

| 字段 | 冻结语义 | 违反时行为 |
|---|---|---|
| `allow_split` | `false` 表示一个订单行的全部数量必须落在同一 Package | 需要拆分时先尝试可容纳整行的更大材料；仍不可行则整单 fail closed |
| `max_units_per_package` | 单个 Package 内 unit 数量上限（unit = 单件包装单元） | 达到上限后不得继续装入该 Package，必须开新 Package 或 fail closed |
| `max_packages_per_order` | 单个订单允许的 Package 数量上限 | 超出即整单 fail closed，不得继续装箱或截断订单行 |
| `allow_mixed_sku` | `false` 表示一个 Package 内只能有一个 SKU | 已在包内的其他 SKU 不参与该包候选；无法安置则开新包或失败 |
| `max_skus_per_package` | 单个 Package 内 SKU 种类上限 | 加入新 SKU 前检查；超限即不得混装 |
| `fragile_mixing` | 含 fragile 物品时的混装许可：`allow` 允许混装；`single_sku_only` 只允许同一 SKU；`alone_only` 必须单独成包 | 违反即拒绝该组合；无法拆分安置则整单 fail closed |
| `max_package_gross_weight_g` | 有效毛重上限（含皮重），只能收紧材料上限 | 超限即该 material-package 不可继续装入 |
| `max_package_outer_dimensions_mm` | 有效外尺寸上限，只能收紧材料外尺寸 | 超限即该材料不可用于该 policy |

危险品混装规则由 D-033 §5.5.2 与 D-035 §5.7 共同约束：`hazardous=true` 与 `hazardous=false` 的物品默认不得同包，且材料必须 `hazmat_approved`。

#### 5.4.5 零匹配与缺失行为（fail closed 矩阵）

| 情形 | 行为 | 公共 reason code | 内部诊断 category |
|---|---|---|---|
| 无 Active ruleset | fail closed，不构造任何 Package | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured`（沿用 J1） |
| ruleset 存在但 `policies` 为空 | fail closed | `PACKAGE_DATA_INCOMPLETE`（沿用 J1 现状） | `rules_not_configured` |
| 订单任一 SKU 无任何 policy 匹配 | fail closed；**禁止**回退到其他规则或猜测 | `PACKAGE_DATA_INCOMPLETE` | `policy_unmatched` |
| 匹配 policy 被 SKU spec / 材料缺失阻塞 | fail closed | `PACKAGE_DATA_INCOMPLETE` | `sku_spec_missing` 或 `material_missing` |
| policy 字段非法 / 枚举越界 / 放宽硬约束 | ruleset 加载期拒绝，不产生运行时结果 | 不适用（配置加载失败） | 配置加载异常 |
| policy 声明的策略未实现 | fail closed | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured` |
| ruleset 为 synthetic | 仅测试路径允许；默认应用永不注入 | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured` |

`CONFIRMED`：**不新增公共 reason code**。`policy_unmatched` 等只是内部 `PackageDiagnosticCategory`，不进入公共 API。容量不足与 split 策略冲突继续统一映射为 `PACKAGE_DATA_INCOMPLETE`（Task 046 F-07 保留，见 §5.6.10）；若业务要求公开区分，必须另行获批新增 reason code（受 D-024 约束）。

#### 5.4.6 AP-1.1～AP-1.7 落地位置

| 批准项 | 落地章节 |
|---|---|
| AP-1.1 字段、类型、必填、无默认值 | §5.4.1 |
| AP-1.2 封闭枚举集合 | §5.4.1、§5.4.3 第 6 项 |
| AP-1.3 优先级与唯一解析 | §5.4.2 |
| AP-1.4 零匹配即 fail closed、禁止隐式默认 | §5.4.5 |
| AP-1.5 拆分/混装语义与组合校验 | §5.4.4、§5.4.3 第 9 项 |
| AP-1.6 只能收紧、放宽即加载期拒绝 | §5.4.1、§5.4.3 第 7/8 项 |
| AP-1.7 缺失矩阵与不新增 reason code | §5.4.5 |

### 5.5 包装约束归属与 `EffectiveConstraintView`（D-033）

`CONFIRMED` / `FROZEN`（D-033，Task 048）。

#### 5.5.1 三处归属

| 归属 | 承载对象 | 记录什么 | 不得记录什么 |
|---|---|---|---|
| 物品事实 | `SkuPackagingSpec.handling` | 该包装单元的方向策略、易碎等级、堆叠能力、危险品标识与分类引用 | 容器尺寸、承重、业务拆分策略 |
| 容器能力与上限 | `PackageMaterialSpec` | 内外尺寸、皮重、最大毛重、材质类型、可用状态、危险品/缓冲/方向能力、选择优先级 | 某个 SKU 该不该装它 |
| 业务策略（只能收紧） | `PackingPolicy` | 有效毛重上限、外尺寸上限、易碎混装许可、拆分/混装上限 | 物品事实、容器物理能力，或任何**放宽**值 |

#### 5.5.2 约束逐项归属、表达与执行点

| 约束 | 归属与字段 | 类型表达 | 执行点 | 违反时行为 |
|---|---|---|---|---|
| Orientation | SKU `handling.orientation_policy`（物品事实）+ 材料 `orientation_supported`（容器能力） | 物品：`any`、`upright_only`、`fixed`；材料：`any`、`upright_only` | 候选材料过滤 + 放置方向枚举（§5.6.3） | 无可行方向即该 unit 不可装，整单 fail closed |
| Fragile | SKU `handling.fragility` + 材料 `cushioned` + policy `fragile_mixing` | `none`、`fragile`、`very_fragile`；布尔；`allow`、`single_sku_only`、`alone_only` | 混装裁决（§5.6.6） | 违反即拒绝该混装组合；无法安置则 fail closed |
| Stackability | SKU `handling.stacking`（物品事实）+ Package 级**派生**结论 | `{stackable: bool, max_stack_units: int 可空, max_top_load_g: Decimal 可空}` | Package 构造后派生；取所含物品最严值 | Package `stackable=false` 仍可装箱，但必须如实保留派生结论；J2 不做堆叠载荷物理建模 |
| Hazardous Goods | SKU `handling.hazardous` + `handling.hazard_class_ref`（物品事实）+ 材料 `hazmat_approved` | 布尔 + opaque 字符串引用 | 候选材料过滤 + 混装裁决 | 危险品与非危险品默认不得同包；材料未获危险品许可见不可选 |
| Weight Limit | 材料 `max_gross_weight_g`（硬上限）+ policy `max_package_gross_weight_g`（收紧） | 正有限 Decimal（g） | 每次加入 unit 前预投影（§5.6.5） | 超限即不可装；无可行材料则 fail closed |
| Dimension Limit | 材料 `inner_dimensions_mm`（容量）/`outer_dimensions_mm`（物理外尺寸）+ policy `max_package_outer_dimensions_mm`（收紧） | `PackageDimensions`（mm / mm³） | 容积预筛与轴对齐可行性检查（§5.6.4） | 同上 |
| Material Compatibility | SKU `compatible_material_ids`（白名单）∧ 材料能力字段 | 字符串元组 / 各能力字段 | 候选材料过滤（§5.7.2 F1、F4、F5） | 交集为空即该 SKU 不可装，fail closed，不得回退 |

`CONFIRMED`：`hazard_class_ref` 只是引用，其取值必须来自业务/合规方批准的目录。工程**不得**自行定义 UN 编号、危险品等级或法规分类，也不得由商品属性推断危险品。

#### 5.5.3 `SkuPackagingSpec` 与 `PackageMaterialSpec` 新增字段

在 §5.1 外壳基础上冻结以下新增字段（字段名固定）：

| 记录 | 新增字段 | 类型与校验 |
|---|---|---|
| `SkuPackagingSpec` | `handling.orientation_policy` | 封闭枚举 `any`、`upright_only`、`fixed` |
| `SkuPackagingSpec` | `handling.fragility` | 封闭枚举 `none`、`fragile`、`very_fragile` |
| `SkuPackagingSpec` | `handling.stacking.stackable` | 布尔 |
| `SkuPackagingSpec` | `handling.stacking.max_stack_units` | 严格整数 ≥1，可空（仅 `stackable=false` 时必须为 `null`） |
| `SkuPackagingSpec` | `handling.stacking.max_top_load_g` | 正有限 Decimal（g），可空（仅 `stackable=false` 时必须为 `null`） |
| `SkuPackagingSpec` | `handling.hazardous` | 布尔 |
| `SkuPackagingSpec` | `handling.hazard_class_ref` | opaque 字符串，可空；`hazardous=true` 时必填，`false` 时必须为 `null` |
| `PackageMaterialSpec` | `material_type` | 封闭枚举 `carton`、`satchel`、`padded_bag`、`tube`、`other` |
| `PackageMaterialSpec` | `availability_status` | 封闭枚举 `active`、`retired` |
| `PackageMaterialSpec` | `hazmat_approved` | 布尔 |
| `PackageMaterialSpec` | `cushioned` | 布尔 |
| `PackageMaterialSpec` | `orientation_supported` | 封闭枚举 `any`、`upright_only` |
| `PackageMaterialSpec` | `selection_priority` | 严格整数 ≥0，可空；`material_selection=priority_order` 时必填 |

`CONFIRMED`：`orientation_policy=fixed` 时，`packed_unit_dimensions_mm` 的三边顺序即为**声明的允许方向**；算法不得重排该方向。`upright_only` 允许绕竖直轴旋转（长宽互换，高度固定）；`any` 允许任意轴对齐排列。

新增材料的逐边关系校验：除 §5.1 已冻结的 `outer.volume_mm3 ≥ inner.volume_mm3` 外，`outer` 的每一边必须 ≥ `inner` 对应边。

#### 5.5.4 约束合并规则

派生 `EffectiveConstraintView` 时按下式取最严值；任何一步缺少合法输入即 fail closed：

```text
effective_max_gross_weight_g      = min(material.max_gross_weight_g, policy.max_package_gross_weight_g 若声明)
effective_max_outer_dimensions_mm = 逐边 min(material.outer_dimensions_mm, policy.max_package_outer_dimensions_mm 若声明)
effective_orientation_supported   = most_restrictive(material.orientation_supported, sku.handling.orientation_policy)
effective_mixing_allowed          = policy.allow_mixed_sku
                                    AND (无 hazardous 与非 hazardous 同包)
                                    AND (fragile_mixing 规则满足)
                                    AND (sku 种类数 <= policy.max_skus_per_package)
effective_material_compatibility  = sku.compatible_material_ids
                                    AND material 能力字段（cushioned / hazmat_approved / orientation_supported）
effective_split_allowed           = policy.allow_split
                                    AND (unit 数 <= policy.max_units_per_package 若声明)
                                    AND (package 数 <= policy.max_packages_per_order 若声明)
```

`most_restrictive` 顺序固定为 `fixed` > `upright_only` > `any`。

#### 5.5.5 禁止事项

1. 禁止 policy 覆盖或放宽任何 SKU/材料硬约束；放宽在 ruleset 加载期拒绝。
2. 禁止隐式忽略约束（例如「该项缺失就跳过」）；缺失即 `PACKAGE_DATA_INCOMPLETE`。
3. 禁止把 `EffectiveConstraintView` 持久化、写入 `PackageProvenance`、暴露到 API 或作为新的公共数据实体。
4. 禁止新增第四个持久化领域实体（不存在独立 `ConstraintSet` 记录）。
5. 禁止用 `Product` 的重量、尺寸、体积、体积毛重或仓储容量推导任何约束（见 §5.5.6）。
6. 禁止工程自行发明危险品分类、UN 编号或法规等级。

#### 5.5.6 商品事实与包装事实分离

| 禁止 | 依据 |
|---|---|
| `Product.weight_g` 作为包装后重量 | D-019；§4.4；§16.2 |
| `Product.dimensions_mm` 作为 Package 尺寸 | D-019；§4.4；§16.2 |
| `Product.volume_mm3` 作为材料内腔容量 | D-019；§4.4 |
| `Product.volumetric_gross_weight_kg` 作为 chargeable weight | §6.2（口径无证据且不符合统一 250 kg/m³ 关系） |
| `Product.max_storage_per_container` 作为运输包装容量 | 仓储语义，非运输包装 |
| Tracking Group 数量或 ID 推导 Package | D-016；§4.1 |

`CONFIRMED`：估算链路**不得读取**上述任一 Product 物理字段；`products` 只用于 SKU 关联一致性校验。该约束必须由「读取即失败」的测试守卫验证（§13.2）。

#### 5.5.7 AP-2.1～AP-2.10 落地位置

| 批准项 | 落地章节 |
|---|---|
| AP-2.1 三处归属 + 派生视图、不新增实体 | §5.5.1、§5.5.5 第 4 项 |
| AP-2.2 OrientationPolicy 三态与尺寸方向约定 | §5.5.3、§5.6.3 |
| AP-2.3 Fragility 与 fragile_mixing | §5.5.2、§5.4.4 |
| AP-2.4 StackingConstraint 与 Package 级派生 | §5.5.2、§5.5.3 |
| AP-2.5 危险品表达与默认禁止混装 | §5.5.2、§5.5.3 |
| AP-2.6 Weight Limit 双层语义 | §5.5.2、§5.5.4 |
| AP-2.7 Dimension Limit 双层语义 | §5.5.2、§5.5.3、§5.5.4 |
| AP-2.8 Material Compatibility AND 语义 | §5.5.2、§5.5.4 |
| AP-2.9 约束不进入公共 API | §5.5.5 第 3 项、§9.3 |
| AP-2.10 材料侧新增字段 | §5.5.3 |

### 5.6 生产级确定性装箱算法（D-034）

`CONFIRMED` / `FROZEN`（D-034，Task 048）。生产算法为**分阶段确定性启发式 + Best-Fit Decreasing 放置**。它**不承诺**数学意义上的最优 3D 装箱，也**不是** J1 的 synthetic 顺序 first-fit（§5.8）。

#### 5.6.1 阶段、输入与输出

| 阶段 | 输入 | 处理 | 输出 | 失败条件 |
|---|---|---|---|---|
| Stage 0 Preflight | order、products、ruleset、policy | 校验 ruleset 已批准且非 synthetic、policy 唯一解析、SKU spec 与材料齐全、覆盖范围一致 | 已解析的 specs、材料集合、policy | 任一项缺失或非法 → 整单 `unavailable` |
| Stage 1 Unit 展开 | order lines | 按 `line_index` 顺序将每行按 `quantity` 展开为 unit；不合并、不丢行 | `(line_index, sku, unit_ordinal)` 列表 | 订单无行、`quantity ≤ 0`、products 与订单行不匹配 |
| Stage 2 确定性排序 | unit 列表 | 按 §5.6.2 排序键排序 | 有序 unit 列表 | 排序键不可比较（类型非法） |
| Stage 3 候选材料过滤 | 每个 unit + policy | 依次执行 §5.7.2 的 F1～F8，并记录每个 unit 的可行材料集合 | 每 unit 的候选材料有序列表 | 任一 unit 候选为空 → 整单 fail closed |
| Stage 4 Best-Fit 放置 | 有序 unit 列表 + 已开 Package | 选择「装入后剩余容积最小」的已开 Package；无可行已开 Package 时按 §5.7.3 选新材开包 | 已开 Package 集合及分配 | 新材选择无候选 / 超 `max_packages_per_order` |
| Stage 5 拆分与混装裁决 | 分配结果 + policy | 按 §5.4.4、§5.6.6 校验拆分与混装；违反时允许「开新 Package 一次」再判定 | 合法分配 | 仍违反 → 整单 fail closed |
| Stage 6 后校验与投影 | 合法分配 + ruleset | 数量守恒、Package ID 唯一、items 非空、材料合法性、毛重/尺寸上限、Package 级派生约束、provenance | `PackageEstimationResult`（available） | 任一不变量失败 |

各阶段失败即**整单**失败，不保留部分结果。

#### 5.6.2 排序键与 tie-breaker

```text
unit 排序键      = (-packed_unit_volume_mm3, -unit_weight_g, sku, line_index, unit_ordinal)
material 排序键  = §5.7.3 中 policy 声明的策略，末位恒为 material_id 字典序
policy 排序键    = (scope_rank, priority, policy_id)，scope_rank 为 sku=0 < handling_class=1 < general=2
Package ID       = 生成顺序 PKG-001..PKG-NNN
已开 Package 的 Best-Fit 决胜键 = (剩余容积, 已开顺序序号) 升序
```

`CONFIRMED`：`-` 表示降序。所有比较使用 Unicode 码点序，不使用 locale。Best-Fit 的「剩余容积」按 `effective_inner_volume_mm3 - 累计 packed unit volume` 计算，不做几何重排估算。

#### 5.6.3 方向枚举

| `orientation_policy` | 允许的轴对齐排列 | 说明 |
|---|---|---|
| `any` | 最多 6 种（三边全排列） | 每个排列都需通过三边可行性检查 |
| `upright_only` | 2 种（绕竖直轴 0°/90°，高度固定） | 高度方向不得改变 |
| `fixed` | 1 种（声明方向） | 不得重排三边 |

材料 `orientation_supported=upright_only` 时，即使物品为 `any`，有效方向集合收敛为 `upright_only`（§5.5.4 `most_restrictive`）。

#### 5.6.4 容积预筛与几何放置约束

- 容积预筛：`累计 packed unit volume + 本 unit volume ≤ material.inner_dimensions_mm.volume_mm3`，作为**必要条件**。
- 几何可行：存在至少一个允许方向，使 unit 三边均 ≤ 材料内腔对应边（逐边比较）。容积通过不构成几何可装证明。
- 禁止：任意角度旋转、非轴对齐放置、精确 3D 装载几何/极值点算法、重量分布或重心建模。

#### 5.6.5 重量与皮重

每次加入 unit 前计算 `item_weight_g 累计 + 本 unit 重量 + material.tare_weight_g`，与 `effective_max_gross_weight_g` 比较。`gross_weight_g = item_weight_g + packaging_weight_g` 的 §2.3 不变量不变，皮重必须计入。

#### 5.6.6 拆分与混装裁决顺序

```text
1. allow_split=false 且该行已分散 => 先尝试可容纳整行的材料；仍不可行 => fail closed
2. max_units_per_package 达标 => 不得继续装入
3. allow_mixed_sku=false 且包内已有其他 SKU => 该包不可作为候选
4. max_skus_per_package 达标 => 不得加入新 SKU
5. 危险品与非危险品不得同包（材料必须 hazmat_approved）
6. fragile_mixing 三态裁决
7. max_packages_per_order 超限 => fail closed
```

#### 5.6.7 容量与数量上限

| 上限 | 来源 | 超限处理 |
|---|---|---|
| 单 Package unit 数 | `policy.max_units_per_package` | 不得继续装入；开新包或 fail closed |
| 单 Package SKU 种类 | `policy.max_skus_per_package` | 不得加入新 SKU |
| 单订单 Package 数 | `policy.max_packages_per_order` | 整单 fail closed，不截断 |
| 单订单 unit 总数 | 500（硬边界，D-034 冻结） | 整单 fail closed（`PACKAGE_DATA_INCOMPLETE`），不得无界扩张运行时间 |
| 单 ruleset 材料数 | 200（硬边界） | ruleset 加载期拒绝 |
| 每 unit 方向枚举 | ≤ 6 | 固定上界 |

#### 5.6.8 复杂度与性能边界

- 时间复杂度：`O(U × (M + P))`，`U` 为 unit 数，`M` 为材料数，`P` 为已开 Package 数；无回溯、无重启、无多轮优化。
- 参考预算（CI 门禁，随实现基线记录）：`U ≤ 50` 时 p95 ≤ 20 ms；`U = 500` 最坏 ≤ 200 ms。超预算视为性能回归失败，不得通过放宽算法语义修复。
- 内存：`O(U + P × 平均 items)`；不得缓存跨请求状态（D-026）。
- 禁止：递归穷举、随机重启、外部求解器、跨请求缓存。

#### 5.6.9 确定性禁止项

1. 禁止依赖 `set`/`frozenset` 迭代顺序做决策；需要遍历时先排序。
2. 禁止随机数、`hash()`、系统时间、locale 参与分配决策（时钟只用于 `checked_at`/`estimated_at`）。
3. 禁止依赖输入 `dict` 插入顺序；订单行顺序只由 `line_index` 决定。
4. 同输入 + 同 ruleset version + 同算法版本 ⇒ `packages` 序列与 `input_fingerprint` 逐字节相同。

#### 5.6.10 整单 fail-closed 与非最优声明

1. 任一 unit 无可行材料、任一阶段不变量失败 → 整单 `unavailable`，`packages=()`。
2. **绝不**返回部分 Package 集合作为报价输入（§4.4）。
3. **绝不**通过放大材料尺寸、放宽重量/方向、丢弃或合并 unit、超出 policy 拆分、改用白名单外或 synthetic 材料来「凑成功」。
4. 公共 reason code 仍只用 `PACKAGE_RULES_NOT_CONFIGURED` 与 `PACKAGE_DATA_INCOMPLETE`；细分原因只进内部诊断 category。
5. Task 046 F-07（容量不足与 split 冲突共用 `PACKAGE_DATA_INCOMPLETE`）继续保持，不在本决策擅自新增枚举。
6. 算法只在「尺寸可行性 + 轴对齐方向枚举」意义上保证可装，**不保证**装载率或最优性；该限制必须写入 J2 交付文档，且不得用新 reason code 表达。

#### 5.6.11 AP-3.1～AP-3.6 落地位置

| 批准项 | 落地章节 |
|---|---|
| AP-3.1 分阶段架构与 Best-Fit Decreasing | §5.6.1、§5.6.2 |
| AP-3.2 显式排序键与禁止不确定性来源 | §5.6.2、§5.6.9 |
| AP-3.3 性能边界与无求解器依赖 | §5.6.7、§5.6.8 |
| AP-3.4 整单 fail closed、禁止部分集合 | §5.6.10 |
| AP-3.5 J1 与生产算法区分及激活门禁 | §5.8 |
| AP-3.6 不承诺最优 3D 装箱 | §5.6.10 第 6 项 |

### 5.7 包装材料选择（D-035）

`CONFIRMED` / `FROZEN`（D-035，Task 048）。

#### 5.7.1 候选集

```text
candidates(unit, policy, ruleset) = ruleset.materials 中通过 F1..F8 的全部材料
```

材料只能来自当前生效 ruleset 的 `materials`。ruleset 加载期已校验 SKU 的 `compatible_material_ids` 全部存在（§5.1），运行期不得做「找不到就忽略」的容错。

#### 5.7.2 F1～F8 硬过滤（按序执行，全部为必要条件）

| 编号 | 过滤项 | 输入与判定规则 | 不通过处理 |
|---|---|---|---|
| F1 | 兼容性 | `material.material_id ∈ sku.compatible_material_ids` | 排除该材料 |
| F2 | 可用性 | `material.availability_status == active` | 排除该材料（`retired` 永不选中） |
| F3 | 危险品 | `sku.handling.hazardous=true` 时要求 `material.hazmat_approved=true` | 排除该材料 |
| F4 | 易碎 | `sku.handling.fragility != none` 且 policy 要求缓冲时，要求 `material.cushioned=true` | 排除该材料 |
| F5 | 方向 | `material.orientation_supported` 必须覆盖 `sku.handling.orientation_policy`（`most_restrictive` 后仍可行） | 排除该材料 |
| F6 | 容量 | 存在允许方向使 unit 三边均 ≤ `material.inner_dimensions_mm` 对应边 | 排除该材料 |
| F7 | 单位容量毛重 | `unit_weight_g + material.tare_weight_g ≤ min(material.max_gross_weight_g, policy.max_package_gross_weight_g 若声明)` | 排除该材料 |
| F8 | 业务外尺寸上限 | `material.outer_dimensions_mm` 逐边 ≤ policy 已声明的 `max_package_outer_dimensions_mm` | 排除该材料 |

`CONFIRMED`：F1～F8 全部为**必要条件**，任一不过即排除该材料；不得以「部分满足 + 加权打分」替代硬过滤。

#### 5.7.3 排序策略与 tie-breaker

| `material_selection` | 排序键（升序） | 必填字段 |
|---|---|---|
| `smallest_inner_volume` | `(inner_dimensions_mm.volume_mm3, outer_dimensions_mm.volume_mm3, tare_weight_g, material_id)` | 无额外必填 |
| `priority_order` | `(selection_priority, inner_dimensions_mm.volume_mm3, outer_dimensions_mm.volume_mm3, tare_weight_g, material_id)` | 覆盖范围内每个材料必须有 `selection_priority` |

`CONFIRMED`：末位恒为 `material_id` 字典序，保证同一 ruleset 内绝对确定。排序后取**第一个**候选；已开 Package 的 Best-Fit 选择仍按 §5.6.2 的剩余容积决胜。

#### 5.7.4 冲突处理

| 冲突 | 冻结处理 |
|---|---|
| 两种策略会选出不同材料 | 由 policy 明确声明一种策略；策略字段必填，无隐式默认 |
| 同策略下多个材料排序完全等价 | 末位 `material_id` 决胜 |
| 兼容性 ∧ 能力冲突 | 取交集；为空即 fail closed，不做优先级加权 |
| policy 上限 < 材料物理能力 | 取更严者（policy 收紧），不报错 |
| policy 上限 > 材料物理能力 | ruleset 加载期拒绝（视为试图放宽） |
| 材料 `availability_status=retired` | 不进入候选；若某 SKU 只剩 retired 材料 → fail closed |

#### 5.7.5 零候选 fail-closed

F1～F8 过滤后为空 → 整单 `unavailable`，公共 reason code 为 `PACKAGE_DATA_INCOMPLETE`，内部 category 为 `material_missing` 或 `capacity_exceeded`。不得返回部分 Package 集合，不得继续用其他 SKU 的材料。

#### 5.7.6 八项禁止 fallback（逐项冻结）

1. 禁止在 `compatible_material_ids` 之外选材（含「该 SKU 没有就直接用任意材料」）。
2. 禁止使用不在当前 ruleset `materials` 中的材料（含硬编码内置目录）。
3. 禁止 synthetic/测试夹具材料进入任何非测试路径。
4. 禁止「最接近尺寸」或模糊匹配（不得按体积差、边长差、相似度选材）。
5. 禁止因容量不足自动放大到更大材料后再放宽重量或方向约束。
6. 禁止跨 SKU 借用白名单（A 的白名单不得用于 B）。
7. 禁止在 `allow_split=false` 时通过换材料实现事实上的拆分。
8. 禁止一个 Package 内混用多种材料；若未来需要，必须新增决策。

#### 5.7.7 AP-4.1～AP-4.4 落地位置

| 批准项 | 落地章节 |
|---|---|
| AP-4.1 过滤顺序与硬过滤集合 | §5.7.2 |
| AP-4.2 两种封闭策略及完整 tie-break | §5.7.3 |
| AP-4.3 八项禁止 fallback | §5.7.6 |
| AP-4.4 单材料与材料来源约束 | §5.7.1、§5.7.6 第 2/8 项 |

### 5.8 Synthetic-only 与 Production Ruleset 边界

`CONFIRMED` / `FROZEN`（Task 045/046 冻结的安全边界，Task 048 以 D-032～D-035 补充生产侧定义；本任务不修改任何代码）。

#### 5.8.1 J1 已冻结的合成隔离（不得削弱）

1. `PackagingRuleSet.synthetic_only` 与 `PackingPolicy.synthetic_only` 为 `Literal[True]`：经校验的 synthetic ruleset **无法**声明自己为生产规则。
2. `PackageEstimationService` 保留纵深防御：拒绝非 synthetic ruleset 与非 synthetic policy，fail closed 为 `PACKAGE_RULES_NOT_CONFIGURED`。
3. 服务层拒绝以 `model_construct` 或其他方式绕过 Domain 校验的对象。
4. 默认应用注入 `StaticPackagingRuleSetReader(None)`，因此所有订单详情返回 `unavailable / PACKAGE_RULES_NOT_CONFIGURED`，`packages=[]`。
5. Synthetic fixtures 只存在于 `backend/tests/`，不得被 `backend.main` 或任何生产模块导入。
6. 不得默认创建包装规格、材料或生产 ruleset；不得用商品物理数据替代真实包装数据。

#### 5.8.2 Production Ruleset 的准入条件

一个 ruleset 要成为**可生产使用**，必须同时满足：

1. 使用 D-032～D-035 的字段级 schema（含 §5.5.3 的约束字段），通过 §5.4.3 的全部加载期校验；
2. 覆盖范围内 SKU 的包装规格、材料目录、皮重、最大毛重、能力字段全部来自已批准数据源（DM-01～DM-14）；
3. 具有 `ruleset_id`、不可变 `version`、`effective_from`（UTC）、`source_revision`；
4. 通过 Validator 与 Approver 签署（治理角色与审批流程属 **DEC-5，暂缓**；在此之前只能由显式配置装配，且默认应用不得启用）；
5. 通过 §13.2 的全部契约测试与真实数据验收（J2-G）。

#### 5.8.3 J2 实施必须新增的识别与门禁（契约要求，本任务不实现）

1. 独立的「已批准生产 ruleset」识别（不得复用或放宽 `synthetic_only`）；
2. 生产 ruleset 的只读 Reader 实现（与 `StaticPackagingRuleSetReader` 契约一致）；
3. 默认装配仍必须是「无生产 ruleset → `PACKAGE_RULES_NOT_CONFIGURED`」；
4. 生产与测试配置的物理/逻辑隔离，禁止共用可变全局；
5. `allocation_strategy=best_fit_decreasing` 与 `sequential_first_fit` 的不同实现路径，且后者不得成为生产默认。

#### 5.8.4 明确禁止的绕过方式

| 禁止 | 原因 |
|---|---|
| 把 `synthetic_only` 改为可配置或默认 `False` | 会回退 Task 046 F-02 的整改 |
| 用 `model_construct` 或关闭校验装配「生产」ruleset | 绕过 Domain 校验 |
| 把测试 fixtures 移入生产模块或默认装配 | 合成数据冒充生产 |
| 在默认 `main` 装配中注入任何真实/合成 ruleset | 无批准数据时不得产生包装结果 |
| 用 Product 重量/尺寸/体积填充 packaging spec | 违反 D-019 与 §4.4 |
| 因 D-032～D-035 获批就宣称生产数据就绪 | 决策冻结 ≠ 数据就绪 |

#### 5.8.5 DEC-5 / DEC-6 暂缓对契约的影响

- Packaging 配置治理（角色、审批、原子激活、rollback、审计、存储载体）仍为 `DEFERRED / NOT_APPROVED`；§8.4 的 Provider 配置治理契约**不**扩展到 Packaging。
- Batch J2-F（配置治理）不在当前授权范围；生产 ruleset 只能通过显式、受控的装配方式提供，默认应用不得启用。
- 多进程全局限流（DEC-6）仍为 `DEFERRED / NOT_APPROVED`；`InMemoryTrackingRateLimiter` 的单进程语义不变，多 worker/多实例部署与真实 Provider 激活仍被禁止。
- 两者都**不**阻塞 J2-B～J2-E 的离线实现，但阻塞生产激活与 J2-F 实施。

## 6. Weight & Pricing Contract

### 6.1 单位

| 边界 | 尺寸 | 重量 | 分类 |
|---|---|---|---|
| Product/Package Domain | mm / mm³ | g | DERIVED，延续现有模型 |
| Australia Post/StarTrack request | cm | kg | DERIVED，官方 Get Shipment Price |
| API Money | 不适用 | AUD Decimal String | CONFIRMED |

转换必须用 Decimal 精确执行：`mm / 10 -> cm`、`g / 1000 -> kg`，不得经过 float。单位转换本身不舍入。

### 6.2 实际、体积与计费重量

- `gross_weight_g`：商品分配重量 + 包装材料重量。
- `volumetric_weight_kg`：只在 Provider/account/product 的 cubing factor 和取整规则明确时计算。
- `chargeable_weight_kg`：只采用 Provider 明确规则或返回值；不得统一假设为 `max(actual, volumetric)`。
- 当前 Product 的 `volumetric_gross_weight_kg` 不符合统一 250 kg/m³ 关系，不得直接作为 Package chargeable weight。

`CONFIRMED`（D-029）边界：cubing factor、取整方向、最小重量、尺寸精度和 Provider input quantization 必须来自明确 Provider/Product/合同规则。官方字段长度不是业务舍入授权；缺少证据时拒绝生成正式报价并返回 unavailable。

推荐让 Provider 使用真实 Package dimensions/gross weight 定价；本系统只在合同明确要求时计算 provider-specific volumetric/chargeable weight。

### 6.3 Shipping Fee 与现有 Pricing

`CONFIRMED`：D-004、D-022 与 D-029 通过以下唯一金额链同时执行；任何步骤缺少证据或验证失败均 fail closed，不得进入下一步：

```text
Provider raw amount string + raw currency
  -> 按 Provider/Product/Contract 证据解析与验证为 Decimal（禁止 float）
  -> 保留单元 raw string/currency、precision_rule_ref、amount_semantics_ref
  -> 得到每个单元未经 D-004 舍入的 validated_total_cost_incl_gst
  -> 按稳定 Quote Unit 顺序用 Decimal 精确求和
  -> 得到内部 order_total_cost_incl_gst_exact
  -> 仅在此订单级边界按 D-004 使用 ROUND_HALF_UP 量化到 Decimal("0.01")
  -> 同时形成 quoted_fee == applied_fee == shipment_fee_input
  -> Pricing Service 再执行其既有 D-004 验证/量化（对两位输入为幂等）
  -> API Money 显式序列化为恰好两位 AUD Decimal String
```

金额字段边界：

- `raw_total_cost`/`raw_currency`：Provider 原始字符串事实，仅内部、`repr=False`，不进入 API/log；不得提前丢弃原始精度。
- `validated_total_cost_incl_gst`：按该 Provider/Product/合同规则验证后的单元 Decimal；保留 Provider 允许的精度，不使用通用 D-004 舍入代替 Provider 规则。
- `order_total_cost_incl_gst_exact`：所有必要单元 validated total 的 Decimal 精确和，仅内部诊断/计算中间值，不进入公共 API。
- `quoted_fee` 与 `applied_fee`：订单级 D-004 两位标准化后的同一个含 GST 金额；二者在 available 时必须相等。该定义细化 D-022，不把 Provider 原始精度伪装成 API Money。
- `pricing.shipment_fee`：Pricing Service 接收 `applied_fee`，必须与其相等；Pricing 的既有 `ROUND_HALF_UP` 不修改、不移除，也不得被 Provider Adapter 调用。
- `shipping_gst`：仅在第 2.2 节完整证据条件满足时，对单元 GST Decimal 精确求和后，在同一订单级展示边界量化为两位；它不加入 Pricing，不从 `total_cost` 反推。

Provider 专属的输入量化、最小计费单位或金额转换只能在明确的 `precision_rule_ref` 授权下发生，并必须先于单元验证完成；D-004 的 `ROUND_HALF_UP` 只在全部单元精确聚合后的订单级 Shipment Fee 边界使用。若 Provider 规则禁止这种 AUD 两位转换，或没有说明如何把其金额合法表示为 AUD minor units，则返回 `unavailable / PROVIDER_CONFIGURATION_MISSING`；若规则已存在但本次响应违反它，则返回 `unavailable / PROVIDER_RESPONSE_INVALID`。

商品 `gst_amount` 继续只按商品 subtotal 的 D-004 公式计算。不得把 `shipping_gst` 加入该字段或订单总额，不得从商品税率推导运费税。Australia Post 的已审阅证据只适用于对应 Australia Post Product；其他 Provider/Product 必须分别提供同等证据。

## 7. Quote Aggregation

### 7.1 All-or-nothing

`CONFIRMED`：

1. 必要报价单元集合非空且 unit ID 唯一；
2. 每个 Package 恰好分配到一个必要报价单元；
3. 全部单元 available 才能形成订单级 available；
4. 一个必要单元时，该单元 unavailable 的唯一公共 reason 成为订单级 reason；两个或更多必要单元进入调用阶段后任一失败时，订单级固定为 `unavailable / PARTIAL_QUOTE_FAILURE`、`quoted_fee=null`、`applied_fee=0.00`、`shipping_gst=null`；
5. 部分成功金额不得进入 Pricing；
6. 单元结果可保留为内部诊断，不默认进入 API。

### 7.2 空与重复单元

- 空必要单元集合：固定 `unavailable / QUOTE_UNIT_EMPTY`；不得调用 Provider。
- 重复 unit ID、重复 Package ID 或 Package 跨单元：固定 `unavailable / QUOTE_UNIT_DUPLICATE`；内部可另记 contract-violation category，但公共 reason 不变；不得调用 Provider。
- 重复请求：相同 fingerprint 在单次 API 请求内只执行一次。

### 7.3 全部成功聚合

`CONFIRMED`：Provider Money 字段先按 D-029 验证为符合该 Provider/Product 规则的 AUD Decimal，再按必要单元稳定顺序精确求和为内部 `order_total_cost_incl_gst_exact`，最后仅按第 6.3 节在订单级 D-004 边界量化一次，形成 API 可表示的 `quoted_fee`。不得转 float，不得把部分结果加入。

`CONFIRMED`：按 D-022，只有明确证明含 GST 语义的单元 `total_cost` 才能聚合；成功时订单级 `applied_fee = quoted_fee`。任何单元缺少金额、币种、total-cost GST 口径或精度证据时，按 all-or-nothing 返回 unavailable/zero fallback。独立 GST breakdown 不完整只使订单级 `shipping_gst=null`，不得形成部分 GST；它不否定已有证据证明含 GST 的完整 `total_cost`。

### 7.4 重试边界

- 认证、请求校验、package data、产品不可用和业务拒绝不自动重试。
- timeout、network、429、5xx 仅在 Provider/HTTP method 的安全性已确认后有限重试。
- Get Shipment Price 的 POST 幂等保证未在已审阅资料中确认；结果不确定的 timeout 默认不自动重放。
- 同一请求内可保留已成功单元用于诊断，但跨请求不得复用，除非缓存/有效期策略获批。

## 8. Tracking Contract

### 8.1 Models

#### `TrackingRequest`

| 字段 | 类型 | 分类 |
|---|---|---|
| `tracking_group_id` | str | CONFIRMED，内部关联 |
| `provider` | CarrierProvider | CONFIRMED，D-023 显式 mapping |
| `tracking_id` | str, repr false | CONFIRMED，来自 tracking.json |
| `requested_at` | UTC datetime | CONFIRMED |

#### `TrackingResult`

| 字段 | 类型 | 分类 |
|---|---|---|
| `tracking_group_id` | str | CONFIRMED |
| `provider` | CarrierProvider/null | CONFIRMED，D-031 条件可空 |
| `status` | ResultStatus | CONFIRMED |
| `reason_code` | TrackingReasonCode/null | CONFIRMED，D-024 |
| `checked_at` | UTC datetime | CONFIRMED |
| `provider_status` | str/null | DERIVED |
| `current_status` | NormalizedTrackingStatus/null | CONFIRMED，D-028 |
| `latest_event_at` | UTC/null | DERIVED |
| `events` | tuple[TrackingEvent] | CONFIRMED |

#### D-031 Provider 投影矩阵（冻结）

`provider` 条件可空，但合法组合唯一：

```json
{
  "provider": null,
  "status": "unavailable",
  "reason_code": "CARRIER_MAPPING_UNRESOLVED",
  "events": [],
  "provider_status": null,
  "current_status": null,
  "latest_event_at": null
}
```

- `CONFIRMED`：仅当 `provider=null`、`status=unavailable`、`reason_code=CARRIER_MAPPING_UNRESOLVED` 同时成立时，该结果合法；反向同样成立，`CARRIER_MAPPING_UNRESOLVED` 不得与具体 Provider 组合。
- `CONFIRMED`：其余所有结果（`available`、`unavailable` 的其他 reason、`unsupported`）必须具有具体 Provider。
- `CONFIRMED`：不得新增虚构 `UNKNOWN`/`unresolved` Provider enum，不得根据 carrier 展示文本、Tracking Group ID 或 tracking number 形状推断 Provider。
- `CONFIRMED`：`provider=null` 的结果必须保持 `events=[]`、`provider_status=null`、`current_status=null`、`latest_event_at=null`；不得构造事件、ETA 或 raw status。
- `CONFIRMED`：`CARRIER_MAPPING_UNRESOLVED` 是真实 `unavailable`，不是 `not_requested`，也不是 `unsupported`；Mapping failure 与 Shipping Quote failure 相互隔离。
- `CONFIRMED`：Provider 内部诊断、原始错误、HTTP 状态和凭证不得进入公开 `TrackingResult`；内部诊断只存在于 Integration/Service 边界内。
- `CONFIRMED`：Tracking Service 必须为每个唯一 Tracking Group 产生且仅产生一个公开结果。空 `tracking_results` 只有在订单不存在任何唯一 Tracking Group 时合法；API 不得用空数组掩盖 Mapping 错误。
- `CONFIRMED`：Mapping 预检失败（无 Active Release、无适用 Mapping、多个适用 Mapping）不得发出任何 Provider 请求；已确定 Provider 但 Account/Product Revision 配置无效时保留 Provider 并使用现有配置错误 reason（如 `PROVIDER_CONFIGURATION_MISSING`），不得归类为 Mapping Unresolved。

#### `TrackingEvent`

| 字段 | 类型 | 分类 |
|---|---|---|
| `event_time` | UTC datetime | DERIVED；来自 Provider event time |
| `location` | str/null | DERIVED；可能缺失 |
| `description` | str | DERIVED；验证后展示 |
| `provider_status` | str/null | DERIVED |
| `normalized_status` | enum | CONFIRMED，D-028 |

冻结 normalized statuses：`pending`, `ready_for_pickup`, `in_transit`, `out_for_delivery`, `awaiting_collection`, `delivered`, `delivery_exception`, `cancelled`, `unknown`。按 D-028，未知 Provider status 映射 `unknown` 并保留安全 raw status，不从描述文本猜测。

冻结 Tracking reason codes：`CARRIER_NOT_IMPLEMENTED`、`PROVIDER_CONFIGURATION_MISSING`、`CARRIER_MAPPING_UNRESOLVED`、`PROVIDER_AUTHENTICATION_FAILED`、`PROVIDER_TIMEOUT`、`PROVIDER_NETWORK_ERROR`、`PROVIDER_RATE_LIMITED`、`TRACKING_ID_INVALID`、`PRODUCT_NOT_TRACKABLE`、`PROVIDER_RESPONSE_INVALID`、`PROVIDER_ERROR`。

#### `ProviderTrackingResult` 与 `TrackingProviderError`（内部）

`CONFIRMED`：`ProviderTrackingResult` 按单个 request item 返回 Provider 成功数据或分类失败，至少包含 request item index、provider status、事件 tuple、Provider 时间和 `TrackingDiagnostic | None`；它不能直接作为公共 `TrackingResult` 返回。

`CONFIRMED`：`TrackingProviderError` 是 Integration Layer 的分类异常族，至少区分 configuration、authentication、timeout、network、rate limit、invalid request、invalid response 和 provider error，并携带 `retryable` 与安全 diagnostic。Tracking Service 必须把它映射为稳定 reason code；异常文本、HTTP headers/body、凭证和完整 tracking ID 不得越过 Integration Layer。公共 API 不新增独立 ErrorResponse 形态来表达单个外部查询失败。

#### `TrackingDiagnostic`（内部）

字段与 `ProviderDiagnostic` 相同，另外允许记录批次内的安全 item index；不得记录完整 tracking ID 或 Provider raw response。公共 `TrackingResult` 只携带稳定 reason code。

### 8.2 Provider 与批处理

```text
TrackingProvider.track(batch: tuple[TrackingRequest, ...])
    -> tuple[ProviderTrackingResult, ...]
```

- `DERIVED`：Australia Post 与 StarTrack 不允许混合在同一 Track Items request。
- `DERIVED`：每批最多 10 个 IDs；Track Items 每分钟最多 10 次请求。
- `CONFIRMED`：当前 `StarTrack / Australia Post` 合并 carrier 文本不能直接选择 Provider；不得根据 tracking number 形状猜测。
- `CONFIRMED`（D-023）：每个 tracking group 必须通过独立显式配置获得 Provider/Account/Product mapping；当前具体 mapping 值属于实施输入，缺失时按 D-031 返回 `unavailable / CARRIER_MAPPING_UNRESOLVED`，不得猜测。
- `CONFIRMED`（D-031）：Mapping preflight 必须在任何 Provider 请求之前完成；零个或多个适用 Mapping、或没有可用 Active Release，均产生 provider-null unavailable，且不得发出部分或全部 Provider 请求。
- `CONFIRMED`：Tracking Group 只组织追踪关联，不与 Package 或 Quote Unit 合并。
- `CONFIRMED`：无事件但响应有效是 available empty result，不是 unavailable；不得构造事件。

### 8.3 Tracking Service

```text
TrackingService.track_order(
    groups: tuple[TrackingGroup, ...],
) -> tuple[TrackingResult, ...]
```

Service 负责读取 D-023 显式 provider mapping、按 Provider 分批、请求内去重、结果顺序恢复、D-028 raw/normalized status 映射和 D-024 reason-code 映射；Provider 只负责单一承运商批次的外部协议。一个 group 失败不取消其他 group，也不影响 Shipping Quote。

`CONFIRMED`（D-031）：Service 的 Mapping preflight 失败不得作为订单级异常抛出，也不得返回空数组；它必须转换为该 group 的 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED` 结果，并保持零 Provider 请求。Default 应用即使没有任何已批准 Mapping/Release，也必须具备 Tracking Service 并返回该结果；不得用 Fake Adapter、虚构账号/凭证/映射或真实外呼替代。

### 8.4 Provider configuration 与认证

D-023 的显式 mapping 使用 Task 034 冻结的 `Stable ID + Immutable Revision ID + Configuration Release` 模型。Stable ID 只标识逻辑实体；真实请求只能使用 Active Release 捕获并显式引用的不可变 Revision。不得按 `latest`、最高版本号、创建时间或任意 active 记录推断版本。所有 ID 均为服务端 opaque ID，不含凭证、客户 PII、tracking number 或真实 secret。

`CONFIRMED`（Task 042，T041-M01）：五种 Revision ID 必须各自独立决定其完整配置内容，完整性不得由 `(provider_revision_id, account_revision_id, product_revision_id)` 三元组替代：

```text
provider_revision_id -> 唯一、不可变的 ProviderRevision 内容
account_revision_id  -> 唯一、不可变的 AccountRevision 内容
product_revision_id  -> 唯一、不可变的 ProductRevision 内容
mapping_revision_id  -> 唯一、不可变的 MappingRevision 内容
release_revision_id  -> 唯一、不可变的 Release 内容
```

同一 ID 的相同内容可幂等读取；同一 ID 的不同内容必须拒绝。Release 内同一 ID 出现两份不同内容即拒绝；发布目录（append-only revision repository）对跨 Release 的同一 ID 也必须拒绝内容变化。不得因为其他 Revision ID 不同而绕过本实体的不可变性。Active Release 指针仍是唯一允许变化的激活引用。

#### `ProviderIdentity`

| 字段 | 规则 |
|---|---|
| `provider_id: CarrierProvider` | 稳定逻辑 ID；首批枚举为 australia_post/startrack/tnt |
| `provider_revision_id: str` | 全局唯一、不可变；配置变化必须创建新 Revision |
| `adapter_key: str` | 在 Adapter registry 中唯一，不是展示名称 |
| `display_name: str` | 仅展示，不参与选择 |
| `environment: testbed | production` | 环境显式隔离，不默认 production |
| `base_url: str` | 受控配置；不含认证信息 |
| `capabilities: frozenset[tracking | shipping_quote]` | 声明配置能力；仍须与已实现 Adapter capability 交叉验证 |
| `source_revision/evidence_ref` | 非空、可追溯；Revision 创建后不可原地改变语义 |
| `validation_status/validated_at` | 只有 verified Revision 才能进入 Release |
| `credential_ref` | `repr=False` 的安全配置引用；secret 本体不属于该 model |
| `connect_timeout/read_timeout` | 有限正值；实际值为实施输入 |

`provider_revision_id` 唯一确定全部字段；同一 Revision 不得覆盖。Stable `provider_id` 可有多个历史 Revision，但一次请求只使用 Release 固定的一个 Revision。

#### `ProviderAccount`

| 字段 | 规则 |
|---|---|
| `account_id: str` | 服务端稳定逻辑 ID；公共 API/log 不输出真实 account number |
| `account_revision_id: str` | 全局唯一、不可变；配置变化创建新 Revision |
| `provider_revision_id/environment` | 显式引用同环境 Provider Revision；不得运行时重选 Provider 版本 |
| `external_account_ref` | 安全受控引用，`repr=False`；不存凭证 |
| `origin_id: str` | 引用批准的 ProviderOrigin |
| `source_revision` | 不可变配置追溯 |
| `validation_status` | `unverified | verified | invalid` |
| `validated_at/evidence_ref` | verified 时必填；来自 Get Accounts 或等价受控证据 |
| `capabilities` | 已验证的 tracking/quote 能力集合 |

`account_revision_id` 唯一确定全部字段。只有 verified 且 capability 已验证的 Account Revision 可进入 Release；unverified/invalid 固定 fail closed 为 `PROVIDER_CONFIGURATION_MISSING`。

#### `ProviderProduct`

| 字段 | 规则 |
|---|---|
| `product_id: str` | 内部稳定逻辑 ID，与 Provider service code 分离 |
| `product_revision_id: str` | 全局唯一、不可变；配置变化创建新 Revision |
| `provider_revision_id/environment` | 显式引用同环境 Provider Revision |
| `service_code: str` | Get Accounts/合同验证后的 Provider code，不从订单或 tracking 猜测 |
| `quote_source` | 首批固定 `contract`；PAC 不得配置成 fallback |
| `currency` | 首批固定 AUD |
| `capabilities` | product 支持的 quote/tracking capability |
| `gst_semantics_ref` | D-022 total/GST 字段证据；Quote 启用时必填 |
| `precision_rule_ref` | D-029 精度/舍入证据；Quote 启用时必填 |
| `source_revision` | 不可变配置追溯 |
| `validation_status/validated_at/evidence_ref` | 只有 verified Revision 可进入 Release |

`product_revision_id` 唯一确定全部字段；同一 Release 内 `(provider_revision_id, environment, service_code)` 唯一。Account 无该 Product 权限或 Product Revision invalid/unverified 时固定 `PRODUCT_NOT_AVAILABLE`。

#### `ProviderProductMapping`

| 字段 | 规则 |
|---|---|
| `mapping_id: str` | stable logical ID |
| `mapping_revision_id: str` | 全局唯一、不可变；任何 mapping 变化创建新 Revision |
| `capability` | `shipping_quote | tracking`；两种能力不得隐式复用 mapping |
| `provider_revision_id/account_revision_id/product_revision_id` | 三个精确 Revision 外键；不得只按 stable ID 寻找 latest |
| `provider_id/account_id/product_id` | 保留为逻辑分组和审计字段，必须与所引用 Revision 一致；不参与版本选择 |
| `environment/origin_id` | 与 Provider、Account 一致；Quote mapping 必填 origin |
| `selection_scope` | 版本化、已批准的安全选择条件；不得读取 carrier 展示文本、tracking number 形状或 Tracking Group 来选择 Quote Provider |
| `source_revision/evidence_ref` | 可追溯，Revision 不可原地修改 |
| `validation_status/validated_at` | 只有 verified Revision 可进入 Release；是否生效仅由 Release membership + Active Release 决定，不设独立 latest/active fallback |

同一 Configuration Release 中，同一 capability 和 selection scope 必须恰好解析一个 Mapping Revision；零个或多个匹配均固定为 `CARRIER_MAPPING_UNRESOLVED`，禁止任意选择。Quote mapping 必须把每个 Package 恰好分配到一个必要 Quote Unit；`quote_unit_id` 由本次订单、`mapping_revision_id` 和稳定 Package 集合生成 opaque 请求内 ID，绝不使用 Tracking Group ID。Tracking mapping 可以以明确配置的 tracking-group safe reference 作为选择条件，但不得反向影响 Package 或 Quote mapping。

#### `ProviderConfigurationRelease`

| 字段 | 规则 |
|---|---|
| `release_id: str` | 稳定逻辑 ID |
| `release_revision_id: str` | 全局唯一、不可变，唯一确定 Release 内容 |
| `environment/configuration_scope` | Active 指针的隔离边界 |
| `mapping_revision_ids: tuple[str, ...]` | 非空、稳定排序，只引用 verified Mapping Revision |
| `approval_status/approved_at/approval_ref` | 只有 approved Release 可激活；记录审批证据 |
| `created_at/source_revision/audit_ref` | UTC、不可变、可追溯，不含凭证 |

`ActiveConfigurationPointer` 至少包含 `environment`、`configuration_scope`、`active_release_revision_id`、`activated_at` 和 `activation_audit_ref`。每个 `(environment, configuration_scope)` 同一时刻只能有一个指针值和一个 Active Release。Active 指针切换必须原子完成；切换失败时原 Release 保持 Active，不允许部分 Provider 使用新 Release、其他 Provider 使用旧 Release。Release 内每个 Mapping Revision 必须交叉验证其 Provider/Account/Product Revision、环境、capability、Contract Product、GST/精度证据和 Account 权限。

#### `ResolvedQuoteUnitMapping`

```text
release_revision_id
mapping_revision_id
provider_revision_id
account_revision_id
product_revision_id
selection_scope
environment
resolved_at
```

该对象是 Capability Preflight 和 Provider Request 的唯一配置依据。Provider 请求阶段不得再次使用 stable ID 解析版本；内部 diagnostic/provenance 必须记录上述 Revision ID，但不得记录凭证、原始 Provider payload 或敏感配置内容。

#### Reader / Registry 契约

```text
ProviderConfigurationReleaseReader.get_active(environment, configuration_scope, at)
    -> ProviderConfigurationRelease
ProviderProductMappingReader.resolve(release_revision_id, capability, selection_scope)
    -> ProviderProductMapping
ProviderReader.get_revision(provider_revision_id) -> ProviderIdentity
ProviderAccountReader.get_revision(account_revision_id) -> ProviderAccount
ProviderProductReader.get_revision(product_revision_id) -> ProviderProduct
ProviderProductMappingReader.resolve_quote(release_revision_id, order, packages, at)
    -> tuple[ResolvedQuoteUnitMapping, ...]
ProviderProductMappingReader.resolve_tracking(release_revision_id, group, at)
    -> ResolvedTrackingMapping
ProviderCapabilityRegistry.is_implemented(provider_revision_id, capability) -> bool
ProviderCapabilityValidator.validate(resolved_mapping, at) -> CapabilityValidationResult
```

确定性解析顺序冻结为：捕获唯一 Active Configuration Release → 在该 Release 内精确解析一个 Mapping Revision → 按显式 Revision ID 加载 Provider、Account、Product → 验证交叉引用和 capability → 构造 `ResolvedQuoteUnitMapping` → Capability Preflight → Provider Request。Readers 只读取已验证的版本化服务端配置，不读取 carrier 展示文本作为 Quote 选择依据。Capability Validator 不得发网络报价请求，也不得 fallback 到其他 Provider、Account、Product 或 PAC。

一次 Order Quote Request 在开始时只捕获一次 Active Release，并固定全部 Mapping/Provider/Account/Product Revision；同一订单所有必要 Quote Unit 必须使用同一 `release_revision_id`。Active Release 在执行中切换不影响已开始请求；新请求才使用新 Release，禁止在多个 Unit 之间重新解析 Active Release。

具体账号、service code、selection scope 值、Revision 内容、Active Release、凭证、timeout 和验证证据仍是 `IMPLEMENTATION_INPUT_REQUIRED`，本文不虚构任何真实值。API key/secret 为独立敏感配置，不进入上述普通 model dump/repr、API、日志或诊断对象。

#### Configuration publication、activation 与 rollback

发布必须依次完成：创建不可变 Revision；校验 schema/必填字段；校验 Provider/Account/Product Revision 外键；校验 Mapping/selection scope 唯一性；验证 Account 权限与 Get Accounts 证据；验证 Contract Product、GST、精度、Ruleset、Provider capability 和环境；完成审批；生成不可变 Release；原子切换 Active 指针；记录发布审计。未审批或未验证的 Revision 不得进入 Release，凭证不得进入 Git、公开文档或普通配置记录。

Rollback 只能通过原子重新激活先前已批准的不可变 Release 完成，不得原地修改或删除历史 Revision，不得改写历史 Mapping，也不得使用隐式 latest fallback。每次 rollback 必须记录原 Active Release、目标 Release、UTC 操作时间、操作主体、原因、审批引用和审计引用；切换失败时保持原 Active Release。

在途请求继续使用启动时固定的 Revision；切换或 rollback 不改变已开始请求，新请求使用切换后的 Release。请求内诊断及必要 provenance 保存 `release_revision_id` 和实际 Mapping/Provider/Account/Product Revision ID，且不得在一次报价的多个 Unit 之间重新解析配置。

Configuration Revision、Release 及发布/rollback 审计属于配置治理数据，不是 Quote History。它们不授权 Quote History、跨请求 Quote Cache、PAC 或 D-026/D-027 排除的其他能力，也不保存 Provider 报价结果。

Task 028 官方资料的 `DERIVED` 约束继续有效：

- Shipping and Tracking API 使用 HTTP Basic Authentication（API key + secret）及需要时的 `Account-Number`；已审阅资料没有 OAuth 流程。
- Australia Post account 以 10 位形式发送，StarTrack account 为 8 位且不补零。
- testbed 与 production 配置必须显式分离；不得默认 production。
- testbed 使用通用合同、不同 product IDs 和模拟 Tracking，不能证明真实合同价或生产可用性。
- Provider/account/product 权限必须通过 Get Accounts/受控环境验证，不能由环境变量存在性推断。

## 9. API Contract

### 9.1 兼容原则

- 现有 `/api/v1/orders`、`/api/v1/orders/{order_number}`、`{"data":...}` 和 ErrorResponse 不删除、不改名。
- Money 保持两位 AUD string；时间为 RFC 3339 UTC aware datetime。
- 外部 Provider 失败作为 200 成功 envelope 内的 unavailable result 表达，不转成全局 500。
- 本地数据损坏/内部未分类错误继续使用现有 ErrorResponse。
- 部分 quote diagnostics、Provider raw code、tracking number、Package rule internals和凭证不进入 API。
- D-025 不新增 endpoint：列表与详情仍使用现有路径，只通过协调发布的 additive/schema-union 扩展表达 request state 和结果。

#### Quote request state projection

| API 流程 | `quote_request_state` | Quote result | Provider 调用 |
|---|---|---|---|
| `GET /api/v1/orders` | `not_requested` | `shipping_quote_status=null`、`shipping_quote_reason_code=null` | 禁止 |
| `GET /api/v1/orders/{order_number}`，能力尚未实现 | `requested` | D-015 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED` | 不调用 Provider |
| 订单详情，必要 Provider Adapter 未实现 | `requested` | `unsupported / CARRIER_NOT_IMPLEMENTED` | Capability Preflight 禁止全部调用 |
| 订单详情，Package/mapping/config 预检失败 | `requested` | `unavailable` + 第 3.1 节唯一 reason | Capability Preflight 禁止全部调用 |
| 订单详情，真实调用成功 | `requested` | `available`（即 quoted） | 允许，受限流/timeout 约束 |
| 订单详情，真实调用失败 | `requested` | `unavailable` + D-024 reason | 一个或多个必要单元已尝试 |

`not_requested` 不进入 `ShippingQuoteResponse.status`，也不携带金额、checked_at 或 Provider reason。Phase 6 rollout 必须同步更新 Backend schema、OpenAPI 和 Phase 5 runtime validator；本任务不修改运行时代码。

列表中的现有 `order_total` 字段继续存在；按 D-030，在 `quote_request_state=not_requested` 时固定为 `order_subtotal + gst_amount`，表示 `Total before shipping`。列表 UI 必须同时说明 `Shipping quote not requested`，不得把该金额解释为最终含运费总额、零运费、免费运输或任何 fallback。详情返回的 PricingResult 才使用本次 `ShippingQuoteResult.applied_fee` 并成为包含报价降级/成功语义的详情权威结果；列表与详情金额不同是预期行为。

Phase 6 `OrderSummaryResponse` 保留现有订单标识、日期、公司、状态、item/unit count 和 `order_total: Money`，并协调增加以下公开字段：

```text
quote_request_state: Literal["not_requested"]
shipping_quote_status: null
shipping_quote_reason_code: null
```

该扩展不改变 `/api/v1/orders` 路径、`{"data": ...}` envelope、`order_total` 字段名、Money Decimal String 或 ErrorResponse。实际 Pydantic Schema/OpenAPI/Frontend 修改留待 Phase 6 获得实现授权后的协调发布。

### 9.2 `ShippingQuoteResponse` 冻结联合结构

```text
status: available | unavailable | unsupported
reason_code: ShippingQuoteReasonCode | null
checked_at: UTC datetime
quoted_at: UTC datetime | null
expires_at: UTC datetime | null
quoted_fee: Money | null
applied_fee: Money
providers: CarrierProvider[]
quote_source: contract | null
ruleset_id: string | null
ruleset_version: string | null
shipping_gst: Money | null       # D-022，只读，不再次加入 total
```

首批 `quote_source` 的非空值只能是 `contract`；未来 PAC 若获独立批准，再以兼容性审查扩展 enum。

状态字段组合执行第 2.2 节不变量。`status=unavailable` 本身就是降级标记；API 不需要冗余 `is_degraded` boolean。

API Mapper 只投影已经由 Domain 验证的金额：available 时将两位 `quoted_fee`/`applied_fee` 映射为 Money；仅当 Domain `shipping_gst` 非空时映射为只读 Money，否则为 null。Mapper 不读取 `unit_results`，不求和、不量化、不反推 GST，也不重新计算 Order Total。unavailable/unsupported 必须输出 `shipping_gst=null`。

### 9.3 `PackageResponse` 冻结结构

```text
package_id
source: actual | rules
items: [{order_item_ref, sku, quantity}]
dimensions: {length_mm, width_mm, height_mm, volume_mm3}
weight: {item_weight_g, packaging_weight_g, gross_weight_g}
ruleset_id / ruleset_version
```

Package response 仅允许出现在订单详情，列表不得返回 Package 集合。它不含 Provider chargeable weight，除非该值有明确来源并标注 provider；不公开 material compatibility、packing policy、capacity、diagnostics 或内部规则内容。

### 9.4 `TrackingResponse` 冻结结构

订单详情新增 `tracking_results: []`，每个唯一 Tracking Group 一个结果，字段与第 8.1 节一致。默认不返回完整 tracking number。

`CONFIRMED`（D-031）：`provider` 在 API/OpenAPI/TypeScript 中均为 nullable，但它是**运行时条件契约**，不是“任何 provider-null 都合法”。只有 `status=unavailable` 且 `reason_code=CARRIER_MAPPING_UNRESOLVED` 时 `provider` 才允许为 `null`；API Mapper、Domain 和前端 Runtime Validator 都必须拒绝其他 provider-null 组合，并继续严格校验非空 Provider 结果。Mapper 不计算金额、不猜测 Provider、不暴露 Provider 原始诊断或凭证。`tracking_results=[]` 只表示该订单没有唯一 Tracking Group。

### 9.5 Phase 5 兼容阻塞项

当前 Phase 5 runtime validator 把 quote status/reason 固定为 D-015。Backend 一旦返回 available/unavailable，现有前端会判定为 invalid response。因此必须同步发布前端 union validator、types 和 UI，或在 rollout flag 开启前保持 D-015。

`CONFIRMED`（D-025）：订单列表不进行 live quote，订单详情是首批唯一报价触发流程。

| 方案 | 优点 | 缺点 |
|---|---|---|
| 列表实时报价每笔订单 | 保持现有 summary status/total 语义 | N 次 Provider 调用、延迟和失败面 |
| 列表不报价并使用 `not_requested` + `Total before shipping` | 无外部调用；金额语义明确 | 需要 Phase 6 Backend/OpenAPI/Frontend 协调扩展；已由 D-025/D-030 批准 |
| 新增独立 logistics evaluation endpoint | 保持现有 Phase 5 endpoint 不变 | 新前端需组合权威 Pricing；增加 endpoint 契约 |
| **已选：同步扩展 detail；列表固定 not_requested** | 最小化首批外部调用；保护前端 | Phase 6 Quote 不能在列表启用 |

D-025 已冻结 API 调用边界，D-030 已冻结列表金额和展示语义。真实 Quote rollout 仍需 Backend/OpenAPI/Frontend 协调发布，但不再需要业务选择。

### 9.6 OpenAPI

实现阶段必须由 Pydantic schema 生成 OpenAPI，并以测试验证 discriminated union、Money regex、UTC date-time、nullable fields 和 reason-code enum。`CONFIRMED`（D-031）：`TrackingResponse.provider` 必须是 `enum | null`，并在 schema description 中说明只有 `unavailable / CARRIER_MAPPING_UNRESOLVED` 才允许 null；OpenAPI 必须包含一个 Mapping unresolved 示例（`provider=null`）。FastAPI 默认以 `exclude_none` 编码生成文档，会删除示例中的 null 字段，因此应用必须在不改变 API 行为的前提下还原该示例。`available`、`unavailable`、`unsupported` 的语义必须在 `status` description 中可读，API 路径、envelope 与错误结构保持不变。

## 10. Persistence & Lifecycle

### 10.1 Phase 6 必须实现

- request-scoped 去重与稳定 fingerprint；
- checked_at 与 Provider 返回时间分离；
- ruleset ID/version/input fingerprint 与 quote result 关联；
- 有界 timeout、分类错误和安全 diagnostics；
- 同一请求内 all-or-nothing unit results；
- Provider capability/config 在启动时验证，不读取前端配置。

### 10.2 推迟项

`DERIVED`：当前架构没有数据库且业务 JSON 只读，因此持久化 quote history、partial result history 或 Package history 不是 Phase 6 默认能力；新增持久化需要新决策。

`CONFIRMED`（D-026）：首批不持久化 quote/package/partial-result history，不做跨请求 quote cache；官方 Get Shipment Price 未提供 expiry 时不得发明 TTL。

未来若另行批准缓存，候选 key 才可使用 order identity + destination revision + package fingerprint + ruleset version + provider/account/product + currency 的不可逆 hash；不得包含明文 PII或凭证。该结构当前不得实现为跨请求 cache。

quote freshness、expiry policy、历史保留期、跨请求 partial success reuse 和失效规则明确推迟，均不属于首批范围；未来启用必须形成新决策。

### 10.3 幂等与重复请求

- Package estimation 是纯确定性函数：相同输入/rules version 结果相同。
- Service 在单请求内以 fingerprint 去重。
- Tracking GET 可按安全策略有限重试。
- Quote POST 在官方幂等语义未确认前不对结果不确定的 timeout 自动重放。
- 用户 Retry 重新执行整个订单 quote evaluation；按 D-026，跨请求不复用旧成功单元。

## 11. Error Handling

| 场景 | 结果 | 分类 |
|---|---|---|
| 列表未发起 Quote | request state `not_requested`；无 Quote result/reason/amount | CONFIRMED D-025 |
| 功能未实现 | unsupported + frozen reason | CONFIRMED |
| Provider mapping/config 缺失 | unavailable + frozen reason | CONFIRMED D-023/D-024 |
| Package rules/input 不完整 | quote unavailable, null/zero | CONFIRMED D-017/D-019/D-024 |
| 任一必要单元失败 | order quote unavailable, null/zero | CONFIRMED D-018/D-017 |
| Tracking Provider 失败 | 仅对应 Tracking unavailable | CONFIRMED D-012 |
| Quote Provider 失败 | 仅 Shipping Quote unavailable | CONFIRMED D-012 |
| 无 tracking events 的有效响应 | Tracking available + empty events | DERIVED |
| Provider response schema 无效 | unavailable，不透传 payload | CONFIRMED |
| 本地 Repository 引用损坏 | 现有安全 ErrorResponse | DERIVED |

内部异常必须按 capability、transient/permanent、retryable 和 safe diagnostic 分类。公共 reason code 稳定且非敏感；原始异常链只进入受保护诊断，不进入 API。

## 12. Security & Observability

- API key/secret 只从后端环境变量读取，`repr=False`，不进入 exception、logs、API 或 frontend。
- Account number、tracking number、客户地址/电话/邮箱和 Provider payload 不写普通日志。
- 日志允许：correlation ID、order 的安全内部摘要、provider code、capability、稳定 reason code、耗时、retry count、ruleset version。
- request fingerprint 必须为不可逆 hash，不保存明文 destination。
- Provider request 发送最小必需字段；通知 email/phone 默认不启用。
- metrics 只按 provider/capability/status/reason 聚合，不以客户或 tracking ID 作为 label。
- 外部响应设置大小限制并严格验证，禁止 raw JSON 透传。

## 13. Testing Contract

### 13.1 Domain

- frozen models/tuples、extra forbid、Decimal-only、非有限值拒绝、UTC-only；
- status-field matrix：available/unavailable/unsupported；
- request-state matrix：列表 not_requested 与详情 requested，且 not_requested 不产生 Quote result；
- D-030：`OrderSummaryResult` 不含 ShippingQuoteResult、列表不调用详情、`order_total = order_subtotal + gst_amount`；Domain 必须拒绝 `order_total` 不等于该公式、`gst_amount` 不一致、非零 `shipment_fee` 和 float 金额；`OrderDetailResult` 强制 quote applied fee 与 pricing shipment fee 相等，且只按详情规则使用 `applied_fee`；
- D-031：`TrackingResult` 的条件 nullable Provider 矩阵，合法组合仅 `provider=null + unavailable + CARRIER_MAPPING_UNRESOLVED`，并拒绝 provider-null + available/unsupported/其他 reason，以及具体 Provider + `CARRIER_MAPPING_UNRESOLVED`；每个唯一 Tracking Group 一个结果，空结果只允许在订单没有 Tracking Group 时；
- Revision 不可变性：五种 Revision ID 分别独立决定完整内容，同一 ID 相同内容幂等、不同内容拒绝；Release 固定精确 Mapping Revision 集合；
- D-015 与 D-017 的 canonical zero；
- `shipping_gst` 的全单元证据、null、聚合和禁止反推不变量；
- Package volume/weight invariants、allocation quantity conservation、ID uniqueness；
- Tracking Group 与 Package ID 不可互换。

### 13.2 Packaging rules

- 同输入/version 的确定性与稳定顺序；
- actual source 优先；
- missing SKU/material/tare/capacity 返回 unavailable；
- split/mix 每个批准策略的数量守恒；
- ruleset 生效时间、版本不可变和 provenance。

Task 048 基于 D-032～D-035 增补以下**必测项**（J2-B～J2-E 实施时必须全部覆盖）：

**Policy schema 与匹配（D-032，§5.4）**

- 字段级 schema：缺省必填字段即加载失败；`extra="forbid"`；枚举越界拒绝；
- scope 专属字段：`scope=sku` 缺 `sku` 或 `scope=general` 携带 `sku` 均拒绝；
- `scope=sku` 引用不存在的 `sku_specs` 拒绝；`scope=handling_class` 不可达拒绝；
- 同 scope + 同匹配键 + 同 priority 重复拒绝；不同 priority 允许；
- 匹配优先级：sku 命中时忽略 handling_class/general；无 sku 时用 handling_class；再无则 general；
- 零匹配 → `unavailable / PACKAGE_DATA_INCOMPLETE` + 内部 `policy_unmatched`，且零 Package；
- policy 放宽材料毛重/外尺寸上限 → 加载期拒绝；收紧值允许；
- `allow_mixed_sku` 与 `max_skus_per_package` 组合校验；`fragile_mixing` 三态行为；
- 不新增公共 reason code（断言公共枚举仅两个包装 code）。

**约束归属（D-033，§5.5）**

- 三处归属的字段校验：方向三态、易碎三态、堆叠组合、危险品与 `hazard_class_ref` 组合、材料能力字段；
- `EffectiveConstraintView` 取最严：毛重 min、外尺寸逐边 min、方向 `most_restrictive`、混装 AND；
- policy 不得放宽：放宽值在加载期拒绝；
- 派生视图不持久化、不进 provenance、不进 API（断言序列化结果字段集合）；
- 材料逐边 `outer ≥ inner` 校验；
- 商品事实隔离：读取 `weight_g`/`dimensions_mm`/`volume_mm3`/`volumetric_gross_weight_kg`/`max_storage_per_container` 即失败的守卫测试。

**算法（D-034，§5.6）**

- Stage 0～6 各自的失败路径独立用例；
- 排序键逐项：体积降序、重量降序、sku、line_index、unit_ordinal；
- Best-Fit 决胜键（剩余容积、已开序号）；同输入重跑 100 次结果与 fingerprint 完全一致；
- 方向：`any`（含不可行排列）、`upright_only`（H 固定）、`fixed`（不得重排）；
- 容积通过但几何不可行必须 fail closed（不得以容积代替几何）；
- 重量含皮重；毛重上限取 policy 与材料的较小值；
- 拆分/混装七步裁决顺序与回退「开新包一次」语义；
- 上限：`max_units_per_package`、`max_skus_per_package`、`max_packages_per_order`、order unit 硬上限 500；
- 整单 fail closed：任一 unit 不可装时 `packages=()`；
- 禁止不确定性来源：随机、集合迭代序、时钟、locale（以固定种子/打乱输入顺序的等价测试证明）。

**材料选择（D-035，§5.7）**

- F1～F8 每项独立用例，且验证「任一不过即排除」而非加权；
- F1 白名单外材料、F2 retired、F3 危险品未许可、F4 未缓冲、F5 方向不覆盖、F6 三边不可行、F7 毛重超限、F8 外尺寸超限；
- 两种策略的排序键与末位 `material_id` 决胜；`priority_order` 缺 `selection_priority` 时加载期拒绝；
- 零候选 → `unavailable / PACKAGE_DATA_INCOMPLETE`；
- 八项禁止 fallback 逐项负向测试（含跨 SKU 借用白名单、`allow_split=false` 换材料、同包多材料）。

**Synthetic / Production 边界（§5.8）**

- `synthetic_only` 仍为 `Literal[True]`；`model_construct` 绕过被 Service 拒绝；
- 默认应用（`build_package_estimation_service()`）在无生产 ruleset 时返回 `PACKAGE_RULES_NOT_CONFIGURED` 且零 Package；
- 生产 ruleset 识别门禁存在且默认关闭；synthetic fixtures 未被生产模块导入（模块导入图断言）。

### 13.3 Provider/Service

- 使用 fake/synthetic payload，不要求真实 API；
- AP/ST 不混批、每批不超过 10；
- HTTP 200 内单项失败、400/401/403/429/5xx、timeout、invalid JSON；
- all-or-nothing、empty/duplicate units、partial diagnostics 不进 Pricing；
- Capability Preflight 验证混合 Provider unsupported、mapping/config unavailable、无网络短路和稳定 reason precedence；
- Stable ID 不参与版本选择；Release 精确引用 Mapping/Provider/Account/Product Revision，缺失或多匹配 fail closed；
- Active Release 原子切换失败保持旧版本；rollback 重新激活历史 Release；请求级 pinning 和在途请求不发生 Revision 漂移；
- Tracking 与 Quote 交叉成功/失败互不传播；
- D-031：Mapping missing、Mapping ambiguous、Active Release missing 均产生 provider-null unavailable；Mapping failure 不发出 HTTP 请求；多 Tracking Group 分别产生结果；已确定 Provider 的配置错误保留 Provider 与既有 reason；默认 FastAPI 应用注入 Tracking Service 且无 Mapping 时不外呼；
- 五种 Revision ID 的独立不可变性：同 ID 同内容允许、同 ID 不同 Provider/Account/Product/Mapping/Release 内容拒绝、不同 ID 与不同 Release 可合法持有不同内容；
- 金额、单位转换和聚合不经过 float；raw、validated unit、exact aggregate、D-004 cent normalization 各边界分别覆盖；
- D-022 含 GST total 不重复计税，D-029 缺少精度规则时拒绝报价，单元精度和订单级两位 Money 的转换可追溯；
- D-023/D-027 不发生 Provider、Account、Product 或 PAC 静默 fallback；

### 13.4 API/Frontend

- Money two-decimal string、UTC、联合字段不变量和 OpenAPI；
- Phase 5 validator 在 rollout 前同步支持 union；
- 列表公开 `quote_request_state=not_requested`、金额标签 `Total before shipping` 和 `Shipping quote not requested`，不把内部零值显示为报价或 fallback；
- unavailable A$0.00 明确降级，unsupported 文案保持未实现；
- 部分成功不显示为完整报价；
- API/log/caplog/frontend build 不含凭证、tracking number 或 PII。
- 列表不会触发 Provider 调用或 N+1，详情才触发 Quote；
- raw Tracking status 与 normalized/unknown 同时保留。
- D-031：后端 Schema/OpenAPI 与前端 Runtime Validator 都必须只接受合法 provider-null 组合；UI 必须区分 Mapping unresolved 与 `not_requested`，`tracking_results=[]` 只能表达订单没有可处理的唯一 Tracking Group，多 Tracking Group 独立展示且不显示虚构承运商/事件/ETA。

Task 042 实现后现有 Backend 286 tests、Frontend 49 tests、typecheck/build/lint 必须持续通过；后续任务不得通过删除、跳过或放宽既有测试获得绿色结果。

## 14. Compatibility Requirements

- 不修改 D-001～D-031 的原文或语义；Task 034 新增 D-030，Task 042 新增 D-031 并以 Revision/Release 技术契约落实 D-023，Task 048 新增 D-032～D-035 并以 §5.4～§5.8 落实包装契约。
- D-032～D-035 只冻结包装规则、约束、算法与材料选择的语义，不改变 API 路径/envelope、Money、Tracking/Quote 状态语义、Pricing 公式或 `PackageResponse` 字段集合。
- D-032～D-035 不新增公共 reason code；包装失败仍只用 `PACKAGE_RULES_NOT_CONFIGURED` 与 `PACKAGE_DATA_INCOMPLETE`（D-024）。
- 包装合成隔离（`synthetic_only`、Service 纵深拒绝、默认无 ruleset）在 Task 048 后不得削弱。
- Pricing Service 的商品行、GST、Shipment Fee normalization 和总额顺序不变。
- Existing API paths/envelopes/error schema/Money 保持。
- D-015 在 Quote Integration 未启用期间完整保留。
- Phase 5 前端与 Phase 6 backend status union 必须协调发布。
- D-025 的 `not_requested` 是独立 request state，不扩展 D-013 Provider result enum。
- D-031 只改变 `TrackingResult.provider` 的条件可空投影，不改变 D-013 状态语义、D-024 reason code 集合、D-028 raw/normalized 规则或 D-012 的 Tracking/Quote 独立性。
- Repository 继续只读四个业务 JSON；rules 配置不得覆盖原始/标准化业务数据。
- 不引入数据库、Redis、消息队列或微服务。
- TNT 未实现不阻塞核心，但必须明确 unsupported。

## 15. Approved Decisions and Remaining Prerequisites

### 15.1 Frozen decision matrix

| 原 ID | 正式决策 | 冻结选择 | 状态 |
|---|---|---|---|
| OD-01 | D-020 | 模型允许拆分/混装，ruleset 控制 | APPROVED / FROZEN |
| OD-02 | D-021 | 独立、只读、版本化 Packaging Rules | APPROVED / FROZEN |
| OD-03 | D-022 | 明确含 GST 的 total_cost 作为 applied_fee；shipping_gst 只读 | APPROVED / FROZEN |
| OD-04 | D-023 | 显式 Provider/Account/Product mapping，无 fallback | APPROVED / FROZEN |
| OD-05 | D-024 | 小型稳定公共 reason enum + 内部 diagnostics | APPROVED / FROZEN |
| OD-06 | D-025 | 详情触发 Quote；列表 not_requested 且不调用 Provider | APPROVED / FROZEN |
| OD-07 | D-026 | 首批无历史持久化、无跨请求 cache | APPROVED / FROZEN |
| OD-08 | D-027 | Contract Price 核心；PAC 未批准且不 fallback | APPROVED / FROZEN |
| OD-09 | D-028 | normalized + raw + unknown Tracking status | APPROVED / FROZEN |
| OD-10 | D-029 | 遵循明确 Provider/Product/合同精度；缺失即拒绝报价 | APPROVED / FROZEN |
| Task 034 | D-030 | 列表 `order_total = order_subtotal + gst_amount`；Total before shipping | APPROVED / FROZEN |
| Task 042 | D-031 | Mapping 无法解析时 provider-null `unavailable / CARRIER_MAPPING_UNRESOLVED`，每个 Tracking Group 一个结果 | APPROVED / FROZEN |
| Task 048（DEC-1） | D-032 | `PackingPolicy` 结构化封闭 schema：scope/封闭枚举/拆分混装/上限/优先级/零匹配 fail closed | APPROVED / FROZEN |
| Task 048（DEC-2） | D-033 | 约束三处归属（SKU 事实 / 材料能力 / policy 只收紧）+ 运行时 `EffectiveConstraintView` | APPROVED / FROZEN |
| Task 048（DEC-3） | D-034 | 分阶段确定性启发式 + Best-Fit Decreasing；整单 fail closed；不承诺最优 3D 装箱 | APPROVED / FROZEN |
| Task 048（DEC-4） | D-035 | 材料选择 F1～F8 硬过滤 + `smallest_inner_volume`/`priority_order` + 8 条禁止 fallback | APPROVED / FROZEN |

### 15.2 Remaining implementation prerequisites

以下不是待批准的 OD，也不改变冻结业务选择：

- 提供具体 SKU packaging specs、材料目录、capacity、tare weight、方向/易碎/堆叠/危险品取值和获批 ruleset（DM-01～DM-18）；算法与策略本身已由 D-032～D-035 冻结，不再待批准；
- 提供真实 Provider/Account/Product/Mapping Revision、获批准 Configuration Release、服务端凭证和 Get Accounts 验证结果；
- 为每个启用的 Provider/Product 提供 GST、体积/计费重量、输入精度和舍入证据；
- 以真实文档/响应样本建立 Provider raw Tracking Status 映射；
- 选择符合 D-021 的只读配置文件路径和安全发布流程（载体选择本身属待批准项）；
- 提供配置发布审批、Active Release 切换/rollback 权限、rollback 操作与审计、请求级 Revision pinning、在途请求策略，以及配置 provenance 的保存和受控查询方式（Provider 侧已由 §8.4 冻结；**Packaging 侧治理属 DEC-5，暂缓**）；
- 明确 runtime HTTP client 的 timeout、并发和限流参数，但不得改变 D-023/D-026/D-027 的边界（**多进程限流策略属 DEC-6，暂缓**）。

`DEFERRED / NOT_APPROVED`（不得作为已冻结业务决策实施）：DEC-5 Packaging 配置治理、DEC-6 多进程全局限流。两者不阻塞 Batch J2-B～J2-E 的离线实现，但阻塞生产包装激活、J2-F 实施与多进程/多实例部署。

任何未来改变 D-001～D-035 的选择都必须新增正式决策，不得修改历史记录。

## 16. Implementation Boundaries

### 16.1 获得 Phase 6 实施授权后可按顺序实现

1. 实现 immutable primitives、公共 enums、Provider protocols、safe diagnostics 与 fake clients；
2. 按 D-023/D-024/D-028 实现 Tracking vertical slice；
3. 按 D-020/D-021 实现 Package/rules vertical slice；
4. 按 D-032～D-035 实现生产 ruleset schema、约束归属、生产算法与材料选择的 J2-B～J2-E 切片；
5. 按 D-022/D-024～D-027/D-029/D-030 实现详情 Quote、列表 Summary、Pricing 输入和 API/Frontend vertical slice；
6. 最后实现 reliability、受控 testbed 验证和 E2E。

### 16.2 当前明确禁止

- 不用 Tracking Group 推导 Package；
- 不用 Product dimensions/volume/weight/体积毛重/仓储容量直接充当 Package 或包装约束；
- 不硬编码 cubing factor、product/service code 或 Provider mapping；
- 不把 partial quote 应用到 Pricing；
- 不把 zero fallback 显示为免费运输；
- 不在 Provider Adapter 中计算订单价格；
- 不在前端计算 Money；
- 不放宽 `synthetic_only`、不用 `model_construct` 绕过校验、不把测试 fixtures 接入生产模块；
- 不用 policy 放宽材料/SKU 硬约束，不在材料选择中做任何未批准 fallback；
- 不新增 D-026 禁止的历史持久化或跨请求缓存；未获得 Phase 6 实施授权前不开始真实 API 调用；
- 不实现 DEC-5 配置治理与 DEC-6 多进程限流（两者 `DEFERRED / NOT_APPROVED`）。

### 16.3 Readiness 结论

D-020～D-029 已将 OD-01～OD-10 全部转化为可测试的冻结业务契约，D-030 冻结了列表 `Total before shipping` 语义，D-031 冻结了 Tracking Mapping 失败的公开投影，D-032～D-035 冻结了包装策略、约束归属、生产装箱算法与材料选择。仍缺少的具体配置值、真实包装数据、外部账号条件、治理权限和 Provider 证据属于实施前置输入，不再是待批准业务决策；DEC-5/DEC-6 明确暂缓。

Task 030 Decision Approval：`PASS`。Task 031 独立审查为 `FAIL`；Task 032 完成第一轮技术整改。Task 033 独立复审为 `FAIL`；Task 034 已新增 D-030，并完成不可变 Revision、Configuration Release、rollback、version pinning 和在途请求契约整改。Task 037～040 完成 Batch I Tracking 基础实现；Task 041 独立审查为 `FAIL`（0 Critical、1 High、2 Medium、1 Low）。Task 042 已按 D-031 完成 T041-H01 全链路整改，并关闭 T041-M01、T041-M02、T041-L01；没有修改 D-012～D-030 的原有业务语义，也没有开始 Packaging、Shipping Quote、PAC 或其他 Batch J/K 功能。Task 045/046 完成 Batch J1 synthetic-only 实现与复审；Task 047 完成 Batch J2 决策包；Task 048 依据用户批准新增 D-032～D-035 并冻结 §5.4～§5.8。

`TASK_042_FINAL_STATUS: PASS`

`TASK_043_FINAL_STATUS: BATCH_I_REVIEW_PASS`（离线实现通过 + Git Checkpoint 创建成功；真实 Provider 验证仍未完成）

`TASK_046_FINAL_STATUS: PASS`（Batch J1 离线实现与复审；Git Checkpoint `3c3675e`）

`TASK_047_FINAL_STATUS: DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL`

`TASK_048_FINAL_STATUS: PASS`（DEC-1～DEC-4 → D-032～D-035 正式化；DEC-5/DEC-6 暂缓；Batch J2 Contract `COMPLETE`）

契约状态：`CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW` 已由 Task 043 独立复审关闭，Batch I 离线实现冻结为 Checkpoint `6ccdc5f`。Batch I 仍为 `PARTIALLY_COMPLETE`，真实 Provider/账号/凭证/Mapping/Release/testbed 验证仍为 `BLOCKED`。Batch J1 为 `COMPLETE`（synthetic-only，Checkpoint `3c3675e`）；Batch J2 Contract 为 `COMPLETE`，Batch J2 Implementation 为 `NOT_STARTED`，J2-F 未获授权，J2-G 阻塞于真实包装数据。Batch K 尚未开始；真实 Provider 验证不得因离线测试通过而被表述为已完成，Phase 6 不得标记为 `COMPLETE`。
