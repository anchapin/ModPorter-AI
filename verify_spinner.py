from playwright.sync_api import sync_playwright, expect
import re
import os

def verify_conversion_spinner():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Intercept the API call and just let it hang to simulate processing
        def handle_route(route):
            print("Intercepted conversion request. Hanging to verify spinner...")
            # Do not fulfill or continue, effectively hanging the request
            # This keeps the UI in 'isUploading=true' state because convertMod awaits the request

        # Intercept both new and legacy endpoints just in case
        page.route("**/api/v1/conversions", handle_route)
        page.route("**/convert", handle_route) # legacy fallback

        print("Navigating to home page...")
        page.goto("http://localhost:3000")

        # Wait for the page to load
        expect(page.get_by_role("heading", name="Convert Your Modpack")).to_be_visible()

        # Create a dummy file
        with open("test-mod.jar", "w") as f:
            f.write("dummy content")

        print("Uploading file...")
        # Handle file chooser
        with page.expect_file_chooser() as fc_info:
            page.get_by_text("Browse Files").click()
        file_chooser = fc_info.value
        file_chooser.set_files("test-mod.jar")

        # Wait for file preview
        expect(page.get_by_text("test-mod.jar")).to_be_visible()

        # Check initial button text
        convert_button = page.locator(".convert-button")
        expect(convert_button).to_be_visible()
        expect(convert_button).to_be_enabled()
        expect(convert_button).to_have_text("Upload & Convert")

        print("Clicking convert button...")
        convert_button.click()

        # Check for Uploading state
        print("Waiting for Uploading state...")
        # Should show Uploading... X%
        expect(convert_button).to_contain_text("Uploading...", timeout=5000)

        # Check for spinner
        # The spinner is rendered conditionally: {isProcessing && <span className="spinner" ...>}
        # isProcessing = isConverting || isUploading
        # isUploading is true, so spinner should be there.
        print("Checking for spinner...")
        spinner = convert_button.locator(".spinner")
        expect(spinner).to_be_visible()

        print("Taking screenshot...")
        page.screenshot(path="verification_spinner.png")

        print("Verification successful!")

        # Cleanup
        if os.path.exists("test-mod.jar"):
            os.remove("test-mod.jar")

        browser.close()

if __name__ == "__main__":
    verify_conversion_spinner()
