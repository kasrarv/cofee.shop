#!/usr/bin/env node
/**
 * ساختِ خروجی‌های پوستر از روی همان یک الگو.
 *
 *   node build.js                       ← اطلاعاتِ پیش‌فرضِ داخل poster.html
 *   node build.js sessions/mordad.json  ← اطلاعاتِ یک نشستِ مشخص
 *   node build.js sessions/mordad.json --name mordad-29
 *
 * خروجی در پوشهٔ out/ :
 *   ‑ *-post.png    ۱۰۸۰×۱۳۵۰   پستِ اینستاگرام، تلگرام، واتساپ
 *   ‑ *-story.png   ۱۰۸۰×۱۹۲۰   استوری (با حاشیهٔ امن)
 *   ‑ *-print.png   ۳۵۷۹×۵۰۳۲   A3 با ۳۰۰dpi و ۳ میلی‌متر نشتِ رنگ
 *   ‑ *-print.pdf   ۳۰۳×۴۲۶ mm  فایلِ چاپ، متن به‌صورت برداری
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium';
const PAGE   = 'file://' + path.join(__dirname, 'poster.html');
const OUT    = path.join(__dirname, 'out');

const args = process.argv.slice(2);
const dataFile = args.find(a => !a.startsWith('--'));
const nameIdx  = args.indexOf('--name');
const prefix   = nameIdx > -1 ? args[nameIdx + 1] : 'poster';
const overrides = dataFile ? JSON.parse(fs.readFileSync(dataFile, 'utf8')) : null;

const draw = async (page, fmt) =>
  page.evaluate(async ([o, f]) => {
    if (o) Object.assign(DATA, o);
    await render(f);
    document.querySelector('.stage').style.setProperty('--fit', 1);
  }, [overrides, fmt]);

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME });

  /* ــ تصویرها ــ scale: نسبتِ پیکسل به واحدِ CSS (۳٫۱۲۵ ⇒ ۳۰۰dpi) */
  for (const [fmt, w, h, scale] of [
    ['post',  1080, 1350, 1],
    ['story', 1080, 1920, 1],
    ['print', 1145.2, 1610.08, 3.125],   /* ۹۶dpi × ۳٫۱۲۵ = ۳۰۰dpi */
  ]) {
    const page = await browser.newPage({
      viewport: { width: Math.round(w), height: Math.round(h) },
      deviceScaleFactor: scale,
    });
    await page.goto(`${PAGE}?f=${fmt}&fit=0`, { waitUntil: 'networkidle' });
    await draw(page, fmt);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const file = path.join(OUT, `${prefix}-${fmt}.png`);
    await page.screenshot({ path: file });
    console.log('✓', path.relative(process.cwd(), file));
    await page.close();
  }

  /* ــ فایلِ چاپ ــ A3 + ۳ میلی‌متر نشتِ رنگ در هر طرف = ۳۰۳×۴۲۶ میلی‌متر */
  const page = await browser.newPage({ viewport: { width: 1146, height: 1611 } });
  await page.goto(`${PAGE}?f=print&fit=0`, { waitUntil: 'networkidle' });
  await draw(page, 'print');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  const pdf = path.join(OUT, `${prefix}-print.pdf`);
  await page.pdf({ path: pdf, width: '1145.2px', height: '1610.08px', printBackground: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  console.log('✓', path.relative(process.cwd(), pdf));

  await browser.close();
})();
