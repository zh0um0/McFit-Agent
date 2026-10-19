"""TDEE 代谢模型（Mifflin-St Jeor）。

公式口径（国际权威，PRD 模块1）：
  男：BMR = 10×体重kg + 6.25×身高cm − 5×年龄 + 5
  女：BMR = 10×体重kg + 6.25×身高cm − 5×年龄 − 161
  TDEE = BMR × 活动系数（久坐1.2 / 轻度1.375 / 中度1.55 / 高强1.725）
"""
from __future__ import annotations

from dataclasses import dataclass

ACTIVITY_FACTORS: dict[str, tuple[str, float]] = {
    "sedentary": ("久坐（几乎不运动）", 1.2),
    "light": ("轻度（每周1-3次）", 1.375),
    "moderate": ("中度（每周3-5次）", 1.55),
    "active": ("高强（每周6-7次）", 1.725),
}

GOALS: dict[str, tuple[str, float]] = {
    # 目标：单餐热量上限系数 × TDEE × 目标分配比例
    "cut": ("减脂", 0.82),
    "keep": ("维持", 1.00),
    "lean_bulk": ("增肌（lean bulk）", 1.10),
}

# 单餐占总摄入比例：早20% / 午40% / 晚40%
MEAL_RATIO = {"早餐": 0.20, "午餐": 0.40, "晚餐": 0.40}

# 蛋白质目标 g/kg 体重（减脂期高蛋白保肌）
PROTEIN_PER_KG = {"cut": (1.6, 2.0), "keep": (1.2, 1.6), "lean_bulk": (1.6, 2.2)}


@dataclass(frozen=True)
class TdeeResult:
    bmr: float
    tdee: float
    daily_target: float
    protein_min_g: float
    protein_max_g: float
    meal_limit: dict[str, float]
    activity_label: str
    goal_label: str

    def as_dict(self) -> dict:
        return {
            "bmr": round(self.bmr, 1),
            "tdee": round(self.tdee, 1),
            "daily_target": round(self.daily_target, 1),
            "protein_min_g": round(self.protein_min_g, 1),
            "protein_max_g": round(self.protein_max_g, 1),
            "meal_limit": {k: round(v, 1) for k, v in self.meal_limit.items()},
            "activity_label": self.activity_label,
            "goal_label": self.goal_label,
        }


def calc_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor 基础代谢率。"""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


def calc_tdee(weight_kg: float, height_cm: float, age: int, gender: str,
              activity: str = "sedentary") -> float:
    factor = ACTIVITY_FACTORS.get(activity, ACTIVITY_FACTORS["sedentary"])[1]
    return calc_bmr(weight_kg, height_cm, age, gender) * factor


def compute_profile_metrics(weight_kg: float, height_cm: float, age: int, gender: str,
                            activity: str = "sedentary", goal: str = "cut") -> TdeeResult:
    """一次性算出档案页需要的全部指标。"""
    if gender not in ("male", "female"):
        raise ValueError("gender 必须为 male 或 female")
    if not (0 < age <= 120):
        raise ValueError("年龄需在 1-120 之间")
    if not (50 <= height_cm <= 250):
        raise ValueError("身高需在 50-250 cm 之间")
    if not (20 <= weight_kg <= 400):
        raise ValueError("体重需在 20-400 kg 之间")

    bmr = calc_bmr(weight_kg, height_cm, age, gender)
    tdee = bmr * ACTIVITY_FACTORS.get(activity, ACTIVITY_FACTORS["sedentary"])[1]
    daily_target = tdee * GOALS.get(goal, GOALS["cut"])[1]
    pmin, pmax = PROTEIN_PER_KG.get(goal, PROTEIN_PER_KG["cut"])

    return TdeeResult(
        bmr=bmr,
        tdee=tdee,
        daily_target=daily_target,
        protein_min_g=pmin * weight_kg,
        protein_max_g=pmax * weight_kg,
        meal_limit={name: daily_target * r for name, r in MEAL_RATIO.items()},
        activity_label=ACTIVITY_FACTORS.get(activity, ACTIVITY_FACTORS["sedentary"])[0],
        goal_label=GOALS.get(goal, GOALS["cut"])[0],
    )


def evaluate_meal_status(total_kcal: float, meal_limit: float) -> str:
    """判断本餐状态：达标 / 维持 / 超标。

    meal_limit 传「该餐段的热量上限」（由 TdeeResult.meal_limit 给出），
    不再在此处二次乘餐段比例——避免同一上限被缩放两次。
    """
    if meal_limit <= 0:
        return "维持"
    ratio = total_kcal / meal_limit
    if ratio <= 0.95:
        return "达标"
    if ratio <= 1.10:
        return "维持"
    return "超标"


def meal_limit_of(daily_target: float, meal_name: str = "午餐") -> float:
    """由整日目标推算某餐段上限（daily_target 口径）。"""
    return daily_target * MEAL_RATIO.get(meal_name, 0.40)


def checkin_status(daily_total_kcal: float, daily_target: float) -> str:
    """当日打卡状态（对比整日目标）。"""
    if daily_target <= 0:
        return "维持"
    ratio = daily_total_kcal / daily_target
    if ratio <= 1.0:
        return "达标"
    if ratio <= 1.1:
        return "维持"
    return "超标"