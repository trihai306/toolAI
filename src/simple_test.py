"""
Simple test script to verify element finding functionality
"""

import sys
import time
from pathlib import Path

# Add the root directory to sys.path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from automation import BrowserController

def run_test():
    print("Starting element finder test...")
    
    # Initialize browser
    browser = BrowserController(debug=True)
    
    try:
        # Start browser
        result = browser.start_browser(headless=False)
        print(f"Browser started: {result}")
        
        # Navigate to a test page
        browser.navigate_to('https://www.google.com')
        print("Navigated to Google")
        
        time.sleep(2)
        
        # Test element finding - by selector
        search_box = browser.wait_for_selector('input[name="q"]', timeout=5000)
        print(f"Found search box by selector: {search_box}")
        
        # Test element finding - by description
        search_button = browser.find_element_by_description("search button")
        print(f"Found search button by description: {search_button}")
        
        # Test typing
        browser.type_text('input[name="q"]', "test element finder", description="search box")
        print("Typed text in search box")
        
        time.sleep(1)
        
        # Test clicking
        if search_button:
            success = browser.click_element(search_button, description="search button")
        else:
            success = browser.click_element('input[name="btnK"], input[value="Google Search"]', description="search button")
        print(f"Clicked search button: {success}")
        
        # Wait for results
        time.sleep(3)
        
        # Take screenshot
        screenshot = browser.take_screenshot("test_results.png")
        print(f"Screenshot taken: {screenshot}")
        
        print("Element finder test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        # Wait for user input
        input("Press Enter to close the browser...")
        
        # Close browser
        browser.close_browser()

if __name__ == "__main__":
    run_test()
