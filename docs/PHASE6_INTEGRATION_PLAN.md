# Phase 6 Logistics Integration Plan and Frozen Contract

## 1. 文档状态与结论

- 核对日期：2026-11-07
- 基线分支：`main`
- 基线 HEAD：`cc8209ae08b3770594f8d490097128924e6cfca8`
- Task 028 原始工作区基线：干净；当前包含 Task 028～034 文档变更
- Phase 0～5：`COMPLETE`
- Phase 6 实现：`NOT_STARTED`
- 本文范围：现状审计、官方资料调研、已冻结领域/API/前端契约、架构与测试计划
- 本文不包含：业务代码、API 修改、依赖安装、JSON 修改、凭证创建或真实承运商调用
- Task 031 独立审查：`FAIL`；Task 032 契约整改：`PASS`；Task 033 独立复审：`FAIL`
- Implementation Readiness：`CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW`
- Task 030 Decision Approval：`PASS`；OD-01～OD-10 已形成 D-020～D-029
- Task 034：D-030 已批准，Provider Revision/Configuration Release 与配置治理整改已完成，等待 Task 035

本文保留 Task 028 的原始审计和官方调研，并以 D-016～D-030 及 `PHASE6_CONTRACT.md` 同步冻结 Phase 6 业务边界。具体 rules 数据、账号映射值、配置治理权限、凭证和 Provider/Product 证据仍是实施前置输入，不以工程假设替代。

`D-001`～`D-030` 全部有效。D-020～D-029 只解决 OD-01～OD-10，D-030 冻结列表 `Total before shipping`；均不修改 D-012、D-015～D-019。

## 2. 当前项目审计

### 2.1 数据与 Repository 边界

当前运行时数据链路为：

```text
orders.json   -> OrderRepository
skus.json     -> ProductRepository
tracking.json -> TrackingRepository
                    |
                    v
             RepositoryCollection
```

- `skus_raw.json` 仅用于溯源，不被 Repository 读取。
- Repository 在初始化时读取并缓存不可变 Domain Model；`RepositoryCollection` 校验订单 SKU 和 tracking group 引用。
- `TrackingGroup` 的真实结构只有 `tracking_group_id`、`carrier`、`tracking_number`。它是本地关联，不是物流事件。
- `tracking_number` 来自 `tracking.json`，在 Domain/Source Model 的 `repr` 中隐藏；不得写入普通日志、测试快照或文档示例。
- 当前基线为 2 笔订单、9 条订单行、31 件商品、9 个唯一 SKU、3 个物流分组；3 个分组均被引用。
- 承运商数据只有两类文本：2 个分组为 `StarTrack / Australia Post`，1 个分组为 `TNT`。合并文本无法可靠决定前两个分组究竟应使用 Australia Post 还是 StarTrack 账号、请求规则和响应映射。

因此，Phase 6 不得根据 tracking number 格式猜测承运商。真实调用前必须将每个分组映射到规范化 provider code，并获得数据来源或用户确认。

### 2.2 Product 的重量和尺寸

现有 `Product` 包含：

| 字段 | 当前模型含义 | 数据审计 |
|---|---|---|
| `weight_g` | 商品重量，克 | 9 条均非零，范围 25～93 g |
| `dimensions_mm` | 商品长宽高，毫米 | 9 条均为非零三维数据 |
| `volume_mm3` | 商品体积，立方毫米 | 9 条均等于三维字段乘积 |
| `volumetric_gross_weight_kg` | 来源数据中的体积毛重，千克 | 9 条均非零，但不符合统一 `volume_m3 × 250` 关系 |

这些是商品数据，不是已装箱包裹数据。当前没有 package、carton、satchel、packing quantity、tare weight、orientation、危险品或承运商 product/service code。不得把商品重量直接当包裹重量，也不得把多件商品的尺寸相加生成包裹尺寸。

### 2.3 Service 与金额链路

- `OrderService` 只依赖 Order/Product reader，没有使用 Tracking Repository。
- 每次订单查询都会创建 D-015 的 `ShippingQuoteResult`：`unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`、运行时 UTC `checked_at`、`quoted_fee=null`、`applied_fee=Decimal("0.00")`。
- `shipping_quote.applied_fee` 被传入 `PricingService`；`OrderResult` 校验它与 `PricingResult.shipment_fee` 一致。
- `PricingService` 保持纯 Decimal 链路，并执行 D-004 的逐行、GST、运费和总额舍入时点。Phase 6 不重新设计这些规则。
- 当前没有 Tracking Service、Shipping Quote Service、Integration model 或外部 HTTP client。

### 2.4 API v1 与前端

- `GET /api/v1/orders` 返回订单摘要、Order Total 和 Shipping Quote 状态/reason code。
- `GET /api/v1/orders/{order_number}` 返回订单详情、商品行、价格和完整 `shipping_quote`。
- Money 固定为 `{"amount":"123.45","currency":"AUD"}`；Pydantic 显式序列化 Decimal，TypeScript 保持 `amount: string`。
- 当前 API 和前端类型把 Shipping Quote 收窄为唯一的 D-015 `unsupported` 形态；还没有 TrackingResult。
- 订单详情把 `tracking_group_id` 标为内部关联，明确不把它显示成承运商事件。
- Shipping Quote UI 明确说明 `A$0.00` 是降级计算值，不是免费运输报价。
- 前端已具备页面级 loading/error/retry，但还没有独立的 tracking timeline、quote expiry 或局部重试状态。

### 2.5 Task 028 契约冲突的 Task 029 结论

`D-012` 规定无有效报价（`unavailable` 或 `unsupported`）时 `quoted_fee=null`、`applied_fee=A$0.00`。`D-015` 又把该规则具体化为“Integration 尚未实现时”的 `unsupported` 占位契约。

Task 028 曾要求“绝不能默认 `unavailable` 时应用 AUD 0.00”，因此把真实集成失败路径列为阻断性业务问题。Task 029 已通过 D-017 明确选择 `zero_fallback`，该冲突现已解决：

- D-015 可继续原样用于当前 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED`，不得静默改写。
- 真实集成后的 `unavailable` 使用独立 reason code、`quoted_fee=null` 和 `applied_fee=Decimal("0.00")`，并继续按现有 Pricing Service 公式生成降级订单总额。
- 零值只表示业务降级，不是承运商报价或免费运输；`unsupported` 与 `unavailable` 继续遵循 D-013 的独立语义。
- Task 030 Decision Approval 已由 D-020～D-029 冻结联合契约、reason code、Provider、lifecycle、Tracking status 与 Decimal 边界；本任务仍未修改现有 Domain/API/前端代码。

## 3. 官方 API 调研

### 3.1 证据范围

以下资料均为官方 Australia Post / StarTrack 页面，核对日期为 2026-11-07。本任务只读取公开文档，没有使用凭证、调用 testbed/production 或验证账号权限。官方页面所述能力不等于本项目已获得产品权限、配额或生产访问。

本文证据分类为：`VERIFIED_REPOSITORY`（当前代码/数据直接证明）、`VERIFIED_OFFICIAL`（官方资料明确说明）、`INFERENCE`（从多项证据得出的设计判断）和 `DECISION_REQUIRED`（必须由业务/账号所有者确认）。所有 endpoint、认证和 provider 字段均只采用 `VERIFIED_OFFICIAL` 资料；`INFERENCE` 不作为外部 API 事实。

| 文档 | 官方来源 | 用途 |
|---|---|---|
| Track Items | https://developers.auspost.com.au/apis/shipping-and-tracking/reference/track-items | Tracking endpoint、字段、限制和错误 |
| Get Shipment Price | https://developers.auspost.com.au/apis/shipping-and-tracking/reference/get-shipment-price | 合同报价请求/响应、GST、错误 |
| REST and authentication | https://developers.auspost.com.au/content/apis/shipping-and-tracking/reference-restful.html | Basic Auth、Account-Number 和 JSON headers |
| Developer Test Bed | https://developers.auspost.com.au/content/apis/shipping-and-tracking/info/integration/testbed-environment.html | 测试环境能力与限制 |
| Shipping and Tracking FAQ | https://developers.auspost.com.au/content/apis/shipping-and-tracking/info/api-resources/faq.html | 资格、生产开通、测试环境和 GST 说明 |
| Get Accounts | https://developers.auspost.com.au/apis/shipping-and-tracking/reference/get-accounts | 合同产品、地址和 volumetric pricing |
| Check account details | https://developers.auspost.com.au/content/apis/shipping-and-tracking/info/api-resources/check-account.html | 产品变化和账号格式 |
| Statuses | https://developers.auspost.com.au/content/apis/shipping-and-tracking/reference-statuses.html | Australia Post / StarTrack 状态集合 |
| Calculating shipping rates | https://developers.auspost.com.au/apis/shipping-and-tracking/info/api-resources/calc-shipping-rates | 合同价、GST 和 StarTrack 报价建议 |
| Postage Assessment Calculator | https://developers.auspost.com.au/apis/pac/tutorial/domestic-parcel | 零售报价 API 和 AUTH-KEY |
| Cubic weight | https://auspost.com.au/business/grow-your-business/business-ideas-blog/what-is-cubic-weight | Australia Post 通用体积重量说明 |
| StarTrack Terms and Conditions | https://startrack.com.au/content/dam/startrack_corp/documents/printable-services-agreement-terms-and-conditions.pdf | StarTrack cubic factor 的合同边界 |

### 3.2 共同的 Shipping and Tracking API 边界

- Shipping and Tracking API 仅面向符合条件的 Australia Post eParcel 或 StarTrack contract customer；需要注册并由 Australia Post 开通。
- 请求使用 HTTP Basic Authentication：API key 为 username、创建的 secret 为 password；很多调用还必须发送 `Account-Number`。
- 已审阅的官方 Shipping and Tracking 资料指定 Basic Authentication，没有给出 OAuth 流程；不得自行设计或声称需要 OAuth，除非账号开通材料另有明确要求。
- Australia Post account number 以 10 位形式发送（必要时左补零）；StarTrack account number 为 8 位且不补零。
- testbed 与 production 使用不同 URL/credentials。testbed 提供 Australia Post 与 StarTrack 国内包裹合同能力，但使用通用合同、不同 product IDs 和模拟 Tracking 响应；其价格不代表客户真实合同价。
- 官方说明生产访问需要先完成 testbed 集成验证。具体开通材料依实际启用的服务而定，必须由账号所有者与 Australia Post 确认。
- Get Accounts 是产品和合同能力的权威来源；product IDs 可能变化，不能硬编码为永久业务常量。

### 3.3 Australia Post Tracking

官方明确支持：

- `GET /shipping/v1/track?tracking_ids=...`。
- Track Items 返回 queried tracking ID、carrier status、trackable items 和事件；事件包含 `location`（可能缺失）、`description` 和带时区的日期时间。
- 单次最多 10 个 Australia Post IDs；每分钟最多 10 次请求。
- 同一个请求不能混合 Australia Post 与 StarTrack IDs。
- 一个合法响应可以对单个 ID 返回业务错误；HTTP 200 不等于每个 tracking ID 都成功。
- 明确错误包括 invalid ID、product not trackable、system error、缺少 IDs、超过数量、混合承运商和 HTTP 429。

官方没有为本项目定义：客户端 timeout、重试次数、归一化状态枚举、缓存时间、事件保留期或 UI 刷新频率。这些必须作为本系统策略显式配置和测试。

### 3.4 Australia Post Shipping Quote

有两套不同用途的官方能力：

1. Postage Assessment Calculator (PAC) 提供公开零售运价，使用 `AUTH-KEY`，输入起止邮编、包裹厘米尺寸、千克重量和 service code。
2. Shipping and Tracking API 的 Get Shipment Price 提供合同账号价格，使用 Basic Auth 与 Account-Number；官方明确说明 PAC 不返回客户合同价。

按 D-027，本项目首批只使用经验证的 Get Shipment Price Contract Price；PAC 只能在未来独立业务批准后成为另一 capability，不能自动回退。

Get Shipment Price 的已证实契约：

- `POST /shipping/v1/prices/shipments`，官方标注为不受该页面的 rate limit。
- 输入包含 from/to 地址、一个或多个 parcel item、product ID、厘米尺寸和千克重量。
- 若合同采用 volumetric pricing，尺寸为必填；flat-rate product 反而可能禁止尺寸/重量。
- 响应 `shipment_summary.total_cost` 是含 GST 的总价，并提供 `shipping_cost` 和 `total_gst`。
- 官方说明这些价格是 indicative contract pricing，最终实际价格在包裹进入网络处理时确定；不得向客户声称为 Australia Post 最终收费。
- 错误覆盖合同不支持产品、起始邮编不匹配、无法按重量/体积重量计价、尺寸/重量上限、缺失字段和无合同价。
- 已审阅的响应契约没有独立的 quote expiry 或 carrier quote reference。`shipment_reference` 是 merchant reference，不能伪装成承运商 quote reference。

### 3.5 StarTrack Tracking 与 Shipping Quote

StarTrack 不是需要另找未经证实 endpoint 的独立猜测接口；官方 Shipping and Tracking 文档在同一 API 家族内明确支持 StarTrack account、consignment tracking 和 shipment pricing，但账号、产品与响应结构仍须独立处理：

- Track Items 接受 StarTrack consignment IDs，不能与 Australia Post IDs 混在一次请求中；单次最多 10 个 StarTrack IDs。
- StarTrack tracking response 可包含 consignment-level events/status 和 freight-item status；状态集合与 Australia Post article status 不同。
- StarTrack quote 使用 8 位 StarTrack account，具体 product IDs 和 volumetric pricing 从该账号的 Get Accounts 结果获得。
- 官方推荐 StarTrack pricing 使用 Get Shipment Price。
- Get Shipment Price 的 packaging/unit type 对 StarTrack 产品可能为必填，具体可用产品和能力由合同决定。
- testbed 支持 StarTrack domestic parcel contract，但使用通用合同和模拟数据，不能证明生产账号可用服务或真实价格。

因此应共享底层认证/HTTP transport 和官方 API family knowledge，但 Australia Post 与 StarTrack 必须保留独立 provider code、account configuration、请求验证和响应 mapper。

### 3.6 重量与体积重量证据

- Australia Post 公共说明通常以实际重量与 cubic weight 较大者计费；常见 cubic factor 为 `250 kg/m³`。
- StarTrack 当前条款也说明默认行业 cubic factor 为 `250 kg/m³`，但允许合同另有约定，并规定其自身的取整方式。
- Get Accounts 可以返回合同是否采用 volumetric pricing 和 cubing factor。

因此 Phase 6 不得把 250 写成跨承运商、跨产品、跨合同的固定公式。应把 Get Accounts/合同返回或用户确认的规则视为 provider/account capability；最好向承运商报价 API提交真实 package dimensions/weight，让承运商计算价格，而不是在订单系统中重建完整计费算法。

## 4. 领域契约

### 4.1 规范化 Carrier 标识

D-023 冻结的内部值：

```text
australia_post
startrack
tnt
```

显示名称与内部值分离。现有 `StarTrack / Australia Post` 必须在数据层之外通过已确认映射解析，不能依据 tracking number 形状推断。Provider 尚未实现时按 D-013 返回 `unsupported`；Provider 已实现但该映射仍未解决时返回 `unavailable / CARRIER_MAPPING_UNRESOLVED`，且不得发出外部请求。

### 4.2 TrackingResult

每个唯一 tracking group 返回一个独立结果：

```text
TrackingResult
  tracking_group_id: str
  provider: CarrierProvider
  status: available | unavailable | unsupported
  reason_code: TrackingReasonCode | null
  checked_at: UTC aware datetime
  provider_status: str | null
  current_status: NormalizedTrackingStatus | null
  latest_event_at: UTC aware datetime | null
  events: tuple[TrackingEvent, ...]

TrackingEvent
  event_time: UTC aware datetime
  location: str | null
  description: str
  provider_status: str | null
  normalized_status: NormalizedTrackingStatus
```

D-028 冻结的 `NormalizedTrackingStatus`：

```text
pending
ready_for_pickup
in_transit
out_for_delivery
awaiting_collection
delivered
delivery_exception
cancelled
unknown
```

约束：

- `checked_at` 是本系统检查时间；`event_time` 来自承运商并转换为 UTC，二者不得混用。
- `provider_status` 保留已验证的承运商顶层 raw status；`current_status` 只通过显式 provider mapping 产生。
- 不认识的承运商状态映射为 `unknown`，同时保留 `provider_status`，不得从 description 文本猜测。
- `latest_event_at` 只可取已验证事件的最大 `event_time`；无事件时为 `null`。
- 查询成功、响应有效但没有事件：`status=available`、`reason_code=null`、`events=[]`。这与查询失败不同，且不扩张 D-024 枚举。
- 承运商/能力尚未实现：`unsupported`，所有 carrier-derived 字段为空；适配器已实现但 provider mapping 仍无法确定时为 `unavailable / CARRIER_MAPPING_UNRESOLVED`，不得发出外部请求。
- timeout、network、authentication、rate limit、invalid response 或 provider business error：`unavailable`，不得回填旧事件，除非未来明确设计并标注 snapshot/staleness。
- tracking number 不进入普通 API 响应；如业务要求展示，需单独做隐私与最小披露确认。

冻结的稳定 reason codes（D-024）：

| 状态 | reason code |
|---|---|
| available | `null`（有效空事件仍为 available） |
| unavailable | `PROVIDER_CONFIGURATION_MISSING`, `CARRIER_MAPPING_UNRESOLVED`, `PROVIDER_TIMEOUT`, `PROVIDER_NETWORK_ERROR`, `PROVIDER_AUTHENTICATION_FAILED`, `PROVIDER_RATE_LIMITED`, `TRACKING_ID_INVALID`, `PRODUCT_NOT_TRACKABLE`, `PROVIDER_RESPONSE_INVALID`, `PROVIDER_ERROR` |
| unsupported | `CARRIER_NOT_IMPLEMENTED` |

Provider 原始错误码只用于经过脱敏的内部诊断，不直接成为公共 reason code 或错误 message。

### 4.3 ShippingQuoteResult

为支持多个必要报价单元，订单级结果必须能关联内部单元结果，而不是只保留一个无法解释来源的金额；下列内部结构已由 D-018、D-022～D-024、D-027 和 D-029 冻结：

```text
ShippingQuoteResult
  status: available | unavailable | unsupported
  reason_code: ShippingQuoteReasonCode | null
  checked_at: UTC aware datetime
  currency: AUD
  quoted_fee: Decimal | null
  applied_fee: Decimal
  shipping_gst: Decimal | null
  quote_source: contract | null
  ruleset_id/version: str | null
  expires_at: UTC aware datetime | null
  unit_results: tuple[QuoteUnitResult, ...]  # 内部诊断，不进入公共 API

QuoteUnitResult
  quote_unit_id: str
  provider: CarrierProvider
  status: available | unavailable
  reason_code: ShippingQuoteReasonCode | null
  total_cost_incl_gst: Decimal | null
  shipping_cost: Decimal | null
  gst_amount: Decimal | null
  raw amount/currency evidence: internal, repr false
  provider_reference: str | null
  expires_at: UTC aware datetime | null
```

共同约束：

- Provider amount 先以字符串解析为有限、非负 Decimal，并保留 D-029 所需 raw amount/currency 证据，禁止经过 float。
- API Money 仍只接受 AUD；非 AUD 报价不得静默换汇，返回 `unavailable / CURRENCY_NOT_SUPPORTED`。
- Tracking Group 不是 Package ID 或报价单元；`quote_unit_id` 与 Package/OrderItem 的关系遵循 D-020 的分配守恒和 `PHASE6_CONTRACT.md`。
- 只有所有必要报价单元均有效、币种一致且可按已确认规则聚合时，订单级状态才可为 `available`。
- 任一必要报价单元失败时执行 D-018：订单级为 `unavailable`、`quoted_fee=null`、`applied_fee=Decimal("0.00")`。部分成功金额不得进入订单总额；按 D-024 只保留安全内部诊断，按 D-026 不持久化或跨请求复用。
- `shipping_gst` 只在所有必要单元均有明确 Provider GST 字段和语义证据时，按稳定单元顺序用 Decimal 精确聚合并在订单级展示边界形成两位 Money；任一单元缺少独立 GST breakdown 时订单级为 null，不得展示部分 GST，也不得从 `total_cost` 或商品 GST 反推。它从不进入 Pricing。
- Provider 原始金额字符串/币种与单元 validated Decimal 保留为内部证据；所有单元含 GST total 精确求和后，才按 D-004 在订单级使用 `ROUND_HALF_UP` 标准化到两位，同时形成相等的 `quoted_fee/applied_fee`。缺少 Provider 精度/转换证据时 fail closed。
- 官方 Get Shipment Price 当前没有独立 expiry/reference 字段，因此这两个字段为 `null`。不得把 merchant reference 当 carrier quote reference，也不得发明过期时间。
- `checked_at` 不是报价生成时间或有效期。

冻结的 reason codes（D-024）：

| 状态 | reason code |
|---|---|
| available | `null` |
| unavailable | `PROVIDER_CONFIGURATION_MISSING`, `CARRIER_MAPPING_UNRESOLVED`, `PACKAGE_RULES_NOT_CONFIGURED`, `PACKAGE_DATA_INCOMPLETE`, `QUOTE_UNIT_EMPTY`, `QUOTE_UNIT_DUPLICATE`, `PROVIDER_AUTHENTICATION_FAILED`, `PROVIDER_TIMEOUT`, `PROVIDER_NETWORK_ERROR`, `PROVIDER_RATE_LIMITED`, `PROVIDER_RESPONSE_INVALID`, `CONTRACT_PRICE_UNAVAILABLE`, `PRODUCT_NOT_AVAILABLE`, `CURRENCY_NOT_SUPPORTED`, `PARTIAL_QUOTE_FAILURE`, `PROVIDER_ERROR` |
| unsupported | `SHIPPING_QUOTE_NOT_IMPLEMENTED`, `CARRIER_NOT_IMPLEMENTED` |

### 4.4 D-015 与 D-017 兼容边界

Task 029 已选择 `zero_fallback`：

- 现有 `unsupported / SHIPPING_QUOTE_NOT_IMPLEMENTED` 保持 D-015 的非空 `applied_fee=0.00`。
- 已实现能力本次失败时使用 `unavailable`、独立 reason code、`quoted_fee=null`、`applied_fee=0.00`。
- 两种状态虽然具有相同的降级金额，但 reason code 与能力语义不同；不得互相替换。
- Pricing Service 不需要改变公式，只继续使用 Shipping Quote Service 提供的 applied fee。

Task 028 的兼容方案评估保留如下，Task 029 已正式选择 C：

| 方案 | `unavailable` 的 applied fee | 对 API/总额的影响 | 评价 |
|---|---|---|---|
| A | `null` | Pricing/Order Total 需增加不可计算状态；可能需要 v2 或兼容字段 | 不伪造金额，但影响最大 |
| B | 最近一次仍有效的真实报价 | 必须有持久化、来源、获取时间、有效期和 stale policy | 当前无数据库/有效期证据，不可先做 |
| C — **DECIDED / ZERO_FALLBACK** | `0.00` | 保持 D-012 现状和既有 Pricing 输入 | D-017 已接受；必须保留 unavailable 状态和独立 reason code |
| D | 业务批准的固定 fallback fee | 必须有明确金额、适用范围、GST 和版本依据 | 当前没有依据 |

## 5. 业务决策矩阵

### 5.1 Task 029 已确认决策

| 决策主题 | 状态 | 选择值 | 核心约束 |
|---|---|---|---|
| Tracking Group | **DECIDED** | **UNKNOWN** | 仅为订单内部物流分组，不等同 Package ID、实际包裹或报价单元 |
| unavailable handling | **DECIDED** | **ZERO_FALLBACK** | `quoted_fee=null`、`applied_fee=Decimal("0.00")`，独立 reason code，继续现有 Pricing 公式 |
| Partial Quote Failure | **DECIDED** | **ALL_OR_NOTHING** | 任一必要报价单元失败即订单级 unavailable；部分金额不得作为完整运费 |
| Package Data Source | **DECIDED** | **RULES** | 使用可配置、可追溯、可测试的 SKU 包装映射与确定性装箱规则；真实数据优先 |

决策原因：

- `UNKNOWN`：当前只有内部物流关联，没有实际包裹、装箱或报价单元证据。
- `ZERO_FALLBACK`：保持外部失败时订单总额可按既有 Pricing 公式降级计算，并依靠状态/reason code 防止零值被误报为真实报价。
- `ALL_OR_NOTHING`：部分金额不能证明订单全部运输需求的成本，不能作为完整订单运费。
- `RULES`：现有 SKU 字段描述商品而非包裹；确定性、版本化规则可审计可测试，且未来真实装箱数据可以明确覆盖估算。

这些决策对各层的影响如下：

- Domain：Tracking Group 与 Package/报价单元分离；订单级 Shipping Quote 保持 quoted/applied fee；单元级结果和 Package 模型见 `PHASE6_CONTRACT.md` 的分类契约。
- Shipping Quote Service：用 rules 准备 Package 估算；数据不足直接 unavailable；多单元 all-or-nothing；失败时 zero fallback。
- Pricing Service：公式与实现均不改变，只继续接收 applied fee；unavailable 输入为 Decimal 零值。
- API Response：当前 schema 未修改；未来扩展必须让 unavailable 与 unsupported 使用不同 reason code，并都明确零值不是免费运输。冻结结构见 `PHASE6_CONTRACT.md`。
- Tracking Integration：仍可按 Tracking Group 获取追踪关联，但不得把 Tracking Group 复用为 Package ID 或报价单元。

### 5.2 Task 030 Decision Approval 冻结矩阵

| 主题 | 正式决策 | 冻结边界 | 尚需的实施输入 |
|---|---|---|---|
| Package cardinality | D-020 | 允许拆分/混装；OrderItem 数量严格守恒 | 分配算法已由 D-034 冻结；规则数据仍待提供 |
| Packaging config | D-021 | 独立、只读、版本化；已发布版本不可原地修改 | SKU specs、materials、capacity、tare |
| Carrier quote GST | D-022 | 有证据的含 GST `total_cost` 作为 `quoted_fee/applied_fee`；`shipping_gst` 只读 | 每个 Provider/Product 的税务证据 |
| Provider mapping | D-023 | Provider/Account/Product 显式建模与映射；不得 fallback | 真实 mapping、账号权限和凭证 |
| Reason codes | D-024 | 小型稳定公共 enum；原始错误仅内部诊断 | Adapter error mapping tests |
| List/detail quote | D-025 | 列表 `not_requested` 且不调用 Provider；详情触发 Quote | Backend/OpenAPI/Frontend 协调发布 |
| History/cache | D-026 | 首批不持久化、不跨请求缓存 | 无；未来变化需新决策 |
| Quote product | D-027 | Contract Price 核心；PAC 未批准且不得 fallback | 经 Get Accounts 验证的 Contract Product |
| Tracking status | D-028 | normalized + raw + unknown | Provider raw status 映射证据 |
| Provider precision | D-029 | 遵循明确规则；缺少规则即 unavailable | 每个 Product/合同的精度与舍入证据 |
| List summary amount | D-030 | `order_total = order_subtotal + gst_amount`；`quote_request_state=not_requested`；UI 为 Total before shipping | Backend/OpenAPI/Frontend 协调发布 |
| Product weight/dimensions | D-019/D-021 | 只作为规则输入，不直接成为 Package | 获授权包装数据 |
| Volumetric/chargeable weight | D-029 | 不固定通用公式，不从现有来源字段猜测 | Provider/Product cubing 与计费规则 |
| Currency | D-011/D-024 | 仅 AUD；非 AUD 为 unavailable | 无；FX 不在范围内 |

### 5.3 Task 048 已批准包装决策矩阵（D-032～D-035）

用户已批准 Task 047 的 DEC-1～DEC-4，并由 Task 048 形成正式决策；DEC-5/DEC-6 明确 `DEFERRED / NOT_APPROVED`。详细契约见 `docs/PHASE6_CONTRACT.md` §5.4～§5.8。

| 主题 | 正式决策 | 冻结边界 | 尚需的实施输入 |
|---|---|---|---|
| PackingPolicy schema | D-032 | 结构化封闭 schema；scope 三层匹配；封闭枚举；拆分/混装/上限字段；零匹配 fail closed；policy 只能收紧 | 具体 policy 取值与获批 ruleset（DM-15、DM-16） |
| 约束归属 | D-033 | SKU handling 事实 + 材料能力上限 + policy 收紧；运行时 `EffectiveConstraintView`；AND 兼容性；不新增第四实体、不进 API | 方向/易碎/堆叠/危险品取值与材料能力字段（DM-04～DM-07、DM-13） |
| 生产装箱算法 | D-034 | 分阶段确定性启发式 + Best-Fit Decreasing；Stage 0～6；显式排序键；整单 fail closed；不承诺最优 3D 装箱 | 真实规格与材料数据（DM-01～DM-14） |
| 材料选择 | D-035 | F1～F8 硬过滤 + `smallest_inner_volume`/`priority_order` + 8 条禁止 fallback；零候选 fail closed | 材料目录与 `selection_priority`（DM-09～DM-14） |
| Packaging 配置治理 | **DEC-5（暂缓）** | 未批准；不得实现角色/审批/激活/rollback/审计并声称已具备治理能力 | 治理角色与审批流程（MI-16/MI-17） |
| 多进程全局限流 | **DEC-6（暂缓）** | 未批准；仍为单进程内存限流，多 worker/多实例与真实 Provider 激活仍禁止 | 部署形态与运维参数（MI-18/MI-19） |

**边界重申**：D-032～D-035 冻结的是**规则语义**，不是**数据**。9/9 SKU 仍只有商品物理数据，包装规格 0/9、材料目录 0 条、获批 ruleset 0 份；因此 J2-G 仍为 `BLOCKED`，任何「包装已验证」表述都不成立。

## 6. 技术架构

### 6.1 最小组件

```text
API v1
  -> OrderService (只编排，不解释 provider payload)
       -> TrackingService
       |    -> TrackingProvider registry
       -> ShippingQuoteService
       |    -> QuoteProvider registry
       -> PricingService
       -> RepositoryCollection

Provider registry
  -> AustraliaPostProvider
  -> StarTrackProvider
  -> TNTUnsupportedProvider (仅显式 unsupported)
       -> shared Australia Post Shipping & Tracking transport
```

不使用一个包含所有方法的巨大 Carrier interface。使用两个小 Protocol：

```text
TrackingProvider.track(request) -> ProviderTrackingResult
QuoteProvider.quote(request) -> ProviderQuoteResult
```

Provider registry 只按 Active Configuration Release 固定的 `ResolvedQuoteUnitMapping.provider_revision_id` 和 capability 选择实现；不得直接用 stable ID 猜测 latest Revision，也不得用 carrier 展示文本、tracking number 形状或 Tracking Group 选择 Quote Provider。Australia Post 与 StarTrack 可共享 HTTP transport、认证机制和错误解析工具，但必须保留各自 ProviderIdentity Revision、Account Revision、Product Revision、Mapping Revision、状态 mapper 和 request validator。

### 6.2 配置

敏感凭证只能在后端启动边界从环境变量或等价批准的 secret store 读取；非敏感 Provider/Account/Product/Mapping 元数据使用独立、只读、版本化配置。必须校验：

- environment：testbed 或 production；不允许隐式默认到 production；
- base URL：来自批准配置，不由用户输入；
- API key、secret：敏感字段，`repr`/日志隐藏；
- account number：按 provider 格式验证并作为敏感业务配置处理；
- capability enable flags：tracking 与 quote 分开；
- connect/read timeout：明确的有限值；
- product selection：来自 Get Accounts/批准配置，不散落在业务代码。

配置模型与接口以 `PHASE6_CONTRACT.md` 第 8.4 节为准：Provider、Account、Product、Mapping 均区分 Stable ID 与不可变 Revision ID；Mapping Revision 显式引用三个目标 Revision；Configuration Release 固定获批准 Mapping Revision 集合。Reader 按精确 Revision ID 读取，Capability Validator 只允许 Release 中 verified、环境一致且交叉引用有效的 Revision。实际 ID、Revision 内容、账号、service code、selection scope、凭证和验证证据仍是实施输入。

所有必要 Quote Unit 在网络调用前统一执行 Capability Preflight。请求开始时只捕获一次 Active Release，同一订单全部 Unit 使用同一 `release_revision_id`；任一必要 Adapter/Quote capability 尚未实现时，订单级固定 `unsupported / CARRIER_NOT_IMPLEMENTED` 且不发任何报价请求。Adapter 已实现但 release/mapping/config/account/product/GST/精度验证失败时返回对应 `unavailable` reason，仍不发任何报价请求。凭证有效性只能由受控 testbed 调用验证，环境变量存在不等于可用。

### 6.3 Configuration Release 与配置治理

发布流程为：创建不可变 Revision → schema/外键/Mapping 唯一性校验 → Account 权限及 Get Accounts 证据校验 → Contract Product、GST、精度、Ruleset、capability 和环境校验 → 审批 → 生成不可变 Release → 原子切换 Active Release → 记录发布审计。未审批或未验证 Revision 不得进入 Release。

每个 environment/configuration scope 同一时刻只能有一个 Active Release。切换失败保持原 Release，不允许部分 Provider 使用新配置、部分仍使用旧配置。Rollback 只能原子重新激活先前已批准的不可变 Release；不得修改或删除历史 Revision、改写 Mapping 或通过 latest fallback 回滚。发布和 rollback 审计必须包含原/目标 Release、UTC 时间、主体、原因和审批/审计引用。

每个订单请求在开始时固定 Release 及全部 Mapping/Provider/Account/Product Revision。在途请求继续使用已固定 Revision；Active Release 切换只影响新请求，不得在同一请求的不同 Quote Unit 之间重新解析。Revision provenance 只进入受控内部诊断，不公开凭证或敏感配置。

配置 Revision、Release 和发布/rollback 审计属于配置治理数据，不属于 D-026 禁止的 Quote History，也不授权跨请求 Quote Cache 或 PAC。

### 6.4 HTTP、超时、重试和限流

- Phase 6 需要一个运行时 HTTP client；当前 `httpx` 仅为 dev dependency。实现前必须决定把受支持的 client 加入 runtime dependency，不能依赖测试依赖偶然存在。
- 所有调用使用 HTTPS、有限 connect/read timeout、最大响应体限制和严格 JSON schema 验证。
- Track Items 可按 provider 批量查询，每批最多 10 个 IDs；Australia Post 与 StarTrack 分批。
- 同一订单请求内对重复 tracking group 去重。
- 429 优先遵守 `Retry-After`；若无法在同步请求预算内安全重试，返回 `PROVIDER_RATE_LIMITED`。
- 对 GET Tracking 只做有限、带抖动的重试；认证、验证和业务错误不重试。
- 官方文档没有确认 Get Shipment Price 的幂等保证；自动重试 POST 前必须获得证据或接受明确的内部策略。第一实现可在网络结果不确定时直接返回 unavailable。
- 一个 provider 的失败不取消另一个 provider，也不覆盖另一能力的成功结果。

### 6.5 缓存与并发

初始实现不引入 Redis、数据库或分布式缓存。先使用：

- 单请求去重；
- Track Items 的同 provider 批处理；
- 有界并发；
- 独立 timeout budget；
- fake provider 的确定性测试。

D-026 已冻结首批不做 Quote 历史持久化或跨请求 Quote cache，仅允许请求内去重；Tracking 跨请求缓存也没有获批，不在首批中加入。未来任何 freshness、quote expiry、stale 展示、TTL 或跨请求复用都必须通过新的正式决策。

### 6.6 Error mapping

Integration 层将 HTTP、provider error 和解析失败转换为内部分类异常；Service 层将其转换为稳定 reason code。API 不返回：

- provider 原始响应；
- API key/secret 或 Authorization header；
- 完整 tracking number；
- 客户电话、邮箱、地址的诊断副本；
- stack trace 或内部 endpoint 配置。

外部服务失败属于结果数据的 `unavailable`，不应把整个订单请求转换为通用 500。只有本地数据完整性、未分类内部错误或无法构造合法响应时才使用现有 ErrorResponse 边界。

## 7. API v1 兼容扩展

### 7.1 订单详情

保留现有 envelope 和字段，在 `data` 中新增：

```json
{
  "tracking_results": [
    {
      "tracking_group_id": "SYNTHETIC-GROUP-1",
      "provider": "australia_post",
      "status": "available",
      "reason_code": null,
      "checked_at": "2026-11-07T00:00:00Z",
      "provider_status": "In transit",
      "current_status": "in_transit",
      "latest_event_at": "2026-11-06T23:30:00Z",
      "events": [
        {
          "event_time": "2026-11-06T23:30:00Z",
          "location": null,
          "description": "Synthetic event for contract illustration",
          "provider_status": "In transit",
          "normalized_status": "in_transit"
        }
      ]
    }
  ]
}
```

示例仅用于 shape，不是承运商事实。事件按 `event_time` 的确定顺序返回；排序方向须在实现前固定并测试，建议 API 使用最新在前，Timeline 组件可直接展示。

现有 `shipping_quote` 后续按 D-024/D-025 扩展为 request state 与三种结果状态的联合结构。Money 仍用 Decimal String；`unavailable` 已由 D-017 冻结为 `quoted_fee=null` 和零值 `applied_fee`。Reason code、单元级内部模型和 API 投影已由 D-020～D-029 冻结，列表金额由 D-030 冻结；本任务不修改 API 实现。

### 7.2 订单列表的特殊问题

当前 `list_orders()` 逐笔调用 `get_order()`，并返回包含降级运费的 Order Total。若未来 `get_order()` 直接执行外部查询，列表会产生多次报价调用，增加延迟、敏感数据传输和失败面；Tracking 的 10 requests/min 限制也不允许无界扩张。

D-025/D-030 已冻结：列表不执行 live quote，返回独立 `quote_request_state=not_requested`，quote status/reason 为空；`order_total` 固定为 `order_subtotal + gst_amount`，API/前端表达为 `Total before shipping` 并同时说明 `Shipping quote not requested`。内部 Decimal `0.00` 不是 Quote result、zero fallback 或免费运输。订单详情使用 `requested` 并按结果返回 `unsupported`、`unavailable` 或 `available`；列表与详情金额不同是预期业务结果。D-026 同时禁止用持久化 snapshot 或跨请求 cache 代替本次实时报价。

领域与 Service 边界已由 Task 032 细化：`list_orders()` 返回不含 ShippingQuoteResult 的 `OrderSummaryResult`，不得调用 `get_order()`、Package Estimation、Tracking 或 Provider；`get_order()` 返回 `quote_request_state=requested` 且包含必填 ShippingQuoteResult 的 `OrderDetailResult`。两者可复用只读 Order/Product 关联 helper，但使用独立 Mapper/API schema。现有路径、`data` envelope、Money 和错误结构不变。

### 7.3 Retry

前端 Retry 只重新请求本系统 API，不直接调用 carrier。后端按当前请求重新检查每个独立能力。实现应支持取消旧请求、防止重复点击并分别显示 Tracking 与 Quote 的 loading/error 状态。

如需要只刷新一个分组或一种能力，应新增经过 D-014 一致性审查的 endpoint；本计划不预先冻结未经需求证明的写式 endpoint。

## 8. 前端契约

### 8.1 Tracking Timeline

- 以 tracking group 为卡片边界，展示 provider/carrier display name、StatusBadge、system check time 和事件时间线。
- 显示 carrier status 与 normalized status，但不把内部 group ID 当成事件。
- `available + events=[]` 显示“承运商查询成功，暂未记录事件”。
- `unavailable` 显示稳定用户文案和 Retry；不显示原始 provider error。
- `unsupported` 明确为尚未支持/配置，不使用“暂时故障”文案。
- `location=null` 时省略地点；`latest_event_at=null` 时不构造日期。

### 8.2 Shipping Quote

- `not_requested`：仅用于订单列表调用状态，不展示报价金额、Provider reason 或检查时间。
- `available`：展示 quoted fee、applied fee、只读 shipping GST 和 system check time；单元结果保持内部诊断，不向 API/前端公开。若 provider 没有 expiry/reference，不显示占位值。
- `unavailable`：显示 A$0.00 降级金额和独立失败原因，不得显示成 carrier free shipping 或真实零报价。
- `unsupported`：D-015 期间继续显示 A$0.00 降级说明。
- 多报价单元部分成功时，订单级显示 unavailable 和 A$0.00；按 D-024/D-026，部分成功事实只保留为本次请求的安全内部诊断，不公开、不持久化、不跨请求复用。

### 8.3 类型与运行时验证

- Money amount 继续为 `string`，不得转为 number 或由前端求和。
- TypeScript 使用 discriminated union 覆盖 `not_requested/requested` 调用状态和三种结果状态的字段不变量。
- runtime validator 同步验证 UTC 时间、Money、reason code、request state 及 available/unavailable/unsupported 的字段组合。
- Tracking 与 Quote 的 loading/error/result 状态独立；一个失败不能隐藏另一个成功结果。

## 9. 安全与可靠性

- 任何生产/testbed 凭证只存在于后端环境配置，不进入 Git、前端 bundle、JSON、日志或文档示例。
- provider request builder 只发送 API 必需的最小客户字段；是否允许发送电话/邮箱通知必须单独确认，默认不启用。
- 日志只记录 correlation ID、provider code、capability、分类结果、耗时和安全 reason code。
- tracking number 使用不可逆摘要或尾部最小片段进行诊断，默认完全不记录。
- 不记录完整请求/响应 body；测试 fixture 使用合成客户、地址、tracking ID 和 provider response。
- account number、API key、secret 和 Authorization header 必须在模型 `repr`、异常和 telemetry 中隐藏。
- provider 响应设大小上限并做 closed-schema 验证；未知字段不直接透传到 API。
- 所有 checked/event/expiry 时间均为 timezone-aware；API 统一输出 UTC。

## 10. 测试策略

### 10.1 Provider contract tests

- 使用保存的合成响应验证 Australia Post 与 StarTrack mapper，不调用真实 API。
- 覆盖多 ID、空事件、顶层状态、StarTrack consignment/freight item 差异、单 ID 业务错误、HTTP 400/401/403/429/5xx、timeout、无效 JSON、超大响应和未知状态。
- 验证请求不混合 provider、每批不超过 10 个 IDs、认证和 account header 不进入异常文本。
- Quote 覆盖含 GST total、total_gst、合同无价格、产品无效、package 数据不全、体积计价警告、非 AUD/非法 Decimal、缺失字段和部分 group 成功。

### 10.2 Service tests

- available / unavailable / unsupported 全路径。
- Tracking 成功 + Quote 失败，以及 Tracking 失败 + Quote 成功。
- 查询成功无事件与查询失败严格区分。
- provider mapping unresolved 不发网络请求。
- 多分组去重、分 provider 批处理、稳定结果顺序。
- quote aggregation、D-004 订单级 `ROUND_HALF_UP`、zero fallback、含 GST total、只读/nullable `shipping_gst` 和 all-or-nothing 均按 D-017、D-018、D-022、D-029 的已冻结矩阵编写期望值，不再等待业务确认。
- 全金额链路断言 Decimal-only，无 float。
- 覆盖原始金额证据、单元 validated Decimal、exact aggregate、两位 `quoted_fee/applied_fee` 和 API Money 的完整转换链。
- 覆盖 Capability Preflight：必要 Adapter 未实现为 unsupported；mapping/config/product 不可用为 unavailable；任一预检失败时不发出任何报价网络请求；多单元调用失败固定 all-or-nothing。

### 10.3 API tests

- 新字段保持现有 `data` envelope 和统一 ErrorResponse。
- Money 为恰好两位 Decimal String，UTC 时间合法。
- 每种 status 的 reason/data 不变量。
- 外部失败返回订单数据中的独立 unavailable result，而不是泄露为 500。
- OpenAPI 与 TypeScript/runtime validator 一致。
- 响应、异常和 caplog 不包含凭证、完整 tracking number 或客户 PII。

### 10.4 Frontend tests

- Timeline 的 events、empty、unsupported、unavailable、retry 和 loading。
- Shipping Quote available、partial、expired（仅在有规则后）、unavailable、unsupported。
- Tracking/Quote 任一失败不隐藏另一结果。
- Money 只添加 `A$`，不转 number、不重新计算。
- null location、未知 normalized status、缺失 expiry/reference 的优雅降级。
- AbortController、重复 retry 和可访问焦点/状态播报。

### 10.5 Sandbox 与 E2E

- 单元/集成测试不得依赖真实 API。
- 只有用户明确授权且提供安全环境后，才运行 testbed smoke test。
- testbed 只证明认证、请求 schema 和受模拟响应支持的 mapper；不能证明真实 tracking、合同价格、配额或生产可用性。
- production 验证需单独授权、最小范围和可撤销凭证；不得用真实客户数据做开发测试。

## 11. 三批实施计划

### Batch A：Integration Foundation & Tracking

前置门槛：按 D-023 提供显式 Provider/Account/Product/Mapping Revision、获批准 Configuration Release、账号/测试环境和安全凭证；确认 runtime HTTP client 参数；获得 Phase 6 实施授权。

交付：

- provider config、shared transport、capability registry 和分类错误；
- 独立 Provider/Account/Product/Mapping Revision Readers、Configuration Release Reader/Registry、request-level pinning 及 validation evidence；
- Australia Post / StarTrack TrackingProvider；
- TrackingResult/TrackingEvent、TrackingService 和 OrderService 独立编排；
- API detail 的 `tracking_results`；
- 前端 Tracking Timeline 和局部 retry；
- fake/provider contract/API/frontend tests。

验收：不记录或暴露凭证/完整 tracking number；空事件与失败可区分；两种 provider 不混批；Quote 仍保持 D-015，Tracking 失败不影响现有订单/Quote。

### Batch B：Shipping Quote & Pricing Integration

前置门槛：D-020～D-030 已批准；仍需提供 D-021 ruleset 数据、D-023 Revision/Release mapping 与账号条件、D-022/D-029 Provider/Product 证据，并获得 Phase 6 实施授权。

交付：

- package request model 与确认后的 packing input；
- Australia Post / StarTrack QuoteProvider；
- per-quote-unit result 和 order aggregation；
- ShippingQuoteResult 三状态联合契约；
- Pricing/Order Service 的已批准 applied-fee 编排；
- API/前端 `quote_request_state`、D-030 `Total before shipping`、detail quote、partial failure 和只读 shipping GST 展示；
- Decimal、GST、聚合和失败测试。

验收：真实 quote source 可追溯；没有二次 GST；没有 float；部分报价不生成虚假总额；D-015 只在其原始未实现语义内保留。

### Batch C：Reliability & End-to-End Validation

前置门槛：获得受控 testbed 凭证和用户对外部调用的明确授权。

交付：

- timeout、bounded retry、429/backoff、response limits 和安全日志；
- provider contract regression；
- testbed smoke evidence 与限制说明；
- backend/frontend/E2E 回归、安全复核和 README 更新；
- 独立代码审查与修复闭环。

验收：自动化测试可离线重复；testbed 结论不夸大为 production；凭证/PII 未进入 Git、日志和构建产物；所有实施前置输入有证据或明确限制。

### Batch J2：Production Packaging（Task 048 契约已冻结，实施未开始）

Batch J2 取代第 11 节 Batch B 中的 Packaging 部分；Batch A/B 中的 Tracking 与 Shipping Quote 规划**不变**。D-032～D-035 已冻结规则语义，因此 J2-B～J2-E 可在没有真实包装数据的前提下用 synthetic fixtures 实现**机制与行为**。

| 批次 | 范围 | 依赖 | 验收标准 | BLOCKED 条件 |
|---|---|---|---|---|
| J2-A | 契约与决策落地（已完成于 Task 048） | 用户批准 DEC-1～DEC-4 | D-032～D-035 与契约 §5.4～§5.8 逐条可对照 | 已完成，不再重复 |
| J2-B | Packaging Rules schema、加载期校验、只读 Reader | J2-A | §13.2「Policy schema 与匹配」「约束归属」测试全绿；synthetic 隔离不削弱；默认应用仍 `PACKAGE_RULES_NOT_CONFIGURED` | J2-A 未完成；DEC-5 未批准（仅治理载体） |
| J2-C | 生产级确定性装箱算法（`best_fit_decreasing`） | J2-B | §13.2「算法」测试全绿；确定性重跑一致；整单 fail closed；性能预算达标；商品数据零读取 | J2-B 未完成 |
| J2-D | 材料选择（F1～F8 + 两策略 + 8 条禁止 fallback 负向测试） | J2-B、J2-C | §13.2「材料选择」测试全绿；零候选 fail closed | J2-B/C 未完成 |
| J2-E | OrderService 编排、API/OpenAPI 投影、Frontend 展示、Runtime Validation | J2-C、J2-D | 契约 §9.3 字段集合不变；D-030/D-031 回归不破；前端不重算金额；约束/材料/策略不进入 API | J2-C/D 未完成 |
| J2-F | Packaging 配置治理（角色/审批/激活/rollback/审计） | **DEC-5 批准** | 按 DEC-5 批准内容另行定义 | **`DEFERRED`：DEC-5 未批准，本批次不在当前授权范围** |
| J2-G | 真实数据接入、获批 ruleset 激活与生产验证 | J2-B～J2-F + DM-01～DM-18 | 数据验收 12 条全部满足 + 抽样业务复核签字 | **`BLOCKED`：无任何真实包装数据、材料目录或获批 ruleset** |
| J2-H | 回归、性能、安全与文档门禁 | J2-B～J2-E | Backend/Frontend/Markdown/OpenAPI/决策编号/业务 JSON 哈希全部通过 | 前置批次未完成 |

接口与投影约束（本批次不改变）：

```text
PackagingRulesReader.get_active(at) -> PackagingRuleSet                    # 契约 §4.4，接口不变
PackageEstimationService.estimate(order, products, rules) -> PackageEstimationResult
PackageResponse                                                             # 契约 §9.3，字段集合不变
EffectiveConstraintView                                                     # 内部派生，不进入 API/provenance
```

**明确不在 J2-B～J2-E 范围**：DEC-5 治理实现、DEC-6 限流实现、Shipping Quote 真实化、PAC、Quote History/缓存、数据库/Redis、真实 Provider 调用、真实包装数据导入。

## 12. Remaining Prerequisites and Deferred Scope

### 12.1 已冻结、不再待批准

OD-01～OD-10 已分别形成 D-020～D-029；Task 034 已形成 D-030；Task 048 依据用户批准形成 D-032～D-035。Package cardinality、版本化 rules、GST/applied fee、显式 Provider mapping、reason codes、列表/详情触发、无历史/cache、Contract Price、Tracking status、Provider Decimal 规则、列表 `Total before shipping`、PackingPolicy schema、约束归属、生产装箱算法与材料选择均已冻结。

### 12.2 实施前置输入

1. 每个现有 tracking group 的显式 Provider/Account/Product/Mapping Revision 和获批准 Configuration Release；不得修改或猜测合并 carrier 文本的语义，也不得使用 latest fallback。
2. 合格 Contract Account 对 Tracking、Get Accounts、Get Shipment Price 的权限、凭证和受控环境验证。
3. 具体 SKU packaging specs、材料目录、capacity、tare、orientation/易碎/堆叠/危险品取值和获批 ruleset（DM-01～DM-18）。**算法、策略与约束归属已由 D-032～D-035 冻结，不再属于待批准项**。
4. 每个启用 Provider/Product 的 GST、cubing、chargeable weight、金额精度和舍入证据。
5. Provider raw Tracking Status 到 D-028 normalized enum 的映射证据。
6. runtime HTTP client 的 timeout、并发、限流和 bounded retry 参数（多进程限流策略属 DEC-6，暂缓）。
7. 配置发布审批流程，以及创建不可变 Revision 和生成 Configuration Release 的职责与权限（Provider 侧；Packaging 侧治理属 DEC-5，暂缓）。
8. Active Release 原子切换与 rollback 权限、rollback 操作步骤、审批和审计要求（Provider 侧；Packaging 侧属 DEC-5）。
9. 请求级 Revision pinning 和在途请求处理策略；同一请求不得跨 Release 漂移。
10. 配置 provenance 的保存期限、访问控制和受控查询方式；不得保存凭证或把它扩张为 Quote History。

### 12.3 Phase 6 可暂缓或禁止

- TNT 是否从 Bonus 转为实际交付；在此之前保持 `unsupported / CARRIER_NOT_IMPLEMENTED`。
- PAC、跨请求缓存和报价历史；D-026/D-027 明确不属于首批，未来必须另立决策。
- 后台刷新/异步工作流；同步方案不能满足已确认限制时再立项。
- `0Days` ETA 的业务语义；与物流 API 集成独立，但前端仍需保持现有降级。
- **DEC-5 Packaging 配置治理**：`DEFERRED / NOT_APPROVED`；Batch J2-F 不在当前授权范围。
- **DEC-6 多进程全局限流**：`DEFERRED / NOT_APPROVED`；多 worker/多实例部署与真实 Provider 激活继续禁止。

### 12.4 与 Phase 6 核心实现无关

- HTML v2 GST 规则是否获得出题方正式批准；继续保留 caveat，不改变 D-004。
- 原始 PDF 第二笔订单编号冲突的最终审计展示方式。
- 公开仓库采用完全替换还是字段级脱敏；必须在公开发布前解决，但不决定 provider 设计。
- JSON 是否长期只读；本阶段继续只读，未来订单写入需另立架构决策。

## 13. Implementation Readiness

最终状态：`CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW`

已就绪：

- 当前代码、数据、API 和前端边界已审计；
- Australia Post / StarTrack 官方 Tracking、Quote、认证、testbed、账号和限制已形成证据链；
- Tracking/Quote 的领域结构、独立失败语义、安全边界和测试策略已整改；D-030 List/Detail 金额语义、不可变 Provider Revision、Configuration Release、金额转换链、`shipping_gst` 和 Capability Preflight 已补齐；
- 三批纵向实施计划已定义；
- D-016～D-030 已确认 Tracking Group、fallback、aggregation、rules、Package、Provider、GST、status、lifecycle、列表金额与 Decimal 边界；
- 未引入微服务、数据库、Redis、消息队列或未经证明的 endpoint/字段。

尚需实施输入：真实 Provider/Account/Product/Mapping Revision、获批准 Release、配置治理权限、账号权限、ruleset 数据、Provider/Product 税务/重量/精度证据和 runtime HTTP 参数。

Task 034 已关闭 Task 033 的 T033-M01/M02/L01/L02，验收状态为 `PASS`。下一步是 Task 035 对整改后契约执行独立只读复审；复审通过前不得创建 Contract Checkpoint 或进入 Batch A～C。本文状态不表示真实物流与报价功能已经实现、已获凭证或已通过 sandbox/production 验证；Phase 6 仍为 `NOT_STARTED`。

`TASK_034_FINAL_STATUS: PASS`

> **Task 048 追记**：上文的 `CONTRACT_REMEDIATED_AWAITING_INDEPENDENT_REVIEW` 状态与「Phase 6 仍为 `NOT_STARTED`」表述已被后续任务推进：Task 043 关闭 Batch I 契约关卡并创建 Checkpoint `6ccdc5f`；Task 045/046 完成 Batch J1 并创建 Checkpoint `3c3675e`；Task 048 冻结 D-032～D-035。当前实际状态为 Phase 6 `IN_PROGRESS`、Batch I `PARTIALLY_COMPLETE`（离线实现已冻结，真实 Provider 验证 `BLOCKED`）、Batch J1 `COMPLETE`（synthetic-only）、Batch J2 Contract `COMPLETE`、Batch J2 Implementation `NOT_STARTED`。历史结论不回写。

## 14. Batch J1 离线实施记录（Task 045）

> 本节记录实际实施结果，覆盖第 11 节 Batch B 中"Packaging 部分"的离线范围。Shipping Quote、PAC、TNT、报价历史与跨请求缓存的规划结论不变。

### 14.1 实际完成范围

| 交付 | 状态 | 说明 |
|---|---|---|
| Package Domain（`Package`/`PackageItem`/`PackageDimensions`/`PackageWeight`/`PackageProvenance`/`PackageEstimationResult`/`PackageEstimationDiagnostic`） | 已实现 | 不可变、`extra="forbid"`、Decimal-only、尺寸 `_mm`/`_mm3`、重量 `_g` |
| 只读版本化 Packaging Rules（`PackagingRuleSet`/`SkuPackagingSpec`/`PackageMaterialSpec`/`PackingPolicy`） | 已实现 | D-021 外壳、按 ID/版本不可变、生效窗口、引用完整性 |
| `PackagingRuleSetReader` + `StaticPackagingRuleSetReader` | 已实现 | 缺失或不在生效窗口即配置失败 |
| `PackageEstimationService.estimate(order, products, rules)` | 已实现 | 契约 §4.4 签名；另有 `estimate_for_order` 负责解析 Active ruleset |
| 确定性 synthetic packing strategy | 已实现 | 顺序 first-fit（packed unit 体积 + 毛重），仅供 J1 测试 |
| 数量守恒 / split 策略 / provenance | 已实现 | 违反即 `unavailable`，不返回部分 Package |
| OrderService 集成与故障隔离 | 已实现 | 详情提供 `packages`/`package_estimation`；列表不调用估算；估算异常不影响 Tracking/Quote/Pricing |
| API Schema / Mapper / OpenAPI | 已实现 | `PackageEstimationResponse` + `PackageResponse`；尺寸与重量为十进制字符串 |
| Frontend 类型 / Runtime Validator / PackagePanel | 已实现 | 覆盖 available、多 Package、unavailable、规则未配置、数据不完整、synthetic 标注 |
| 自动化测试 | 已实现 | Backend 385 passed；Frontend 75 passed（详见 Task 045 报告） |

### 14.2 与冻结契约的投影细化（Task 046 已确认）

以下为实现层细化，未改变冻结业务语义，已由 Task 046 独立复审确认：

1. `OrderDetailResult` 同时暴露 `packages` 与 `package_estimation`，且 `package_estimation` 为**必填**（契约 §4.1 规定每次详情都有一次估算结果）；不变量强制 `packages == package_estimation.packages`，因此不存在两个字段表达不同集合或状态的可能。
2. 订单详情 API 使用嵌套的 `package_estimation` 对象承载 `status`/`reason_code`/`checked_at`/`source`/`ruleset_id`/`ruleset_version`/`synthetic_ruleset`/`packages`。契约 §9.3 只冻结了单个 Package 的字段，未规定外层载体；嵌套使 `unavailable` 与"零 Package"不可能混淆。`PackageResponse` 的字段集合与 §9.3 完全一致。
3. 尺寸与重量以十进制字符串输出（非 JSON number），与 D-011 的精度哲学一致，避免浏览器经过二进制浮点。Money 仍严格按 D-011 两位小数。
4. 新增 `synthetic_ruleset` 布尔字段（必填，无默认值），用于区分合成测试规则与生产规则，满足"不得把合成数据描述为生产能力"；它只暴露规则性质，不暴露材料、策略或容量等内部实现。
5. `PackingPolicy` 只实现最小 synthetic 形态；`PackagingRuleSet.synthetic_only` 为 `Literal[True]`，非 synthetic ruleset 无法构造；Service 另外拒绝非 synthetic ruleset/policy，防止 `model_construct` 绕过。
6. Domain 独立校验数量守恒与归属（Task 046 整改）：`OrderDetailResult` 自行验证 Package 属于本订单、行索引存在、SKU 与订单行一致、逐行数量守恒，且 `unavailable` 时不得携带 Package；不依赖 Service 的分配过程自证。
7. API 与前端交叉校验（Task 046 整改）：Package 的 `ruleset_id`/`ruleset_version` 必须与估算一致；Package item 引用的 `order_number` 必须等于详情订单号。
8. 容量不足与 split 策略冲突仍映射到 `PACKAGE_DATA_INCOMPLETE`（契约未提供容量/策略专属公共 code，且不得新增枚举）；前端文案同时覆盖"数据不完整或无法满足包装规则"两种情况。

### 14.3 仍未解决的业务决策与外部输入

Task 048 更新：DEC-1～DEC-4 已获用户批准并形成 D-032～D-035（规则语义已冻结）；DEC-5/DEC-6 仍为 `DEFERRED / NOT_APPROVED`。

- **DEC-1 → D-032**（已批准）：`PackingPolicy` 结构化封闭 schema，见契约 §5.4。
- **DEC-2 → D-033**（已批准）：约束三处归属与 `EffectiveConstraintView`，见契约 §5.5。
- **DEC-3 → D-034**（已批准）：分阶段确定性启发式 + Best-Fit Decreasing，见契约 §5.6。
- **DEC-4 → D-035**（已批准）：材料选择 F1～F8 + 两种封闭策略 + 8 条禁止 fallback，见契约 §5.7。
- **DEC-5（暂缓）**：Packaging 配置治理（角色/审批/激活/rollback/审计/载体）未批准，J2-F 不在授权范围。
- **DEC-6（暂缓）**：多进程全局限流未批准，单进程约束与多 worker 禁令继续有效。
- 真实 SKU 包装规格、包装材料目录、容量/皮重、方向/易碎/堆叠/危险品取值与获批 ruleset 仍全部缺失；真实 Shipping Quote 证据（Contract Price、GST、cubing、精度）同样缺失。

### 14.4 阻塞条件

- Batch J2 **契约**阻塞已解除（Task 048）：D-032～D-035 已冻结。
- Batch J2 **实施**（J2-B～J2-E、J2-H）可在 synthetic fixtures 下开始，但不得宣称生产就绪。
- Batch J2-F 阻塞于 DEC-5 批准（暂缓）。
- Batch J2-G 阻塞于真实包装数据（DM-01～DM-18）与获批 ruleset。
- Batch K 阻塞于 J2 生产启用、testbed 授权与运维参数（含 DEC-6）。
- 真实 Provider 验证继续阻塞于 Batch I 的外部输入。

`TASK_045_FINAL_STATUS: PASS`（离线实现；真实包装数据与真实 Shipping Quote 未验证）

## 15. Batch J2 契约实施记录（Task 048）

> 本节记录 D-032～D-035 的正式化结果。Shipping Quote、Tracking、PAC、TNT、报价历史与跨请求缓存的规划结论不变；本任务不修改任何代码、数据或依赖。

### 15.1 已冻结内容与契约位置

| 决策 | 主题 | 契约位置 | 状态 |
|---|---|---|---|
| D-032 | `PackingPolicy` 结构化封闭 schema、匹配优先级、加载期校验、零匹配 fail closed | `PHASE6_CONTRACT.md` §5.4 | `APPROVED / FROZEN` |
| D-033 | 约束三处归属、材料/SKU 新增字段、`EffectiveConstraintView` 合并规则、商品事实隔离 | §5.5 | `APPROVED / FROZEN` |
| D-034 | Stage 0～6、排序键、方向枚举、容量/重量、拆分混装裁决、性能边界、整单 fail closed | §5.6 | `APPROVED / FROZEN` |
| D-035 | F1～F8 硬过滤、两种排序策略、冲突处理、零候选、8 条禁止 fallback | §5.7 | `APPROVED / FROZEN` |
| — | Synthetic-only 与 Production Ruleset 边界（J1 隔离保留 + J2 门禁要求） | §5.8 | `CONFIRMED`（安全边界） |

### 15.2 与 J1 已冻结实现的关系

- J1 的 Package Domain、守恒校验、provenance、`PackageEstimationService` 接口、API 投影与前端展示**均不改变**。
- J1 的 `SyntheticPackingStrategy.SEQUENTIAL_FIRST_FIT` 与 `SMALLEST_VOLUME_FIT` 保留为回归对照，但**不是**生产算法；生产算法为 `best_fit_decreasing`（D-034）。
- `synthetic_only: Literal[True]`、Service 纵深拒绝、默认无 ruleset 的 fail-closed 装配全部继续有效；不得通过放宽该标记激活生产行为。
- 未新增公共 reason code；容量不足与 split 冲突继续映射为 `PACKAGE_DATA_INCOMPLETE`（Task 046 F-07 保留）。

### 15.3 未授权范围

- **DEC-5 Packaging 配置治理**：`DEFERRED / NOT_APPROVED`，J2-F 不在授权范围。
- **DEC-6 多进程全局限流**：`DEFERRED / NOT_APPROVED`，部署约束与多 worker 禁令继续有效。
- 真实包装数据导入、真实 Provider 调用、Batch K、Phase 7 均未开始。
- Batch J2 实施（J2-B～J2-E、J2-H）已获准在 synthetic fixtures 下进行，但**不得**表述为生产验证。

`TASK_048_FINAL_STATUS: PASS`（契约更新；`BATCH_J2_CONTRACT: COMPLETE`、`BATCH_J2_IMPLEMENTATION: NOT_STARTED`）
