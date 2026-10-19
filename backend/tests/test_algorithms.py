"""P1 验收：算法层单元测试（TDEE / 运动换算 / 凑单比价）。"""
from __future__ import annotations

import pytest

from app.services import exercise, pricing, tdee


# ---------------- TDEE ----------------
def test_bmr_male_formula():
    #10×70 + 6.25×175 − 5×30 + 5 = 700 + 1093.75 − 150 + 5 = 1648.75
    assert tdee.calc_bmr(70, 175, 30, "male") == pytest.approx(1648.75)


def test_bmr_female_formula():
    # 700 + 1093.75 − 150 − 161 = 1482.75
    assert tdee.calc_bmr(70, 175, 30, "female") == pytest.approx(1482.75)


def test_tdee_applies_activity_factor():
    bmr = tdee.calc_bmr(70, 175, 30, "male")
    assert tdee.calc_tdee(70, 175, 30, "male", "sedentary") == pytest.approx(bmr * 1.2)
    assert tdee.calc_tdee(70, 175, 30, "male", "active") == pytest.approx(bmr * 1.725)


def test_compute_metrics_protein_range():
    r = tdee.compute_profile_metrics(80, 180, 28, "male", "light", "cut")
    # 减脂期 1.6~2.0 g/kg
    assert r.protein_min_g == pytest.approx(128.0)
    assert r.protein_max_g == pytest.approx(160.0)


def test_meal_limits_sum_to_daily_target():
    r = tdee.compute_profile_metrics(65, 170, 30, "female", "sedentary", "cut")
    total = sum(r.meal_limit.values())
    assert total == pytest.approx(r.daily_target)


@pytest.mark.parametrize("kwargs", [
    dict(weight_kg=10, height_cm=175, age=30, gender="male"),      # 体重过低
    dict(weight_kg=70, height_cm=10, age=30, gender="male"),      # 身高过低
    dict(weight_kg=70, height_cm=175, age=999, gender="male"),    # 年龄越界
    dict(weight_kg=70, height_cm=175, age=30, gender="other"),    # 性别非法
])
def test_invalid_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        tdee.compute_profile_metrics(**kwargs)


def test_meal_status_thresholds():
    limit = 600.0
    assert tdee.evaluate_meal_status(500, limit) == "达标"
    assert tdee.evaluate_meal_status(570, limit) == "达标"
    assert tdee.evaluate_meal_status(620, limit) == "维持"
    assert tdee.evaluate_meal_status(660, limit) == "维持"
    assert tdee.evaluate_meal_status(700, limit) == "超标"


def test_meal_limit_of_uses_ratio():
    assert tdee.meal_limit_of(2000.0, "早餐") == pytest.approx(400.0)
    assert tdee.meal_limit_of(2000.0, "午餐") == pytest.approx(800.0)
    assert tdee.meal_limit_of(2000.0, "晚餐") == pytest.approx(800.0)


def test_checkin_status_thresholds():
    assert tdee.checkin_status(1900, 2000) == "达标"
    assert tdee.checkin_status(2050, 2000) == "维持"
    assert tdee.checkin_status(2400, 2000) == "超标"


# ---------------- 运动代偿 ----------------
def test_jog_conversion_matches_formula():
    plans = {p.code: p for p in exercise.convert(300, 70)}
    # 300 / (70 × 1.036) ≈ 4.135 km
    assert plans["jog"].amount == pytest.approx(300 / (70 * 1.036), rel=1e-3)


def test_pushup_and_rope_conversion():
    plans = {p.code: p for p in exercise.convert(110, 70)}
    assert plans["pushup"].amount == pytest.approx(200.0)   # 110 / 0.55
    assert plans["rope"].amount == pytest.approx(10.0)       # 110 / 11


def test_zero_kcal_returns_empty():
    assert exercise.convert(0, 70) == []


def test_narrate_within_budget_is_positive():
    r = exercise.narrate(500, 600, 70)
    assert r["status"] == "达标"
    assert "自律" in r["message"]


def test_narrate_never_has_empty_placeholder():
    """回归：达标时曾出现「约  的运动量」——gap 换算不能为空列表。"""
    for total, limit in [(500, 600), (626, 800), (300, 300.5), (900, 1000)]:
        r = exercise.narrate(total, limit, 70)
        assert "约  " not in r["message"]
        assert "即可回归平衡 -" not in r["message"]
        assert r["plans"] or total == limit


def test_narrate_exact_limit_has_no_gap():
    r = exercise.narrate(600, 600, 70)
    assert r["status"] == "维持"
    assert r["gap_kcal"] == 0


def test_narrate_over_budget_is_action_oriented():
    r = exercise.narrate(800, 600, 70)
    assert r["status"] == "超标"
    assert r["gap_kcal"] == 200
    # 正向激励红线：不得出现反省/放纵/惩罚
    for banned in ("反省", "放纵", "惩罚"):
        assert banned not in r["message"]
    assert r["plans"]


def test_narrate_maintenance_zone():
    r = exercise.narrate(640, 600, 70)
    assert r["status"] == "维持"
    assert r["headline"] == "稳稳达标"


# ---------------- 凑单比价 ----------------
def _meal(code, name, price, kcal, category="汉堡", protein=10.0):
    return {"code": code, "name": name, "price": price, "kcal": kcal,
            "category": category, "protein_g": protein}


def test_evaluate_single_point():
    plan = pricing.evaluate([_meal("A", "堡", 22.0, 500)])
    assert plan.subtotal == 22.0
    assert plan.final_price == 22.0
    assert plan.coupon_code is None


def test_coupon_applied_when_threshold_met():
    coupon = pricing.Coupon("C1", "满30减15", 30.0, 15.0)
    plan = pricing.evaluate([_meal("A", "堡", 22.0, 500), _meal("B", "可乐", 7.0, 140,
                                                             "饮料")], [coupon])
    assert plan.subtotal == 29.0
    assert plan.discount == 0.0          # 29 < 30，不满足门槛

    plan2 = pricing.evaluate([_meal("A", "堡", 22.0, 500), _meal("B", "可乐", 8.0, 140,
                                                              "饮料")], [coupon])
    assert plan2.subtotal == 30.0
    assert plan2.discount == 15.0
    assert plan2.final_price == 15.0


def test_evaluate_picks_best_coupon():
    # 两张券门槛都满足，算法必须选减免额更大的那张
    coupons = [
        pricing.Coupon("C1", "满30减15", 30.0, 15.0),
        pricing.Coupon("C2", "满20减8", 20.0, 8.0),
    ]
    plan = pricing.evaluate([_meal("A", "堡", 35.0, 500)], coupons)
    assert plan.coupon_code == "C1"
    assert plan.discount == 15.0
    assert plan.final_price == 20.0


def test_coupon_threshold_not_met_is_skipped():
    coupons = [pricing.Coupon("C1", "满30减15", 30.0, 15.0),
               pricing.Coupon("C2", "满20减8", 20.0, 8.0)]
    plan = pricing.evaluate([_meal("A", "堡", 25.0, 500)], coupons)
    assert plan.coupon_code == "C2"      # C1 门槛 30 未达成
    assert plan.final_price == 17.0


def test_empty_selection_raises():
    with pytest.raises(ValueError):
        pricing.evaluate([])


def test_recommend_finds_cheaper_combo():
    pool = [
        _meal("M1", "麦辣", 22.0, 516, "鸡肉"),
        _meal("D1", "可乐", 7.0, 140, "饮料"),
        _meal("F1", "薯条", 9.0, 335, "小食"),
    ]
    coupons = [pricing.Coupon("C1", "满30减15", 30.0, 15.0)]
    base = [pool[0]]
    baseline = pricing.evaluate(base, coupons).final_price

    result = pricing.recommend(base, pool, coupons)
    assert result["baseline_price"] == baseline
    assert result["final_price"] <= baseline
    assert result["extra_saving"] >= 0
    assert "凑" in result["recommend_text"] or "最优" in result["recommend_text"]


def test_recommend_respects_kcal_budget():
    pool = [
        _meal("M1", "麦辣", 22.0, 516, "鸡肉"),
        _meal("H1", "豪炸", 30.0, 900, "小食"),
    ]
    result = pricing.recommend([pool[0]], pool, [], kcal_budget=600)
    assert result["total_kcal"] <= 600     # 高热量单品不得入选

# ---------------- 回归：未吃满不应做运动代偿（v1.2 语义修正）----------------
# 旧实现两种情况都调 convert()，导致「今日可补足：慢跑 0.9 公里」——
# 把尚未摄入的热量折算成运动量，逻辑荒谬。
def test_gap_under_target_has_no_exercise_plan():
    r = exercise.suggestion_for_gap(922, 78)
    assert r["state"] == "under"
    assert r["headline"] == "今日还可吃"
    assert r["plans"] == [], "未吃满时不应给出任何运动代偿"
    assert "慢跑" not in r["message"]
    assert "公里" not in r["message"]
    assert "922" in r["message"]


def test_gap_exactly_on_target():
    r = exercise.suggestion_for_gap(0, 78)
    assert r["state"] == "on_target"
    assert r["plans"] == []
    assert "刚好" in r["message"]


def test_gap_over_target_gives_exercise_plan():
    r = exercise.suggestion_for_gap(-571, 78)
    assert r["state"] == "over"
    assert r["headline"] == "今日已超出"
    assert len(r["plans"]) >= 2
    assert "慢跑" in r["message"]
    assert "571" in r["message"]


def test_small_overflow_still_convertible():
    """小幅超出也要能换算（不能因量小就返回空）"""
    r = exercise.suggestion_for_gap(-180, 78)
    assert r["plans"], "超出 180 kcal 仍应给出可执行的运动建议"


def test_negative_gap_not_truncated_by_caller():
    """接口层不得用 max(gap,0) 截断，否则超标建议永远显示不出来。"""
    import inspect
    from app.api.v1 import orders
    src = inspect.getsource(orders.today_summary)
    assert "max(metrics.daily_target - kcal, 0)" not in src, \
        "today_summary 仍把差额截断为非负，超出场景会被抹掉"
    assert "suggestion_for_gap(gap, weight)" in src
