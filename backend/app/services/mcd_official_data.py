"""麦门控卡 McFit-Agent · 官方营养数据精选集

【数据来源】麦当劳官方 MCP `list-nutrition-foods` 接口实时返回（160 条全量）
【采集时间】2026-10-19
【选取原则】每个类别精选 5 个最具控卡/省钱代表性的单品（非全量展示）

【为什么手工指定而非关键词分类】
官方接口仅返回 productName + 营养素，**不提供商品编码、分类、价格**：
  - `nutritionDescription` 字段 160 条中仅 3 条非空，无分类价值
  - 关键词匹配会误判（巨无霸是汉堡但名称无「堡」字；麦香鱼是鱼类堡）
故采用人工白名单，保证每条都准确且具业务代表性。

【字段映射】
  productName→ name          energyKcal   → kcal
  protein     → protein_g    fat          → fat_g
  carbohydrate→ carb_gsodium    → sodium_mg
  calcium     → calcium_mg（额外保留，官方独有字段）

【价格说明】官方营养接口不含价格，故 price 取项目既有定价估算值，
已在页面标注「价格为估算，实时以官方 App 为准」。
"""

# ── 分类精选（每类恰好 5 个，共 4 类 20 个）────────────────
# 格式：productName → (category, price估算, is_high_protein, is_fried)
#
# 【为什么只有 4 类】饮料与饮品同属「喝的东西」，业务上无需分开，
# 合并为「饮品」一类，各 5 个，总计 20 条——演示场景 20 条比 25 条更聚焦。
MCD_OFFICIAL_PICKS: dict[str, tuple[str, float, bool, bool]] = {
    # 【汉堡】控卡刚需：去酱/双层等高蛋白优选
    "板烧鸡腿堡":        ("汉堡", 22.0, True,  False),
    "麦辣鸡腿汉堡":      ("汉堡", 22.0, True,  True),
    "巨无霸":            ("汉堡", 25.0, True,  True),
    "双层吉士汉堡":      ("汉堡", 23.0, True,  False),
    "麦香鸡":            ("汉堡", 20.0, True,  True),

    # 【小食】高蛋白与低卡优选
    "麦乐鸡5块":         ("小食", 13.0, True,  True),
    "麦辣鸡翅-2块":      ("小食", 14.0, True,  True),
    "大杯玉米杯":        ("小食", 8.5,  False, False),
    "中薯条":            ("小食", 9.0,  False, True),
    "脆薯饼":            ("小食", 7.0,  False, True),

    # 【甜点】低卡优先
    "菠萝派":            ("甜点", 7.0,  False, True),
    "香芋派":            ("甜点", 7.5,  False, True),
    "草莓新地":          ("甜点", 10.0, False, False),
    "奥利奥麦旋风":      ("甜点", 11.0, False, False),
    "圆筒冰淇淋":        ("甜点", 6.0,  False, False),

    # 【饮品】饮料与奶饮合并，含零卡选择
    "无糖可口可乐中杯":  ("饮品", 7.0, False, False),
    "可乐中杯":          ("饮品", 7.0,  False, False),
    "100%苹果汁":        ("饮品", 11.0, False, False),
    "纯牛奶（盒装）":    ("饮品", 8.0,  True,  False),
    "冰美式中杯":        ("饮品", 9.0,  False, False),
}

# ── 展示用免责声明（与接口返回保持一致口径）────────────────
OFFICIAL_SOURCE_NOTE = (
    "营养数据来自麦当劳官方 MCP 实时接口（list-nutrition-foods），"
    "共 160 条全量中精选 20 个代表性单品（每类 5 个）；价格为估算值，实时以官方 App 为准。"
)

# 类别顺序（前端展示用）
CATEGORY_ORDER = ["汉堡", "小食", "甜点", "饮品"]


def verify_picks(official_names: set[str]) -> dict:
    """校验白名单与官方实际返回是否一致。

    返回 {缺失的白名单单品, 官方未被选中的单品数}
    接入时调用此函数，避免官方数据变化导致静默失效。
    """
    missing = [n for n in MCD_OFFICIAL_PICKS if n not in official_names]
    return {
        "missing": missing,
        "total_picked": len(MCD_OFFICIAL_PICKS),
        "official_total": len(official_names),
        "coverage": f"{len(MCD_OFFICIAL_PICKS)}/{len(official_names)}",
    }