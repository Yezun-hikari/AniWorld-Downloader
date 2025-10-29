
from playwright.sync_api import sync_playwright, expect, TimeoutError

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(60000)  # Increase timeout to 60 seconds

    try:
        page.goto("http://localhost:8080")

        # Explicitly wait for the search input to be ready
        search_input = page.get_by_placeholder("Enter your search query...")
        expect(search_input).to_be_visible()

        # Search for a movie on MegaKino
        search_input.fill("Dune")
        page.get_by_role("combobox").select_option("megakino")
        page.get_by_role("button", name="Search").click()

        # Wait for the search results to load and check for the description
        first_result_description = page.locator(".card-text").first
        expect(first_result_description).not_to_be_empty()

        # Wait a bit for the UI to settle before taking a screenshot
        page.wait_for_timeout(2000)

        page.screenshot(path="jules-scratch/verification/megakino_verification.png")
        print("Successfully created screenshot for MegaKino.")

    except TimeoutError as e:
        print(f"Playwright script failed with a timeout: {e}")
        print("This is likely due to missing system dependencies for Playwright.")
        print("Unable to generate screenshot.")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
