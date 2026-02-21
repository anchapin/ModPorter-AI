import json
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. Go to page
    print("Navigating to dashboard page...")
    page.goto("http://localhost:3000/dashboard")

    # 2. Inject data
    history_data = [
        {
            "job_id": "job-123",
            "original_filename": "test-modpack.zip",
            "status": "completed",
            "created_at": "2023-10-27T10:00:00Z",
            "file_size": 5242880,
            "options": {"smartAssumptions": True, "includeDependencies": True}
        },
        {
            "job_id": "job-456",
            "original_filename": "failed-modpack.zip",
            "status": "failed",
            "created_at": "2023-10-26T10:00:00Z",
            "error_message": "Invalid format"
        }
    ]

    # Use proper JSON stringification
    data_str = json.dumps(history_data)

    # Evaluate with argument
    print("Injecting localStorage data...")
    page.evaluate("(data) => localStorage.setItem('modporter_conversion_history', data)", data_str)

    # 3. Reload
    print("Reloading page...")
    page.reload()

    # 4. Click Tab
    print("Clicking 'Conversion History' tab...")
    # Use text selector or class if known. From screenshot: "Conversion History"
    page.get_by_text("Conversion History").click()

    # 5. Check for loading spinner immediately
    try:
        # Check if list is visible
        history_list = page.locator(".history-list")

        # If loading spinner was there, it might be gone by now if it was fast.
        # But if we see history list immediately, it's good.

        if history_list.is_visible():
             print("SUCCESS: History list is visible.")
        else:
             print("WAITING: History list not yet visible...")
             history_list.wait_for(state="visible", timeout=2000)
             print("SUCCESS: History list is visible after wait.")

        # Check if loading spinner is currently visible
        spinner = page.locator(".conversion-history .loading-spinner")
        if spinner.is_visible():
            print("FAIL: Spinner is visible!")
        else:
            print("SUCCESS: Spinner is NOT visible.")

    except Exception as e:
        print(f"Error: {e}")

    page.screenshot(path="verification_history.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
