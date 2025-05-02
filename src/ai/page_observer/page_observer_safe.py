"""
Page Observer Module - Thread-Safe Version
Theo dõi các thay đổi trang web và tự động gửi HTML mới cho AI để phân tích
"""

import os
import time
import base64
import hashlib
from pathlib import Path
import threading
import queue

class PageObserverSafe:
    """
    Theo dõi các thay đổi trang web và cung cấp HTML cập nhật cho AI - An toàn với threading
    """
    
    def __init__(self, browser_controller, html_analyzer, update_interval=1.0, debug=False):
        """
        Khởi tạo PageObserver
        
        Args:
            browser_controller: Controller trình duyệt
            html_analyzer: Đối tượng phân tích HTML
            update_interval (float): Khoảng thời gian kiểm tra cập nhật (giây)
            debug (bool): Mode debug để kiểm soát log chi tiết
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
        
        # Lock để đồng bộ truy cập vào tài nguyên dùng chung
        self.lock = threading.Lock()
        
        self.debug = debug
        if self.debug:
            self.logger.info("Page Observer đã được khởi tạo (debug mode)")
    
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
        """Vòng lặp chính để theo dõi các thay đổi trang - không truy cập trình duyệt trực tiếp"""
        while self.running:
            try:
                # Kiểm tra trạng thái của trình duyệt bằng cách gửi yêu cầu
                time.sleep(self.update_interval)
                
                # Không thực hiện gì cho đến khi main thread xử lý các nhiệm vụ
                # Chúng ta sẽ kiểm tra lại trạng thái trang khi main thread gọi process_page_update
            except Exception as e:
                self.logger.error(f"Lỗi trong vòng lặp PageObserver: {str(e)}")
                time.sleep(self.update_interval)  # Đợi một chút trong trường hợp lỗi
    
    def process_page_update(self):
        """
        Kiểm tra và xử lý cập nhật trang - phải được gọi từ main thread
        
        Returns:
            bool: True nếu trang đã thay đổi, False nếu không
        """
        try:
            # Kiểm tra nếu browser được khởi tạo
            if not self.browser or not self.browser.page:
                return False
            
            # Lấy thông tin trang hiện tại
            try:
                current_url = self.browser.get_current_url()
                current_html = self.browser.page.content()
                
                if not current_url or not current_html:
                    return False
                    
                # Tính hash của HTML
                current_hash = hashlib.md5(current_html.encode()).hexdigest()
                
                # Kiểm tra nếu trang đã thay đổi lớn (chuyển url hoặc hash khác biệt lớn)
                with self.lock:
                    if current_url != self.last_url or current_hash != self.last_html_hash:
                        if self.debug:
                            self.logger.info(f"Phát hiện thay đổi trang. URL: {current_url}")
                        
                        # Cập nhật trạng thái
                        self.last_url = current_url
                        self.last_html_hash = current_hash
                        
                        # Xử lý trang mới
                        self._process_updated_page(current_url, current_html)
                        
                        # Thêm thông báo vào hàng đợi
                        self.update_queue.put({
                            "url": current_url,
                            "html_hash": current_hash,
                            "timestamp": time.time()
                        })
                        
                        # Cảnh báo nếu queue quá dài
                        if self.update_queue.qsize() > 10 and self.debug:
                            self.logger.warning(f"PageObserver update_queue backlog: {self.update_queue.qsize()}")
                        
                        return True
            except Exception as e:
                if self.debug:
                    self.logger.error(f"Lỗi khi xử lý cập nhật trang: {str(e)}")
                
            return False
        except Exception as e:
            if self.debug:
                self.logger.error(f"Lỗi trong process_page_update: {str(e)}")
            return False
    
    def _process_updated_page(self, url, html):
        """
        Xử lý khi trang được cập nhật - gọi từ main thread
        
        Args:
            url (str): URL của trang
            html (str): Nội dung HTML của trang
        """
        try:
            # An toàn để chụp ảnh màn hình vì được gọi từ main thread
            screenshot_path = self.browser.take_screenshot(f"page_snapshot_{int(time.time())}.png")
            
            # Gửi HTML và ảnh chụp màn hình đến bộ phân tích
            self.html_analyzer.analyze_page(url, html, screenshot_path)
            
            # Lưu snapshot của trang
            self._save_page_snapshot(url, html)
            
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
        with self.lock:
            keys_to_remove = []
            for key in self.selector_cache:
                if key.startswith(url + ":"):
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                del self.selector_cache[key]
                
            if self.debug:
                self.logger.debug(f"Đã xóa {len(keys_to_remove)} cache selector cho URL: {url}")
    
    def find_element_by_description(self, description, context=None):
        """
        Tìm phần tử dựa trên mô tả sử dụng dữ liệu HTML đã lưu - An toàn cho threading
        
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
        with self.lock:
            if cache_key in self.selector_cache:
                cached_selector = self.selector_cache[cache_key]
                self.logger.info(f"Đã tìm thấy selector trong cache: {cached_selector}")
                return cached_selector
        
        # Cập nhật trang nếu cần
        self.process_page_update()
        
        # Chuyển yêu cầu đến HTML analyzer
        selector = self.html_analyzer.find_element_by_description(description, context)
        
        # Lưu vào cache nếu tìm thấy
        if selector:
            with self.lock:
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
        Đợi cho đến khi trang được tải hoàn tất - An toàn cho threading
        
        Args:
            timeout (float): Thời gian tối đa đợi (giây)
            check_interval (float): Khoảng thời gian kiểm tra (giây)
            
        Returns:
            dict: Thông tin cập nhật hoặc None nếu hết thời gian
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Kiểm tra thông tin cập nhật từ hàng đợi
            update = self.get_page_update(timeout=0)
            if update:
                return update
                
            # Kiểm tra trạng thái tải trang (gọi từ main thread nên an toàn)
            if self.browser and self.browser.page:
                try:
                    # Đánh giá trạng thái tải trang
                    load_state = self.browser.page.evaluate("""() => {
                        return {
                            readyState: document.readyState,
                            loadingComplete: document.readyState === 'complete'
                        }
                    }""")
                    
                    if load_state and load_state.get("loadingComplete"):
                        # Cập nhật trang
                        if self.process_page_update():
                            # Trả về thông tin cập nhật mới nhất
                            return {
                                "url": self.last_url,
                                "html_hash": self.last_html_hash,
                                "timestamp": time.time(),
                                "ready_state": load_state.get("readyState")
                            }
                except Exception as e:
                    self.logger.error(f"Lỗi khi kiểm tra trạng thái tải: {str(e)}")
                
            # Đợi một chút trước khi kiểm tra lại
            time.sleep(check_interval)
            
        self.logger.warning(f"Hết thời gian đợi trang tải hoàn tất ({timeout}s)")
        return None

    def cleanup(self):
        self.stop()
        if self.debug:
            self.logger.info("Đã cleanup PageObserverSafe")
