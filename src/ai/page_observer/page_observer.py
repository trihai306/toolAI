"""
Page Observer Module
Theo dõi các thay đổi trang web và tự động gửi HTML mới cho AI để phân tích
"""

import os
import time
import base64
import hashlib
from pathlib import Path
import threading
import queue

class PageObserver:
    """
    Theo dõi các thay đổi trang web và cung cấp HTML cập nhật cho AI
    """
    
    def __init__(self, browser_controller, html_analyzer, update_interval=1.0):
        """
        Khởi tạo PageObserver
        
        Args:
            browser_controller: Controller trình duyệt
            html_analyzer: Đối tượng phân tích HTML
            update_interval (float): Khoảng thời gian kiểm tra cập nhật (giây)
        """
        # Cấu hình logging
        try:
            from src.utils.logging_utils import get_logger
            self.logger = get_logger("PageObserver")
        except ImportError:
            import logging
            self.logger = logging.getLogger("PageObserver")
            
        self.browser = browser_controller
        self.html_analyzer = html_analyzer
        self.update_interval = update_interval
        self.running = False
        self.observer_thread = None
        self.last_html_hash = None
        self.last_url = None
        self.update_queue = queue.Queue()
        self.page_snapshot_dir = Path("data/page_snapshots")
        self.page_snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache selectors đã tìm thấy
        self.selector_cache = {}
        
        # Hàng đợi nhiệm vụ để tương tác an toàn với trình duyệt
        self.task_queue = queue.Queue()
        # Hàng đợi kết quả cho các tác vụ đồng bộ
        self.result_queue = queue.Queue()
        
        self.logger.info("Page Observer đã được khởi tạo")
    
    def start(self):
        """Bắt đầu theo dõi trang web"""
        if self.running:
            self.logger.warning("PageObserver đã đang chạy")
            return False
            
        self.running = True
        self.observer_thread = threading.Thread(target=self._observer_loop, daemon=True)
        self.observer_thread.start()
        self.logger.info("Đã bắt đầu theo dõi trang web")
        return True
    
    def process_browser_tasks(self):
        """
        Xử lý các tác vụ trình duyệt đang chờ - phải được gọi từ main thread
        """
        try:
            # Xử lý tất cả các tác vụ hiện có trong hàng đợi (non-blocking)
            while not self.task_queue.empty():
                try:
                    # Lấy tác vụ từ hàng đợi với timeout ngắn
                    task_function, args, kwargs = self.task_queue.get(block=False)
                    
                    # Thực thi tác vụ
                    result = task_function(*args, **kwargs)
                    
                    # Đặt kết quả vào hàng đợi kết quả
                    self.result_queue.put(result)
                except queue.Empty:
                    break
                except Exception as e:
                    # Xử lý lỗi và vẫn đặt kết quả (None) vào hàng đợi
                    self.logger.error(f"Lỗi khi xử lý tác vụ trình duyệt: {str(e)}")
                    self.result_queue.put(None)
        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý các tác vụ trình duyệt: {str(e)}")
            
    def _screenshot_task(self, filename):
        """Tác vụ chụp màn hình an toàn cho threading"""
        if self.browser and self.browser.page:
            return self.browser.take_screenshot(filename)
        return None
    
    def stop(self):
        """Dừng theo dõi trang web"""
        if not self.running:
            self.logger.warning("PageObserver không đang chạy")
            return False
            
        self.running = False
        if self.observer_thread:
            self.observer_thread.join(timeout=3.0)
        self.logger.info("Đã dừng theo dõi trang web")
        return True
    
    def _observer_loop(self):
        """Vòng lặp chính để theo dõi các thay đổi trang"""
        while self.running:
            try:
                # Thay vì truy cập trực tiếp đối tượng page từ thread này,
                # chúng ta kiểm tra nếu browser đã kết nối
                if self.browser:
                    # Sử dụng phương thức an toàn để lấy thông tin
                    current_url = self._execute_browser_task(self._get_current_url)
                    
                    if current_url:
                        # Lấy HTML của trang hiện tại thông qua task queue
                        current_html = self._execute_browser_task(self._get_page_content)
                        
                        if current_html:
                            current_hash = hashlib.md5(current_html.encode()).hexdigest()
                            
                            # Kiểm tra nếu trang đã thay đổi (URL hoặc nội dung)
                            if current_url != self.last_url or current_hash != self.last_html_hash:
                                self.logger.info(f"Phát hiện thay đổi trang. URL: {current_url}")
                                
                                # Cập nhật trạng thái
                                self.last_url = current_url
                                self.last_html_hash = current_hash
                                
                                # Gửi HTML mới để phân tích
                                self._process_updated_page(current_url, current_html)
                                
                                # Lưu trữ snapshot của trang cho việc sử dụng sau
                                self._save_page_snapshot(current_url, current_html)
                                
                                # Thêm vào hàng đợi cập nhật để thông báo cho các observer
                                self.update_queue.put({
                                    "url": current_url,
                                    "html_hash": current_hash,
                                    "timestamp": time.time()
                                })
            except Exception as e:
                self.logger.error(f"Lỗi trong vòng lặp PageObserver: {str(e)}")
            
            # Đợi cho đến chu kỳ tiếp theo
            time.sleep(self.update_interval)
    
    def _execute_browser_task(self, task_function, *args, **kwargs):
        """
        Thực thi tác vụ trình duyệt một cách an toàn theo thread
        
        Args:
            task_function: Hàm cần thực thi
            *args, **kwargs: Tham số cho hàm
            
        Returns:
            Any: Kết quả của tác vụ
        """
        try:
            # Đặt tác vụ vào hàng đợi để main thread xử lý
            self.task_queue.put((task_function, args, kwargs))
            
            # Đợi và lấy kết quả (timeout để tránh treo)
            try:
                return self.result_queue.get(timeout=5.0)
            except queue.Empty:
                self.logger.warning("Hết thời gian chờ tác vụ browser")
                return None
        except Exception as e:
            self.logger.error(f"Lỗi khi thực thi tác vụ browser: {str(e)}")
            return None
            
    def _get_current_url(self):
        """Hàm an toàn để lấy URL hiện tại"""
        if self.browser and self.browser.page:
            return self.browser.page.url
        return None
        
    def _get_page_content(self):
        """Hàm an toàn để lấy nội dung HTML của trang"""
        if self.browser and self.browser.page:
            return self.browser.page.content()
        return None
    
    def _process_updated_page(self, url, html):
        """
        Xử lý khi trang được cập nhật
        
        Args:
            url (str): URL của trang
            html (str): Nội dung HTML của trang
        """
        try:
            # Chụp ảnh màn hình để hỗ trợ phân tích
            screenshot_path = self.browser.take_screenshot(f"page_snapshot_{int(time.time())}.png")
            
            # Gửi HTML và ảnh chụp màn hình đến bộ phân tích
            self.html_analyzer.analyze_page(url, html, screenshot_path)
            
            # Xóa cache selector cho URL này vì trang đã thay đổi
            self._clear_selector_cache_for_url(url)
            
            self.logger.info(f"Đã gửi HTML mới để phân tích: {url}")
        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý trang được cập nhật: {str(e)}")
    
    def _save_page_snapshot(self, url, html):
        """
        Lưu snapshot của trang hiện tại
        
        Args:
            url (str): URL của trang
            html (str): Nội dung HTML
        """
        try:
            # Tạo tên tệp an toàn từ URL
            safe_filename = self._get_safe_filename_from_url(url)
            timestamp = int(time.time())
            snapshot_path = self.page_snapshot_dir / f"{safe_filename}_{timestamp}.html"
            
            # Lưu nội dung HTML
            with open(snapshot_path, "w", encoding="utf-8") as f:
                f.write(html)
                
            # Lưu metadata
            metadata_path = self.page_snapshot_dir / f"{safe_filename}_{timestamp}.meta"
            with open(metadata_path, "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Title: {self.browser.get_page_title()}\n")
                
            self.logger.debug(f"Đã lưu snapshot trang: {snapshot_path}")
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu snapshot trang: {str(e)}")
    
    def _get_safe_filename_from_url(self, url):
        """
        Tạo tên tệp an toàn từ URL
        
        Args:
            url (str): URL cần chuyển đổi
            
        Returns:
            str: Tên tệp an toàn
        """
        # Loại bỏ schema và các ký tự không an toàn
        safe_name = url.replace("http://", "").replace("https://", "")
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe_name)
        
        # Giới hạn độ dài
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
            
        return safe_name
    
    def _clear_selector_cache_for_url(self, url):
        """
        Xóa cache selector cho URL cụ thể
        
        Args:
            url (str): URL cần xóa cache
        """
        keys_to_remove = []
        for key in self.selector_cache:
            if key.startswith(url + ":"):
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.selector_cache[key]
            
        self.logger.debug(f"Đã xóa {len(keys_to_remove)} cache selector cho URL: {url}")
    
    def find_element_by_description(self, description, context=None):
        """
        Tìm phần tử dựa trên mô tả sử dụng dữ liệu HTML đã lưu
        
        Args:
            description (str): Mô tả phần tử
            context (str, optional): Bối cảnh bổ sung
            
        Returns:
            str: CSS selector hoặc XPath, hoặc None nếu không tìm thấy
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa được khởi động")
            return None
            
        current_url = self.browser.get_current_url()
        
        # Kiểm tra cache
        cache_key = f"{current_url}:{description}:{context if context else ''}"
        if cache_key in self.selector_cache:
            cached_selector = self.selector_cache[cache_key]
            self.logger.info(f"Đã tìm thấy selector trong cache: {cached_selector}")
            return cached_selector
        
        # Chuyển yêu cầu đến HTML analyzer
        selector = self.html_analyzer.find_element_by_description(description, context)
        
        # Lưu vào cache nếu tìm thấy
        if selector:
            self.selector_cache[cache_key] = selector
            
        return selector
    
    def get_page_update(self, timeout=0.1):
        """
        Lấy thông tin về cập nhật trang gần nhất
        
        Args:
            timeout (float): Thời gian tối đa chờ đợi
            
        Returns:
            dict: Thông tin cập nhật hoặc None nếu không có
        """
        try:
            return self.update_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def wait_for_page_load(self, timeout=30.0, check_interval=0.5):
        """
        Đợi cho đến khi trang được tải hoàn tất
        
        Args:
            timeout (float): Thời gian tối đa đợi (giây)
            check_interval (float): Khoảng thời gian kiểm tra (giây)
            
        Returns:
            dict: Thông tin cập nhật hoặc None nếu hết thời gian
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            update = self.get_page_update(timeout=check_interval)
            if update:
                return update
                
            # Kiểm tra trạng thái tải trang
            if self.browser.page:
                try:
                    load_state = self.browser.page.evaluate("""() => {
                        return {
                            readyState: document.readyState,
                            loadingComplete: document.readyState === 'complete'
                        }
                    }""")
                    
                    if load_state.get("loadingComplete"):
                        # Đảm bảo HTML đã được phân tích
                        current_html = self.browser.page.content()
                        current_url = self.browser.get_current_url()
                        self._process_updated_page(current_url, current_html)
                        
                        return {
                            "url": current_url,
                            "html_hash": hashlib.md5(current_html.encode()).hexdigest(),
                            "timestamp": time.time(),
                            "ready_state": load_state.get("readyState")
                        }
                except Exception as e:
                    self.logger.error(f"Lỗi khi kiểm tra trạng thái tải: {str(e)}")
                
            time.sleep(check_interval)
            
        self.logger.warning(f"Hết thời gian đợi trang tải hoàn tất ({timeout}s)")
        return None
