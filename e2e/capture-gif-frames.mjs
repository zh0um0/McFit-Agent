/**
 * 演示 GIF 录帧：在 demo 构建站点走完整用户旅程，逐动作截帧。
 * 帧由 scripts/make_gif.py 合成为 GIF。
 */
import { chromium } from 'file:///C:/Users/zhoumh/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';
import fs from 'node:fs';

const B = 'http://127.0.0.1:8899/McFit-Agent/';
const OUT = '../docs/gif-frames';

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 960, height: 640 }, deviceScaleFactor: 1 });

let n = 0;
const shot = async (hold = false) => {
  n++;
  await page.screenshot({ path: `${OUT}/${String(n).padStart(3, '0')}${hold ? 'H' : ''}.png` });
};
const wait = (ms) => page.waitForTimeout(ms);

// 1 登录页
await page.goto(`${B}/#/login`, { waitUntil: 'networkidle' });
await wait(800);
await shot(true);
await page.locator('input').first().fill('demo_gif');
await page.locator('input[type=password]').fill('pwd123456');
await wait(400);
await shot();

// 2 注册 → 建档页
await page.getByRole('button', { name: /注册并开始|登录/ }).last().click();
await wait(1800);
await shot(true);
const nums = page.locator('input[type=number]');
await nums.nth(0).fill('30');
await wait(350);
await shot();
await nums.nth(1).fill('175');
await wait(350);
await shot();
await nums.nth(2).fill('78');
await wait(350);
await shot();

// 3 保存 → 指标卡
await page.getByRole('button', { name: /保存并计算目标/ }).click();
await wait(2000);
await shot(true);
await wait(400);
await shot(true);

// 4 点餐页勾选
await page.goto(`${B}/#/order`, { waitUntil: 'networkidle' });
await wait(1500);
await shot(true);
await page.locator('.meal-card').nth(0).click();
await wait(500);
await shot();
await page.locator('.meal-card').nth(1).click();
await wait(500);
await shot();
await page.locator('.meal-card').nth(5).click();
await wait(600);
await shot(true);

// 5 凑单试算
await page.getByRole('button', { name: /试算凑单最优/ }).click();
await wait(1600);
await shot(true);
await wait(400);
await shot(true);

// 6 保存 → 打卡页
await page.getByRole('button', { name: /保存这一餐/ }).click();
await wait(2000);
await shot(true);

// 7 完成打卡 → 贴纸
await page.getByRole('button', { name: /完成今日打卡/ }).click();
await wait(1800);
await shot(true);

// 8 滚动看贴纸 + 日历
await page.mouse.wheel(0, 420);
await wait(700);
await shot(true);
await page.mouse.wheel(0, 480);
await wait(700);
await shot(true);
await wait(400);
await shot(true);

console.log(`DONE: ${n} frames`);
await browser.close();
