"""
GUI Manager for Browser Automation Agent
Provides a user-friendly interface using Flask and PyWebView
"""

import os
import sys
import json
import time
import threading
import logging
import webview
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import socket
from contextlib import closing

# Add the parent directory to sys.path so we can import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import from src modules
try:
    from src.main import BrowserAutomationAgent, parse_user_command_ai, confirm_workflow
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
agent = None
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
    global agent, is_browser_running
    try:
        # Kiểm tra BrowserController hiện tại
        from automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        
        # Nếu đã có instance BrowserController và browser đang chạy, sử dụng lại
        if current_browser_controller and current_browser_controller.browser is not None:
            # Kiểm tra xem page còn hoạt động không
            try:
                if current_browser_controller.page and current_browser_controller.page.url:
                    logger.info(f"Sử dụng lại BrowserController hiện tại, page hiện tại: {current_browser_controller.page.url}")
                    # Đảm bảo agent sử dụng BrowserController hiện tại
                    if agent is None:
                        agent = BrowserAutomationAgent(
                            browser_controller=current_browser_controller,
                            browser_type=browser_type,
                            headless=False,
                            human_like=True
                        )
                    is_browser_running = True
                    return True
            except Exception as e:
                logger.warning(f"BrowserController hiện tại có vấn đề: {str(e)}, sẽ khởi tạo mới")
        
        # Nếu chưa có hoặc browser không còn hoạt động, tạo mới
        if agent is not None and hasattr(agent, 'browser') and agent.browser is not None:
            try:
                agent._cleanup()  # Đóng browser cũ nếu có
            except Exception as e:
                logger.warning(f"Không thể đóng browser cũ: {str(e)}")
                
        agent = BrowserAutomationAgent(
            browser_type=browser_type,
            headless=False,  # Luôn hiển thị giao diện
            human_like=True  # Bật chế độ giả lập người
        )
        
        # Configure browser
        browser_config = {
            "headless": False,  # Luôn hiển thị giao diện
            "user_agent": None,
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        
        # Start browser
        if agent.browser.start_browser(**browser_config):
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
    global current_status, process_output, agent, is_browser_running
    
    if not is_browser_running or not agent or not hasattr(agent, 'browser') or not agent.browser:
        return {"success": False, "message": "Browser is not running"}
    
    # Kiểm tra page trước khi thực hiện lệnh
    try:
        if not agent.browser._ensure_page():
            logger.error("Page không còn hoạt động, không thể thực hiện lệnh")
            return {"success": False, "message": "Page không còn hoạt động, không thể thực hiện lệnh"}
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra page: {str(e)}")
        return {"success": False, "message": f"Lỗi khi kiểm tra page: {str(e)}"}
    
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
            parsed = parse_user_command_ai(command)
            
            if not parsed:
                process_output.append("Could not parse command. Please try again.")
                current_status = "error"
                return {"success": False, "message": "Could not parse command"}
            
            url = parsed.get("url")
            steps = parsed.get("steps", [])
            
            # Navigate to URL
            process_output.append(f"Navigating to {url}...")
            success = agent.navigate_to(url)
            
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
                    # Kiểm tra lại page một lần nữa trước khi thực hiện các bước
                    if not agent.browser._ensure_page():
                        process_output.append("Error: Page is not active anymore")
                        current_status = "error"
                        return {"success": False, "message": "Error: Page is not active anymore"}
                        
                    success = agent.browser.execute_human_like_workflow(steps)
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
    global agent, is_browser_running
    
    if agent:
        try:
            agent._cleanup()
            is_browser_running = False
            return True
        except Exception as e:
            logger.error(f"Error stopping browser: {str(e)}")
            return False
    return True

def take_screenshot():
    """Take a screenshot of the current browser state"""
    if not is_browser_running or not agent:
        return None
    
    try:
        screenshot_path = agent.browser.take_screenshot()
        return screenshot_path
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
    global agent, is_browser_running
    
    try:
        # Kiểm tra BrowserController hiện tại
        from automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        
        # Nếu đã có instance BrowserController và browser đang chạy
        if current_browser_controller and current_browser_controller.browser is not None:
            # Kiểm tra xem page còn hoạt động không
            try:
                url = current_browser_controller.page.url if hasattr(current_browser_controller, 'page') and current_browser_controller.page else None
                if url:
                    logger.info(f"Browser đã khởi động, page hiện tại: {url}")
                    # Đảm bảo agent sử dụng BrowserController hiện tại
                    if agent is None:
                        agent = BrowserAutomationAgent(
                            browser_controller=current_browser_controller,
                            browser_type=request.json.get('browser_type', 'chromium'),
                            headless=False,
                            human_like=True
                        )
                    is_browser_running = True
                    return jsonify({"success": True, "message": "Browser đã khởi động trước đó"})
            except Exception as e:
                logger.warning(f"Browser đang chạy nhưng page không hoạt động, sẽ khởi động lại: {str(e)}")
                # Tiếp tục khởi động lại browser phía dưới
                is_browser_running = False
    
        browser_type = request.json.get('browser_type', 'chromium')
        headless = False  # Luôn đặt headless=False để hiển thị giao diện
        
        # Đóng browser cũ nếu có
        if agent is not None and hasattr(agent, 'browser') and agent.browser is not None:
            try:
                agent._cleanup()
            except Exception as e:
                logger.warning(f"Không thể đóng browser cũ: {str(e)}")
        
        # Khởi tạo agent mới
        agent = BrowserAutomationAgent(
            browser_type=browser_type,
            headless=headless,
            human_like=True  # Bật chế độ giả lập người
        )
        
        # Cấu hình browser
        browser_config = {
            "headless": headless,  # Luôn là False
            "user_agent": None,
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        
        # Khởi động browser
        logger.info("Đang khởi động browser...")
        if agent.browser.start_browser(**browser_config):
            logger.info("Browser khởi động thành công")
            is_browser_running = True
            return jsonify({"success": True, "message": "Browser khởi động thành công"})
        else:
            logger.error("Không thể khởi động browser")
            return jsonify({"success": False, "message": "Không thể khởi động browser"})
    except Exception as e:
        logger.error(f"Lỗi khi khởi động browser: {str(e)}")
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"})

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
    global agent, is_browser_running
    
    try:
        command = request.json.get('command', '')
        if not command:
            return jsonify({"success": False, "message": "Không có lệnh nào được cung cấp"})
        
        # Kiểm tra BrowserController hiện tại
        from automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        
        # Nếu có BrowserController với browser đang chạy, sử dụng nó
        if current_browser_controller and current_browser_controller.browser is not None:
            try:
                # Kiểm tra page
                if not current_browser_controller.page or not current_browser_controller._ensure_page():
                    logger.warning("BrowserController hiện tại không có page hoạt động, thử phục hồi...")
                    if not current_browser_controller._ensure_page():
                        logger.error("Không thể phục hồi page, khởi động lại browser...")
                        current_browser_controller.start_browser(headless=False)
                
                # Đảm bảo agent sử dụng BrowserController hiện tại
                if agent is None or agent.browser != current_browser_controller:
                    agent = BrowserAutomationAgent(
                        browser_controller=current_browser_controller,
                        browser_type="chromium",
                        headless=False,
                        human_like=True
                    )
                is_browser_running = True
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra BrowserController hiện tại: {str(e)}")
                # Tiếp tục khởi động mới browser nếu cần
        
        # Nếu trình duyệt chưa chạy thì tự động khởi động
        if not is_browser_running or agent is None or not hasattr(agent, 'browser') or not agent.browser:
            logger.info("Browser chưa khởi động, đang khởi động tự động...")
            
            # Khởi tạo agent nếu chưa có
            if agent is None:
                agent = BrowserAutomationAgent(
                    browser_type="chromium",
                    headless=False,
                    human_like=True
                )
            
            # Khởi động browser
            browser_config = {
                "headless": False,
                "user_agent": None,
                "viewport_size": {"width": 1280, "height": 800},
                "locale": "vi-VN"
            }
            
            success = agent.browser.start_browser(**browser_config)
            if not success:
                return jsonify({"success": False, "message": "Không thể khởi động trình duyệt"})
            
            is_browser_running = True
            logger.info("Browser đã được khởi động tự động")
        
        # Kiểm tra xem page còn hoạt động không
        try:
            if not hasattr(agent.browser, 'page') or not agent.browser.page:
                logger.error("Page không tồn tại, cần khởi động lại browser")
                # Thử phục hồi page
                if not agent.browser._ensure_page():
                    # Nếu phục hồi không thành công, khởi động lại browser
                    success = agent.browser.start_browser(headless=False)
                    if not success:
                        return jsonify({"success": False, "message": "Không thể khởi động lại trình duyệt"})
                
                logger.info("Browser đã được khởi động lại")
            else:
                # Kiểm tra xem page có hoạt động không
                url = agent.browser.page.url
                logger.info(f"Page hiện tại: {url}")
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra page: {str(e)}")
            # Thử phục hồi page
            if not agent.browser._ensure_page():
                # Nếu phục hồi không thành công, khởi động lại browser
                success = agent.browser.start_browser(headless=False)
                if not success:
                    return jsonify({"success": False, "message": "Không thể khởi động lại trình duyệt sau lỗi"})
            
            logger.info("Browser đã được khởi động lại sau lỗi")
        
        # Chạy lệnh
        logger.info(f"Chạy lệnh: {command}")
        result = run_command_thread(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện API run-command: {str(e)}")
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"})

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

@app.route('/api/parse-command', methods=['POST'])
def api_parse_command():
    """API nhận lệnh tự nhiên, phân tích và trả về các bước workflow"""
    data = request.json
    command = data.get('command', '')
    if not command:
        return jsonify({'success': False, 'message': 'No command provided'}), 400
    parsed = parse_user_command_ai(command)
    if not parsed:
        return jsonify({'success': False, 'message': 'Không phân tích được lệnh'}), 200
    return jsonify({'success': True, 'parsed': parsed})

@app.route('/api/confirm-workflow', methods=['POST'])
def api_confirm_workflow():
    """API xác nhận và thực thi workflow (có thể sửa, xóa, thêm bước nếu cần)"""
    global is_browser_running
    data = request.json
    steps = data.get('steps', [])
    url = data.get('url', None)
    if not is_browser_running:
        success = initialize_agent()
        if not success:
            return jsonify({'success': False, 'message': 'Không thể khởi động trình duyệt'}), 200
    confirmed_steps = confirm_workflow(steps, get_agent().browser, parsed_url=url)
    if not confirmed_steps:
        return jsonify({'success': False, 'message': 'Workflow bị hủy hoặc không xác nhận'}), 200
    # Thực thi workflow
    try:
        success = get_agent().browser.execute_human_like_workflow(confirmed_steps)
        if success:
            return jsonify({'success': True, 'message': 'Đã thực thi workflow thành công'})
        else:
            return jsonify({'success': False, 'message': 'Lỗi khi thực thi workflow'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi khi thực thi workflow: {str(e)}'})

def run_server(port=None):
    """Run the Flask server"""
    global app
    if port is None:
        port = find_free_port()
    
    # Bật debug mode
    app.run(debug=True, host='0.0.0.0', port=port)

def start_gui():
    """Start the GUI application"""
    # Đã chuyển sang main.py trong thư mục src.gui
    from src.gui.main import main as start_gui_from_main
    start_gui_from_main()

def get_agent():
    global agent
    if agent is None:
        agent = BrowserAutomationAgent(browser_type="chromium", headless=False, human_like=False)
    return agent

if __name__ == '__main__':
    try:
        start_gui()
    except KeyboardInterrupt:
        print("Application terminated by user")
        stop_browser()
    except Exception as e:
        print(f"Error: {str(e)}")
        stop_browser()
