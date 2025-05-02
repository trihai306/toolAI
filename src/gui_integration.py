"""
GUI Integration Module for Browser Automation Agent
Integrates Flask + PyWebView GUI with the main Browser Automation project
"""

import os
import sys
import json
import time
import threading
import logging
import webview
from contextlib import closing
import socket
import subprocess

# Flask imports with compatibility handling
try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session
except ImportError as e:
    print(f"Flask import error: {e}")
    print("Attempting to install compatible Flask and Werkzeug versions...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.1", "werkzeug==2.0.1"])
    # Try importing again
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session

# Import local modules
from src.automation import BrowserController
from src.utils.logging_utils import configure_unicode_logging, get_logger

# Configure logging
logger = get_logger("GUIIntegration")

# Initialize Flask app
app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.secret_key = os.urandom(24)

# Global variables
browser_controller = None
browser_thread = None
command_history = []
is_browser_running = False
current_status = "idle"  # idle, running, error
process_output = []

# Browser configuration parameters
browser_config = {
    "headless": False,
    "user_agent": None,
    "viewport_size": {"width": 1280, "height": 800},
    "locale": "vi-VN"
}

def find_free_port():
    """Find a free port to use for the Flask server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def initialize_browser(browser_type="chromium", headless=False, human_like=False):
    """Initialize the browser controller"""
    global browser_controller, is_browser_running, browser_config
    
    try:
        logger.info(f"Initializing browser: {browser_type}, headless={headless}")
        add_to_output(f"Khởi tạo trình duyệt {browser_type}...")
        
        # Set browser config
        browser_config["headless"] = headless
        
        # Create browser controller
        browser_controller = BrowserController(
            browser_type=browser_type,
            human_like_mode=human_like
        )
        
        # Start browser
        if browser_controller.start_browser(**browser_config):
            logger.info("Browser started successfully")
            add_to_output("Trình duyệt đã khởi động thành công!")
            is_browser_running = True
            return True
        else:
            logger.error("Could not start browser")
            add_to_output("Không thể khởi động trình duyệt!")
            is_browser_running = False
            return False
    except Exception as e:
        logger.error(f"Error initializing browser: {str(e)}")
        add_to_output(f"Lỗi khởi tạo trình duyệt: {str(e)}")
        is_browser_running = False
        return False

def parse_command(command):
    """Parse a natural language command into actions"""
    try:
        # Import here to avoid circular imports
        from src.main import parse_user_command_ai
        parsed = parse_user_command_ai(command)
        return parsed
    except Exception as e:
        logger.error(f"Error parsing command: {str(e)}")
        add_to_output(f"Lỗi phân tích lệnh: {str(e)}")
        return None

def execute_workflow(steps):
    """Execute a workflow of steps"""
    try:
        for idx, step in enumerate(steps, 1):
            action = step.get('action', '')
            selector = step.get('selector', '')
            description = step.get('description', '') or step.get('text', '')
            value = step.get('value', '')
            
            add_to_output(f"Bước {idx}: {action} - {selector or description}")
            
            if action == 'click' and selector:
                browser_controller.page.click(selector)
            elif action == 'type' and selector:
                browser_controller.page.fill(selector, value)
            elif action == 'find_and_click' and description:
                xpath = f"//button[contains(text(), '{description}')] | //a[contains(text(), '{description}')] | //*[@value='{description}'] | //*[contains(text(), '{description}')]"
                browser_controller.page.click(f"xpath={xpath}")
            elif action == 'wait':
                wait_time = float(step.get("time", 1.0))
                time.sleep(wait_time)
            elif action == 'scroll':
                direction = step.get("direction", "down")
                distance = step.get("distance", 500)
                if direction == "down":
                    browser_controller.page.evaluate(f"window.scrollBy(0, {distance})")
                else:
                    browser_controller.page.evaluate(f"window.scrollBy(0, -{distance})")
            
            # Wait a bit between actions
            time.sleep(0.5)
        
        return True
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        add_to_output(f"Lỗi thực thi workflow: {str(e)}")
        return False

def add_to_output(message):
    """Add message to output log"""
    global process_output
    process_output.append(message)
    logger.info(message)

def run_command(command):
    """Run a command in the browser"""
    global current_status, process_output
    
    if not is_browser_running:
        return {"success": False, "message": "Browser is not running"}
    
    current_status = "running"
    process_output = []
    
    try:
        # Log the command
        logger.info(f"Running command: {command}")
        command_history.append(command)
        
        # Add to output log
        add_to_output(f"Thực thi lệnh: {command}")
        
        # Parse and execute command
        try:
            # Use the command parsing logic
            parsed = parse_command(command)
            
            if not parsed:
                add_to_output("Không thể phân tích lệnh. Vui lòng thử lại.")
                current_status = "error"
                return {"success": False, "message": "Could not parse command"}
            
            url = parsed.get("url")
            steps = parsed.get("steps", [])
            
            # Navigate to URL
            add_to_output(f"Đang điều hướng đến {url}...")
            success = browser_controller.navigate_to(url)
            
            if success:
                add_to_output(f"Đã điều hướng thành công đến {url}")
                time.sleep(2)  # Allow page to load
            else:
                add_to_output(f"Không thể điều hướng đến {url}")
                current_status = "error"
                return {"success": False, "message": f"Failed to navigate to {url}"}
            
            # Execute steps
            if steps:
                add_to_output("Thực thi các bước workflow:")
                success = execute_workflow(steps)
                
                if success:
                    add_to_output("Đã thực thi tất cả các bước thành công")
                else:
                    add_to_output("Lỗi thực thi workflow")
                    current_status = "error"
                    return {"success": False, "message": "Error executing workflow steps"}
            else:
                add_to_output("Không có bước nào để thực thi")
            
            current_status = "idle"
            return {"success": True, "message": "Command executed successfully"}
            
        except Exception as e:
            add_to_output(f"Lỗi: {str(e)}")
            current_status = "error"
            logger.error(f"Error executing command: {str(e)}")
            return {"success": False, "message": str(e)}
    except Exception as e:
        add_to_output(f"Lỗi: {str(e)}")
        current_status = "error"
        logger.error(f"Error in run_command: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        current_status = "idle"

def run_command_thread(command):
    """Run a command in a separate thread"""
    global browser_thread
    
    # If there's already a thread running, don't start a new one
    if browser_thread and browser_thread.is_alive():
        return {"success": False, "message": "A command is already running"}
    
    # Create and start the thread
    browser_thread = threading.Thread(target=run_command, args=(command,))
    browser_thread.daemon = True
    browser_thread.start()
    
    return {"success": True, "message": "Command started"}

def stop_browser():
    """Stop the browser and clean up resources"""
    global browser_controller, is_browser_running
    
    if browser_controller:
        try:
            add_to_output("Đang đóng trình duyệt...")
            browser_controller.close_browser()
            add_to_output("Đã đóng trình duyệt")
            is_browser_running = False
            return True
        except Exception as e:
            logger.error(f"Error stopping browser: {str(e)}")
            add_to_output(f"Lỗi khi đóng trình duyệt: {str(e)}")
            return False
    return True

def take_screenshot():
    """Take a screenshot of the current browser state"""
    if not is_browser_running or not browser_controller:
        return None
    
    try:
        add_to_output("Đang chụp ảnh màn hình...")
        screenshot_path = browser_controller.take_screenshot()
        add_to_output(f"Đã chụp ảnh màn hình: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        add_to_output(f"Lỗi chụp ảnh màn hình: {str(e)}")
        return None

def check_playwright_installation():
    """Check if Playwright is installed properly"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                # Try to launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                browser.close()
                return {"installed": True, "message": "Playwright is installed correctly"}
            except Exception as e:
                return {"installed": False, "message": f"Playwright is installed but browsers may be missing: {str(e)}"}
    except ImportError:
        return {"installed": False, "message": "Playwright is not installed"}
    except Exception as e:
        return {"installed": False, "message": f"Unknown error checking Playwright: {str(e)}"}

# Flask routes
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/start-browser', methods=['POST'])
def api_start_browser():
    """API endpoint to start the browser"""
    global is_browser_running
    
    if is_browser_running:
        return jsonify({"success": False, "message": "Browser is already running"})
    
    browser_type = request.json.get('browser_type', 'chromium')
    headless = request.json.get('headless', False)
    
    # Check Playwright installation first
    playwright_check = check_playwright_installation()
    if not playwright_check["installed"]:
        return jsonify({"success": False, "message": playwright_check["message"]})
    
    success = initialize_browser(browser_type, headless)
    
    if success:
        return jsonify({"success": True, "message": "Browser started successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to start browser"})

@app.route('/api/stop-browser', methods=['POST'])
def api_stop_browser():
    """API endpoint to stop the browser"""
    global is_browser_running
    
    if not is_browser_running:
        return jsonify({"success": False, "message": "Browser is not running"})
    
    success = stop_browser()
    
    if success:
        return jsonify({"success": True, "message": "Browser stopped successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to stop browser"})

@app.route('/api/run-command', methods=['POST'])
def api_run_command():
    """API endpoint to run a command"""
    if not is_browser_running:
        return jsonify({"success": False, "message": "Browser is not running"})
    
    command = request.json.get('command', '')
    
    if not command:
        return jsonify({"success": False, "message": "No command provided"})
    
    result = run_command_thread(command)
    
    return jsonify(result)

@app.route('/api/command-status', methods=['GET'])
def api_command_status():
    """API endpoint to get the status of the current command"""
    return jsonify({
        "status": current_status,
        "output": process_output,
        "is_browser_running": is_browser_running
    })

@app.route('/api/take-screenshot', methods=['POST'])
def api_take_screenshot():
    """API endpoint to take a screenshot"""
    if not is_browser_running:
        return jsonify({"success": False, "message": "Browser is not running"})
    
    screenshot_path = take_screenshot()
    
    if screenshot_path:
        return jsonify({"success": True, "path": screenshot_path})
    else:
        return jsonify({"success": False, "message": "Failed to take screenshot"})

@app.route('/api/command-history', methods=['GET'])
def api_command_history():
    """API endpoint to get the command history"""
    return jsonify({"history": command_history})

@app.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint to check if server is running"""
    return jsonify({"status": "ok"})

@app.route('/api/check-dependencies', methods=['GET'])
def api_check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import flask
        import webview
        
        playwright_status = check_playwright_installation()
        
        if playwright_status["installed"]:
            return jsonify({
                "all_installed": True,
                "flask_version": flask.__version__,
                "webview_version": webview.__version__,
                "playwright_status": "installed"
            })
        else:
            return jsonify({
                "all_installed": False,
                "missing": ["playwright_browsers"],
                "error": playwright_status["message"]
            })
    except ImportError as e:
        module_name = str(e).split("'")[1] if "'" in str(e) else str(e)
        return jsonify({
            "all_installed": False,
            "missing": [module_name],
            "error": str(e)
        })

@app.route('/api/check-browser-config', methods=['GET'])
def api_check_browser_config():
    """Check browser configuration"""
    return jsonify(check_playwright_installation())

@app.route('/check')
def check_page():
    """Render the connection check page"""
    return render_template('check.html')

@app.route('/debug')
def debug_page():
    """Debug page with detailed information"""
    info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "modules": {
            "flask": None,
            "webview": None,
            "playwright": None,
            "openai": None
        },
        "paths": {
            "current_dir": os.path.abspath(os.curdir),
            "app_dir": os.path.dirname(os.path.abspath(__file__)),
            "sys_path": sys.path
        },
        "browser_status": {
            "running": is_browser_running,
            "status": current_status,
            "config": browser_config
        }
    }
    
    # Check modules
    for module in info["modules"]:
        try:
            m = __import__(module)
            info["modules"][module] = getattr(m, "__version__", "Unknown version")
        except ImportError:
            info["modules"][module] = "Not installed"
    
    return render_template('debug.html', info=info)

def run_server(port=None):
    """Run the Flask server"""
    global app
    if port is None:
        port = find_free_port()
    
    # Bật debug mode
    app.run(debug=True, host='0.0.0.0', port=port)

def start_gui(port=None):
    """Start the GUI with PyWebView"""
    if port is None:
        port = find_free_port()
    
    logger.info(f"Starting GUI on port {port}")
    
    # Start Flask server in a separate thread
    server_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=port, debug=False, threaded=True))
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Create PyWebView window
    try:
        url = f"http://127.0.0.1:{port}"
        window = webview.create_window(
            'Browser Automation Manager', 
            url, 
            width=1200, 
            height=800,
            min_size=(800, 600)
        )
        webview.start(debug=True)
        
        # Clean up when window is closed
        stop_browser()
    except Exception as e:
        logger.error(f"Error starting PyWebView: {str(e)}")
        print(f"PyWebView error: {str(e)}")
        print(f"Please open {url} in your browser manually")
        
        # Keep server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Server stopped")
            stop_browser()
