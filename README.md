# 🍔 麦门控卡精明私教 (McFit-Agent)

> 控卡 + 省钱 + 贴纸打卡。一个麦当劳，也不会吃垮你的减脂计划。

基于**麦当劳中国官方 MCP（Model Context Protocol）**打造的智能点餐助手：
用科学热量模型守住每一餐，用优惠券凑单算法把每一单花到最省，用自绘贴纸日历让坚持看得见。

**⚠️ 免责声明：本项目所有营养与运动换算数据均为估算值，仅供参考，不构成医疗或营养专业建议。**

```
⚡ 想看效果？  双击 start.bat  →  打开 http://localhost:5173  →  demo / demo123456
无需数据库，无需任何密钥，约 2 分钟完成首次依赖安装。
```

---

## ✨ 30 秒看到效果

### 最短路径（推荐）

**Windows**：双击 `start.bat`
**macOS / Linux**：终端执行 `./start.sh`

脚本会自动建虚拟环境、装依赖、等待后端就绪、再拉起前端。

然后打开 **http://localhost:5173**，用演示账号登录：

| 用户名 | 密码 |
| :--- | :--- |
| `demo` | `demo123456` |

> **无需配置任何密钥**：不需要 MCP Token，也不需要 LLM Key。
> 数据库表、20 个精选单品、demo 账号会在首次启动时自动创建。

### 前置要求

| 依赖 | 版本 | 说明 |
| :--- | :--- | :--- |
| Python | 3.10+ | 必需。后端语言 |
| Node.js | 18+ | 必需。构建前端 |

两者都是主流工具，**不需要安装数据库**（SQLite 零配置，文件自动生成）。

### 手动启动（想看每一步时）

```bash
# 终端 1 —— 后端
cd backend
python -m venv .venv
.venv\Scripts\activate                 # Windows
# source .venv/bin/activate             # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 终端 2 —— 前端
cd frontend
npm install
npm run dev
```

### 起不来？跑一下自检

双击 `check.bat`（Windows）或 `./check.sh`（macOS/Linux），
它会逐项告诉你缺什么、并给出**具体该执行的命令**。

**不需要配置任何 LLM Key，也不需要 MCP Token** —— 内置种子菜单即可跑通全部主流程。

---

## 🩺 遇到问题？先跑自检

双击 **`check.bat`**（Windows）或 **`./check.sh`**（macOS / Linux）：

```
运行环境
  ✓ Python: Python 3.13.14
  ✓ Node.js: v22.22.2
依赖
  ✓ 后端虚拟环境已创建
  ✓ 前端依赖已安装
配置
  ! 未配置 MCP_TOKEN → 使用内置种子菜单（功能不降级）
服务状态
  ✓ 后端运行中 → http://127.0.0.1:8000
  ✓ 前端运行中 → http://localhost:5173
  ───────────────────────────
  全部就绪（6 项通过）
```

它会逐项告诉你缺什么、以及**具体该执行哪条命令**。

| 常见症状 | 原因与解决 |
| :--- | :--- |
| 页面提示「未检测到后端服务」 | 后端没启动 → `cd backend && uvicorn app.main:app --port 8000` |
| 端口 8000 被占用 | 残留进程 → 任务管理器结束占用该端口的进程 |
| `pip install` 很慢/失败 | 换国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `npm install` 很慢/失败 | 换镜像：`npm config set registry https://registry.npmmirror.com` 后重试 |
| 想看接口文档 | 访问 **http://127.0.0.1:8000/docs**（Swagger 可直接 Try-it） |
| 想用官方实时营养数据 | 在 `backend/.env` 填入 `MCP_TOKEN=你的Token`，重启后端 |

> 两个服务是**独立进程**，需分别启动。关闭终端即停止服务，重新执行启动命令即可。

---

## ❓ 评委常问的三个问题

**Q：需要我自己装数据库吗？**
不需要。项目用 SQLite，数据库就是一个文件，首次启动时自动生成在 `backend/mcfit.db`。
表结构、20 个精选单品、demo 账号都会自动建好，**零配置**。

**Q：为什么菜单只有 20 个，不是官方 160 个？**
官方接口返回 160 条全量，但本项目是**演示型应用**，只精选每类 5 个（共 20 个），
避免列表淹没核心卖点。内置种子数据与官方实时数据**完全一致**，
所以配不配 Token，你看到的菜单都是这 20 个。

**Q：要不要做安装包？**
不需要，也**不建议**做。评委是技术人，装包反而增加失败环节。
一个 `start.bat` 足够——它已经封装了建虚拟环境、装依赖、等后端就绪、拉前端全部流程。

---

## 🎯 三个卖点

### 1. 科学控卡：Mifflin-St Jeor 公式，不是拍脑袋

录入身材档案后自动算出你的 BMR / TDEE / 每日目标热量 / 蛋白质区间，
并精确拆分到早、午、晚三餐上限。点餐时热量与差额**毫秒级累加**。

### 2. 极致省钱：凑单算法帮你把券用满

结合卡券门槛做穷举比价，自动推荐「实付最低」组合 —— 单点 vs 券 vs 凑单的差额一眼可见。

> 实测：巨无霸单点 ¥22 → 推荐组合 ¥17，一单省 ¥5

### 3. 坚持可视化：自绘贴纸 + 打卡日历

每餐生成专属食物贴纸（**全部为项目内自绘 SVG 简笔图标**），
打卡日历按月展示达标/维持/超出，可一键导出分享 —— **海报默认脱敏，不含体重、TDEE 等身体数据**。

---

## 🛠 技术架构

```
[前端]  Vue 3 + Vite + Pinia + Vue Router（路由懒加载，gzip 后约 41 KB）
    │  JWT Bearer自动刷新
    ▼
[后端]  FastAPI + SQLAlchemy 2.0（30 个 REST 接口，自动生成 Swagger 文档）
    │
    ├── 算法层  TDEE 代谢模型 / 运动代偿换算 / 优惠券凑单比价 / 自绘 SVG 贴纸引擎
    │
    ├── 协议层  MCP Streamable HTTP 客户端（JSON-RPC 2.0）
    │           ↓ 配置 MCP_TOKEN 时
    │      麦当劳官方 MCP Server (https://mcp.mcd.cn)
    │
    └── 数据层  SQLite 零配置（改 DATABASE_URL 即切 PostgreSQL）
```

### 调用的官方 MCP 工具（6 个，与 PRD 严格一致）

| Tool | 用途 |
|---|---|
| `list-nutrition-foods` | 官方真实热量、蛋白质、脂肪、碳水、钠 |
| `auto-bind-coupons` | 一键领券 |
| `query-my-coupons` | 读取卡包可用卡券 |
| `query-meals` | 门店实时可售菜单 |
| `calculate-price` | 折后实付价校验 |
| `campaign-calendar` | 今日特惠与会员日 |

未配置 Token 时自动降级到内置种子数据，**功能不降级**。

### 官方营养数据已接入（2026-10-19 实测）

| 项 | 实测结果 |
| :--- | :--- |
| 官方开放工具 | **35 个**（本项目按需取用 6 个） |
| `list-nutrition-foods` 返回 | **160 条**餐品营养数据 |
| 本项目接入 | 精选 **20 条**（汉堡/小食/甜点/饮品 各 5 个） |
| 数据一致性 | 内置种子数值已按官方真实值校正，最大偏差从 83 kcal 降至 0 |

配置 Token 后同步官方数据：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/coupons/sync-nutrition \
  -H "Authorization: Bearer <你的access_token>"
```

详见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md) 与 [接口探查报告](docs/MCP_PROBE_REPORT.md)。

---

## 🔐 用户认证

| 能力 | 说明 |
|---|---|
| 注册 / 登录 | 用户名 + 密码（Argon2id 哈希，加盐抗暴力破解） |
| 双令牌JWT | access 2h + refresh 7d，前端 401 自动刷新并重放请求 |
| 暴力破解防护 | 连续 5 次失败锁定 15 分钟 |
| 用户枚举防护 | 用户名不存在与密码错误返回**完全相同**的文案 |
| 越权防护 | 所有个人数据查询以 token 中的 `user_id` 为准，无法跨用户访问 |
| 敏感字段加密 | 体重、目标体重、TDEE 以 Fernet 密文落库，密钥走环境变量 |
| 第三方登录预留 | `provider` / `provider_id` 字段与 `/auth/oauth-providers` 接口位已就绪 |

**隐私口径**：身体数据默认仅本地存储（`CLOUD_SYNC_ENABLED=false`），不参与任何云端同步，分享海报默认脱敏。

---

## 📊 数据库设计（8 张表）

| 表 | 用途 | 关键点 |
| :--- | :--- | :--- |
| `users` | 账号 | 锁定状态、失败计数、OAuth 预留字段 |
| `user_profiles` | 身材档案 | 体重/TDEE **加密存储** |
| `meals_cache` | 菜单营养缓存 | `source` 字段区分 seed / mcp |
| `order_records` | 点餐记录 | 餐品 JSON 快照，历史不受菜单更新影响 |
| `daily_checkins` | 每日打卡 | `(user_id, date)` 唯一，覆盖式更新 |
| `coupon_snapshots` | 卡券快照 | Token 绝不落库 |
| `user_coupons` | 用户↔卡券绑定 | 支持核销与转赠 |
| `exercise_presets` | 运动换算参数 | 可后台调参，无需改代码 |

切 PostgreSQL：只需修改 `.env` 中的 `DATABASE_URL`，**代码零改动**。

---

## 🧪 验收与测试

```bash
# 后端：108 项自动化测试
cd backend
python -m pytest tests/ -v

# 端到端：18 项浏览器真实流程验收（需前后端已启动）
npm install                # 安装 playwright（根目录 package.json）
npx playwright install chromium
node e2e/journey.spec.mjs
```

**108 项后端测试全绿**，分五层：

| 层级 | 覆盖内容 |
| :--- | :--- |
| 单元层 | TDEE公式（含男女分支、极值边界）、运动换算精度、凑单最优性、券门槛判定、文案无空占位 |
| 接口层 | 注册/登录/刷新/改密、令牌类型混淆、账号锁定、越权访问、加密落库校验 |
| 端到端 | 档案 → 菜单 → 凑单 → 存档 → 打卡 → 日历 → 海报 完整链路（按实际日期断言，跨天不失效） |
| 安全 | 越权删除他人记录、XSS 载荷、SQL 注入、用户枚举、暴力破解锁定、海报脱敏字段级校验 |
| 官方MCP | 专有字符串格式解析、精选集完整性（每类 5 个）、两源数值一致、**贴纸固定尺寸**、图标唯一性 |

> 隐私断言采用**递归遍历 JSON 键名 + 字段白名单**校验（而非全文搜数字），
> 并有反向测试确保它真能抓到顶层与嵌套泄露，防止退化成「永远通过」的空断言。

**另有18 项端到端验收**（`e2e/journey.spec.mjs`，Playwright 真实浏览器）覆盖新手引导、
档案页指标说明、路由守卫回跳、说明文字溢出、控制台报错—— **18/18 通过**。

> 这套 E2E 曾抓出一个后端 55 项测试全绿时都没发现的 P0 Bug
> （不填邮箱的用户注册被误判「邮箱已注册」），详见[开发计划文档](docs/DEVELOPMENT_PLAN.md)第六章。

---

## 📁 项目结构

```
mcfit-agent/
├── backend/
│   ├── app/
│   │   ├── core/         配置、密码哈希、JWT、加密、鉴权依赖
│   │   ├── db/           引擎会话、ORM 模型、建表与种子
│   │   ├── services/     TDEE、运动换算、凑单算法、MCP 客户端
│   │   │                 贴纸引擎、商品图标库、精选集定义
│   │   └── api/v1/       30 个 REST 接口
│   └── tests/            108 项测试
├── frontend/
│   └── src/
│       ├── api/          统一请求客户端（含 token 自动刷新）
│       ├── stores/       Pinia 状态
│       └── views/        登录/概览/点餐/打卡/档案/我的
├── e2e/
│   └── journey.spec.mjs  18 项浏览器端到端验收
├── docs/
│   ├── PRD.md                 产品需求与架构规划
│   ├── MCP_INTEGRATION.md     MCP 集成说明（含官方接口全景）
│   ├── MCP_PROBE_REPORT.md    官方接口实测探查报告
│   └── DEVELOPMENT_PLAN.md    开发计划与验收方案
├── scripts/
│   ├── judge_clone_test.sh    评委视角验证（模拟全新克隆）
│   └── verify_live_mcp.py     官方 MCP 真实联调
├── start.bat / start.sh       一键启动（Windows / macOS·Linux）
├── check.bat / check.sh       环境自检
├── README.md
├── CONTEST_DECLARATION.md    赛事声明
└── .env.example
```

---

## 🔒 合规声明

- 贴纸图标**全部为项目内自绘 SVG 简笔图标**，不使用麦当劳官方 Logo、餐品实拍图或官方物料
- 代码中**零硬编码密钥**，所有凭据走环境变量；MCP Token 不入库、不进版本库
- **不调用 `create-order`**，不产生任何真实订单与支付行为
- 营养数值来自麦当劳官方 MCP `list-nutrition-foods` 公开接口（对齐 2026-10-19 快照），
  为**单份参考值**（实际食用会因做法/配料/份量浮动）；价格为项目估算值，实时以官方 App 为准
- 热量目标基于 Mifflin-St Jeor 公式估算，运动代偿为换算参考，**均不构成医疗或营养专业建议**

---

## 📄 相关文档

**参赛必备文件（仓库根目录）**

| 文件 | 说明 |
| :--- | :--- |
| [README.md](README.md) | 本文件，项目说明书 |
| [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md) | 官方参赛声明（一字未改） |
| [MCP_INTEGRATION.md](MCP_INTEGRATION.md) | MCP 集成说明 + 官方 35 个接口全景 |
| [mcp-config.example.json](mcp-config.example.json) | 脱敏配置示例（仅占位符） |
| [workbuddy.md](workbuddy.md) | WorkBuddy 辅助开发记录（专项奖核验） |

**扩展文档（docs/）**

- [产品需求与架构规划文档 (PRD)](docs/PRD.md)
- [官方接口实测探查报告](docs/MCP_PROBE_REPORT.md)
- [开发计划与验收方案](docs/DEVELOPMENT_PLAN.md)