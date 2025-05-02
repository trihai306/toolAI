"""
GUI Manager for Browser Automation Agent with Werkzeug compatibility fix
Provides a user-friendly interface using Flask and PyWebView
"""

import os
import sys
import json
import time
import threading
import logging
import webview
import socket
from contextlib import closing

# Workaround for Werkzeug import issues
try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session
except ImportError as e:
    if "url_quote" in str(e):
        print("Detected Werkzeug compatibility issue. Applying fix...")
        # Install compatible versions
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.1", "werkzeug==2.0.1"])
        # Now try importing again
        from flask import Flask, render_template, request, jsonify, redirect, url_for, session
    else:
        raise

# Add the parent directory to sys.path so we can import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import from src modules
try:
    from src.main import BrowserAutomationAgent
    from src.utils.logging_utils import configure_unicode_logging
    
    # Configure logging
    configure_unicode_logging("gui_manager.log", logging.INFO)
except ImportError as e:
    print(f"Warning: Unable to import from src modules: {e}")
    logging.basicConfig(
        filename="gui_manager.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    BrowserAutomationAgent = None  # Will be handled gracefully later

logger = logging.getLogger("GUIManager")

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = os.urandom(24)

# Global variables
browser_agent = None
agent_thread = None
command_history = []
is_browser_running = False
current_status = "idle"  # idle, running, error
process_output = []

def find_free_port():
    """Find a free port to use for the Flask server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def initialize_agent(browser_type="chromium", headless=False):
    """Initialize the browser automation agent"""
    global browser_agent, is_browser_running
    try:
        if BrowserAutomationAgent is None:
            logger.error("BrowserAutomationAgent module could not be imported")
            return False
            
        browser_agent = BrowserAutomationAgent(
            browser_type=browser_type,
            headless=headless,
            human_like=False  # Tắt chế độ giả lập người
        )
        # Configure browser
        browser_config = {
            "headless": headless,
            "user_agent": None,
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        # Start browser
        if browser_agent.browser.start_browser(**browser_config):
            logger.info("Browser started successfully")
            is_browser_running = True
            return True
        else:
            logger.error("Could not start browser")
            return False
    except Exception as e:
        logger.error(f"Error initializing agent: {str(e)}")
        return False

def run_command(command):
    """Run a command in the browser agent"""
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
        process_output.append(f"Running command: {command}")
        
        # Parse and execute command
        try:
            # Use the agent's command parsing logic
            if hasattr(browser_agent, 'parse_user_command_ai'):
                parsed = browser_agent.parse_user_command_ai(command)
            else:
                process_output.append("Command parsing not available")
                current_status = "error" 
                return {"success": False, "message": "Command parsing not available"}
            
            if not parsed:
                process_output.append("Could not parse command. Please try again.")
                current_status = "error"
                return {"success": False, "message": "Could not parse command"}
            
            url = parsed.get("url")
            steps = parsed.get("steps", [])
            
            # Navigate to URL
            process_output.append(f"Navigating to {url}...")
            success = browser_agent.navigate_to(url)
            
            if success:
                process_output.append(f"Successfully navigated to {url}")
                time.sleep(2)  # Allow page to load
            else:
                process_output.append(f"Failed to navigate to {url}")
                current_status = "error"
                return {"success": False, "message": f"Failed to navigate to {url}"}
            
            # Execute steps
            if steps:
                process_output.append("Executing workflow steps:")
                for idx, step in enumerate(steps, 1):
                    action = step.get('action', '')
                    selector = step.get('selector', '')
                    description = step.get('description', '') or step.get('text', '')
                    value = step.get('value', '')
                    
                    step_description = f"Step {idx}: "
                    if action == 'type':
                        step_description += f"Type '{value}' into {selector or description}"
                    elif action == 'click':
                        step_description += f"Click on {selector or description}"
                    elif action == 'find_and_click':
                        step_description += f"Find and click on '{description}'"
                    elif action == 'scroll':
                        step_description += f"Scroll {step.get('direction', 'down')}"
                    elif action == 'wait':
                        step_description += f"Wait {step.get('time', 1.0)} seconds"
                    else:
                        step_description += f"{action} | {step}"
                    
                    process_output.append(step_description)
                    
                # Execute steps
                try:
                    if hasattr(browser_agent.browser, 'execute_workflow'):
                        success = browser_agent.browser.execute_workflow(steps)
                    else:
                        # Fallback to manual execution
                        success = True
                        for step in steps:
                            action = step.get('action', '').lower()
                            if action == 'click' and 'selector' in step:
                                browser_agent.browser.page.click(step['selector'])
                            elif action == 'type' and 'selector' in step and 'value' in step:
                                browser_agent.browser.page.fill(step['selector'], step['value'])
                            elif action == 'wait':
                                time.sleep(float(step.get('time', 1.0)))
                    
                    if success:
                        process_output.append("Successfully executed all steps")
                    else:
                        process_output.append("Error executing workflow steps")
                        current_status = "error"
                        return {"success": False, "message": "Error executing workflow steps"}
                except Exception as e:
                    process_output.append(f"Error executing workflow: {str(e)}")
                    current_status = "error"
                    return {"success": False, "message": f"Error executing workflow: {str(e)}"}
            else:
                process_output.append("No steps to execute")
            
            current_status = "idle"
            return {"success": True, "message": "Command executed successfully"}
            
        except Exception as e:
            process_output.append(f"Error: {str(e)}")
            current_status = "error"
            logger.error(f"Error executing command: {str(e)}")
            return {"success": False, "message": str(e)}
    except Exception as e:
        process_output.append(f"Error: {str(e)}")
        current_status = "error"
        logger.error(f"Error in run_command: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        current_status = "idle"

def run_command_thread(command):
    """Run a command in a separate thread"""
    global agent_thread
    
    # If there's already a thread running, don't start a new one
    if agent_thread and agent_thread.is_alive():
        return {"success": False, "message": "A command is already running"}
    
    # Create and start the thread
    agent_thread = threading.Thread(target=run_command, args=(command,))
    agent_thread.daemon = True
    agent_thread.start()
    
    return {"success": True, "message": "Command started"}

def stop_browser():
    """Stop the browser and clean up resources"""
    global browser_agent, is_browser_running
    
    if browser_agent:
        try:
            if hasattr(browser_agent, '_cleanup'):
                browser_agent._cleanup()
            is_browser_running = False
            return True
        except Exception as e:
            logger.error(f"Error stopping browser: {str(e)}")
            return False
    return True

def take_screenshot():
    """Take a screenshot of the current browser state"""
    if not is_browser_running or not browser_agent:
        return None
    
    try:
        if hasattr(browser_agent.browser, 'take_screenshot'):
            screenshot_path = browser_agent.browser.take_screenshot()
            return screenshot_path
        else:
            logger.error("Screenshot function not available")
            return None
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return None

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
    
    success = initialize_agent(browser_type, headless)
    
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

def run_server(port=None):
    """Run the Flask server"""
    if port is None:
        port = find_free_port()
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
    return port
