"""
Browser Automation Agent
Browser automation application with workflow recording and replay capabilities
"""

import os
import sys
import traceback
import logging
import time
import locale
from dotenv import load_dotenv
import re
import openai
import json
from bs4 import BeautifulSoup
import hashlib
import random
import asyncio

# Set UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    try:
        # Try to set console to UTF-8 mode
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older Python versions
        pass

from automation import BrowserController, WorkflowManager
from ai.agent import AIAgent
from utils import UserInteraction

# Load environment variables
load_dotenv()

# Sử dụng tiện ích logging với hỗ trợ Unicode
from utils.logging_utils import configure_unicode_logging
configure_unicode_logging("browser_automation.log", logging.INFO)

class BrowserAutomationAgent:
    """
    Ứng dụng chính cho tự động hóa trình duyệt
    Điều phối giữa các module phân tích lệnh, điều khiển trình duyệt và quản lý quy trình
    """
    
    def __init__(self, browser_type="chromium", headless=False, human_like=True, human_profile=None, browser_controller=None):
        """
        Khởi tạo Browser Automation Agent
        
        Args:
            browser_type (str): Loại trình duyệt ("chromium", "firefox", "webkit")
            headless (bool): Chế độ không giao diện
            human_like (bool): Bật/tắt chế độ mô phỏng người dùng thật
            human_profile (dict, optional): Hồ sơ người dùng tùy chỉnh
            browser_controller (BrowserController, optional): Instance BrowserController có sẵn để sử dụng
        """
        # Sử dụng get_logger để đảm bảo xử lý Unicode đúng
        from utils.logging_utils import get_logger
        self.logger = get_logger("BrowserAutomationAgent")
        
        # Các cấu hình cho thao tác giống người thật
        self.human_like = human_like
        # Tùy chọn profile người dùng khác nhau
        self.human_profiles = {
            "elderly": {
                "reading_speed": 120,  # Từ/phút
                "cursor_accuracy": 0.75,  # Độ chính xác khi di chuột
                "decision_speed": 0.6,  # Hệ số tốc độ quyết định
                "age_group": "55+",
                "tech_savvy": 0.5,  # Mức độ thành thạo công nghệ
            },
            "young": {
                "reading_speed": 300,
                "cursor_accuracy": 0.95,
                "decision_speed": 1.2,
                "age_group": "25-34",
                "tech_savvy": 0.9,
            },
            "casual": {
                "reading_speed": 200,
                "cursor_accuracy": 0.85,
                "decision_speed": 0.9,
                "age_group": "35-44",
                "tech_savvy": 0.7,
            }
        }
        # Sử dụng profile đã chỉ định hoặc lấy profile "casual" mặc định
        selected_profile = human_profile or self.human_profiles.get("casual")
        
        # Khởi tạo các thành phần
        if browser_controller:
            # Sử dụng BrowserController đã được cung cấp
            self.logger.info("Sử dụng BrowserController có sẵn")
            self.browser = browser_controller
            # Cập nhật cấu hình nếu cần
            self.browser.human_like_mode = human_like
            if human_profile:
                self.browser.set_human_profile(selected_profile)
        else:
            # Tạo BrowserController mới
            self.browser = BrowserController(
                browser_type=browser_type,
                human_like_mode=human_like,
                human_profile=selected_profile
            )
            
        self.workflow = WorkflowManager(self.browser)
        self.ui = UserInteraction()
        
        # Cấu hình trình duyệt
        self.headless = headless
        self.browser_type = browser_type
        
        # Tạo thư mục dữ liệu nếu chưa tồn tại
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/downloads", exist_ok=True)
        os.makedirs("data/screenshots", exist_ok=True)
        os.makedirs("data/videos", exist_ok=True)
        
        self.agent = AIAgent(self.browser, debug=True)
    
    def run(self):
        """Run automation agent"""
        self.ui.display_welcome_message()
        
        # Auto-start browser with advanced configuration
        print("Starting browser...")
        browser_config = {
            "headless": self.headless,
            "user_agent": None,  # Can be configured from env
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        
        # Tắt chế độ giả lập người như yêu cầu
        self.human_like = False
        self.browser.human_like_mode = False
        
        if self.browser.start_browser(**browser_config):
            self.logger.info("Browser started successfully")
            print("Browser is open and ready to use!")
            print("Đã tắt chế độ giả lập người để tập trung vào xử lý tương tác trực tiếp!")
        else:
            self.logger.error("Could not start browser")
            print("Could not start browser. Please try again.")
            return
        
        # Display welcome message
        welcome_msg = "Tell me what you'd like to do with the browser. For example: 'Go to Google and search for OpenAI Agents'"
        self.ui.display_assistant_message(welcome_msg)
        
        # Vòng lặp chính của ứng dụng
        try:
            last_page_update = time.time()
            
            while True:
                # Cập nhật PageObserver nếu có
                current_time = time.time()
                if current_time - last_page_update > 1.0:  # Cập nhật mỗi giây
                    self._update_page_observer()
                    last_page_update = current_time
                
                user_input = self.ui.get_user_input("\nWhat would you like to do next? ")
                
                # Check exit command
                if user_input.lower() in ['exit', 'quit']:
                    continue_session = self.ui.ask_yes_no_question("Are you sure you want to end this session?")
                    if continue_session:
                        print("Continuing session...")
                        continue
                    else:
                        print("Ending session...")
                        self._cleanup()
                        break
                
                # Xử lý lệnh đặc biệt
                if user_input.startswith('/'):
                    self._handle_special_command(user_input)
                    continue
                
                # Hiển thị thông báo đang xử lý
                self.ui.display_processing_message()
                
                # Phân tích và thực hiện lệnh
                try:
                    responses = self.command_parser.parse_command(user_input)
                    for response in responses:
                        self.ui.display_assistant_message(response)
                except Exception as e:
                    self.logger.error(f"Lỗi xử lý lệnh: {str(e)}")
                    self.ui.display_error_message(f"Lỗi xử lý lệnh: {str(e)}")
                
                # Hiển thị thông báo hoàn thành
                self.ui.display_completion_message()
                
        except KeyboardInterrupt:
            self.logger.info("Đã phát hiện sự ngắt. Đang kết thúc chương trình...")
            print("\nĐã phát hiện sự ngắt. Đang kết thúc chương trình...")
        except Exception as e:
            self.logger.error(f"Lỗi không mong đợi: {str(e)}")
            print(f"\nLỗi không mong đợi: {str(e)}")
            traceback.print_exc()
        finally:
            # Đảm bảo dọn dẹp tài nguyên
            self._cleanup()
            print("Chương trình đã kết thúc!")
            
    def navigate_to(self, url):
        """Điều hướng đến URL và tự động xử lý popup"""
        if not self.browser:
            self.logger.error("Trình duyệt chưa được khởi động")
            return False
            
        # Điều hướng đến URL
        result = self.browser.navigate_to(url)
        
        if result:
            # Đợi trang tải xong
            time.sleep(2)
            
            # Tự động xử lý popup nếu có
            self._auto_handle_popup()
            
            return True
        
        return False
        
    def _auto_handle_popup(self):
        """Tự động phát hiện và xử lý popup/overlay trên trang"""
        try:
            if not hasattr(self.browser, 'overlay_handler') or not self.browser.overlay_handler:
                return False
                
            # Phát hiện overlay với giới hạn thời gian thực thi
            start_time = time.time()
            overlays = self.browser.overlay_handler.detect_overlays(take_screenshot=False)
            
            # Kiểm tra thời gian thực thi
            detection_time = time.time() - start_time
            if detection_time > 1.0:  # Nếu việc phát hiện mất quá 1 giây
                self.logger.warning(f"Phát hiện overlay mất {detection_time:.2f}s, cần tối ưu")
            
            if not overlays or len(overlays) == 0:
                return False
                
            self.logger.info(f"Phát hiện {len(overlays)} popup/overlay, đang xử lý tự động...")
            
            # Xử lý với timeout để tránh treo
            close_start_time = time.time()
            result = self.browser.overlay_handler.close_overlay(close_all=True, timeout=3000)
            close_time = time.time() - close_start_time
            
            if result:
                self.logger.info(f"Đã xử lý popup/overlay thành công trong {close_time:.2f}s")
                return True
            elif close_time >= 3.0:
                # Nếu mất quá nhiều thời gian, thử phương pháp mạnh
                self.logger.info("Đã hết thời gian, đang thử phương pháp mạnh để xử lý popup/overlay...")
                return self.browser.overlay_handler.remove_all_overlays()
            else:
                # Nếu không thể đóng thông thường, thử xóa mạnh mẽ
                self.logger.info("Đang thử phương pháp mạnh để xử lý popup/overlay...")
                return self.browser.overlay_handler.remove_all_overlays()
        except Exception as e:
            self.logger.warning(f"Lỗi khi tự động xử lý popup: {str(e)}")
            return False
            
    def _update_page_observer(self):
        """Cập nhật PageObserver nếu có"""
        if not hasattr(self.browser, 'ai_element_finder') or not self.browser.ai_element_finder:
            return
            
        try:
            # Kiểm tra thuộc tính page_observer trước khi truy cập
            page_observer = getattr(self.browser.ai_element_finder, 'page_observer', None)
            if not page_observer:
                return
                
            # Kiểm tra phương thức process_page_update tồn tại
            if not hasattr(page_observer, 'process_page_update'):
                return
                
            # Đặt timeout cho xử lý cập nhật để tránh treo
            start_time = time.time()
            
            # Tạo thread riêng để cập nhật với timeout
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def update_with_timeout():
                try:
                    page_observer.process_page_update()
                    result_queue.put(True)
                except Exception as e:
                    self.logger.debug(f"Lỗi khi cập nhật PageObserver: {str(e)}")
                    result_queue.put(False)
            
            # Tạo và chạy thread
            update_thread = threading.Thread(target=update_with_timeout)
            update_thread.daemon = True  # Đảm bảo thread kết thúc khi chương trình chính kết thúc
            update_thread.start()
            
            # Chờ hoàn thành hoặc hết thời gian
            try:
                success = result_queue.get(timeout=1.0)  # Timeout 1 giây
                if success:
                    # Tự động xử lý popup sau khi cập nhật trang
                    self._auto_handle_popup()
            except queue.Empty:
                self.logger.warning("Cập nhật PageObserver mất quá nhiều thời gian, đã hủy bỏ")
                
        except Exception as e:
            self.logger.debug(f"Lỗi khi cập nhật PageObserver: {str(e)}")

    
    def _cleanup(self):
        """Đóng trình duyệt và dọn dẹp tài nguyên"""
        try:
            # Chỉ đóng browser nếu không phải instance được truyền từ bên ngoài
            from automation.browser_controller import BrowserController
            current_instance = BrowserController.get_current_instance()
            
            # Nếu không phải instance hiện tại, có thể đóng an toàn
            if self.browser and self.browser != current_instance:
                self.browser.close_browser()
                self.logger.info("Đã đóng trình duyệt")
            
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi dọn dẹp tài nguyên: {str(e)}")
            return False
    
    def _handle_special_command(self, command):
        """
        Xử lý các lệnh đặc biệt bắt đầu bằng '/'
        
        Args:
            command (str): Lệnh đặc biệt
        """
        cmd = command.lower().strip()
        
        if cmd == '/help' or cmd == '/trợgiúp':
            self._show_help()
        elif cmd == '/screenshot' or cmd == '/chụp':
            self._take_screenshot()
        elif cmd == '/newtab' or cmd == '/tab mới':
            self._open_new_tab()
        elif cmd == '/tabs' or cmd == '/danh sách tab':
            self._list_tabs()
        elif cmd == '/closetab' or cmd == '/đóng tab':
            self._close_current_tab()
        elif cmd.startswith('/switchtab ') or cmd.startswith('/chuyểntab '):
            parts = cmd.split(' ', 1)
            if len(parts) > 1:
                self._switch_tab(parts[1])
        elif cmd == '/clearcookies' or cmd == '/xóa cookies':
            self._clear_cookies()
        elif cmd == '/human' or cmd == '/người thật':
            self._toggle_human_mode()
        elif cmd.startswith('/profile '):
            parts = cmd.split(' ', 1)
            if len(parts) > 1:
                self._set_human_profile(parts[1])
        else:
            print(f"Lệnh không được hỗ trợ: {command}")
            print("Nhập '/help' hoặc '/trợgiúp' để xem danh sách lệnh.")
    
    def _show_help(self):
        """Hiển thị trợ giúp về các lệnh đặc biệt"""
        help_text = """
        === DANH SÁCH LỆNH ĐẶC BIỆT ===
        /help, /trợgiúp - Hiển thị trợ giúp này
        /screenshot, /chụp - Chụp ảnh màn hình
        /newtab, /tabmới - Mở tab mới
        /tabs, /danhsáchtab - Liệt kê các tab đang mở
        /closetab, /đóngtab - Đóng tab hiện tại
        /switchtab <tên>, /chuyểntab <tên> - Chuyển đến tab có tên cụ thể
        /clearcookies, /xóacookies - Xóa cookies
        /human, /người thật - Bật/tắt chế độ mô phỏng người dùng thật
        /profile <tên> - Thiết lập profile người dùng (elderly, young, casual)
        
        === CÁCH SỬ DỤNG ===
        Để điều khiển trình duyệt, chỉ cần nhập yêu cầu bằng ngôn ngữ tự nhiên.
        Ví dụ: "Mở Google và tìm kiếm tin tức về AI"
        
        === CHẾ ĐỘ MÔ PHỎNG NGƯỜI DÙNG THẬT ===
        Khi bật chế độ này, hệ thống sẽ thao tác giống người thật:
        - Di chuyển chuột theo đường cong tự nhiên
        - Tốc độ gõ phím và lỗi đánh máy như người thật
        - Cuộn trang có dừng lại để "đọc"
        - Thời gian phản ứng và ngập ngừng tự nhiên
        
        Các profile người dùng:
        - elderly: Người lớn tuổi, ít thành thạo công nghệ
        - young: Người dùng trẻ, thành thạo công nghệ 
        - casual: Người dùng thông thường (mặc định)
        """
        print(help_text)
    
    def _take_screenshot(self):
        """Chụp ảnh màn hình hiện tại"""
        screenshot_path = self.browser.take_screenshot(full_page=True)
        if screenshot_path:
            print(f"Đã chụp ảnh màn hình thành công: {screenshot_path}")
        else:
            print("Không thể chụp ảnh màn hình")
    
    def _open_new_tab(self):
        """Mở tab mới"""
        if self.browser.new_tab():
            print(f"Đã mở tab mới: {self.browser.active_page_name}")
        else:
            print("Không thể mở tab mới")
    
    def _list_tabs(self):
        """Liệt kê các tab đang mở"""
        if hasattr(self.browser, 'pages') and self.browser.pages:
            print("=== DANH SÁCH TAB ===")
            for i, (name, _) in enumerate(self.browser.pages.items(), 1):
                active = " (đang hoạt động)" if name == self.browser.active_page_name else ""
                print(f"{i}. {name}{active}")
        else:
            print("Không có tab nào đang mở")
    
    def _close_current_tab(self):
        """Đóng tab hiện tại"""
        current_tab = self.browser.active_page_name
        if self.browser.close_tab():
            print(f"Đã đóng tab: {current_tab}")
        else:
            print("Không thể đóng tab hiện tại")
    
    def _switch_tab(self, tab_name):
        """Chuyển đến tab có tên cụ thể"""
        if self.browser.switch_tab(tab_name):
            print(f"Đã chuyển đến tab: {tab_name}")
        else:
            print(f"Không tìm thấy tab: {tab_name}")
    
    def _clear_cookies(self):
        """Xóa cookies"""
        try:
            if hasattr(self.browser, 'context') and self.browser.context:
                self.browser.context.clear_cookies()
                print("Đã xóa tất cả cookies")
            else:
                print("Không thể xóa cookies")
        except Exception as e:
            print(f"Lỗi khi xóa cookies: {str(e)}")
            
    def _toggle_human_mode(self):
        """Bật/tắt chế độ mô phỏng người dùng thật"""
        try:
            if hasattr(self.browser, 'toggle_human_like_mode'):
                new_state = self.browser.toggle_human_like_mode()
                self.human_like = new_state
                print(f"Chế độ mô phỏng người dùng thật: {'BẬT' if new_state else 'TẮT'}")
            else:
                print("Không hỗ trợ chế độ mô phỏng người dùng thật")
        except Exception as e:
            print(f"Lỗi khi chuyển đổi chế độ mô phỏng người dùng thật: {str(e)}")
    
    def _set_human_profile(self, profile_name):
        """Thiết lập profile người dùng"""
        try:
            if profile_name.lower() not in self.human_profiles:
                print(f"Profile không tồn tại: {profile_name}")
                print(f"Các profile có sẵn: {', '.join(self.human_profiles.keys())}")
                return
                
            if hasattr(self.browser, 'set_human_profile'):
                profile = self.human_profiles[profile_name.lower()]
                success = self.browser.set_human_profile(profile)
                if success:
                    print(f"Đã thiết lập profile người dùng: {profile_name}")
                    # Đảm bảo chế độ mô phỏng người dùng thật được bật
                    if not self.human_like:
                        self.browser.toggle_human_like_mode(True)
                        self.human_like = True
                        print("Đã tự động bật chế độ mô phỏng người dùng thật")
                else:
                    print(f"Không thể thiết lập profile người dùng: {profile_name}")
            else:
                print("Không hỗ trợ chế độ mô phỏng người dùng thật")
        except Exception as e:
            print(f"Lỗi khi thiết lập profile người dùng: {str(e)}")

    def run_ai_task(self, task, context=None):
        """
        Nhận task tự nhiên, agent tự động phân tích, chia nhỏ, thực thi workflow, highlight, log chi tiết.
        """
        results = self.agent.run_task(task, context)
        print("Kết quả từng bước:")
        for r in results:
            print(r)
        return results

ai_cache = {}

def should_send_html(goal):
    return goal in ["login", "register", "submit_form", "complex_action"]

def parse_user_command_ai(command, lang="vi", html_snippet=None, goal=None):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # Cache key
    html_short = ""
    cache_key = None
    if should_send_html(goal) and html_snippet:
        try:
            soup = BeautifulSoup(html_snippet, "html.parser")
            # Loại bỏ script, style, comment
            for tag in soup(["script", "style"]):
                tag.decompose()
            for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.comment))):
                comment.extract()
            # Chỉ lấy các thẻ quan trọng, bỏ hidden
            important_tags = []
            for tag in soup.find_all(["form", "input", "button", "a", "div"]):
                if tag.name == "input" and tag.get("type") == "hidden":
                    continue
                if tag.name in ["div", "a"] and not (tag.get("id") or tag.get("class") or tag.get("name") or tag.get("placeholder") or tag.text.strip()):
                    continue
                if tag.name in ["form", "input", "button"] and not (tag.get("id") or tag.get("name") or tag.get("placeholder") or tag.text.strip()):
                    continue
                important_tags.append(str(tag))
            if important_tags:
                html_short = "\n".join(important_tags)
            else:
                html_short = str(soup.body) if soup.body else html_snippet
            if len(html_short) > 4000:
                html_short = html_short[:2000] + "\n...\n" + html_short[-2000:]
        except Exception:
            html_short = html_snippet[:2000] + "\n...\n" + html_snippet[-2000:] if html_snippet else ""
        cache_key = hashlib.md5((command + html_short).encode()).hexdigest()
    else:
        cache_key = hashlib.md5(command.encode()).hexdigest()
    if cache_key in ai_cache:
        return ai_cache[cache_key]
    prompt = f"""
Bạn là một trợ lý tự động hóa trình duyệt web. Hãy phân tích lệnh người dùng dưới đây và trả về một JSON với các trường:
- url: URL của trang web cần thao tác (luôn ở dạng đầy đủ, bắt đầu bằng https:// hoặc http://)
- goal: mục tiêu chính (ví dụ: login, search, send_message, ...)
- credentials: thông tin đăng nhập hoặc dữ liệu cần thiết (nếu có)
- steps: (nếu có) danh sách tối đa 5 bước thao tác chi tiết (mỗi bước là một dict với action, selector, value, ...)
Chỉ sinh step dựa trên selector, id, name, placeholder, text hiển thị trong HTML (nếu có). Nếu lệnh không rõ ràng, hãy hỏi lại người dùng để làm rõ ý định.
Lệnh người dùng: \"{command}\"\n"""
    if should_send_html(goal) and html_short:
        prompt += f"\nDưới đây là phần HTML rút gọn của trang (chỉ gồm các thẻ quan trọng, có thể bị cắt bớt):\n{html_short}\n"
    prompt += "\nTrả về JSON duy nhất, không giải thích gì thêm."
    # Giảm max_tokens cho lệnh đơn giản
    max_tokens = 250 if not should_send_html(goal) else 400
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_str = content[json_start:json_end]
            parsed = json.loads(json_str)
            url = parsed.get("url")
            if url and not url.startswith("http"):
                url = "https://" + url
                parsed["url"] = url
            ai_cache[cache_key] = parsed
            return parsed
        except Exception:
            print("AI trả về không đúng định dạng JSON. Nội dung trả về:", content)
            return None
    except Exception as e:
        print("Lỗi khi gọi OpenAI API:", e)
        return None

def print_workflow_steps(steps):
    print("\nCác bước AI sẽ thực hiện:")
    for idx, step in enumerate(steps, 1):
        action = step.get('action', '')
        if action == 'type':
            print(f"{idx}. Nhập vào ô {step.get('selector', '')}: '{step.get('value', '')}'")
        elif action == 'click':
            print(f"{idx}. Click vào '{step.get('selector', '') or step.get('description', '')}'")
        elif action == 'find_and_click':
            print(f"{idx}. Tìm và click vào '{step.get('text', '') or step.get('description', '')}'")
        elif action == 'scroll':
            print(f"{idx}. Cuộn trang ({step.get('direction', 'down')})")
        elif action == 'wait':
            print(f"{idx}. Đợi {step.get('time', 1.0)} giây")
        elif action == 'view':
            print(f"{idx}. Xem trang {step.get('time', 2.0)} giây")
        else:
            print(f"{idx}. {action} | {step}")
    print()

def guardrail_agent_check(steps):
    """
    Guardrail kiểm tra các bước workflow, cảnh báo nếu có thao tác nguy hiểm.
    Trả về (is_safe, list_canh_bao)
    """
    nguy_hiem = ["delete", "remove", "transfer", "submit", "send_money", "close_account", "shutdown", "format", "drop", "reset"]
    canh_bao = []
    for idx, step in enumerate(steps, 1):
        action = step.get('action', '').lower()
        if any(kw in action for kw in nguy_hiem):
            canh_bao.append(f"Bước {idx}: {action.upper()} có thể là thao tác nguy hiểm!")
    return (len(canh_bao) == 0, canh_bao)

def confirm_workflow(steps, browser_controller=None, parsed_url=None):
    # Guardrail kiểm tra thao tác nguy hiểm
    is_safe, canh_bao = guardrail_agent_check(steps)
    if not is_safe:
        print("\n⚠️  CẢNH BÁO: Phát hiện thao tác nguy hiểm trong workflow!")
        for cb in canh_bao:
            print("   -", cb)
        xac_nhan = input("Bạn có chắc chắn muốn tiếp tục thực hiện các bước này không? (y/n): ").strip().lower()
        if xac_nhan != 'y':
            print("Đã hủy thao tác nguy hiểm. Bạn có thể sửa lại workflow hoặc nhập lại yêu cầu.")
            return None
    # Tự động sửa bước navigate nếu thiếu url
    for step in steps:
        if step.get('action') == 'navigate':
            if not step.get('url') or not str(step.get('url')).strip():
                if parsed_url:
                    step['url'] = parsed_url
                    print(f"[Workflow] Đã tự động điền url cho bước navigate: {parsed_url}")
                else:
                    url_input = input("Bước 'navigate' thiếu url. Vui lòng nhập url cần điều hướng: ").strip()
                    if url_input:
                        step['url'] = url_input
                        print(f"[Workflow] Đã cập nhật url cho bước navigate: {url_input}")
                    else:
                        print("Không có url cho bước navigate. Hủy workflow.")
                        return None
    print_workflow_steps(steps)
    action_suggestions = ['type', 'click', 'find_and_click', 'scroll', 'wait', 'view']
    while True:
        user_input = input("Bạn có muốn thực hiện các bước này không? (y = đồng ý / n = nhập lại yêu cầu / s = sửa từng bước / a = thêm bước / d = xóa bước / m = di chuyển bước): ").strip().lower()
        if user_input == 'y':
            return steps
        elif user_input == 'n':
            print("Bạn hãy mô tả lại yêu cầu hoặc mục tiêu mới:")
            return None
        elif user_input == 's':
            print("Bạn có thể sửa từng bước. Nhập số thứ tự bước muốn sửa (hoặc 0 để quay lại):")
            print_workflow_steps(steps)
            try:
                idx = int(input("Số thứ tự bước muốn sửa: "))
                if idx == 0:
                    continue
                if 1 <= idx <= len(steps):
                    step = steps[idx-1]
                    print(f"\nBước hiện tại: {step}")
                    print(f"Gợi ý action: {', '.join(action_suggestions)}")
                    current_action = step.get('action', '')
                    new_action = input(f"Nhập lại action [{current_action}]: ").strip()
                    if new_action:
                        step['action'] = new_action
                    else:
                        new_action = current_action
                    # Gợi ý và sửa các trường theo action
                    if new_action == 'type':
                        current_selector = step.get('selector', '')
                        current_value = step.get('value', '')
                        selector = input(f"Selector [{current_selector}]: ").strip()
                        # Gợi ý selector thông minh nếu để trống và có browser_controller
                        if not selector and browser_controller and step.get('description'):
                            suggested = browser_controller.find_element_by_description(step.get('description'))
                            if suggested:
                                print(f"Gợi ý selector: {suggested}")
                                selector = suggested
                        if selector:
                            step['selector'] = selector
                        value = input(f"Giá trị muốn nhập [{current_value}]: ").strip()
                        if value:
                            step['value'] = value
                    elif new_action == 'click':
                        current_selector = step.get('selector', '')
                        selector = input(f"Selector [{current_selector}]: ").strip()
                        if not selector and browser_controller and step.get('description'):
                            suggested = browser_controller.find_element_by_description(step.get('description'))
                            if suggested:
                                print(f"Gợi ý selector: {suggested}")
                                selector = suggested
                        if selector:
                            step['selector'] = selector
                    elif new_action == 'find_and_click':
                        current_text = step.get('text', '')
                        text = input(f"Text mô tả [{current_text}]: ").strip()
                        if text:
                            step['text'] = text
                    elif new_action == 'scroll':
                        current_direction = step.get('direction', 'down')
                        direction = input(f"Hướng cuộn (down/up) [{current_direction}]: ").strip()
                        if direction:
                            step['direction'] = direction
                    elif new_action == 'wait':
                        current_time = step.get('time', 1.0)
                        time_val = input(f"Thời gian đợi (giây) [{current_time}]: ").strip()
                        if time_val:
                            try:
                                step['time'] = float(time_val)
                            except:
                                print("Giá trị không hợp lệ, giữ nguyên.")
                    elif new_action == 'view':
                        current_time = step.get('time', 2.0)
                        time_val = input(f"Thời gian xem trang (giây) [{current_time}]: ").strip()
                        if time_val:
                            try:
                                step['time'] = float(time_val)
                            except:
                                print("Giá trị không hợp lệ, giữ nguyên.")
                    print("Đã cập nhật bước.")
                else:
                    print("Số thứ tự không hợp lệ.")
            except Exception as e:
                print(f"Lỗi: {e}")
        elif user_input == 'a':
            print("Thêm bước mới vào workflow.")
            action = input(f"Action ({', '.join(action_suggestions)}): ").strip()
            step = {'action': action}
            if action == 'type':
                selector = input("Selector: ").strip()
                value = input("Giá trị muốn nhập: ").strip()
                description = input("Mô tả (nếu có): ").strip()
                if not selector and browser_controller and description:
                    suggested = browser_controller.find_element_by_description(description)
                    if suggested:
                        print(f"Gợi ý selector: {suggested}")
                        selector = suggested
                step['selector'] = selector
                step['value'] = value
                if description:
                    step['description'] = description
            elif action == 'click':
                selector = input("Selector: ").strip()
                description = input("Mô tả (nếu có): ").strip()
                if not selector and browser_controller and description:
                    suggested = browser_controller.find_element_by_description(description)
                    if suggested:
                        print(f"Gợi ý selector: {suggested}")
                        selector = suggested
                step['selector'] = selector
                if description:
                    step['description'] = description
            elif action == 'find_and_click':
                text = input("Text mô tả: ").strip()
                step['text'] = text
            elif action == 'scroll':
                direction = input("Hướng cuộn (down/up): ").strip()
                step['direction'] = direction
            elif action == 'wait':
                time_val = input("Thời gian đợi (giây): ").strip()
                try:
                    step['time'] = float(time_val)
                except:
                    pass
            elif action == 'view':
                time_val = input("Thời gian xem trang (giây): ").strip()
                try:
                    step['time'] = float(time_val)
                except:
                    pass
            steps.append(step)
            print("Đã thêm bước mới.")
        elif user_input == 'd':
            print_workflow_steps(steps)
            idx = int(input("Nhập số thứ tự bước muốn xóa: "))
            if 1 <= idx <= len(steps):
                steps.pop(idx-1)
                print("Đã xóa bước.")
            else:
                print("Số thứ tự không hợp lệ.")
        elif user_input == 'm':
            print_workflow_steps(steps)
            idx = int(input("Nhập số thứ tự bước muốn di chuyển: "))
            if 1 <= idx <= len(steps):
                new_idx = int(input(f"Chuyển đến vị trí (1-{len(steps)}): "))
                if 1 <= new_idx <= len(steps):
                    step = steps.pop(idx-1)
                    steps.insert(new_idx-1, step)
                    print("Đã di chuyển bước.")
                else:
                    print("Vị trí không hợp lệ.")
            else:
                print("Số thứ tự không hợp lệ.")
        else:
            print("Vui lòng nhập y, n, s, a, d hoặc m.")

# --- TÍCH HỢP OPENAI AGENTS SDK VÀO LUỒNG CHÍNH ---
try:
    from agents import Agent, Runner
    import asyncio
    # Tạo agent chuyên phân tích lệnh tự động hóa
    automation_agent = Agent(
        name="AutomationCommandAgent",
        instructions=(
            "Bạn là trợ lý tự động hóa trình duyệt web. Phân tích lệnh người dùng và trả về JSON đúng chuẩn, gồm url, goal, credentials, steps. "
            "Mỗi step trong steps là một dict với các trường: action, selector (hoặc description), value (nếu cần). "
            "Chỉ sử dụng các action sau: navigate, click, type, wait, scroll, view, find_and_click, double_click, right_click, hover, drag_and_drop, check, uncheck, select, extract_text, get_attribute, focus, blur, file_upload, contenteditable, custom_input. "
            "Nếu dự đoán selector nhưng không chắc chắn, hãy dùng mô tả rõ ràng (description) hoặc text button, không tự tạo selector giả định. Nếu không xác định được selector thực tế trên trang, hãy bỏ qua bước đó hoặc hỏi lại, không tạo selector giả định. "
            "Với lệnh đăng nhập, luôn xác định selector trường username, password và nút đăng nhập rõ ràng nhất có thể dựa vào id, name, placeholder, label, text button. Nếu không xác định được selector, hãy hỏi lại người dùng. "
            "Luôn trả về đầy đủ tất cả các bước thao tác (navigate, click, type, submit, ...) trong một lần, không hỏi lại từng bước. Nếu thiếu selector hoặc không chắc chắn, hãy tự phân tích HTML và đoán selector hợp lý nhất, không hỏi lại người dùng. Chỉ hỏi lại nếu thực sự không thể xác định được bất kỳ trường selector nào." 
            "Không tạo action lạ hoặc thừa. Luôn trả về đúng định dạng JSON chuẩn."
        )
    )
    async def analyze_command_with_agent(command):
        result = await Runner.run(automation_agent, command)
        # Kết quả agent trả về là chuỗi, cố gắng parse JSON
        import json
        try:
            json_start = result.final_output.find('{')
            json_end = result.final_output.rfind('}') + 1
            json_str = result.final_output[json_start:json_end]
            parsed = json.loads(json_str)
            return parsed
        except Exception:
            print("Agent trả về không đúng định dạng JSON. Nội dung:", result.final_output)
            return None
except ImportError:
    automation_agent = None
    analyze_command_with_agent = None
    print("[OpenAI Agents SDK] Chưa cài đặt hoặc không tìm thấy openai-agents. Hãy cài bằng: pip install openai-agents")

def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Nếu đã có event loop đang chạy (Jupyter, VSCode, ...)
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)

def main():
    """Main entry point of the application"""
    try:
        print("=== Starting Browser Automation Agent (AI-powered) ===")
        
        # Read configuration from environment variables
        browser_type = os.getenv("BROWSER_TYPE", "chromium")
        headless = os.getenv("HEADLESS", "False").lower() == "true"
        human_like = False  # Tắt chế độ mô phỏng người theo yêu cầu
        human_profile_name = os.getenv("HUMAN_PROFILE", "casual")
        
        # Initialize and run agent
        agent = BrowserAutomationAgent(
            browser_type=browser_type, 
            headless=headless,
            human_like=human_like,
            human_profile=None
        )
        agent.ui.display_welcome_message()
        browser_config = {
            "headless": headless,
            "user_agent": None,
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        if agent.browser.start_browser(**browser_config):
            agent.logger.info("Browser started successfully")
            print("Browser is open and ready to use!")
            print("Đã tắt chế độ giả lập người để tập trung vào xử lý tương tác trực tiếp!")
        else:
            agent.logger.error("Could not start browser")
            print("Could not start browser. Please try again.")
            exit(1)
        while True:
            command = agent.ui.get_user_input("\nBạn muốn làm gì tiếp? ").strip()
            if command.lower() in ['exit', 'quit', 'q']:
                print("Kết thúc chương trình!")
                break
            agent.ui.display_processing_message()
            # --- SỬ DỤNG AGENT PHÂN TÍCH LỆNH ---
            parsed = None
            if analyze_command_with_agent:
                try:
                    parsed = run_async(analyze_command_with_agent(command))
                except Exception as e:
                    print("Lỗi khi gọi agent phân tích lệnh:", e)
            else:
                parsed = parse_user_command_ai(command)
            if not parsed:
                agent.ui.display_error_message("Tôi chưa hiểu yêu cầu. Hãy nhập lệnh rõ ràng hơn!")
                continue
            url = parsed.get("url")
            goal = parsed.get("goal")
            credentials = parsed.get("credentials")
            steps = parsed.get("steps")
            encryption_key = None
            
            # Bước 1: Navigate tới trang
            print(f"Đang mở trang {url}...")
            success = agent.browser.navigate_to(url)
            
            if success:
                print(f"Đã mở trang {url} thành công, đang phân tích trang...")
                # Cho phép 2 giây để trang tải hoàn tất
                time.sleep(2)
            else:
                agent.ui.display_error_message(f"Không thể mở trang {url}")
                continue
            
            # Bước 2: Xử lý workflow
            if steps:
                # Hiển thị thông tin các bước sẽ thực hiện
                print("\nCác bước AI sẽ thực hiện:")
                for idx, step in enumerate(steps, 1):
                    action = step.get('action', '')
                    selector = step.get('selector', '')
                    description = step.get('description', '') or step.get('text', '')
                    value = step.get('value', '')
                    
                    if action == 'type':
                        print(f"{idx}. Nhập vào {selector or description}: '{value}'")
                    elif action == 'click':
                        print(f"{idx}. Click vào {selector or description}")
                    elif action == 'find_and_click':
                        print(f"{idx}. Tìm và click vào '{description}'")
                    elif action == 'scroll':
                        print(f"{idx}. Cuộn trang ({step.get('direction', 'down')})")
                    elif action == 'wait':
                        print(f"{idx}. Đợi {step.get('time', 1.0)} giây")
                    elif action == 'view':
                        print(f"{idx}. Xem trang {step.get('time', 2.0)} giây")
                    else:
                        print(f"{idx}. {action} | {step}")
                print()
                
                confirmed_steps = confirm_workflow(steps, agent.browser, parsed_url=url)
                if not confirmed_steps:
                    continue
                    
                # Sử dụng phương thức đã sửa để thực hiện trực tiếp các thao tác
                print("\nĐang thực hiện các bước tương tác với trang...")
                
                try:
                    # Thêm timeout toàn cục
                    start_time = time.time()
                    timeout = 60  # 60 giây cho toàn bộ workflow
                    
                    # Thử phương pháp thứ 1: Sử dụng phương thức đã sửa
                    try:
                        success = agent.browser.execute_human_like_workflow(confirmed_steps, credentials)
                    except Exception as e:
                        print(f"Lỗi khi sử dụng phương thức execute_human_like_workflow: {str(e)}")
                        
                        # Phương pháp thứ 2: Thực hiện từng bước trực tiếp
                        print("\nĐang thử phương pháp thay thế...")
                        success = True
                        
                        for idx, step in enumerate(confirmed_steps):
                            try:
                                print(f"\nThực hiện bước {idx+1}/{len(confirmed_steps)}")
                                action = step.get("action", "").lower()
                                selector = step.get("selector", "")
                                description = step.get("description", "") or step.get("text", "")
                                value = step.get("value", "")
                                
                                if action == "click" and selector:
                                    print(f"Đang click vào {selector}...")
                                    agent.browser.page.click(selector)
                                    print(f"Đã click thành công")
                                elif action == "type" and selector:
                                    print(f"Đang nhập '{value}' vào {selector}...")
                                    agent.browser.page.fill(selector, value)
                                    print(f"Đã nhập thành công")
                                elif action == "find_and_click" and description:
                                    print(f"Đang tìm và click vào '{description}'...")
                                    xpath = f"//button[contains(text(), '{description}')] | //a[contains(text(), '{description}')] | //*[@value='{description}'] | //*[contains(text(), '{description}')]"
                                    agent.browser.page.click(f"xpath={xpath}")
                                    print(f"Đã click thành công")
                                elif action == "wait":
                                    wait_time = float(step.get("time", 1.0))
                                    print(f"Đang đợi {wait_time} giây...")
                                    time.sleep(wait_time)
                                    print(f"Đã đợi xong")
                                elif action == "scroll":
                                    direction = step.get("direction", "down")
                                    distance = step.get("distance", 500)
                                    print(f"Đang cuộn trang {direction}...")
                                    if direction == "down":
                                        agent.browser.page.evaluate(f"window.scrollBy(0, {distance})")
                                    else:
                                        agent.browser.page.evaluate(f"window.scrollBy(0, -{distance})")
                                    print(f"Đã cuộn xong")
                                else:
                                    print(f"Không hỗ trợ hành động {action}, bỏ qua")
                                
                                # Đợi một chút giữa các bước
                                time.sleep(0.5)
                                
                            except Exception as step_error:
                                print(f"Lỗi khi thực hiện bước {idx+1}: {str(step_error)}")
                                success = False
                    
                    if time.time() - start_time > timeout:
                        print("Quá thời gian thực hiện, hủy bỏ các bước còn lại")
                    
                    if not success:
                        agent.ui.display_error_message("Thực hiện workflow không thành công")
                        # Chụp ảnh để debug
                        screenshot_path = agent.browser.take_screenshot()
                        if screenshot_path:
                            print(f"Đã chụp ảnh màn hình lỗi: {screenshot_path}")
                except Exception as e:
                    print(f"Lỗi khi thực hiện workflow: {e}")
                    traceback.print_exc()
                    
            else:
                print("Không có bước nào được xác định để thực hiện")
                
            agent.ui.display_completion_message()
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Terminating program...")
        print("Program terminated safely!")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        print("Program terminated!")

if __name__ == "__main__":
    main()
