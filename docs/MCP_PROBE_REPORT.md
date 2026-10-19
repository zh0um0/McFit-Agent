# 麦当劳官方 MCP 接口实测探查报告

> 探查时间：2026-10-19 13:54~13:56
> Server：`https://mcp.mcd.cn`，协议版本 `2025-06-18`
> serverInfo：`mcd-mcp v1.0.0`
> 鉴权：Bearer Token（有效）
> 探查方式：标准 MCP 三步握手（`initialize` → `notifications/initialized` → `tools/list` / `tools/call`）

---

## 一、协议层：实际行为与预设一致

| 项 | 实测结果 |
| :--- | :--- |
| 传输 | Streamable HTTP + JSON-RPC 2.0 |
| 响应 Content-Type | `application/json; charset=utf-8`（本次**未**返回 SSE） |
| 会话保持 | 响应头**未**返回 `Mcp-Session-Id`，即**无状态模式**，无需维护会话 |
| 协议协商 | 请求 `2025-06-18`，响应同为 `2025-06-18` |
| 能力声明 | `capabilities: {"tools": {}}`（仅工具，无 resources / prompts） |
| 链路追踪 | 响应含 `x-request-id`，业务体含 `traceId`（32 位 hex） |

> 修正我方实现认知：既有 `mcp_client.py` 按「需缓存 `Mcp-Session-Id`」设计，
> 实际该服务无状态。**缓存逻辑不会出错（取不到就不加），但属不必要的复杂度，可后续简化。**

---

## 二、工具总数：**35 个**（远超预期的 6 个）

官方实际开放 35 个工具，按业务域分类如下：

### 2.1 营养与菜单（4 个）
| 工具 | 说明 |
| :--- | :--- |
| `list-nutrition-foods` | **营养成分数据（本次核心）** |
| `query-meals` | 餐品列表（到店 `orderType=1` / 外送 `orderType=2`） |
| `query-meal-detail` | 餐品详情 |
| `query-meal-assistance` | 企业团餐助餐服务（`beType=6`） |

### 2.2 优惠与卡券（5 个）
| 工具 | 说明 |
| :--- | :--- |
| `available-coupons` | **可领取的券列表** |
| `auto-bind-coupons` | 一键领券（自动领取全部当前可用券） |
| `query-my-coupons` | **用户卡包已有券** |
| `query-store-coupons` | 指定门店 + 订单类型下可用的券 |
| `query-promotions` | 门店企业团餐满减/满折规则 |

### 2.3 下单与订单（6 个）
`create-order`、`cancel-order`、`query-order`、`order-list`、`query-survey-coupon`（CSAT 满意度）、`calculate-price`

### 2.4 外送与门店（4 个）
`query-nearby-stores`、`delivery-query-stores`、`delivery-query-addresses`、`delivery-create-address`

### 2.5 积分与商城（8 个）
`query-my-account`、`mall-points-products`、`mall-product-detail`、`mall-create-order`、`mall-order-list`、`mall-order-detail`、`draw-lottery`、`query-lottery-info`、`query-my-prizes`

### 2.6 主题派对（5 个）
`party-order-create`、`query-party-city`、`query-party-store`、`query-party-store-date`、`query-party-store-session`

### 2.7 其他（2 个）
`campaign-calendar`（活动日历）、`now-time-info`（服务器时间）

---

## 三、核心接口返回结构（实测）

### 3.1 统一响应信封

所有业务接口返回同一层信封：

```json
{
  "success": true,
  "code": 200,
  "message": "请求成功",
  "datetime": "2026-10-19 13:55:07",
  "traceId": "4d04158080366f5b4e9f7f818ab50612",
  "data": { }
}
```

失败时 `success=false`、`code` 为业务码（如 `400 缺少参数`），**HTTP 状态码仍为 200**——
必须判断 `success` 字段，不能只看 HTTP 码。

### 3.2 `list-nutrition-foods`（营养成分）★ 核心

**返回 160 条餐品记录**，但 `data` 是**字符串而非 JSON 数组**，格式为：

```
[160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
  麦辣鸡腿汉堡,null,2029,485,24,24,42,1208,154
  ...
```

需自行解析：先读 `[N]{字段列表}:` 头部，再按行 + 逗号拆分。

| 字段 | 类型 | 含义 |
| :--- | :--- | :--- |
| `productName` | string | 餐品中文名 |
| `nutritionDescription` | string/null | 营养描述（**大量为 null**） |
| `energyKj` | number | 能量（千焦） |
| `energyKcal` | number | 能量（千卡）★ 控卡核心字段 |
| `protein` | number | 蛋白质（g） |
| `fat` | number | 脂肪（g） |
| `carbohydrate` | number | 碳水化合物（g） |
| `sodium` | number | 钠（mg） |
| `calcium` | number | 钙（mg） |

⚠️ **注意**：**无商品编码、无价格字段**。仅有名称与营养素。
这意味着 `list-nutrition-foods` **无法直接与菜单/价格关联**，需靠名称匹配。

### 3.3 `query-my-coupons`（我的卡包）

`data` 结构：`{ coupons: [...], totalCount, currentPage, pageSize, totalPages }`

单张券 **58 个字段**，实测返回 4 张券，真实样例：

| 字段 | 实测值 |
| :--- | :--- |
| `id` | `A255280326E3328D179C362B7B8DDA65` |
| `code` | `MCD6C0UC98001C0106Q1P` |
| `title` | `11.9元麦辣鸡腿堡` |
| `subtitle` | （空串） |
| `showType` | `100` |
| `image` / `bigImage` | COS 腾讯云图片地址 |
| `instructions` | `{ labels: [], availableTime: [{ text: "2026.10.19-2026.10.23", color, type }] }` |

### 3.4 `available-coupons`（可领券）

`data` 为**数组**，元素 4 字段（字段名与卡包券完全不同）：

```json
{ "couponName": "19.9元王牌炸鸡任选2",
  "couponImage": "https://img.mcd.cn/cms/images/....png",
  "couponStatus": "HAVING_RECEIVE",
  "label": "已领取" }
```

⚠️ **口径不一致**：`query-my-coupons` 用 `title`/`code`，`available-coupons` 用
`couponName`/`couponStatus`。凑单算法接入时需分别映射。

### 3.5 `campaign-calendar`（活动日历）

`data: { currentTime, dailyList: [{ date, dateText, events: [...], today }], subscribedEvents: [] }`

实测 13 天日历、当日 15 个活动；单个 `events` 元素 17 字段
（`activityCode`、`activityStage`、`eventType`、`position`、`showStyle` 等）。

### 3.6 `query-my-account`（积分账户）

`data` 10 字段，积分以**字符串**返回（注意类型）：

```
availablePoint: "104.3"    accumulativePoint: "2686.5"
expiredPoint: "1502.2"     frozenPoint: "0"
currency: "麦享会积分"      accountId: "2E0FF8FC-..."
```

### 3.7 `query-nearby-stores`（附近门店）

空参数调用返回：`success=false, code=400, message="缺少参数"`。
即：**错误走业务码，HTTP 仍 200**——再次印证需判断 `success`。

---

## 四、官方数据 vs 项目内置种子数据（重要差异）

既然官方营养数据可用，对既有 27 条种子数据做了比对：

| 单品 | 官方 kcal | 种子 kcal | 差值 | 官方蛋白 | 种子蛋白 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 麦辣鸡腿汉堡 | 485 | 516 | **−31** | 24 | 22 |
| 板烧鸡腿堡 | 391 | 474 | **−83** | 23 | 26.5 |
| 巨无霸 | 513 | 550 | **−37** | 27 | 25 |
| 吉士汉堡包 | 294 | 250 | **+44** | 16 | 13 |

**最大偏差 83 kcal（约 21%）**。种子数据虽已在页面标注「估算值」，但既然官方接口可用，
参赛演示时若走实时数据，说服力显著提升。

### 接入的三个障碍（需决策）

1. **无商品编码** —— 官方仅给 `productName`，项目现有主键是 `mcp_code`（如 `M1001`），
   需改用**名称匹配**，或调整主键策略。
2. **无价格** —— `list-nutrition-foods` 不含价格，而凑单算法强依赖价格。
   需搭配 `query-meals` 取价格，或按名称关联种子数据的价格。
3. **字符串格式解析** —— 需写专门的 `[N]{fields}:` 解析器（我方现有解析逻辑假设 JSON 数组，
   **对官方返回会解析失败**）。

---

## 五、对我方实现的三项修正建议

> **本节已于2026-10-19 全部处理完毕**，详见 `MCP_INTEGRATION.md` 第 5 节。

| # | 现状 | 问题 | 处理结果 |
| :--- | :--- | :--- | :--- |
| 1 | `mcp_client.py` 假设返回 JSON 数组 | 官方 `data` 是 `[N]{...}:` 字符串格式| ✅ 已新增 `parse_nutrition_payload()` 专用解析器 |
| 2 | 维护 `Mcp-Session-Id` | 服务实际无状态 | 保留代码（无害），已在文档说明「该服务无会话概念」 |
| 3 | 仅白名单 6 个工具 | 实测有 35 个 | ✅ PRD 收敛决策依然正确，已补充第 9 节「官方工具全景」说明 |
| 4 | — | 返回文本还包了一层 markdown | ✅ `_extract_text()` 增加 `## Original Response` 剥离逻辑 |

---

## 五·二、接入后新发现的数据质量问题

**官方原始数据自身存在不一致**：`可乐中杯` 钠 = 0mg，而 `无糖可口可乐中杯` 钠 = 35mg
（含糖饮料钠含量反而低于无糖，逻辑上反常）。

本项目**忠实透传不做修改**，以免偏离官方口径。如评审问起，这是官方数据本身的特性。

**与内置种子的偏差**：接入前实测发现内置估算值与官方最大偏差 83 kcal（约 21%），
已全部按官方真实值校正，并对两源重名单品加回归测试保证数值一致。

---

## 六、合规与安全

- Token 仅用于本次探查，**未写入任何项目文件、日志或 memory**
- `mcp-config.example.json` 保持占位符不变
- 探查过程**未调用任何写操作接口**（`create-order` / `cancel-order` / `mall-create-order` /
  `auto-bind-coupons` / `delivery-create-address` / `draw-lottery` 等一律未触碰），
  未产生任何真实订单、领券或积分变动