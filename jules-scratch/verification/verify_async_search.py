
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:8080")

    # Wait for the main search input to be visible
    search_input = page.locator('#search-input')
    search_input.wait_for(state='visible')

    # Perform a search for "One Piece" on "All" sites
    search_input.fill("One Piece")
    page.get_by_label("All").check()
    page.get_by_role("button", name="Search").click()

    # Wait for the initial (fast) results to load and take a screenshot
    page.wait_for_selector(".anime-card")
    page.screenshot(path="jules-scratch/verification/01_initial_results.png")

    # Wait for the MegaKino results to be appended asynchronously
    page.wait_for_function("""
        () => {
            const cards = document.querySelectorAll('.anime-card');
            for (const card of cards) {
                const siteInfo = card.querySelector('.anime-info');
                if (siteInfo && siteInfo.textContent.includes('MegaKino')) {
                    return true;
                }
            }
            return false;
        }
    """)
    page.screenshot(path="jules-scratch/verification/02_appended_results.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
