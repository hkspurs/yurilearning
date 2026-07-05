const { test, expect } = require('@playwright/test');

const HOMEWORK_URL = process.env.HOMEWORK_URL || 'https://hkspurs.github.io/yurilearning/phonics-game/homework.html?v=gggeeeggu';

test.describe('YURI Brighter Phonics Train homework page', () => {
  test('Level 2 loads, all stations render, review and quiz flow work', async ({ page }) => {
    const failedRequests = [];
    const consoleErrors = [];

    page.on('requestfailed', request => {
      const url = request.url();
      const failure = request.failure()?.errorText || 'unknown';
      if (!url.startsWith('data:')) failedRequests.push(`${url} => ${failure}`);
    });

    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });

    await page.goto(HOMEWORK_URL, { waitUntil: 'networkidle' });

    await expect(page.locator('.brand')).toContainText('YURI Brighter Phonics Train');
    await expect(page.locator('.level-card')).toHaveCount(2);
    await expect(page.locator('.level-card').nth(1)).toContainText('Brighter Phonics Train');

    await page.locator('.level-card').nth(1).click();
    await expect(page.locator('#selectedLevelTitle')).toContainText('Brighter Phonics Train');

    const reviewRows = await page.locator('#reviewRow option').evaluateAll(options => options.map(o => o.textContent.trim()));
    expect(reviewRows).toEqual([
      'A Station - AB to AZ',
      'E Station - EB to EZ',
      'I Station - IB to IZ',
      'O Station - OB to OZ',
      'U Station - UB to UZ',
    ]);

    for (const row of reviewRows) {
      await page.selectOption('#reviewRow', { label: row });
      await expect(page.locator('#reviewGrid .answer-btn')).toHaveCount(21);
      await page.locator('#reviewGrid .answer-btn').first().click();
      await expect(page.locator('#audioStatus')).toContainText(/播放車卡|音檔未能播放/);
    }

    const configCheck = await page.evaluate(() => {
      const cfg = window.PHONICS_LEVEL2_CLIPS || {};
      const rows = Object.entries(cfg).map(([name, row]) => ({
        name,
        count: Object.keys(row.clips || {}).length,
        audio: row.audio,
        first: Object.keys(row.clips || {})[0],
        last: Object.keys(row.clips || {}).slice(-1)[0],
      }));
      const issues = [];
      for (const [rowName, row] of Object.entries(cfg)) {
        let prevEnd = -Infinity;
        for (const [label, range] of Object.entries(row.clips || {})) {
          if (!Array.isArray(range) || range.length !== 2) issues.push(`${label} missing range`);
          else if (!(Number.isFinite(range[0]) && Number.isFinite(range[1]) && range[0] < range[1])) issues.push(`${label} invalid range`);
          else if (range[0] < prevEnd) issues.push(`${label} overlaps previous in ${rowName}`);
          if (Array.isArray(range)) prevEnd = range[1];
        }
      }
      return { rows, issues };
    });

    expect(configCheck.rows).toHaveLength(5);
    for (const row of configCheck.rows) expect(row.count).toBe(21);
    expect(configCheck.issues).toEqual([]);

    await page.selectOption('#quizRowFilter', 'A');
    await page.locator('#quizMode').click();
    await expect(page.locator('#progressText')).toContainText('第 1 / 5 站');
    await expect(page.locator('#choices .answer-btn')).toHaveCount(4);
    await page.locator('#playQuestion').click();
    await expect(page.locator('#audioStatus')).toContainText(/播放車卡|音檔未能播放/);

    for (let i = 0; i < 5; i++) {
      const choiceCount = await page.locator('#choices .answer-btn').count();
      if (choiceCount > 0) await page.locator('#choices .answer-btn').first().click();
      await page.locator('#nextQuestion').click();
    }

    await expect(page.locator('#resultScreen')).toHaveClass(/active/);
    await expect(page.locator('#finalScore')).toContainText('/ 5');

    expect(consoleErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
