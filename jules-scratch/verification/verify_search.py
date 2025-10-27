from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8080/")
    page.check("#site-megakino")
    page.get_by_placeholder("Enter anime or series name...").click()
    page.get_by_placeholder("Enter anime or series name...").fill("Bad Boys")
    page.get_by_role("button", name="Search").click()
    page.screenshot(path="jules-scratch/verification/search_results.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
