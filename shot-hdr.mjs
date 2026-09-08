import { chromium } from '/Users/nanomesh/Workspace/presentation/node_modules/playwright/index.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const demoPath = 'file://' + path.join(__dirname, 'cmx-mega-sheet/demo/index.html');

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage();
await page.setViewportSize({ width: 1440, height: 850 });

const consoleMessages = [];
const pageErrors = [];
page.on('console', msg => consoleMessages.push(`[${msg.type()}] ${msg.text()}`));
page.on('pageerror', err => pageErrors.push(err.message));

await page.goto(demoPath);
await page.waitForTimeout(700);

// Step 2: read outline info via public API
const outlineInfo = await page.evaluate(() => {
  const el = document.getElementById('ms');
  if (!el) return { error: 'no #ms element' };
  try {
    const ws = el.getActiveSheetObject();
    const maxLevel = ws.rowOutlines.maxLevel();
    const groupCount = ws.rowOutlines.list().length;
    return { maxLevel, groupCount };
  } catch (e) {
    return { error: e.message };
  }
});
console.log('outlineInfo:', JSON.stringify(outlineInfo));

// Step 3: screenshot
const screenshotPath = path.join(__dirname, 'cmx-mega-sheet/demo/preview-hdr-fix.png');
await page.screenshot({ path: screenshotPath, fullPage: true });
console.log('Screenshot saved to:', screenshotPath);

// Step 4: count non-blank pixels in row-header band x:[30,80], y:[200,500]
const rowHeaderPixels = await page.evaluate(() => {
  // Find the canvas element inside the shadow DOM or direct
  let canvas = document.querySelector('canvas');
  if (!canvas) {
    // try shadow DOM
    const el = document.getElementById('ms');
    if (el && el.shadowRoot) {
      canvas = el.shadowRoot.querySelector('canvas');
    }
  }
  if (!canvas) return { error: 'no canvas found' };

  const ctx = canvas.getContext('2d');
  if (!ctx) return { error: 'no 2d context' };

  const x1 = 30, x2 = 80, y1 = 200, y2 = 500;
  const w = x2 - x1, h = y2 - y1;
  let imgData;
  try {
    imgData = ctx.getImageData(x1, y1, w, h);
  } catch (e) {
    return { error: e.message };
  }

  let nonBlank = 0;
  const data = imgData.data;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
    // non-blank = not white/near-white and not fully transparent
    if (a > 10 && !(r > 240 && g > 240 && b > 240)) {
      nonBlank++;
    }
  }
  return { nonBlank, totalPixels: w * h };
});
console.log('row-header band [30,80]x[200,500] non-blank pixels:', JSON.stringify(rowHeaderPixels));

// Step 5: check top-left corner x:[0,30], y:[0,80] for level button pixels
const cornerPixels = await page.evaluate(() => {
  let canvas = document.querySelector('canvas');
  if (!canvas) {
    const el = document.getElementById('ms');
    if (el && el.shadowRoot) {
      canvas = el.shadowRoot.querySelector('canvas');
    }
  }
  if (!canvas) return { error: 'no canvas found' };

  const ctx = canvas.getContext('2d');
  if (!ctx) return { error: 'no 2d context' };

  const x1 = 0, x2 = 30, y1 = 0, y2 = 80;
  const w = x2 - x1, h = y2 - y1;
  let imgData;
  try {
    imgData = ctx.getImageData(x1, y1, w, h);
  } catch (e) {
    return { error: e.message };
  }

  let nonBlank = 0;
  const data = imgData.data;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
    if (a > 10 && !(r > 240 && g > 240 && b > 240)) {
      nonBlank++;
    }
  }
  return { nonBlank, totalPixels: w * h };
});
console.log('corner region [0,30]x[0,80] non-blank pixels:', JSON.stringify(cornerPixels));

// Step 6: print collected errors
console.log('Console messages (', consoleMessages.length, '):');
consoleMessages.slice(0, 20).forEach(m => console.log(' ', m));
console.log('Page errors (', pageErrors.length, '):');
pageErrors.slice(0, 10).forEach(e => console.log(' ', e));

await browser.close();
