import json
import os
from playwright.sync_api import sync_playwright, TimeoutError

SESSION_FILE = "session.json"
PRODUCTS_FILE = "prod1.json"

EMAIL = "nikhath.fatimam@gmail.com"
PASSWORD = "VBFzAiNg"


def save_session(context, file_path=SESSION_FILE):
    """Save the current browser context's session (cookies & localStorage)."""
    storage = context.storage_state()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(storage, f, indent=4)
    print(f"Session saved to {file_path}")


def load_or_create_context(browser):
    """
    Load existing session if available; otherwise create a new browser context and login.
    Returns the browser context and the page object.
    """
    context = None
    page = None

    if os.path.exists(SESSION_FILE):
        try:
            context = browser.new_context(storage_state=SESSION_FILE)
            page = context.new_page()
            print("Loaded existing session")
            return context, page
        except Exception as e:
            print(f"Failed to load session: {e}, will create a new session.")

    # If no session or failed to load, create new context
    context = browser.new_context()
    page = context.new_page()
    login_and_save_session(page, EMAIL, PASSWORD)
    save_session(context)
    return context, page


def login_and_save_session(page, email, password):
    """Perform login using provided credentials."""
    try:
        page.goto("https://hiring.idenhq.com/")
        page.wait_for_selector("input#email", timeout=10000)
        page.fill("input#email", email)
        page.fill("input#password", password)
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle", timeout=15000)
        print("Login successful")
    except TimeoutError:
        print("Timeout while logging in. Check selectors or network.")


def navigate_to_products(page):
    page.goto("https://hiring.idenhq.com/instructions")
    page.wait_for_selector("text=Launch Challenge")
    page.click("text=Launch Challenge")
    page.wait_for_url("**/challenge")
    page.click("text=Open Dashboard Menu")
    page.click("text=Data Tools")
    page.click("text=Data Tools")
    page.click("text=Inventory Options")
    page.click("text=Open Products Drawer")
    page.get_by_role("button", name="Open Products Drawer").click()
    page.wait_for_selector("div.space-y-2 div.flex.flex-col")


def extract_all_products(page, table_selector="div.space-y-2 > div.flex.flex-col"):
    """
    Extract all products from a table with lazy loading and pagination.
    Returns a list of product rows.
    """
    all_data = []
    page_number = 1

    while True:
        print(f"➡️ Extracting page {page_number}...")

        # 1. Scroll to bottom to load lazy-loaded rows
        last_count = 0
        scroll_attempts = 0
        while True:
            rows = page.query_selector_all(table_selector)
            current_count = len(rows)
            if current_count == last_count or scroll_attempts > 100:
                break
            last_count = current_count
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(500)
            scroll_attempts += 1

        # 2. Extract all rows on this page
        data = page.eval_on_selector_all(
            table_selector,
            "elements => elements.map(el => el.innerText.trim().split('\\n'))"
        )
        all_data.extend(data)
        print(f"Loaded {len(all_data)} rows so far")

        # 3. Check if a "Next" button exists and is enabled
        try:
            next_btn = page.query_selector("button:has-text('Next')")
            if next_btn and next_btn.is_enabled():
                next_btn.click()
                page.wait_for_timeout(1000)  # small wait for next page to load
                page_number += 1
            else:
                break
        except Exception:
            break

    print(f"Finished extraction: {len(all_data)} rows collected")
    return all_data



def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)

            # Load or create session
            context, page = load_or_create_context(browser)

            # Navigate and extract
            navigate_to_products(page)
            products = extract_all_products(page)

            # Save extracted data
            with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=4, ensure_ascii=False)

            print(f"✅ Extracted {len(products)} products into {PRODUCTS_FILE}")

            browser.close()

    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
