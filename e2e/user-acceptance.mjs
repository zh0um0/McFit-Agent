/**
 * 用户视角验收脚本 v2（独立于开发者的 journey.spec.mjs）
 * 覆盖核心业务链路：建档 → 档案页指标卡 → 点餐勾选+凑单试算+采用推荐+保存 → 打卡 → 贴纸 → 日历 → 海报脱敏 → 我的页 → 重登持久化
 *
 * 运行前置：
 *   npm install -D playwright && npx playwright install chromium
 *   node e2e/user-acceptance.mjs（需前后端已启动，前端 5173）
 */
import { chromium } from 'playwright';

const B = process.env.E2E_BASE_URL || 'http://localhost:5173';
const USER = 'ua_' + Date.now().toString().slice(-8);
const PWD = 'pwd123456';
const W_FINGERPRINT = '78';   // 体重指纹，用于海报脱敏校验

const results = [];
const check = (n, p, d = '') => {
  results.push({ n, p });
  console.log(`${p ? 'PASS' : 'FAIL'} | ${n}${d ? '  → ' + d : ''}`);
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

async function loginForm() {
  await page.locator('input').first().fill(USER);
  await page.locator('input[type=password]').fill(PWD);
}

console.log(`验收账号：${USER}\n`);
console.log('--- A. 注册并建档 ---');
await page.goto(`${B}/#/login`, { waitUntil: 'networkidle' });
await page.getByRole('button', { name: '注册' }).first().click();
await page.waitForTimeout(400);
await loginForm();
await page.getByRole('button', { name: /注册并开始/ }).click();
await page.waitForTimeout(2800);
check('A1 注册后进入档案页', page.url().includes('/profile'), page.url());

// 数字输入顺序：年龄 → 身高 → 体重（性别/活动强度/目标为下拉，默认值合法）
const nums = page.locator('input[type=number]');
check('A2 档案表单数字输入项 = 3（年龄/身高/体重）', (await nums.count()) === 3, `${await nums.count()} 个`);
check('A3 年龄默认值合法（1-120）', [30, 25, 28].includes(Number(await nums.nth(0).inputValue())), await nums.nth(0).inputValue());
await nums.nth(0).fill('30');
await nums.nth(1).fill('175');
await nums.nth(2).fill(W_FINGERPRINT);
await page.getByRole('button', { name: /保存并计算目标/ }).click();
await page.waitForTimeout(2500);
const savedOk = !(await page.locator('.alert-error').count());
check('A4 档案保存成功（无错误提示且离开引导态）', savedOk && !page.url().includes('alert'), page.url());

console.log('--- B. 档案页指标卡 ---');
await page.goto(`${B}/#/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
const notes = await page.locator('.stat-note').allTextContents();
check('B1 4 张指标卡且都带白话说明', notes.length === 4 && notes.every(n => n.trim().length > 0), `${notes.length} 条`);
const vals = await page.locator('.stat .value').allTextContents();
check('B2 指标数值非空且非 0', vals.length >= 4 && vals.slice(0, 4).every(v => { const n = parseFloat(v.replace(/[^\d.]/g, '')); return !isNaN(n) && n > 0; }), vals.slice(0, 4).join(' | '));
const ovf = await page.evaluate(() => {
  const bad = [];
  document.querySelectorAll('.stat').forEach((c) => {
    const n = c.querySelector('.stat-note');
    if (n && n.scrollWidth > n.clientWidth + 1) bad.push(n.textContent.slice(0, 10));
  });
  return bad;
});
check('B3 说明文字无横向溢出', ovf.length === 0, ovf.join(',') || '无溢出');
await page.screenshot({ path: 'docs/screenshot-acceptance-profile.png', fullPage: true });

console.log('--- C. 点餐页：勾选 + 累加 + 凑单 + 保存 ---');
await page.goto(`${B}/#/order`, { waitUntil: 'networkidle' });
await page.waitForTimeout(3000);
check('C0 点餐页未被守卫拦截（档案已存在）', !page.url().includes('/profile'), page.url());
const mealCards = page.locator('.meal-card');
const mealCount = await mealCards.count();
check('C1 菜单卡片已渲染（≥10 个单品）', mealCount >= 10, `${mealCount} 个`);
if (mealCount >= 2) {
  await mealCards.nth(0).click();
  await mealCards.nth(1).click();
  await page.waitForTimeout(600);
  const kcalText = await page.locator('.stat .value.mono').first().textContent();
  check('C2 勾选 2 件后热量实时累加（>0）', parseFloat(kcalText) > 0, `合计 ${kcalText} kcal`);
  const priceText = await page.locator('.stat .value.mono').nth(2).textContent();
  check('C3 实付价实时显示（>0）', parseFloat(priceText.replace('¥', '')) > 0, priceText);

  await page.getByRole('button', { name: /试算凑单最优/ }).click();
  await page.waitForTimeout(2500);
  const hasCalc = await page.locator('text=省钱凑单方案').count();
  check('C4 凑单方案卡出现', hasCalc > 0);
  if (hasCalc) {
    const baseline = await page.locator('text=当前方案原价').count();
    const recommend = await page.locator('text=推荐方案实付').count();
    check('C5 baseline 与推荐方案并列展示（语义不混淆）', baseline > 0 && recommend > 0);
    const recText = (await page.locator('.alert.alert-ok').first().textContent()) || '';
    check('C6 推荐文案无空占位', recText.trim().length > 0 && !/约\s{2,}|undefined|null/.test(recText), recText.trim().slice(0, 40));
    await page.getByRole('button', { name: /采用推荐组合/ }).click();
    await page.waitForTimeout(800);
  }
  await page.getByRole('button', { name: /保存这一餐/ }).click();
  await page.waitForTimeout(900);   // 成功提示展示 1.6s 后自动跳转打卡页，须在跳转前断言
  const okMsg = await page.locator('.alert.alert-ok').count();
  const jumped = page.url().includes('/checkin');
  check('C7 保存这一餐成功（提示或自动跳转打卡页）', okMsg > 0 || jumped, okMsg ? '有成功提示' : page.url());
}

console.log('--- D. 打卡页：汇总 + 打卡 + 贴纸 ---');
await page.goto(`${B}/#/checkin`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
const sumKcal = await page.locator('.stat .value.mono').first().textContent();
check('D1 今日汇总热量 >0（与点餐联动）', parseFloat(sumKcal) > 0, `${sumKcal} kcal`);
const exHead = await page.locator('.card b').first().textContent().catch(() => '');
check('D2 运动代偿文案存在（正向口径）', (exHead || '').trim().length > 0, (exHead || '').trim().slice(0, 30));
const badWords = await page.locator('text=/放纵|反省|惩罚/').count();
check('D3 无负罪感字眼（放纵/反省/惩罚）', badWords === 0, `${badWords} 处`);

await page.getByRole('button', { name: /完成今日打卡/ }).click();
await page.waitForTimeout(2500);
const stickerSvg = await page.locator('svg').count();
check('D4 打卡后贴纸 SVG 渲染', stickerSvg > 0, `${stickerSvg} 个 svg`);
const stamp = await page.locator('text=印章').count();
check('D5 印章/状态/文案信息展示', stamp > 0);

console.log('--- E. 打卡日历 ---');
const calCells = await page.locator('.calendar *').count();
check('E1 日历网格已渲染', calCells > 20, `${calCells} 个元素`);
const todayMark = await page.locator('.calendar .today, .calendar [class*=on], .calendar [class*=ok]').count();
check('E2 今日格有状态标记', todayMark > 0, `${todayMark} 个`);
await page.screenshot({ path: 'docs/screenshot-acceptance-checkin.png', fullPage: true });

console.log('--- F. 海报脱敏（指纹体重 78 不得出现）---');
const posterData = await page.evaluate(async () => {
  const t = localStorage.getItem('mcfit_access');
  const r = await fetch('/api/v1/sticker/poster', { headers: { Authorization: `Bearer ${t}` } });
  return { status: r.status, body: await r.text() };
});
check('F1 海报接口 200', posterData.status === 200, `HTTP ${posterData.status}`);
const bodyStr = posterData.body;
const hasWeight = /"(weight|weight_kg|target_weight|tdee|bmr)"\s*:/i.test(bodyStr);
check('F2 响应 JSON 无体重/TDEE/BMR 字段键', !hasWeight);
const hasFingerprint = new RegExp(`${W_FINGERPRINT}\\s*(kg|公斤|千克)`).test(bodyStr);
check('F3 海报文本不含「78 kg」指纹', !hasFingerprint);

console.log('--- G. 我的页 ---');
await page.goto(`${B}/#/me`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
check('G1 显示用户名', (await page.locator(`text=${USER}`).count()) > 0);
check('G2 健康状态卡可见（正常/云同步未开启）', (await page.locator('text=正常').count()) > 0 && (await page.locator('text=未开启').count()) > 0);

console.log('--- H. 退出重登：数据持久化 ---');
const logoutBtn = page.getByRole('button', { name: /退出|登出/ });
if (await logoutBtn.count()) { await logoutBtn.first().click(); await page.waitForTimeout(1500); }
else { await page.evaluate(() => localStorage.clear()); }
await page.goto(`${B}/#/login`, { waitUntil: 'domcontentloaded' });
await page.reload({ waitUntil: 'networkidle' });
await page.waitForSelector('input[type=password]', { timeout: 15000 });
await loginForm();
await page.getByRole('button', { name: '登录' }).last().click();
await page.waitForTimeout(2500);
check('H1 重登后直达首页（档案已存在）', !page.url().includes('/profile'), page.url());
check('H2 首页今日概览仍显示', (await page.locator('text=今天吃得怎么样').count()) > 0);
await page.goto(`${B}/#/checkin`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
check('H3 打卡记录重登后仍在', parseFloat(await page.locator('.stat .value.mono').first().textContent()) > 0);

console.log('--- I. 控制台健康 ---');
const realErrors = errors.filter((e) => !e.includes('favicon') && !/40[149]/.test(e));
check('I1 无意外控制台错误', realErrors.length === 0, realErrors.slice(0, 2).join(' | ') || '无');

const passed = results.filter((r) => r.p).length;
console.log(`\n${passed}/${results.length} 通过`);
await browser.close();
process.exit(passed === results.length ? 0 : 1);
