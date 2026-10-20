/**
 * README 素材截图：在 demo 构建站点上走核心流程，拍 5 张视口图。
 */
import { chromium } from 'file:///C:/Users/zhoumh/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';

const B = 'http://127.0.0.1:8899/McFit-Agent/';
const OUT = '../docs/screenshots';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1360, height: 850 }, deviceScaleFactor: 2 });

await page.goto(`${B}/#/login`, { waitUntil: 'networkidle' });
await page.locator('input').first().fill('demo_shots');
await page.locator('input[type=password]').fill('pwd123456');
await page.getByRole('button', { name: /注册并开始|登录/ }).last().click();
await page.waitForTimeout(2200);

// 0 先建档（守卫要求）
const nums = page.locator('input[type=number]');
if ((await nums.count()) >= 3) {
  await nums.nth(0).fill('30');
  await nums.nth(1).fill('175');
  await nums.nth(2).fill('78');
  await page.getByRole('button', { name: /保存并计算目标/ }).click();
  await page.waitForTimeout(2000);
}

// 1 档案页（指标卡）
await page.goto(`${B}/#/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/01-profile-metrics.png` });

// 2 点餐页（勾选 2 件 + 实时累加）
await page.goto(`${B}/#/order`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1800);
await page.locator('.meal-card').nth(0).click();
await page.locator('.meal-card').nth(1).click();
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/02-order.png` });

// 3 凑单方案
await page.getByRole('button', { name: /试算凑单最优/ }).click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/03-coupon-calc.png` });

// 4 保存后打卡页
await page.getByRole('button', { name: /保存这一餐/ }).click();
await page.waitForTimeout(2200);
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/04-dashboard.png` });

// 5 打卡 + 贴纸 + 日历
await page.goto(`${B}/#/checkin`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1800);
await page.getByRole('button', { name: /完成今日打卡/ }).click();
await page.waitForTimeout(1800);
await page.screenshot({ path: `${OUT}/05-checkin-sticker.png`, fullPage: true });

console.log('DONE: 5 screenshots saved');
await browser.close();
