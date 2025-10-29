
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://localhost:8080');

  // Wait for the page to load
  await page.waitForSelector('#search-input');

  // Select the MegaKino site
  await page.click('#site-megakino');

  // Enter the search query and click the search button
  await page.fill('#search-input', 'V/H/S');
  await page.click('#search-btn');

  // Wait for the search results to be displayed
  await page.waitForSelector('#results-container .anime-card');

  // Take a screenshot of the results
  await page.screenshot({ path: 'screenshot.png' });

  await browser.close();
})();
