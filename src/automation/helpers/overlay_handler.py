"""
Overlay Handler Module
Phát hiện và xử lý các dialog, popup, overlay ngăn cản tương tác
"""

import logging
import time
import json
from pathlib import Path

class OverlayHandler:
    """
    Công cụ xử lý các dialog, popup, overlay cản trở việc tương tác
    """
    
    def __init__(self, browser_controller, debug=False):
        """
        Khởi tạo Overlay Handler
        
        Args:
            browser_controller: Controller trình duyệt
            debug (bool): Bật log chi tiết
        """
        # Cấu hình logging
        try:
            from utils.logging_utils import get_logger
            self.logger = get_logger("OverlayHandler")
        except ImportError:
            self.logger = logging.getLogger("OverlayHandler")
            
        self.browser = browser_controller
        self.debug = debug
        
        # Danh sách loại overlay phổ biến
        self.common_overlay_patterns = {
            "cookie_consent": [
                ".cookie", ".cookies", "#cookie", "#cookies", 
                "[class*='cookie']", "[id*='cookie']",
                ".consent", "#consent", "[class*='consent']",
                "[class*='gdpr']", "[id*='gdpr']"
            ],
            "newsletter_signup": [
                ".newsletter", "#newsletter", "[class*='newsletter']",
                ".signup", "#signup", "[class*='signup']",
                ".subscribe", "#subscribe", "[class*='subscribe']"
            ],
            "modal_popup": [
                ".modal", "#modal", "[class*='modal']", 
                ".popup", "#popup", "[class*='popup']",
                ".dialog", "#dialog", "[role='dialog']",
                "[aria-modal='true']"
            ],
            "login_wall": [
                ".login", "#login", "[class*='login']",
                ".register", "#register", "[class*='register']",
                ".paywall", "#paywall", "[class*='paywall']"
            ],
            "social_share": [
                ".social", "#social", "[class*='social']",
                ".share", "#share", "[class*='share']"
            ],
            "chat_widget": [
                ".chat", "#chat", "[class*='chat']",
                ".support", "#support", "[class*='support']",
                ".messenger", "#messenger", "[class*='messenger']"
            ],
            "sticky_header": [
                "header.fixed", "header.sticky", ".fixed-header", 
                ".sticky-header", "[class*='fixed-header']"
            ],
            "ad_banner": [
                ".ad", "#ad", "[class*='ad-']", "[id*='ad-']",
                ".banner", "#banner", "[class*='banner']"
            ]
        }
        
        # Quy tắc đóng phổ biến
        self.close_button_patterns = [
            ".close", "#close", "[class*='close']", 
            ".dismiss", "#dismiss", "[class*='dismiss']",
            ".no-thanks", "#no-thanks", "[class*='no-thanks']",
            "button[aria-label='Close']", "[aria-label*='close']",
            "button.btn-close", ".modal-close",
            "button.x", "button.X", ".x-close",
            "[data-dismiss='modal']"
        ]
    
    def detect_overlays(self, take_screenshot=True):
        """
        Phát hiện các overlay trên trang
        
        Args:
            take_screenshot (bool): Chụp ảnh màn hình của overlay
            
        Returns:
            list: Danh sách các overlay phát hiện được
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return None
        
        try:
            # Mã JavaScript để tìm các overlay
            import json as _json
            # Serialize sang JSON string
            overlay_patterns_json = _json.dumps(self.common_overlay_patterns, ensure_ascii=False)
            close_button_patterns_json = _json.dumps(self.close_button_patterns, ensure_ascii=False)
            js_code = """
(args) => {
    const overlayPatterns = JSON.parse(args[0]);
    const closeButtonPatterns = JSON.parse(args[1]);
    const results = [];
    
    // Hàm kiểm tra nếu phần tử là overlay
    const isOverlay = (element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        
        // Kiểm tra xem có phải z-index cao và position fixed/absolute
        const zIndex = parseInt(style.zIndex, 10);
        const isFixed = style.position === 'fixed';
        const isAbsolute = style.position === 'absolute';
        const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
        const isLarge = (rect.width > window.innerWidth * 0.3 || rect.height > window.innerHeight * 0.3);
        
        // Nếu là fixed/absolute với z-index cao và hiển thị
        return (isFixed || isAbsolute) && zIndex > 10 && isVisible && isLarge;
    };
    
    // Kiểm tra phần tử có phải modal/dialog
    const isModal = (element) => {
        return element.getAttribute('role') === 'dialog' || 
               element.getAttribute('aria-modal') === 'true' ||
               element.classList.contains('modal') ||
               element.id.includes('modal');
    };
    
    // Tìm phần tử theo selector, trả về danh sách kết quả
    const findElements = (selector) => {
        try {
            return Array.from(document.querySelectorAll(selector));
        } catch (e) {
            return [];
        }
    };
    
    // Tìm nút đóng bên trong phần tử
    const findCloseButtons = (element) => {
        const buttons = [];
        for (const pattern of closeButtonPatterns) {
            const found = Array.from(element.querySelectorAll(pattern));
            buttons.push(...found);
        }
        
        // Tìm thêm các phần tử có text như "Đóng", "Close", "X", "×"
        const possibleClose = Array.from(element.querySelectorAll('button, a, div, span'))
            .filter(el => {
                const text = el.textContent?.trim();
                return text === 'X' || text === '×' || text === 'x' || text === 'Đóng' || 
                       text === 'Close' || text === 'Cancel' || text === 'No Thanks';
            });
        
        buttons.push(...possibleClose);
        return buttons;
    };
    
    // Kiểm tra mọi loại overlay phổ biến
    for (const [overlayType, patterns] of Object.entries(overlayPatterns)) {
        if (!Array.isArray(patterns)) {
            console.warn('patterns for', overlayType, 'is not array:', patterns);
            continue;
        }
        for (const pattern of patterns) {
            const elements = findElements(pattern);
            
            for (const element of elements) {
                if (isOverlay(element) || isModal(element)) {
                    // Tìm nút đóng
                    const closeButtons = findCloseButtons(element);
                    
                    // Lấy selector và text của nút đóng
                    const buttonInfos = closeButtons.map(button => {
                        // Tạo selector cho nút
                        let buttonSelector = '';
                        if (button.id) buttonSelector = `#${button.id}`;
                        else if (button.classList.length > 0) buttonSelector = `${button.tagName.toLowerCase()}.${Array.from(button.classList).join('.')}`;
                        else buttonSelector = button.tagName.toLowerCase();
                        
                        return {
                            text: button.textContent?.trim(),
                            selector: buttonSelector
                        };
                    });
                    
                    // Lấy vị trí
                    const rect = element.getBoundingClientRect();
                    
                    // Tạo selector cho overlay
                    let overlaySelector = '';
                    if (element.id) overlaySelector = `#${element.id}`;
                    else if (element.classList.length > 0) overlaySelector = `${element.tagName.toLowerCase()}.${Array.from(element.classList).join('.')}`;
                    else overlaySelector = element.tagName.toLowerCase();
                    
                    // Thêm vào kết quả 
                    results.push({
                        type: overlayType,
                        selector: overlaySelector,
                        position: {
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        zIndex: parseInt(window.getComputedStyle(element).zIndex, 10),
                        closeButtons: buttonInfos,
                        hasVisibleCloseButton: buttonInfos.length > 0,
                        text: element.textContent?.trim().substring(0, 200) // Giới hạn text
                    });
                    
                    // Tránh trùng lặp
                    break;
                }
            }
        }
    }
    
    // Tìm thêm các phần tử có vẻ là overlay nhưng không khớp với pattern phổ biến
    const allElements = document.querySelectorAll('div, section, aside');
    for (const element of allElements) {
        // Bỏ qua nếu đã có trong kết quả
        if (results.some(r => r.selector === `#${element.id}` || 
                             r.selector === `${element.tagName.toLowerCase()}.${Array.from(element.classList).join('.')}`)) {
            continue;
        }
        
        if (isOverlay(element)) {
            // Tìm nút đóng
            const closeButtons = findCloseButtons(element);
            const buttonInfos = closeButtons.map(button => {
                let buttonSelector = '';
                if (button.id) buttonSelector = `#${button.id}`;
                else if (button.classList.length > 0) buttonSelector = `${button.tagName.toLowerCase()}.${Array.from(button.classList).join('.')}`;
                else buttonSelector = button.tagName.toLowerCase();
                
                return {
                    text: button.textContent?.trim(),
                    selector: buttonSelector
                };
            });
            
            // Lấy vị trí
            const rect = element.getBoundingClientRect();
            
            // Tạo selector
            let overlaySelector = '';
            if (element.id) overlaySelector = `#${element.id}`;
            else if (element.classList.length > 0) overlaySelector = `${element.tagName.toLowerCase()}.${Array.from(element.classList).join('.')}`;
            else overlaySelector = element.tagName.toLowerCase();
            
            // Đoán loại overlay
            let overlayType = 'unknown';
            const textLower = element.textContent?.toLowerCase() || '';
            if (textLower.includes('cookie') || textLower.includes('gdpr')) overlayType = 'cookie_consent';
            else if (textLower.includes('newsletter') || textLower.includes('subscribe')) overlayType = 'newsletter_signup';
            else if (textLower.includes('login') || textLower.includes('sign in')) overlayType = 'login_wall';
            
            // Thêm vào kết quả
            results.push({
                type: overlayType,
                selector: overlaySelector,
                position: {
                    x: Math.round(rect.left),
                    y: Math.round(rect.top),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                },
                zIndex: parseInt(window.getComputedStyle(element).zIndex, 10),
                closeButtons: buttonInfos,
                hasVisibleCloseButton: buttonInfos.length > 0,
                text: element.textContent?.trim().substring(0, 200) // Giới hạn text
            });
        }
    }
    
    // Sắp xếp theo z-index (giảm dần)
    results.sort((a, b) => b.zIndex - a.zIndex);
    
    return results;
}"""
            
            # Thực thi mã JavaScript với các tham số đã được kiểm tra
            overlays = self.browser.page.evaluate(js_code, [overlay_patterns_json, close_button_patterns_json])
            
            if not overlays or len(overlays) == 0:
                self.logger.info("Không phát hiện overlay nào trên trang")
                return []
            
            # Thêm screenshot nếu yêu cầu
            if take_screenshot:
                screenshot_folder = Path("data/overlay_screenshots")
                screenshot_folder.mkdir(parents=True, exist_ok=True)
                
                for i, overlay in enumerate(overlays):
                    try:
                        # Chụp ảnh màn hình
                        timestamp = int(time.time())
                        screenshot_path = screenshot_folder / f"overlay_{i+1}_{timestamp}.png"
                        
                        # Chụp overlay
                        if overlay["position"]:
                            clip = {
                                "x": max(0, overlay["position"]["x"]),
                                "y": max(0, overlay["position"]["y"]),
                                "width": min(overlay["position"]["width"], self.browser.page.viewport_size["width"] - overlay["position"]["x"]),
                                "height": min(overlay["position"]["height"], self.browser.page.viewport_size["height"] - overlay["position"]["y"])
                            }
                            
                            # Chỉ chụp nếu có vùng hiển thị hợp lệ
                            if clip["width"] > 0 and clip["height"] > 0:
                                self.browser.page.screenshot(path=str(screenshot_path), clip=clip)
                                overlay["screenshot"] = str(screenshot_path)
                            
                    except Exception as e:
                        self.logger.warning(f"Không thể chụp ảnh overlay: {str(e)}")
            
            # In thông tin về overlay
            print(f"\n=== ĐÃ PHÁT HIỆN {len(overlays)} OVERLAY ===")
            for i, overlay in enumerate(overlays):
                print(f"{i+1}. Loại: {overlay['type']}")
                print(f"   Selector: {overlay['selector']}")
                print(f"   Z-index: {overlay['zIndex']}")
                print(f"   Nút đóng: {'Có' if overlay['hasVisibleCloseButton'] else 'Không'}")
                if overlay.get("screenshot"):
                    print(f"   Ảnh chụp: {overlay['screenshot']}")
                print()
            
            return overlays
            
        except Exception as e:
            self.logger.error(f"Lỗi khi phát hiện overlay: {str(e)}")
            return []
    
    def close_overlay(self, close_all=True):
        # Cải tiến: thử nhiều chiến lược nếu overlay không đóng được
        result = self._close_overlay_base(close_all)
        if not result and self.debug:
            self.logger.info("Overlay cứng đầu, thử scroll, zoom, reload, chuyển tab mới...")
            try:
                self.browser.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)
                self.browser.page.evaluate("document.body.style.zoom='80%'")
                time.sleep(0.5)
                self.browser.page.reload()
                time.sleep(1)
                # Thử mở tab mới nếu vẫn không được
                self.browser.new_tab()
                self.browser.page.goto(self.browser.get_current_url())
                time.sleep(1)
                result = self._close_overlay_base(close_all)
            except Exception as e:
                self.logger.warning(f"Lỗi khi thử các chiến lược overlay nâng cao: {e}")
        return result
    
    def _close_overlay_base(self, close_all=True):
        # Hàm gốc đóng overlay như cũ
        # ... (giữ nguyên logic cũ hoặc gọi lại hàm cũ nếu có) ...
        # Ví dụ:
        try:
            # Phát hiện overlay
            overlays = self.detect_overlays()
            if not overlays or len(overlays) == 0:
                if self.debug:
                    self.logger.info("Không phát hiện overlay nào cản trở (base)")
                return True
            # Đóng overlay
            for overlay in overlays:
                try:
                    overlay.click()
                    if self.debug:
                        self.logger.info(f"Đã click overlay: {overlay}")
                    if not close_all:
                        break
                except Exception as e:
                    if self.debug:
                        self.logger.warning(f"Không thể click overlay: {e}")
            return True
        except Exception as e:
            if self.debug:
                self.logger.warning(f"Lỗi khi đóng overlay (base): {e}")
            return False
    
    def remove_all_overlays(self):
        """
        Xóa tất cả overlay trên trang
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Mã JavaScript để xóa tất cả overlay
            js_code = """() => {
                // Các loại overlay phổ biến
                const overlaySelectors = [
                    // Cookie consent
                    ".cookie-banner", "#cookie-banner", ".cookie-consent", "#cookie-consent",
                    "[class*='cookie-banner']", "[id*='cookie-banner']", 
                    "[class*='cookie-consent']", "[id*='cookie-consent']",
                    "[class*='gdpr']", "[id*='gdpr']",
                    
                    // Modals/Dialogs
                    ".modal", "#modal", "[class*='modal']", "[role='dialog']", "[aria-modal='true']",
                    ".popup", "#popup", "[class*='popup']", 
                    
                    // Newsletter/Signup
                    ".newsletter", "#newsletter", "[class*='newsletter']",
                    ".signup", "#signup", "[class*='signup']",
                    
                    // Paywalls/Login
                    ".paywall", "#paywall", "[class*='paywall']",
                    ".login-wall", "#login-wall", "[class*='login-wall']",
                    
                    // Chat widgets
                    ".chat-widget", "#chat-widget", "[class*='chat-widget']",
                    
                    // Làm sạch body overflow
                    "body.modal-open", "body.no-scroll", "body[style*='overflow: hidden']"
                ];
                
                // Đếm số lượng overlay đã xóa
                let removedCount = 0;
                
                // Xóa các overlay dựa trên selector
                for (const selector of overlaySelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            // Đối với body, chỉ xóa class và style
                            if (el.tagName.toLowerCase() === 'body') {
                                el.classList.remove('modal-open', 'no-scroll');
                                el.style.overflow = '';
                                continue;
                            }
                            
                            // Ẩn hoặc xóa phần tử
                            if (el.parentNode) {
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                                el.style.opacity = '0';
                                el.style.pointerEvents = 'none';
                                removedCount++;
                            }
                        }
                    } catch (e) {
                        // Bỏ qua lỗi
                    }
                }
                
                // Tìm và xóa các phần tử cố định với z-index cao 
                const allElements = document.querySelectorAll('div, section, aside');
                for (const el of allElements) {
                    try {
                        const style = window.getComputedStyle(el);
                        const position = style.position;
                        const zIndex = parseInt(style.zIndex, 10);
                        
                        // Nếu là fixed/absolute với z-index cao
                        if ((position === 'fixed' || position === 'absolute') && zIndex > 100) {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.opacity = '0';
                            el.style.pointerEvents = 'none';
                            removedCount++;
                        }
                    } catch (e) {
                        // Bỏ qua lỗi
                    }
                }
                
                // Sửa lại body overflow
                document.body.style.overflow = 'auto';
                document.documentElement.style.overflow = 'auto';
                
                return removedCount;
            }"""
            
            # Thực thi mã JavaScript
            removed_count = self.browser.page.evaluate(js_code)
            
            self.logger.info(f"Đã xóa {removed_count} overlay")
            print(f"Đã xóa {removed_count} overlay để cải thiện khả năng tương tác")
            
            return removed_count > 0
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xóa overlay: {str(e)}")
            return False
    
    def check_and_handle_dialog(self, wait_time=0.5):
        """
        Kiểm tra và xử lý dialog hệ thống (alert, confirm, prompt)
        
        Args:
            wait_time (float): Thời gian đợi (giây)
            
        Returns:
            bool: True nếu phát hiện và xử lý dialog, False nếu không có dialog
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Thiết lập handler cho dialog
            dialog_detected = False
            dialog_info = {"type": None, "message": None}
            
            def dialog_handler(dialog):
                nonlocal dialog_detected, dialog_info
                dialog_detected = True
                dialog_info["type"] = dialog.type
                dialog_info["message"] = dialog.message
                
                # Tự động chấp nhận dialog
                if dialog.type == "alert":
                    dialog.accept()
                elif dialog.type == "confirm":
                    dialog.accept()  # Có thể thay đổi thành dismiss() nếu muốn từ chối
                elif dialog.type == "prompt":
                    dialog.accept("")  # Có thể thay đổi để nhập giá trị
                elif dialog.type == "beforeunload":
                    dialog.accept()
                
                print(f"Đã xử lý dialog: {dialog.type} - {dialog.message}")
            
            # Đăng ký handler
            self.browser.page.once("dialog", dialog_handler)
            
            # Đợi một chút để xem có dialog không
            time.sleep(wait_time)
            
            # Trả về kết quả
            return dialog_detected
            
        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra dialog: {str(e)}")
            return False
    
    def enable_auto_dismiss_dialogs(self, accept_all=True):
        """
        Bật tính năng tự động xử lý dialog
        
        Args:
            accept_all (bool): True để chấp nhận tất cả dialog, False để từ chối
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            def dialog_handler(dialog):
                dialog_type = dialog.type
                dialog_message = dialog.message
                
                self.logger.info(f"Phát hiện dialog: {dialog_type} - {dialog_message}")
                
                # Xử lý theo loại
                if dialog_type == "beforeunload":
                    dialog.accept()  # Luôn chấp nhận beforeunload
                elif accept_all:
                    if dialog_type == "prompt":
                        dialog.accept("")  # Chấp nhận với chuỗi rỗng
                    else:
                        dialog.accept()
                else:
                    dialog.dismiss()  # Từ chối
                
                self.logger.info(f"Đã {'chấp nhận' if accept_all else 'từ chối'} dialog: {dialog_type}")
            
            # Đăng ký handler
            self.browser.page.on("dialog", dialog_handler)
            
            print(f"Đã bật tự động {'chấp nhận' if accept_all else 'từ chối'} dialog")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi bật tự động xử lý dialog: {str(e)}")
            return False
    
    def make_element_clickable(self, selector, description=None):
        """
        Làm cho phần tử có thể click được (xử lý các phần tử cản trở)
        
        Args:
            selector (str): CSS Selector hoặc XPath của phần tử
            description (str, optional): Mô tả phần tử để tìm kiếm nếu selector không hoạt động
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Tìm selector nếu chỉ có mô tả
            if not selector and description:
                if hasattr(self.browser, 'ai_element_finder') and self.browser.ai_element_finder:
                    selector = self.browser.ai_element_finder.find_element_by_description(description)
                    if not selector:
                        self.logger.warning(f"Không tìm thấy phần tử với mô tả: {description}")
                        return False
                else:
                    self.logger.warning("AI Element Finder không khả dụng")
                    return False
            
            # Kiểm tra nếu phần tử có thể click được
            js_code = """(selector) => {
                try {
                    const element = document.querySelector(selector);
                    if (!element) return { found: false, message: "Không tìm thấy phần tử" };
                    
                    // Kiểm tra các thuộc tính
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    
                    const isVisible = style.display !== 'none' && 
                                     style.visibility !== 'hidden' && 
                                     style.opacity !== '0';
                    
                    const isInViewport = rect.top >= 0 &&
                                        rect.left >= 0 &&
                                        rect.bottom <= window.innerHeight &&
                                        rect.right <= window.innerWidth;
                    
                    // Kiểm tra overlay che phủ
                    let coveredBy = null;
                    const elementAtPoint = document.elementFromPoint(
                        rect.left + rect.width/2,
                        rect.top + rect.height/2
                    );
                    
                    if (elementAtPoint && !element.contains(elementAtPoint) && !elementAtPoint.contains(element)) {
                        coveredBy = {
                            tag: elementAtPoint.tagName,
                            id: elementAtPoint.id,
                            classes: Array.from(elementAtPoint.classList)
                        };
                    }
                    
                    return {
                        found: true,
                        isVisible,
                        isInViewport,
                        coveredBy,
                        position: {
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }
                    };
                } catch (e) {
                    return { found: false, message: e.toString() };
                }
            }"""
            
            # Thực thi mã JavaScript
            check_result = self.browser.page.evaluate(js_code, selector)
            
            if not check_result["found"]:
                self.logger.warning(f"Không tìm thấy phần tử: {selector}")
                return False
            
            # Nếu phần tử không hiển thị, thử làm cho nó hiển thị
            if not check_result["isVisible"]:
                self.logger.info(f"Phần tử không hiển thị, thử làm cho nó hiển thị: {selector}")
                
                js_fix = f"""(selector) => {{
                    try {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.style.display = '';
                            element.style.visibility = 'visible';
                            element.style.opacity = '1';
                            return true;
                        }}
                        return false;
                    }} catch (e) {{
                        return false;
                    }}
                }}"""
                
                result = self.browser.page.evaluate(js_fix, selector)
                if not result:
                    self.logger.warning(f"Không thể làm cho phần tử hiển thị: {selector}")
                    return False
            
            # Nếu phần tử không trong viewport, cuộn đến nó
            if not check_result["isInViewport"]:
                self.logger.info(f"Phần tử không trong viewport, cuộn đến nó: {selector}")
                try:
                    # Sử dụng phương thức của playwright
                    if selector.startswith('xpath=') or selector.startswith('/'):
                        element = self.browser.page.locator(f"{selector}")
                    else:
                        element = self.browser.page.locator(f"css={selector}")
                    
                    element.scroll_into_view_if_needed()
                    time.sleep(0.5)  # Đợi cuộn hoàn tất
                except Exception as e:
                    self.logger.warning(f"Không thể cuộn đến phần tử: {str(e)}")
                    
                    # Thử dùng JavaScript
                    js_scroll = f"""(selector) => {{
                        try {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                                return true;
                            }}
                            return false;
                        }} catch (e) {{
                            return false;
                        }}
                    }}"""
                    
                    result = self.browser.page.evaluate(js_scroll, selector)
                    if not result:
                        self.logger.warning(f"Không thể cuộn đến phần tử: {selector}")
                        return False
                    
                    time.sleep(0.5)  # Đợi cuộn hoàn tất
            
            # Nếu phần tử bị che phủ, xử lý overlay
            if check_result["coveredBy"]:
                self.logger.info(f"Phần tử bị che phủ bởi: {check_result['coveredBy']}")
                
                # Thử xóa phần tử che phủ
                js_remove = """(params) => {
                    try {
                        const elementAtPoint = document.elementFromPoint(params.x, params.y);
                        if (elementAtPoint) {
                            // Nếu là một overlay
                            if (elementAtPoint.style.position === 'fixed' || 
                                elementAtPoint.style.position === 'absolute') {
                                // Thử ẩn
                                elementAtPoint.style.display = 'none';
                                elementAtPoint.style.visibility = 'hidden';
                                elementAtPoint.style.opacity = '0';
                                elementAtPoint.style.pointerEvents = 'none';
                                return true;
                            } else {
                                // Thử làm cho phần tử có thể click qua overlay
                                elementAtPoint.style.pointerEvents = 'none';
                                return true;
                            }
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }"""
                
                # Tính toán điểm giữa của phần tử
                center_x = check_result["position"]["x"] + check_result["position"]["width"] / 2
                center_y = check_result["position"]["y"] + check_result["position"]["height"] / 2
                
                # Truyền tọa độ dưới dạng một đối tượng duy nhất
                params = {"x": center_x, "y": center_y}
                
                result = self.browser.page.evaluate(js_remove, params)
                
                if not result:
                    # Thử phương pháp khắc phục khác - click bằng JavaScript
                    self.logger.info("Thử click bằng JavaScript để vượt qua overlay")
                    
                    js_click = f"""(selector) => {{
                        try {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                // Kích hoạt cả mousedown, mouseup và click
                                const clickEvent = new MouseEvent('click', {{
                                    view: window,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                element.dispatchEvent(clickEvent);
                                return true;
                            }}
                            return false;
                        }} catch (e) {{
                            return false;
                        }}
                    }}"""
                    
                    result = self.browser.page.evaluate(js_click, selector)
                    if result:
                        self.logger.info(f"Đã click bằng JavaScript: {selector}")
                        return True
            
            self.logger.info(f"Phần tử đã có thể click được: {selector}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi làm cho phần tử có thể click: {str(e)}")
            return False
