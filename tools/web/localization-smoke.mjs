// Run against the generated static site without a live server or product releases.
import { chromium } from 'playwright';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import assert from 'node:assert/strict';

const root = resolve(process.argv[2] || '_site');
const origin = 'https://broiler-platform.github.io';
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (['fonts.googleapis.com', 'fonts.gstatic.com'].includes(url.hostname)) {
      return route.fulfill({ contentType: 'text/css', body: '' });
    }
    assert.equal(url.origin, origin);
    const path = resolve(root, '.' + url.pathname + (url.pathname.endsWith('/') ? 'index.html' : ''));
    assert.ok(path.startsWith(root + sep));
    const mime = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png' };
    await route.fulfill({ contentType: mime[extname(path)] || 'application/octet-stream', body: await readFile(path) });
  });

  for (const path of ['/', '/de/', '/applications.html', '/de/applications.html',
    '/applications/browser.html', '/de/applications/browser.html',
    '/applications/writer.html', '/de/applications/writer.html',
    '/applications/code.html', '/de/applications/code.html',
    '/applications/mail.html', '/de/applications/mail.html', '/de/about.html']) {
    await page.goto(origin + path);
    const broken = await page.locator('img').evaluateAll(async images => {
      const results = await Promise.all(images.map(async image => {
        image.loading = 'eager';
        try { await image.decode(); return null; }
        catch { return image.getAttribute('src'); }
      }));
      return results.filter(Boolean);
    });
    assert.deepEqual(broken, [], 'Images must decode on ' + path);
  }
  await page.goto(origin + '/applications/writer.html');
  await page.getByRole('link', { name: 'Deutsch', exact: true }).click();
  await page.waitForURL(origin + '/de/applications/writer.html');
  assert.equal(await page.locator('html').getAttribute('lang'), 'de');
  assert.equal(await page.locator('.nav [aria-current="page"]').getAttribute('href'), '/de/applications.html');
  assert.ok((await page.locator('main').textContent()).includes('Deine Dokumente'));
  await page.getByRole('link', { name: 'English', exact: true }).click();
  await page.waitForURL(origin + '/applications/writer.html');

  await page.goto(origin + '/de/');
  await mkdir('evidence', { recursive: true });
  await page.screenshot({ path: 'evidence/localization-desktop.png', fullPage: true });
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    for (const path of ['/de/', '/de/applications.html', '/de/applications/writer.html', '/architecture.html']) {
      await page.goto(origin + path);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow: ' + path + ' at ' + width);
      const menu = page.locator('[data-nav-toggle]');
      await menu.click();
      assert.equal(await menu.getAttribute('aria-expanded'), 'true');
      await page.locator('.nav a').first().click();
      await page.waitForURL(origin + (path.startsWith('/de/') ? '/de/applications.html' : '/applications.html'));
    }
  }
  await page.goto(origin + '/de/');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'evidence/localization-mobile.png', fullPage: true });
  const theme = page.getByRole('button', { name: 'Farbschema wechseln' });
  await theme.click();
  assert.ok(['light', 'dark'].includes(await page.locator('html').getAttribute('data-theme')));
  // Language switching remains usable if JavaScript is disabled.
  const context = await browser.newContext({ javaScriptEnabled: false });
  const noScript = await context.newPage();
  await noScript.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin) return route.abort();
    const path = resolve(root, '.' + url.pathname + (url.pathname.endsWith('/') ? 'index.html' : ''));
    await route.fulfill({ contentType: extname(path) === '.html' ? 'text/html' : 'text/css', body: await readFile(path) });
  });
  await noScript.goto(origin + '/de/about.html');
  await noScript.getByRole('link', { name: 'English', exact: true }).click();
  await noScript.waitForURL(origin + '/about.html');
  await context.close();
  assert.deepEqual(errors, []);
  console.log('PASS: reciprocal language links, German content and navigation, mobile layouts at 320/390/768px, theme toggle, and language switch without JavaScript.');
} finally {
  await browser.close();
}
