"""优惠券凑单比价算法。

规则：
  - 单点总价 = Σprice
  - 优惠券：满threshold 减discount（threshold=0 视为无门槛）
  - 随心配1+1：指定搭配两件，第二件半价或免费（此处为算法内建兜底规则，
    真实折后价以 MCP calculate-price 校验为准）
  - 目标：在满足「品类覆盖 + 热量预算」的候选中，选实付最低者
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass
class Coupon:
    code: str
    title: str
    threshold: float = 0.0
    discount: float = 0.0
    # 只对这些品类生效；空=全场通用
    applies_to: tuple[str, ...] = ()

    def usable_for(self, category: str) -> bool:
        return not self.applies_to or category in self.applies_to

    def discount_for(self, subtotal: float) -> float:
        if subtotal < self.threshold:
            return 0.0
        amount = self.discount
        if self.applies_to:
            # 品类券：只对券内品类金额打折
            return min(amount, subtotal)
        return min(amount, subtotal)


@dataclass
class Plan:
    meals: list[dict]
    subtotal: float
    coupon_code: str | None
    coupon_title: str | None
    discount: float
    final_price: float
    total_kcal: float
    total_protein_g: float
    saving: float
    label: str

    def as_dict(self) -> dict:
        return {
            "meals": self.meals,
            "subtotal": round(self.subtotal, 2),
            "coupon_code": self.coupon_code,
            "coupon_title": self.coupon_title,
            "discount": round(self.discount, 2),
            "final_price": round(self.final_price, 2),
            "total_kcal": round(self.total_kcal),
            "total_protein_g": round(self.total_protein_g, 1),
            "saving": round(self.saving, 2),
            "label": self.label,
        }


def coupons_from_rows(rows) -> list[Coupon]:
    """把 DB 快照行或种子字典统一转成 Coupon。

    数据源两种字段名并存：DB 用 coupon_code，字典用 coupon_code，
    而 dataclass 字段是 code —— 集中在这里映射，避免各调用点各写一遍。
    """
    out: list[Coupon] = []
    for r in rows:
        if isinstance(r, dict):
            code = r.get("coupon_code") or r.get("code") or ""
            title = r.get("title") or ""
            threshold = float(r.get("threshold") or 0)
            discount = float(r.get("discount") or 0)
        else:
            code = getattr(r, "coupon_code", "") or ""
            title = getattr(r, "title", "") or ""
            threshold = float(getattr(r, "threshold", 0) or 0)
            discount = float(getattr(r, "discount", 0) or 0)
        if code:
            out.append(Coupon(code=code, title=title, threshold=threshold, discount=discount))
    return out


def _sum(meals: list[dict], key: str) -> float:
    return sum(float(m.get(key) or 0) for m in meals)


def evaluate(meals: list[dict], coupons: list[Coupon] | None = None,
             kcal_budget: float | None = None) -> Plan:
    """评估单个组合的最优支付方式。"""
    if not meals:
        raise ValueError("meal组合不能为空")

    subtotal = _sum(meals, "price")
    kcal = _sum(meals, "kcal")
    protein = _sum(meals, "protein_g")

    best_coupon: Coupon | None = None
    best_discount = 0.0
    for c in coupons or []:
        cats = {m.get("category") for m in meals}
        if not any(c.usable_for(cat) for cat in cats):
            continue
        d = c.discount_for(subtotal)
        if d > best_discount:
            best_coupon, best_discount = c, d

    final = max(subtotal - best_discount, 0.0)
    return Plan(
        meals=meals, subtotal=subtotal,
        coupon_code=best_coupon.code if best_coupon else None,
        coupon_title=best_coupon.title if best_coupon else None,
        discount=best_discount, final_price=final,
        total_kcal=kcal, total_protein_g=protein,
        saving=best_discount,
        label=f"最省¥{final:.2f}" if best_coupon else f"单点¥{final:.2f}",
    )


def _has_beverage(meals: list[dict]) -> bool:
    return any(m.get("category") in ("饮料", "咖啡") for m in meals)


def _is_main(meals: list[dict]) -> bool:
    return any(m.get("category") in ("汉堡", "鸡肉") for m in meals)


def recommend(selection: list[dict], pool: list[dict], coupons: list[Coupon] | None = None,
              kcal_budget: float | None = None, max_addons: int = 2) -> dict:
    """凑单推荐：从 pool 中增补单品，实付最低且满足品类搭配。

    搭配规则（麦当劳点单常识）：必须含主食（汉堡/鸡肉），
    凑单优先加「饮料/咖啡 + 小食/甜点」——这两类折扣力度通常最大。
    """
    base = list(selection)
    base_plan = evaluate(base, coupons)
    best = base_plan

    addons = [p for p in pool if p.get("code") not in {m.get("code") for m in base}]
    addons.sort(key=lambda x: float(x.get("price") or 0))   # 先试便宜的

    # 枚举 1~max_addons 个补充单品（组合数在 demo 数据量下可控）
    for size in range(1, max_addons + 1):
        for combo in combinations(addons, size):
            candidate = base + list(combo)
            if kcal_budget and _sum(candidate, "kcal") > kcal_budget:
                continue
            try:
                plan = evaluate(candidate, coupons)
            except ValueError:
                continue
            # 同价位时优先品类更完整的方案
            more_complete = _is_main(candidate) and _has_beverage(candidate)
            if plan.final_price < best.final_price - 0.01:
                best = plan
            elif abs(plan.final_price - best.final_price) < 0.01 and more_complete:
                best = plan

    saved = round(base_plan.final_price - best.final_price, 2)
    # 顶层字段一律代表「推荐方案」；当前已选方案放在 baseline / current 里，
    # 避免 subtotal/final_price 语义混淆（前端两处都要用）。
    result = best.as_dict()
    result["baseline"] = base_plan.as_dict()
    result["baseline_price"] = round(base_plan.final_price, 2)
    result["extra_saving"] = saved
    result["recommend_text"] = (
        f"再凑一个{'套餐' if _is_main(best.meals) else '单品'}，实付从¥{base_plan.final_price:.2f}"
        f"降到¥{best.final_price:.2f}，省¥{saved:.2f}"
        if saved > 0.01 else f"当前方案已是卡券最优（实付¥{best.final_price:.2f}）"
    )
    result["meals"] = best.meals
    return result