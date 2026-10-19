/**
 * McFit-Agent 端到端验收脚本（Playwright 直连库，不走 daemon）
 * 覆盖：新用户引导、档案页指标说明、路由守卫、说明文字溢出、控制台报错
 *
 * 运行前置：
 *   npm install -D playwright && npx playwright install chromium
 *   node e2e/journey.spec.mjs
 *
 * 注：需前后端已启动（后端 8000 / 前端 5173）
 */
import { chromium } from 'playwright';

const B = process.env.E2E_BASE_URL || 'http://localhost:5173';
const USER = 'e2e_' + Date.now().toString().slice(-8);   // 时间戳保证全新账号
const PWD = 'pwd123456';

const results = [];
const check = (n, p, d = '') => {
  results.push({ n, p });
  console.log(`${p ? 'PASS' : 'FAIL'} | ${n}${d ? '  → ' + d : ''}`);
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
const badResponses = [];
page.on('response', (r) => { if (r.status() === 404) badResponses.push(r.url()); });

async function fillLoginForm() {
  await page.getByPlaceholder('3-30位字母/数字/中文').fill(USER);
  await page.locator('input[type=password]').fill(PWD);
}

async function register() {
  await page.goto(`${B}/#/login`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '注册' }).first().click();
  await page.waitForTimeout(400);
  await fillLoginForm();
  await page.getByRole('button', { name: /注册并开始/ }).click();
  await page.waitForTimeout(2800);
}

async function login() {
  // 已登录状态下访问 /#/login 会被守卫打回首页，故必须先清 token。
  // 清完还要等 Pinia 的 auth.hydrated 标志被重置（守卫 bootstrap 依赖它），
  // 否则 goto 会被当作「已登录」而再次打回首页。
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${B}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector('input[type=password]', { timeout: 15000 });
  await fillLoginForm();
  await page.getByRole('button', { name: '登录' }).last().click();
  await page.waitForTimeout(2500);
}

console.log(`测试账号：${USER}\n`);
console.log('--- 场景0：注册全新账号 ---');
await register();
check('注册后立即被引导到档案页', page.url().includes('/profile'), page.url());

console.log('--- 场景1：全新用户首次登录（清 token 重登验证守卫）---');
await login();
check('被拦到档案页', page.url().includes('/profile'), page.url());
check('携带 from 参数', page.url().includes('from='));
check('显示新手引导横幅', (await page.locator('text=先完善身材档案').count()) > 0);
check('"公式分支"字样已删除', (await page.locator('text=Mifflin-St Jeor 公式分支').count()) === 0);

console.log('--- 场景2：从点餐页被拦应记录 from=/order ---');
await page.goto(`${B}/#/order`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
check('点餐页也被拦截', page.url().includes('/profile'), page.url());
check('from 记录为 /order', page.url().includes('from=/order'));

console.log('--- 场景3：填写并保存后回跳 ---');
await page.locator('input[type=number]').nth(2).fill('78');       // 体重
await page.getByRole('button', { name: /保存并计算目标/ }).click();
await page.waitForTimeout(2500);
check('保存后跳回原点餐页', page.url().includes('/order'), page.url());

console.log('--- 场景4：档案页指标卡说明文字 ---');
await page.goto(`${B}/#/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
const notes = await page.locator('.stat-note').allTextContents();
check('4张卡都有说明', notes.length === 4, `${notes.length} 条`);
check('BMR 白话说明', (notes[0] || '').includes('最低消耗'), notes[0] || '');
check('TDEE 白话说明', (notes[1] || '').includes('总消耗'), notes[1] || '');
check('蛋白白白话说明', (notes[3] || '').includes('保肌'), notes[3] || '');
const ovf = await page.evaluate(() => {
  const bad = [];
  document.querySelectorAll('.stat').forEach((c) => {
    const n = c.querySelector('.stat-note');
    if (n && n.scrollWidth > n.clientWidth + 1) bad.push(n.textContent.slice(0, 10));
  });
  return bad;
});
check('说明文字无横向溢出', ovf.length === 0, ovf.join(',') || '无溢出');
await page.screenshot({ path: 'docs/screenshot-profile.png', fullPage: true });

console.log('--- 场景5：二次登录（有档案）---');
await login();
check('有档案直达首页', !page.url().includes('/profile'), page.url());
check('首页显示今日概览', (await page.locator('text=今天吃得怎么样').count()) > 0);

console.log('--- 场景6：控制台 ---');
// 新用户首次访问时 GET /api/v1/profile 必然返回 404「尚未建立身材档案」——
// 这是预期的业务响应（前端据此判定 hasProfile=false），不是缺陷，故排除。
const fe = errors.filter((e) => e.includes('favicon'));
// 过滤掉「无档案用户访问 /api/v1/profile 时的 404」——这是预期行为
const re = errors.filter((e) => !e.includes('favicon') && !e.includes('404'));
check('无 favicon 404', fe.length === 0, `${fe.length} 个`);
check('无其他控制台错误', re.length === 0, re.slice(0, 2).join(' | ') || '无');

// 附带确认：确实只存在「无档案」这一个 404，没有别的资源缺失
const r404 = badResponses.filter((u) => !u.includes('/api/v1/profile'));
check('无意外404资源', r404.length === 0, r404.slice(0, 3).join(' | ') || '无');

const passed = results.filter((r) => r.p).length;
console.log(`\n${passed}/${results.length} 通过`);
await browser.close();
process.exit(passed === results.length ? 0 : 1);