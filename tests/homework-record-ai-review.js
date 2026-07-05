const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const HOMEWORK_URL = process.env.HOMEWORK_URL || 'https://hkspurs.github.io/yurilearning/phonics-game/homework.html?v=gggeeeggu';
const OUT_DIR = path.resolve('test-results/homework-ai-review');
const VIDEO_WEBM = path.join(OUT_DIR, 'homework-ai-review.webm');
const VIDEO_MP4 = path.join(OUT_DIR, 'homework-ai-review.mp4');
const REPORT_JSON = path.join(OUT_DIR, 'homework-ai-review-report.json');

const SPOT_CHECKS = {
  A: ['AB', 'AM', 'AZ'],
  E: ['EB', 'EM', 'EZ'],
  I: ['IB', 'IM', 'IZ'],
  O: ['OB', 'OM', 'OZ'],
  U: ['UB', 'UM', 'UZ'],
};

async function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function clickExactLabel(page, containerSelector, label) {
  const buttons = page.locator(`${containerSelector} .answer-btn`);
  const index = await buttons.evaluateAll((nodes, target) => {
    return nodes.findIndex(node => (node.firstChild?.textContent || node.textContent || '').trim() === target);
  }, label);
  if (index < 0) throw new Error(`Cannot find exact button label ${label} in ${containerSelector}`);
  await buttons.nth(index).click();
}

async function labelsIn(container) {
  return container.locator('.answer-btn').evaluateAll(nodes => nodes.map(node => (node.firstChild?.textContent || node.textContent || '').trim()));
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    recordVideo: { dir: OUT_DIR, size: { width: 390, height: 844 } },
  });

  const page = await context.newPage();
  const report = {
    url: HOMEWORK_URL,
    checks: [],
    warnings: [],
    generatedAt: new Date().toISOString(),
  };

  function ok(name, details = {}) {
    report.checks.push({ name, status: 'PASS', ...details });
    console.log(`PASS: ${name}`);
  }

  await page.goto(HOMEWORK_URL, { waitUntil: 'networkidle' });
  await page.locator('.brand').waitFor();
  ok('Page loaded');
  await wait(700);

  await page.locator('.level-card').nth(1).click();
  await page.locator('#selectedLevelTitle').waitFor();
  ok('Entered Level 2');
  await wait(900);

  const routeText = await page.locator('#stationRoute').innerText();
  ok('Station route visible', { routeText });

  for (const [row, labels] of Object.entries(SPOT_CHECKS)) {
    const labelText = `${row} Station - ${labels[0]} to ${labels[2]}`;
    await page.selectOption('#reviewRow', { label: labelText });
    await wait(700);
    const activeStation = await page.locator('#stationRoute .station-node.active').innerText();
    const gridLabels = await labelsIn(page.locator('#reviewGrid'));
    ok(`${row} Station selected`, { activeStation, visibleTickets: gridLabels.slice(0, 5) });

    for (const label of labels) {
      await clickExactLabel(page, '#reviewGrid', label);
      await wait(850);
      const audioStatus = await page.locator('#audioStatus').innerText();
      if (!audioStatus.includes(label)) {
        report.warnings.push({ name: `audioStatus may not match ${label}`, audioStatus });
      }
      ok(`Tapped review ticket ${label}`, { audioStatus });
    }
  }

  await page.selectOption('#quizRowFilter', 'A');
  await wait(500);
  await page.locator('#quizMode').click();
  await page.locator('#choices .answer-btn').first().waitFor();
  await wait(700);
  ok('Quiz started');

  await page.locator('#playQuestion').click();
  await wait(700);
  const firstStatus = await page.locator('#audioStatus').innerText();
  const firstChoices = await labelsIn(page.locator('#choices'));
  ok('Quiz play question pressed', { firstStatus, firstChoices });

  // Demonstrate one wrong answer if possible.
  const match = firstStatus.match(/(?:sound ticket|播放車卡|電腦聲音：)\s*([A-Z]{2})/i);
  const correct = match ? match[1].toUpperCase() : firstChoices[0];
  const wrong = firstChoices.find(label => label !== correct) || firstChoices[0];
  await clickExactLabel(page, '#choices', wrong);
  await wait(700);
  ok('Wrong answer tapped', {
    tapped: wrong,
    feedback: await page.locator('#feedback').innerText(),
    tries: await page.locator('#triesText').innerText(),
  });

  if (firstChoices.includes(correct)) {
    await clickExactLabel(page, '#choices', correct);
    await wait(700);
    ok('Correct answer tapped', {
      tapped: correct,
      feedback: await page.locator('#feedback').innerText(),
      score: await page.locator('#scoreText').innerText(),
    });
  }

  for (let i = 0; i < 4; i++) {
    await page.locator('#nextQuestion').click();
    await wait(500);
    await page.locator('#playQuestion').click();
    await wait(500);
    const status = await page.locator('#audioStatus').innerText();
    const choices = await labelsIn(page.locator('#choices'));
    const statusMatch = status.match(/(?:sound ticket|播放車卡|電腦聲音：)\s*([A-Z]{2})/i);
    const answer = statusMatch && choices.includes(statusMatch[1].toUpperCase()) ? statusMatch[1].toUpperCase() : choices[0];
    await clickExactLabel(page, '#choices', answer);
    await wait(500);
    ok(`Quiz question ${i + 2} answered`, {
      status,
      answer,
      feedback: await page.locator('#feedback').innerText(),
    });
  }

  await page.locator('#nextQuestion').click();
  await page.locator('#resultScreen.active').waitFor();
  await wait(1000);
  ok('Result screen shown', {
    finalScore: await page.locator('#finalScore').innerText(),
    resultNote: await page.locator('#resultNote').innerText(),
  });

  fs.writeFileSync(REPORT_JSON, JSON.stringify(report, null, 2));
  const video = page.video();
  await context.close();
  await browser.close();

  if (video) {
    const webmPath = await video.path();
    fs.copyFileSync(webmPath, VIDEO_WEBM);
    console.log(`Video written: ${VIDEO_WEBM}`);
  }

  try {
    execFileSync('ffmpeg', ['-y', '-i', VIDEO_WEBM, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', VIDEO_MP4], { stdio: 'inherit' });
    console.log(`MP4 written: ${VIDEO_MP4}`);
  } catch (err) {
    console.log('ffmpeg not available or MP4 conversion failed. Use the .webm video instead.');
  }

  console.log(`Report written: ${REPORT_JSON}`);
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
