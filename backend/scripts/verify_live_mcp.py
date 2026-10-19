"""官方 MCP 真实接入验证（Token 由环境变量注入，不落盘）。

用法：
  set MCP_TOKEN=<token>
  python scripts/verify_live_mcp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.services.mcp_client import McpClient, sync_meals_to_cache  # noqa: E402

# 强制走内存库，绝不污染开发数据库
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'


def main() -> int:
    token = os.environ.get('MCP_TOKEN', '').strip()
    if not token:
        print('[x] 未注入 MCP_TOKEN，跳过真实联调')
        return 1

    print('=' * 60)
    print('官方 MCP 真实接入验证')
    print('=' * 60)

    # 1) 握手
    try:
        client = McpClient(token)
        info = client.initialize()
        print(f"[1] 握手成功: {info.get('serverInfo')}")
    except Exception as exc:
        print(f'[x] 握手失败: {exc}')
        return 1

    # 2) 工具清单
    try:
        tools = client.list_tools()
        names = {t['name'] for t in tools}
        print(f'[2] 官方工具数: {len(names)}')
        from app.services.mcp_client import ALLOWED_TOOLS
        print(f'    本项目白名单全部可用: '
              f'{"是" if ALLOWED_TOOLS <= names else "否，缺 " + str(ALLOWED_TOOLS - names)}')
    except Exception as exc:
        print(f'[!] 工具清单获取失败: {exc}')

    # 3) 同步（内存库）
    Base.metadata.create_all(bind=engine)
    init_db()
    with SessionLocal() as db:
        try:
            r = sync_meals_to_cache(db, picked_only=True)
            print(f"[3] 同步完成:落库 {r['synced']} 条，"
                  f"官方全量 {r['official_total']} 条，匹配 {r['matched']}/{25}")
            if r['missing']:
                print(f"    [缺失] {r['missing']}")
            else:
                print('    精选集全部命中，无缺失')

            # 4) 抽样展示落库结果
            from sqlalchemy import select
            from app.models.entities import MealCache
            rows = db.scalars(select(MealCache)
                              .where(MealCache.source == 'mcp')
                              .order_by(MealCache.category, MealCache.kcal)).all()
            print(f'\n[4] 落库明细（{len(rows)} 条）:')
            for m in rows:
                flag = '高蛋白' if m.is_high_protein else ''
                print(f"    [{m.category}] {m.name:<12} "
                      f"{m.kcal:>4.0f}kcal 蛋白{m.protein_g:>5.1f}g "
                      f"脂肪{m.fat_g:>4.1f}g 钠{m.sodium_mg:>6.0f}mg "
                      f"¥{m.price:<5} {flag}")
            return 0 if r['synced'] == 25 and not r['missing'] else 1
        except Exception as exc:
            print(f'[x] 同步失败: {exc}')
            return 1


if __name__ == '__main__':
    sys.exit(main())