import os
import time
from playwright.sync_api import sync_playwright

def verify_pdf_download():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        print("Navigating to frontend...")
        page.goto("http://localhost:5173")
        
        # Wait for the app to load
        page.wait_for_selector(".chat-input")
        
        print("Filling out the interview...")
        
        # Just type something to get state populated
        page.fill(".chat-input", "Harshad from Pune")
        page.click("button:has-text('Send')")
        time.sleep(2)
        
        # Switch to Document tab
        print("Switching to Document tab...")
        page.click("button:has-text('Document')")
        time.sleep(1)
        
        # Click Download
        print("Clicking download...")
        with page.expect_download() as download_info:
            page.click("button:has-text('Download PDF Document')")
        
        download = download_info.value
        path = download.path()
        print(f"Downloaded PDF to: {path}")
        
        size = os.path.getsize(path)
        print(f"PDF size: {size} bytes")
        
        browser.close()

if __name__ == "__main__":
    verify_pdf_download()
