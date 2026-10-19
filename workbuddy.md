# WorkBuddy 开发过程记录 (workbuddy.md)

> 本文件用于核验麦当劳程序员创意开发大赛 × 腾讯 WorkBuddy 专项奖励资格。
> 记录周期：2026-10-13 ~ 2026-10-16（基于 WorkBuddy 会话协作过程整理）

---

## 1. 接入配置

在 WorkBuddy 中配置麦当劳 MCP 连接器：
- **MCP Server**：`https://mcp.mcd.cn`
- **协议**：`streamablehttp`
- **鉴权**：Bearer Token（本地环境变量，未入代码库）
- **状态**：连接成功，已识别 `list-nutrition-foods`、`auto-bind-coupons`、`query-my-coupons`、`query-meals`、`calculate-price`、`campaign-calendar` 共 6 个工具。
- **降级策略**：未配置 Token 时使用内置种子菜单（离线演示模式），主流程不降级。

---

## 2. 交互与开发记录摘要

### 对话轮次 1（2026-10-13）：赛事规则研读与方案评审
- **开发者**：提供赛事资料包（赛事速览、参赛操作指南、各模板文件）与已完成构思的《麦门控卡精明私教 PRD v1.0》，要求从产品视角审核并提修改建议。
- **WorkBuddy**：输出结构化评审——痛点切入 ★5 / 差异化 ★4 / 范围控制 ★2 / PRD 规范度 ★3，指出 5 个必改项：双轨架构范围过大、README/GIF 优先级排反（纯 Star 评审规则下 GIF 是核心资产）、MCP 工具未用满与模板不一致、缺 Non-goals/用户故事/风险/指标、公式乱码与贴纸版权风险。并给出 P0/P1/P2 三层取舍图。

### 对话轮次 2（2026-10-13）：PRD v1.1 修订落盘
- **开发者拍板 3 条口径**：Agent 功能移到最后做加分项（不砍）；MCP 保持原 6 个工具不扩展；运动代偿换算由负罪感框架改为正向激励框架；其余按评审建议修改。
- **WorkBuddy**：产出 PRD v1.1（保留 v1.0 不覆盖）。关键变更：Agent 移至 Phase 5；新增 Non-goals（不做下单/不做医疗建议等 6 条）、用户故事 4 条、风险与合规清单、成功指标（Star ≥100）；贴纸明确自绘 SVG 禁官方素材；路线图按 12 天倒排。

### 对话轮次 3（2026-10-13）：开发计划与验收方案制定
- **开发者**：确认进入开发，要求先对齐技术选型与验收标准。
- **WorkBuddy**：产出《开发计划与验收方案》（docs/DEVELOPMENT_PLAN.md）。关键决策：
  - 技术选型升级为 Vue 3 + Vite + Pinia / FastAPI + SQLAlchemy 2.0（FastAPI 自带 Swagger 是 Star 加分项）；
  - 数据库默认 SQLite 零配置（评委克隆后三条命令跑起来），`DATABASE_URL` 一行切换 Postgres；
  - 认证采用 Argon2id + JWT 双令牌；体重/TDEE 以 Fernet 密文落库；
  - 范围变更：PRD v1.1 中「不做账号体系」Non-goal 经论证后移除，以「加密落库 + 同步默认关 + 海报脱敏」三道措施补足隐私防线。

### 对话轮次 4（2026-10-14 ~ 10-15）：全栈开发与缺陷修复（P0~P4）
- **WorkBuddy 协作产出**：8 张表 ORM、7 个认证接口、30 个 REST 接口、6 页面前端、TDEE/运动换算/凑单比价/贴纸引擎 4 个算法模块、MCP JSON-RPC 客户端、55 项 pytest 测试、18 项 Playwright E2E。
- **典型协作片段**：
  - 开发者：「凑单接口 500」→ WorkBuddy 定位为种子券键名 `coupon_code` 与实体字段 `code` 不一致，抽出 `coupons_from_rows()` 统一映射并补回归测试；
  - WorkBuddy 主动发现达标文案空占位缺陷（`convert(0,...)` 返回空列表仍取 `plans[0]`），修复为按差额换算并补断言 `test_narrate_never_has_empty_placeholder`；
  - 端到端验证发现 P0 级注册 Bug：不填邮箱的第二个用户注册被误判 409（`email IS NULL` 误匹配），修复为拆分独立查询，补 5 条回归测试并做「还原 bug 版验证测试确实失败」的反向校验。

### 对话轮次 5（2026-10-16）：独立用户视角验收
- **开发者**：要求以用户角度对项目做测试验收，确认功能完整性。
- **WorkBuddy**：三层复核全绿——后端 pytest 55/55、自带 E2E 18/18、新增《用户验收脚本 user-acceptance.mjs》31/31（覆盖自验未触及的点餐勾选/凑单试算/采用推荐/保存/打卡/贴纸/日历/海报脱敏指纹校验/重登持久化）。3 个疑似缺陷均甄别为验收脚本侧问题（非产品缺陷）。结论：P0~P4 功能完整性验收通过，PRD 模块 1~4 全部可用，Non-goals 全部守住。验收记录回写进度书六·三章。

---

## 3. WorkBuddy 在本项目中的核心价值

1. **评审前置**：开发前 2 小时的 PRD 评审避免了双轨架构的范围失控——按 12 天窗口砍出可交付的 P0 集合。
2. **测试即资产**：55 项 pytest + 18+31 项 E2E 全部由协作产出并沉淀为仓库文件，其中 E2E 曾抓出单元测试全绿时未暴露的 P0 注册 Bug。
3. **合规内建**：贴纸自绘 SVG、海报脱敏、Token 零硬编码、Non-goals 约束等合规要求在设计与验收两道关口被反复校验。
4. **决策留痕**：范围变更（账号体系 Non-goal 移除）、选型修正（Postgres → SQLite 默认）均落盘进度书，可追溯。

---

## 4. 交付物清单（本仓库）

- `README.md` / `CONTEST_DECLARATION.md` / `MCP_INTEGRATION.md` / `mcp-config.example.json` / `workbuddy.md`
- `backend/`（FastAPI 源码 + 55 项测试）、`frontend/`（Vue 3 源码）、`e2e/`（2 个 E2E 验收脚本）、`docs/`（PRD / 开发计划 / MCP 集成说明）
