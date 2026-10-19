"""端到端业务链路：档案 → 菜单 → 凑单 → 存档 → 打卡 → 日历 → 海报。

同时覆盖安全测试：越权访问、XSS 载荷、SQL 注入。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

PROFILE = {
    "gender": "male", "age": 30, "height_cm": 175, "weight_kg": 80,
    "activity_level": "light", "goal": "cut",
}


def _mkuser(client, name: str) -> dict:
    r = client.post("/api/v1/auth/register",
                    json={"username": name, "password": "pwd123456"})
    return {"headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}


def test_full_journey(client, auth):
    h = auth["headers"]

    # 1) 档案
    r = client.put("/api/v1/profile", json=PROFILE, headers=h)
    assert r.status_code == 200, r.text
    m = r.json()["metrics"]
    # BMR = 10×80 + 6.25×175 − 5×30 + 5 = 800 + 1093.75 − 150 + 5 = 1748.75
    # 接口按 1 位小数返回，故断言 1748.8
    assert m["bmr"] == pytest.approx(1748.75, abs=0.05)
    assert m["daily_target"] > 0
    assert m["protein_min_g"] == 128.0

    # 2) 菜单
    r = client.get("/api/v1/meals", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 20
    assert body["source"] == "seed"
    assert body["disclaimer"]

    # 3) 勾选 + 凑单
    r = client.post("/api/v1/meals/calculate",
                    json={"codes": ["M1001"]}, headers=h)
    assert r.status_code == 200, r.text
    calc = r.json()
    # 价格断言不可硬编码——种子价格会随官方数据对齐而调整，改为动态读取
    menu0 = {m["code"]: m for m in client.get(
        "/api/v1/meals", headers=h).json()["items"]}
    assert calc["baseline"]["subtotal"] == menu0["M1001"]["price"]
    assert calc["final_price"] <= calc["baseline"]["final_price"]
    assert calc["coupon_source"] == "seed"

    # 4) 存档
    # 注意：热量断言不可硬编码数字——种子数据已对齐官方接口，后续更新会连带改测试。
    # 改为按接口返回的实际值交叉校验，保证测试与数据解耦。
    r = client.post("/api/v1/orders",
                    json={"codes": ["M1001", "M3004", "M5005"]}, headers=h)
    assert r.status_code == 201, r.text
    order = r.json()

    menu = client.get("/api/v1/meals", headers=h).json()["items"]
    kcal_by_code = {m["code"]: m["kcal"] for m in menu}
    expected_kcal = (kcal_by_code["M1001"] + kcal_by_code["M3004"] + kcal_by_code["M5005"])
    assert order["total_kcal"] == expected_kcal
    assert order["status"] in ("达标", "维持", "超标")
    assert order["exercise_equivalent"]["message"]

    # 5) 今日汇总
    r = client.get("/api/v1/orders/today-summary", headers=h)
    assert r.status_code == 200
    s = r.json()
    assert s["order_count"] == 1
    assert s["has_profile"] is True
    assert "status" in s and "gap_kcal" in s

    # 6) 打卡
    r = client.post("/api/v1/checkin", json={
        "status": order["status"], "total_kcal": order["total_kcal"],
        "protein_g": order["total_protein_g"],
        "meals": [{"code": "M1001", "category": "鸡肉", "name": "麦辣鸡腿汉堡"},
                  {"code": "M3004", "category": "小食", "name": "大杯玉米杯"},
                  {"code": "M5005", "category": "饮品", "name": "冰美式中杯"}],
    }, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["sticker_length"] > 200

    # 7) 日历
    # 注意：不可硬编码月份与格子索引（曾因写死 2026-10 / index 12 导致跨天跑必失败），
    # 一律按「今天实际日期」推导，打卡落在哪天就该哪天有状态。
    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"
    r = client.get(f"/api/v1/checkin/calendar?month={month}", headers=h)
    assert r.status_code == 200
    cal = r.json()
    import calendar as _cal
    assert cal["days"] == _cal.monthrange(today.year, today.month)[1]
    assert cal["summary"]["checked_days"] == 1
    today_cell = next(c for c in cal["cells"] if c["day"] == today.day)
    assert today_cell["status"] == order["status"]
    assert today_cell["has_sticker"] is True

    # 8) 海报（脱敏校验）
    r = client.get("/api/v1/sticker/poster", headers=h)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["watermark"]
    # 脱敏校验：海报只允许暴露展示字段，不得出现任何身体原始数据字段名。
    # 注意必须检查「键名」而非全文搜单词——英文子串会误命中
    # （"age" 命中 "message"/"package"，"weight" 命中运动换算文案）。
    allowed = {"name", "category", "kcal"}
    assert p["items"] and all(set(i) <= allowed for i in p["items"])

    def _keys(obj) -> set[str]:
        out: set[str] = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                out.add(str(k))
                out |= _keys(v)
        elif isinstance(obj, list):
            for v in obj:
                out |= _keys(v)
        return out

    forbidden = {"weight", "weight_kg", "target_weight", "height", "height_cm",
                 "tdee", "bmr", "daily_target", "protein_target", "gender", "age"}
    assert not (forbidden & _keys(p))

    # 9) 统计
    r = client.get("/api/v1/sticker/stats", headers=h)
    assert r.json()["total_days"] == 1


def test_profile_missing_404(client, auth):
    assert client.get("/api/v1/profile", headers=auth["headers"]).status_code == 404


def test_profile_boundary_rejected(client, auth):
    bad = {**PROFILE, "weight_kg": 999}
    r = client.put("/api/v1/profile", json=bad, headers=auth["headers"])
    assert r.status_code == 422


def test_cloud_sync_blocked_when_server_off(client, auth):
    r = client.put("/api/v1/profile",
                   json={**PROFILE, "cloud_sync_enabled": True}, headers=auth["headers"])
    assert r.status_code == 400
    assert "本地" in r.json()["detail"]


def test_weight_stored_encrypted(client, auth):
    client.put("/api/v1/profile", json=PROFILE, headers=auth["headers"])
    # 直接查库：必须是密文，不能是明文 "80.0"
    from app.db.session import SessionLocal
    from app.models.entities import UserProfile
    with SessionLocal() as db:
        p = db.query(UserProfile).filter(
            UserProfile.user_id == auth["user"]["id"]).one()
        raw = p.weight_kg_enc
    assert raw and raw != "80.0" and "80.0" not in raw   # 密文不含明文


# ---------------- 安全测试 ----------------
def test_cannot_read_other_users_orders(client, auth):
    other = _mkuser(client, "intruder")
    r1 = client.post("/api/v1/orders", json={"codes": ["M1001"]}, headers=auth["headers"])
    oid = r1.json()["id"]
    # 攻击者尝试删除他人记录
    r = client.delete(f"/api/v1/orders/{oid}", headers=other["headers"])
    assert r.status_code == 404                # 查不到=不存在，不泄露存在性

    # 攻击者看不到他人历史
    r = client.get("/api/v1/orders", headers=other["headers"])
    assert r.json()["count"] == 0


def test_xss_payload_is_not_executed(client, auth):
    h = auth["headers"]
    xss = "<script>alert(1)</script>"
    client.post("/api/v1/coupons/bind",
                json={"code": xss, "title": xss, "threshold": 0, "discount": 1}, headers=h)
    r = client.get("/api/v1/coupons", headers=h)
    # 响应是 JSON 字符串，不含可执行上下文；前端渲染时需转义
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)


def test_sql_injection_attempt_is_safe(client, auth):
    payload = "'; DROP TABLE users; --"
    r = client.post("/api/v1/auth/register",
                    json={"username": payload[:30], "password": "pwd123456"})
    assert r.status_code in (201, 409, 422)
    # 表仍存在
    assert client.get("/health").json()["database_ok"] is True


def test_login_lockout_after_repeated_failures(client, auth):
    for _ in range(5):
        client.post("/api/v1/auth/login",
                    json={"username": "tester", "password": "badpwd123"})
    r = client.post("/api/v1/auth/login",
                    json={"username": "tester", "password": "test123456"})
    assert r.status_code == 423             # 锁定

# ---------------- 回归：脱敏断言本身的有效性 ----------------
# 反向验证：若有人把脱敏检查改成「永远通过」，测试应立刻失败。
def test_privacy_key_visitor_detects_nested_leak():
    def _keys(obj) -> set[str]:
        out: set[str] = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                out.add(str(k))
                out |= _keys(v)
        elif isinstance(obj, list):
            for v in obj:
                out |= _keys(v)
        return out

    forbidden = {"weight", "weight_kg", "target_weight", "height", "height_cm",
                 "tdee", "bmr", "daily_target", "protein_target", "gender", "age"}

    assert not (forbidden & _keys({"items": [{"name": "板烧鸡腿堡", "kcal": 474}]}))
    assert forbidden & _keys({"weight_kg": 80})                      # 顶层泄露
    assert forbidden & _keys({"meta": {"stats": {"tdee": 2457}}})   # 嵌套泄露
    # 英文文案里的子串不得误命中（age 命中 message/package 是旧写法的坑）
    assert not (forbidden & _keys({"message": "package average age"}))


def test_calendar_uses_actual_today_not_hardcoded_month(client, auth):
    """回归：日历断言不可写死月份与格子索引，否则跨天必失败。

    本用例在不同日期运行都应通过——正因如此才有意义。
    """
    h = auth["headers"]
    client.put("/api/v1/profile", json=PROFILE, headers=h)
    client.post("/api/v1/orders", json={"codes": ["M1002"]}, headers=h)

    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"
    client.post("/api/v1/checkin", json={"status": "达标", "total_kcal": 474,
                                          "protein_g": 26.5, "meals": []}, headers=h)
    cal = client.get(f"/api/v1/checkin/calendar?month={month}", headers=h).json()

    # 今天必须有打卡记录，且正好落在今天
    assert cal["summary"]["checked_days"] == 1
    today_cell = next(c for c in cal["cells"] if c["day"] == today.day)
    assert today_cell["status"] == "达标"

    # 顺带确认：不同月份的查询不会把今天的记录算进去
    other_month = f"{today.year + 1}-01"
    assert client.get(f"/api/v1/checkin/calendar?month={other_month}",
                      headers=h).json()["summary"]["checked_days"] == 0
