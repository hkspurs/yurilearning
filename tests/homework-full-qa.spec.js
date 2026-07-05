const { test, expect } = require('@playwright/test');

const HOMEWORK_URL = process.env.HOMEWORK_URL || 'https://hkspurs.github.io/yurilearning/phonics-game/homework.html?v=gggeeeggu';

const EXPECTED_ROWS = {
  A: ['AB', 'AC', 'AD', 'AF', 'AG', 'AH', 'AJ', 'AK', 'AL', 'AM', 'AN', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AV', 'AW', 'AX', 'AY', 'AZ'],
  E: ['EB', 'EC', 'ED', 'EF', 'EG', 'EH', 'EJ', 'EK', 'EL', 'EM', 'EN', 'EP', 'EQ', 'ER', 'ES', 'ET', 'EV', 'EW', 'EX', 'EY', 'EZ'],
  I: ['IB', 'IC', 'ID', 'IF', 'IG', 'IH', 'IJ', 'IK', 'IL', 'IM', 'IN', 'IP', 'IQ', 'IR', 'IS', 'IT', 'IV', 'IW', 'IX', 'IY', 'IZ'],
  O: ['OB', 'OC', 'OD', 'OF', 'OG', 'OH', 'OJ', 'OK', 'OL', 'OM', 'ON', 'OP', 'OQ', 'OR', 'OS', 'OT', 'OV', 'OW', 'OX', 'OY', 'OZ'],
  U: ['UB', 'UC', 'UD', 'UF', 'UG', 'UH', 'UJ', 'UK', 'UL', 'UM', 'UN', 'UP', 'UQ', 'UR', 'US', 'UT', 'UV', 'UW', 'UX', 'UY', 'UZ'],
};

function isIgnorableRequestFailure(url, failure) {
  const isMedia = /\.(mp3|mp4|wav|m4a)(\?|$)/i.test(url);
  return isMedia && /ERR_ABORTED/i.test(failure);
}

function labelRegex(labels) {
  return new RegExp(`\\b(${labels.join('|')})\\b`);
}

async function collectRuntime(page) {
  const failedRequests = [];
  const ignoredMediaCancels = [];
  const consoleErrors = [];
  const importantResponses = [];

  page.on('requestfailed', request => {
    const url = request.url();
    const failure = request.failure()?.errorText || 'unknown';
    if (url.startsWith('data:')) return;
    if (isIgnorableRequestFailure(url, failure)) {
      ignoredMediaCancels.push(`${url} => ${failure}`);
      return;
    }
    failedRequests.push(`${url} => ${failure}`);
  });

  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  page.on('response', response => {
    const url = response.url();
    if (/\.(html|css|js|mp3)(\?|$)/i.test(url)) {
      importantResponses.push({ url, status: response.status() });
    }
  });

  return { failedRequests, ignoredMediaCancels, consoleErrors, importantResponses };
}

async function enterLevel2(page) {
  await page.goto(HOMEWORK_URL, { waitUntil: 'networkidle' });
  await expect(page.locator('.brand')).toContainText('YURI Brighter Phonics Train');
  await expect(page.locator('.level-card')).toHaveCount(2);
  await expect(page.locator('.level-card').nth(1)).toContainText('Brighter Phonics Train');
  await page.locator('.level-card').nth(1).click();
  await expect(page.locator('#selectedLevelTitle')).toContainText('Brighter Phonics Train');
}

test.describe('YURI homework full QA - distrust everything', () => {
  test('static assets, Level 2 config, rows, timings, and audio trigger checks', async ({ page }) => {
    const runtime = await collectRuntime(page);
    await enterLevel2(page);

    await expect(page.locator('#stationRoute .station-node')).toHaveCount(6);
    await expect(page.locator('#stationRoute')).toContainText('A');
    await expect(page.locator('#stationRoute')).toContainText('Finish');

    const configCheck = await page.evaluate(expectedRows => {
      const cfg = window.PHONICS_LEVEL2_CLIPS || {};
      const issues = [];
      const rowResults = [];

      for (const [key, expectedLabels] of Object.entries(expectedRows)) {
        const rowEntry = Object.entries(cfg).find(([rowName]) => rowName.startsWith(`${key} row`));
        if (!rowEntry) {
          issues.push(`${key} row missing`);
          continue;
        }

        const [rowName, row] = rowEntry;
        const labels = Object.keys(row.clips || {});
        const audio = row.audio || '';
        rowResults.push({ key, rowName, audio, labels });

        if (!audio.includes(`brighter-${key.toLowerCase()}.mp3`)) issues.push(`${key} row wrong audio path: ${audio}`);
        if (labels.length !== 21) issues.push(`${key} row expected 21 clips, got ${labels.length}`);
        if (JSON.stringify(labels) !== JSON.stringify(expectedLabels)) issues.push(`${key} row label order mismatch: ${labels.join(' ')}`);

        let prevEnd = -Infinity;
        for (const label of labels) {
          const range = row.clips[label];
          if (!Array.isArray(range) || range.length !== 2) {
            issues.push(`${label} missing timing range`);
            continue;
          }
          const [start, end] = range.map(Number);
          const duration = end - start;
          if (!Number.isFinite(start) || !Number.isFinite(end)) issues.push(`${label} non-numeric timing`);
          if (!(start >= 0 && end > start)) issues.push(`${label} invalid timing ${start}-${end}`);
          if (duration < 0.25) issues.push(`${label} suspiciously short duration ${duration.toFixed(3)}s`);
          if (duration > 2.5) issues.push(`${label} suspiciously long duration ${duration.toFixed(3)}s`);
          if (start < prevEnd) issues.push(`${label} overlaps previous clip`);
          prevEnd = end;
        }
      }

      return { rowResults, issues };
    }, EXPECTED_ROWS);

    expect(configCheck.issues).toEqual([]);
    expect(configCheck.rowResults).toHaveLength(5);

    const reviewRows = await page.locator('#reviewRow option').evaluateAll(options => options.map(o => o.textContent.trim()));
    expect(reviewRows).toEqual([
      'A Station - AB to AZ',
      'E Station - EB to EZ',
      'I Station - IB to IZ',
      'O Station - OB to OZ',
      'U Station - UB to UZ',
    ]);

    for (const [rowKey, labels] of Object.entries(EXPECTED_ROWS)) {
      const rowLabel = `${rowKey} Station - ${labels[0]} to ${labels[labels.length - 1]}`;
      await page.selectOption('#reviewRow', { label: rowLabel });
      await expect(page.locator('#stationRoute .station-node.active')).toContainText(rowKey);
      await expect(page.locator('#reviewGrid .answer-btn')).toHaveCount(21);

      const renderedLabels = await page.locator('#reviewGrid .answer-btn').evaluateAll(buttons => buttons.map(b => b.firstChild.textContent.trim()));
      expect(renderedLabels).toEqual(labels);

      for (const label of [labels[0], labels[10], labels[20]]) {
        await page.locator('#reviewGrid .answer-btn').filter({ hasText: label }).click();
        await expect(page.locator('#audioStatus')).toContainText(new RegExp(`(播放.*${label}|音檔未能播放.*${label})`));
      }
    }

    const badResponses = runtime.importantResponses.filter(r => r.status >= 400 && !/favicon\.ico/i.test(r.url));
    if (runtime.ignoredMediaCancels.length) console.log(`Ignored normal media cancellations: ${runtime.ignoredMediaCancels.length}`);
    expect(badResponses).toEqual([]);
    expect(runtime.consoleErrors).toEqual([]);
    expect(runtime.failedRequests).toEqual([]);
  });

  test('quiz answer correctness, wrong-answer handling, scoring, progress, and result flow', async ({ page }) => {
    const runtime = await collectRuntime(page);
    await enterLevel2(page);

    const aLabels = EXPECTED_ROWS.A;
    await page.selectOption('#quizRowFilter', 'A');
    await page.locator('#quizMode').click();
    await expect(page.locator('#progressText')).toContainText('第 1 / 5 站');
    await expect(page.locator('#choices .answer-btn')).toHaveCount(4);
    await expect(page.locator('#trainJourney .journey-stop.current')).toHaveCount(1);

    // First question: deliberately answer wrong first, then correct.
    await page.locator('#playQuestion').click();
    await expect(page.locator('#audioStatus')).toContainText(/播放|音檔未能播放/);
    const firstAudioStatus = await page.locator('#audioStatus').textContent();
    const firstCorrect = firstAudioStatus.match(labelRegex(aLabels))?.[1];
    expect(firstCorrect, `Cannot extract correct label from audioStatus: ${firstAudioStatus}`).toBeTruthy();

    const firstChoiceLabels = await page.locator('#choices .answer-btn').evaluateAll(buttons => buttons.map(b => b.firstChild.textContent.trim()));
    expect(firstChoiceLabels).toContain(firstCorrect);
    const wrong = firstChoiceLabels.find(label => label !== firstCorrect);
    expect(wrong).toBeTruthy();

    await page.locator('#choices .answer-btn').filter({ hasText: wrong }).click();
    await expect(page.locator('#feedback')).toContainText(/差少少|再聽一次/);
    await expect(page.locator('#triesText')).toContainText('機會 2/3');
    await expect(page.locator('#scoreText')).toContainText('星星 0');

    await page.locator('#choices .answer-btn').filter({ hasText: firstCorrect }).click();
    await expect(page.locator('#feedback')).toContainText(/好嘢|火車行前一步/);
    await expect(page.locator('#scoreText')).toContainText('星星 1');
    await expect(page.locator('#questionLabel')).toContainText(firstCorrect);
    await expect(page.locator('#trainJourney .journey-stop.done')).toHaveCount(1);

    await page.locator('#nextQuestion').click();

    // Remaining 4 questions: use audioStatus as source of truth, click the exact matching answer.
    for (let expectedQuestion = 2; expectedQuestion <= 5; expectedQuestion++) {
      await expect(page.locator('#progressText')).toContainText(`第 ${expectedQuestion} / 5 站`);
      await page.locator('#playQuestion').click();
      await expect(page.locator('#audioStatus')).toContainText(/播放|音檔未能播放/);
      const status = await page.locator('#audioStatus').textContent();
      const correct = status.match(labelRegex(aLabels))?.[1];
      expect(correct, `Cannot extract correct label from audioStatus: ${status}`).toBeTruthy();
      const choices = await page.locator('#choices .answer-btn').evaluateAll(buttons => buttons.map(b => b.firstChild.textContent.trim()));
      expect(choices).toContain(correct);
      await page.locator('#choices .answer-btn').filter({ hasText: correct }).click();
      await expect(page.locator('#feedback')).toContainText(/好嘢|火車行前一步/);
      await expect(page.locator('#trainJourney .journey-stop.done')).toHaveCount(expectedQuestion);
      await page.locator('#nextQuestion').click();
    }

    await expect(page.locator('#resultScreen')).toHaveClass(/active/);
    await expect(page.locator('#finalScore')).toContainText('5 / 5');
    await expect(page.locator('#resultNote')).toContainText(/到站|sound tickets/);

    if (runtime.ignoredMediaCancels.length) console.log(`Ignored normal media cancellations: ${runtime.ignoredMediaCancels.length}`);
    expect(runtime.consoleErrors).toEqual([]);
    expect(runtime.failedRequests).toEqual([]);
  });

  test('navigation buttons and restart/home flows are wired correctly', async ({ page }) => {
    const runtime = await collectRuntime(page);
    await enterLevel2(page);

    await page.selectOption('#reviewRow', { label: 'U Station - UB to UZ' });
    await expect(page.locator('#stationRoute .station-node.active')).toContainText('U');

    await page.locator('#quizMode').click();
    await expect(page.locator('#quizScreen')).toHaveClass(/active/);

    await page.locator('#restartBtn').click();
    await expect(page.locator('#learnScreen')).toHaveClass(/active/);
    await expect(page.locator('#stationRoute .station-node.active')).toContainText('U');

    await page.locator('#backToStart').click();
    await expect(page.locator('#startScreen')).toHaveClass(/active/);

    expect(runtime.consoleErrors).toEqual([]);
    expect(runtime.failedRequests).toEqual([]);
  });
});
