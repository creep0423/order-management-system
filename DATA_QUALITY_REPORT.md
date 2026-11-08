# Phase 0 数据准备记录

## 数据来源
- 订单：`IT_Coding_Assessment_Update_v2.html` 中的两笔示例订单及 9 条订单明细。
- SKU：用户通过 SQL-like 查询网站逐个查询后提供的 9 条结果。
- SKU 表名：`product_list`；商品主键字段：`SKU`。
- 货币：AUD。
- 税务口径：RRP 含 GST；后续计算按更新版需求执行。

## 数据质量发现
1. `HARNIG`、`LELCBD100`、`AURPUR10` 的 `Description` 原始值为 `.`，标准化后记为 null。
2. `HALGEO15` 的 Description 在复制到聊天中的结果疑似被截断，仅保留已收到文本，并标记 `partial_needs_requery`；不得把它当作完整描述。
3. 多个 SKU 的 `ETA` 为 `nullDays`，标准化为 `eta_days: null`，同时保留 `eta_raw`。
4. `HARNIG.DosageType` 有换行符；`HARNIG.PlantSpecies`、`AURPUR10.PlantSpecies`、`MCMW10.ProductName`、`MCMW10.Spectrum`、`MCBO30.Spectrum` 存在首尾空格。标准化数据已 trim，原始文件保留原值。
5. 重量、尺寸、体积字段带单位。标准化文件分别转换为 g、mm、mm³、kg，数值仍以字符串保存，避免浮点精度损失。
6. `RRP` 保留为十进制字符串，后端计算应使用 Python `Decimal`。

## 订单和物流
- 订单按更新版 HTML 的订单号、客户信息、地址、SKU、数量及 tracking group 录入。
- `TRACK_1`、`TRACK_2` 使用 StarTrack / Australia Post；`TRACK_3` 使用 TNT。
- 订单联系方式属于题目样例数据；公开仓库前应评估是否需要脱敏。

## 尚待补充
- 重新查询 `HALGEO15` 的完整 Description。
- 之后阶段再检查 Windows 开发环境和第三方物流 API 可用性。
