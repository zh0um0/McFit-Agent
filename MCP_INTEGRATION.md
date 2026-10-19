# 麦当劳 MCP 服务集成说明 (MCP_INTEGRATION.md)

## 1. 接入的 MCP Server 基础信息

| 项 | 值 |
| :--- | :--- |
| 服务提供方 | 麦当劳中国 (McDonald's China) |
| 服务地址 | `https://mcp.mcd.cn` |
| 通信协议 | Streamable HTTP |
| 鉴权方式 | Bearer Token (`Authorization: Bearer <TOKEN>`) |
| 客户端实现 | `backend/app/services/mcp_client.py`（httpx 手写 JSON-RPC 2.0） |

---

## 2. 核心调用的 MCP Tools 清单

本项目根据业务场景实际调用以下 **6 个**官方工具，范围与 PRD 模块 2 严格一致（不扩展、不追求用满）：

| 序号 | Tool 名称 | 工具定位 | 在本项目中的应用场景 |
| :---: | :--- | :--- | :--- |
| 1 | `list-nutrition-foods` | 餐品营养成分查询 | 拉取官方真实热量、蛋白质、脂肪、碳水、钠，做营养打标 |
| 2 | `auto-bind-coupons` | 麦麦省一键领券 | 冷启动时一键同步领取最新优惠券 |
| 3 | `query-my-coupons` | 查询我的可用卡券 | 读取用户卡包中可用的满减、买赠等卡券 |
| 4 | `query-meals` | 查询当前门店菜单 | 获取门店实时可售单品与套餐分类 |
| 5 | `calculate-price` | 价格与折扣计算 | 组合凑单后校验优惠券生效并计算折后总价 |
| 6 | `campaign-calendar` | 今日特惠与会员日 | 查询活动日历，支撑活动提示 |

**明确不接入**：`query-my-account`、`mall-points-products`（积分商城）、`create-order`（真实下单）。

---

## 3. 协议实现细节

### 3.1 三步握手

```
POST https://mcp.mcd.cn
Headers: Authorization: Bearer <TOKEN>
         Content-Type: application/json
         Accept: application/json, text/event-stream

1) initialize → 返回 result + Mcp-Session-Id 响应头
2) notifications/initialized → 确认会话
3) tools/call → 业务调用
```

### 3.2 两个工程要点

**① 会话保持**：Streamable HTTP 通过响应头 `Mcp-Session-Id` 维持会话状态，
客户端将该 ID 缓存并在后续请求中回传，否则每次调用都会被视为新会话。

**② 响应双格式**：服务端可能返回 `application/json`，也可能返回
`text/event-stream`（SSE）。客户端需同时处理：

- JSON → 直接解析
- SSE → 逐行扫描 `data:` 前缀帧，取出 JSON

---

## 4. 工具调用链路与业务架构

```
用户勾选餐品 / 唤醒点餐
         │
         ▼
   [轨道 A：GUI 自助模式 —— 主链路]
         │
         ├── query-meals / list-nutrition-foods ──► 官方营养数据
         │                                            ↓
         │                                        meals_cache 落库
         ├── auto-bind-coupons ──► 领取新券
         ├── query-my-coupons ──► 卡包明细 ↓
         │                                    coupon_snapshots 落库
         ▼
   [算法层：凑单比价]
    枚举补充单品 × 卡券组合
    约束：品类搭配 + 热量预算
    目标：实付最低
         │
         ├── calculate-price ──► 官方折后价校验
         ▼
   输出最省方案 + 运动代偿换算 + 贴纸打卡
         │
         ▼
   [轨道 B：Agent 智能私教 —— P5 加分项]
    Thought→Action→Thought→Final 的 ReAct 思维链
```

---

## 5. 官方营养数据接入（实测于 2026-10-19）

### 5.1 为什么只取每类 5 个

官方 `list-nutrition-foods` 返回 **160 条**全量餐品。本项目是**演示型**应用，
160 条会淹没「控卡 + 省钱」的核心卖点，故采用**精选集策略**：

| 类别 | 数量 | 选取原则 |
| :--- | :--- | :--- |
| 汉堡 | 5 | 减脂优选（板烧鸡腿堡 391kcal、双层吉士 429kcal 为高蛋白低卡代表） |
| 小食 | 5 | 高蛋白（麦乐鸡5块/鸡翅）与低卡（大杯玉米杯 87kcal）各半 |
| 甜点 | 5 | 低卡优先（圆筒冰淇淋 93kcal、菠萝派 221kcal） |
| 饮品 | 5 | **饮料与奶饮合并**，含零卡选择（无糖可口可乐 0kcal） |

共 **20 条**，配置项 `MCD_PICKED_ONLY=true`（默认）；置为 `false` 可落库全部 160 条供开发调试。

> **饮料与饮品为何合并**：二者同属「喝的东西」，业务上拆开没有意义，
> 分成两个板块各5 条反而稀释了演示焦点。合并后统一为「饮品」类，
> 内部涵盖可乐/果汁（饮料）与咖啡/牛奶（奶饮），共 5 个，层次更清晰。

### 5.2 精选集为何手工指定而非关键词分类

官方接口**不提供分类字段**（`nutritionDescription` 160 条中仅 3 条非空，无分类价值）。
关键词匹配会误判——「巨无霸」是汉堡但名称无「堡」字、「麦香鱼」是鱼类堡。
故采用人工白名单（`app/services/mcd_official_data.py`），每条都准确且具业务代表性。

### 5.3 接入中解决的三个技术障碍

| 障碍 | 解决方案 |
| :--- | :--- |
| **返回文本包markdown** —— `content.text` 内是`# API Response Information … ## Original Response {json}` | `_extract_text()` 用正则剥离说明段，只留原始响应体再解析 JSON |
| **`data` 是专有字符串格式** —— `[160]{字段列表}:\n  名称,值,值…`，非 JSON 数组 | 新增 `parse_nutrition_payload()` 专用解析器；字段数不匹配的行直接跳过，不猜测错位 |
| **无商品编码** —— 仅中文名 | 以 md5(name) 前 8 位生成稳定伪编码作主键（**不可用内置 `hash()`，其对 str 逐进程加盐会导致重启后主键漂移、产生重复记录**） |

### 5.4 数据口径统一

接入后发现内置种子数据与官方偏差最大达 **83 kcal（约21%）**，已按官方真实值校正，
并保证**两条来源重名单品数值完全一致**——否则用户会看到「板烧鸡腿堡 474/391 kcal」两个答案。
有3 条回归测试锁死这一点。

官方原始数据自身存在一处不一致（可乐钠=0mg 而无糖可乐钠=35mg），本项目**忠实透传不做修改**，
以免偏离官方口径。

### 5.5 种子与官方数据的互斥

同步官方数据后，`init_db()` 会**自动清理 27 条种子菜单**——否则界面会同时出现
25 条官方 + 27 条种子，演示时口径混乱。无 Token 时种子照常写入，保证零配置可跑。

---

## 6. 降级策略：离线可演示

**这是本项目 Star 转化的关键设计。**

评委克隆仓库后通常**没有 MCP Token**。若此时界面空白，30 秒决策窗口直接失效。
因此实现两级数据源：

| 场景 | 数据来源 | 界面标识 |
| :--- | :--- | :--- |
| 已同步官方数据（`source='mcp'`） | 官方实时营养数据，每类精选 5 条共 25 条 | 绿色徽标「官方MCP实时」 |
| 未配置 Token / 未同步 | 内置种子菜单 31 条（数值已对齐官方），`source='seed'` | 灰色徽标「内置种子」 |

**关键约束**：两条来源**互斥**——一旦库中存在 `source='mcp'` 的记录，
`init_db()` 会在启动时清理全部种子菜单，避免界面同时出现两套口径。

**界面标识的准确性**：`source` 与 `/health` 的 `mcp_mode` 均以**库内真实数据**为准，
而非「是否配置了Token」——配了 Token 但未同步时仍显示「内置种子」，避免对用户说谎。

**同步方式**（需配置 Token）：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/coupons/sync-nutrition \
  -H "Authorization: Bearer <access_token>"
```

---

## 7. 业务价值与创新点

1. **消除决策成本**：把「查卡券 → 比单点/凑单 → 算折后价」这条需要 3~5 分钟人工对比的链路，
   压缩为一次点击、毫秒级输出。
2. **热量的约束下的省钱**：多数省钱工具只关心价格，本项目把**热量预算作为硬约束**加入凑单算法
   （`kcal_budget` 参数），实现「既控得住、又花得少」的双目标求解。
3. **科学口径**：热量目标基于 Mifflin-St Jeor 公式而非粗略估算；
   运动代偿换算按体重动态计算（慢跑距离与体重直接相关）。
4. **正向激励设计**：超标时给的是「低门槛补救动作」而非情绪审判，
   禁止出现「反省/放纵/惩罚」类字眼——这是留存设计的核心判断。
5. **隐私最小化**：身体数据密文落库、云同步默认关闭、分享海报默认脱敏。

---

## 8. 安全说明

- Token 仅从环境变量 `MCP_TOKEN` 读取，**零硬编码**，异常信息中不含 `Authorization` 头
- 工具白名单 `ALLOWED_TOOLS` 硬编码在客户端，越权调用在客户端层即被拒绝
- `mcp-config.example.json` 仅含占位符，真实配置在 `.gitignore` 中
- **接口探查过程未调用任何写操作**（下单/领券/抽奖/地址创建一律未触碰），未产生任何真实订单或积分变动

---

## 9. 官方工具全景（实测 35 个）

项目按需取用 6 个（见第 2 节），官方实际开放 35 个，分类如下：

| 业务域 | 数量 | 工具 |
| :--- | :---: | :--- |
| 营养与菜单 | 4 | `list-nutrition-foods`、`query-meals`、`query-meal-detail`、`query-meal-assistance` |
| 优惠与卡券 | 5 | `available-coupons`、`auto-bind-coupons`、`query-my-coupons`、`query-store-coupons`、`query-promotions` |
| 下单与订单 | 6 | `create-order`、`cancel-order`、`query-order`、`order-list`、`query-survey-coupon`、`calculate-price` |
| 积分与商城 | 8 | `query-my-account`、`mall-points-products`、`mall-product-detail`、`mall-create-order`、`mall-order-list`、`mall-order-detail`、`draw-lottery`、`query-lottery-info`、`query-my-prizes` |
| 外送与门店 | 4 | `query-nearby-stores`、`delivery-query-stores`、`delivery-query-addresses`、`delivery-create-address` |
| 主题派对 | 5 | `party-order-create`、`query-party-city`、`query-party-store`、`query-party-store-date`、`query-party-store-session` |
| 其他 | 2 | `campaign-calendar`、`now-time-info` |

> PRD「不追求用满官方接口」的收敛决策依然成立——取 6 个即可覆盖控卡/省钱/打卡三条主线，
> 接更多反而会稀释重点。完整的接口探查细节见 `MCP_PROBE_REPORT.md`。