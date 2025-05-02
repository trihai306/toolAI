"""
Browser Controller Module
Cung cấp các chức năng để điều khiển trình duyệt web với Playwright
Tích hợp AI để xác định phần tử trong trường hợp không tìm thấy bằng selector
"""

import os
import time
import logging
import traceback
import hashlib
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
# Thêm import cho playwright_stealth
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None
import base64
from cryptography.fernet import Fernet
from src.automation.human_like_utils import HumanLikeInteraction
import random
import re
import yaml
from functools import lru_cache
from src.utils.logging_utils import get_logger
from src.automation.helpers.exceptions import BrowserControllerException, BrowserNotAvailable, ElementNotFound, ActionTimeout, PopupNotClosed
from src.automation.helpers.overlay_handler import OverlayHandler
from src.automation.helpers.element_inspector import ElementInspector

class BrowserController:
    """Quản lý tất cả các thao tác với trình duyệt web"""
    
    # Biến static/class để lưu trữ instance hiện tại
    _current_instance = None
    
    @classmethod
    def get_current_instance(cls):
        """Lấy instance hiện tại hoặc trả về None nếu chưa có"""
        return cls._current_instance
    
    @classmethod
    def set_current_instance(cls, instance):
        """Đặt instance hiện tại"""
        cls._current_instance = instance
    
    @classmethod
    def get_current_browser_url(cls):
        """Lấy URL hiện tại của browser đang chạy (nếu có)"""
        current_instance = cls.get_current_instance()
        if current_instance and hasattr(current_instance, 'page') and current_instance.page:
            try:
                return current_instance.page.url
            except Exception:
                return None
        return None
    
    def __init__(self, screenshots_dir="../data", use_ai_fallback=True, browser_type="chromium", use_stealth=True, debug=False,
                 enable_auto_popup_handler=True, enable_cursor_icon=True, cursor_icon_url=None, cursor_move_delay=0.2, enable_highlight=True,
                 human_like_mode=True, human_profile=None, logger=None, overlay_handler=None, element_inspector=None, human_like_interaction=None, config_path=None, config_dict=None):
        """
        Khởi tạo controller với DI và config động
        """
        # Đọc config động từ YAML nếu có
        config = {}
        if config_path:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            except Exception as e:
                print(f"[Config] Không thể đọc file config: {e}")
        if config_dict:
            config.update(config_dict)
        # Ưu tiên giá trị truyền vào hơn config file
        screenshots_dir = config.get('screenshots_dir', screenshots_dir)
        use_ai_fallback = config.get('use_ai_fallback', use_ai_fallback)
        browser_type = config.get('browser_type', browser_type)
        use_stealth = config.get('use_stealth', use_stealth)
        debug = config.get('debug', debug)
        enable_auto_popup_handler = config.get('enable_auto_popup_handler', enable_auto_popup_handler)
        enable_cursor_icon = config.get('enable_cursor_icon', enable_cursor_icon)
        cursor_icon_url = config.get('cursor_icon_url', cursor_icon_url)
        cursor_move_delay = config.get('cursor_move_delay', cursor_move_delay)
        enable_highlight = config.get('enable_highlight', enable_highlight)
        human_like_mode = config.get('human_like_mode', human_like_mode)
        human_profile = config.get('human_profile', human_profile)
        # Logger chuẩn hóa
        self.logger = logger or get_logger("BrowserController")
        
        # Đặt instance hiện tại là self
        BrowserController.set_current_instance(self)
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.pages = {}  # Lưu trữ nhiều trang với key là tên trang
        self.active_page_name = "main"  # Tên của trang đang hoạt động
        self.screenshots_dir = Path(screenshots_dir)
        self.use_ai_fallback = use_ai_fallback
        self.ai_element_finder = None
        self.browser_type = browser_type
        self.use_stealth = use_stealth
        self.debug = debug
        # Cấu hình nâng cao
        self.enable_auto_popup_handler = enable_auto_popup_handler
        self.enable_cursor_icon = enable_cursor_icon
        self.cursor_icon_url = cursor_icon_url
        self.cursor_move_delay = cursor_move_delay
        self.enable_highlight = enable_highlight
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self.downloads_dir = self.screenshots_dir / "downloads"
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # Khởi tạo các công cụ helper
        self.overlay_handler = overlay_handler or OverlayHandler(self, debug)
        self.element_inspector = element_inspector or ElementInspector(self, debug)
        self.human_like_interaction = human_like_interaction or (HumanLikeInteraction(self, debug) if human_like_mode else None)
        
        # Lưu trữ các selector đã tìm thấy trước đó để tái sử dụng
        self._selector_cache = {}
        
        # Cache selectors từ xpath pattern sang CSS
        self._xpath_to_css_cache = {}
        
        # Cấu hình mô phỏng người dùng thực
        self.human_like_mode = human_like_mode
        self.human_profile = human_profile or {}

    def _close_existing_browser(self):
        """
        Đóng context và browser cũ nếu có
        Trả về True nếu đóng thành công, False nếu không có browser đang chạy
        """
        closed = False
        
        # Kiểm tra và đóng page hiện tại
        if hasattr(self, 'page') and self.page is not None:
            try:
                # Kiểm tra xem page còn hoạt động không trước khi đóng
                url = self.page.url
                self.logger.info(f"Đóng page hiện tại (URL: {url})")
                self.page.close()
                closed = True
            except Exception as e:
                self.logger.warning(f"Không thể đóng page hiện tại: {str(e)}")
            finally:
                self.page = None
        
        # Kiểm tra và đóng context hiện tại
        if hasattr(self, 'context') and self.context is not None:
            try:
                self.logger.info("Đóng context hiện tại")
                self.context.close()
                closed = True
            except Exception as e:
                self.logger.warning(f"Không thể đóng context hiện tại: {str(e)}")
            finally:
                self.context = None
        
        # Kiểm tra và đóng browser hiện tại
        if hasattr(self, 'browser') and self.browser is not None:
            try:
                self.logger.info("Đóng browser hiện tại")
                self.browser.close()
                closed = True
            except Exception as e:
                self.logger.warning(f"Không thể đóng browser hiện tại: {str(e)}")
            finally:
                self.browser = None
        
        # Đóng playwright nếu có
        if hasattr(self, 'playwright') and self.playwright is not None:
            try:
                self.logger.info("Đóng playwright hiện tại")
                self.playwright.stop()
                closed = True
            except Exception as e:
                self.logger.warning(f"Không thể đóng playwright hiện tại: {str(e)}")
            finally:
                self.playwright = None
                
        # Xóa cache và các biến liên quan
        self.pages = {}
        self.active_page_name = "main"
        
        return closed

    def start_browser(self, headless=False, user_agent=None, viewport_size=None, locale=None):
        """
        Khởi động trình duyệt với các tùy chọn nâng cao
        """
        try:
            # Kiểm tra xem browser và page hiện tại còn hoạt động không
            if hasattr(self, 'browser') and self.browser is not None and hasattr(self, 'page') and self.page is not None:
                try:
                    # Thử lấy URL hiện tại để kiểm tra trạng thái
                    current_url = self.page.url
                    self.logger.info(f"Trình duyệt hiện tại đang hoạt động (URL: {current_url}), sẽ sử dụng lại")
                    # Trình duyệt vẫn hoạt động tốt, không cần khởi động lại
                    return True
                except Exception as e:
                    self.logger.warning(f"Trình duyệt hiện tại không hoạt động: {str(e)}, sẽ khởi động lại")
                    # Tiếp tục và khởi động trình duyệt mới nếu hiện tại không hoạt động
            
            # Đóng trình duyệt cũ nếu có
            self._close_existing_browser()
            
            # Đặt self làm instance hiện tại
            BrowserController.set_current_instance(self)
            
            self.playwright = sync_playwright().start()
            
            # Chọn loại trình duyệt
            if self.browser_type == "firefox":
                browser_instance = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_instance = self.playwright.webkit
            else:
                browser_instance = self.playwright.chromium
            
            # Khởi tạo trình duyệt với headless=False để luôn hiển thị giao diện
            self.browser = browser_instance.launch(headless=False)
            
            # Thiết lập context với các tùy chọn
            context_options = {
                "accept_downloads": True,
                "record_video_dir": str(self.screenshots_dir / "videos") if not headless else None
            }
            
            if user_agent:
                context_options["user_agent"] = user_agent
            if viewport_size:
                context_options["viewport"] = viewport_size
            if locale:
                context_options["locale"] = locale
                
            self.context = self.browser.new_context(**context_options)
            
            # Tạo trang mặc định
            self.page = self.context.new_page()
            self.pages["main"] = self.page
            
            # Áp dụng stealth nếu được yêu cầu và có thư viện
            if self.use_stealth and stealth_sync is not None:
                try:
                    stealth_sync(self.page)
                    self.logger.info("Đã kích hoạt playwright-stealth cho page.")
                except Exception as e:
                    self.logger.warning(f"Không thể kích hoạt stealth: {str(e)}")
            elif self.use_stealth:
                self.logger.warning("Thư viện playwright-stealth chưa được cài đặt. Hãy cài đặt bằng: pip install playwright-stealth")
            
            # Thiết lập download handler
            self._setup_dialog_handlers()
            
            # Khởi tạo Enhanced Element Finder nếu được cấu hình
            if self.use_ai_fallback:
                try:
                    from src.ai.enhanced_element_finder import EnhancedElementFinder
                    self.ai_element_finder = EnhancedElementFinder(self, use_page_observer=True, debug=self.debug)
                    if self.debug:
                        self.logger.info("Đã khởi tạo Enhanced Element Finder")
                except Exception as e:
                    self.logger.warning(f"Không thể khởi tạo Enhanced Element Finder: {str(e)}")
                    if self.debug:
                        self.logger.warning(traceback.format_exc())
                    try:
                        from src.ai.ai_element_finder import AIElementFinder
                        self.ai_element_finder = AIElementFinder(self)
                        if self.debug:
                            self.logger.info("Đã khởi tạo AIElementFinder thay thế")
                    except Exception as e2:
                        self.logger.warning(f"Không thể khởi tạo AI Element Finder: {str(e2)}")
                        self.use_ai_fallback = False
                        
            # Khởi tạo Human-like Interaction nếu được cấu hình
            if self.human_like_mode:
                self.human_like_interaction = HumanLikeInteraction(self.page, self.human_profile)
                if self.debug:
                    self.logger.info("Đã khởi tạo Human-like Interaction")
                
            self.logger.info(f"Đã khởi động trình duyệt {self.browser_type} thành công")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi khởi động trình duyệt: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def _handle_download(self, download):
        """Xử lý sự kiện tải xuống từ trình duyệt"""
        try:
            download_path = self.downloads_dir / download.suggested_filename
            download.save_as(download_path)
            self.logger.info(f"Đã tải xuống tệp: {download_path}")
        except Exception as e:
            self.logger.error(f"Lỗi khi tải xuống tệp: {str(e)}")

    def _setup_dialog_handlers(self):
        """Thiết lập xử lý hộp thoại mặc định"""
        try:
            self.page.on("dialog", lambda dialog: dialog.accept())
        except Exception as e:
            self.logger.warning(f"Không thể thiết lập dialog handler: {str(e)}")

    def close_browser(self):
        """Đóng trình duyệt và dọn dẹp cache"""
        try:
            # Dọn dẹp EnhancedElementFinder nếu có
            if hasattr(self, 'ai_element_finder') and self.ai_element_finder:
                if hasattr(self.ai_element_finder, 'cleanup'):
                    try:
                        self.ai_element_finder.cleanup()
                        if self.debug:
                            self.logger.info("Đã dọn dẹp EnhancedElementFinder")
                    except Exception as e:
                        if self.debug:
                            self.logger.warning(f"Lỗi khi dọn dẹp EnhancedElementFinder: {str(e)}")
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.browser = None
            self.context = None
            self.playwright = None
            self.page = None
            self.pages = {}
            # Nếu instance hiện tại là self, đặt thành None
            if BrowserController.get_current_instance() == self:
                BrowserController.set_current_instance(None)
            # Dọn dẹp cache LRU
            try:
                self.find_element_by_description.cache_clear()
                self.logger.info("Đã dọn dẹp cache LRU cho find_element_by_description")
            except Exception as e:
                self.logger.warning(f"Lỗi khi dọn dẹp cache LRU: {e}")
            self.logger.info("Trình duyệt đã được đóng")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi đóng trình duyệt: {str(e)}")
            return False

    def navigate_to(self, url, wait_until="load"):
        """
        Điều hướng trình duyệt đến URL được chỉ định
        
        Args:
            url (str): URL đích
            wait_until (str): Điều kiện để coi trang đã tải xong ('domcontentloaded', 'load', 'networkidle')
        
        Returns:
            bool: True nếu điều hướng thành công, False nếu thất bại
        """
        try:
            # Đảm bảo URL có giao thức
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
                
            # Kiểm tra và đảm bảo page tồn tại và hoạt động
            if not self._ensure_page():
                self.logger.error("Không thể đảm bảo page hoạt động, không thể điều hướng")
                return False
            
            self.logger.info(f"Đang điều hướng đến {url}")
            
            # Thực hiện điều hướng
            if self.human_like_mode and hasattr(self, 'human_like_interaction') and self.human_like_interaction:
                # Sử dụng điều hướng giống người thật nếu có
                self.logger.info("Sử dụng điều hướng giống người thật")
                self.human_like_interaction.type_in_address_bar(url)
            else:
                # Điều hướng thông thường
                response = self.page.goto(url, wait_until=wait_until, timeout=60000)
                if response is None:
                    self.logger.warning(f"Không nhận được response khi điều hướng đến {url}")
                elif not response.ok:
                    self.logger.warning(f"Phản hồi không thành công: {response.status} từ {url}")
            
            # Đợi thêm cho trang tải hoàn tất
            try:
                self.page.wait_for_load_state(wait_until, timeout=30000)
            except Exception as e:
                self.logger.warning(f"Cảnh báo khi chờ load_state: {str(e)}")
            
            # Kiểm tra tự động popup nếu được cấu hình
            if self.enable_auto_popup_handler:
                self._handle_popups_and_overlays()
            
            self.logger.info(f"Đã điều hướng đến {url} thành công")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi điều hướng đến {url}: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
                
            # Nếu page không còn hoạt động, thử khởi tạo lại browser
            try:
                self.logger.info("Đang thử khởi động lại trình duyệt sau lỗi điều hướng")
                if self.start_browser(headless=False):
                    # Điều hướng lại sau khi khởi động lại browser thành công
                    self.logger.info(f"Thử điều hướng lại sau khi khởi động lại browser: {url}")
                    response = self.page.goto(url, wait_until=wait_until, timeout=60000)
                    # Đợi thêm cho trang tải hoàn tất sau khi restart
                    self.page.wait_for_load_state(wait_until, timeout=30000)
                    self.logger.info("Điều hướng thành công sau khi khởi động lại trình duyệt")
                    return True
            except Exception as restart_error:
                self.logger.error(f"Không thể khởi động lại trình duyệt: {str(restart_error)}")
                
            return False

    def _normalize_selector(self, selector, description=None):
        """
        Chuẩn hóa selector để xử lý đúng cả CSS và XPath
        
        Args:
            selector (str): Selector gốc
            description (str, optional): Mô tả phần tử để tìm kiếm nếu selector thất bại
            
        Returns:
            tuple: (selector_normalized, is_xpath)
        """
        if not selector:
            if description and self.use_ai_fallback and self.ai_element_finder:
                selector = self.ai_element_finder.find_element_by_description(description)
                if not selector:
                    return (None, False)
            else:
                return (None, False)
                
        # Check if this is an XPath selector
        is_xpath = selector.startswith('xpath=') or selector.startswith('/') or selector.startswith('.//')
        
        # Convert to the proper format for Playwright
        if is_xpath and not selector.startswith('xpath='):
            selector = f"xpath={selector}"
        
        return (selector, is_xpath)

    def _normalize_selector_contains(self, selector):
        """
        Nếu selector có dạng :contains('text') hoặc :contains("text"), chuyển thành XPath tương đương.
        """
        if not selector or ':contains' not in selector:
            return selector
        # Tìm tag và text
        m = re.match(r"([a-zA-Z0-9]+):contains\(['\"](.+?)['\"]\)", selector)
        if m:
            tag, text = m.group(1), m.group(2)
            xpath = f"xpath=//{tag}[contains(normalize-space(text()), '{text}') or contains(@value, '{text}') or contains(@aria-label, '{text}')]"
            self.logger.info(f"[normalize_selector_contains] Đã chuyển selector '{selector}' thành '{xpath}'")
            return xpath
        return selector

    def click_element(self, selector, description=None, force=False, timeout=30000, auto_handle_popup=True, retry_count=2):
        if not self._ensure_page():
            self.logger.error("Không có page để click!")
            return False
        self.logger.info(f"[DEBUG] Click vào selector: {selector} | desc: {description}")
        selector = self._normalize_selector_contains(selector)
        """
        Click vào phần tử với selector đã cho
        
        Args:
            selector (str): CSS selector hoặc XPath
            description (str, optional): Mô tả phần tử để dùng AI tìm kiếm nếu selector thất bại
            force (bool): Sử dụng force click khi cần (cho các phần tử bị che phủ)
            timeout (int): Thời gian chờ tối đa (ms)
            auto_handle_popup (bool): Tự động xử lý popup sau khi click
            retry_count (int): Số lần thử lại nếu thất bại
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Đảm bảo page đã được khởi tạo
            self._ensure_page()
            
            # Chuẩn hóa selector (thêm prefix nếu cần)
            selector = self._normalize_selector(selector, description)
            if not selector:
                self.logger.error(f"Không thể nhận dạng selector cho phần tử{' ' + description if description else ''}")
                return False
        
            # Đo thời gian thực thi để phát hiện và tối ưu các hoạt động chậm
            start_time = time.time()
            
            # Tạo danh sách các phương pháp click để thử theo thứ tự ưu tiên
            click_methods = []
            
            # Phương pháp 1: Click thông thường
            def normal_click():
                try:
                    # Chờ đến khi phần tử xuất hiện
                    element = self.page.wait_for_selector(selector, timeout=timeout, state="visible")
                    if not element:
                        return False
                    # Nếu dùng human_like_mode, thực hiện human-like click
                    if self.human_like_mode and hasattr(self, 'human_like_interaction') and self.human_like_interaction:
                        return self.human_like_click(selector, description)
                    # Ngược lại thực hiện click thông thường
                    element.click()
                    return True
                except Exception as e:
                    self.logger.debug(f"Normal click failed: {str(e)}")
                    return False
            
            # Phương pháp 2: Click với JavaScript
            def js_click():
                try:
                    element = self.page.query_selector(selector)
                    if not element:
                        return False
                    
                    # Làm nổi bật element nếu debug hoặc highlight được bật
                    if self.debug or self.enable_highlight:
                        self.page.evaluate("""element => {
                            const originalStyle = element.getAttribute('style') || '';
                            element.setAttribute('style', originalStyle + '; border: 2px solid blue; background-color: rgba(0, 0, 255, 0.1);');
                            setTimeout(() => { element.setAttribute('style', originalStyle); }, 500);
                        }""", element)
                    
                    # Click bằng JavaScript
                    self.page.evaluate("element => element.click()", element)
                    return True
                except Exception as e:
                    self.logger.debug(f"JavaScript click failed: {str(e)}")
                    return False
            
            # Phương pháp 3: Force click
            def force_click():
                try:
                    element = self.page.query_selector(selector)
                    if not element:
                        return False
                    
                    # Click với force=True
                    element.click(force=True)
                    return True
                except Exception as e:
                    self.logger.debug(f"Force click failed: {str(e)}")
                    return False
                    
            # Phương pháp 4: Tạo tọa độ và click
            def coordinate_click():
                try:
                    # Lấy vị trí và kích thước của element
                    element = self.page.query_selector(selector)
                    if not element:
                        return False
                    
                    bbox = element.bounding_box()
                    if not bbox:
                        return False
                    
                    # Click vào tọa độ giữa của element
                    x = bbox["x"] + bbox["width"] / 2
                    y = bbox["y"] + bbox["height"] / 2
                    
                    # Cuộn đến vị trí đó nếu cần
                    element.scroll_into_view_if_needed()
                    
                    # Click vào tọa độ
                    self.page.mouse.click(x, y)
                    return True
                except Exception as e:
                    self.logger.debug(f"Coordinate click failed: {str(e)}")
                    return False
            
            # Thiết lập thứ tự các phương pháp dựa trên force flag
            if force:
                click_methods = [force_click, js_click, normal_click, coordinate_click]
            else:
                click_methods = [normal_click, js_click, coordinate_click, force_click]
            
            # Theo dõi xem click thành công hay không
            click_success = False
            
            # Thực hiện click với số lần retry_count
            for attempt in range(retry_count + 1):
                if attempt > 0:
                    self.logger.info(f"Thử lại click lần {attempt}/{retry_count}...")
                    # Chờ một chút trước khi thử lại
                    time.sleep(0.5)
                
                # Thử từng phương pháp click cho đến khi thành công
                for method in click_methods:
                    if method():
                        click_success = True
                        break
                
                if click_success:
                    break
            
            # Tự động xử lý popup sau khi click nếu được yêu cầu
            if click_success and auto_handle_popup:
                # Chờ một chút để trang phản hồi sau khi click
                time.sleep(0.5)
                
                # Thử xử lý popup nếu có
                if hasattr(self, 'overlay_handler') and self.overlay_handler:
                    self.overlay_handler.close_overlay(close_all=True)
            
            # Tính toán thời gian thực thi để ghi log
            execution_time = time.time() - start_time
            if click_success:
                if execution_time > 1.0:  # Nếu thao tác mất hơn 1 giây
                    self.logger.info(f"Click thành công nhưng mất {execution_time:.2f}s, cần tối ưu")
                else:
                    self.logger.debug(f"Click thành công trong {execution_time:.2f}s")
            else:
                self.logger.warning(f"Click thất bại sau {execution_time:.2f}s và {retry_count+1} lần thử")
                
                # Thử dùng AI fallback nếu được cấu hình và có mô tả
                if self.use_ai_fallback and description and hasattr(self, 'ai_element_finder') and self.ai_element_finder:
                    self.logger.info(f"Đang thử dùng AI để tìm phần tử: {description}")
                    return self.ai_element_finder.interact_with_element_by_description(description, "click")
            
            return click_success
            
        except Exception as e:
            self.logger.error(f"Lỗi click element: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
        return False

    def type_text(self, selector, text, description=None, delay=0, auto_handle_popup=True, retry_count=2):
        if not self._ensure_page():
            self.logger.error("Không có page để nhập liệu!")
            return False
        self.logger.info(f"[DEBUG] Nhập '{text}' vào selector: {selector} | desc: {description}")
        selector = self._normalize_selector_contains(selector)
        """
        Nhập văn bản vào phần tử
        
        Args:
            selector (str): CSS selector hoặc XPath của phần tử
            text (str): Văn bản cần nhập
            description (str, optional): Mô tả phần tử để sử dụng AI tìm kiếm nếu selector thất bại
            delay (float): Độ trễ giữa các ký tự (ms) để mô phỏng người dùng thật
            auto_handle_popup (bool): Tự động xử lý popup nếu gặp lỗi
            retry_count (int): Số lần thử lại nếu gặp lỗi
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra cache selector nếu chỉ có description
            if not selector and description:
                cache_key = f"desc:{description}"
                if cache_key in self._selector_cache:
                    selector = self._selector_cache[cache_key]
                    self.logger.info(f"Sử dụng selector từ cache: {selector}")
            
            # Chuẩn hóa selector
            selector, is_xpath = self._normalize_selector(selector, description)
            if not selector:
                self.logger.error(f"Không thể xác định selector cho phần tử: {description}")
                return False
                
            # Lưu vào cache nếu tìm thấy bằng description
            if description and not is_xpath:
                self._selector_cache[f"desc:{description}"] = selector
            
            for attempt in range(retry_count + 1):
                try:
                    # Thử focus vào phần tử trước
                    try:
                        self.page.focus(selector)
                        time.sleep(0.2)
                    except Exception as focus_e:
                        if self.debug:
                            self.logger.debug(f"Không thể focus vào phần tử: {str(focus_e)}")
                    
                    # Thực hiện fill
                    self.page.fill(selector, text, timeout=30000)
                    
                    # Type lại với delay nếu cần
                    if delay > 0:
                        self.page.fill(selector, "")
                        self.page.type(selector, text, delay=delay)
                    
                    self.logger.info(f"Đã nhập văn bản vào phần tử: {selector}")
                    return True
                    
                except Exception as e:
                    self.logger.warning(f"Lỗi khi nhập văn bản vào {selector}: {str(e)}")
                    
                    # Nếu không phải lần thử cuối cùng, thử xử lý popup và thử lại
                    if attempt < retry_count and auto_handle_popup:
                        self.logger.info(f"Đang thử xử lý popup (lần thử {attempt+1}/{retry_count+1})")
                        
                        # Thử các phương pháp xử lý popup
                        try:
                            if hasattr(self, 'overlay_handler') and self.overlay_handler:
                                # Phương pháp 1: Xử lý overlay
                                self.overlay_handler.close_overlay(close_all=True)
                                time.sleep(0.5)
                                
                                # Phương pháp 2: Làm cho phần tử có thể click
                                self.overlay_handler.make_element_clickable(selector)
                                time.sleep(0.5)
                                
                                # Phương pháp 3: Xóa tất cả overlay
                                if attempt == retry_count - 1:  # Lần thử cuối cùng, dùng biện pháp mạnh
                                    self.overlay_handler.remove_all_overlays()
                                    time.sleep(0.5)
                                    
                            # Phương pháp 4: Thử sử dụng JavaScript để nhập văn bản
                            try:
                                self.logger.info(f"Đang thử nhập văn bản bằng JavaScript")
                                
                                # Tạo code JS phù hợp với loại selector
                                js_text = text.replace("'", "\\'").replace('"', '\\"')
                                
                                if is_xpath:
                                    xpath_selector = selector.replace('xpath=', '')
                                    js_code = f"""() => {{
                                        const result = document.evaluate(\"{xpath_selector}\", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                        const element = result.singleNodeValue;
                                        if (element) {{
                                            element.value = \"{js_text}\";
                                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            return true;
                                        }}
                                        return false;
                                    }}"""
                                else:
                                    escaped_selector = selector.replace('"', '\\"')
                                    js_code = f"""() => {{
                                        const element = document.querySelector(\"{escaped_selector}\");
                                        if (element) {{
                                            element.value = \"{js_text}\";
                                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            return true;
                                        }}
                                        return false;
                                    }}"""
                                    
                                result = self.page.evaluate(js_code)
                                if result:
                                    self.logger.info(f"Đã nhập văn bản bằng JavaScript thành công")
                                    return True
                                    
                                time.sleep(0.5)
                            except Exception as js_e:
                                self.logger.warning(f"Lỗi khi nhập văn bản bằng JavaScript: {str(js_e)}")
                        except Exception as handle_e:
                            self.logger.warning(f"Lỗi khi xử lý popup: {str(handle_e)}")
                        
                        continue  # Thử lại
                    
                    # Thử dùng AI hoặc human-like nếu là lần thử cuối cùng và có mô tả
                    if attempt == retry_count:
                        # Thử với human-like mode nếu được bật
                        if self.human_like_mode and self.human_like_interaction and description:
                            self.logger.info(f"Đang thử tìm và nhập văn bản bằng human-like mode: {description}")
                            # Tìm phần tử
                            element = self.human_like_interaction.find_and_click_visible_element(description, highlight=True)
                            if element:
                                time.sleep(0.5)  # Đợi sau khi click
                                # Nhập văn bản
                                return self.human_like_interaction.human_like_type("", text) # Selector rỗng vì đã có focus
                        
                        # Nếu không thành công, thử với AI
                        if self.use_ai_fallback and self.ai_element_finder and description:
                            self.logger.info(f"Đang thử tìm phần tử bằng AI với mô tả: {description}")
                            return self.ai_element_finder.interact_with_element_by_description(description, action="type", value=text)
                
            return False
        except Exception as e:
            self.logger.error(f"Lỗi khi human_like_type: {str(e)}")
            return self.type_text(selector, text, description)
    
    
    def human_like_scroll(self, direction="down", distance=None, speed="medium"):
        """
        Cuộn trang với hành vi giống người thật
        
        Args:
            direction (str): Hướng cuộn ("down", "up", "left", "right")
            distance (int, optional): Khoảng cách cuộn (pixel)
            speed (str): Tốc độ cuộn ("slow", "medium", "fast")
            
        Returns:
            bool: True nếu thành công
        """
        if not self.human_like_mode or not self.human_like_interaction:
            # Fallback về phương thức cuộn thông thường
            try:
                # Thực hiện cuộn đơn giản
                if direction == "down":
                    self.page.mouse.wheel(0, distance or 300)
                elif direction == "up":
                    self.page.mouse.wheel(0, -(distance or 300))
                elif direction == "right":
                    self.page.mouse.wheel(distance or 300, 0)
                elif direction == "left":
                    self.page.mouse.wheel(-(distance or 300), 0)
                return True
            except Exception as e:
                self.logger.error(f"Lỗi khi cuộn trang: {str(e)}")
                return False
                
        try:
            return self.human_like_interaction.human_like_scroll(direction, distance, speed)
        except Exception as e:
            self.logger.error(f"Lỗi khi human_like_scroll: {str(e)}")
            # Fallback về phương thức cuộn thông thường
            try:
                if direction == "down":
                    self.page.mouse.wheel(0, distance or 300)
                elif direction == "up":
                    self.page.mouse.wheel(0, -(distance or 300))
                elif direction == "right":
                    self.page.mouse.wheel(distance or 300, 0)
                elif direction == "left":
                    self.page.mouse.wheel(-(distance or 300), 0)
                return True
            except Exception as e2:
                self.logger.error(f"Lỗi khi cuộn trang fallback: {str(e2)}")
                return False
    
    def human_like_scan_page(self, focus_area=None, read_time=None):
        """
        Mô phỏng người dùng đang xem/quét trang web
        
        Args:
            focus_area (dict, optional): Khu vực tập trung (x, y, width, height)
            read_time (float, optional): Thời gian đọc (giây)
            
        Returns:
            bool: True nếu thành công
        """
        if not self.human_like_mode or not self.human_like_interaction:
            # Fallback: chỉ đợi một khoảng thời gian
            time.sleep(read_time or 2.0)
            return True
            
        try:
            return self.human_like_interaction.scan_page_like_human(focus_area, read_time)
        except Exception as e:
            self.logger.error(f"Lỗi khi human_like_scan_page: {str(e)}")
            time.sleep(read_time or 2.0)
            return False
    
    def execute_human_like_workflow(self, steps, credentials=None):
        """
        Thực hiện một chuỗi thao tác trên trình duyệt 
        """
        import time  # Đảm bảo import time trong phương thức
        
        # Kiểm tra xem page có đang hoạt động không
        if not self._ensure_page():
            self.logger.error("Không thể thực hiện workflow vì page không hoạt động.")
            return False
        
        has_type = any(s.get("action") == "type" for s in steps)
        steps_to_run = list(steps)
        already_filled = set()
        
        # Nếu bước đầu là navigate, chỉ thực hiện navigate trước, đợi trang load xong rồi mới thực hiện các bước còn lại
        if steps_to_run and steps_to_run[0].get("action") == "navigate":
            nav_step = steps_to_run[0]
            url_nav = nav_step.get("url")
            if url_nav:
                print(f"[Workflow] Thực hiện bước navigate đầu tiên tới {url_nav}...")
                self.logger.info(f"[Workflow] Thực hiện bước navigate đầu tiên tới {url_nav}...")
                
                if self.navigate_to(url_nav):
                    time.sleep(1)  # Đợi thêm để đảm bảo trang đã load hoàn toàn
                    print(f"[Workflow] ✓ Đã navigate đến {url_nav} thành công")
                    self.logger.info(f"[Workflow] Đã navigate đến {url_nav} thành công")
                else:
                    print(f"[Workflow] ✗ Không thể navigate đến {url_nav}")
                    self.logger.error(f"[Workflow] Không thể navigate đến {url_nav}")
                    return False
                
                # Loại bỏ bước navigate và tiếp tục với các bước còn lại
                steps_to_run = [s for s in steps_to_run if s.get("action") != "navigate"]
            else:
                print("[Workflow] ✗ Không có url cho bước navigate")
                self.logger.error("[Workflow] Không có url cho bước navigate.")
                return False
                
        # Thực thi từng bước
        try:
            all_success = True
            
            # Hiển thị các bước sẽ thực hiện
            print(f"\n[Workflow] Thực hiện {len(steps_to_run)} bước trên trình duyệt...")
            
            for idx, step in enumerate(steps_to_run):
                # Kiểm tra lại page trước mỗi bước
                if not self._ensure_page():
                    self.logger.error(f"[Workflow] Page không còn hoạt động sau bước {idx}, đang thử phục hồi...")
                    print(f"[Workflow] ⚠️ Page không còn hoạt động sau bước {idx}, đang thử phục hồi...")
                    
                    # Thử phục hồi page
                    recovery_success = self._ensure_page()
                    if not recovery_success:
                        print(f"[Workflow] ✗ Không thể phục hồi page sau bước {idx}, dừng workflow.")
                        self.logger.error(f"[Workflow] Không thể phục hồi page sau bước {idx}, dừng workflow.")
                        return False
                    else:
                        print(f"[Workflow] ✓ Đã phục hồi page thành công, tiếp tục thực hiện workflow.")
                        self.logger.info(f"[Workflow] Đã phục hồi page thành công, tiếp tục thực hiện workflow.")
                        
                        # Nếu page mới thì cần navigate lại
                        if steps_to_run and steps_to_run[0].get("action") == "navigate":
                            nav_url = steps_to_run[0].get("url")
                            if nav_url:
                                print(f"[Workflow] Điều hướng lại đến URL ban đầu: {nav_url}")
                                self.logger.info(f"[Workflow] Điều hướng lại đến URL ban đầu: {nav_url}")
                                if not self.navigate_to(nav_url):
                                    print(f"[Workflow] ✗ Không thể điều hướng lại đến URL ban đầu.")
                                    self.logger.error(f"[Workflow] Không thể điều hướng lại đến URL ban đầu.")
                                    return False
                                time.sleep(1)  # Đợi trang load
                    
                action = step.get("action", "").lower()
                selector = step.get("selector")
                description = step.get("description") or step.get("text")
                
                print(f"[Workflow] Bắt đầu thực thi bước {idx+1}/{len(steps_to_run)}: {action} {selector if selector else description}")
                self.logger.info(f"[Workflow] Đang thực thi bước {idx+1}/{len(steps_to_run)}: {action} | {step}")
                
                # Thêm độ trễ để có thể quan sát rõ ràng
                time.sleep(0.5)
                
                try:
                    # Xử lý các loại action
                    if action == "click":
                        # Nếu chỉ có mô tả, tìm selector trước
                        if not selector and description:
                            selector = self.find_element_by_description(description)
                            if selector:
                                print(f"[Workflow] Đã tìm thấy selector cho '{description}': {selector}")
                            else:
                                print(f"[Workflow] ✗ Không tìm thấy selector cho '{description}'")
                                self.logger.error(f"[Workflow] Không tìm thấy selector cho '{description}'")
                                all_success = False
                                continue
                        
                        if selector:
                            if not self.click_element(selector, description):
                                print(f"[Workflow] ✗ Không thể click vào {selector}")
                                self.logger.error(f"[Workflow] Không thể click vào {selector}")
                                all_success = False
                            else:
                                print(f"[Workflow] ✓ Đã click vào phần tử {selector} thành công")
                                self.logger.info(f"[Workflow] Đã click vào phần tử {selector} thành công")
                        else:
                            print(f"[Workflow] ✗ Bước click không có selector hoặc mô tả")
                            self.logger.error(f"[Workflow] Bước click không có selector hoặc mô tả")
                            all_success = False
                    
                    elif action == "type":
                        value = step.get("value", "")
                        text = step.get("text", value)
                        
                        if not selector and description:
                            selector = self.find_element_by_description(description)
                            if selector:
                                print(f"[Workflow] Đã tìm thấy selector cho '{description}': {selector}")
                            else:
                                print(f"[Workflow] ✗ Không tìm thấy selector cho '{description}'")
                                self.logger.error(f"[Workflow] Không tìm thấy selector cho '{description}'")
                                all_success = False
                                continue
                        
                        if selector:
                            if not self.type_text(selector, text, description):
                                print(f"[Workflow] ✗ Không thể nhập văn bản vào {selector}")
                                self.logger.error(f"[Workflow] Không thể nhập văn bản vào {selector}")
                                all_success = False
                            else:
                                print(f"[Workflow] ✓ Đã nhập văn bản vào phần tử {selector} thành công")
                                self.logger.info(f"[Workflow] Đã nhập văn bản vào phần tử {selector} thành công")
                        else:
                            print(f"[Workflow] ✗ Bước type không có selector hoặc mô tả")
                            self.logger.error(f"[Workflow] Bước type không có selector hoặc mô tả")
                            all_success = False
                    
                    elif action == "find_and_click":
                        text_to_find = step.get("text") or description
                        if text_to_find:
                            try:
                                if hasattr(self, 'ai_element_finder') and self.ai_element_finder:
                                    if self.ai_element_finder.interact_with_element_by_description(text_to_find, "click"):
                                        print(f"[Workflow] ✓ Đã click vào phần tử '{text_to_find}' thành công")
                                        self.logger.info(f"[Workflow] Đã click vào phần tử '{text_to_find}' thành công")
                                    else:
                                        print(f"[Workflow] ✗ Không tìm thấy hoặc không thể click vào '{text_to_find}'")
                                        self.logger.error(f"[Workflow] Không tìm thấy hoặc không thể click vào '{text_to_find}'")
                                        all_success = False
                                else:
                                    print(f"[Workflow] ✗ Không có AI Element Finder để tìm '{text_to_find}'")
                                    self.logger.error(f"[Workflow] Không có AI Element Finder để tìm '{text_to_find}'")
                                    all_success = False
                            except Exception as e:
                                print(f"[Workflow] ✗ Lỗi khi tìm và click '{text_to_find}': {str(e)}")
                                self.logger.error(f"[Workflow] Lỗi khi tìm và click '{text_to_find}': {str(e)}")
                                all_success = False
                        else:
                            print(f"[Workflow] ✗ Bước find_and_click không có text để tìm kiếm")
                            self.logger.error(f"[Workflow] Bước find_and_click không có text để tìm kiếm")
                            all_success = False
                    
                    elif action == "wait":
                        wait_time = float(step.get("time", 1.0))
                        print(f"[Workflow] Đợi {wait_time} giây...")
                        time.sleep(wait_time)
                        print(f"[Workflow] ✓ Đã đợi xong")
                        self.logger.info(f"[Workflow] Đã đợi {wait_time} giây")
                    
                    elif action == "scroll":
                        direction = step.get("direction", "down")
                        distance = step.get("distance")
                        
                        if self.human_like_scroll(direction, distance):
                            print(f"[Workflow] ✓ Đã cuộn {direction} thành công")
                            self.logger.info(f"[Workflow] Đã cuộn {direction} thành công")
                        else:
                            print(f"[Workflow] ✗ Không thể cuộn {direction}")
                            self.logger.error(f"[Workflow] Không thể cuộn {direction}")
                            all_success = False
                            
                    elif action == "view" or action == "scan":
                        view_time = float(step.get("time", 3.0))
                        try:
                            if hasattr(self, 'human_like_interaction') and self.human_like_interaction:
                                self.human_like_interaction.scan_page_like_human(read_time=view_time)
                                print(f"[Workflow] ✓ Đã xem trang trong {view_time} giây")
                                self.logger.info(f"[Workflow] Đã xem trang trong {view_time} giây")
                            else:
                                time.sleep(view_time)
                                print(f"[Workflow] ✓ Đã đợi {view_time} giây")
                                self.logger.info(f"[Workflow] Đã đợi {view_time} giây")
                        except Exception as e:
                            print(f"[Workflow] ✗ Lỗi khi xem trang: {str(e)}")
                            self.logger.error(f"[Workflow] Lỗi khi xem trang: {str(e)}")
                            time.sleep(view_time)  # Fallback
                    else:
                        print(f"[Workflow] ⚠️ Hành động '{action}' không được hỗ trợ, bỏ qua")
                        self.logger.warning(f"[Workflow] Hành động '{action}' không được hỗ trợ, bỏ qua")
                
                except Exception as step_error:
                    self.logger.error(f"[Workflow] Lỗi khi thực hiện bước {idx+1}: {str(step_error)}")
                    print(f"[Workflow] ✗ Lỗi khi thực hiện bước {idx+1}: {str(step_error)}")
                    all_success = False
                    
            # Sau khi thực thi xong, nếu tất cả bước đều thành công, lưu workflow ra file JSON
            if all_success:
                import hashlib, time, json, os
                url = self.get_current_url() or "unknown"
                goal = "auto_workflow"
                url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
                goal_hash = hashlib.md5(goal.encode('utf-8')).hexdigest()
                ts = int(time.time())
                os.makedirs("workflows", exist_ok=True)
                file_path = f"workflows/{url_hash}_{goal_hash}_{ts}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps_to_run, f, ensure_ascii=False, indent=2)
                self.logger.info(f"[Workflow] Đã lưu workflow vào file: {file_path}")
                print(f"[Workflow] ✅ Tất cả bước đã thực hiện thành công và đã lưu workflow")
            else:
                print(f"[Workflow] ❌ Có lỗi xảy ra trong quá trình thực hiện workflow")
                
            return all_success
        except Exception as e:
            print(f"[Workflow] ❌ Lỗi nghiêm trọng: {str(e)}")
            self.logger.error(f"Lỗi khi execute_human_like_workflow: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def get_current_url(self):
        """Lấy URL hiện tại của trang"""
        if not self._ensure_page():
            return None
        try:
            return self.page.url
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy URL hiện tại: {str(e)}")
            return None

    def set_human_profile(self, profile_data):
        """
        Cài đặt profile người dùng cho tính năng mô phỏng
        
        Args:
            profile_data (dict): Dữ liệu profile với các thuộc tính như:
                - reading_speed: Tốc độ đọc (từ/phút)
                - cursor_accuracy: Độ chính xác chuột (0.0-1.0)
                - typing_speed: Tốc độ gõ phím (ký tự/giây)
                - age_group: Nhóm tuổi ("18-24", "25-34", "35-44", "45-54", "55+")
                - tech_savvy: Mức độ thành thạo công nghệ (0.0-1.0)
                
        Returns:
            bool: True nếu thành công
        """
        try:
            if not self.human_like_mode:
                self.human_like_mode = True
                
            if not self.human_like_interaction:
                self.human_like_interaction = HumanLikeInteraction(self, debug=self.debug)
                
            # Cập nhật profile
            if profile_data:
                self.human_like_interaction.user_profile.update(profile_data)
                self.human_like_interaction._adjust_params_based_on_profile()
                
            if self.debug:
                self.logger.info(f"Đã cài đặt human profile: {json.dumps(self.human_like_interaction.user_profile, indent=2)}")
                
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi cài đặt human profile: {str(e)}")
            return False
            
    def get_human_profile(self):
        """Lấy profile người dùng hiện tại"""
        if self.human_like_interaction:
            return self.human_like_interaction.user_profile
        return None
        
    def toggle_human_like_mode(self, enabled=None):
        """
        Bật/tắt chế độ mô phỏng người dùng thật
        
        Args:
            enabled (bool, optional): Bật/tắt. Nếu None sẽ đảo trạng thái hiện tại
            
        Returns:
            bool: Trạng thái sau khi thay đổi
        """
        if enabled is None:
            # Đảo trạng thái hiện tại
            self.human_like_mode = not self.human_like_mode
        else:
            # Đặt trạng thái mới
            self.human_like_mode = bool(enabled)
            
        # Khởi tạo HumanLikeInteraction nếu chưa có và đang bật
        if self.human_like_mode and not self.human_like_interaction:
            self.human_like_interaction = HumanLikeInteraction(self, debug=self.debug)
            
        self.logger.info(f"Chế độ mô phỏng người thật: {'BẬT' if self.human_like_mode else 'TẮT'}")
        return self.human_like_mode

    def auto_handle_page(self, goal, credentials=None, encryption_key=None, use_human_like=True):
        """
        Tự động xử lý trang web theo mục tiêu
        """
        url = self.page.url
        base_path = self._get_script_base_path(url, goal)
        html = self.page.content()
        html_hash = self._get_html_hash(html)

        # --- TÍCH HỢP AGENT PHÂN TÍCH LỆNH ---
        steps = None
        try:
            from main import analyze_command_with_agent
        except ImportError:
            analyze_command_with_agent = None
        if analyze_command_with_agent:
            import asyncio
            try:
                parsed = asyncio.run(analyze_command_with_agent(goal))
                # CHUẨN HÓA: Nếu agent trả về object có trường 'steps', lấy ra danh sách steps
                if isinstance(parsed, dict) and "steps" in parsed:
                    steps = parsed["steps"]
                else:
                    steps = parsed if isinstance(parsed, list) else None
            except Exception as e:
                self.logger.warning(f"Lỗi khi gọi agent phân tích lệnh: {e}")
        # Nếu agent không trả về steps, fallback về AI cũ
        if not steps:
            steps = self._call_ai_to_generate_steps(html, goal, credentials)
        # Nếu bước đầu là navigate, chỉ thực hiện navigate trước, đợi trang load xong rồi mới phân tích lại các bước còn lại
        if steps and steps[0].get("action") == "navigate":
            nav_step = steps[0]
            url_nav = nav_step.get("url")
            if url_nav:
                self.logger.info(f"[auto_handle_page] Thực hiện bước navigate đầu tiên tới {url_nav}...")
                self.navigate_to(url_nav)
                # Đợi trang load xong, lấy lại HTML mới nhất
                html = self.page.content()
                html_hash = self._get_html_hash(html)
                # Gọi lại agent để phân tích các bước tiếp theo dựa trên HTML mới
                self.logger.info("[auto_handle_page] Đã tới trang, phân tích lại HTML để xác định selector cho các bước tiếp theo...")
                new_steps = self._call_ai_to_generate_steps(html, goal, credentials)
                # Nếu agent trả về không phải list bước hợp lệ, fallback dùng các bước cũ (trừ navigate) và tiếp tục thực thi
                if not (new_steps and isinstance(new_steps, list) and any(s.get("action") in supported_actions for s in new_steps)):
                    self.logger.warning("[auto_handle_page] Agent trả về nội dung không hợp lệ sau navigate, sẽ tiếp tục thực thi các bước đã xác định selector.")
                    steps = [s for s in steps if s.get("action") != "navigate"]
                else:
                    steps = new_steps
                # Loại bỏ bước navigate đầu tiên nếu agent trả về lại
                if steps and steps[0].get("action") == "navigate":
                    steps = steps[1:]
            else:
                self.logger.error("[auto_handle_page] Không có url cho bước navigate.")
                return False
        # CHUẨN HÓA ACTION: chuyển 'open_url' thành 'navigate', bỏ qua action lạ
        supported_actions = {
            "navigate", "click", "type", "wait", "scroll", "view", "find_and_click",
            "double_click", "right_click", "hover", "drag_and_drop", "check", "uncheck", "select",
            "extract_text", "get_attribute", "focus", "blur", "file_upload", "contenteditable", "custom_input"
        }
        normalized_steps = []
        for step in steps:
            action = step.get("action")
            # Map các action đặc biệt về chuẩn
            if action == "open_url" or action == "go_to_url" or action == "go_to":
                step["action"] = "navigate"
                if "value" in step and not step.get("url"):
                    step["url"] = step["value"]
                action = "navigate"
            if action == "input_text":
                step["action"] = "type"
                if "value" in step and not step.get("text"):
                    step["text"] = step["value"]
                action = "type"
            # Bỏ qua action không hỗ trợ hoặc không hợp lệ
            if action not in supported_actions:
                self.logger.warning(f"[auto_handle_page] Action không hỗ trợ hoặc không hợp lệ: {action}, bỏ qua bước này.")
                continue
            # Loại bỏ các bước cần mô tả nhưng thiếu description/text/selector
            if action in {"find_and_click", "click", "type"}:
                desc = step.get("description") or step.get("text")
                if not desc and not step.get("selector"):
                    self.logger.warning(f"[auto_handle_page] Bước {action} thiếu mô tả và selector, bỏ qua: {step}")
                    continue
            normalized_steps.append(step)
        steps = normalized_steps
        if not steps:
            self.logger.error("[auto_handle_page] Agent trả về JSON không có bước hợp lệ. Yêu cầu agent trả lại JSON chỉ gồm các action hợp lệ: " + str(list(supported_actions)))
            raise ValueError("Agent trả về JSON không có bước hợp lệ. Hãy yêu cầu agent trả lại JSON đúng chuẩn, chỉ gồm các action hợp lệ: " + str(list(supported_actions)))
        
        # Nếu sử dụng chế độ người thật, đảm bảo bật nó lên
        if use_human_like:
            if not self.human_like_mode:
                self.toggle_human_like_mode(True)
            
            # Mô phỏng người dùng xem trang trước khi thực hiện
            if self.human_like_interaction:
                self.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 5))
        
        # Kiểm tra thay đổi giao diện
        latest_steps = self._load_steps_from_json(base_path)
        last_html_hash = None
        if latest_steps:
            # Lưu hash html của lần trước nếu có
            log_dir = Path("logs")
            for log_file in sorted(log_dir.glob(f"{hashlib.md5((url+goal).encode()).hexdigest()}_*.log"), reverse=True):
                with open(log_file, "r", encoding="utf-8") as f:
                    try:
                        log_data = json.load(f)
                        if log_data.get("html_hash"):
                            last_html_hash = log_data["html_hash"]
                            break
                    except Exception:
                        continue
        
        # Nếu giao diện thay đổi lớn hoặc chưa có step, sinh lại step mới
        if (not latest_steps) or (last_html_hash and last_html_hash != html_hash):
            steps = self._call_ai_to_generate_steps(html, goal, credentials)
            self._save_steps_to_json(base_path, steps)
        else:
            steps = latest_steps
        
        # Mã hóa thông tin nhạy cảm nếu có
        if credentials and encryption_key:
            for k in credentials:
                credentials[k] = self._encrypt(credentials[k], encryption_key)
        
        # Nếu sử dụng chế độ người thật và có nhiều bước, chuyển đổi thành workflow
        if use_human_like and self.human_like_mode and self.human_like_interaction and len(steps) > 1:
            # Chuyển đổi các bước sang định dạng phù hợp với human_like_workflow
            human_steps = []
            for step in steps:
                human_step = {}
                if step.get("action") == "click":
                    human_step["action"] = "click" 
                    human_step["selector"] = step.get("selector")
                    if step.get("description"):
                        human_step["description"] = step.get("description")
                    # Thêm tìm theo text nếu không có selector
                    if not step.get("selector") and step.get("description"):
                        human_step["action"] = "find_and_click"
                        human_step["text"] = step.get("description")
                elif step.get("action") == "type":
                    human_step["action"] = "type"
                    human_step["selector"] = step.get("selector")
                    human_step["value"] = step.get("value", "")
                    if step.get("description"):
                        human_step["description"] = step.get("description")
                # Thêm các hành động khác
                elif step.get("action") == "scroll":
                    human_step["action"] = "scroll"
                    human_step["direction"] = step.get("direction", "down")
                    if step.get("distance"):
                        human_step["distance"] = step.get("distance")
                elif step.get("action") == "wait":
                    human_step["action"] = "wait"
                    human_step["time"] = step.get("time", 1.0)
                elif step.get("action") == "view":
                    human_step["action"] = "view"
                    human_step["time"] = step.get("time", 3.0)
                    
                # Thêm vào danh sách nếu hợp lệ
                if human_step:
                    human_steps.append(human_step)
                    
            # Thêm bước xem trang ban đầu
            if human_steps:
                human_steps.insert(0, {"action": "view", "time": random.uniform(1.5, 3.0)})
                
            # Thực hiện theo workflow
            success = self.execute_human_like_workflow(human_steps, credentials)
            result = [{"step": step, "success": success} for step in steps]
            
            if not success:
                # Nếu thất bại, gửi lại trạng thái mới cho AI để sinh lại step
                html = self.page.content()
                steps = self._call_ai_to_generate_steps(html, goal, credentials)
                self._save_steps_to_json(base_path, steps)
        else:
            # Thực hiện theo cách thông thường
            result = []
            for step in steps:
                success = self._do_step(step, credentials, encryption_key, use_human_like)
                result.append({"step": step, "success": success})
                if not success:
                    # Nếu thất bại, gửi lại trạng thái mới cho AI để sinh lại step
                    html = self.page.content()
                    steps = self._call_ai_to_generate_steps(html, goal, credentials)
                    self._save_steps_to_json(base_path, steps)
                    break
        
        # Lưu log chi tiết
        self._log_execution(url, goal, steps, result, error=None, html=html)
        
        # Sau khi xong, mô phỏng người dùng đọc kết quả
        if use_human_like and self.human_like_mode and self.human_like_interaction:
            self.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 4))
            
        return result

    def _do_step(self, step, credentials=None, encryption_key=None, use_human_like=True):
        """
        Thực hiện một bước trong quy trình tự động
        
        Args:
            step (dict): Thông tin bước thực hiện
            credentials (dict, optional): Thông tin đăng nhập
            encryption_key (str, optional): Khóa mã hóa
            use_human_like (bool): Sử dụng thao tác giống người thật
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Tùy chọn tự động xử lý popup/overlay
            if self.enable_auto_popup_handler and hasattr(self, 'overlay_handler') and self.overlay_handler:
                try:
                    self.overlay_handler.detect_overlays(take_screenshot=False)
                    self.overlay_handler.close_overlay(close_all=True)
                except Exception:
                    pass
                    
            # Lấy thông tin từ step
            action = step.get("action", "")
            selector = step.get("selector")
            description = step.get("description") or step.get("text")
            if not selector and description:
                selector = self.find_element_by_description(description)
                if selector:
                    step["selector"] = selector
            # BỔ SUNG: Hỗ trợ action 'navigate'
            if action == "navigate":
                url = step.get("url")
                if url:
                    self.logger.info(f"[Step] Điều hướng đến: {url}")
                    return self.navigate_to(url)
                else:
                    self.logger.error(f"[Step] Không có url cho bước navigate")
                    return False
            elif action == "double_click":
                if not self.human_like_interaction or not self.human_like_interaction.human_like_double_click(selector, description):
                    self.logger.error(f"[Workflow] Double click thất bại: {selector or description}")
                    return False
            elif action == "right_click":
                if not self.human_like_interaction or not self.human_like_interaction.human_like_right_click(selector, description):
                    self.logger.error(f"[Workflow] Right click thất bại: {selector or description}")
                    return False
            elif action == "hover":
                if not self.human_like_interaction or not self.human_like_interaction.human_like_hover(selector, description):
                    self.logger.error(f"[Workflow] Hover thất bại: {selector or description}")
                    return False
            elif action == "drag_and_drop":
                source = step.get("source_selector")
                target = step.get("target_selector")
                if not self.human_like_interaction or not self.human_like_interaction.human_like_drag_and_drop(source, target, description):
                    self.logger.error(f"[Workflow] Drag and drop thất bại: {source} -> {target}")
                    return False
            elif action == "check":
                if not self.click_element(selector, description):
                    self.logger.error(f"[Workflow] Check thất bại: {selector or description}")
                    return False
            elif action == "uncheck":
                if not self.click_element(selector, description):
                    self.logger.error(f"[Workflow] Uncheck thất bại: {selector or description}")
                    return False
            elif action == "select":
                option = step.get("option")
                if not self.page:
                    self.logger.error(f"[Workflow] Không có page để select")
                    return False
                try:
                    self.page.select_option(selector, option)
                except Exception as e:
                    self.logger.error(f"[Workflow] Select option thất bại: {e}")
                    return False
            elif action == "extract_text":
                text = self.extract_text(selector, description)
                self.logger.info(f"[Workflow] Extracted text: {text}")
            elif action == "get_attribute":
                attr = step.get("attribute")
                try:
                    element = self.page.query_selector(selector)
                    value = element.get_attribute(attr) if element else None
                    self.logger.info(f"[Workflow] Attribute {attr}: {value}")
                except Exception as e:
                    self.logger.error(f"[Workflow] Get attribute thất bại: {e}")
            elif action == "focus":
                try:
                    self.page.focus(selector)
                except Exception as e:
                    self.logger.error(f"[Workflow] Focus thất bại: {e}")
                    return False
            elif action == "blur":
                try:
                    self.page.eval_on_selector(selector, "el => el.blur()")
                except Exception as e:
                    self.logger.error(f"[Workflow] Blur thất bại: {e}")
                    return False
            elif action == "file_upload":
                file_path = step.get("file_path")
                try:
                    self.page.set_input_files(selector, file_path)
                except Exception as e:
                    self.logger.error(f"[Workflow] File upload thất bại: {e}")
                    return False
            elif action == "contenteditable":
                value = step.get("value", "")
                try:
                    self.page.eval_on_selector(selector, "(el, val) => { el.innerText = val; el.dispatchEvent(new Event('input', { bubbles: true })); }", value)
                except Exception as e:
                    self.logger.error(f"[Workflow] Contenteditable nhập thất bại: {e}")
                    return False
            elif action == "custom_input":
                self.logger.warning(f"[Workflow] Custom input chưa được hỗ trợ cụ thể: {step}")
                return False
            else:
                self.logger.warning(f"[Workflow] Hành động không được hỗ trợ hoặc chưa triển khai: {action}")
                return False
            
            # Nếu sử dụng chế độ người thật
            if use_human_like and self.human_like_mode and self.human_like_interaction:
                if action == "click":
                    if selector:
                        return self.human_like_click(selector, description)
                    elif description:
                        return self.human_like_interaction.find_and_click_visible_element(description)
                    else:
                        self.logger.error("Không có selector hoặc description cho bước click")
                        return False
                
                elif action == "type":
                    value = step.get("value", "")
                    if selector:
                        return self.human_like_type(selector, value, description)
                    elif description:
                        # Tìm và click trước, sau đó nhập
                        if self.human_like_interaction.find_and_click_visible_element(description):
                            time.sleep(0.5)  # Đợi sau khi click
                            self.page.keyboard.type(value)
                            return True
                        return False
                    else:
                        self.logger.error("Không có selector hoặc description cho bước type")
                        return False
                
                elif action == "scroll":
                    direction = step.get("direction", "down")
                    distance = step.get("distance")
                    speed = step.get("speed", "medium")
                    return self.human_like_scroll(direction, distance, speed)
                
                elif action == "wait":
                    time.sleep(step.get("time", 1.0))
                    return True
                
                elif action == "view":
                    return self.human_like_scan_page(focus_area=None, read_time=step.get("time", 3.0))
                
                else:
                    self.logger.warning(f"Hành động không được hỗ trợ trong chế độ người thật: {action}")
                    # Fallback về phương thức thông thường
            
            # Sử dụng cách thông thường với cursor icon
            if self.enable_cursor_icon and selector and hasattr(self, 'element_inspector') and self.element_inspector:
                try:
                    if action == "click":
                        self.element_inspector.move_and_click_with_cursor_icon(
                            selector,
                            cursor_icon_url=self.cursor_icon_url,
                            highlight=self.enable_highlight,
                            click_delay=self.cursor_move_delay,
                            description=description,
                            action="click"
                        )
                        time.sleep(self.cursor_move_delay)
                        return True
                    elif action == "type":
                        value = step.get("value", "")
                        self.element_inspector.move_and_click_with_cursor_icon(
                            selector,
                            cursor_icon_url=self.cursor_icon_url,
                            highlight=self.enable_highlight,
                            click_delay=self.cursor_move_delay,
                            description=description,
                            action="type",
                            type_text=value,
                            type_delay=0.08
                        )
                        time.sleep(self.cursor_move_delay)
                        return True
                except Exception as e:
                    self.logger.warning(f"Lỗi khi sử dụng cursor icon: {e}")
                    # Tiếp tục thử các phương pháp khác
            
            # Sử dụng phương thức thông thường
            if action == "click":
                if selector:
                    return self.click_element(selector, description)
                elif description and self.use_ai_fallback and self.ai_element_finder:
                    return self.ai_element_finder.interact_with_element_by_description(description, action="click")
                else:
                    self.logger.error("Không có selector hoặc description cho bước click")
                    return False
            
            elif action == "type":
                value = step.get("value", "")
                if selector:
                    return self.type_text(selector, value, description)
                elif description and self.use_ai_fallback and self.ai_element_finder:
                    return self.ai_element_finder.interact_with_element_by_description(description, action="type", value=value)
                else:
                    self.logger.error("Không có selector hoặc description cho bước type")
                    return False
            
            elif action == "scroll":
                direction = step.get("direction", "down")
                distance = step.get("distance", 300)
                if direction == "down":
                    self.page.mouse.wheel(0, distance)
                elif direction == "up":
                    self.page.mouse.wheel(0, -distance)
                elif direction == "right":
                    self.page.mouse.wheel(distance, 0)
                elif direction == "left":
                    self.page.mouse.wheel(-distance, 0)
                else:
                    self.logger.warning(f"Hướng cuộn không hỗ trợ: {direction}")
                return True
            
            elif action == "wait":
                time.sleep(step.get("time", 1.0))
                return True
            
            elif action == "view":
                # Chỉ đợi
                time.sleep(step.get("time", 2.0))
                return True
            
            else:
                self.logger.warning(f"Hành động không được hỗ trợ: {action}")
                return False
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thực hiện step {step}: {e}")
            return False

    def auto_fill_inputs_with_ai(self, credentials: dict):
        """
        Tự động dùng AI để tìm selector cho từng trường (username, password, ...) và nhập giá trị vào đúng input.
        Args:
            credentials (dict): {"username": ..., "password": ..., ...}
        Returns:
            dict: {"field": (selector, success)}
        """
        result = {}
        field_map = {
            "username": ["username", "tài khoản", "email", "user", "login"],
            "password": ["password", "mật khẩu", "pass", "pwd"]
        }
        for field, value in credentials.items():
            found = False
            tried_selectors = set()
            for desc in field_map.get(field, [field]):
                selector = self.find_element_by_description(desc)
                self.logger.info(f"[auto_fill_inputs_with_ai] Tìm selector cho '{field}' với mô tả '{desc}': {selector}")
                if selector:
                    ok = self.human_like_type(selector, value, description=desc)
                    self.logger.info(f"[auto_fill_inputs_with_ai] Nhập '{field}' vào {selector}: {'THÀNH CÔNG' if ok else 'THẤT BẠI'}")
                    result[field] = (selector, ok)
                    found = True
                    tried_selectors.add(selector)
                    if ok:
                        break
            # Nếu không tìm được selector, thử tất cả input type phù hợp
            if not found:
                self.logger.warning(f"[auto_fill_inputs_with_ai] Không tìm được input cho '{field}' bằng AI, thử quét toàn bộ input phù hợp trên trang.")
                try:
                    input_infos = self._find_all_inputs_advanced()
                    # Ưu tiên input type phù hợp, không phải captcha/otp
                    for info in input_infos:
                        selector = info.get('selector')
                        if not selector or selector in tried_selectors:
                            continue
                        if info.get('is_captcha') or info.get('is_otp'):
                            self.logger.warning(f"[auto_fill_inputs_with_ai] Phát hiện trường captcha/otp: {selector}, bỏ qua tự động nhập.")
                            continue
                        t = info.get('type','')
                        if field == 'username' and t in ['text', 'email']:
                            ok = self.human_like_type(selector, value, description=selector)
                            self.logger.info(f"[auto_fill_inputs_with_ai] Thử nhập username vào {selector}: {'THÀNH CÔNG' if ok else 'THẤT BẠI'}")
                            result[field] = (selector, ok)
                            if ok:
                                found = True
                                break
                        if field == 'password' and t == 'password':
                            ok = self.human_like_type(selector, value, description=selector)
                            self.logger.info(f"[auto_fill_inputs_with_ai] Thử nhập password vào {selector}: {'THÀNH CÔNG' if ok else 'THẤT BẠI'}")
                            result[field] = (selector, ok)
                            if ok:
                                found = True
                                break
                except Exception as e:
                    self.logger.warning(f"[auto_fill_inputs_with_ai] Lỗi khi thử input toàn trang: {e}")
            if not found:
                self.logger.warning(f"[auto_fill_inputs_with_ai] Không thể tự động nhập '{field}' trên trang.")
                result[field] = (None, False)
        return result

    def _find_all_inputs_advanced(self):
        """
        Quét toàn bộ input, textarea, contenteditable, role="textbox" trên trang, bao gồm cả trong iframe, shadow DOM.
        Trả về list dict: {selector, type, placeholder, name, aria, label, in_iframe, in_shadow, is_contenteditable, is_custom, is_captcha, is_otp, is_disabled, is_readonly, is_hidden, is_visible}
        """
        try:
            js_code = '''() => {
                function getInputs(root, in_iframe=false, iframe_selector=null) {
                    let results = [];
                    // 1. input, textarea
                    let inputs = Array.from(root.querySelectorAll('input, textarea'));
                    for (let el of inputs) {
                        let type = el.type ? el.type.toLowerCase() : el.tagName.toLowerCase();
                        let is_hidden = ['hidden', 'file', 'checkbox', 'radio', 'submit', 'button', 'reset'].includes(type);
                        let is_disabled = el.disabled;
                        let is_readonly = el.readOnly;
                        let is_visible = el.offsetWidth > 0 && el.offsetHeight > 0;
                        let selector = el.id ? `#${el.id}` : (el.name ? `${el.tagName.toLowerCase()}[name='${el.name}']` : '');
                        let label = (el.labels && el.labels.length > 0) ? el.labels[0].innerText : '';
                        let is_captcha = /captcha|recaptcha|robot|not a robot|prove/i.test(el.name+el.id+el.placeholder+label);
                        let is_otp = /otp|one.?time|mã otp|code/i.test(el.name+el.id+el.placeholder+label);
                        results.push({
                            selector, type, placeholder: el.placeholder||'', name: el.name||'', aria: el.getAttribute('aria-label')||'', label,
                            in_iframe, iframe_selector, in_shadow: false, is_contenteditable: false, is_custom: false,
                            is_captcha, is_otp, is_disabled, is_readonly, is_hidden, is_visible
                        });
                    }
                    // 2. contenteditable, role="textbox"
                    let editables = Array.from(root.querySelectorAll('[contenteditable="true"], [role="textbox"]'));
                    for (let el of editables) {
                        let selector = el.id ? `#${el.id}` : (el.className ? el.tagName.toLowerCase()+'.'+el.className.split(' ').join('.') : el.tagName.toLowerCase());
                        let label = '';
                        let is_captcha = /captcha|recaptcha|robot|not a robot|prove/i.test(el.getAttribute('aria-label')+el.id+el.className);
                        let is_otp = /otp|one.?time|mã otp|code/i.test(el.getAttribute('aria-label')+el.id+el.className);
                        results.push({
                            selector, type: 'contenteditable', placeholder: '', name: '', aria: el.getAttribute('aria-label')||'', label,
                            in_iframe, iframe_selector, in_shadow: false, is_contenteditable: true, is_custom: true,
                            is_captcha, is_otp, is_disabled: false, is_readonly: false, is_hidden: false, is_visible: el.offsetWidth>0 && el.offsetHeight>0
                        });
                    }
                    // 3. shadow DOM
                    let all = Array.from(root.querySelectorAll('*'));
                    for (let el of all) {
                        if (el.shadowRoot) {
                            results = results.concat(getInputs(el.shadowRoot, in_iframe, iframe_selector));
                        }
                    }
                    return results;
                }
                let all_results = getInputs(document);
                // 4. iframe
                let iframes = Array.from(document.querySelectorAll('iframe'));
                for (let iframe of iframes) {
                    try {
                        if (iframe.contentDocument) {
                            let iframe_selector = iframe.id ? `#${iframe.id}` : (iframe.name ? `iframe[name='${iframe.name}']` : 'iframe');
                            all_results = all_results.concat(getInputs(iframe.contentDocument, true, iframe_selector));
                        }
                    } catch(e) {}
                }
                return all_results;
            }'''
            return self.page.evaluate(js_code)
        except Exception as e:
            self.logger.error(f"[Workflow] Lỗi khi quét input nâng cao: {e}")
            return []

    def _generate_sample_value(self, info, credentials=None):
        # Sinh dữ liệu mẫu nâng cao dựa trên loại input, tên trường, ngữ cảnh
        if credentials:
            for k, v in credentials.items():
                key = k.lower()
                if key in info['name'].lower() or key in info['placeholder'].lower() or key in info['aria'].lower() or key in info['label'].lower():
                    return v
        if info.get('is_captcha'):
            return '[captcha]'  # Cảnh báo không tự động nhập captcha
        if info.get('is_otp'):
            return '[otp]'     # Cảnh báo không tự động nhập otp
        t = info.get('type','')
        n = info.get('name','').lower()
        if 'email' in t or 'email' in n:
            return 'example@gmail.com'
        if 'password' in t or 'password' in n:
            return 'Password123!'
        if 'search' in t or 'search' in n:
            return 'tìm kiếm mẫu'
        if 'phone' in t or 'phone' in n or 'tel' in t:
            return '0912345678'
        if 'user' in n or 'tài khoản' in n:
            return 'testuser'
        if t == 'textarea' or info.get('is_contenteditable'):
            return 'Nội dung mẫu'
        if 'number' in t:
            return '12345'
        return 'Dữ liệu mẫu'

    def _try_input_methods(self, selector, value, info, max_retry=3):
        # Thử nhiều phương pháp nhập liệu, KHÔNG log di chuyển chuột ảo
        for attempt in range(max_retry):
            try:
                # Di chuyển chuột ảo tới input trước khi nhập nếu có human_like_interaction (không log)
                if self.human_like_mode and self.human_like_interaction:
                    try:
                        element = self.page.query_selector(selector)
                        if element:
                            box = element.bounding_box()
                            if box:
                                x = box["x"] + box["width"] / 2
                                y = box["y"] + box["height"] / 2
                                self.human_like_interaction.human_like_move_mouse(x, y, click=True, reason=f"Focus vào {selector}")
                    except Exception:
                        pass
                # 1. Playwright fill
                try:
                    self.page.fill(selector, value, timeout=10000)
                    value_after = self.page.evaluate("selector => { const el = document.querySelector(selector); return el ? el.value : null; }", selector)
                    if value_after == value:
                        return True
                except Exception:
                    pass
                # 2. Playwright type (xóa nội dung cũ trước)
                try:
                    self.page.focus(selector)
                    self.page.keyboard.press('Control+A')
                    self.page.keyboard.press('Backspace')
                    self.page.type(selector, value, delay=50)
                    value_after = self.page.evaluate("selector => { const el = document.querySelector(selector); return el ? el.value : null; }", selector)
                    if value_after == value:
                        return True
                except Exception:
                    pass
                # 3. JavaScript set value (dùng element handle)
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        js_code = """
                        (el, value) => {
                            el.value = value;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        """
                        self.page.evaluate(js_code, element, value)
                        value_after = self.page.evaluate("selector => { const el = document.querySelector(selector); return el ? el.value : null; }", selector)
                        if value_after == value:
                            return True
                except Exception:
                    pass
                # 4. Clipboard paste (xóa nội dung cũ trước)
                try:
                    import pyperclip
                    pyperclip.copy(value)
                    self.page.focus(selector)
                    self.page.keyboard.press('Control+A')
                    self.page.keyboard.press('Backspace')
                    self.page.keyboard.press('Control+V')
                    value_after = self.page.evaluate("selector => { const el = document.querySelector(selector); return el ? el.value : null; }", selector)
                    if value_after == value:
                        return True
                except Exception:
                    pass
            except Exception:
                pass
            return False

    def _ensure_page(self):
        """
        Đảm bảo đối tượng page tồn tại và hợp lệ
        Nếu page không tồn tại hoặc bị đóng, thử tạo mới
        Trả về True nếu page hoạt động, False nếu không thể tạo page
        """
        try:
            # Kiểm tra xem page có tồn tại và có hợp lệ không
            if self.page is not None:
                try:
                    # Kiểm tra page có hoạt động không bằng cách lấy URL
                    current_url = self.page.url
                    self.logger.debug(f"Page hoạt động bình thường, URL hiện tại: {current_url}", extra={"url": current_url})
                    return True
                except Exception as e:
                    self.logger.warning(f"Page hiện tại không hoạt động: {str(e)}", exc_info=True)
            if self.context is None or not self.browser:
                self.logger.warning("Context hoặc browser không tồn tại, cần khởi động lại browser")
                success = self.start_browser(headless=False)
                if not success:
                    raise BrowserNotAvailable("Không thể khởi động lại browser")
                return success
            self.logger.info("Tạo page mới")
            self.page = self.context.new_page()
            self.pages["main"] = self.page
            if self.use_stealth and stealth_sync is not None:
                try:
                    stealth_sync(self.page)
                    self.logger.info("Đã kích hoạt stealth cho page mới")
                except Exception as e:
                    self.logger.warning(f"Không thể kích hoạt stealth: {str(e)}", exc_info=True)
            self._setup_dialog_handlers()
            self.logger.info("Đã tạo mới page thành công")
            return True
        except BrowserNotAvailable as e:
            self.logger.error(f"Lỗi khi đảm bảo page: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Lỗi không xác định khi đảm bảo page: {str(e)}", exc_info=True)
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def _handle_popups_and_overlays(self):
        """
        Xử lý các popup, overlay tự động
        """
        try:
            # Kiểm tra các popup/overlay phổ biến
            selectors = [
                # Nút đóng popup/overlay
                "button.close, .close-btn, .btn-close, [aria-label='Close'], [title='Close'], .modal-close, .popup-close, .dismiss",
                # Icon đóng (x)
                "[class*='close'] i.fa-times, [class*='close'] i.fa-xmark, .modal i.fa-times, .popup i.fa-times",
                # Cookie consent
                "[class*='cookie'] button, [id*='cookie'] button, [class*='consent'] button, [id*='consent'] button",
                # Quảng cáo, newsletter
                "[class*='banner'] .close, [class*='ad'] .close, [class*='newsletter'] .close, [class*='popup'] .close",
                # Overlay nền mờ
                ".modal-backdrop, .overlay"
            ]
            
            found = False
            self.logger.info("Đang kiểm tra và xử lý các popup/overlay...")
            
            for selector in selectors:
                try:
                    # Thử tìm phần tử
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        try:
                            # Kiểm tra xem phần tử có nhìn thấy được không
                            if element.is_visible():
                                # Lấy thông tin về phần tử
                                tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                                
                                # In thông tin về button đóng
                                self.logger.info(f"Đang đóng {tag_name} với selector '{selector}'")
                                
                                # Click để đóng
                                element.click(force=True)
                                
                                # Đặt cờ đã tìm thấy
                                found = True
                                
                                # Đợi một chút để hiệu ứng đóng hoàn tất
                                time.sleep(0.5)
                        except Exception as element_e:
                            self.logger.debug(f"Không thể tương tác với phần tử '{selector}': {str(element_e)}")
                except Exception as selector_e:
                    self.logger.debug(f"Lỗi khi tìm '{selector}': {str(selector_e)}")
            
            # Thử các phương pháp JavaScript để đóng popup
            if not found:
                try:
                    # Thử đóng các modal Bootstrap
                    self.page.evaluate("""() => {
                        // Đóng các modal Bootstrap
                        if (typeof $ !== 'undefined' && $.fn && $.fn.modal) {
                            $('.modal').modal('hide');
                        }
                        
                        // Đóng modal bằng các phương thức native
                        document.querySelectorAll('.modal, .popup, [role="dialog"]').forEach(el => {
                            // Tìm và click nút đóng
                            const closeBtn = el.querySelector('.close, .btn-close, [data-dismiss], [aria-label="Close"]');
                            if (closeBtn) {
                                closeBtn.click();
                            } else {
                                // Thử ẩn modal
                                el.style.display = 'none';
                                // Hoặc xóa khỏi DOM
                                if (el.parentNode) {
                                    el.parentNode.removeChild(el);
                                }
                            }
                        });
                        
                        // Xóa các overlay
                        document.querySelectorAll('.modal-backdrop, .overlay, .fade').forEach(el => {
                            el.parentNode.removeChild(el);
                        });
                        
                        // Bỏ class tránh scroll
                        document.body.classList.remove('modal-open', 'no-scroll', 'overflow-hidden');
                        document.body.style.overflow = 'auto';
                    }""")
                    
                    self.logger.info("Đã xử lý popup/overlay bằng JavaScript")
                except Exception as js_e:
                    self.logger.debug(f"Lỗi khi xử lý popup bằng JavaScript: {str(js_e)}")
            
            # Nếu có sử dụng overlay_handler thì gọi
            if hasattr(self, 'overlay_handler') and self.overlay_handler:
                try:
                    self.overlay_handler.close_overlay(close_all=True)
                except Exception as handler_e:
                    self.logger.debug(f"Lỗi khi gọi overlay_handler: {str(handler_e)}")
            
            return found
            
        except Exception as e:
            self.logger.warning(f"Lỗi khi xử lý popup/overlay: {str(e)}")
            return False

    @lru_cache(maxsize=128)
    def find_element_by_description(self, description):
        """
        Tìm selector dựa trên mô tả bằng AI hoặc heuristic, có cache LRU
        """
        # Ưu tiên AI finder nếu có
        if self.use_ai_fallback and self.ai_element_finder:
            selector = self.ai_element_finder.find_element_by_description(description)
            if selector:
                return selector
        # Fallback: thử tìm bằng element_inspector nếu có
        if self.element_inspector:
            selector = self.element_inspector.find_element_by_text(description)
            if selector:
                return selector
        # Fallback cuối cùng: None
        return None
