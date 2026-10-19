"""自绘 SVG 食物图标库（贴纸引擎专用）。

【合规声明】全部为项目内自绘线条简笔图标，**严禁使用麦当劳官方 Logo、
餐品实拍图或官方物料**——此为参赛声明的知识产权红线。

【设计规范】
  - 统一 viewBox 100×100，所有图标线条粗细、圆角风格一致
  - 采用「类别基础形 + 单品特征细节」两层结构：
    同类别共享轮廓骨架（视觉统一），单品叠加 1~2 处辨识特征
  - 线条风格：stroke 3，round linecap/linejoin，fill 均为none
"""
from __future__ import annotations

# ── 类别基础骨架（4 类）────────────────────────────────────
# 每个骨架描述该类别的典型外形，单品图标在此基础上叠加特征细节
_CATEGORY_BASE: dict[str, list[str]] = {
    # 汉堡：上层面包弧 + 夹心横带 + 下层面包
    "汉堡": [
        "M20 44 q30-26 60 0",                      # 上层面包
        "M16 48 h68 v9 h-68 z",                    # 夹心（顶部横带）
        "M18 62 h64 a4 4 0 0 1 4 4 v5 a4 4 0 0 1 -4 4 h-64 a4 4 0 0 1 -4-4 v-5 a4 4 0 0 1 4-4 z",
        "M20 44 q4-10 12-10 M50 34 q10 0 14 10",   # 面包顶部起伏
    ],
    # 小食：纸杯容器 + 杯口 + 吸管
    "小食": [
        "M30 28 h40 l-4 50 a5 5 0 0 1 -5 4 h-22 a5 5 0 0 1 -5-4 z",   # 杯体
        "M28 28 h44",                             # 杯口
        "M46 28 l6-12",                           # 吸管
    ],
    # 甜点：甜品杯 + 顶部半球（简洁，不加勺，避免视觉噪声）
    "甜点": [
        "M28 48 h44 l-5 30 a5 5 0 0 1 -5 4 h-24 a5 5 0 0 1 -5-4 z",   # 杯身
        "M28 48 q22-28 44 0",                     # 顶部半球
        "M26 48 h48",                             # 杯口线
    ],
    # 饮品：马克杯 + 杯盖 + 吸管 + 杯把
    "饮品": [
        "M26 34 h38 v44 a6 6 0 0 1 -6 6 h-26 a6 6 0 0 1 -6-6 z",       # 杯身
        "M24 34 l6-14 h32 l6 14",                 # 杯盖
        "M32 20 v-10",                            # 吸管
        "M64 42 h7 a9 9 0 0 1 0 18 h-7",          # 杯把（居中偏上）
    ],
}

# ── 单品特征细节（叠加在骨架之上）──────────────────────────
# key = 官方单品名；value = 该单品独有的辨识特征路径
# 设计原则：细节必须落在骨架的「空白区」而非轮廓内，否则肉眼看不出差别
_ITEM_DETAIL: dict[str, list[str]] = {
    # ---- 汉堡类：靠「夹心层数 + 顶部配料」区分 ----
    # 层数是最直观的辨识维度：1 层=单层堡，2 层=双层，3 层=巨无霸
    "板烧鸡腿堡": ["M24 52 h52"],                              # 单层肉饼
    "麦辣鸡腿汉堡": ["M24 51 h14 M40 51 h14 M56 51 h12"],        # 三段=辣味块
    "巨无霸": ["M24 50 h52", "M24 56 h52"],                    # 三层=双夹心线
    "双层吉士汉堡": ["M24 49 h52", "M24 58 h52"],              # 双层肉饼
    "麦香鸡": ["M36 42 q14-6 28 0", "M40 38 q10-4 20 0"],        # 顶部炸鸡双层盖

    # ---- 小食类：靠杯内物品形状区分 ----
    "麦乐鸡5块": ["M36 46 h28 v14 h-28 z", "M50 46 v14"],# 方块鸡块
    "麦辣鸡翅-2块": ["M34 50 l16-8 12 14-16 8 z"],            # 鸡翅菱形
    "大杯玉米杯": ["M36 48 h28 l-3 12 h-22 z", "M42 50 v8 M52 50 v8"],  # 玉米粒
    "中薯条": ["M36 40 v32 M46 40 v32 M56 40 v32"],            # 竖条薯
    "脆薯饼": ["M34 50 q16-8 32 0 v12 q-16 8 -32 0 z"],        # 椭圆薯饼

    # ---- 甜点类：靠顶部装饰区分 ----
    "菠萝派": ["M38 40 l4-8 4 8", "M50 40 l4-8 4 8"],          # 派皮两点
    "香芋派": ["M40 38 q10-6 20 0 v6 q-10 6 -20 0 z"],          # 芋泥块
    "草莓新地": ["M44 24 l4-10 4 10"],                          # 草莓尖
    "奥利奥麦旋风": ["M40 36 h8 v6 h-8 z", "M52 36 h8 v6 h-8 z"],  # 巧克力碎
    "圆筒冰淇淋": ["M38 18 h24 l-4 16 h-16 z", "M46 18 v-8"],   # 甜筒

    # ---- 饮品类：靠杯身内图案区分 ----
    "无糖可口可乐中杯": ["M34 50 h26 M34 62 h26"],# 双横线=无糖
    "可乐中杯": ["M38 52 q6 6 0 12 q6-6 0-12", "M48 52 q6 6 0 12"],  # 气泡
    "100%苹果汁": ["M44 54 q8-10 12 0 q4 10-4 10z", "M48 44 v-8"],  # 苹果
    "纯牛奶（盒装）": ["M36 52 h24 v18 h-24 z", "M44 52 l8-8"],   # 奶盒
    "冰美式中杯": ["M38 56 h8 v12 h-8 z", "M52 56 h6 v12 h-6 z"], # 冰块
}

# ── 兜底：名称未匹配时按关键词猜测，猜不到用通用餐盘──────
_FALLBACK_RULES: list[tuple[tuple[str, ...], str]] = [
    (("麦满分", "堡"), "汉堡"),
    (("鸡", "翅", "乐鸡", "脆鸡"), "小食"),
    (("薯", "玉米", "饼", "脆"), "小食"),
    (("派", "新地", "旋风", "冰淇淋", "雪冰"), "甜点"),
    (("可乐", "雪碧", "咖啡", "美式", "牛奶", "汁", "茶"), "饮品"),
]


def resolve_category(name: str, default: str = "") -> str:
    """按单品名推断类别：先查精确映射，再走关键词兜底。"""
    if name in MCD_CATEGORY_HINT:
        return MCD_CATEGORY_HINT[name]
    for keywords, cat in _FALLBACK_RULES:
        if any(k in name for k in keywords):
            return cat
    return default or "汉堡"


def get_icon_paths(name: str, category: str = "") -> list[str]:
    """返回该单品图标的全部路径：类别骨架 + 单品特征。"""
    cat = category or resolve_category(name)
    base = list(_CATEGORY_BASE.get(cat, _CATEGORY_BASE["汉堡"]))
    detail = _ITEM_DETAIL.get(name)
    if detail is None:
        # 未单独设计的单品，给一个通用装饰以免图标空洞
        detail = ["M44 20 q6-6 12 0", "M70 46 q4 4 0 8"]
    return base + detail


def render_icon(name: str, category: str = "", color: str = "#1f9d55",
                size: float = 60, x: float = 0, y: float = 0) -> str:
    """渲染单个商品图标为<g> 分组。

    内部坐标系 100×100，通过 translate(x,y) + scale(size/100) 缩放。
    详情路径用更粗的线宽，保证缩小到 60px 时仍能看清差异。
    """
    cat = category or resolve_category(name)
    base = _CATEGORY_BASE.get(cat, _CATEGORY_BASE["汉堡"])
    detail = _ITEM_DETAIL.get(name) or ["M44 20 q6-6 12 0", "M70 46 q4 4 0 8"]
    scale = size / 100.0

    body = (
        f'<g transform="translate({x:.2f},{y:.2f}) scale({scale:.4f})" '
        f'stroke="{color}" stroke-width="3" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        + "".join(f'<path d="{d}"/>' for d in base)
        + "</g>"
        # 详情层单独描边并加粗，避免与骨架糊在一起
        + f'<g transform="translate({x:.2f},{y:.2f}) scale({scale:.4f})" '
          f'stroke="{color}" stroke-width="4.2" fill="none" '
          f'stroke-linecap="round" stroke-linejoin="round">'
        + "".join(f'<path d="{d}"/>' for d in detail)
        + "</g>"
    )
    return body


# 类别提示表（单品 → 类别），避免每次都跑关键词匹配
MCD_CATEGORY_HINT: dict[str, str] = {
    "板烧鸡腿堡": "汉堡", "麦辣鸡腿汉堡": "汉堡", "巨无霸": "汉堡",
    "双层吉士汉堡": "汉堡", "麦香鸡": "汉堡",
    "麦乐鸡5块": "小食", "麦辣鸡翅-2块": "小食", "大杯玉米杯": "小食",
    "中薯条": "小食", "脆薯饼": "小食",
    "菠萝派": "甜点", "香芋派": "甜点", "草莓新地": "甜点",
    "奥利奥麦旋风": "甜点", "圆筒冰淇淋": "甜点",
    "无糖可口可乐中杯": "饮品", "可乐中杯": "饮品", "100%苹果汁": "饮品",
    "纯牛奶（盒装）": "饮品", "冰美式中杯": "饮品",
}


def render_icon_at(name: str, category: str = "", color: str = "#1f9d55",
                   size: float = 60, x: float = 0, y: float = 0) -> str:
    """render_icon 的别名（语义更清晰）。"""
    return render_icon(name, category, color, size, x, y)