"""
Test script to verify Playwright installation and browser functionality
"""

import os
import sys
from playwright.sync_api import sync_playwright

def test_browser(browser_type="chromium"):
    """Test if a browser can be launched properly"""
    print(f"Testing {browser_type} browser...")
    try:
        with sync_playwright() as p:
            if browser_type == "chromium":
                browser_launcher = p.chromium
            elif browser_type == "firefox":
                browser_launcher = p.firefox
            elif browser_type == "webkit":
                browser_launcher = p.webkit
            else:
                print(f"Unknown browser type: {browser_type}")
                return False
                
            # Try to launch browser
            print(f"Attempting to launch {browser_type}...")
            browser = browser_launcher.launch(headless=True)
            
            # Create a page and navigate
            print("Creating page...")
            page = browser.new_page()
            
            print("Navigating to google.com...")
            page.goto("https://www.google.com")
            
            # Take screenshot as proof
            screenshot_path = os.path.join(os.path.dirname(__file__), f"{browser_type}_test.png")
            print(f"Taking screenshot: {screenshot_path}")
            page.screenshot(path=screenshot_path)
            
            # Close browser
            print("Closing browser...")
            browser.close()
            
            print(f"✅ {browser_type} test PASSED!")
            return True
            
    except Exception as e:
        print(f"❌ {browser_type} test FAILED: {str(e)}")
        return False

def main():
    """Run tests for all browser types"""
    print("=== PLAYWRIGHT BROWSER TEST ===\n")
    
    print("Python version:", sys.version)
    print("System platform:", sys.platform)
    
    # Try to get Playwright version
    try:
        import playwright
        print("Playwright version:", playwright.__version__)
    except (ImportError, AttributeError):
        print("Could not determine Playwright version")
    
    print("\nTesting browsers...")
    results = {}
    
    for browser in ["chromium", "firefox", "webkit"]:
        results[browser] = test_browser(browser)
        print()
    
    print("=== TEST SUMMARY ===")
    all_passed = True
    for browser, result in results.items():
        print(f"{browser}: {'✅ PASSED' if result else '❌ FAILED'}")
        all_passed = all_passed and result
    
    if all_passed:
        print("\nAll browser tests passed! Playwright is working correctly.")
    else:
        print("\nSome browser tests failed. Check the logs above for details.")
        
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
