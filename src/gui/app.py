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
from src.gui.views.browser_view import browser_bp

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

# Tắt cache cho các template để phát hiện thay đổi ngay lập tức
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Không cache tài nguyên tĩnh

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
        logger.info("Initializing browser automation agent")
        
        # 1. Kiểm tra BrowserController hiện tại
        from src.automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        
        # 2. Kiểm tra xem BrowserController hiện tại có hoạt động không
        if current_browser_controller:
            logger.info("Đã tìm thấy BrowserController hiện tại")
            browser_working = False
            
            # Kiểm tra xem browser của controller còn hoạt động không
            if hasattr(current_browser_controller, 'browser') and current_browser_controller.browser:
                if hasattr(current_browser_controller, 'page') and current_browser_controller.page:
                    try:
                        # Kiểm tra trang có hoạt động không bằng cách lấy URL hiện tại
                        current_url = current_browser_controller.page.url
                        logger.info(f"Trình duyệt hiện tại đang hoạt động (URL: {current_url})")
                        browser_working = True
                    except Exception as e:
                        logger.warning(f"Page hiện tại không hoạt động: {str(e)}")
                        # Thử khởi động lại page nếu browser vẫn hoạt động
                        try:
                            if current_browser_controller.browser:
                                # Tạo context mới nếu cần
                                if not current_browser_controller.context:
                                    logger.info("Tạo context mới")
                                    current_browser_controller.context = current_browser_controller.browser.new_context()
                                
                                # Tạo page mới
                                logger.info("Tạo page mới trong browser hiện tại")
                                current_browser_controller.page = current_browser_controller.context.new_page()
                                current_browser_controller.pages["main"] = current_browser_controller.page
                                browser_working = True
                        except Exception as e2:
                            logger.warning(f"Không thể tạo page mới: {str(e2)}")
            
            # Nếu browser hiện tại hoạt động, sử dụng nó
            if browser_working:
                logger.info("Sử dụng lại browser hiện tại")
                
                # Cập nhật cấu hình nếu cần
                current_browser_controller.human_like_mode = True
                
                # Đảm bảo agent sử dụng BrowserController hiện tại
                if agent is None:
                    logger.info("Tạo agent mới với browser hiện tại")
                    agent = BrowserAutomationAgent(
                        browser_controller=current_browser_controller,
                        browser_type=browser_type,
                        headless=False,
                        human_like=True
                    )
                else:
                    logger.info("Cập nhật agent hiện tại với browser hiện tại")
                    agent.browser = current_browser_controller
                
                is_browser_running = True
                return True
        
        # Nếu chưa có hoặc browser không còn hoạt động, tạo mới
        logger.info("Khởi tạo browser mới")
        if agent is not None and hasattr(agent, 'browser') and agent.browser is not None:
            try:
                logger.info("Đóng browser cũ")
                agent._cleanup()  # Đóng browser cũ nếu có
            except Exception as e:
                logger.warning(f"Không thể đóng browser cũ: {str(e)}")
                
        # Tạo agent mới        
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
        logger.info("Khởi động browser mới")
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
    
    # Kiểm tra và đảm bảo rằng browser đang chạy
    if not is_browser_running or not agent or not hasattr(agent, 'browser'):
        # Cố gắng khởi tạo lại agent nếu chưa chạy
        logger.info("Browser chưa được khởi tạo, đang cố gắng khởi tạo...")
        success = initialize_agent()
        if not success:
            logger.error("Không thể khởi tạo browser")
            return {"success": False, "message": "Browser is not running and could not be started"}
    
    # Kiểm tra đảm bảo browser_controller có sẵn và hoạt động
    if not hasattr(agent, 'browser') or not agent.browser:
        logger.error("Không tìm thấy browser controller")
        return {"success": False, "message": "Browser controller not found"}
    
    # Đảm bảo rằng browser, context và page đã được tạo và đang hoạt động
    browser_controller = agent.browser
    try:
        # Kiểm tra xem browser còn hoạt động không
        if not hasattr(browser_controller, 'browser') or not browser_controller.browser:
            logger.error("Browser không tồn tại hoặc đã bị đóng")
            # Thử khởi động lại
            success = initialize_agent()
            if not success:
                return {"success": False, "message": "Browser không tồn tại và không thể khởi động lại"}
            browser_controller = agent.browser
        
        # Kiểm tra xem page có hoạt động không bằng cách truy cập URL
        try:
            if not hasattr(browser_controller, 'page') or not browser_controller.page:
                logger.warning("Page không tồn tại, đang tạo mới...")
                # Thử tạo page mới nếu có thể
                if hasattr(browser_controller, 'context') and browser_controller.context:
                    browser_controller.page = browser_controller.context.new_page()
                    browser_controller.pages["main"] = browser_controller.page
                else:
                    # Cần khởi động lại toàn bộ browser
                    logger.warning("Context không tồn tại, cần khởi động lại browser")
                    success = browser_controller.start_browser(headless=False)
                    if not success:
                        return {"success": False, "message": "Không thể khởi động lại browser"}
            else:
                # Kiểm tra xem page có hoạt động không
                current_url = browser_controller.page.url
                logger.info(f"Page hiện tại đang hoạt động tại URL: {current_url}")
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra page: {str(e)}")
            # Thử khởi động lại page
            try:
                logger.info("Đang thử tạo page mới...")
                if hasattr(browser_controller, 'context') and browser_controller.context:
                    browser_controller.page = browser_controller.context.new_page()
                    browser_controller.pages["main"] = browser_controller.page
                else:
                    # Cần khởi động lại toàn bộ browser
                    logger.warning("Context không tồn tại, cần khởi động lại browser")
                    success = browser_controller.start_browser(headless=False)
                    if not success:
                        return {"success": False, "message": "Không thể khởi động lại browser"}
            except Exception as e2:
                logger.error(f"Không thể tạo page mới: {str(e2)}")
                return {"success": False, "message": f"Không thể tạo page mới: {str(e2)}"}
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra browser: {str(e)}")
        return {"success": False, "message": f"Lỗi khi kiểm tra browser: {str(e)}"}
    
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
                    elif action == 'wait':
                        step_description += f"Wait for {step.get('time', 1)} seconds"
                    else:
                        step_description += f"{action} {selector or description or value}"
                    
                    process_output.append(step_description)
                    
                    # Execute step
                    try:
                        if action == 'click' and selector:
                            agent.browser.click_element(selector, description=description, timeout=30000)
                        elif action == 'click' and description:
                            agent.browser.click_element_by_description(description, timeout=30000)
                        elif action == 'type' and selector:
                            agent.browser.type_text(selector, value, description=description)
                        elif action == 'type' and description:
                            agent.browser.type_into_element_by_description(description, value)
                        elif action == 'wait':
                            wait_time = float(step.get("time", 1.0))
                            time.sleep(wait_time)
                        elif action == 'scroll':
                            direction = step.get("direction", "down")
                            distance = int(step.get("distance", 500))
                            agent.browser.human_like_scroll(direction=direction, distance=distance)
                        elif action == 'hover' and selector:
                            agent.browser.hover_element(selector, description=description)
                        elif action == 'hover' and description:
                            agent.browser.hover_element_by_description(description)
                        
                        # Added delay between steps for stability
                        time.sleep(0.5)
                        
                    except Exception as e:
                        process_output.append(f"Error executing step: {str(e)}")
                        logger.error(f"Error executing step {idx}: {str(e)}")
                        # Continue with next step after error
            
            process_output.append("Command executed successfully!")
            current_status = "idle"
            return {"success": True, "message": "Command executed successfully"}
            
        except Exception as e:
            logger.error(f"Error parsing command: {str(e)}")
            process_output.append(f"Error parsing command: {str(e)}")
            current_status = "error"
            return {"success": False, "message": f"Error parsing command: {str(e)}"}
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        process_output.append(f"Error: {str(e)}")
        current_status = "error"
        return {"success": False, "message": str(e)}

def run_command_thread(command):
    """Run a command in a separate thread"""
    global agent_thread, current_status, process_output
    
    # If there's already a thread running, don't start a new one
    if agent_thread and agent_thread.is_alive():
        return {"success": False, "message": "A command is already running"}
    
    # Đảm bảo trạng thái ban đầu
    current_status = "running"
    process_output = []
    
    try:
        # Đảm bảo browser controller đã được khởi tạo đúng trước khi bắt đầu
        if not is_browser_running:
            process_output.append("Browser chưa chạy, khởi động tự động...")
            success = initialize_agent()
            if not success:
                process_output.append("Không thể khởi động browser!")
                current_status = "error"
                return {"success": False, "message": "Không thể khởi động browser"}
            process_output.append("Browser đã được khởi động thành công")
            
        # Create and start the thread
        agent_thread = threading.Thread(target=run_command, args=(command,))
        agent_thread.daemon = True
        agent_thread.start()
        
        return {"success": True, "message": "Command started in background"}
    except Exception as e:
        logger.error(f"Error starting command thread: {str(e)}")
        process_output.append(f"Error: {str(e)}")
        current_status = "error"
        return {"success": False, "message": str(e)}

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
    # Thêm tham số timestamp để tránh cache template
    timestamp = int(time.time())
    return render_template('index.html', timestamp=timestamp)

@app.route('/api/reload-template')
def api_reload_template():
    """API endpoint để tải lại template mà không cần tải lại cả trang"""
    template_name = request.args.get('template', 'index.html')
    timestamp = int(time.time())
    html_content = render_template(template_name, timestamp=timestamp)
    return html_content

@app.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint để lấy thông tin trạng thái chung"""
    try:
        # Kiểm tra xem có browser controller hiện tại không
        from src.automation.browser_controller import BrowserController
        current_browser = BrowserController.get_current_instance()
        has_current_browser = current_browser is not None
        
        # Lấy URL hiện tại nếu có browser đang chạy
        current_url = None
        if has_current_browser and hasattr(current_browser, 'page') and current_browser.page:
            try:
                current_url = current_browser.page.url
            except Exception:
                pass
        
        # Trả về thông tin
        return jsonify({
            "success": True,
            "has_current_browser": has_current_browser,
            "is_browser_running": is_browser_running,
            "current_url": current_url,
            "status": current_status
        })
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Lỗi: {str(e)}",
            "has_current_browser": False,
            "is_browser_running": False
        })

@app.route('/api/start-browser', methods=['POST'])
def api_start_browser():
    """API endpoint to start the browser or reuse existing browser"""
    global agent, is_browser_running
    
    try:
        use_existing = request.json.get('use_existing', False)
        browser_type = request.json.get('browser_type', 'chromium')
        headless = False  # Luôn đặt headless=False để hiển thị giao diện
        
        # Kiểm tra BrowserController hiện tại
        from src.automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        
        # Nếu yêu cầu sử dụng browser hiện tại
        if use_existing and current_browser_controller and current_browser_controller.browser is not None:
            logger.info(f"Đang thử kết nối với trình duyệt hiện có")
            try:
                # Kiểm tra xem page có hoạt động không
                current_url = None
                if hasattr(current_browser_controller, 'page') and current_browser_controller.page:
                    try:
                        current_url = current_browser_controller.page.url
                        logger.info(f"Trình duyệt hiện tại hoạt động, URL: {current_url}")
                        
                        # Đảm bảo agent sử dụng BrowserController hiện tại
                        if agent is None:
                            agent = BrowserAutomationAgent(
                                browser_controller=current_browser_controller,
                                browser_type=browser_type,
                                headless=False,
                                human_like=True
                            )
                        else:
                            # Cập nhật agent với browser hiện tại
                            agent.browser = current_browser_controller
                            
                        is_browser_running = True
                        return jsonify({"success": True, "message": "Đã kết nối với trình duyệt hiện có", "current_url": current_url})
                    except Exception as e:
                        logger.warning(f"Page hiện tại không hoạt động: {str(e)}")
                        
                        # Nếu browser còn nhưng page không hoạt động, tạo page mới
                        if current_browser_controller.browser:
                            try:
                                # Đảm bảo context
                                if not current_browser_controller.context:
                                    logger.info("Tạo context mới")
                                    current_browser_controller.context = current_browser_controller.browser.new_context()
                                
                                # Tạo page mới
                                logger.info("Tạo page mới trong browser hiện tại")
                                current_browser_controller.page = current_browser_controller.context.new_page()
                                current_browser_controller.pages["main"] = current_browser_controller.page
                                
                                # Cập nhật agent
                                if agent is None:
                                    agent = BrowserAutomationAgent(
                                        browser_controller=current_browser_controller,
                                        browser_type=browser_type,
                                        headless=False,
                                        human_like=True
                                    )
                                else:
                                    agent.browser = current_browser_controller
                                
                                is_browser_running = True
                                return jsonify({"success": True, "message": "Đã tạo page mới trong trình duyệt hiện có"})
                            except Exception as e2:
                                logger.warning(f"Không thể tạo page mới: {str(e2)}")
                                # Tiếp tục với khởi động mới
            except Exception as e:
                logger.warning(f"Lỗi khi kết nối trình duyệt hiện có: {str(e)}")
                # Tiếp tục khởi động mới
        
        # Khởi động trình duyệt mới nếu không dùng hiện có hoặc hiện có không hoạt động
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
        logger.info("Đang khởi động browser mới...")
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
        from src.automation.browser_controller import BrowserController
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
    
    # Đảm bảo trình duyệt đã được khởi động
    if not is_browser_running:
        logger.info("Browser chưa khởi động, khởi động tự động...")
        success = initialize_agent()
        if not success:
            return jsonify({'success': False, 'message': 'Không thể khởi động trình duyệt'}), 200
    
    # Đảm bảo page đang hoạt động
    try:
        browser_agent = get_agent()
        if not browser_agent.browser._ensure_page():
            logger.error("Page không còn hoạt động, thử khởi động lại browser")
            try:
                # Khởi động lại browser nếu page không hoạt động
                success = browser_agent.browser.start_browser(headless=False)
                if not success:
                    return jsonify({'success': False, 'message': 'Không thể khởi động lại trình duyệt'}), 200
                
                # Nếu có URL, điều hướng đến URL trước khi thực hiện các bước
                if url:
                    browser_agent.navigate_to(url)
                    time.sleep(2)  # Đợi trang tải
            except Exception as e:
                logger.error(f"Lỗi khi khởi động lại browser: {str(e)}")
                return jsonify({'success': False, 'message': f'Lỗi khi khởi động lại browser: {str(e)}'}), 200
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra page: {str(e)}")
        return jsonify({'success': False, 'message': f'Lỗi khi kiểm tra page: {str(e)}'}), 200
    
    # Xác nhận workflow
    confirmed_steps = confirm_workflow(steps, get_agent().browser, parsed_url=url)
    if not confirmed_steps:
        return jsonify({'success': False, 'message': 'Workflow bị hủy hoặc không xác nhận'}), 200
    
    # Thực thi workflow
    try:
        # Kiểm tra lại page một lần nữa trước khi thực hiện
        if not get_agent().browser._ensure_page():
            # Thử làm mới trang
            try:
                current_url = get_agent().browser.page.url
                get_agent().browser.page.goto(current_url, wait_until="networkidle")
            except Exception as e:
                logger.error(f"Lỗi khi làm mới trang: {str(e)}")
                # Khởi động lại browser nếu cần
                get_agent().browser.start_browser(headless=False)
                if url:
                    get_agent().navigate_to(url)
        
        # Sử dụng phương thức execute_human_like_workflow nếu có
        if hasattr(get_agent().browser, 'execute_human_like_workflow'):
            success = get_agent().browser.execute_human_like_workflow(confirmed_steps)
        else:
            # Fallback đến thực thi thủ công
            logger.info("Không tìm thấy phương thức execute_human_like_workflow, thực thi thủ công...")
            success = True
            for step in confirmed_steps:
                action = step.get('action', '').lower()
                
                if action == 'click' and 'selector' in step:
                    get_agent().browser.page.click(step['selector'])
                
                elif action == 'type' and 'selector' in step and 'value' in step:
                    get_agent().browser.page.fill(step['selector'], step['value'])
                
                elif action == 'wait':
                    wait_time = float(step.get('time', 1.0))
                    time.sleep(wait_time)
                
                elif action == 'find_and_click':
                    text = step.get('text') or step.get('description', '')
                    get_agent().browser.find_and_click_text(text)
                
                elif action == 'scroll':
                    direction = step.get('direction', 'down')
                    get_agent().browser.scroll_page(direction)
                else:
                    logger.error(f"Hành động không xác định: {action}")
                    success = False
                    break
        
        if success:
            return jsonify({'success': True, 'message': 'Đã thực thi workflow thành công'})
        else:
            return jsonify({'success': False, 'message': 'Lỗi khi thực thi workflow'})
    except Exception as e:
        logger.error(f"Lỗi khi thực thi workflow: {str(e)}")
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
        app.register_blueprint(browser_bp)
        start_gui()
    except KeyboardInterrupt:
        print("Application terminated by user")
        stop_browser()
    except Exception as e:
        print(f"Error: {str(e)}")
        stop_browser()
