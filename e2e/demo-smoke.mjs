/**
 * Demo 构建冒烟验证：base=/-McFit-Agent/ 静态托管下，无后端走通核心链路。
 * 覆盖：注册（任意输入）→ 建档 → 指标 → 点餐勾选 → 凑单 → 保存 → 打卡 → 贴纸 → 日历 → 海报
 */
import { chromium } from 'file:///C:/Users/zhoumh/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';

const B = 'http://127.0.0.1:8899/McFit-Agent/';
const results = [];
const check = (n, p, d = '') => { results.push(p); console.log(`${p ? 'PASS' : 'FAIL'} | ${n}${d ? '  → ' + d : ''}`); };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

console.log('--- demo 冒烟 ---');
await page.goto(`${B}/#/login`, { waitUntil: 'networkidle' });
await page.locator('input').first().fill('demo_smoke');
await page.locator('input[type=password]').fill('pwd123456');
await page.getByRole('button', { name: /注册并开始|登录/ }).last().click();
await page.waitForTimeout(2500);
check('1 注册/登录进入流程', !page.url().includes('/login') || page.url().includes('/profile'), page.url());

// 建档（无档案守卫应已在 profile）
const nums = page.locator('input[type=number]');
if ((await nums.count()) >= 3) {
  await nums.nth(0).fill('30');
  await nums.nth(1).fill('175');
  await nums.nth(2).fill('78');
  await page.getByRole('button', { name: /保存并计算目标/ }).click();
  await page.waitForTimeout(2000);
}
check('2 档案保存成功', !(await page.locator('.alert-error').count()));

// 点餐
await page.goto(`${B}/#/order`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
const cards = await page.locator('.meal-card').count();
check('3 菜单渲染（demo 种子）', cards >= 10, `${cards} 个`);
if (cards >= 2) {
  await page.locator('.meal-card').nth(0).click();
  await page.locator('.meal-card').nth(1).click();
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: /试算凑单最优/ }).click();
  await page.waitForTimeout(1200);
  check('4 凑单方案出现', (await page.locator('text=省钱凑单方案').count()) > 0);
  const rec = (await page.locator('.alert.alert-ok').first().textContent().catch(() => '')) || '';
  check('5 推荐文案正常', rec.trim().length > 0 && !/undefined|null/.test(rec), rec.trim().slice(0, 36));
  await page.getByRole('button', { name: /采用推荐组合/ }).click().catch(() => {});
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: /保存这一餐/ }).click();
  await page.waitForTimeout(1500);
}

// 打卡
await page.goto(`${B}/#/checkin`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
check('6 打卡页汇总>0', parseFloat(await page.locator('.stat .value.mono').first().textContent()) > 0);
await page.getByRole('button', { name: /完成今日打卡/ }).click();
await page.waitForTimeout(1500);
check('7 贴纸 SVG 渲染', (await page.locator('svg').count()) > 0);
check('8 日历有格子', (await page.locator('.calendar *').count()) > 20);

// 刷新持久化
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
check('9 刷新后汇总仍在（localStorage）', parseFloat(await page.locator('.stat .value.mono').first().textContent()) > 0);

const realErrors = errors.filter((e) => !e.includes('favicon') && !/404/.test(e));
check('10 控制台无意外错误', realErrors.length === 0, realErrors.slice(0, 2).join(' | ') || '无');

console.log(`\n${results.filter(Boolean).length}/${results.length} 通过`);
await page.screenshot({ path: '../docs/screenshot-demo-order.png', fullPage: false });
await browser.close();
process.exit(results.every(Boolean) ? 0 : 1);
