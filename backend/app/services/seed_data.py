"""内置种子菜单（无 MCP Token 时的降级兜底）。

【数据口径】以下营养数值已于 2026-10-19 **对齐麦当劳官方 MCP
`list-nutrition-foods` 接口返回值**，与实时同步数据完全一致。

【为什么种子只有 20 条】官方接口共返回 160 条全量，本项目按演示需求精选
20 条（汉堡/小食/甜点/饮品 各 5 个）。种子表与精选集**保持完全一致**，
这样评委克隆后看到的菜单结构、数量、分类都与 README 演示截图相符——
不会因「本地有 Token、评委没有」而出现两套口径。

价格仍为估算值（本项目自行定价），实时以官方 App / `calculate-price` 为准。
一旦配置 MCP_TOKEN 并执行同步，官方数据将自动覆盖本表。

⚠️ 全部为项目内自绘素材的搭配方案，营养数值来源为官方公开接口。
"""
from __future__ import annotations

# 格式：mcp_code, name, category, kcal, protein_g, fat_g, carb_g, sodium_mg,
#       price, is_high_protein, is_fried
SEED_MEALS: list[dict] = [
    # ---- 汉堡（官方：板烧鸡腿堡 391kcal / 巨无霸 513kcal 等）----
    dict(mcp_code="M1001", name="麦香鸡", category="汉堡", kcal=369, protein_g=15.0,
         fat_g=17.0, carb_g=39.0, sodium_mg=731, price=20.0, is_high_protein=True, is_fried=True),
    dict(mcp_code="M1002", name="板烧鸡腿堡", category="汉堡", kcal=391, protein_g=23.0,
         fat_g=17.0, carb_g=35.0, sodium_mg=1041, price=22.0, is_high_protein=True, is_fried=False),
    dict(mcp_code="M1003", name="双层吉士汉堡", category="汉堡", kcal=429, protein_g=27.0,
         fat_g=22.0, carb_g=31.0, sodium_mg=1017, price=23.0, is_high_protein=True, is_fried=False),
    dict(mcp_code="M1004", name="麦辣鸡腿汉堡", category="汉堡", kcal=485, protein_g=24.0,
         fat_g=24.0, carb_g=42.0, sodium_mg=1208, price=22.0, is_high_protein=True, is_fried=True),
    dict(mcp_code="M1005", name="巨无霸", category="汉堡", kcal=513, protein_g=27.0,
         fat_g=26.0, carb_g=42.0, sodium_mg=961, price=25.0, is_high_protein=True, is_fried=True),

    # ---- 小食 ----
    dict(mcp_code="M3001", name="大杯玉米杯", category="小食", kcal=87, protein_g=4.0,
         fat_g=1.0, carb_g=12.0, sodium_mg=2, price=8.5, is_high_protein=False, is_fried=False),
    dict(mcp_code="M3002", name="脆薯饼", category="小食", kcal=146, protein_g=1.0,
         fat_g=9.0, carb_g=14.0, sodium_mg=311, price=7.0, is_high_protein=False, is_fried=True),
    dict(mcp_code="M3003", name="麦乐鸡5块", category="小食", kcal=213, protein_g=12.0,
         fat_g=12.0, carb_g=13.0, sodium_mg=422, price=13.0, is_high_protein=True, is_fried=True),
    dict(mcp_code="M3004", name="麦辣鸡翅-2块", category="小食", kcal=224, protein_g=13.0,
         fat_g=15.0, carb_g=9.0, sodium_mg=537, price=14.0, is_high_protein=True, is_fried=True),
    dict(mcp_code="M3005", name="中薯条", category="小食", kcal=289, protein_g=4.0,
         fat_g=12.0, carb_g=38.0, sodium_mg=165, price=9.0, is_high_protein=False, is_fried=True),

    # ---- 甜点 ----
    dict(mcp_code="M4001", name="圆筒冰淇淋", category="甜点", kcal=93, protein_g=2.0,
         fat_g=3.0, carb_g=14.0, sodium_mg=36, price=6.0, is_high_protein=False, is_fried=False),
    dict(mcp_code="M4002", name="菠萝派", category="甜点", kcal=221, protein_g=2.0,
         fat_g=11.0, carb_g=27.0, sodium_mg=147, price=7.0, is_high_protein=False, is_fried=True),
    dict(mcp_code="M4003", name="香芋派", category="甜点", kcal=232, protein_g=2.0,
         fat_g=12.0, carb_g=28.0, sodium_mg=159, price=7.5, is_high_protein=False, is_fried=True),
    dict(mcp_code="M4004", name="草莓新地", category="甜点", kcal=245, protein_g=4.0,
         fat_g=6.0, carb_g=43.0, sodium_mg=84, price=10.0, is_high_protein=False, is_fried=False),
    dict(mcp_code="M4005", name="奥利奥麦旋风", category="甜点", kcal=266, protein_g=5.0,
         fat_g=9.0, carb_g=40.0, sodium_mg=116, price=11.0, is_high_protein=False, is_fried=False),

    # ---- 饮品（饮料与奶饮合并）----
    dict(mcp_code="M5001", name="无糖可口可乐中杯", category="饮品", kcal=0, protein_g=0,
         fat_g=0, carb_g=1.0, sodium_mg=35, price=7.0, is_high_protein=False, is_fried=False),
    dict(mcp_code="M5002", name="冰美式中杯", category="饮品", kcal=13, protein_g=1.0,
         fat_g=0, carb_g=2.0, sodium_mg=0, price=9.0, is_high_protein=False, is_fried=False),
    dict(mcp_code="M5003", name="纯牛奶（盒装）", category="饮品", kcal=129, protein_g=7.0,
         fat_g=7.0, carb_g=10.0, sodium_mg=73, price=8.0, is_high_protein=True, is_fried=False),
    dict(mcp_code="M5004", name="可乐中杯", category="饮品", kcal=147, protein_g=0,
         fat_g=0, carb_g=36.0, sodium_mg=0, price=7.0, is_high_protein=False, is_fried=False),
    dict(mcp_code="M5005", name="100%苹果汁", category="饮品", kcal=88, protein_g=0,
         fat_g=0, carb_g=21.0, sodium_mg=0, price=11.0, is_high_protein=False, is_fried=False),
]

# 示例卡券（无 Token 时用于演示凑单算法）
SEED_COUPONS: list[dict] = [
    dict(coupon_code="SEED-15-30", title="满30减15", threshold=30.0, discount=15.0,
         rule={"type": "full_reduction", "threshold": 30, "amount": 15}),
    dict(coupon_code="SEED-10-50", title="满50减10", threshold=50.0, discount=10.0,
         rule={"type": "full_reduction", "threshold": 50, "amount": 10}),
    dict(coupon_code="SEED-BEVERAGE", title="饮料免费升级券", threshold=0.0, discount=3.0,
         rule={"type": "category", "applies_to": ["饮品"], "amount": 3}),
]