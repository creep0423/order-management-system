# Phase 6 外部集成就绪性审计（Task 044）

- 审计日期：2026-11-08
- 审计类型：Audit & Planning（只读审计，不实现功能）
- 审计基线 HEAD：`0683c678383e8bec1db73c6fbd1eec184cc725ab`
- 依据：`AGENTS.md`、D-001～D-031、`docs/PHASE6_CONTRACT.md`、`docs/PHASE6_INTEGRATION_PLAN.md`、`docs/ARCHITECTURE.md`、`docs/PROJECT_PLAN.md`、当前代码/测试/数据字段结构
- 本次审计**未**执行真实 Provider 请求、Get Accounts、凭证读取、配置发布或业务 JSON 修改

---

## 1. Executive Summary

**结论：Phase 6 Batch J 的"契约与离线工程"与"真实生产输入"可以清晰切割。**

1. **Batch I 真实 Provider 验证仍然 BLOCKED**，且阻塞项不是代码缺陷，而是六类外部输入：Provider/Account/Product/Mapping Revision 内容、获批 Active Release、服务端凭证与账号权限、testbed 访问授权、受控环境、以及每个 group 的显式 Provider 归属。**没有任何一项可以在本仓库内自行生成。**
2. **Packaging 数据是 Batch J 的真实硬约束**：当前 9 个 SKU 只有**商品**重量/尺寸/体积/体积毛重，**完全没有任何包装规格**（无包装三维、无单件包装重量、无材料、无皮重、无 capacity、无方向/易碎/堆叠/危险品约束）。`skus.json` 中不存在任何 packing 字段。
3. **Batch J 的 Package 领域契约本身是充分且可实现的**：`Package`、`PackageItem`、`PackageDimensions`、`PackageWeight`、`PackageProvenance`、`PackageEstimationResult`、`PackageEstimationService` 接口、数量守恒、确定性原则、错误 reason、`PackageResponse` 投影与测试契约均已冻结，可用 synthetic fixtures 离线实现。
4. 但存在 **2 项必须在开始"完整装箱算法"前解决的真实契约缺口**（不是数据缺口）：`PackingPolicy` 只有散文描述而无字段级 schema；方向/易碎/堆叠/危险品约束在冻结的最小 ruleset schema 中**没有承载字段**。另有 1 项：没有批准任何具体分配算法。
5. 因此本审计给出**分层结论**：`Batch J Contract Ready` = **NO（整体）**，但 **bounded offline slice J1 = YES**；`Batch J Offline Implementation Ready` = **YES（限于 J1 范围 + synthetic fixtures）**；`Batch J Production Data Ready` = **NO**。
6. **Audit A 另有 2 项实现层发现**（不影响 Batch I 结冻，但会阻塞真实激活）：StarTrack 账号"不得以 0 开头"的校验属推断而非官方证据；AP 账号要求调用方已左补零到 10 位，集成边界未做归一化。
7. **Audit E 治理结论**：现有 `TrackingConfigurationCatalog` 只是内存内 append-only Revision 存储，**不具备**审批主体、激活指针、rollback、审计日志。Enterprise 配置治理仍为 `BLOCKED_BUSINESS_DECISION`。
8. **Audit F 运维发现**：`InMemoryTrackingRateLimiter` 是**单进程**内存实现；一旦以多 worker 部署，10 requests/minute 的全局约束不成立。文档已如实标注"单进程"，因此这是**部署约束**而非代码缺陷，但必须在生产部署决策中显式固化。

**最大程度减少阻塞的工程建议**：允许 Batch J 只做 **J1（Package 领域 + ruleset 读取 + 守恒 + provenance + fail-closed + API/前端投影，全部 synthetic）**，把"完整装箱算法 + 真实规格 + 材料目录 + 容量/皮重"留给 J2。J1 不依赖任何外部输入。

---

## 2. Current Git / Phase Baseline

### 2.1 审计开始时实际核对结果

| 项目 | 实际值 | 与任务预期 |
|---|---|---|
| Branch | `main` | 一致 |
| HEAD | `0683c678383e8bec1db73c6fbd1eec184cc725ab` | 一致 |
| HEAD^ | `6ccdc5f5300daa3aa92da97f7ae923596c605a11` | 一致（Batch I Checkpoint） |
| HEAD^^ | `30544ad226bae79795c47028383a99e16581646b` | 一致（Contract Checkpoint） |
| 工作区 | clean（0 dirty entries） | 一致 |
| 暂存区 | 空 | 一致 |
| Untracked | 无 | 一致 |

### 2.2 阶段与冻结状态

- D-001～D-031 全部有效且冻结；`docs/DECISIONS.md` 内 D 编号唯一、无缺号、无更高编号。
- Phase 6：`IN_PROGRESS`；Batch I：离线实现 COMPLETE 且已 Checkpoint，真实 Provider 验证 `BLOCKED`；Batch J/K：`NOT_STARTED`。
- 四个业务 JSON SHA-256 与冻结基线一致（orders `8305fba3…`、skus `fa71b788…`、skus_raw `44b0db54…`、tracking `4d79e67c…`），审计期间未修改。
- Backend 286 tests / Frontend 49 tests 的基线未被本次审计触碰。

### 2.3 审计中发现的两项文档不一致（不修改，仅记录）

| 编号 | 现象 | 影响 | 建议 |
|---|---|---|---|
| D-01 | 任务将 `backend/README.md` 列为权威来源，但该文件**不存在**（`backend/integrations/README.md` 存在） | 后端运行/配置/部署说明缺少单一入口 | 由文档所有者决定是否新增；不属本任务授权范围 |
| D-02 | `PHASE6_INTEGRATION_PLAN.md` 使用 Batch A/B/C（Tracking / Quote&Pricing / Reliability），而 Task 037 起全程使用 Batch I/J/K | 批次命名不一致，易误读 | 记录映射：A≈I、B≈J、C≈K；不修改冻结文档 |

---

## 3. Audit A — Batch I External Provider Readiness

### 3.1 Provider Identity

| 检查项 | 现状 | 证据 | 状态 |
|---|---|---|---|
| Provider Stable ID | 存在模型位（`provider_revision_id`），**无实际 ID 值** | `backend/models/tracking.py:305-327` | `BLOCKED_EXTERNAL_INPUT` |
| Provider Immutable Revision ID | 模型与不可变性已实现，**无内容** | `backend/services/tracking_configuration.py:98-110` | `BLOCKED_EXTERNAL_INPUT` |
| Adapter identity | 已实现 `AustraliaPostTrackingProvider` / `StarTrackTrackingProvider`，`adapter_key` 来自配置 | `backend/integrations/tracking.py:545-550` | `READY`（代码） |
| API environment | `ProviderEnvironment{TESTBED,PRODUCTION}`，Release 内强制一致 | `backend/models/tracking.py:82-84,460-461` | `READY`（契约+代码） |
| Base URL | 强制 credential-free HTTPS，Release 内一致校验 | `backend/models/tracking.py:98-112,478-489` | `READY`（代码） |
| Capability definition | `ConfigurationCapability{TRACKING,SHIPPING_QUOTE}`，Release 校验 tracking capability | `backend/models/tracking.py:87-89,490-491` | `READY`（代码） |
| Timeout configuration | connect ≤30s、read ≤60s，**无默认值**（必须显式提供） | `backend/models/tracking.py:319-321` | `BLOCKED_OPERATIONS_DECISION`（需运维定值） |
| Credential reference | `credential_ref` 仅引用，值不进配置；resolver 存在但未接线 | `backend/integrations/credentials.py:29-62` | `BLOCKED_EXTERNAL_INPUT` |
| Provider verification evidence | 仅有 `evidence_ref` 字符串位，无真实证据 | `backend/models/tracking.py:292-302` | `NEEDS_EVIDENCE` |

**特别确认**：`tracking.json` 的 3 个 group 中，2 个 carrier 文本为合并值 `StarTrack / Australia Post`，1 个为 `TNT`。按 D-023 与 Task 030 结论，**不得**由该文本、tracking number 形状或 Tracking Group ID 推断 Provider；默认应用因此对全部 group 返回 D-031 `CARRIER_MAPPING_UNRESOLVED`。

### 3.2 Account Configuration

| 检查项 | Australia Post | StarTrack | 证据 | 状态 |
|---|---|---|---|---|
| Account Stable ID | 无 | 无 | 无配置数据 | `BLOCKED_EXTERNAL_INPUT` |
| Account Revision ID | 模型就绪，无内容 | 模型就绪，无内容 | `backend/models/tracking.py:330-342` | `BLOCKED_EXTERNAL_INPUT` |
| Provider Revision 外键 | 强制相等校验 | 强制相等校验 | `backend/models/tracking.py:494-501` | `READY`（代码） |
| Environment | 强制与 Release 一致 | 强制与 Release 一致 | 同上 | `READY`（代码） |
| Origin address/reference | `origin_id` 必填，无值 | 同 | `backend/models/tracking.py:340` | `BLOCKED_EXTERNAL_INPUT` |
| Account number/reference | 格式规则：10 位数字 | 格式规则：8 位数字且不以 `0` 开头 | `backend/models/tracking.py:278-289` | 见下方 A-F1/A-F2 |
| Account capabilities | 需含 `TRACKING` | 需含 `TRACKING` | `backend/models/tracking.py:500-501` | `READY`（代码） |
| Get Accounts 验证结果 | 未执行 | 未执行 | 本任务禁止调用 | `BLOCKED_EXTERNAL_INPUT` |
| 账号使用权限 | 未提供 | 未提供 | 无开通材料 | `BLOCKED_EXTERNAL_INPUT` |

**A-F1（NEEDS_EVIDENCE）**：StarTrack 账号校验额外要求 `not account.startswith("0")`。已调研资料（`PHASE6_INTEGRATION_PLAN.md` §3.2）只说明"StarTrack account number 为 8 位且不补零"，**没有**说明 8 位账号不得以 `0` 开头。该条件是实现推断，若真实账号以 `0` 开头将被错误拒绝。不改代码，登记为待证据项。

**A-F2（NEEDS_EVIDENCE）**：AP 账号"必要时左补零到 10 位"是官方发送格式要求，但 `ProviderCredentials` 要求**恰好 10 位**，且 `EnvironmentCredentialReader` 原样透传环境变量，集成边界**没有**归一化步骤。真实账号若以 9 位配置将直接被拒绝。登记为实现缺口（真实激活前需确认由配置侧补零还是代码侧归一化）。

### 3.3 Product and Mapping

| 检查项 | 现状 | 状态 |
|---|---|---|
| Product Stable ID / Revision ID | 模型就绪，无内容（`backend/models/tracking.py:345-365`） | `BLOCKED_EXTERNAL_INPUT` |
| Service code | 必填字段，无值 | `BLOCKED_EXTERNAL_INPUT` |
| Contract Price 证据 | 仅治理占位字段 `contract_price_aud`，从不被读取 | `BLOCKED_EXTERNAL_INPUT` |
| GST evidence | 仅 `gst_semantics_ref` 引用位 | `NEEDS_EVIDENCE` |
| Decimal precision evidence | 仅 `precision_rule_ref` 引用位 | `NEEDS_EVIDENCE` |
| Product permissions | 未验证 | `BLOCKED_EXTERNAL_INPUT` |
| Mapping Revision | 模型就绪；`tracking_group_id` 选择器强制执行 | `READY`（代码） |
| Selection scope | 必填字符串，无值 | `BLOCKED_EXTERNAL_INPUT` |
| Tracking Group → Provider 业务对应 | **完全缺失**（2 组为合并文本） | `BLOCKED_EXTERNAL_INPUT` |

禁止项复核（全部成立）：未从 tracking number 格式推断 Provider；未从 carrier 文本推断；无 latest fallback（`get_release`/`get_*_revision` 只按精确 ID）；无 PAC fallback（PAC 无任何代码）；无默认账号/产品自动选择。

### 3.4 Active Configuration Release

| 检查项 | 现状 | 状态 |
|---|---|---|
| 存在获批 Active Release | 不存在；默认应用为 `StaticTrackingConfigurationReader(None)` | `BLOCKED_EXTERNAL_INPUT` |
| Release 精确引用 Revision | 模型强制（含逐字段内容比对） | `READY`（代码） |
| 完整审计记录 | **不存在**（无审计模型/存储） | `BLOCKED_BUSINESS_DECISION` |
| 发布审批主体 | **未定义** | `BLOCKED_BUSINESS_DECISION` |
| 激活权限 | **未实现**（catalog 无激活指针） | `NOT_IN_SCOPE`（Batch J/K 之后） |
| Rollback 权限 | **未实现** | `NOT_IN_SCOPE` |
| 回滚演练证据 | 无 | `BLOCKED_EXTERNAL_INPUT` |

### 3.5 Real Provider Validation — 结论矩阵

| 项目 | Australia Post | StarTrack | 证据 | 状态 |
|---|---|---|---|---|
| Provider Revision | 无 | 无 | 仓库无 Revision 内容 | `BLOCKED_EXTERNAL_INPUT` |
| Account Revision | 无 | 无 | 同上 | `BLOCKED_EXTERNAL_INPUT` |
| Product Revision | 无 | 无 | 同上 | `BLOCKED_EXTERNAL_INPUT` |
| Mapping Revision | 无 | 无 | 2 组为合并 carrier 文本 | `BLOCKED_EXTERNAL_INPUT` |
| Active Release | 无 | 无 | 默认 reader 为 None | `BLOCKED_EXTERNAL_INPUT` |
| Credentials | 无 | 无 | 无 `.env`/secret store 绑定 | `BLOCKED_EXTERNAL_INPUT` |
| Account Permission | 未验证 | 未验证 | Get Accounts 未执行 | `BLOCKED_EXTERNAL_INPUT` |
| Testbed Authorization | 无 | 无 | 无授权材料 | `BLOCKED_EXTERNAL_INPUT` |
| Real Validation | 未执行 | 未执行 | 全链路缺失 | `BLOCKED_EXTERNAL_INPUT` |

**Batch I 真实验证的最小闭环条件**（全部满足才可发起一次受控 testbed 调用）：

1. 每个 tracking group 的显式 `provider_revision_id / account_revision_id / product_revision_id / mapping_revision_id`；
2. 一个获批 `release_revision_id`，且 `environment=testbed`；
3. 服务端注入的 API key/secret/account number（`EnvironmentCredentialReader` 绑定）；
4. Get Accounts 回执证明该账号具备 tracking 能力；
5. 明确授权的一次性 testbed 调用许可与速率预算（≤10 次/分钟）；
6. 原始响应样本的可留存方式（脱敏后作为回归证据）。

**缺任一项即必须继续返回 `CARRIER_MAPPING_UNRESOLVED` / `PROVIDER_CONFIGURATION_MISSING`，不得以合成数据替代。**

---

## 4. Audit B（其一）— SKU Packaging Data Readiness

### 4.1 当前 SKU 数据实际包含什么

`skus.json`：9 条商品记录。与重量/尺寸相关的字段（`backend/models/source.py:133-159` 为准）：

| 字段 | 语义 | 是否包装数据 |
|---|---|---|
| `weight_g` | **商品**重量（克） | 否 |
| `dimensions_mm {length,width,height}` | **商品**三维（毫米） | 否 |
| `volume_mm3` | 商品体积（= 三维乘积） | 否 |
| `volumetric_gross_weight_kg` | 来源"体积毛重"，且**不符合**统一 250 kg/m³ 关系（`PHASE6_INTEGRATION_PLAN.md` §2.2） | 否，且语义不明 |
| `max_storage_per_container` | 仓储装箱容量（存储语义） | 否，非运输包装 |

### 4.2 包装规格字段逐项核对

| 包装规格项 | 是否存在 | 说明 |
|---|---|---|
| 单件包装长度/宽度/高度 | **否** | 只有商品三维；按 D-019/契约 §4.4 不得直拷为包装尺寸 |
| 包装后重量 | **否** | 无包装增重数据 |
| 尺寸单位 / 重量单位 | 仅有商品侧 mm / g | 包装侧无数据，无单位声明 |
| 可旋转 / 不可旋转方向 | **否** | 商品数据无 orientation |
| 易碎限制 | **否** | 无字段 |
| 堆叠限制 | **否** | 无字段 |
| 单件包装类型（carton/satchel…） | **否** | 无字段 |
| 特殊运输限制（危险品等） | **否** | 无字段 |

### 4.3 结论

**必须严格区分**：Product Dimensions ≠ Package Dimensions；Product Weight ≠ Package Weight。当前系统只有前者。

- SKU Packaging Specification：`BLOCKED_EXTERNAL_INPUT`
- 不允许把 `weight_g`/`dimensions_mm`/`volume_mm3` 直接当作 Package 尺寸重量（契约 §16.2 已明确禁止）
- `volumetric_gross_weight_kg` 虽形似计费重量输入，但其推导口径无证据，且契约 §6.2 明确禁止直接作为 chargeable weight → `NEEDS_EVIDENCE`

---

## 5. Audit B（其二）— Packaging Materials Readiness

| 所需数据 | 现状 | 缺失 | 状态 |
|---|---|---|---|
| Material ID | 模型字段就绪（`PackageMaterialSpec.material_id`），**无目录** | 材料清单 | `BLOCKED_EXTERNAL_INPUT` |
| Material Revision | 由 ruleset `version`/`source_revision` 承载，无内容 | 版本化材料数据 | `BLOCKED_EXTERNAL_INPUT` |
| Material Dimensions（inner/outer） | 契约已定义双套尺寸 | 实际尺寸 | `BLOCKED_EXTERNAL_INPUT` |
| Internal Capacity | 契约以 `inner_dimensions_mm` 表达容量，无独立 capacity 字段 | 容量策略确认 | `NEEDS_EVIDENCE` |
| Tare Weight | 契约字段 `tare_weight_g`，无值 | 皮重 | `BLOCKED_EXTERNAL_INPUT` |
| Maximum Gross Weight | 契约字段 `max_gross_weight_g`，无值 | 上限 | `BLOCKED_EXTERNAL_INPUT` |
| Material Type | 无显式类型字段（仅 material_id） | 类型/材质分类 | `NEEDS_EVIDENCE` |
| Orientation Constraints | **契约 schema 无字段** | 需契约扩展 | `BLOCKED_BUSINESS_DECISION` |
| Availability（库存/停用） | **契约 schema 无字段** | 需契约扩展 | `BLOCKED_BUSINESS_DECISION` |
| Selection Policy | 契约 `PackingPolicy.material selection strategy`，散文描述 | 需要枚举化 | `BLOCKED_BUSINESS_DECISION` |

**结论**：仓库内**不存在**任何包装材料数据，也不得编造生产材料。任何离线实现只能使用明确标记 `synthetic` 的合成材料，且**不得**被描述为真实可用库存。

---

## 6. Audit B（其三）— Packing Rules Readiness

### 6.1 已冻结的部分（可直接实现）

契约 §5.1 冻结了最小 ruleset 外壳与三类记录（`PackagingRuleSet`、`SkuPackagingSpec`、`PackageMaterialSpec`、`PackingPolicy`），§5.2 冻结确定性要求与优先级（真实数据 > SKU policy > handling-class policy > general policy；同 priority 以稳定 policy ID 排序；禁止"任选第一个可用箱型"），§5.3 冻结缺失即 `PACKAGE_DATA_INCOMPLETE`、版本不可变、UTC 生效时间、同一时刻最多一个 active version。

### 6.2 未冻结的部分（真实契约缺口）

| 编号 | 缺口 | 证据 | 影响 | 分类 |
|---|---|---|---|---|
| C-J1 | `PackingPolicy` 仅散文描述（"match criteria / allocation strategy / material selection strategy / split-mix constraints"），**无字段级 schema 与枚举值** | 契约 §5.1 第 500-507 行 | 实现者必须自行发明策略词汇 → 事实上创造新契约 | `BLOCKED_BUSINESS_DECISION` |
| C-J2 | 方向/易碎/堆叠/危险品约束在 `SkuPackagingSpec` 与 `PackageMaterialSpec` 中**无承载字段** | 契约 §5.1 第 486-499 行 | 若业务需要这些约束，规则无法表达 | `BLOCKED_BUSINESS_DECISION` |
| C-J3 | 未批准任何具体分配算法 | D-020（`docs/DECISIONS.md` 第 174 行）、契约 §5.3 第 522 行 | 无法确定生产级装箱行为 | `BLOCKED_BUSINESS_DECISION` |
| C-J4 | 材料选择策略未枚举（最小可用箱？最省材料？优先级？） | 契约 §5.1 | 选择结果不可审计 | `BLOCKED_BUSINESS_DECISION` |
| C-J5 | `PackageWeight.chargeable_weight_kg` 依赖 Provider 规则 | 契约 §6.2 | 离线可为 `null`，不阻塞 J1 | `BLOCKED_EXTERNAL_INPUT` |
| C-J6 | `actual` package source 读取接口在真实数据获批前**明确未定义** | 契约 §4.4 末条 | 离线只能实现 `rules` 路径 | `NOT_IN_SCOPE`（J2 之后） |

**说明**：C-J1～C-J4 是**业务决策缺口**，本任务不得自行批准。它们不阻塞 J1（领域模型 + 守恒 + provenance + fail-closed + 单一确定性策略的 synthetic 实现），但阻塞"可用于生产的完整装箱算法"。

### 6.3 现有契约是否足以实现确定性装箱算法

**部分足以**：数量守恒、Package ID 唯一性、优先级、稳定排序、版本不可变、provenance、失败分类均已冻结；**不足以**确定"在什么约束下选哪个箱、如何分配数量"的算法本体。因此可实现一个**确定性但策略受限**的 packer（例如"按 SKU 排序的顺序装箱 + 最小可容材料 + 超限即失败"），前提是该策略被标注为 synthetic-only 且不得成为生产默认。

### 6.4 Packaging 输入就绪矩阵（汇总）

| 输入类别 | 所需数据 | 当前来源 | 缺失项 | 状态 |
|---|---|---|---|---|
| SKU Packaging Specs | 单件包装三维/包装后重量/单位 | 仅商品三维与商品重量（`skus.json`） | 全部包装字段 | `BLOCKED_EXTERNAL_INPUT` |
| Package Materials | 材料 ID/内外尺寸/类型 | 无 | 全部 | `BLOCKED_EXTERNAL_INPUT` |
| Capacity/Tare | 内容积、皮重、最大毛重 | 无 | 全部 | `BLOCKED_EXTERNAL_INPUT` |
| Orientation | 允许/禁止旋转、堆叠、易碎 | 无（且 schema 无字段） | 数据 + schema | `BLOCKED_BUSINESS_DECISION` |
| Packing Policy | 匹配条件、分配策略、拆分/混装限制 | 契约仅有散文 | 结构化 schema | `BLOCKED_BUSINESS_DECISION` |
| Deterministic Rules | 稳定排序、策略枚举、材料选择 | 只冻结原则 | 具体算法 | `BLOCKED_BUSINESS_DECISION` |
| Ruleset Revision | ruleset_id/version/effective_from/source_revision | 契约已定义外壳 | 实际 ruleset | `BLOCKED_EXTERNAL_INPUT` |

---

## 7. Audit C — Can Batch J Start Offline?

### 7.1 C1 Contract Readiness（逐项）

| 契约要素 | 是否冻结 | 证据 | 离线可实现 |
|---|---|---|---|
| Package Domain | YES | 契约 §2.3（`Package` 含 package_id/source/items/dimensions/weight/material_id/ruleset/provenance） | YES |
| PackageDimensions / PackageWeight | YES | §2.3（volume 精确等于三维乘积；gross = item + packaging） | YES |
| PackageItem / OrderItemReference | YES | §2.3（`(order_number, zero_based_line_index)` 内部确定性引用） | YES |
| PackageProvenance | YES | §2.3（source_revision/ruleset/input_fingerprint/generated_at） | YES |
| PackageEstimationResult / PackageDiagnostic | YES | §2.3、§4.1 | YES |
| PackagingRuleSet 外壳 | YES | §5.1 | YES |
| SkuPackagingSpec | YES（字段有限） | §5.1（无 orientation/易碎/堆叠字段） | YES（synthetic 值） |
| PackageMaterialSpec | YES | §5.1 | YES（synthetic 值） |
| PackingPolicy 字段级 schema | **NO** | §5.1 散文 | 仅能以自定义封闭枚举实现，需决策确认 |
| 确定性分配算法 | **NO（未批准）** | D-020、§5.3 | 可实现单一策略，但非生产授权 |
| PackageEstimationService 接口 | YES | §4.4（`estimate(order, products, rules)`） | YES |
| 数量守恒不变量 | YES | D-020、§4.1 | YES |
| 错误 / Reason Code | YES | §3.1（`PACKAGE_RULES_NOT_CONFIGURED`、`PACKAGE_DATA_INCOMPLETE`、`QUOTE_UNIT_EMPTY/DUPLICATE`） | YES |
| Provenance | YES | §2.3、§5.3 | YES |
| API 投影 `PackageResponse` | YES | §9.3（不含 diagnostics/policy/chargeable） | YES |
| 测试契约 | YES | §13.1、§13.2 | YES |

### 7.2 C2 Offline Implementation Readiness（合成夹具）

| 可离线实现项 | 判定 | 依据 |
|---|---|---|
| Packaging Rules Reader | YES | §4.4 `get_active(at)` 签名冻结 |
| Immutable Ruleset | YES | D-021、§5.3（版本不可变、生效窗口） |
| SKU Packaging Specification | YES（synthetic） | §5.1 字段确定 |
| Package Material Specification | YES（synthetic） | §5.1 字段确定 |
| Package Domain | YES | §2.3 |
| Package Item Domain | YES | §2.3 |
| Deterministic Packing Algorithm | **PARTIAL** | 可写确定性 packer；策略须标 synthetic-only（C-J1/C-J3） |
| Package Estimation Service | YES | §4.4 |
| Quantity Conservation Validation | YES | D-020、§4.1 |
| Package Provenance | YES | §2.3 |
| OrderService Integration | YES | §2.4（`OrderDetailResult.packages` 已在契约中） |
| API/OpenAPI Integration | YES | §9.3、§9.6 |
| Frontend Package Display | YES | §9.3（纯投影，不重算金额） |
| 完整自动化测试 | YES | §13.1、§13.2、§13.3 |

### 7.3 C3 Synthetic Fixture 合规规则（离线实现的强制条件）

1. 所有合成数据必须显式标记 `synthetic`（建议字段位或 ruleset_id 前缀，如 `synthetic-ruleset-*`）；
2. Synthetic fixture 不得冒充真实客户数据（不得使用真实客户字段）；
3. Synthetic ruleset **不得**被默认激活为生产配置（默认应用必须保持"无 active ruleset → `PACKAGE_RULES_NOT_CONFIGURED`"）；
4. Synthetic 材料不得声称真实可用库存；
5. Synthetic SKU packaging specs **不得**写入四个业务 JSON（D-021 明确禁止）；
6. 测试结果不得描述为"真实包装验证"；
7. 每条 provenance 必须保留 ruleset ID/version 与 `input_fingerprint`；
8. 生产配置与测试 fixture 必须物理/逻辑隔离（独立只读文件或独立 reader 实例，不得共用可变全局）。

**额外建议（不改契约）**：合成 fixture 放入独立的 `tests/fixtures/` 或 `backend/data/packaging/synthetic/`，并在文件名与 ruleset_id 中双重标注 `synthetic`，避免任何人误当成生产 ruleset。

### 7.4 最终回答

| 问题 | 回答 | 说明 |
|---|---|---|
| **Batch J Contract Ready** | **NO（整体）**；**YES（J1 bounded slice）** | 领域/守恒/provenance/API/测试契约已冻结；`PackingPolicy` 字段级 schema、orientation/易碎/堆叠约束、具体算法未批准（C-J1～C-J4） |
| **Batch J Offline Implementation Ready** | **YES（限 J1）** | 14 项中 13 项可完全离线实现，1 项（装箱算法）需限定为 synthetic-only 单一策略 |
| **Batch J Production Data Ready** | **NO** | 无任何 SKU 包装规格、材料目录、capacity/tare、获批 ruleset |

---

## 8. Audit D — Shipping Quote Readiness

### 8.1 Provider / Product 依赖

| 项目 | 状态 | 证据 |
|---|---|---|
| Provider Mapping | `BLOCKED_EXTERNAL_INPUT` | 无内容（同 Audit A） |
| Account Mapping | `BLOCKED_EXTERNAL_INPUT` | 同上 |
| Product Mapping | `BLOCKED_EXTERNAL_INPUT` | 同上 |
| Contract Price | `BLOCKED_EXTERNAL_INPUT` | 需 Get Accounts + 合同；`contract_price_aud` 为占位 |
| Product authorization | `BLOCKED_EXTERNAL_INPUT` | 未执行 Get Accounts |

### 8.2 Shipping Calculation

| 计算要素 | 状态 | 证据/说明 |
|---|---|---|
| Package dimensions | `BLOCKED_EXTERNAL_INPUT` | 依赖 Audit B |
| Actual weight（gross） | `BLOCKED_EXTERNAL_INPUT` | 需包装皮重 |
| Cubic weight | `NEEDS_EVIDENCE` | 250 kg/m³ 仅为行业默认，必须由 Get Accounts/合同确认（计划 §3.6） |
| Chargeable weight | `NEEDS_EVIDENCE` | 不得统一假设 `max(actual, volumetric)`（契约 §6.2） |
| Provider cubing factor | `NEEDS_EVIDENCE` | 同上 |
| GST（total_cost 含 GST） | AP：`NEEDS_EVIDENCE`（官方调研支持，但需该 Product 的合同/文档确认）；ST：`NEEDS_EVIDENCE` | D-022 要求逐 Provider/Product 证据 |
| Total cost incl GST | `BLOCKED_EXTERNAL_INPUT` | 需真实响应 |
| Currency | `READY` | 仅 AUD；非 AUD → `CURRENCY_NOT_SUPPORTED` |
| Raw amount precision | `NEEDS_EVIDENCE` | D-029，需 precision_rule_ref |
| Provider rounding rules | `NEEDS_EVIDENCE` | 同上，禁止用通用 ROUND_HALF_UP 代替 |
| D-004 订单级 ROUND_HALF_UP | `READY` | 契约 §6.3 金额链已冻结，可离线实现 |

### 8.3 Quote Lifecycle

| 项目 | 状态 | 证据 |
|---|---|---|
| Quote Unit（必要单元） | `READY`（契约） | 契约 §7、`QuoteUnitResult` 内部模型 |
| All-or-nothing 聚合 | `READY`（契约） | D-018、§7.1 |
| Capability Preflight | `READY`（契约） | §3.4、§13.3 |
| Unsupported/unavailable 优先级 | `READY`（契约） | §3.4、§3.1 reason 表 |
| Zero fallback | `READY`（契约） | D-017 |
| Quote expiration | `READY`（判定为 null） | 官方无 expiry 字段 → 固定 `null`，不得发明 |
| Checked time vs quoted time | `READY`（契约） | `checked_at` 非报价时间；`quoted_at`/`expires_at` 可为 null |
| 不得 PAC fallback | `READY`（契约+代码） | D-027；代码中无 PAC 任何痕迹 |
| 不得从商品价格推导运费 | `READY`（约束） | D-004/契约 §6.3 |
| 不得从 total_cost 反推 shipping GST | `READY`（约束） | D-022/§6.3 |
| 不得提前舍入 | `READY`（约束） | §6.3 唯一金额链 |

### 8.4 Quote Readiness Matrix（可离线 vs 需真实输入）

| 能力 | 离线可实现 | 需真实 Provider 输入 | 结论 |
|---|---|---|---|
| ShippingQuoteResult 三状态联合（含 quoted_at/expires_at/providers/quote_source/ruleset_*/shipping_gst） | YES | NO | `READY_WITH_SYNTHETIC_FIXTURES` |
| 金额链（raw → validated → exact → 两位 → Pricing → Money） | YES（synthetic provider 值） | NO | `READY_WITH_SYNTHETIC_FIXTURES` |
| All-or-nothing / 空单元 / 重复单元 | YES | NO | `READY_WITH_SYNTHETIC_FIXTURES` |
| Capability Preflight 与 reason 优先级 | YES | NO | `READY_WITH_SYNTHETIC_FIXTURES` |
| QuoteUnitResult 内部诊断与脱敏 | YES | NO | `READY_WITH_SYNTHETIC_FIXTURES` |
| 真实 Contract Price / Get Accounts 权限 | NO | YES | `BLOCKED_EXTERNAL_INPUT` |
| GST 语义证据（逐 Provider/Product） | NO | YES | `NEEDS_EVIDENCE` |
| Cubing factor / chargeable weight | NO | YES | `NEEDS_EVIDENCE` |
| 精度与舍入规则 | NO | YES | `NEEDS_EVIDENCE` |

**关键判断**：Quote 的**机制**（聚合、状态、金额链、失败语义）完全可离线实现并有 synthetic 契约测试；Quote 的**数值**必须等待真实账号与合同证据。二者不可混为一谈。

---

## 9. Audit E — Configuration Governance Readiness

### 9.1 治理操作 vs 现状

| 操作 | 需要的责任 | 现状 | 状态 |
|---|---|---|---|
| 创建 Revision | 创建主体 | 无主体概念（`register_*` 无 actor 参数） | `BLOCKED_BUSINESS_DECISION` |
| 修改 Revision | 必须通过新 Revision | ✅ 已强制（同 ID 不同内容拒绝） | `READY` |
| 配置验证 | 验证主体 | 仅 `validation_status="verified"` 自声明默认值，无验证者身份 | `BLOCKED_BUSINESS_DECISION` |
| Release Approval | 审批主体 | 无审批模型/字段 | `BLOCKED_BUSINESS_DECISION` |
| Release Creation | 发布主体 | 有 `register_release`，无发布者/时间/审批引用 | `BLOCKED_BUSINESS_DECISION` |
| Active Release Switch | 激活权限 | **未实现**（无 active 指针，reader 为静态单 release） | `NOT_IN_SCOPE` |
| Rollback | 回滚权限 | **未实现** | `NOT_IN_SCOPE` |
| Audit Review | 审计主体 | 无审计日志 | `BLOCKED_BUSINESS_DECISION` |

### 9.2 逐项核实

- **角色定义**：不存在。`AGENTS.md` 与契约只描述"必须审批/可审计"，未定义角色主体。
- **审批流程**：不存在（无状态机、无审批记录）。
- **发布前验证**：部分存在——Release 构造时强制 schema/外键/能力/环境/内容一致性（`backend/models/tracking.py:443-528`），但"账号权限 + Get Accounts 证据 + 合同价证据"无法在代码内校验。
- **原子激活机制**：不存在。`TrackingConfigurationCatalog` 只有 `register_*`/`get_*`（`backend/services/tracking_configuration.py:56-96`），无 `activate`/`set_active`。
- **回滚审批**：不存在。
- **保留旧 Release**：✅ append-only 保证历史 Release 不被删除（内存内）。
- **固定在途请求版本**：✅ 语义成立（每请求捕获单个 release 对象），但因无激活切换能力而无法真实验证。
- **配置变更审计**：不存在（无 actor/UTC 时间/原因/审批引用记录）。

### 9.3 结论

现有 `TrackingConfigurationCatalog` 是**正确但最小**的 append-only Revision 存储，仅保证"同一 ID 内容不可变"这一条不变量。它**不是**企业级配置管理后台，也**不得**被描述为已具备配置治理能力。

- 治理**业务决策**（谁审批、谁激活、谁回滚）：`BLOCKED_BUSINESS_DECISION`
- 治理**工程实现**（激活指针、rollback、审计日志、actor 记录）：`NOT_IN_SCOPE`（Batch I 未要求，属后续配置治理批次）
- 持久化：`NOT_IN_SCOPE`（D-026/基础架构约束禁止数据库、Redis）

---

## 10. Audit F — Runtime and Operations Readiness

### 10.1 现状分类

| 项目 | 已有代码能力 | 已冻结契约 | 需要真实业务参数 | 需要运维决策 |
|---|---|---|---|---|
| HTTP connect/read timeout | ✅ 强制有限值、无默认 | ✅ 必须显式 | — | **✅ 具体值** |
| Concurrency | ❌ 未实现（同步调用、无并发池） | ✅ "有界并发"要求 | — | **✅ 并发上限** |
| Rate limiting | ✅ `InMemoryTrackingRateLimiter` 10/60s，**单进程** | ✅ 10 req/min | — | **✅ 多进程策略** |
| Retry policy | ✅ 无自动重试（更安全） | ✅ GET 有限重试可选、POST 默认不重放 | — | **✅ 是否启用** |
| Response size limit | ✅ `max_response_bytes`（默认 1,000,000，上限 10,000,000） | ✅ 必须有上限 | — | **✅ 具体值** |
| Circuit breaker | ❌ 未实现 | ❌ **未冻结** | — | ⚠️ 未冻结即**不得擅自引入** |
| Secret management | ✅ `SecretStr`、`repr=False`、env-only resolver | ✅ 仅服务端 | — | **✅ secret store 选型** |
| Credential rotation | ❌ 无机制 | ❌ 未冻结流程 | — | **✅ 轮换流程** |
| Provider availability monitoring | ❌ 无 | ❌ 未冻结 | — | **✅ 监控方案** |
| Error observability | ❌ 无 logging/telemetry（刻意） | ✅ 安全日志字段清单 | — | **✅ 观测落地方式** |
| Safe logging | ✅ 全局无 logging/print；诊断 `repr=False` | ✅ 禁止凭证/tracking number/PII | — | — |
| Environment separation | ✅ `ProviderEnvironment` 枚举 + 一致性校验 | ✅ testbed≠production | — | **✅ 环境清单与访问控制** |
| Deployment configuration | ❌ 无（无 `.env.example`、无容器/进程管理说明） | — | — | **✅ 部署形态** |
| Rollback procedure | ❌ 无（应用配置回滚与 Release rollback 均缺） | ✅ Release rollback 要求 | — | **✅ 操作手册** |

### 10.2 关键运维发现

| 编号 | 发现 | 影响 | 建议 |
|---|---|---|---|
| F-1 | `InMemoryTrackingRateLimiter` 为单进程内存实现（`backend/integrations/tracking.py:75-115`）。多 worker 部署时全局 10 req/min 不再成立 | 可能触发官方 429 甚至账号风控 | 生产部署**显式固定单 worker**，或经新决策引入受控共享计数（会触碰"禁止 Redis"约束，需独立批准） |
| F-2 | 无任何日志/遥测（刻意满足安全要求），因此生产故障不可观测 | 真实激活后难以排障 | 需在批准的安全日志字段清单内引入，不得记录凭证/tracking number/PII |
| F-3 | 无 `.env.example`、无部署/启动说明（`README_PHASE0.md` 仅 dev 命令） | 运维无法按文档部署 | 由所有者决定补文档；本任务不创建 |
| F-4 | timeout 无默认值属**正确设计**（避免静默生产参数），但意味着未配置即无法构造 `ProviderConfiguration` | 激活必须显式配置 | 保持现状，登记为运维输入 |
| F-5 | Circuit breaker 未被任何决策冻结 | 擅自实现会扩大契约 | **不得引入**；如需，走新决策 |

---

## 11. READY / BLOCKED Matrix（汇总）

### 11.1 可立即进行（READY / READY_WITH_SYNTHETIC_FIXTURES）

| 项 | 状态 |
|---|---|
| Package Domain（含 PackageItem/Provenance/EstimationResult/Diagnostic） | `READY` |
| 数量守恒校验 | `READY` |
| PackageEstimationService 接口与 fail-closed 语义 | `READY` |
| PackagingRuleSet 外壳与不可变版本规则 | `READY` |
| Package API 投影（`PackageResponse`）与前端展示契约 | `READY` |
| Package 失败 reason（`PACKAGE_RULES_NOT_CONFIGURED`/`PACKAGE_DATA_INCOMPLETE`） | `READY` |
| Synthetic fixtures 的 ruleset/SKU spec/material | `READY_WITH_SYNTHETIC_FIXTURES` |
| ShippingQuoteResult 联合结构 + 金额链 + all-or-nothing + preflight | `READY_WITH_SYNTHETIC_FIXTURES` |
| QuoteUnitResult 内部诊断与脱敏 | `READY_WITH_SYNTHETIC_FIXTURES` |
| 单一确定性装箱策略（synthetic-only） | `READY_WITH_SYNTHETIC_FIXTURES` |

### 11.2 必须等待（BLOCKED / NEEDS_EVIDENCE）

| 项 | 状态 |
|---|---|
| SKU 包装规格 | `BLOCKED_EXTERNAL_INPUT` |
| 包装材料目录（含皮重/容量/最大毛重） | `BLOCKED_EXTERNAL_INPUT` |
| 生产获批 ruleset（id/version/生效期） | `BLOCKED_EXTERNAL_INPUT` |
| AP/ST Provider/Account/Product/Mapping Revision | `BLOCKED_EXTERNAL_INPUT` |
| 获批 Active Configuration Release | `BLOCKED_EXTERNAL_INPUT` |
| 服务端凭证与账号权限、Get Accounts 回执 | `BLOCKED_EXTERNAL_INPUT` |
| testbed 访问与调用授权 | `BLOCKED_EXTERNAL_INPUT` |
| 各 group 的显式 Provider 归属 | `BLOCKED_EXTERNAL_INPUT` |
| `PackingPolicy` 字段级 schema | `BLOCKED_BUSINESS_DECISION` |
| 方向/易碎/堆叠/危险品约束承载字段 | `BLOCKED_BUSINESS_DECISION` |
| 生产级分配算法批准 | `BLOCKED_BUSINESS_DECISION` |
| 材料选择策略 | `BLOCKED_BUSINESS_DECISION` |
| 配置治理角色/审批/激活/回滚主体 | `BLOCKED_BUSINESS_DECISION` |
| Contract Price 证据 | `BLOCKED_EXTERNAL_INPUT` |
| GST 语义（逐 Provider/Product） | `NEEDS_EVIDENCE` |
| Cubing factor / chargeable weight | `NEEDS_EVIDENCE` |
| 金额精度与舍入规则 | `NEEDS_EVIDENCE` |
| StarTrack 账号"不以 0 开头"规则 | `NEEDS_EVIDENCE` |
| AP 账号左补零归一化归属 | `NEEDS_EVIDENCE` |
| Provider raw tracking status 映射证据 | `NEEDS_EVIDENCE` |

### 11.3 不在范围

| 项 | 状态 |
|---|---|
| PAC / 跨请求缓存 / 报价历史 | `NOT_IN_SCOPE`（D-026/D-027） |
| TNT 真实适配器 | `NOT_IN_SCOPE`（D-006 Bonus） |
| `actual` 真实装箱数据读取接口 | `NOT_IN_SCOPE`（真实数据获批后才定义） |
| 数据库 / Redis / 消息队列 | `NOT_IN_SCOPE`（基础架构约束） |
| Circuit breaker | `NOT_IN_SCOPE`（未冻结，禁止擅自引入） |

---

## 12. Missing Input Register

| ID | 缺失输入 | 类别 | 阻塞对象 | 提供方 |
|---|---|---|---|---|
| MI-01 | 9 个 SKU 的单件包装三维与包装后重量 | 数据 | Batch J 完整实现 + Quote | 业务/仓储 |
| MI-02 | 包装材料目录（ID、内外尺寸、皮重、最大毛重、类型） | 数据 | Batch J 完整实现 | 业务/仓储 |
| MI-03 | 获批 Packaging Ruleset（ID/version/生效期/策略） | 数据+决策 | Batch J 生产启用 | 业务 + 配置治理 |
| MI-04 | 方向/易碎/堆叠/危险品约束的数据与 schema 位置 | 决策 | Batch J 完整实现 | 业务 |
| MI-05 | `PackingPolicy` 字段级 schema 与策略枚举 | 决策 | Batch J 完整实现 | 业务 + 架构 |
| MI-06 | 生产级装箱算法批准 | 决策 | Batch J 生产启用 | 业务 |
| MI-07 | 每个 tracking group 的 Provider 归属 | 数据 | Batch I 真实验证、Quote | 业务/数据所有者 |
| MI-08 | AP/ST Provider/Account/Product/Mapping Revision 内容 | 数据 | Batch I 真实验证、Quote | 账号所有者 |
| MI-09 | 获批 Active Configuration Release | 治理 | Batch I 真实验证、Quote | 配置审批人 |
| MI-10 | 服务端凭证（API key/secret/account）与 secret store | 安全 | 一切真实调用 | 账号所有者 + 运维 |
| MI-11 | Get Accounts 回执（账号权限/产品） | 证据 | 真实调用前置 | Australia Post / StarTrack |
| MI-12 | testbed 访问与调用授权 | 授权 | 真实验证 | 用户 + 承运商 |
| MI-13 | GST 语义证据（逐 Provider/Product） | 证据 | Quote 生产启用 | 承运商/合同 |
| MI-14 | Cubing factor 与 chargeable weight 规则 | 证据 | Quote 计算 | 承运商/合同 |
| MI-15 | 金额精度与舍入规则 | 证据 | Quote 金额验证 | 承运商/合同 |
| MI-16 | 配置治理角色与审批流程 | 决策 | 生产配置启用 | 业务/管理层 |
| MI-17 | 激活/rollback 权限与操作手册 | 决策 | Release 生命周期 | 运维/管理层 |
| MI-18 | runtime timeout/并发/限流/重试具体值 | 运维 | 生产部署 | 运维 |
| MI-19 | 部署形态与多进程限流策略 | 运维 | 生产部署 | 运维 |
| MI-20 | 监控与安全日志落地方式 | 运维 | 生产运行 | 运维 |
| MI-21 | Provider raw status → normalized 映射证据 | 证据 | 状态准确性 | 承运商文档/真实响应 |

---

## 13. Required Business Owners

| 决策/输入 | 建议责任角色 | 说明 |
|---|---|---|
| MI-01 / MI-02（包装规格与材料） | 仓储/运营负责人 + 商品主数据所有者 | 不得由工程推断 |
| MI-03 / MI-05 / MI-06（ruleset 与算法） | 业务负责人（物流）+ 架构负责人 | 需形成正式决策 |
| MI-04（方向/易碎/堆叠/危险品） | 业务负责人（合规/安全） | 涉及运输合规 |
| MI-07（group → Provider 归属） | 订单/物流业务所有者 | 合并 carrier 文本的语义澄清 |
| MI-08 / MI-09（Revision 与 Release） | 配置管理员 + 审批人 | 需职责分离（创建者 ≠ 审批者） |
| MI-10 / MI-12（凭证与 testbed 授权） | 账号所有者 + 用户（授权方） | 工程不得自行获取 |
| MI-11 / MI-13 / MI-14 / MI-15 | 承运商合同/商务负责人 | 需官方或合同书面证据 |
| MI-16 / MI-17（治理角色与激活权限） | 管理层 + 运维负责人 | 企业级治理前提 |
| MI-18 / MI-19 / MI-20（运行参数与运维） | 运维/SRE | 不得由工程写死生产默认值 |

---

## 14. Evidence References

### 14.1 冻结决策

- `docs/DECISIONS.md`：D-016（Tracking Group ≠ Package）、D-017（zero fallback）、D-018（all-or-nothing）、D-019（rules 数据源）、D-020（拆分/混装 + 守恒）、D-021（独立只读版本化 rules）、D-022（含 GST total_cost）、D-023（显式 mapping）、D-024（reason code）、D-025（仅详情报价）、D-026（无 history/cache）、D-027（Contract Price only，无 PAC）、D-028（normalized/raw/unknown）、D-029（精度证据）、D-030（列表金额）、D-031（provider-null 投影）
- 未决问题原文（包装/材料/计费重量/精度证据）：`docs/DECISIONS.md` 第 322-326 行

### 14.2 契约

- `docs/PHASE6_CONTRACT.md`：§2.2（Quote 模型，第 83 行起）、§2.3（Package 模型，181-259）、§2.4（Order 结果，261-301）、§3.1（reason codes，305）、§3.4（Preflight）、§4（Package Contract，431-467）、§5（Packaging Rules，469-524）、§6（Weight & Pricing，526-577）、§7（Quote Aggregation，579-609）、§8.4（配置与治理，714-867）、§9.3（PackageResponse，927-938）、§13（测试契约，1021-1072）、§15.2（实施前置，1106-1116）、§16.2（禁止项，1130-1139）

### 14.3 规划与调研

- `docs/PHASE6_INTEGRATION_PLAN.md`：§2.2（重量/尺寸数据审计，46-57）、§3.1（官方资料清单，96-109）、§3.2（认证与账号格式，111-119）、§3.4（Get Shipment Price 契约与 GST，134-151）、§3.6（cubic factor 证据，166-172）、§4.3（ShippingQuoteResult 冻结结构，247-296）、§6.3（发布与 rollback 治理，407-415）、§12.2（实施前置输入，639-650）

### 14.4 代码（只读核对）

- `backend/models/source.py:127-159`：Product 字段集合（商品重量/尺寸/体积/体积毛重）
- `backend/models/tracking.py:243-289`：ProviderConfiguration / ProviderCredentials（含账号格式规则）
- `backend/models/tracking.py:305-365`：Provider/Account/Product Revision
- `backend/models/tracking.py:420-528`：TrackingConfigurationRelease 校验
- `backend/services/tracking_configuration.py:56-110`：append-only Catalog 的 register/get 面
- `backend/integrations/tracking.py:75-115`：单进程限流器
- `backend/integrations/tracking.py:141-211`：有界 HTTP transport（HTTPS/timeout/大小/重定向）
- `backend/integrations/credentials.py:29-62`：环境变量凭证解析（未接线）
- `backend/main.py:40-70`：默认应用注入无 Release 的 Tracking Service
- `backend/api/schemas.py`：现有 API schema（无 `packages`、无 Quote 联合结构）
- `frontend/src/components/TrackingPanel.tsx`：现有 Tracking UI（无 Package UI）

### 14.5 数据（仅结构，未输出真实值）

- `backend/data/skus.json`：9 条商品；字段集合确认**无**任何 packing/material/tare/orientation 字段
- `backend/data/tracking.json`：3 个 group；carrier 文本为 `StarTrack / Australia Post`（2 组）与 `TNT`（1 组）
- 四份业务 JSON SHA-256 在审计前后一致

---

## 15. Recommended Implementation Sequence

### 15.1 立即可做（不依赖任何外部输入）

| 序号 | 工作 | 前置 | 产出 |
|---|---|---|---|
| J1-1 | Package/PackageItem/PackageDimensions/PackageWeight/PackageProvenance/PackageEstimationResult/PackageDiagnostic 不可变 Domain 模型 + 不变量 | 契约 §2.3 | Domain + 测试 |
| J1-2 | `PackagingRuleSet` 外壳、版本不可变、生效窗口、`PackagingRulesReader` 接口 + synthetic 只读实现 | 契约 §4.4/§5 | Reader + 测试 |
| J1-3 | Synthetic `SkuPackagingSpec`/`PackageMaterialSpec` fixtures（显式 `synthetic` 标记、不入业务 JSON） | D-021 | 测试夹具 |
| J1-4 | 数量守恒与 Package ID 唯一性校验、fail-closed 路径（`PACKAGE_RULES_NOT_CONFIGURED`/`PACKAGE_DATA_INCOMPLETE`） | D-020 | Service + 测试 |
| J1-5 | 单一确定性装箱策略（synthetic-only，稳定排序 + 明确文档化算法），不激活为生产默认 | 本审计 C-J1/C-J3 | Service + 测试 |
| J1-6 | `PackageEstimationService` + `OrderService` 详情集成（`OrderDetailResult.packages`） | J1-1～J1-5 | 编排 + 测试 |
| J1-7 | API `PackageResponse` 投影 + OpenAPI + 前端 Package 展示（只读、不重算金额） | 契约 §9.3 | API/前端 + 测试 |
| J1-8 | 全套离线回归（Backend/Frontend/OpenAPI 一致性/安全扫描） | J1-1～J1-7 | 门禁通过 |

### 15.2 必须先获得批准的契约增量（阻塞 J2）

| 序号 | 事项 | 类型 |
|---|---|---|
| DEC-1 | `PackingPolicy` 字段级 schema（match criteria / allocation strategy / material selection / split-mix） | 业务+架构决策 |
| DEC-2 | 方向 / 易碎 / 堆叠 / 危险品约束的字段位置与语义 | 业务决策 |
| DEC-3 | 生产级分配算法批准（策略集合） | 业务决策 |
| DEC-4 | 材料选择策略（最小可容 / 最省材料 / 优先级） | 业务决策 |

### 15.3 必须等待外部输入（J2/J3）

1. MI-01/MI-02/MI-03 → 真实 ruleset 与规格；
2. MI-07～MI-12 → Provider 配置、凭证、testbed 授权 → Batch I 真实验证；
3. MI-13～MI-15 → Quote 数值证据；
4. MI-16/MI-17 → 配置治理；
5. MI-18～MI-20 → 生产运维参数。

**不要**把 J1 的完成描述为"Packaging 已实现"，也**不要**把 synthetic fixtures 描述为真实包装验证。

---

## 16. Task 044 Final Status

- 审计类型：Audit & Planning（无功能实现、无依赖、无业务 JSON、无配置）
- 修改范围：仅新增本文档 + 更新 `docs/PROJECT_PLAN.md`（Task 044 记录）
- 未修改：`docs/DECISIONS.md`、`docs/PHASE6_CONTRACT.md`、任何冻结业务规则、Backend/Frontend 实现、API/OpenAPI、业务 JSON、依赖与锁文件

| 判定 | 结果 |
|---|---|
| Batch I 真实 Provider 验证 | `BLOCKED_EXTERNAL_INPUT`（未完成） |
| Batch J Contract Ready（整体） | `NO`（C-J1～C-J4 决策缺口） |
| Batch J Contract Ready（J1 限定范围） | `YES` |
| Batch J Offline Implementation Ready | `YES`（限 J1 + synthetic fixtures） |
| Batch J Production Data Ready | `NO` |
| Batch K Readiness | `BLOCKED`（依赖 J1/J2 完成 + MI-12 testbed 授权 + MI-18～MI-20 运维参数） |

`TASK_044_FINAL_STATUS: AUDIT_COMPLETE_WITH_BATCH_J_SPLIT`

- Phase 6：`IN_PROGRESS`（未变更）
- Batch I：离线实现状态不变（已 Checkpoint `6ccdc5f`），真实验证仍 `BLOCKED`
- Batch J/K：未开始；本审计**不**授权自动开始任何批次
- 新增业务决策需求：**存在**（DEC-1～DEC-4；另 MI-16/MI-17 治理决策）
- 推荐下一实施入口：经用户明确授权后执行 **Batch J1**（Package 领域 + synthetic ruleset + 守恒 + provenance + API/前端投影），与真实包装数据并行推进 DEC-1～DEC-4 的澄清

---

## 17. Task 047 追记（2026-11-08）

本节只追加**后续状态**，不修改上文任何历史结论。Batch J1 已由 Task 045 实现、Task 046 独立复审通过并创建 Checkpoint `3c3675e`；Task 047 已完成 Batch J2 决策准备（`docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md`）。

| 本审计登记项 | Task 047 处理结果 |
|---|---|
| §15.2 DEC-1～DEC-4 | 已给出候选比较、唯一推荐方案与待批准内容；仍为 `PROPOSED`，未被批准 |
| §6.2 C-J1～C-J4 | 分别由 DEC-1（policy schema）、DEC-2（约束承载）、DEC-3（算法）、DEC-4（材料选择）覆盖并提出推荐 |
| §9.3 治理缺口 / MI-16、MI-17 | 新增 **DEC-5**（Packaging 配置治理：复用语义、独立实现、5 角色职责分离、原子激活/rollback/审计、不引入数据库/Redis）；仍为 `PROPOSED` |
| §10.2 F-1 单进程限流 | 新增 **DEC-6**（短期显式单进程部署约束 + 启动断言 + 禁止多 worker/多实例；不引入 Redis/新基础设施）；仍为 `PROPOSED` |
| §4/§5/§6 包装与材料数据缺口 | 复核结论不变：9/9 SKU 仅有商品物理数据，包装数据 0/9，材料目录 0，获批 ruleset 0；已补充 DM-01～DM-20 与数据模板、验收标准 |
| §11/§12 READY-BLOCKED 与缺失输入登记 | 未变；DEC-5/DEC-6 使「J2 生产启用」的决策前置从 4 项扩展到 6 项 |
| §16 Batch I 真实 Provider 验证 | 未变，仍 `BLOCKED_EXTERNAL_INPUT`；Task 047 零真实请求 |

**因此**：本审计 §15.2 的「阻塞 J2 的契约增量」应理解为 DEC-1～DEC-6（原四项 + 配置治理 + 多进程限流）。本追记不改变任何既有判定，也不授权开始 Batch J2/K。

### 17.1 Task 048 追记（2026-11-08，最小更新）

- **DEC-1～DEC-4 已获用户批准**，并由 Task 048 正式化为 **D-032～D-035**（`APPROVED / FROZEN`，契约见 `docs/PHASE6_CONTRACT.md` §5.4～§5.8）。本审计 §6.2 的 C-J1～C-J4 因此**已关闭**；§15.2 原「阻塞 J2 的四项决策」不再是阻塞项。
- **DEC-5 / DEC-6 明确 `DEFERRED / NOT_APPROVED`**：本审计 §9（配置治理）与 §10.2 F-1（多进程限流）的结论**继续有效**——`TrackingConfigurationCatalog` 仍不是企业级配置治理，`InMemoryTrackingRateLimiter` 仍只在单进程成立，多 worker/多实例部署与真实 Provider 激活仍被禁止。
- **Batch J2 状态**：`BATCH_J2_CONTRACT: COMPLETE`；`BATCH_J2_IMPLEMENTATION: NOT_STARTED`（下一入口 Task 049）。J2-B～J2-E、J2-H 可在 synthetic fixtures 下实施；**J2-F 不在当前授权范围**；**J2-G 仍 `BLOCKED`**。
- **真实数据缺口不变**：§4/§5/§6 的结论与 §12 的 MI-01～MI-21 全部继续有效；9/9 SKU 仍只有商品物理数据，包装规格 0/9、材料目录 0、获批 ruleset 0。D-032～D-035 冻结的是**规则语义**，不是数据。
- **Batch I 真实 Provider 验证**仍为 `BLOCKED_EXTERNAL_INPUT`；Task 048 零真实请求，未修改代码、API、OpenAPI、业务 JSON 或依赖。
