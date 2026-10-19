"""运动代偿换算器 —— 全程正向激励口径（PRD 模块3 v1.1）。

基准（估算值，仅供参考）：
  慢跑8km/h: kcal ≈ 体重kg × 距离km × 1.036
  俯卧撑:   0.5~0.6 kcal/个（取 0.55）
  跳绳中速: 10~12 kcal/分钟（取 11）
  快走5km/h: 130 步 ≈ 5 kcal

文案禁止出现「反省/放纵/惩罚」类字眼；超标给的是「低门槛补救动作」。
"""
from __future__ import annotations

from dataclasses import dataclass

SEED_PRESETS: list[tuple[str, str, str, float, int]] = [
    ("jog", "慢跑(8km/h)", "km", 1.036, 1),
    ("walk", "快走(5km/h)", "step", 5 / 130, 2),
    ("rope", "跳绳(中速)", "minute", 11.0, 3),
    ("pushup", "俯卧撑", "rep", 0.55, 4),
    ("cycling", "骑行(16km/h)", "minute", 8.5, 5),
]


@dataclass(frozen=True)
class ExercisePlan:
    """单项运动的代偿方案。"""
    code: str
    name: str
    amount: float
    unit: str
    kcal: float
    text: str

    def as_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "amount": round(self.amount, 1),
                "unit": self.unit, "kcal": round(self.kcal), "text": self.text}


_UNIT_TEXT = {"km": "公里", "minute": "分钟", "rep": "个", "step": "步"}


def _fmt(amount: float, unit: str) -> str:
    amt = round(amount, 1)
    amt = int(amt) if float(amt).is_integer() else amt
    return f"{amt} {_UNIT_TEXT.get(unit, unit)}"


def convert(kcal: float, weight_kg: float, presets=None) -> list[ExercisePlan]:
    """把热量缺口换算为多项运动参考量，按直观程度排序。"""
    if kcal <= 0 or weight_kg <= 0:
        return []
    table = {p[0]: p for p in (presets or SEED_PRESETS)}
    out: list[ExercisePlan] = []

    for code in ("jog", "walk", "rope", "pushup"):
        p = table.get(code)
        if not p:
            continue
        _, name, unit, factor, _ = p
        if code == "jog":
            amount = kcal / (weight_kg * factor)      # 慢跑距离与体重相关
        else:
            amount = kcal / factor
        out.append(ExercisePlan(
            code=code, name=name, amount=amount, unit=unit, kcal=kcal,
            text=f"{name} {_fmt(amount, unit)}",
        ))
    return out


def _plans_to_dict(plans: list[ExercisePlan]) -> list[dict]:
    return [p.as_dict() for p in plans]


def narrate(total_kcal: float, limit_kcal: float, weight_kg: float,
            presets=None) -> dict:
    """生成正向激励文案 + 代偿建议。

    返回：{status, gap_kcal, headline, message, plans:[...]}
    """
    gap = abs(total_kcal - limit_kcal)
    # 达标时用「剩余预算」换算可消耗运动量；超标时用「超出量」换算需补足运动量。
    # 注意不能用 convert(0, ...)：那会返回空列表，导致文案里的运动量为空。
    plans = convert(gap, weight_kg, presets) if gap > 0 else []

    if total_kcal <= limit_kcal * 0.95:
        status = "达标"
        headline = "控卡成功"
        best = plans[0].text if plans else "散步放松"
        message = (f"本餐摄入 {round(total_kcal)} kcal，处于健康减脂区间！"
                   f"还余 {round(gap)} kcal 预算，约 {best} 就能消耗掉，今天也是自律的一天 🎉")
    elif total_kcal <= limit_kcal * 1.10:
        status = "维持"
        headline = "稳稳达标"
        message = (f"本餐摄入 {round(total_kcal)} kcal，接近单餐上限 {round(limit_kcal)} kcal。"
                   f"保持这个节奏就很好，明天继续加油！")
    else:
        status = "超标"
        headline = "轻微超出"
        top2 = "、".join(p.text for p in plans[:2]) if plans else "快走一会儿"
        message = (f"本餐超出预算 {round(gap)} kcal —— {top2} 即可回归平衡。"
                   f"一次小调整不影响整体进度，明天继续！")

    return {
        "status": status,
        "headline": headline,
        "gap_kcal": round(abs(total_kcal - limit_kcal)),
        "message": message,
        "plans": _plans_to_dict(plans[:2] if status == "超标" else plans[:3]),
    }


def suggestion_for_gap(gap_kcal: float, weight_kg: float, presets=None) -> dict:
    """当日热量差额的处置建议（打卡页用）。

    语义澄清（v1.2 修正）：
      - gap_kcal > 0 表示**尚未吃满目标**，此时给出「还能吃多少」的建议，
        **不做运动代偿换算**——没吃满本来就不需要靠运动找补。
      - gap_kcal < 0 表示**超出目标**，此时才做运动代偿换算。
    旧实现两种情况都调 convert()，导致「今日可补足：慢跑 0.9 公里」
    这类把未摄入热量折算成运动量的荒谬文案。
    """
    gap = round(gap_kcal)

    if gap > 0:
        return {
            "gap_kcal": gap,
            "state": "under",
            "headline": "今日还可吃",
            "message": f"距今日目标还有 {gap} kcal 预算，"
                       f"优先安排高蛋白低脂的搭配（如麦香鸡 + 玉米杯）",
            "plans": [],
        }

    over = abs(gap)
    plans = convert(over, weight_kg, presets) if over > 0 else []
    if not plans:
        return {
            "gap_kcal": gap,
            "state": "on_target",
            "headline": "今日正好达标",
            "message": "今日摄入刚好等于目标，保持这个节奏就很好 🌟",
            "plans": [],
        }

    top = "、".join(p.text for p in plans[:2])
    return {
        "gap_kcal": gap,
        "state": "over",
        "headline": "今日已超出",
        "message": f"今日超出 {over} kcal —— {top} 即可回归平衡，明天继续！",
        "plans": _plans_to_dict(plans[:3]),
    }