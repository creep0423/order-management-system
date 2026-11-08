# Phase 6 Batch J2 决策准备包（Task 047）

## 0. 文档状态与执行边界

| 项目 | 内容 |
|---|---|
| 文档编号 | Task 047 |
| 文档类型 | Decision Preparation / Planning（**无功能实现**） |
| 冻结基线 | Batch J1 Git Checkpoint `3c3675e4cb2deb47bba81346f4d1bc0c6ae290db` |
| 执行时 HEAD | `537e165d59eee484149dccbe562020d774396dc1`（仅在其后追加 Task 046 文档记录） |
| 关联文档 | `AGENTS.md`、`docs/DECISIONS.md`（D-001～D-031）、`docs/PHASE6_CONTRACT.md`、`docs/PHASE6_INTEGRATION_PLAN.md`、`docs/PHASE6_EXTERNAL_READINESS_AUDIT.md`、`docs/ARCHITECTURE.md`、`docs/PROJECT_PLAN.md` |
| 最终状态 | `DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL` |

### 0.1 本任务做了什么

1. 以 Batch J1 Checkpoint 为冻结基线，核实实际 HEAD、Branch 与工作区状态。
2. 对 DEC-1～DEC-4（Task 044 登记的包装业务决策缺口）给出候选方案比较、唯一推荐方案与待批准内容。
3. 对 DEC-5（Packaging 配置治理）与 DEC-6（多进程全局限流）给出候选方案比较、唯一推荐方案与待批准内容。
4. 逐项核查 9 个真实 SKU 的数据就绪性，区分商品物理数据、单件包装数据、包装材料数据、业务规则与尚未取得的真实数据，并给出缺失清单、数据模板与验收标准。
5. 给出生产级装箱算法选型与 Batch J2 完整实施计划。

### 0.2 本任务没有做什么（明确禁止项）

- 未开始 Batch J2 代码实现，未开始 Batch K。
- 未修改 Batch I / J1 已冻结的 Backend、Frontend、API/OpenAPI、测试实现。
- 未修改 `docs/DECISIONS.md`、`docs/PHASE6_CONTRACT.md`、四个业务 JSON、依赖与锁文件。
- 未新增正式 D 编号（D 编号范围仍为 D-001～D-031），未批准 DEC-1～DEC-6。
- 未调用任何真实 Provider，未创建 Commit / Git Checkpoint，未 Push，未修改 Remote。
- 未执行 `reset`、`clean`、`checkout`、`stash`，未覆盖任何未提交工作。
- 未运行全量测试或构建（本任务按任务说明不需要）。

### 0.3 编号约定

- **DEC-1～DEC-4** 是 Task 044 审计登记的待批准业务决策需求编号（见 `docs/PHASE6_EXTERNAL_READINESS_AUDIT.md` §15.2），不是正式 D 决策。
- **DEC-5、DEC-6** 是本任务新增的**任务级提案编号**，用于把「配置治理」与「多进程全限流」两项治理缺口显式化，同样不是正式 D 决策。
- DEC-1～DEC-6 在 Task 047 中全部为 `PROPOSED — AWAITING_USER_APPROVAL`。**Task 047 没有批准任何一项**，也不构成对 `docs/PHASE6_CONTRACT.md` 的修改授权。
- **Task 048 更新（批准结果）**：用户已批准 DEC-1～DEC-4，并分别形成正式决策 D-032（PackingPolicy schema）、D-033（约束归属与合并规则）、D-034（生产级装箱算法）、D-035（材料选择策略）；DEC-5、DEC-6 为 `DEFERRED / NOT_APPROVED`。批准范围、契约落地位置与最终状态见 §17。

---

## 1. 基线与执行前核实

### 1.1 Git 核实结果（执行前）

| 项 | 实际值 |
|---|---|
| `git rev-parse HEAD` | `537e165d59eee484149dccbe562020d774396dc1` |
| Branch | `main` |
| `git status --porcelain` | 空（工作区与暂存区干净） |
| `git remote -v` | 空（未配置 Remote） |
| `git stash list` / `git tag` | 均为空 |
| 基线是否为祖先 | 是（`git merge-base --is-ancestor 3c3675e HEAD` 返回 0） |
| `3c3675e..HEAD` 差异 | 仅 `docs/PROJECT_PLAN.md`，+31 / −3（Task 046 复审与 Checkpoint 记录） |

**结论**：`HEAD` 比冻结基线多一个**纯文档提交**，实现代码与基线完全一致。因此本任务的实现基线等价于 `3c3675e`，无需任何回退动作。

### 1.2 业务 JSON 完整性（执行前）

| 文件 | SHA-256 |
|---|---|
| `backend/data/orders.json` | `8305fba3856a14a2e9e7ff4798f2e2da14278423bc63293608ef7f56a558ddeb` |
| `backend/data/skus.json` | `fa71b78879b6cfeea98460487ad048f44e0458dba9b06391066382fb15f0f942` |
| `backend/data/skus_raw.json` | `44b0db54c736891e23478f9bf412984d9e5006d9d0a1d286671b7128134ac3c5` |
| `backend/data/tracking.json` | `4d79e67c730f3c5dbfbd1ec66dd9e29e5b394fec0467634af55631ff4859c316` |

以上与 Task 043、Task 046 记录的值逐字一致；执行后复核结果见 §16。

### 1.3 已冻结实现的实际形态（本决策包的事实依据）

本任务只读取，不改动。关键事实：

| 能力 | 现状 | 证据位置 |
|---|---|---|
| Package Domain | 不可变、`extra="forbid"`、Decimal-only，尺寸 `_mm`/`_mm3`、重量 `_g` | `backend/models/package.py` |
| PackingPolicy | 仅 7 个字段的 synthetic-only 最小形态，无 match criteria、无 orientation/fragile/stacking/hazmat | `backend/models/packaging_rules.py:102-116` |
| PackagingRuleSet | ID + version + UTC 生效窗口 + 三类记录 + 交叉引用校验 | `backend/models/packaging_rules.py:119-194` |
| 估算算法 | 顺序 first-fit（packed unit 体积 + 毛重），`SMALLEST_VOLUME_FIT` 材料选择 | `backend/services/package_estimation.py:245-333` |
| 合成隔离 | `synthetic_only: Literal[True]` + Service 纵深拒绝 | `backend/models/packaging_rules.py:112,127`；`package_estimation.py:154-200` |
| 默认运行时 | `StaticPackagingRuleSetReader(None)` → 所有详情 `PACKAGE_RULES_NOT_CONFIGURED` | `backend/main.py:58-69` |
| 公共 reason code | 仅 `PACKAGE_RULES_NOT_CONFIGURED`、`PACKAGE_DATA_INCOMPLETE` | `backend/models/package.py:59-68` |
| 配置治理 | append-only Catalog，同 ID 同内容幂等/不同内容拒绝；**无 active 指针、无 activate、无 rollback、无审批、无 actor、无审计日志** | `backend/services/tracking_configuration.py` |
| 限流 | `InMemoryTrackingRateLimiter`，进程内 `deque` + `threading.Lock`，按 `(provider_revision_id, account_revision_id)` 共享 | `backend/integrations/tracking.py:75-115` |

---

## 2. Task 047 总体结论

### 2.1 结论摘要

1. **六项决策全部具备可实现、可测试、可审计的推荐方案**。Task 047 提交时全部为 `PROPOSED`；**Task 048 已批准 DEC-1～DEC-4 并形成 D-032～D-035，DEC-5/DEC-6 保持暂缓**（§17）。推荐方案均在 D-001～D-031 与冻结契约的既有不变量之内，不推翻任何已批准语义。
2. **真实包装数据完全不可用**：9 个 SKU 有**商品**物理数据（重量/三维/体积/体积毛重/仓储容量）9/9；**包装**数据 0/9；包装材料目录 0 条；获批 ruleset 0 份。`Product Dimensions ≠ Package Dimensions`、`Product Weight ≠ Package Weight` 的边界必须在 J2 继续强制。
3. **Batch J2 可以拆成「可离线做」与「必须等真实输入」两段**：J2-A～J2-F 与 J2-H（契约固化、规则 schema、生产算法、材料选择、配置治理、OrderService/API/前端/运行时校验，以及回归/性能/安全门禁）在 DEC 获批后可用 synthetic fixtures 完成**行为**实现；J2-G（真实数据接入与生产启用验证）在 DM-01/DM-02/DM-16 到位前 `BLOCKED`。
4. **生产级装箱算法推荐「分阶段确定性启发式 + Best-Fit Decreasing 放置」**，明确不等同于最优 3D Bin Packing，也不等同于 J1 的 synthetic 顺序 first-fit。
5. **DEC-6 推荐「显式单进程部署约束」**，J2 不引入任何新基础设施；多进程/多实例下真实 Provider 激活必须保持禁止。
6. **DEC-5 推荐复用既有 Revision/Release 治理语义内核、独立实现 Packaging 治理**，并以职责分离的最小企业方案落地；存储仍不得引入数据库/Redis。
7. **Batch I 外部阻塞状态完全未变**：真实 Provider/账号/凭证/Mapping/Release/testbed 仍 `BLOCKED`，本任务未发起任何真实请求。

### 2.2 DEC-1～DEC-6 决策推荐矩阵

| 决策 | 主题 | 推荐方案（唯一） | 主要备选 | 关键风险（未批准就实施） | 批准后解锁 | 状态 |
|---|---|---|---|---|---|---|
| DEC-1 | `PackingPolicy` 字段级 schema | **结构化封闭 schema**：`scope`（sku / handling_class / general）+ 显式 match 字段 + 封闭 `allocation_strategy`/`material_selection` 枚举 + 拆分/混装/上限字段；无匹配即 fail closed，不设隐式默认策略 | (a) 维持散文由实现者自定；(b) 单一全局 policy 无匹配条件；(d) 外部规则 DSL/表达式引擎 | 实现者事实上发明新契约；策略词汇不可审计；不同人写出不同行为 | J2-B、J2-C、J2-D、J2-E、生产 ruleset 发布 | `APPROVED` → D-032 |
| DEC-2 | 包装约束模型（Orientation / Fragile / Stackability / Hazardous / Weight / Dimension / Material Compatibility） | **三处归属 + 派生视图**：SKU 侧 `handling` 事实、材料侧能力上限、policy 侧收紧规则；运行时派生 `EffectiveConstraintView`，不新增第四类持久实体 | (a) 全塞 `SkuPackagingSpec` 平铺字段；(b) 全塞 `PackingPolicy`；(d) 独立顶层 `ConstraintSet` 实体 + 引用 | 约束无承载字段 → 危险品/易碎/方向无法表达；或约束可被 policy 悄然放宽；或出现多重事实来源 | J2-B、J2-C、J2-E | `APPROVED` → D-033 |
| DEC-3 | 生产级装箱算法 | **分阶段确定性启发式 + Best-Fit Decreasing 放置**（Stage 0～6，显式排序键、有界搜索、无回溯、无随机、全失败即 fail closed） | FFD；Best-Fit；完整 3D Bin Packing/EP 精确解；MIP/CP-SAT 约束求解 | 算法未批准则生产行为不可定义；若擅自使用求解器则引入未批准依赖 | J2-C、J2-E、J2-G 生产算法门禁 | `APPROVED` → D-034 |
| DEC-4 | 包装材料选择 | **硬过滤 + 策略声明排序键**：兼容性→容量（含方向）→毛重→尺寸上限→危险品/易碎能力→可用性，再按 policy 声明的排序键确定性取第一；`priority_order` 与 `smallest_inner_volume` 两种封闭策略；**禁止任何 fallback** | (a) 最小可容箱优先（无优先级层）；(b) 最省材料（成本最小化）；(c) 固定优先级列表唯一 | 静默 fallback 或「最接近尺寸」猜测会产出不可审计的包装与报价 | J2-C、J2-D | `APPROVED` → D-035 |
| DEC-5 | Packaging 配置治理 | **复用治理语义内核、独立实现**：不可变 Revision + 唯一 Active Release + 原子激活 + rollback 即重新激活 + 请求级 pinning + append-only 审计；职责分离（Author / Validator / Approver / Activator / Auditor）；只读版本化文件 + 显式 active 指针，**不引入数据库/Redis** | (a) 直接复用 Tracking 的 Catalog/Release 实现与存储；(b) 完全独立复制且不沿用不变量；(d) 引入配置管理后台/数据库 | Release 可被原地改写、无审批、无审计、激活非原子、在途请求被切换污染 | J2-F、生产 ruleset 激活 | `DEFERRED / NOT_APPROVED` |
| DEC-6 | 多进程全局限流 | **短期：显式单进程部署约束**（每 `(provider, account)` 同时只允许一个应用进程；启动断言 + 运维手册 + 禁止多 worker/多实例横向扩展）；不新增基础设施、不引入 Redis | (b) 共享存储分布式限流；(c) 独立 Egress Gateway 单一出口 | 多 worker 部署下 10 req/min 全局约束失效 → 触发承运商 429/风控 | 生产 Provider 激活、Batch K 前置 | `DEFERRED / NOT_APPROVED` |

### 2.3 三类状态必须分开记录

| 维度 | 状态 | 说明 |
|---|---|---|
| 离线实现 | Batch I ✅ 已完成并通过复审；Batch J1 ✅ 已完成并通过复审 | Checkpoint `6ccdc5f`、`3c3675e` |
| 决策准备 | ✅ 本决策包完成 | `DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL` |
| 生产可用性 | ❌ 未达成 | 无真实包装数据、无获批 ruleset、无真实 Provider 配置与凭证 |

---

## 3. 需要用户批准的具体内容（批准清单）

以下条目是**逐条可批准/可拒绝**的清单。全部批准之前，J2 只能停留在「等待批准」状态，且默认应用必须保持 `PACKAGE_RULES_NOT_CONFIGURED` 的 fail-closed 行为。

> **Task 048 批准结果**：AP-1.1～AP-1.7（DEC-1 → D-032）、AP-2.1～AP-2.10（DEC-2 → D-033）、AP-3.1～AP-3.6（DEC-3 → D-034）、AP-4.1～AP-4.4（DEC-4 → D-035）已全部获批并写入 `docs/PHASE6_CONTRACT.md` §5.4～§5.7；**AP-5.1～AP-5.6 与 AP-6.1～AP-6.4 仍为 `DEFERRED / NOT_APPROVED`**。下列表格保留提交时的原始措辞。

### 3.1 DEC-1 批准项（已批准 → D-032）

| 编号 | 待批准内容 |
|---|---|
| AP-1.1 | 采纳 §4.3 的 `PackingPolicy` 字段级 schema（字段、类型、必填、无默认值原则） |
| AP-1.2 | 采纳封闭枚举值集合：`scope ∈ {sku, handling_class, general}`、`allocation_strategy ∈ {sequential_first_fit, best_fit_decreasing}`、`material_selection ∈ {smallest_inner_volume, priority_order}` |
| AP-1.3 | 采纳策略优先级：真实 `actual` > SKU scope > handling-class scope > general scope；同 scope 内 `priority` 升序、`policy_id` 字典序决胜；**必须唯一选中一个 policy** |
| AP-1.4 | 采纳「零匹配 policy 即 `PACKAGE_DATA_INCOMPLETE`，禁止隐式默认策略」；若业务需要兜底，必须在 ruleset 中显式声明一条 `general` policy |
| AP-1.5 | 采纳拆分/混装规则：`allow_split`、`max_units_per_package`、`max_packages_per_order`、`allow_mixed_sku`、`max_skus_per_package` 的语义与组合校验 |
| AP-1.6 | 采纳「policy 只能收紧、不得放宽 SKU/材料硬约束」；放宽即 ruleset 加载期拒绝（fail closed） |
| AP-1.7 | 采纳缺失配置行为矩阵（§4.5），并明确规定**不新增公共 reason code**（继续受 D-024 约束，新 code 需独立决策） |

### 3.2 DEC-2 批准项（已批准 → D-033）

| 编号 | 待批准内容 |
|---|---|
| AP-2.1 | 采纳「三处归属 + 派生视图」模型：约束分别落在 `SkuPackagingSpec.handling`、`PackageMaterialSpec`、`PackingPolicy`，不新增顶层 `ConstraintSet` 持久实体 |
| AP-2.2 | 采纳 `OrientationPolicy ∈ {any, upright_only, fixed}` 语义与「packed unit 尺寸按声明方向记录」的约定 |
| AP-2.3 | 采纳 `Fragility ∈ {none, fragile, very_fragile}` 以及 `PackingPolicy.fragile_mixing ∈ {allow, single_sku_only, alone_only}` |
| AP-2.4 | 采纳 `StackingConstraint {stackable: bool, max_stack_units: int\|null, max_top_load_g: Decimal\|null}`，并明确 Package 级堆叠能力取所含物品的最严值 |
| AP-2.5 | 采纳危险品表达方式：`hazardous: bool` + `hazard_class_ref: str\|null`（指向**已批准分类目录**的 opaque 引用），**禁止工程自行发明 DG 代码/法规分类**；危险品默认不得与非危险品混装 |
| AP-2.6 | 采纳 Weight Limit 双层语义：材料 `max_gross_weight_g`（硬上限）与 policy `max_package_gross_weight_g`（业务/承运商上限，只能收紧） |
| AP-2.7 | 采纳 Dimension Limit 双层语义：材料 `inner/outer_dimensions_mm`（硬上限）与 policy `max_package_outer_dimensions_mm`（只能收紧） |
| AP-2.8 | 采纳 Material Compatibility 的 **AND 语义**：SKU 侧白名单 ∧ 材料侧能力；冲突即 fail closed，不得放宽或回退 |
| AP-2.9 | 采纳「全部上述约束**不进入公共 API**」，继续遵守契约 §9.3 的 `PackageResponse` 边界 |
| AP-2.10 | 采纳材料侧新增字段：`material_type`（封闭枚举）、`availability_status ∈ {active, retired}`、`hazmat_approved: bool`、`cushioned: bool`、`orientation_supported` |

### 3.3 DEC-3 / DEC-4 / DEC-5 / DEC-6 批准项（DEC-3/DEC-4 已批准 → D-034/D-035；DEC-5/DEC-6 暂缓）

| 编号 | 待批准内容 |
|---|---|
| AP-3.1 | 采纳 §6.3 的分阶段确定性启发式架构（Stage 0～6）与 Best-Fit Decreasing 放置 |
| AP-3.2 | 采纳显式确定性排序键（§6.5）与「禁止 set/dict 迭代顺序、随机、时钟、locale 参与决策」的实现约束 |
| AP-3.3 | 采纳性能边界（单订单 unit 硬上限、材料数量上限、时间预算、无回溯/无求解器依赖） |
| AP-3.4 | 采纳 fail-closed 规则：任一 unit 不可装即整单 `unavailable`，禁止部分 Package 集合进入报价 |
| AP-3.5 | 采纳「J2 生产算法与 J1 synthetic 顺序 first-fit 是两个不同对象」的区分与激活门禁（§6.8） |
| AP-3.6 | 确认 3D 放置精度目标为「尺寸可行性 + 轴对齐方向枚举」，**不承诺**最优 3D 装箱，并接受该限制写入文档 |
| AP-4.1 | 采纳 §7.3 的材料候选过滤顺序与硬过滤项集合 |
| AP-4.2 | 采纳两种封闭排序策略 `smallest_inner_volume` / `priority_order` 及其完整 tie-break 键 |
| AP-4.3 | 采纳 §7.5 的 8 条禁止 fallback 规则（含禁止合成材料、禁止跨 SKU 借用白名单、禁止「最接近尺寸」模糊匹配） |
| AP-4.4 | 采纳「一个 Package 只使用一种材料」与「材料必须出现在该 ruleset 内」的 J2 约束 |
| AP-5.1 | 采纳「复用治理语义、独立实现 Packaging 治理」的方向（§8.3 方案 C） |
| AP-5.2 | 采纳最小企业治理角色与职责分离矩阵（§8.5）：Author 不得同时担任 Validator、Approver 或 Activator；Validator 与 Approver 可为同一人（如需更严可另行收紧） |
| AP-5.3 | 采纳 Release 状态机与回滚语义（rollback = 重新激活既有不可变 Release，不改历史） |
| AP-5.4 | 采纳审计记录字段集合与 append-only 要求、保留策略由业务确认 |
| AP-5.5 | 批准 Packaging Release 与 Tracking Release **使用独立 configuration scope、独立激活**（互不连锁） |
| AP-5.6 | 批准只读版本化文件的存储载体与目录约定（**不引入数据库/Redis**），并指定 active 指针载体（配置文件或环境变量） |
| AP-6.1 | 采纳「短期单进程部署约束」为唯一经批准的生产激活形态 |
| AP-6.2 | 采纳启动断言 + 运维手册 + 禁止多 worker/多实例横向扩展作为该约束的执行手段 |
| AP-6.3 | 确认在 DEC-6 批准项之外**不得**自行引入 Redis、共享缓存或新的限流基础设施 |
| AP-6.4 | 确认后续若确需多进程/多实例，必须先经独立决策在 (b) 共享存储与 (c) 独立 Egress Gateway 之间选择，并显式批准新增基础设施 |

### 3.4 批准后的落地方式（Task 047 时未执行；已由 Task 048 执行）

DEC-1～DEC-6 获批**不等于**契约已被修改。落地需要一次**单独授权**的任务，顺序为：

1. 更新 `docs/DECISIONS.md`：为获批的包装决策建立正式的、由用户指定编号的决策记录；
2. 更新 `docs/PHASE6_CONTRACT.md` §5.1（`PackingPolicy` 字段级 schema、约束承载字段）、§5.2/§5.3、新增配置治理小节；
3. 更新 `AGENTS.md` 冻结规则与 `docs/ARCHITECTURE.md` 对应边界；
4. 之后才允许进入 J2 代码实施。

Task 047 **不**代用户决定新决策的编号、不预写 D 编号、不修改上述三份文件。

> **Task 048 更新**：第 1～3 步已对 DEC-1～DEC-4 执行完毕——D-032～D-035 已写入 `docs/DECISIONS.md`；`docs/PHASE6_CONTRACT.md` 已新增 §5.4～§5.8（其中 `PackingPolicy` schema 落在 §5.4，而非原计划的 §5.1）；`AGENTS.md` 已同步冻结规则 23～24。`docs/ARCHITECTURE.md` 的结构性修订未在本任务进行（仅在需要时由后续任务同步）。第 4 步进入 J2 代码实施，下一入口为 Task 049。DEC-5/DEC-6 未获批准，其治理小节与配置治理实现**不得**落地。

---

## 4. DEC-1：PackingPolicy Schema

### 4.1 现状与缺口

冻结契约 `docs/PHASE6_CONTRACT.md` §5.1 只给出散文字段（`match criteria`、`allocation strategy`、`material selection strategy`、`split/mix constraints`），§5.2 只冻结了优先级原则与「禁止任选第一个可用箱型」。J1 实现因此只落地了 7 个字段的 synthetic 形态（`backend/models/packaging_rules.py:102-116`）。审计 C-J1 明确指出：**没有字段级 schema 与枚举值，实现者自行发明策略词汇事实上等于创造新契约**。

### 4.2 候选方案比较

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A 维持散文 | 由实现者在代码中定义策略，文档不枚举 | 无文档成本 | 契约不可审计；不同实现行为不同；无法测试「规则是否符合契约」 | 拒绝 |
| B 单一全局 policy | 无 match 条件，全 ruleset 一个 policy | 最简单 | 无法表达 SKU 差异或 handling-class 差异；逼出配置外的硬编码分支 | 拒绝 |
| C 结构化封闭 schema（推荐） | 显式 scope + match 字段 + 封闭枚举 + 限制字段；排序与匹配规则写死 | 可审计、可测试、可演进（加值需批准）；与契约 §5.2 优先级一致 | 需要一次契约增补 | **推荐** |
| D 外部规则 DSL/表达式引擎 | 用微型表达式或脚本描述匹配与分配 | 表达力最强 | 引入未批准依赖、不可静态验证、安全风险、不可测试边界 | 拒绝 |

### 4.3 推荐 schema（`PackingPolicy`）

所有字段 `frozen=True`、`extra="forbid"`、**除明确标注者外无默认值**（缺省即加载失败，避免静默语义）。

| 字段 | 类型 | 必填 | 不变量 / 语义 |
|---|---|---|---|
| `policy_id` | `str` 1..200，strip 非空 | 是 | ruleset 内唯一；同 `priority` 时的稳定决胜键（字典序升序） |
| `priority` | `int`（strict，≥0） | 是 | 同一 scope 内升序优先；数值越小越优先 |
| `scope` | `enum {sku, handling_class, general}` | 是 | 匹配层级；决定 `scope` 专属字段的必填性 |
| `sku` | `str` \| null | 当且仅当 `scope=sku` | 必须存在于同一 ruleset 的 `sku_specs`；其他 scope 出现即加载失败 |
| `handling_class` | `str` \| null | 当且仅当 `scope=handling_class` | 必须被至少一个 `SkuPackagingSpec.handling_class` 使用；否则视为不可达策略，**加载期拒绝**（D-032 已于契约 §5.4.3 冻结为拒绝） |
| `allocation_strategy` | `enum {sequential_first_fit, best_fit_decreasing}` | 是 | 封闭集合；`best_fit_decreasing` 为 DEC-3 生产算法；`sequential_first_fit` 保留为 J1 语义回归对照，**不得**被当作生产默认 |
| `material_selection` | `enum {smallest_inner_volume, priority_order}` | 是 | DEC-4 的排序策略；`priority_order` 需要材料侧 `selection_priority` 提供值 |
| `allow_split` | `bool` | 是 | `false` 时一个订单行必须完整落在同一 Package |
| `max_units_per_package` | `int` ≥1 \| null | 是（可为 null） | `null` 表示不额外限制（仅受材料容量约束） |
| `max_packages_per_order` | `int` ≥1 \| null | 是（可为 null） | 超出即 fail closed，不得继续装箱 |
| `allow_mixed_sku` | `bool` | 是 | `false` 时一个 Package 只能含单一 SKU |
| `max_skus_per_package` | `int` ≥1 \| null | `allow_mixed_sku=true` 时必填，否则必须为 null | 与 `allow_mixed_sku` 组合校验 |
| `fragile_mixing` | `enum {allow, single_sku_only, alone_only}` | 是 | 由 DEC-2 提供；仅当包内含 fragile 物品时生效 |
| `max_package_gross_weight_g` | `PositiveDecimal` \| null | 是（可为 null） | 只能 ≤ 材料 `max_gross_weight_g`；违反即加载失败（不得放宽） |
| `max_package_outer_dimensions_mm` | `PackageDimensions` \| null | 是（可为 null） | 只能是材料外尺寸的收紧；任一边大于材料外尺寸即加载失败 |

**设计取舍说明**：

- 不引入 `match_criteria` 自由结构体。匹配层级已被契约 §5.2 冻结为「SKU > handling-class > general」，用 `scope` 显式表达即可，不需要表达式求值。
- 不引入 `priority` 之外的排序规则来源，避免「按创建时间/文件名」这类不可审计决胜。
- 不把约束（方向/易碎/堆叠/危险品）放进 policy；它们属于 DEC-2，policy 只做收紧。

### 4.4 策略优先级与选择规则

```text
1. actual 真实装箱数据（若未来存在且已验证）优先于任何 rules 结果
2. rules 内匹配层级: scope=sku > scope=handling_class > scope=general
3. 同层级内: priority 升序 -> policy_id 字典序升序（稳定决胜）
4. 必须恰好解析出 1 个 policy
```

**唯一性约束**：同一 ruleset 内若存在两条 `scope=sku` 且 `sku` 相同且 `priority` 相同的 policy → ruleset **加载期拒绝**（配置错误），不得在运行期任选其一。

**可达性约束**：`scope=handling_class` 的 policy 必须至少被一个 SKU 使用；`scope=sku` 的 policy 的 `sku` 必须有 spec。

### 4.5 缺失配置时的行为（fail closed 矩阵）

| 情形 | 行为 | 公共 reason code | 内部诊断 category |
|---|---|---|---|
| 无 Active ruleset | fail closed，不构造任何 Package | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured`（沿用 J1） |
| ruleset 存在但 `policies` 为空 | fail closed | `PACKAGE_DATA_INCOMPLETE`（沿用 J1 现状） | `rules_not_configured` |
| ruleset 内无任何 policy 匹配该订单 SKU | fail closed，**不得**回退到其他 scope 以外的猜测 | `PACKAGE_DATA_INCOMPLETE` | `policy_unmatched`（内部新增 category） |
| 匹配策略被 SKU spec / 材料缺失阻塞 | fail closed | `PACKAGE_DATA_INCOMPLETE` | `sku_spec_missing` / `material_missing` |
| policy 字段非法 / 枚举越界 / 放宽硬约束 | **ruleset 加载期拒绝**（不进入估算） | 不产生运行时结果 | 配置加载异常 |
| policy 声明策略未实现 | fail closed | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured` |
| 仅是 synthetic ruleset | 仅在测试夹具中允许；默认应用永不注入 | `PACKAGE_RULES_NOT_CONFIGURED` | `rules_not_configured` |

**明确不新增公共 reason code**。`policy_unmatched` 等只是**内部** `PackageDiagnosticCategory`，不进入 API。若业务要求区分「规则缺失」与「规则不匹配」的公开语义，必须走独立决策新增 reason code（受 D-024 约束），本任务不批准。

### 4.6 DEC-1 结论

- 推荐方案：**4.3 的结构化封闭 schema**。
- 批准状态：**`APPROVED`（Task 048 → D-032）**；AP-1.1～AP-1.7 已全部落地到 `docs/PHASE6_CONTRACT.md` §5.4。
- 未批准时的边界（历史）：J2-B/C/D/E 不得实施；默认应用保持 `PACKAGE_RULES_NOT_CONFIGURED`。

---

## 5. DEC-2：包装约束模型

### 5.1 问题本质

七类约束的**事实来源不同**：有些是物品事实（物品必须直立、物品易碎、物品是危险品），有些是容器能力（箱子最多承重多少、内尺寸多大），有些是业务策略（是否允许混装、是否要求单独包裹）。把三者混在一处会导致两种失败：约束被策略悄然放宽，或同一事实出现多个来源。

### 5.2 候选方案比较

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A 全部平铺进 `SkuPackagingSpec` | 方向/易碎/堆叠/危险品/重量/尺寸/兼容性都挂在 SKU 上 | 查找简单 | 容器的承重与内尺寸无法归属 SKU；同一容器在不同 SKU 上重复声明 | 拒绝 |
| B 全部进 `PackingPolicy` | 都由 policy 决定 | 调整灵活 | 事实与策略混合；policy 可放宽安全约束；SKU 事实无持久归属 | 拒绝 |
| C 三处归属 + 派生视图（推荐） | SKU 事实、材料能力、policy 收紧各自归属；运行时派生 `EffectiveConstraintView` | 事实唯一、硬约束不可放宽、算法有单一读取点、provenance 仍由 ruleset version 决定 | 需要在算法中显式构造派生视图 | **推荐** |
| D 独立顶层 `ConstraintSet` 实体 | 新增第四类 ruleset 记录并被 SKU/material 引用 | 可复用约束组合 | 引入第四事实来源、交叉引用爆炸、provenance 歧义 | 拒绝 |

### 5.3 约束归属与执行点（逐项）

| 约束 | 领域归属 | 类型与表达 | 执行点 | 违反时行为 |
|---|---|---|---|---|
| **Orientation** | `SkuPackagingSpec.handling.orientation_policy`（物品事实）+ `PackageMaterialSpec.orientation_supported`（容器能力） | `enum {any, upright_only, fixed}` / `enum {any, upright_only}` | 候选材料过滤 + 放置方向枚举 | 无可行方向 → 该 unit 不可装 → 整单 fail closed |
| **Fragile** | `SkuPackagingSpec.handling.fragility`（物品事实）+ `PackageMaterialSpec.cushioned`（容器能力）+ `PackingPolicy.fragile_mixing`（策略收紧） | `enum {none, fragile, very_fragile}` / `bool` / `enum {allow, single_sku_only, alone_only}` | 混装裁决 | 违反 → 拒绝该混装组合；无法拆分安置 → fail closed |
| **Stackability** | `SkuPackagingSpec.handling.stacking`（物品事实）+ Package 级**派生**结论 | `{stackable: bool, max_stack_units: int\|null, max_top_load_g: Decimal\|null}` | Package 构造后派生；policy 若声明运输堆叠上限则取交集 | Package `stackable=false` 仍可装箱，但必须如实投影「不可堆叠」决策事实；若 policy 要求可堆叠而物品不可 → fail closed |
| **Hazardous Goods** | `SkuPackagingSpec.handling.hazardous` + `hazard_class_ref`（物品事实）+ `PackageMaterialSpec.hazmat_approved`（容器能力） | `bool` + opaque `str\|null` | 候选材料过滤 + 混装裁决 | 危险品 × 非危险品混装默认禁止；材料未获 hazmat 批准 → 该材料不可选 |
| **Weight Limit** | `PackageMaterialSpec.max_gross_weight_g`（硬上限）+ `PackingPolicy.max_package_gross_weight_g`（收紧） | `PositiveDecimal`（g） | 每次加入 unit 前预投影 | 超限 → 尝试其他材料；无材料可装 → fail closed |
| **Dimension Limit** | `PackageMaterialSpec.inner_dimensions_mm`（容量）/`outer_dimensions_mm`（物理外尺寸）+ `PackingPolicy.max_package_outer_dimensions_mm`（收紧） | `PackageDimensions`（mm/mm³） | 容量与轴对齐可行性检查 | 同上 |
| **Material Compatibility** | `SkuPackagingSpec.compatible_material_ids`（白名单）∧ `PackageMaterialSpec` 能力（类型/易碎/危险品/方向） | `tuple[str, ...]` / 各能力字段 | 候选材料过滤 | 交集为空 → 该 SKU 不可装 → fail closed，**不得**回退 |

> 说明：`hazard_class_ref` 是**引用**，其取值必须来自业务/合规方批准的分类目录。工程**不得**自行定义 UN 编号、危险品等级或法规类别。

### 5.4 职责边界（四类对象）

| 对象 | 回答什么问题 | 不回答什么 | 变更方式 |
|---|---|---|---|
| `SkuPackagingSpec` | 一个**包装单元**有多重、多大、允许什么方向、是否易碎/可堆叠/危险品、允许哪些材料 | 容器能装多少、业务是否允许混装 | 新 ruleset version |
| `PackageMaterialSpec` | 一种**容器**的内外尺寸、皮重、最大毛重、材质类型、可用状态、能力（易碎缓冲/危险品/方向） | 某个 SKU 该不该装它、业务拆分策略 | 新 ruleset version |
| `PackingPolicy` | 匹配谁、用哪种分配与材料选择策略、允许拆分/混装到什么程度、业务上限 | 物品事实、容器物理能力 | 新 ruleset version |
| `EffectiveConstraintView`（**派生，不持久化**） | 本次分配中某 (SKU, 材料, policy) 组合的**有效**上限（取最严） | 任何独立事实 | 每次估算在内存中构造 |

派生视图规则：

```text
effective_max_gross_weight_g      = min(material.max_gross_weight_g, policy.max_package_gross_weight_g ?? +inf)
effective_max_outer_dimensions_mm = min_componentwise(material.outer_dimensions_mm, policy.max... ?? +inf)
effective_orientation_supported   = most_restrictive(material.orientation_supported, sku.orientation_policy)
effective_mixing_allowed          = policy.allow_mixed_sku ∧ (无危险品冲突) ∧ (fragility 规则满足)
```

派生视图**不得**进入 `PackageProvenance`、API 或持久化结构；provenance 只记录 ruleset ID/version 与 `input_fingerprint`（沿用 J1）。

### 5.5 与冻结契约的关系

- 契约 §2.3 的 `Package`/`PackageWeight`/`PackageDimensions` 不变量（`volume = L×W×H`、`gross = item + packaging`）**保持不变**。
- 契约 §9.3 明确 `PackageResponse` 不含 material compatibility、capacity、policy、diagnostics。DEC-2 新增字段全部为**内部规则数据**，API 投影零变化。
- 材料内尺寸是**容量**的既有表达方式（`inner_dimensions_mm`），DEC-2 不引入独立 `capacity` 字段，避免双来源。

### 5.6 DEC-2 结论

- 推荐方案：**三处归属 + 派生视图**（方案 C）。
- 批准状态：**`APPROVED`（Task 048 → D-033）**；AP-2.1～AP-2.10 已全部落地到 §5.5。
- 危险品表达方式（涉及合规）、易碎混装策略、堆叠载荷语义均已随 D-033 冻结；真实取值仍属外部数据输入（DM-04～DM-07）。

---

## 6. DEC-3：生产级装箱算法

### 6.1 候选方案比较

| 方案 | 说明 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| First-Fit Decreasing（FFD） | 按体积降序，装入第一个可容纳的容器 | 简单、可证明与确定性易达成 | 空间利用率一般；容器顺序敏感；无「选更合适容器」判断 | 部分采纳（作为 `sequential_first_fit` 兼容策略） |
| Best-Fit | 每次选「装入后剩余空间最小」的容器 | 利用率优于 FF，易实现确定性决胜 | 仍需显式 tie-break；无方向/危险品语义 | **采纳为放置内核** |
| 3D Bin Packing / EP 精确解 | 精确三维装载/极值点算法或精确最优解 | 装载率高 | 最优 3D BPP 为 NP-hard；精确解在配置数据缺失时无意义；实现与测试成本高 | 不采纳（J2 不承诺最优） |
| Constraint-based（MIP / CP-SAT） | 用求解器建模容量/方向/重量约束 | 可表达复杂约束并求最优 | 引入未批准依赖；求解时间不可预测；结果需可复现性保障 | 不采纳 |
| **分阶段启发式（推荐）** | 校验 → 排序 → 候选过滤 → Best-Fit 放置 → 拆分混装裁决 → 守恒校验 → 投影 | 无可变依赖、多项式、可审计、每阶段可单测、严格 fail closed | 非最优装载；须接受并文档化该限制 | **推荐** |

**关键判断**：J2 的目标是**可解释、可复现、可审计的报价输入**，不是物流装载率优化。在真实包装数据尚未取得时追求装载最优没有业务意义，且会把算法复杂度转嫁到不可验证的路径上。

### 6.2 推荐算法架构

```text
Stage 0  Preflight                校验 ruleset 已批准/非 synthetic、policy 唯一匹配、SKU spec 与材料齐全
Stage 1  Unit expansion           订单行按 quantity 展开为 unit 列表（不合并、不丢行）
Stage 2  Deterministic ordering   按 (packed_unit_volume desc, unit_weight desc, sku asc, line_index asc)
Stage 3  Candidate filtering      每 unit 计算可行材料集合（DEC-4 硬过滤 + DEC-2 能力 + 方向可行性）
Stage 4  Placement (Best-Fit)     对每个 unit 选「装入后剩余容积最小」的已开 Package；否则按 DEC-4 选新材料开新 Package
Stage 5  Split/Mix adjudication   按 policy 校验拆分与混装；违反即回退到「开新 Package」一次，仍违反则失败
Stage 6  Post-validation & project 守恒、唯一 ID、非空 items、材料合法、毛重/尺寸上限、生成 provenance
```

各阶段失败即整体失败（fail closed），不保留部分结果。

### 6.3 空间、重量与方向约束的处理

| 约束 | 处理方式 | 明确不做什么 |
|---|---|---|
| 空间（容积） | 以 `inner_dimensions_mm.volume_mm3` 做**必要条件**预筛；每次加入 unit 前做累计容积检查 | 不把容积通过当作装载证明（容积通过 ≠ 几何可装） |
| 空间（几何） | 对每个 unit × 材料枚举**轴对齐方向**（≤6 种排列，受 `orientation_policy` 限制），检查 unit 三边是否 ≤ 材料内尺寸三边 | **不做**任意角度旋转、不做非轴对齐、不做精确 3D 装载几何 |
| 重量 | 每次加入前计算 `item_weight_g_sum + unit_weight + tare`，与 `min(material.max_gross, policy.max)` 比较 | 不做重量分布/重心计算（J2 声明为限制） |
| 方向 | `fixed` 只允许声明方向；`upright_only` 允许绕竖直轴旋转（L/W 互换，H 固定）；`any` 允许全排列 | 不自行放宽 `fixed` |
| 堆叠 | 仅派生 Package 级结论（取所含物品最严），供未来运输策略使用 | 不在 J2 做堆叠载荷的物理建模 |

**受控近似声明**：本算法在空间维度上保证「每个 unit 的轴对齐外接盒能放入材料内腔且累计容积不超限」，**不保证**存在性证明的最优排列。该限制必须写入 J2 交付文档与 `PackageEstimationResult` 的对外说明文字（不新增 reason code）。

### 6.4 拆分与混装

| 规则 | 行为 |
|---|---|
| `allow_split=false` | 一个订单行必须完整落在同一 Package；需要拆分时先尝试更大材料，仍不可行则 fail closed |
| `allow_mixed_sku=false` | 一个 Package 只能含单一 SKU；已在包内的其他 SKU 不参与 Best-Fit 候选 |
| `max_skus_per_package` | 加入新 SKU 前检查数量上限 |
| 危险品 | 危险品与非危险品默认不得同包（受 DEC-2 批准值约束） |
| `fragile_mixing` | 按 DEC-2 批准值裁决（`allow` / `single_sku_only` / `alone_only`） |
| `max_units_per_package` / `max_packages_per_order` | 达到上限即停止装入并按策略失败或收束；超 `max_packages_per_order` 必须 fail closed |

### 6.5 确定性与稳定排序

必须显式固定、且必须写进测试的排序键：

```text
unit 排序键      = (-packed_unit_volume_mm3, -unit_weight_g, sku, line_index)
material 排序键  = §7.3（按 policy 声明的策略，末位恒为 material_id 字典序）
policy 排序键    = (scope_rank, priority, policy_id)
Package ID 顺序  = 生成顺序 index（PKG-001..PKG-NNN，沿用 J1 形态）
```

实现约束（均可测）：

- 禁止依赖 `set` / `frozenset` 的迭代顺序做决策；需要遍历时先排序。
- 禁止随机数、`hash()`、`time`、`datetime.now()` 参与**分配决策**（时钟只用于 `checked_at`/`estimated_at` 记录）。
- 禁止 locale 相关比较（统一按 Unicode 码点比较）。
- 禁止依赖输入 `dict` 插入顺序（订单行顺序由 `line_index` 决定）。
- 同输入 + 同 ruleset version + 同算法版本 ⇒ 逐字节相同的 `packages` 序列与 `input_fingerprint`（须有重跑等价测试）。

### 6.6 性能边界

| 维度 | 边界 | 处理 |
|---|---|---|
| 单订单 unit 数 | 硬上限（建议 500，需批准） | 超限直接 fail closed，不得无界扩张运行时间 |
| 单 ruleset 材料数 | 硬上限（建议 200，需批准） | ruleset 加载期校验 |
| 候选方向枚举 | ≤ 6 排列/unit | 固定上界 |
| 算法复杂度 | `O(U × (M + P))`，`P` 为已开 Package 数 | 多项式、无回溯 restart |
| 时间预算（合成基准） | `U ≤ 50` 时 p95 ≤ 20 ms；`U = 500` 最坏 ≤ 200 ms（CI 参考值，需批准） | 超预算视为性能回归门禁失败 |
| 内存 | `O(U + P × 平均 items)` | 不缓存跨请求状态（D-026） |

禁止：递归穷举、随机重启、多轮迭代优化、外部求解器、跨请求缓存。

### 6.7 无法装箱时的 fail-closed 规则

1. 任一 unit 无可行材料 → **整单** `unavailable`，`packages=()`。
2. 任一阶段不变量失败 → 整单 `unavailable`。
3. **绝不**返回部分 Package 集合作为报价输入（契约 §4.4 冻结）。
4. **绝不**通过以下方式「凑成功」：放大材料尺寸、放宽重量上限、丢弃/合并 unit、超出 policy 拆分、改用未列入白名单的材料、改用 synthetic 材料。
5. 公共 reason code 继续只用 `PACKAGE_RULES_NOT_CONFIGURED` / `PACKAGE_DATA_INCOMPLETE`；细分原因只进内部 `PackageEstimationDiagnostic.category`（受 D-024 约束）。
6. Task 046 的 F-07（容量不足与 split 冲突共用 `PACKAGE_DATA_INCOMPLETE`）在 J2 继续保留；若业务要求公开区分，需独立决策新增 reason code。

### 6.8 J1 Synthetic First-Fit 与生产算法的严格区分

| 维度 | J1（已冻结，`3c3675e`） | J2 生产算法（D-034 已批准） |
|---|---|---|
| 策略枚举 | `SyntheticPackingStrategy.SEQUENTIAL_FIRST_FIT` | `PackingPolicy.allocation_strategy=best_fit_decreasing` |
| 放置规则 | 顺序遍历已开 Package，第一个能装即装（first-fit） | 选「剩余容积最小」的已开 Package（best-fit），否则新材料 |
| 排序 | 订单行顺序 / 单元顺序 | 显式体积降序 + 权重降序 + SKU/行号决胜 |
| 方向 | 无（只做容积与毛重） | 轴对齐方向枚举 + `orientation_policy` |
| 易碎/危险品/堆叠 | 无字段 | DEC-2 约束生效 |
| 拆分/混装 | `allow_split` + `allow_mixed_sku` 两开关 | 六字段组合 + 危险品/易碎裁决 |
| 材料选择 | `SMALLEST_VOLUME_FIT` 单一策略 | DEC-4 硬过滤 + 两种声明策略 |
| 隔离机制 | `synthetic_only: Literal[True]` 全链路强制 | 需新增「已批准生产 ruleset」门禁（**不得**复用 synthetic 标记冒充） |
| 可否作为生产默认 | **否** | 仅在其规则经批准且真实数据到位后方可激活 |

**红线**：J2 实施时**不得**通过「把 `synthetic_only` 改宽」来激活生产算法；必须引入独立的「已批准生产 ruleset」识别与门禁，并保留 synthetic 隔离（否则 Task 046 F-02 的整改会被回退）。

### 6.9 测试与验收指标

| 类别 | 指标 |
|---|---|
| 数量守恒 | 每个订单行在所有 PackageItem 中数量之和 == 订单数量（属性测试 + 真实订单结构） |
| 确定性 | 同输入重跑 100 次，`packages` 与 fingerprint 完全一致 |
| 禁止商品数据 | 以「Product 物理字段被读取即失败」的守卫/桩验证：估算过程零读取 `weight_g`/`dimensions_mm`/`volume_mm3`/`volumetric_gross_weight_kg` |
| fail-closed 矩阵 | 无 ruleset / 无匹配 policy / 缺 spec / 缺材料 / 容量不足 / 重量超限 / 方向不可行 / split 禁止 / 超 packages 上限 / 危险品冲突 各自独立用例 |
| 方向 | `any`/`upright_only`/`fixed` 三态 × 可行/不可行 |
| 材料 | 白名单交集为空、能力冲突（hazmat/cushioned/orientation） |
| 不变量 | `volume = L×W×H`、`gross = item + tare`、Package ID 唯一、items 非空、材料必须来自 ruleset |
| 无 float | 全链路 Decimal；禁止 float 的静态/运行断言 |
| 性能 | 上述预算下的基准测试，纳入回归门禁 |
| 黄金集 | 合成黄金数据集（≥12 场景）作为行为基线；**不得**称为生产验证 |

### 6.10 DEC-3 结论

- 推荐：**分阶段确定性启发式 + Best-Fit Decreasing**，明确非最优、非求解器、非 J1 算法。
- 批准状态：**`APPROVED`（Task 048 → D-034）**；AP-3.1～AP-3.6 已全部落地到 §5.6。
- `allocation_strategy` 仍为封闭枚举；扩张枚举值需新决策。

---

## 7. DEC-4：包装材料选择

### 7.1 候选集来源

`candidates(sku, policy, ruleset) = { m ∈ ruleset.materials : 全部硬过滤通过 }`

材料**只能**来自当前生效 ruleset 的 `materials`。ruleset 加载期已校验 SKU 的 `compatible_material_ids` 全部存在（`backend/models/packaging_rules.py:159-163`），运行期不再做「找不到就忽略」的容错。

### 7.2 硬过滤顺序（全部为必要条件）

```text
F1 兼容性    material.material_id ∈ sku.compatible_material_ids
F2 可用性    material.availability_status == active
F3 危险品    sku.hazardous -> material.hazmat_approved 必须为 true
F4 易碎      sku.fragility != none 且 policy 要求缓冲 -> material.cushioned 必须为 true
F5 方向      material.orientation_supported 必须覆盖 sku.orientation_policy
F6 容量      unit 的轴对齐可行方向存在 -> 三边均 ≤ material.inner_dimensions_mm
F7 单位容量  unit 单独装入后 item_weight + material.tare ≤ min(material.max_gross, policy.max)
F8 业务上限  material.outer_dimensions_mm ≤ policy.max_package_outer_dimensions_mm（若声明）
```

### 7.3 排序与决胜键（`material_selection` 两种封闭策略）

```text
priority_order:
    (material.selection_priority asc, material.inner_volume asc, material.outer_volume asc,
     material.tare_weight_g asc, material.material_id asc)

smallest_inner_volume:
    (material.inner_volume asc, material.outer_volume asc, material.tare_weight_g asc,
     material.material_id asc)
```

- `selection_priority` 仅在 `priority_order` 下必填（`int ≥ 0`，ruleset 内允许重复，靠后续键决胜）。
- 末位恒为 `material_id` 字典序，保证同一 ruleset 内绝对确定。
- 若 F1～F8 过滤后为空 → **fail closed**（`PACKAGE_DATA_INCOMPLETE` / 内部 `material_missing` 或 `capacity_exceeded`）。

### 7.4 容量、尺寸、皮重约束的一致性要求

| 要求 | 检查 |
|---|---|
| 内腔 ≥ 外尺寸 | `outer.volume ≥ inner.volume`（J1 已有） |
| 外尺寸 ≥ 内尺寸逐边 | DEC-2 增补：逐边比较，不只比体积 |
| 皮重 > 0 | J1 已有（`PositiveDecimal`） |
| 最大毛重 > 皮重 | J1 已有 |
| 皮重必须计入毛重 | `gross = item_weight + tare`（冻结不变量） |
| 容量必须以**内**尺寸判定 | 不得用外尺寸判定装载 |
| 体积必须精确等于三维乘积 | 不得提前舍入 |

### 7.5 禁止未经批准的材料 fallback（8 条）

1. 禁止在 `compatible_material_ids` 之外选材（含「该 SKU 没有就直接用任意材料」）。
2. 禁止使用不在当前 ruleset `materials` 中的材料（含硬编码内置目录）。
3. 禁止 synthetic / 测试夹具材料进入任何非测试路径。
4. 禁止「最接近尺寸」或模糊匹配（不得按体积差、边长差选材）。
5. 禁止因容量不足自动放大到更大材料后再放宽重量/方向约束。
6. 禁止跨 SKU 借用白名单（A 的白名单不得用于 B）。
7. 禁止在 `allow_split=false` 时通过换材料实现事实上的拆分。
8. 禁止一个 Package 内混用多种材料（J2 限定；若未来需要必须新决策）。

### 7.6 冲突处理

| 冲突 | 处理 |
|---|---|
| 两个策略均可选到不同材料 | 由 policy 明确声明一种策略；策略在 policy 中必填，无隐式默认 |
| 同一策略下多个材料等价 | 末位 `material_id` 决胜 |
| 兼容性 ∧ 能力冲突 | 取交集；为空即 fail closed，不做优先级加权 |
| policy 上限 < 材料物理能力 | 取更严者（policy 收紧），不报错 |
| policy 上限 > 材料物理能力 | **ruleset 加载期拒绝**（视为试图放宽） |
| 材料 `availability_status=retired` | 不进入候选；若某 SKU 只剩 retired 材料 → fail closed |

### 7.7 DEC-4 结论

- 推荐：**F1～F8 硬过滤 + 两种封闭排序策略 + 8 条禁止 fallback**。
- 批准状态：**`APPROVED`（Task 048 → D-035）**；AP-4.1～AP-4.4 已全部落地到 §5.7。

---

## 8. DEC-5：配置治理

### 8.1 现状评估（复用还是不复用）

现有治理实现只有 `TrackingConfigurationCatalog`（append-only、同 ID 不可变）与 `TrackingConfigurationRelease`（请求内固定、已批准发布）。审计 §9 已明确：**它只保证「同一 ID 内容不可变」这一条不变量，不是企业级配置管理，且没有 active 指针、activate、rollback、审批、actor、审计日志**。

契约 §8.4 已冻结了 Provider 配置治理的完整语义（发布顺序、原子激活、rollback 重新激活、请求级 pinning、审计字段）。Packaging rules 与 Provider config 的**语义内核相同**（不可变 + 唯一 Active + 原子切换 + 可回滚 + 可审计 + 请求固定），但**内容类别不同**（无凭证、无 environment/provider/account 概念、影响所有 Provider 的报价输入）。

### 8.2 候选方案比较

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A 直接复用 Tracking 实现 | Packaging Release 复用 `TrackingConfigurationCatalog` 与 `TrackingConfigurationRelease` | 零新增实现 | 语义污染：Provider/Account/环境字段对包装无意义；凭证模型邻近风险；Active 指针范围混淆；审计混合 | 拒绝 |
| B 完全独立且不沿用不变量 | 另起一套简化配置表 | 简单 | 失去不可变性/原子性保证，正是 Task 041 已判定为缺陷的那类问题 | 拒绝 |
| C 复用治理语义、独立实现（推荐） | 定义 `PackagingConfigurationCatalog` + `PackagingRelease` + `PackagingActivePointer`，逐条沿用 A 的不变量，但独立存储与 scope | 语义一致、边界干净、可独立审计与激活、不影响 Provider 配置 | 需一次契约增补；两套实现需共享命名规范而非共享代码 | **推荐** |
| D 引入配置管理后台/数据库 | 独立配置服务 | 治理最强 | 违反「不引入数据库/Redis/微服务」的既有约束 | 本阶段拒绝 |

### 8.3 推荐架构

```text
PackagingRevision      不可变（ruleset_id + version + content_hash），由 PackagingRuleSet 承载
       |
PackagingRelease       不可变，固定精确的 PackagingRuleSet version 集合 + 审批证据
       |
PackagingActivePointer 唯一可变指针: (configuration_scope="packaging", active_release_revision_id, activated_at, activation_audit_ref)
       |
PackagingRuleSetReader.get_active(at)  返回该时刻唯一 Active Release 中生效的 ruleset
```

- `configuration_scope` 与 Tracking 的 `(environment, configuration_scope)` **独立**：Packaging 首批只有一个 scope（`packaging`），不与 Provider 激活连锁。
- 一请求内固定：`estimate_for_order` 在开始时捕获一次 Active Release，整个估算使用同一 ruleset（J1 已按此形态实现，仅读取来源不同）。
- 切换与 rollback 不得影响在途请求。

### 8.4 最小可行企业治理：状态机与流程

```text
DRAFT --validate--> VALIDATED --approve--> APPROVED --publish--> PUBLISHED --activate--> ACTIVE
                                                                        |                    |
                                                                        |                    +--supersede--> SUPERSEDED
                                                                        +--(rollback: 重新激活旧的 APPROVED/PUBLISHED 版本)
```

| 步骤 | 必做动作 | 记录 |
|---|---|---|
| 创建 | Author 生成不可变 DRAFT（新 version，不改旧 version） | revision_id、content_hash、created_by_ref、created_at |
| 校验 | Validator 执行 schema/交叉引用/单位/守恒/硬约束一致性检查 | validated_by_ref、validated_at、校验器版本、结果摘要 |
| 审批 | Approver 审批（不得为 Author） | approved_by_ref、approved_at、approval_ref |
| 发布 | 生成不可变 Release，固定精确 version 集合 | release_revision_id、created_at、audit_ref |
| 激活 | Activator（不得为 Author）原子切换 Active 指针 | activated_by_ref、activated_at、activation_audit_ref、原因 |
| 回滚 | 重新激活既有已批准 Release（不改历史） | 原 Active、目标 Release、操作主体、UTC 时间、原因、审批引用、audit_ref |

### 8.5 职责分离矩阵（最小可行）

| 角色 | 可以做什么 | 不得做什么 |
|---|---|---|
| Author（业务/仓储数据所有者） | 创建 DRAFT ruleset | 审批自己创建的版本、执行激活 |
| Validator（架构/数据质量） | 执行自动化 + 人工校验并签署 | 审批商业口径 |
| Approver（物流业务负责人 + 合规，涉危险品时） | 批准 Release | 创建 DRAFT |
| Activator（运维/SRE） | 执行原子激活与回滚 | 创建或审批内容 |
| Auditor（管理层/独立方） | 只读审计 | 修改任何记录 |

**职责分离硬约束**：Author 不得同时担任 Validator、Approver 或 Activator；Validator 与 Approver 可为同一人（若业务要求更严，可另行收紧）；每一角色必须有可追溯的身份引用（不含 PII 的 opaque ref 即可）。

### 8.6 版本固定与审计责任

- 每次估算必须记录 `ruleset_id` / `version` / `source_revision` / `input_fingerprint`（J1 已实现，J2 保持）。
- 未来若启用报价历史（当前被 D-026 禁止），必须关联 ruleset ID/version 与 fingerprint，不得事后重算覆盖。
- 审计数据属于**配置治理数据**，不是 Quote History，也不授权跨请求 Quote Cache（与契约 §8.4 同构）。
- 审计日志 append-only、禁止 PII/凭证/tracking number、禁止记录完整订单 payload。

### 8.7 存储载体（需批准）

- 现状：只有 `backend/tests/packaging_fixtures.py` 的 synthetic 夹具；生产 ruleset **不存在**。
- 推荐：**只读版本化 JSON 文件**（独立目录，如 `config/packaging/releases/<release_id>.json`）+ 独立 active 指针文件或环境变量 + append-only 审计 JSONL。
- 明确禁止：数据库、Redis、消息队列、微服务、第三方配置中心（均需新决策）。
- 该载体与目录约定属**待批准项**（AP-5.6），本任务不创建任何目录或文件。

### 8.8 DEC-5 结论

- 推荐：**方案 C（复用语义、独立实现）+ 5 角色最小治理 + 原子激活 + rollback 重新激活 + append-only 审计**。
- 批准状态：**`DEFERRED / NOT_APPROVED`（Task 048）**；AP-5.1～AP-5.6 未获批准，Batch J2-F 不在当前授权范围。
- 明确：Task 047/048 均**没有**实现任何治理代码，也**没有**声称现状已具备配置治理能力。

---

## 9. DEC-6：多进程全局限流

### 9.1 现状事实

| 事实 | 证据 |
|---|---|
| 限流器为进程内内存实现（`deque` + `threading.Lock`） | `backend/integrations/tracking.py:75-101` |
| 共享粒度为单位进程内 `(provider_revision_id, account_revision_id)` | `backend/integrations/tracking.py:104-115` |
| 默认参数 10 请求 / 60 秒 | `backend/integrations/tracking.py:78-83` |
| 触发限流返回 `PROVIDER_RATE_LIMITED`（`retryable`） | `backend/integrations/tracking.py:410-412`、`:451-454` |
| 无并发池、无自动重试、无熔断器 | `backend/integrations/tracking.py:405-430`（同步顺序调用）；审计 F-1/F-5 |
| 无部署配置、无 worker 配置、无 `.env.example` | 仓库与 `backend/main.py` 均无 |

**结论**：10 req/min 的**全局**语义当前只在「单进程」时成立。多 worker（`--workers N`）或多实例（横向扩展）会各自持有独立计数器，实际外部请求速率最高可达 `10 × 进程数`，直接触发承运商 429 甚至账号风控。

### 9.2 候选方案比较

| 方案 | 保证 | 成本 | 失败模式 | 与现有约束的关系 | 结论 |
|---|---|---|---|---|---|
| **A 单 Worker 部署约束** | 单进程时全局成立；多进程时显式禁止激活 | 零新增基础设施 | 依赖部署纪律；横向扩展能力受限 | 完全符合 D-005 模块化单体与「不引入 Redis/数据库」 | **推荐（短期唯一可行）** |
| B 共享存储分布式限流 | 多进程/多实例下全局成立 | 需要**新增基础设施**（共享计数器存储） | 存储不可用时限流行为不确定；引入网络依赖；Redis 已被明令禁止 | 需要独立决策 + 基础设施授权 | 不采纳（J2） |
| C 独立 Egress Gateway | 由单一进程拥有全部外部请求，天然全局 | 新增可部署组件 + IPC + 新故障面 | Gateway 成为单点；部署复杂度上升 | 与「不过度设计/模块化单体」冲突 | 不采纳（J2） |

### 9.3 推荐方案：显式单进程部署约束（方案 A）

必须同时落地的四条（缺一不可）：

1. **部署约束**：每 `(provider, account)` 在任一时刻只允许 1 个应用进程处理 Provider 请求；禁止 `uvicorn --workers > 1`、禁止多副本/多实例共享同一账号。
2. **启动断言**：应用启动时校验「已声明部署进程数」，与配置值不一致即拒绝启用 Provider 能力（fail closed，不得静默降级为「尽力限流」）。
3. **运维手册**：把该约束写入部署文档与扩容前置检查；扩容必须先回到 DEC-6 重新决策。
4. **可观测性**：命中限流必须可识别（现有 `PROVIDER_RATE_LIMITED` 已足够；不得记录凭证或完整 tracking number）。

> 说明：进程数无法在应用内 100% 可靠探测，所以「部署约束 + 显式声明 + 断言」的组合是**已知的不完美但最小**方案；其残余风险必须在运维文档中如实声明，不得声称已完全消除。

### 9.4 当前生产激活限制

在 DEC-6 获批且上述四条落地之前：

| 限制 | 内容 |
|---|---|
| 真实 Provider 激活 | **禁止**（Batch I 本已 `BLOCKED`，本项为额外的前置治理条件） |
| 多 worker / 多实例部署 | **禁止**与真实 Provider 同时启用 |
| 限流器替换 | **禁止**擅自替换为分布式实现 |
| Redis | **禁止**引入（无论是否用于限流） |
| 熔断器 | 仍未冻结，不得引入（审计 F-5） |
| 429 处理 | 保持现有分类与「不自动重试」策略 |

### 9.5 是否需要新增基础设施

- 方案 A：**不需要**。J2 不新增任何依赖、不新增服务、不新增存储。
- 方案 B / C：**需要**，且必须由用户显式批准（含基础设施选型；Redis 仍然禁止，除非另有明确例外的独立决定）。

### 9.6 DEC-6 结论

- 推荐：**方案 A（显式单进程部署约束）**；B/C 仅作为未来升级路径登记，不在 J2 范围。
- 批准状态：**`DEFERRED / NOT_APPROVED`（Task 048）**；AP-6.1～AP-6.4 未获批准，单进程内存限流与多 worker/多实例禁令继续有效。

---

## 10. 真实 SKU 包装数据与材料数据就绪性核查

### 10.1 分类核查结果

数据源：`backend/data/skus.json`（9 条商品记录）、`backend/data/skus_raw.json`（溯源）、`backend/data/orders.json`、`backend/data/tracking.json`。本任务只读、只统计结构，不输出客户信息。

| 数据类别 | 现有内容 | 覆盖 | 是否可用于包装估算 |
|---|---|---|---|
| **A. 商品物理数据** | `weight_g`、`dimensions_mm{length,width,height}`、`volume_mm3`、`volumetric_gross_weight_kg`、`max_storage_per_container` | **9/9 SKU 全部具备** | **否**。商品数据不得充当包装数据（D-019、契约 §4.4 与 §16.2） |
| **B. 单件包装数据** | 无：无包装三维、无包装后重量、无单件包装形式（carton/satchel）、无方向、无易碎、无堆叠、无危险品 | **0/9** | **否**（完全缺失） |
| **C. 包装材料数据** | 无：无材料 ID 目录、无内外尺寸、无皮重、无最大毛重、无材质类型、无可用状态、无危险品许可 | **0 条** | **否**（完全缺失） |
| **D. 业务规则** | 契约已冻结外壳（ruleset ID/version/生效窗口/source_revision/三类记录）、D-020 拆分混装模型、D-021 版本化只读 | 外壳 100%，**内容 0%** | 结构可用，内容缺失 |
| **E. 尚未取得的真实数据** | 单件包装规格、材料目录、能力参数、获批 ruleset、验收签字与数据来源 | 0 | 阻塞生产 |

**逐项核实（7 项包装规格）**：

| 包装规格项 | 现状 | 判定 |
|---|---|---|
| 单件包装长/宽/高 | 只有**商品**三维 | 缺失（禁止直拷） |
| 包装后重量（含包装增重） | 无 | 缺失 |
| 单位声明（包装侧） | 只有商品侧 mm/g | 缺失 |
| 方向（可旋转/仅直立/固定） | 无字段、无数据 | 缺失（且 schema 无字段 → DEC-2） |
| 易碎 | 无字段、无数据 | 缺失（DEC-2） |
| 堆叠 | 无字段、无数据 | 缺失（DEC-2） |
| 危险品/特殊运输限制 | 无字段、无数据 | 缺失（DEC-2） |
| 材料内外尺寸 / 皮重 / 最大毛重 / 容量 | 无目录 | 缺失（DEC-4） |
| 数据来源与 provenance | 无包装侧来源声明 | 缺失 |

### 10.2 严禁等同声明（边界重申）

| 禁止 | 依据 |
|---|---|
| 用 `Product.weight_g` 当包装后重量 | D-019；契约 §4.4、§16.2 |
| 用 `Product.dimensions_mm` 当 Package 外尺寸 | 同上；审计 §4.3 |
| 用 `Product.volume_mm3` 当 Package 内腔容量 | 同上 |
| 用 `volumetric_gross_weight_kg` 当 chargeable weight | 契约 §6.2（口径无证据且不符合统一 250 kg/m³ 关系） |
| 用 `max_storage_per_container` 当运输包装容量 | 仓储语义，非运输包装；审计 §4.1 |
| 用 Tracking Group 数量推断 Package 数量 | D-016；契约 §4.1 |

### 10.3 真实数据缺失清单

| ID | 缺失项 | 单位/精度 | 阻塞对象 | 提供方 | 对应既有登记 |
|---|---|---|---|---|---|
| DM-01 | 9 个 SKU 的单件包装外三维（长/宽/高） | mm，Decimal 字符串，>0 | J2 生产启用 | 仓储/运营 + 商品主数据所有者 | MI-01 |
| DM-02 | 9 个 SKU 的包装后重量（单件，含包装） | g，Decimal 字符串，>0 | J2 生产启用 | 同上 | MI-01 |
| DM-03 | 9 个 SKU 的单件包装形式（carton/satchel/…） | 封闭枚举 | J2 生产启用 | 仓储 | MI-01（细化） |
| DM-04 | 每 SKU 方向策略 | `any / upright_only / fixed` | J2-C/E | 业务 + 合规 | MI-04 / DEC-2 |
| DM-05 | 每 SKU 易碎等级 | `none / fragile / very_fragile` | J2-C/E | 业务 + 合规 | MI-04 / DEC-2 |
| DM-06 | 每 SKU 堆叠约束（是否可堆叠/最大层数/最大顶载） | bool / int / g | J2-C/E | 业务 + 合规 | MI-04 / DEC-2 |
| DM-07 | 每 SKU 危险品标识与分类目录引用 | bool + opaque ref | J2-C/E（合规关键） | 业务 + 合规 | MI-04 / DEC-2 |
| DM-08 | 每 SKU 兼容材料白名单 | 材料 ID 列表 | J2-C/D | 仓储/包装工程 | MI-01/MI-02 |
| DM-09 | 材料目录：material_id、材质类型 | 字符串 / 封闭枚举 | J2-D | 包装采购/仓储 | MI-02 |
| DM-10 | 材料内尺寸与外尺寸 | mm，Decimal，逐边关系合法 | J2-D | 包装供应商/仓储 | MI-02 |
| DM-11 | 材料皮重 | g，Decimal，>0 | J2-D | 同上 | MI-02 |
| DM-12 | 材料最大毛重 | g，Decimal，> 皮重 | J2-D | 同上 | MI-02 |
| DM-13 | 材料能力：是否危险品许可 / 是否缓冲 / 支持方向 | bool / bool / 枚举 | J2-C/D | 同上 | MI-02（细化） |
| DM-14 | 材料可用状态（active/retired）与生效期 | 枚举 + UTC | J2-D/F | 仓储/治理 | MI-02（细化） |
| DM-15 | PackingPolicy 具体取值（每 scope 一条或明确兜底） | DEC-1 schema | J2-B | 业务 + 架构 | MI-05 |
| DM-16 | 获批 ruleset：ID / version / effective_from / source_revision | 契约 §5.1 | J2-F/G | 业务 + 配置治理 | MI-03 |
| DM-17 | 数据来源与采集方法声明（逐字段 provenance） | 文本引用 | J2-G 验收 | 数据所有者 | 新增（Task 047） |
| DM-18 | 数据验收签字（Validator + Approver） | 审计引用 | J2-G 激活 | 治理角色 | MI-16 / DEC-5 |
| DM-19 | 覆盖未来新增 SKU 的补录责任与流程 | 流程文档 | 长期运行 | 业务 | 新增（Task 047） |
| DM-20 | 承运商计费重量/体积重量规则证据（cubing factor 等） | 合同/官方文档 | Quote 计算（J3） | 承运商合同方 | MI-14 / MI-15 |

### 10.4 建议数据模板

以下模板字段与 DEC-1/DEC-2/DEC-4 推荐 schema 对齐。**模板只给结构与类型，不填任何真实值**；`<...>` 为占位标记，提交时必须由数据所有者在**批准后的正式文件**中填写，且不得写入四个业务 JSON（D-021）。

**模板 A：SKU 单件包装规格**

```json
{
  "template": "sku-packaging-spec/v1",
  "synthetic": false,
  "source_revision": "<approved-source-reference>",
  "collected_by_ref": "<role-ref-no-pii>",
  "records": [
    {
      "sku": "<sku-from-skus.json>",
      "packed_unit_dimensions_mm": {
        "length_mm": "<decimal-string>",
        "width_mm": "<decimal-string>",
        "height_mm": "<decimal-string>"
      },
      "unit_weight_g": "<decimal-string>",
      "packaging_form": "<carton|satchel|padded_bag|tube|other-approved>",
      "orientation_policy": "<any|upright_only|fixed>",
      "fragility": "<none|fragile|very_fragile>",
      "stacking": {
        "stackable": "<bool>",
        "max_stack_units": "<int|null>",
        "max_top_load_g": "<decimal-string|null>"
      },
      "hazardous": "<bool>",
      "hazard_class_ref": "<approved-catalogue-ref|null>",
      "compatible_material_ids": ["<material-id>"],
      "handling_class": "<approved-class|null>"
    }
  ]
}
```

**模板 B：包装材料目录**

```json
{
  "template": "package-material-catalogue/v1",
  "synthetic": false,
  "source_revision": "<approved-source-reference>",
  "records": [
    {
      "material_id": "<stable-id>",
      "material_type": "<carton|satchel|padded_bag|tube|other-approved>",
      "inner_dimensions_mm": {"length_mm": "<decimal>", "width_mm": "<decimal>", "height_mm": "<decimal>"},
      "outer_dimensions_mm": {"length_mm": "<decimal>", "width_mm": "<decimal>", "height_mm": "<decimal>"},
      "tare_weight_g": "<decimal-string>",
      "max_gross_weight_g": "<decimal-string>",
      "hazmat_approved": "<bool>",
      "cushioned": "<bool>",
      "orientation_supported": "<any|upright_only>",
      "availability_status": "<active|retired>",
      "selection_priority": "<int|null>"
    }
  ]
}
```

**模板 C：PackingPolicy + ruleset 发布清单**

```json
{
  "template": "packaging-ruleset/v1",
  "synthetic": false,
  "ruleset_id": "<stable-id>",
  "version": "<immutable-version>",
  "effective_from": "<UTC ISO-8601>",
  "effective_to": "<UTC ISO-8601|null>",
  "source_revision": "<approved-source-reference>",
  "sku_specs_source": "<approved file ref>",
  "materials_source": "<approved file ref>",
  "policies": [
    {
      "policy_id": "<stable-id>",
      "priority": "<int>=0>",
      "scope": "<sku|handling_class|general>",
      "sku": "<sku|null>",
      "handling_class": "<class|null>",
      "allocation_strategy": "<sequential_first_fit|best_fit_decreasing>",
      "material_selection": "<smallest_inner_volume|priority_order>",
      "allow_split": "<bool>",
      "max_units_per_package": "<int|null>",
      "max_packages_per_order": "<int|null>",
      "allow_mixed_sku": "<bool>",
      "max_skus_per_package": "<int|null>",
      "fragile_mixing": "<allow|single_sku_only|alone_only>",
      "max_package_gross_weight_g": "<decimal|null>",
      "max_package_outer_dimensions_mm": "<dimensions|null>"
    }
  ]
}
```

**模板 D：Release 与审计记录**

```json
{
  "template": "packaging-release/v1",
  "release_id": "<stable-id>",
  "release_revision_id": "<immutable-id>",
  "configuration_scope": "packaging",
  "ruleset_versions": ["<ruleset_id>@<version>"],
  "created_by_ref": "<role-ref>",
  "created_at": "<UTC ISO-8601>",
  "validated_by_ref": "<role-ref>",
  "validated_at": "<UTC ISO-8601>",
  "validation_summary_ref": "<audit ref>",
  "approved_by_ref": "<role-ref>",
  "approved_at": "<UTC ISO-8601>",
  "approval_ref": "<audit ref>",
  "activation": {
    "activated_by_ref": "<role-ref>",
    "activated_at": "<UTC ISO-8601>",
    "activation_audit_ref": "<audit ref>",
    "reason": "<text>"
  }
}
```

### 10.5 真实数据验收标准

数据只有**同时**满足以下全部条件才可进入生产 ruleset：

1. **覆盖完整**：9/9 现有 SKU 均有单件包装规格；材料目录覆盖全部 `compatible_material_ids` 引用；无悬空引用。
2. **单位与类型**：全部数值为 Decimal 字符串，mm / g；无 float、无科学计数法歧义、无 `null` 冒充 0。
3. **几何一致性**：`volume_mm3 == L×W×H`（精确）；`outer ≥ inner` **逐边**；`max_gross_weight_g > tare_weight_g`；`tare_weight_g > 0`。
4. **来源可追溯**：每个字段有采集来源与采集方法；提交方声明「非由商品数据推算」。
5. **非回填检测**：若包装三维与 `skus.json` 的 `dimensions_mm` 完全一致，必须附**采集证据**说明这是实测结果而非复制；无证据即拒收。
6. **包装后重量独立**：`unit_weight_g` 必须包含包装增重；若与 `weight_g` 完全一致同样需要证据。
7. **约束完整**：方向、易碎、堆叠、危险品四项对每个 SKU 都有显式取值（含「无限制」的显式声明），不得留空由系统猜默认。
8. **危险品合规**：危险品标识与分类引用来自批准目录；工程不得自行推断。
9. **规则自洽**：policy 匹配覆盖全部 SKU（或显式 `general` 兜底）；scope/priority 无二义；policy 上限不宽于材料硬上限。
10. **治理签署**：Validator 与 Approver 均非 Author；`approval_ref` 与 `activation_audit_ref` 可查。
11. **无敏感数据**：文件不含客户信息、追踪编号、凭证。
12. **可复现**：同一文件 + 同一 ruleset version ⇒ 同一 `input_fingerprint` 与同一 `packages` 序列。

任一条不满足 ⇒ 该 ruleset **不得激活**；应用继续 `PACKAGE_RULES_NOT_CONFIGURED`。

### 10.6 数据到位后的处理流程

```text
提交（Author）
  -> 结构校验（模板 schema + 单位 + Decimal）
  -> 交叉校验（SKU 覆盖、材料引用、几何一致性、非回填检测）
  -> 语义校验（policy 唯一匹配、上限不放宽）
  -> Validator 签署
  -> Approver 审批 -> 生成不可变 Release
  -> 原子激活 Active 指针（Activator）
  -> 生产验证（真实订单详情 + 人工复核样例）—— 此步才可称为「真实数据验证」
```

**红线**：在最后一步完成之前，任何关于包装能力的对外表述都不得使用「已验证/生产就绪」措辞。

### 10.7 保留的 Batch I 外部证据缺口

以下缺口与 Task 044 记录**完全一致**，本任务未改变、未补齐、未调用任何真实 Provider：

1. 无真实 Provider/Account/Product/Mapping Revision；
2. 无获批 Active Configuration Release；
3. 无服务端凭证与账号权限，无 Get Accounts 回执；
4. 无 testbed 访问与调用授权；
5. 3 个 tracking group 中 2 个仍只有合并 carrier 文本（`StarTrack / Australia Post`），无显式 Provider 归属；
6. StarTrack 账号「不以 0 开头」规则、Australia Post 账号左补零归一化归属仍为 `NEEDS_EVIDENCE`；
7. Provider/Product GST、cubing factor、金额精度证据仍为 `NEEDS_EVIDENCE`。

---

## 11. Batch J2 实施计划

### 11.1 覆盖矩阵（任务要求的 11 个领域）

| 要求领域 | 承载批次 | 是否依赖真实数据 |
|---|---|---|
| Domain Model | J2-A、J2-B | 否（结构） |
| Packaging Rules | J2-B | 否（schema/loader）；生产内容依赖 DM-01～DM-18 |
| Configuration Release | J2-F | 否（机制）；激活依赖 DM-16/DM-18 |
| 生产级装箱算法 | J2-C | 否（算法）；参数与规则依赖 DM-15/DM-16 |
| Material Selection | J2-D | 否（机制）；目录依赖 DM-09～DM-14 |
| OrderService | J2-E | 否 |
| API / OpenAPI | J2-E | 否 |
| Frontend | J2-E | 否 |
| Runtime Validation | J2-E | 否 |
| Evaluation Dataset | J2-C（合成基准）+ J2-G（真实基准） | 行为集：否；生产集：**是** |
| Regression / Performance / Security Tests | 各批次内 + J2-H 汇总门禁 | 否 |

### 11.2 批次划分

#### J2-A — 决策落地与契约增补

| 项 | 内容 |
|---|---|
| 依赖 | 用户书面批准 DEC-1～DEC-6（至少 DEC-1～DEC-4） |
| 范围 | 更新 `docs/DECISIONS.md`（新决策编号由用户指定）、`docs/PHASE6_CONTRACT.md` §5 与新治理小节、`AGENTS.md` 冻结规则、`docs/ARCHITECTURE.md` 边界 |
| 不做 | 任何代码、任何数据文件 |
| 验收 | 文档与 DEC 批准内容逐条可对照；无 D 编号冲突；Markdown/链接检查通过 |
| BLOCKED | 未获批准则整批不得开始（本任务是它的前置，不是它的替代） |

#### J2-B — Packaging Rules schema 与 Reader

| 项 | 内容 |
|---|---|
| 依赖 | J2-A |
| 范围 | `SkuPackagingSpec.handling`、`PackageMaterialSpec` 能力字段、`PackingPolicy` 完整 schema、加载期交叉校验（逐边尺寸、上限不放宽、policy 唯一性/可达性）、file-backed 只读 `PackagingRuleSetReader` |
| 不做 | 不激活任何生产 ruleset；默认应用继续无 ruleset |
| 验收 | schema 拒绝矩阵全覆盖；同 ID 同内容幂等、不同内容拒绝；生效窗口 UTC；synthetic 隔离保留 |
| BLOCKED | J2-A 未完成 |

#### J2-C — 生产级装箱算法（DEC-3）

| 项 | 内容 |
|---|---|
| 依赖 | J2-B |
| 范围 | Stage 0～6 实现、`best_fit_decreasing` 策略、方向枚举、拆分/混装裁决、确定性排序键、fail-closed 矩阵、性能基准、合成黄金评估集（≥12 场景） |
| 不做 | 不引入求解器/新依赖；不承诺最优装载；不把合成集称为生产验证 |
| 验收 | 守恒、确定性重跑、禁止商品数据读取、fail-closed 全矩阵、性能预算达成 |
| BLOCKED | J2-B 未完成；`allocation_strategy` 未批准 |

#### J2-D — 材料选择（DEC-4）

| 项 | 内容 |
|---|---|
| 依赖 | J2-B、J2-C |
| 范围 | F1～F8 硬过滤、两种排序策略、8 条禁止 fallback 的拒绝用例、材料能力冲突处理 |
| 不做 | 不实现成本最优化；不实现多材料混装 |
| 验收 | 每一条禁止 fallback 都有独立负向测试；冲突场景 fail closed |
| BLOCKED | J2-B/C 未完成 |

#### J2-E — OrderService / API / OpenAPI / Frontend / Runtime Validation

| 项 | 内容 |
|---|---|
| 依赖 | J2-C、J2-D |
| 范围 | 详情编排接入新估算结果（`packages` 结构不变，契约 §9.3）；API Mapper/Schema 保持既有投影；OpenAPI 一致；前端 Package 展示与降级文案；前端 runtime validator 交叉校验 |
| 不做 | 不改变 API 路径/envelope/Money；不把 constraints/capacity/policy 暴露给前端；不改变列表行为 |
| 验收 | Backend/API/Frontend schema 一致性；D-030/D-031 回归不破；前端不重算金额 |
| BLOCKED | J2-C/D 未完成；Phase 5 兼容项需协调发布 |

#### J2-F — Packaging 配置治理（DEC-5）

| 项 | 内容 |
|---|---|
| 依赖 | J2-A；建议与 J2-B 并行 |
| 范围 | `PackagingConfigurationCatalog`、`PackagingRelease`、`PackagingActivePointer`、原子激活、rollback=重新激活、append-only 审计、请求级 pinning、file-backed 载体 |
| 不做 | 不引入数据库/Redis；不与 Tracking 激活连锁；不做管理 UI（超出本阶段） |
| 验收 | 同 ID 不可变、原子切换失败保持原 Active、回滚不改历史、审计字段齐全、在途请求不受切换影响 |
| BLOCKED | AP-5.x 未批准；存储载体未批准 |

#### J2-G — 真实数据接入与生产启用验证

| 项 | 内容 |
|---|---|
| 依赖 | J2-B～J2-F 完成 + DM-01～DM-18 全部到位并签署 |
| 范围 | 导入真实规则数据、按 §10.5 验收、激活 Release、真实订单结构验证、人工复核 |
| 不做 | 不调用真实 Provider（仍属 Batch I/K 授权范围） |
| 验收 | §10.5 的 12 条全部满足；抽样订单包装结果经业务复核签字 |
| BLOCKED | **当前 `BLOCKED`**：无任何真实包装数据、材料目录或获批 ruleset |

#### J2-H — Regression / Performance / Security 门禁汇总

| 项 | 内容 |
|---|---|
| 依赖 | J2-B～J2-F |
| 范围 | 全量回归、确定性基准、性能门禁、安全扫描（无 PII/凭证/追踪号）、Markdown/OpenAPI/决策编号检查、业务 JSON SHA-256 复核 |
| 不做 | 不修改冻结实现以达到门禁 |
| 验收 | 全部门禁绿；业务 JSON 哈希不变；无新增依赖（除非另获批准） |
| BLOCKED | 前置批次未完成 |

### 11.3 依赖图与推荐顺序

```text
批准 DEC-1～DEC-6
   |
J2-A (契约固化)
   |\
   | +--> J2-F (配置治理)  ──┐
   v                          |
J2-B (Rules schema/Reader)    |
   |                          |
J2-C (生产算法)               |
   |                          |
J2-D (材料选择)               |
   |                          |
J2-E (Order/API/前端)         |
   |                          |
   +--------------------------+
   |
J2-H (回归/性能/安全门禁)
   |
J2-G (真实数据接入，当前 BLOCKED)
```

**并行建议**：J2-F 可与 J2-B 并行；J2-C 与 J2-D 紧耦合需串行；J2-E 可与 J2-G 的数据采集窗口重叠但不依赖其完成。

### 11.4 优先推进不依赖真实数据的工作

可以立即（J2-A 完成后）推进：J2-B、J2-C、J2-D、J2-E、J2-F、J2-H 的**机制与行为**部分，全部使用明确标记的 synthetic fixtures，并满足：

- synthetic ruleset 不得被默认激活（默认应用保持 `PACKAGE_RULES_NOT_CONFIGURED`）；
- synthetic 材料不得声称真实库存；
- synthetic 规格不得写入四个业务 JSON；
- 测试结论不得表述为「真实包装验证」。

### 11.5 不允许 Synthetic 验证冒充生产验证

| 允许的表述 | 禁止的表述 |
|---|---|
| 「合成夹具下行为符合契约」 | 「包装能力已验证」 |
| 「算法确定性/守恒性已测试」 | 「生产装箱算法已验收」 |
| 「fail-closed 路径已覆盖」 | 「包装功能已上线」 |
| 「配置治理机制已实现」 | 「配置治理已生效」 |

生产验证的唯一判定：§10.5 十二条 + §10.6 最后一步完成。

### 11.6 门禁（每个批次必须通过）

1. Backend 全量 pytest；Frontend Vitest + TypeScript strict + build + lint；
2. Ruff check / format check；`pip check`；`npm ls` / `npm audit`；
3. `git diff --check`；Markdown 围栏配对与相对链接可达；
4. D 编号唯一性（不得出现未批准的新编号）；
5. OpenAPI/Pydantic 一致性；
6. 敏感信息扫描（凭证/Authorization/tracking number/PII）；
7. 四个业务 JSON SHA-256 未变；
8. 本批次专项验收（见各批次）。

---

## 12. Batch I 外部阻塞状态（未变）

| 项 | 状态 | 说明 |
|---|---|---|
| Batch I 离线实现 | ✅ 完成并通过独立复审（`BATCH_I_REVIEW_PASS`，Checkpoint `6ccdc5f`） | 不因本任务改变 |
| 真实 Provider 调用 | ❌ 未进行 | 本任务零真实请求 |
| Provider/Account/Product/Mapping Revision | ❌ 未提供 | `BLOCKED_EXTERNAL_INPUT` |
| 获批 Active Configuration Release | ❌ 未提供 | `BLOCKED_EXTERNAL_INPUT` |
| 服务端凭证与账号权限 | ❌ 未提供 | `BLOCKED_EXTERNAL_INPUT` |
| Get Accounts 回执 | ❌ 未提供 | `BLOCKED_EXTERNAL_INPUT` |
| testbed 授权 | ❌ 未提供 | `BLOCKED_EXTERNAL_INPUT` |
| 3 个 tracking group 的显式 Provider 归属 | ❌ 未提供（2 组为合并文本） | `BLOCKED_EXTERNAL_INPUT` |
| 真实 Shipping Quote | ❌ 未实现 | D-015 语义保持不变 |
| Batch I 总体 | `PARTIALLY_COMPLETE` | Phase 6 仍 `IN_PROGRESS` |

本任务**新增**的 Batch I 相关治理条件（DEC-6）：真实 Provider 激活前必须满足单进程约束。

---

## 13. D-001～D-035 契约一致性核查

### 13.1 逐项结论

| 决策 | 主题 | 本决策包的关系 | 是否被改变 |
|---|---|---|---|
| D-001 | GST 采用 HTML v2 | 无关（金额链不变） | 否 |
| D-002 | 第二笔订单编号 | 无关 | 否 |
| D-003 | JSON 数据源 | DEC-5 的 ruleset 载体仍不得写入四个业务 JSON | 否 |
| D-004 | Decimal 货币计算 | 包装重量/尺寸全程 Decimal；不涉金额计算 | 否 |
| D-005 | 模块化单体 | DEC-6 方案 C（Egress Gateway）因此不采纳；无微服务 | 否 |
| D-006 | TNT Bonus | 无关 | 否 |
| D-007 | 物流结果不得伪造 | 包装 fail-closed 遵循同精神 | 否 |
| D-008 | 原始/标准化数据分离 | 包装数据不得写入商品主数据 | 否 |
| D-009 | 客户数据与凭证安全 | 模板与审计记录禁止 PII/凭证 | 否 |
| D-010 | 商品缺失数据处理 | 无关 | 否 |
| D-011 | Money Decimal String | API 投影不变 | 否 |
| D-012 | Tracking/Shipping 状态独立 | 包装失败只降级包装区域 | 否 |
| D-013 | 统一状态语义 | 包装沿用 `available`/`unavailable` | 否 |
| D-014 | 订单 API v1 契约 | API 路径/envelope 不变 | 否 |
| D-015 | 初始 Shipping Quote unsupported | 完全不变 | 否 |
| D-016 | Tracking Group ≠ Package | DEC-3 禁止从 group 推断 Package | 否 |
| D-017 | unavailable zero fallback | 不变 | 否 |
| D-018 | all-or-nothing | DEC-3 强制整单 fail closed | 否 |
| D-019 | Package 使用可追溯 rules | DEC-1～DEC-4 是 D-019 的**落地细化**，不改变其选择 | 否 |
| D-020 | 拆分与混装由 Ruleset 控制 | DEC-1 为「ruleset 控制」提供字段级表达 | 否 |
| D-021 | 独立只读版本化配置 | DEC-5 为其提供治理实现机制 | 否 |
| D-022 | 含 GST total cost | 无关 | 否 |
| D-023 | 显式 Provider mapping | 无关 | 否 |
| D-024 | 公共 reason code 稳定 | DEC-1/3/4 明确**不新增**公共 code | 否 |
| D-025 | 详情报价、列表 not_requested | 列表不涉包装估算 | 否 |
| D-026 | 无历史、无跨请求缓存 | DEC-5 存储不得成为 Quote History/Cache；DEC-3 禁止跨请求缓存 | 否 |
| D-027 | 仅 Contract Price | 无关 | 否 |
| D-028 | normalized/raw/unknown | 无关 | 否 |
| D-029 | Provider 精度规则 | 无关（DEC-3 不计算 Provider 金额） | 否 |
| D-030 | 列表 Total before shipping | 不变 | 否 |
| D-031 | provider-null 投影 | 不变 | 否 |

### 13.2 新增正式决策（Task 048，D-032～D-035）

| 正式决策 | 来源提案 | 主题 | 状态 |
|---|---|---|---|
| D-032 | DEC-1 | `PackingPolicy` 结构化封闭 schema、匹配优先级、加载期校验、零匹配 fail closed | `APPROVED / FROZEN` |
| D-033 | DEC-2 | 约束三处归属、材料/SKU 新增字段、`EffectiveConstraintView` 合并规则、商品事实隔离 | `APPROVED / FROZEN` |
| D-034 | DEC-3 | Stage 0～6、排序键、方向枚举、容量/重量、拆分混装裁决、性能边界、整单 fail closed | `APPROVED / FROZEN` |
| D-035 | DEC-4 | F1～F8 硬过滤、两种排序策略、冲突处理、零候选、8 条禁止 fallback | `APPROVED / FROZEN` |

### 13.3 核查结论

- **D-001～D-031 共 31 项，全部保持原义**；本任务未修改 `docs/DECISIONS.md`、未新增、未替代、未回写任何决策。
- **Task 047 没有新增任何正式 D 编号（当时仍为 D-001～D-031）**；DEC-1～DEC-6 是提案/需求编号。**Task 048 依据用户批准新增 D-032～D-035，与 DEC-1～DEC-4 一一对应**；DEC-5/DEC-6 未形成 D 决策（§17）。
- 契约不变量（§2.3 几何/重量、§4.1 守恒、§4.4 服务边界、§5.2 确定性、§9.3 投影、§9.4/D-031、§16.2 禁止项）在新方案下**全部继续成立**。
- 唯一的「扩展」性质是 schema 字段增加：DEC-1/DEC-2 的包装字段已由 Task 048 写入契约（D-032/D-033）；DEC-5 的治理结构**仍未生效**（暂缓）。

---

## 14. Git 状态（Task 047 执行时）

| 项 | 执行前 | 执行后 |
|---|---|---|
| HEAD | `537e165` | `537e165`（未提交任何内容） |
| Branch | `main` | `main` |
| 暂存区 | 空 | 空 |
| Remote | 无 | 无（未配置、未 Push） |
| Tag / Stash | 空 | 空 |

变更文件（预期与最终一致）：

| 文件 | 类型 |
|---|---|
| `docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md` | 新增 |
| `docs/PROJECT_PLAN.md` | 更新（Task 047 记录与状态） |
| `docs/PHASE6_EXTERNAL_READINESS_AUDIT.md` | 最小追记（仅因 DEC-5/DEC-6 与 J2 阻塞清单需保持一致） |

未修改：`docs/DECISIONS.md`、`docs/PHASE6_CONTRACT.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、全部 Backend/Frontend 代码与测试、API/OpenAPI、四个业务 JSON、依赖与锁文件。

实际执行后的 diff 与哈希复核结果见 §16。Task 048 执行后的工作区状态见 §17.4。

---

## 15. 下一步实施建议

1. **用户决策（最高优先）**：逐条审阅并批复 §3 的 AP 清单。建议最小可推进组合为 **DEC-1 + DEC-2 + DEC-3 + DEC-4**（解锁 J2-B～J2-E 的机制实现），DEC-5 与 DEC-6 可随后批复（分别解锁 J2-F 与生产激活）。
2. **授权契约增补任务**：DEC 获批后，以单独任务更新 `DECISIONS.md` / `PHASE6_CONTRACT.md` / `AGENTS.md` / `ARCHITECTURE.md`；本决策包不得被当作契约本身。
3. **并行启动数据采集**：按 §10.4 模板向仓储/运营/采购/合规发起 DM-01～DM-18 采集；采集与工程实现并行，不互相阻塞。
4. **按 J2-A → J2-B → J2-C/D → J2-E → J2-F → J2-H 推进**，J2-G 保持 `BLOCKED` 直至数据与签署到位。
5. **保持 Batch I 阻塞状态**，不因包装工作推进而表述为外部集成就绪；真实 Provider 激活仍受 DEC-6 单进程约束约束。

### 15.1 最终状态

```text
DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL   # Task 047 交付时状态（历史）
```

**Task 048 更新**：DEC-1～DEC-4 已获批准并正式化为 D-032～D-035；DEC-5/DEC-6 暂缓。本决策包的批准状态更新为：

```text
DEC_1_TO_4_APPROVED__DEC_5_6_DEFERRED
```

---

## 16. 验证记录

本任务未运行全量测试或构建（任务说明不需要）。以下为文档与仓库完整性检查的**实际执行结果**。

### 16.1 Git

| 检查 | 命令 | 结果 |
|---|---|---|
| HEAD 未变 | `git rev-parse HEAD` | `537e165d59eee484149dccbe562020d774396dc1` |
| Branch | `git branch --show-current` | `main` |
| 变更范围 | `git status --porcelain` | 3 项：`M docs/PHASE6_EXTERNAL_READINESS_AUDIT.md`、`M docs/PROJECT_PLAN.md`、`?? docs/PHASE6_BATCH_J2_DECISION_PACKAGE.md` |
| diff 统计 | `git diff --stat` | 2 files changed, +45 / −4（审计 +18/−0、计划 +27/−4；不含新增文件） |
| 空白/冲突标记 | `git diff --check` | 通过（已修正审计文档 EOF 多余空行） |
| 暂存区 | `git status --porcelain` | 空（未 `git add`） |
| Remote / Tag / Stash | `git remote -v`、`git tag`、`git stash list` | 均为空；未 Push |

### 16.2 业务 JSON 完整性（执行后复核）

| 文件 | SHA-256 | 与 §1.2 相比 |
|---|---|---|
| `backend/data/orders.json` | `8305fba3856a14a2e9e7ff4798f2e2da14278423bc63293608ef7f56a558ddeb` | 一致 |
| `backend/data/skus.json` | `fa71b78879b6cfeea98460487ad048f44e0458dba9b06391066382fb15f0f942` | 一致 |
| `backend/data/skus_raw.json` | `44b0db54c736891e23478f9bf412984d9e5006d9d0a1d286671b7128134ac3c5` | 一致 |
| `backend/data/tracking.json` | `4d79e67c730f3c5dbfbd1ec66dd9e29e5b394fec0467634af55631ff4859c316` | 一致 |

### 16.3 文档结构

| 检查 | 方法 | 结果 |
|---|---|---|
| Markdown 结构 | 代码围栏配对（30 个围栏标记，全部成对） | 通过 |
| 标题层级 | `## 0`～`## 16` 顺序检查 | 通过 |
| 表格一致性 | 48 个表格，逐行校验未转义管线数与表头一致 | 通过（修正 4 处单元格内 `int\|null` 等管线转义） |
| 仓库路径引用 | 提取 18 个 `backend/`/`docs/`/`frontend/` 路径并逐一核验存在 | 全部存在 |
| 决策编号 | 全文 `D-0xx` 扫描（Task 047 执行时） | 当时仅 D-001～D-031；Task 048 后新增 D-032～D-035（见 §17.3） |

### 16.4 安全与状态一致性

| 检查 | 方法 | 结果 |
|---|---|---|
| 凭证/令牌 | 正则扫描 Bearer、Authorization 头、`api_key=`、AWS key、`sk-` 令牌 | 未发现（仅出现描述性文字） |
| 客户 PII | 邮箱、澳洲手机号模式 | 未发现 |
| 真实 tracking number | Australia Post / StarTrack 编号形状 | 未发现 |
| DEC 批准状态 | 扫描「DEC-x … 已批准/approved」断言（Task 047 执行时） | 当时无实际批准表述；Task 048 后 DEC-1～DEC-4 为 `APPROVED`、DEC-5/6 为 `DEFERRED`（见 §17） |
| 冻结文件未改 | `git status` 交叉核对 | `docs/DECISIONS.md`、`docs/PHASE6_CONTRACT.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、Backend/Frontend 实现、API/OpenAPI、依赖与锁文件均未改动 |

### 16.5 未执行的检查（如实声明）

- 未运行 Backend pytest / Frontend Vitest / TypeScript / build / lint / `pip check` / `npm audit`：本任务为纯文档交付，且任务说明明确不需要运行全量测试或构建。
- 未做真实 Provider 调用、未做 testbed 验证、未做真实包装数据验证（数据不存在）。
- 未做浏览器渲染验证：Markdown 表格/围栏通过结构校验，未在渲染器中目视确认。

---

## 17. Task 048 批准与正式化记录

### 17.1 批准范围

| 提案 | 主题 | 批准结果 | 正式决策 |
|---|---|---|---|
| DEC-1 | Structured `PackingPolicy` Schema | `APPROVED` | D-032 |
| DEC-2 | Constraint Ownership & `EffectiveConstraintView` | `APPROVED` | D-033 |
| DEC-3 | Deterministic Best-Fit Decreasing Packing Algorithm | `APPROVED` | D-034 |
| DEC-4 | Packaging Material Selection Strategy | `APPROVED` | D-035 |
| DEC-5 | Packaging Configuration Governance | `DEFERRED / NOT_APPROVED` | 未形成 D 决策 |
| DEC-6 | Multi-process Global Rate Limiting | `DEFERRED / NOT_APPROVED` | 未形成 D 决策 |

批准范围严格限定为 §2.2 矩阵与 §3 AP 清单中的 DEC-1～DEC-4 内容（AP-1.1～AP-1.7、AP-2.1～AP-2.10、AP-3.1～AP-3.6、AP-4.1～AP-4.4）。DEC-5/DEC-6 的 AP-5.x/AP-6.x 条款**未获批准**，不得作为已冻结业务决策实施。

### 17.2 契约落地位置

| 内容 | 契约章节 | 决策记录 |
|---|---|---|
| `PackingPolicy` 字段级 schema、匹配优先级、加载期校验、零匹配 fail closed | `docs/PHASE6_CONTRACT.md` §5.4 | D-032 |
| 约束三处归属、材料/SKU 新增字段、`EffectiveConstraintView`、商品事实隔离 | §5.5 | D-033 |
| Stage 0～6、排序键、方向枚举、容量/重量、拆分混装裁决、性能边界、整单 fail closed | §5.6 | D-034 |
| F1～F8 硬过滤、两种排序策略、冲突处理、零候选、8 条禁止 fallback | §5.7 | D-035 |
| Synthetic-only 与 Production Ruleset 边界 | §5.8 | 安全边界（Task 045/046 冻结，Task 048 补生产侧定义） |
| 包装必测项（policy/约束/算法/材料/边界） | §13.2 | D-032～D-035 |

同时更新：`docs/DECISIONS.md` 新增 D-032～D-035（`APPROVED / FROZEN`）并在 Open Questions 标注 DEC-5/DEC-6 暂缓；`docs/PHASE6_INTEGRATION_PLAN.md` 新增 §5.3 批准矩阵、§11 Batch J2 映射与 §15 实施记录；`docs/PROJECT_PLAN.md` 记录 Task 048；`docs/PHASE6_EXTERNAL_READINESS_AUDIT.md` §17 追加状态；`AGENTS.md` 同步阶段状态与规则索引。

### 17.3 编号一致性

- 正式决策编号：D-001～D-035 连续、唯一、无缺口、无重复。
- D-032～D-035 与 DEC-1～DEC-4 一一对应，未新增任何其他 D 编号。
- DEC-5、DEC-6 保持任务级提案编号，**未**转化为 D 决策。
- D-001～D-031 的原文与语义均未修改。

### 17.4 Task 048 执行后的仓库状态

| 项 | 值 |
|---|---|
| HEAD | `537e165d59eee484149dccbe562020d774396dc1`（未提交、未移动） |
| Branch | `main` |
| 暂存区 | 空（未 `git add`） |
| Remote / Tag / Stash | 均无变化 |
| 业务 JSON | 四个文件 SHA-256 未变（`8305fba3…`、`fa71b788…`、`44b0db54…`、`4d79e67c…`） |
| 代码 / API / OpenAPI / 依赖 / 锁文件 | 未修改（本任务为纯文档契约更新） |

### 17.5 保持不变的内容

- 未新增公共 reason code；包装失败仍只用 `PACKAGE_RULES_NOT_CONFIGURED` / `PACKAGE_DATA_INCOMPLETE`。
- Money Decimal String、Tracking/Quote 隔离、D-030 金额恒等式、D-031 provider-null 投影、`PackageResponse` 字段集合均不变。
- J1 的 `synthetic_only` 隔离、Service 纵深拒绝、默认 `StaticPackagingRuleSetReader(None)` 全部保留。
- 真实包装数据、真实材料目录、获批 ruleset、真实 Provider 配置/凭证/Mapping 全部仍未提供。

### 17.6 最终状态

```text
TASK_047_FINAL_STATUS: DECISION_PACKAGE_COMPLETE_AWAITING_USER_APPROVAL   # 历史
TASK_048_FINAL_STATUS: PASS
DEC_1_TO_4_APPROVED__DEC_5_6_DEFERRED
BATCH_J2_CONTRACT: COMPLETE
BATCH_J2_IMPLEMENTATION: NOT_STARTED
```
