// Exercise the actual teacher workflow routes without agent logins or paid services.
import { chromium } from '@playwright/test';
import { createService } from '../desktop/service/server.mjs';
import { mkdir, mkdtemp, cp } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

await mkdir('.cache', { recursive: true });
const stateDir = await mkdtemp(path.resolve('.cache/owl-ui-'));
const home = path.join(stateDir, 'home');
await mkdir(home);
await cp('public/assets', 'dist/assets', { recursive: true });
const server = await createService({ repo: process.cwd(), stateDir, uiDir: path.resolve('dist'), restoreSessions: false, mcpOptions: { home, env: {} } });
let browser;
try {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(server.urls.workspace);
    await page.getByRole('heading', { name: 'What are we teaching next?' }).waitFor();
    assert.match(await page.title(), /Mr\. Owl/);
    await page.locator('.home-hero img').evaluate(img => img.decode());
    await page.screenshot({ path: `.cache/mr-owl-${width}.png`, fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const links = await page.locator('.teaching-actions a').all();
    const targets = await Promise.all(links.map(link => link.getAttribute('href')));
    assert.equal(targets.length, 5);
    for (const [i, target] of targets.entries()) {
      await page.goto(server.urls.workspace + target);
      await page.locator('.mak-markdown h1').waitFor();
      assert.equal(await page.getByRole('tab').nth(i).getAttribute('aria-selected'), 'true');
      assert.match(await page.locator('.mak-markdown').innerText(), /Start with this prompt/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.screenshot({ path: `.cache/teaching-${width}-${i}.png`, fullPage: true });
    }
    await page.getByRole('button', { name: 'Workspace', exact: true }).click();
    if (!await page.getByRole('textbox', { name: 'Search entities' }).isVisible()) await page.getByRole('button', { name: 'Show menu', exact: true }).click();
    await page.getByRole('textbox', { name: 'Search entities' }).fill('Teaching Studio');
    await page.locator('.entity-card[data-entity="teaching-studio"]').waitFor();
    assert.equal(await page.locator('.entity-card').count(), 1);
  }
  assert.deepEqual(errors, []);
  console.log('Mr. Owl UI passed: five workflow routes, search, owl images and wide/narrow layouts.');
} finally {
  await browser?.close();
  await server.close();
}
