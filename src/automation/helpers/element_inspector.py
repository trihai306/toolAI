"""
Element Inspector Module
Cung cấp các công cụ trực quan để xác định và tìm kiếm phần tử trên trang web
"""

import logging
import time
import json
import base64
from pathlib import Path
import re
try:
    import pytesseract
    import cv2
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

class ElementInspector:
    """
    Công cụ trực quan để xác định và tìm kiếm phần tử trên trang web
    """
    
    def __init__(self, browser_controller, debug=False):
        """
        Khởi tạo Element Inspector
        
        Args:
            browser_controller: Controller trình duyệt 
            debug (bool): Cho phép log chi tiết
        """
        # Cấu hình logging
        try:
            from src.utils.logging_utils import get_logger
            self.logger = get_logger("ElementInspector")
        except ImportError:
            self.logger = logging.getLogger("ElementInspector")
            
        self.browser = browser_controller
        self.debug = debug
        
        # Thư mục lưu trữ ảnh chụp màn hình
        self.screenshots_dir = Path("data/element_screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # IDs của các highlight đã tạo
        self.highlight_ids = []
        
    def wait_for_page_ready(self, timeout=15):
        """
        Đợi trang web load xong (DOMContentLoaded hoặc networkidle)
        """
        try:
            self.browser.page.wait_for_load_state('domcontentloaded', timeout=timeout*1000)
            self.browser.page.wait_for_load_state('networkidle', timeout=timeout*1000)
            self.logger.info("Trang đã load xong và sẵn sàng thao tác.")
        except Exception as e:
            self.logger.warning(f"Chờ trang load xong bị lỗi hoặc quá thời gian: {e}")

    def highlight_element(self, selector, color="red", timeout=5000, take_screenshot=True):
        """
        Tạo viền sáng quanh phần tử để xác định trực quan
        
        Args:
            selector (str): CSS Selector hoặc XPath
            color (str): Màu viền ("red", "blue", "green", "yellow", "purple")
            timeout (int): Thời gian hiển thị (ms)
            take_screenshot (bool): Chụp ảnh màn hình phần tử được highlight
            
        Returns:
            dict: Thông tin về phần tử hoặc None nếu không tìm thấy
        """
        self.wait_for_page_ready()
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return None
        
        try:
            # Kiểm tra nếu selector là XPath
            is_xpath = selector.startswith('xpath=') or selector.startswith('/') or selector.startswith('.//')
            
            # Chuyển đổi màu thành mã hex
            color_map = {
                "red": "#FF0000", 
                "blue": "#0000FF",
                "green": "#00FF00",
                "yellow": "#FFFF00",
                "purple": "#800080",
                "orange": "#FFA500"
            }
            hex_color = color_map.get(color.lower(), "#FF0000")
            
            # Tạo ID duy nhất cho highlight
            highlight_id = f"highlight_{int(time.time() * 1000)}"
            self.highlight_ids.append(highlight_id)
            
            # Đảm bảo phần tử hiển thị trong viewport
            element_info = None
            
            # Đoạn JavaScript để highlight phần tử
            js_code = f"""(args) => {{
                const [selector, isXPath, highlightId, hexColor, timeout] = args;
                // Tìm phần tử
                const element = isXPath 
                    ? document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
                    : document.querySelector(selector);
                if (!element) return null;
                element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                const rect = element.getBoundingClientRect();
                const elementInfo = {{
                    tagName: element.tagName.toLowerCase(),
                    id: element.id,
                    classes: Array.from(element.classList),
                    text: element.textContent?.trim().substring(0, 100),
                    attributes: {{}},
                    position: {{
                        x: Math.round(rect.left),
                        y: Math.round(rect.top),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    }},
                    isVisible: window.getComputedStyle(element).display !== 'none',
                    html: element.outerHTML.substring(0, 500)
                }};
                for (const attr of element.attributes) {{
                    elementInfo.attributes[attr.name] = attr.value;
                }}
                const highlightElement = document.createElement('div');
                highlightElement.id = highlightId;
                highlightElement.style.position = 'absolute';
                highlightElement.style.left = rect.left + 'px';
                highlightElement.style.top = rect.top + 'px';
                highlightElement.style.width = rect.width + 'px';
                highlightElement.style.height = rect.height + 'px';
                highlightElement.style.border = `3px solid ${{hexColor}}`;
                highlightElement.style.boxShadow = `0 0 5px ${{hexColor}}`;
                highlightElement.style.pointerEvents = 'none';
                highlightElement.style.zIndex = '9999';
                highlightElement.style.boxSizing = 'border-box';
                const label = document.createElement('div');
                label.textContent = elementInfo.tagName + (element.id ? '#' + element.id : '');
                label.style.position = 'absolute';
                label.style.top = '-25px';
                label.style.left = '0';
                label.style.background = hexColor;
                label.style.color = 'white';
                label.style.padding = '2px 5px';
                label.style.borderRadius = '3px';
                label.style.fontSize = '12px';
                label.style.fontWeight = 'bold';
                highlightElement.appendChild(label);
                document.body.appendChild(highlightElement);
                setTimeout(() => {{
                    if (document.getElementById(highlightId)) {{
                        document.body.removeChild(document.getElementById(highlightId));
                    }}
                }}, timeout);
                return elementInfo;
            }}"""
            
            # Thực thi mã JavaScript
            args = [selector, is_xpath, highlight_id, hex_color, timeout]
            element_info = self.browser.page.evaluate(js_code, args)
            
            if not element_info:
                self.logger.warning(f"Không tìm thấy phần tử: {selector}")
                return None
            
            # Chụp ảnh phần tử được highlight nếu yêu cầu
            if take_screenshot:
                screenshot_filename = f"element_{int(time.time())}.png"
                screenshot_path = self.screenshots_dir / screenshot_filename
                
                # Đợi một chút để highlight hiển thị
                time.sleep(0.5)
                
                # Chụp ảnh phần tử trong viewport
                clip = None
                if element_info["position"]:
                    pos = element_info["position"]
                    # Mở rộng clip để bao gồm viền highlight
                    clip = {
                        "x": max(0, pos["x"] - 10),
                        "y": max(0, pos["y"] - 30),  # Thêm không gian cho label
                        "width": pos["width"] + 20,
                        "height": pos["height"] + 40
                    }
                
                # Chụp ảnh
                if clip:
                    self.browser.page.screenshot(path=str(screenshot_path), clip=clip)
                else:
                    self.browser.page.screenshot(path=str(screenshot_path))
                
                # Thêm đường dẫn ảnh vào thông tin phần tử
                element_info["screenshot"] = str(screenshot_path)
            
            self.logger.info(f"Đã highlight phần tử: {selector}")
            return element_info
            
        except Exception as e:
            self.logger.error(f"Lỗi khi highlight phần tử {selector}: {str(e)}")
            return None
    
    def inspect_element(self, selector=None, description=None):
        """
        Kiểm tra và hiển thị thông tin chi tiết về phần tử
        
        Args:
            selector (str, optional): CSS selector hoặc XPath
            description (str, optional): Mô tả phần tử để tìm kiếm
            
        Returns:
            dict: Thông tin về phần tử (bao gồm vị trí, kích thước, trạng thái hiển thị, che khuất) hoặc None nếu không tìm thấy
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return None
        
        try:
            # Nếu chỉ có mô tả, thử tìm selector
            if not selector and description and hasattr(self.browser, 'ai_element_finder') and self.browser.ai_element_finder:
                selector = self.browser.ai_element_finder.find_element_by_description(description)
            if not selector:
                self.logger.error("Cần cung cấp selector hoặc mô tả phần tử")
                return None
            # Kiểm tra nếu selector là XPath
            is_xpath = selector.startswith('xpath=') or selector.startswith('/') or selector.startswith('.//')
            if is_xpath:
                element = self.browser.page.query_selector(f"xpath={selector[6:] if selector.startswith('xpath=') else selector}")
            else:
                element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử: {selector}")
                return None
            # Lấy thông tin chi tiết
            box = element.bounding_box()
            visible = element.is_visible() if hasattr(element, 'is_visible') else True
            # Kiểm tra che khuất
            is_obscured = False
            try:
                is_obscured = not element.is_enabled() or not visible
            except Exception:
                pass
            info = {
                "selector": selector,
                "bounding_box": box,
                "visible": visible,
                "is_obscured": is_obscured,
                "text": element.text_content() if hasattr(element, 'text_content') else '',
                "attributes": element.get_attribute('outerHTML') if hasattr(element, 'get_attribute') else '',
            }
            if self.debug:
                self.logger.info(f"Inspect element: {info}")
            return info
        except Exception as e:
            self.logger.error(f"Lỗi khi inspect element: {e}")
            return None
    
    def find_element_by_text(self, text, exact_match=False, highlight=True):
        """
        Tìm phần tử dựa trên nội dung văn bản
        
        Args:
            text (str): Văn bản cần tìm
            exact_match (bool): Khớp chính xác hay chỉ cần chứa
            highlight (bool): Highlight phần tử tìm thấy
            
        Returns:
            dict: Thông tin về phần tử và selector, hoặc None nếu không tìm thấy
        """
        self.wait_for_page_ready()
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return None
        
        try:
            # Tạo mã JavaScript để tìm phần tử
            js_code = f"""(text, exactMatch) => {{
                // Normalize text for comparison
                const normalizedText = text.trim().toLowerCase();
                
                // Function to check if an element contains the text
                const hasText = (element) => {{
                    const content = element.textContent?.trim().toLowerCase() || '';
                    return exactMatch ? content === normalizedText : content.includes(normalizedText);
                }};
                
                // Elements that commonly contain text
                const selectors = [
                    'button', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'span', 'div', 'li', 'td', 'th', 'label', 'input[type="submit"]',
                    'input[type="button"]', 'input[placeholder]', 'textarea[placeholder]'
                ];
                
                // Results to collect
                const results = [];
                
                // Check selectors one by one
                for (const selector of selectors) {{
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {{
                        const matchesText = hasText(element);
                        const matchesPlaceholder = element.placeholder && 
                            (exactMatch ? element.placeholder.toLowerCase() === normalizedText 
                                       : element.placeholder.toLowerCase().includes(normalizedText));
                        
                        if (matchesText || matchesPlaceholder) {{
                            // Get a unique selector for this element
                            let uniqueSelector = '';
                            
                            // Try ID
                            if (element.id) {{
                                uniqueSelector = '#' + element.id;
                            }} 
                            // Try name for inputs
                            else if (element.name) {{
                                uniqueSelector = element.tagName.toLowerCase() + '[name="' + element.name + '"]';
                            }}
                            // Try classes
                            else if (element.classList.length > 0) {{
                                const classes = Array.from(element.classList).join('.');
                                uniqueSelector = element.tagName.toLowerCase() + (classes ? '.' + classes : '');
                            }}
                            // Fallback to XPath
                            else {{
                                // Create a full XPath
                                let path = '';
                                let current = element;
                                while (current && current.nodeType === Node.ELEMENT_NODE) {{
                                    let index = 0;
                                    let sibling = current.previousSibling;
                                    while (sibling) {{
                                        if (sibling.nodeType === Node.ELEMENT_NODE && 
                                            sibling.tagName === current.tagName) {{
                                            index++;
                                        }}
                                        sibling = sibling.previousSibling;
                                    }}
                                    const tagName = current.tagName.toLowerCase();
                                    const pathIndex = (index > 0) ? '[' + (index + 1) + ']' : '';
                                    path = '/' + tagName + pathIndex + path;
                                    current = current.parentNode;
                                }}
                                uniqueSelector = 'xpath=/html' + path;
                            }}
                            
                            // Get bounding rect
                            const rect = element.getBoundingClientRect();
                            
                            // Add to results
                            results.push({{
                                selector: uniqueSelector,
                                text: element.textContent?.trim(),
                                tagName: element.tagName.toLowerCase(),
                                position: {{
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }},
                                isVisible: window.getComputedStyle(element).display !== 'none'
                            }});
                        }}
                    }}
                }}
                
                // Sort by position (elements at the top left appear first)
                results.sort((a, b) => {{
                    // Visible elements first
                    if (a.isVisible !== b.isVisible) return a.isVisible ? -1 : 1;
                    
                    // Then by vertical position
                    if (Math.abs(a.position.y - b.position.y) > 10) {{
                        return a.position.y - b.position.y;
                    }}
                    // Then by horizontal position
                    return a.position.x - b.position.x;
                }});
                
                // Return the top 5 results
                return results.slice(0, 5);
            }}"""
            
            # Thực thi mã JavaScript
            args = [text, exact_match]
            results = self.browser.page.evaluate(js_code, args)
            
            if not results or len(results) == 0:
                self.logger.warning(f"Không tìm thấy phần tử với văn bản: {text}")
                return None
            
            # Highlight kết quả tìm được nếu yêu cầu
            highlighted_results = []
            for i, result in enumerate(results):
                if highlight:
                    # Sử dụng các màu khác nhau cho từng kết quả
                    colors = ["red", "blue", "green", "purple", "orange"]
                    color = colors[i % len(colors)]
                    
                    # Thêm chi tiết từ highlight
                    element_info = self.highlight_element(
                        result["selector"], 
                        color=color, 
                        timeout=5000 + (i * 1000)  # Hiển thị lâu hơn cho từng phần tử tiếp theo
                    )
                    
                    if element_info:
                        result.update(element_info)
                
                highlighted_results.append(result)
            
            # In kết quả
            print(f"\n=== TÌM THẤY {len(highlighted_results)} PHẦN TỬ CHỨA VĂN BẢN: '{text}' ===")
            for i, result in enumerate(highlighted_results):
                print(f"{i+1}. {result['tagName']} - '{result['text']}'")
                print(f"   Selector: {result['selector']}")
                print(f"   Vị trí: {result['position']}")
                print()
            
            # Trả về phần tử đầu tiên (tốt nhất)
            return highlighted_results[0] if highlighted_results else None
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tìm phần tử theo văn bản '{text}': {str(e)}")
            return None
    
    def create_element_map(self, save_to_file=True):
        """
        Tạo bản đồ các phần tử tương tác trên trang
        
        Args:
            save_to_file (bool): Lưu bản đồ vào tệp
            
        Returns:
            dict: Bản đồ các phần tử
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return None
        
        try:
            # Mã JavaScript để tạo bản đồ phần tử
            js_code = """() => {
                // Bộ chọn cho các phần tử tương tác
                const interactiveSelectors = [
                    'a', 'button', 'input', 'select', 'textarea', 
                    '[role="button"]', '[role="link"]', '[role="checkbox"]',
                    '[role="menuitem"]', '[role="tab"]', '[role="combobox"]',
                    '[tabindex]:not([tabindex="-1"])'
                ];
                
                // Thu thập tất cả phần tử tương tác
                const allElements = [];
                const selector = interactiveSelectors.join(',');
                const elements = document.querySelectorAll(selector);
                
                // Kiểm tra hiển thị
                const isElementVisible = (element) => {
                    if (!element.getBoundingClientRect) return false;
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return !(
                        rect.width === 0 || 
                        rect.height === 0 || 
                        style.display === 'none' || 
                        style.visibility === 'hidden' ||
                        style.opacity === '0'
                    );
                };
                
                // Thu thập thông tin từng phần tử
                for (const element of elements) {
                    // Bỏ qua phần tử ẩn
                    if (!isElementVisible(element)) continue;
                    
                    // Lấy vị trí
                    const rect = element.getBoundingClientRect();
                    
                    // Thu thập text và thuộc tính
                    const text = element.textContent?.trim() || '';
                    const tagName = element.tagName.toLowerCase();
                    const attributes = {};
                    for (const attr of element.attributes) {
                        if (['id', 'class', 'name', 'type', 'placeholder', 'value', 'href', 'role', 'aria-label'].includes(attr.name)) {
                            attributes[attr.name] = attr.value;
                        }
                    }
                    
                    // Tạo selector
                    let selector = '';
                    if (element.id) {
                        selector = '#' + element.id;
                    } else if (element.name) {
                        selector = element.tagName.toLowerCase() + "[name='" + element.name + "']";
                    } else if (attributes['aria-label']) {
                        selector = element.tagName.toLowerCase() + "[aria-label='" + attributes['aria-label'] + "']";
                    } else if (element.classList.length > 0) {
                        const classes = Array.from(element.classList).join('.');
                        selector = element.tagName.toLowerCase() + (classes ? '.' + classes : '');
                    } else {
                        // XPath selector
                        let path = '';
                        let current = element;
                        while (current && current !== document.body) {
                            const parent = current.parentElement;
                            if (!parent) break;
                            
                            const siblings = parent.children;
                            let index = 0;
                            for (let i = 0; i < siblings.length; i++) {
                                if (siblings[i] === current) {
                                    index = i;
                                    break;
                                }
                            }
                            
                            const tagName = current.tagName.toLowerCase();
                            path = '/' + tagName + '[' + (index + 1) + ']' + path;
                            current = parent;
                        }
                        selector = 'xpath=/html/body' + path;
                    }
                    
                    // Xác định hành động phù hợp
                    let actions = [];
                    if (tagName === 'a' || tagName === 'button' || attributes['role'] === 'button') {
                        actions.push('click');
                    } else if (tagName === 'input') {
                        const inputType = attributes['type'] || 'text';
                        if (['text', 'email', 'password', 'number', 'search', 'tel', 'url'].includes(inputType)) {
                            actions.push('type');
                        } else if (['checkbox', 'radio'].includes(inputType)) {
                            actions.push('check');
                        } else if (inputType === 'submit') {
                            actions.push('click');
                        }
                    } else if (tagName === 'textarea') {
                        actions.push('type');
                    } else if (tagName === 'select') {
                        actions.push('select');
                    }
                    
                    // Mô tả phần tử
                    let description = '';
                    if (attributes['aria-label']) {
                        description = attributes['aria-label'];
                    } else if (attributes['placeholder']) {
                        description = 'ô ' + attributes['placeholder'];
                    } else if (text && text.length < 50) {
                        if (tagName === 'button' || attributes['role'] === 'button') {
                            description = 'nút ' + text;
                        } else if (tagName === 'a') {
                            description = 'liên kết ' + text;
                        } else if (tagName === 'input' && attributes['type'] === 'submit') {
                            description = 'nút ' + (text || attributes['value'] || 'gửi');
                        } else {
                            description = text;
                        }
                    } else if (attributes['name']) {
                        description = attributes['name'];
                    } else {
                        description = element.tagName.toLowerCase() + ' ' + (attributes['id'] || '');
                    }
                    
                    // Thêm vào danh sách
                    allElements.push({
                        selector,
                        tagName,
                        description,
                        text: text.substring(0, 100), // Giới hạn độ dài
                        attributes,
                        position: {"x": rect.left, "y": rect.top, "w": rect.width, "h": rect.height},
                        actions
                    });
                }
                
                // Sắp xếp theo vị trí từ trên xuống, trái sang phải
                allElements.sort((a, b) => {
                    // Nếu phần tử cách nhau ít nhất 50px theo chiều dọc
                    if (Math.abs(a.position.y - b.position.y) > 50) {
                        return a.position.y - b.position.y;
                    }
                    // Nếu gần nhau theo chiều dọc, sắp xếp theo chiều ngang
                    return a.position.x - b.position.x;
                });
                
                // Thông tin trang
                const pageInfo = {
                    title: document.title,
                    url: window.location.href,
                    elementsCount: allElements.length,
                    timestamp: new Date().toISOString()
                };
                
                return {
                    pageInfo,
                    elements: allElements
                };
            }"""
            
            # Thực thi mã JavaScript
            element_map = self.browser.page.evaluate(js_code)
            
            if not element_map:
                self.logger.warning("Không thể tạo bản đồ phần tử")
                return None
            
            # Hiển thị thông tin tóm tắt
            print(f"\n=== BẢN ĐỒ PHẦN TỬ: {element_map['pageInfo']['title']} ===")
            print(f"URL: {element_map['pageInfo']['url']}")
            print(f"Số phần tử tương tác: {element_map['pageInfo']['elementsCount']}")
            print("\nCác phần tử chính:")
            
            # Hiển thị các phần tử quan trọng (tối đa 10)
            for i, element in enumerate(element_map['elements'][:10]):
                actions = ', '.join(element['actions']) if element['actions'] else 'không có'
                print(f"{i+1}. {element['description']} ({element['tagName']}) - Hành động: {actions}")
            
            if len(element_map['elements']) > 10:
                print(f"... và {len(element_map['elements']) - 10} phần tử khác.")
            
            # Lưu vào tệp nếu yêu cầu
            if save_to_file:
                timestamp = int(time.time())
                file_path = self.screenshots_dir / f"element_map_{timestamp}.json"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(element_map, f, ensure_ascii=False, indent=2)
                
                print(f"\nĐã lưu bản đồ phần tử vào: {file_path}")
            
            return element_map
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo bản đồ phần tử: {str(e)}")
            return None
            
    def clear_highlights(self):
        """Xóa tất cả highlights đã tạo"""
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Xóa tất cả highlight elements
            for highlight_id in self.highlight_ids:
                js_code = f"""(highlightId) => {{
                    const highlightElement = document.getElementById(highlightId);
                    if (highlightElement) {{
                        document.body.removeChild(highlightElement);
                        return true;
                    }}
                    return false;
                }}"""
                
                self.browser.page.evaluate(js_code, highlight_id)
            
            # Xóa danh sách
            self.highlight_ids = []
            
            self.logger.info("Đã xóa tất cả highlights")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xóa highlights: {str(e)}")
            return False

    def find_element_advanced(self, description, context=None, vision=True, ocr=True, top_n=3, debug=False):
        """
        Nhận diện element chuyên nghiệp: kết hợp heuristic, AI, vision/OCR. Trả về top-N element phù hợp nhất.
        """
        candidates = []
        # 1. Heuristic: tìm theo text, label, aria-label, placeholder, role, ...
        candidates.extend(self._find_by_heuristic(description, context, debug=debug))
        # 2. AI: nếu chưa đủ tự tin, gọi AI với prompt tối ưu, kèm context, DOM subtree
        if not self._is_confident(candidates):
            candidates.extend(self._find_by_ai(description, context, debug=debug))
        # 3. Vision/OCR: nếu vẫn chưa đủ, dùng OCR nhận diện text trên ảnh, map với DOM
        if (vision or ocr) and HAS_OCR and not self._is_confident(candidates):
            candidates.extend(self._find_by_vision(description, debug=debug))
        # 4. Fallback: thử lại với các mô tả gần đúng hơn nếu chưa đủ tự tin
        if not self._is_confident(candidates):
            # Thử lại với mô tả rút gọn hoặc loại bỏ dấu, v.v.
            short_desc = description.split()[0] if description and len(description.split()) > 1 else description
            if short_desc and short_desc != description:
                candidates.extend(self._find_by_heuristic(short_desc, context, debug=debug))
        # 5. Chấm điểm, xếp hạng
        ranked = self._score_and_rank(candidates, description, context)
        # 6. Highlight và log nếu debug
        if debug:
            for el in ranked[:top_n]:
                self.highlight_element(el['selector'], color="orange", timeout=3000)
                self.logger.info(f"[ADVANCED] {el}")
        if not ranked:
            self.logger.warning(f"[ElementInspector] Không tìm thấy candidate nào cho mô tả: {description}")
        return ranked[:top_n]

    def _find_by_heuristic(self, description, context=None, debug=False):
        """Tìm element theo text, label, aria-label, placeholder, role, ..."""
        results = []
        if not self.browser.page:
            return results
        desc = description.lower().strip()
        # Tìm theo text, aria-label, placeholder, role
        js_code = f"""(desc) => {{
            const matches = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {{
                const text = el.textContent?.trim().toLowerCase() || '';
                const aria = el.getAttribute('aria-label')?.toLowerCase() || '';
                const placeholder = el.getAttribute('placeholder')?.toLowerCase() || '';
                const role = el.getAttribute('role')?.toLowerCase() || '';
                if (text.includes(desc) || aria.includes(desc) || placeholder.includes(desc) || role.includes(desc)) {{
                    let selector = '';
                    if (el.id) selector = '#' + el.id;
                    else if (el.name) selector = el.tagName.toLowerCase() + "[name='" + el.name + "']";
                    else if (el.classList.length > 0) selector = el.tagName.toLowerCase() + (Array.from(el.classList).length > 0 ? '.' + Array.from(el.classList).join('.') : '');
                    else selector = el.tagName.toLowerCase();
                    const rect = el.getBoundingClientRect();
                    matches.push({
                        selector,
                        text,
                        aria,
                        placeholder,
                        role,
                        position: {"x": rect.left, "y": rect.top, "w": rect.width, "h": rect.height},
                        visible: window.getComputedStyle(el).display !== 'none',
                        reason: 'heuristic',
                    });
                }}
            }}
            return matches;
        }}"""
        found = self.browser.page.evaluate(js_code, [desc])
        for el in found:
            el['score'] = 0.7
            results.append(el)
        if debug:
            self.logger.info(f"[HEURISTIC] Found {len(results)} candidates")
        return results

    def _find_by_ai(self, description, context=None, debug=False):
        """Tìm element bằng AI (nếu có)"""
        results = []
        if hasattr(self.browser, 'ai_element_finder') and self.browser.ai_element_finder:
            selector = self.browser.ai_element_finder.find_element_by_description(description, context)
            if selector:
                el = {'selector': selector, 'score': 0.9, 'reason': 'ai', 'visible': True, 'position': {}, 'text': description}
                results.append(el)
                if debug:
                    self.logger.info(f"[AI] Found selector: {selector}")
        return results

    def _find_by_vision(self, description, debug=False):
        """Tìm element bằng OCR trên ảnh chụp màn hình, map với DOM (nếu có pytesseract, opencv)"""
        results = []
        if not HAS_OCR or not self.browser.page:
            return results
        # Chụp ảnh màn hình
        screenshot_path = "temp_ocr_screenshot.png"
        self.browser.page.screenshot(path=screenshot_path, full_page=True)
        img = cv2.imread(screenshot_path)
        if img is None:
            return results
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ocr_result = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, lang='vie+eng')
        desc = description.lower().strip()
        for i, text in enumerate(ocr_result['text']):
            if desc in text.lower():
                (x, y, w, h) = (ocr_result['left'][i], ocr_result['top'][i], ocr_result['width'][i], ocr_result['height'][i])
                # Map vị trí với DOM (gần đúng)
                js_code = f"""(x, y, w, h) => {{
                    const all = document.querySelectorAll('*');
                    for (const el of all) {{
                        const rect = el.getBoundingClientRect();
                        if (Math.abs(rect.left-x)<20 && Math.abs(rect.top-y)<20 && Math.abs(rect.width-w)<30 && Math.abs(rect.height-h)<30) {{
                            let selector = '';
                            if (el.id) selector = '#' + el.id;
                            else if (el.name) selector = el.tagName.toLowerCase() + "[name='" + el.name + "']";
                            else if (el.classList.length > 0) selector = el.tagName.toLowerCase() + (Array.from(el.classList).length > 0 ? '.' + Array.from(el.classList).join('.') : '');
                            else selector = el.tagName.toLowerCase();
                            return selector;
                        }}
                    }}
                    return null;
                }}"""
                selector = self.browser.page.evaluate(js_code, [x, y, w, h])
                if selector:
                    el = {'selector': selector, 'score': 0.6, 'reason': 'ocr', 'visible': True, 'position': {"x": x, "y": y, "w": w, "h": h}, 'text': text}
                    results.append(el)
                    if debug:
                        self.logger.info(f"[OCR] Found selector: {selector} for text: {text}")
        return results

    def _is_confident(self, candidates):
        # Nếu có candidate score >= 0.85 thì tự tin
        return any(c.get('score', 0) >= 0.85 for c in candidates)

    def _score_and_rank(self, candidates, description, context=None):
        # Chấm điểm lại dựa trên độ khớp text, lý do, vị trí, v.v.
        desc = description.lower().strip()
        for el in candidates:
            score = el.get('score', 0.5)
            # Ưu tiên lý do AI > heuristic > ocr
            if el.get('reason') == 'ai':
                score += 0.15
            if el.get('reason') == 'heuristic':
                score += 0.05
            if el.get('reason') == 'ocr':
                score += 0.01
            # Ưu tiên text khớp chính xác
            if desc == el.get('text', '').lower():
                score += 0.1
            # Ưu tiên element hiển thị
            if el.get('visible'):
                score += 0.05
            el['score'] = min(score, 1.0)
        # Sắp xếp theo điểm số giảm dần
        return sorted(candidates, key=lambda x: -x['score'])

    def move_and_click_with_cursor_icon(self, selector, cursor_icon_url=None, click_delay=0.2, highlight=True, description=None, action="click", type_text=None, type_delay=0.08):
        """
        Di chuyển chuột đến field, hiển thị icon chuột ảo, thực hiện click thật sự hoặc focus để nhập liệu.
        Args:
            selector (str): CSS selector hoặc XPath
            cursor_icon_url (str, optional): Đường dẫn icon chuột (PNG/SVG). Nếu None dùng icon mặc định.
            click_delay (float): Thời gian chờ trước khi click (giây)
            highlight (bool): Có highlight field không
            description (str, optional): Mô tả phần tử để fallback AI/heuristic nếu selector thất bại
            action (str): 'click' hoặc 'type'
            type_text (str, optional): Chuỗi cần nhập nếu action='type'
            type_delay (float): Độ trễ giữa các ký tự khi nhập (giây)
        Returns:
            bool: True nếu thành công
        """
        self.wait_for_page_ready()
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        try:
            found = False
            for attempt in range(3):
                box = self.browser.page.eval_on_selector(selector, "el => el.getBoundingClientRect()")
                # Kiểm tra visible, enabled, không bị che
                is_visible = self.browser.page.eval_on_selector(selector, "el => { const rect = el.getBoundingClientRect(); const style = window.getComputedStyle(el); return !(rect.width === 0 || rect.height === 0 || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0'); }")
                is_enabled = self.browser.page.eval_on_selector(selector, "el => !el.disabled")
                is_obscured = self.browser.page.eval_on_selector(selector, "el => { const rect = el.getBoundingClientRect(); const x = rect.left + rect.width/2; const y = rect.top + rect.height/2; const elAtPoint = document.elementFromPoint(x, y); return elAtPoint !== el; }")
                if box and is_visible and is_enabled and not is_obscured:
                    found = True
                    break
                # Nếu không visible, thử scroll vào view
                self.browser.page.eval_on_selector(selector, "el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
                time.sleep(0.5)
            if not found:
                self.logger.error(f"Không lấy được vị trí phần tử hoặc element bị che/ẩn: {selector}. Thử fallback AI/heuristic nếu có mô tả...")
                # Fallback AI/heuristic nếu có mô tả
                if description and hasattr(self.browser, 'ai_element_finder') and self.browser.ai_element_finder:
                    new_selector = self.browser.ai_element_finder.find_element_by_description(description)
                    if new_selector:
                        self.logger.info(f"AI/heuristic tìm được selector gần đúng: {new_selector}")
                        selector = new_selector
                        box = self.browser.page.eval_on_selector(selector, "el => el.getBoundingClientRect()")
                        is_visible = self.browser.page.eval_on_selector(selector, "el => { const rect = el.getBoundingClientRect(); const style = window.getComputedStyle(el); return !(rect.width === 0 || rect.height === 0 || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0'); }")
                        is_enabled = self.browser.page.eval_on_selector(selector, "el => !el.disabled")
                        is_obscured = self.browser.page.eval_on_selector(selector, "el => { const rect = el.getBoundingClientRect(); const x = rect.left + rect.width/2; const y = rect.top + rect.height/2; const elAtPoint = document.elementFromPoint(x, y); return elAtPoint !== el; }")
                        if not (box and is_visible and is_enabled and not is_obscured):
                            self.logger.error(f"AI cũng không tìm thấy element hợp lệ: {selector}")
                            self._log_nearby_buttons()
                            return False
                    else:
                        self.logger.error("AI/heuristic không tìm được selector phù hợp.")
                        self._log_nearby_buttons()
                        return False
                else:
                    self._log_nearby_buttons()
                    return False
            x = box['x'] + box['width'] // 2
            y = box['y'] + box['height'] // 2
            # Animation di chuyển chuột từ từ
            current_pos = self.browser.page.mouse._position if hasattr(self.browser.page.mouse, '_position') else {'x': 0, 'y': 0}
            steps = 15
            dx = (x - current_pos['x']) / steps
            dy = (y - current_pos['y']) / steps
            for i in range(steps):
                self.browser.page.mouse.move(current_pos['x'] + dx*i, current_pos['y'] + dy*i)
                time.sleep(0.01)
            self.browser.page.mouse.move(x, y)
            # Hiển thị icon chuột ảo
            js_icon = f'''
                (x, y, iconUrl) => {{
                    let icon = document.getElementById('virtual-cursor-icon');
                    if (!icon) {{
                        icon = document.createElement('img');
                        icon.id = 'virtual-cursor-icon';
                        icon.style.position = 'fixed';
                        icon.style.zIndex = 2147483647;
                        icon.style.width = '32px';
                        icon.style.height = '32px';
                        icon.style.pointerEvents = 'none';
                        icon.style.userSelect = 'none';
                        icon.style.transition = 'left 0.1s, top 0.1s';
                        document.body.appendChild(icon);
                        console.log('Đã thêm icon chuột vào DOM');
                    }}
                    icon.src = iconUrl || 'https://cdn-icons-png.flaticon.com/512/892/892692.png';
                    icon.style.left = (x-16) + 'px';
                    icon.style.top = (y-16) + 'px';
                    icon.style.display = 'block';
                    icon.style.opacity = '1';
                }}
            '''
            self.browser.page.evaluate(js_icon, [x, y, cursor_icon_url])
            if highlight:
                self.highlight_element(selector, color="blue", timeout=1500, take_screenshot=False)
            # Chụp ảnh màn hình trước khi click
            self.browser.page.screenshot(path="before_click.png")
            time.sleep(click_delay)
            if action == "click":
                self.browser.page.mouse.click(x, y)
            elif action == "type":
                self.browser.page.mouse.click(x, y)  # Click để focus vào field
                time.sleep(0.2)
                if type_text:
                    for ch in type_text:
                        self.browser.page.keyboard.insert_text(ch)
                        time.sleep(type_delay)
                # Sau khi nhập liệu, thử submit bằng Enter nếu là form hoặc input search
                try:
                    is_form = self.browser.page.eval_on_selector(selector, "el => { let p=el.parentElement; while(p){if(p.tagName && p.tagName.toLowerCase()==='form') return true; p=p.parentElement;} return false; }")
                    input_type = self.browser.page.eval_on_selector(selector, "el => el.type ? el.type.toLowerCase() : ''")
                    if is_form or input_type in ['search', 'text', 'email', 'password', 'number', 'url']:
                        self.browser.page.keyboard.press('Enter')
                        self.logger.info(f"Đã thử gửi phím Enter để submit form/input sau khi nhập liệu tại {selector}")
                except Exception as e:
                    self.logger.warning(f"Không thể gửi Enter sau khi nhập liệu: {e}")
            # Chụp ảnh màn hình sau khi click
            self.browser.page.screenshot(path="after_click.png")
            # Ẩn icon chuột ảo sau khi thao tác
            js_hide = """
                () => {
                    let icon = document.getElementById('virtual-cursor-icon');
                    if (icon) icon.style.display = 'none';
                }
            """
            self.browser.page.evaluate(js_hide)
            self.logger.info(f"Đã move & {action} với icon chuột tại {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi move_and_click_with_cursor_icon: {e}")
            return False

    def _log_nearby_buttons(self):
        try:
            js_code = """
                () => {
                    const btns = Array.from(document.querySelectorAll('button, input[type=\'button\'], input[type=\'submit\']'));
                    return btns.map(el => ({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className,
                        text: el.textContent?.trim(),
                        selector: el.id ? ('#'+el.id) : (el.name ? el.tagName.toLowerCase()+"[name='"+el.name+"']" : '')
                    }));
                }
            """
            btns = self.browser.page.evaluate(js_code)
            self.logger.info(f"Các button gần đúng trên trang: {btns}")
        except Exception as e:
            self.logger.warning(f"Không thể log các button gần đúng: {e}")

    def highlight_all_interactive_elements(self, show_tooltip=True, show_index=True, highlight_color="#0073b1", hover_color="#ff9800", border_radius=8):
        """
        Highlight tất cả các phần tử có thể tương tác trên trang với giao diện chuyên nghiệp.
        Args:
            show_tooltip (bool): Hiển thị tooltip chức năng khi hover
            show_index (bool): Hiển thị số thứ tự ở góc trái dưới
            highlight_color (str): Màu viền mặc định
            hover_color (str): Màu viền khi hover
            border_radius (int): Độ bo góc viền
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        try:
            js_code = f'''
                (() => {{
                    // Xóa highlight cũ nếu có
                    document.querySelectorAll('.interactive-highlight, .interactive-tooltip, .interactive-index').forEach(e => e.remove());
                    // Chọn các phần tử tương tác
                    const selectors = [
                        'a', 'button', 'input', 'select', 'textarea',
                        '[role="button"]', '[role="link"]', '[role="checkbox"]',
                        '[role="menuitem"]', '[role="tab"]', '[role="combobox"]',
                        '[tabindex]:not([tabindex="-1"])'
                    ];
                    const elements = Array.from(document.querySelectorAll(selectors.join(',')));
                    let idx = 1;
                    elements.forEach(el => {{
                        // Bỏ qua phần tử ẩn hoặc disabled
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || el.disabled) return;
                        // Thêm class highlight
                        el.classList.add('interactive-highlight');
                        el.style.boxSizing = 'border-box';
                        el.style.border = '2.5px solid {highlight_color}';
                        el.style.borderRadius = '{border_radius}px';
                        el.style.boxShadow = '0 0 10px {highlight_color}55';
                        el.style.transition = 'border 0.2s, box-shadow 0.2s';
                        el.setAttribute('data-interactive-index', idx);
                        // Số thứ tự
                        if ({str(show_index).lower()}) {{
                            let indexDiv = document.createElement('div');
                            indexDiv.className = 'interactive-index';
                            indexDiv.textContent = idx;
                            indexDiv.style.position = 'absolute';
                            indexDiv.style.left = '6px';
                            indexDiv.style.bottom = '6px';
                            indexDiv.style.background = '#111';
                            indexDiv.style.color = '#fff';
                            indexDiv.style.fontSize = '13px';
                            indexDiv.style.borderRadius = '4px';
                            indexDiv.style.padding = '1px 7px';
                            indexDiv.style.opacity = '0.88';
                            indexDiv.style.zIndex = '9999';
                            indexDiv.style.pointerEvents = 'none';
                            indexDiv.style.fontWeight = 'bold';
                            indexDiv.style.boxShadow = '0 1px 4px #0002';
                            el.style.position = 'relative';
                            el.appendChild(indexDiv);
                        }}
                        // Tooltip
                        if ({str(show_tooltip).lower()}) {{
                            el.addEventListener('mouseenter', function(e) {{
                                let tooltip = document.createElement('div');
                                tooltip.className = 'interactive-tooltip';
                                let label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') || el.innerText?.trim() || el.value || 'Element';
                                if (label.length > 40) label = label.slice(0, 40) + '...';
                                tooltip.textContent = label;
                                tooltip.style.position = 'fixed';
                                let rect = el.getBoundingClientRect();
                                tooltip.style.left = (rect.left + window.scrollX + rect.width/2 - 60) + 'px';
                                tooltip.style.top = (rect.top + window.scrollY - 38) + 'px';
                                tooltip.style.background = '#222';
                                tooltip.style.color = '#fff';
                                tooltip.style.padding = '6px 16px';
                                tooltip.style.borderRadius = '7px';
                                tooltip.style.fontSize = '15px';
                                tooltip.style.zIndex = '99999';
                                tooltip.style.whiteSpace = 'nowrap';
                                tooltip.style.boxShadow = '0 2px 12px #0003';
                                tooltip.style.pointerEvents = 'none';
                                tooltip.style.fontWeight = '500';
                                document.body.appendChild(tooltip);
                                el._tooltip = tooltip;
                                // Hiệu ứng hover
                                el.style.border = '2.5px solid {hover_color}';
                                el.style.boxShadow = '0 0 16px {hover_color}99';
                            }});
                            el.addEventListener('mouseleave', function(e) {{
                                if (el._tooltip) {{
                                    el._tooltip.remove();
                                    el._tooltip = null;
                                }}
                                el.style.border = '2.5px solid {highlight_color}';
                                el.style.boxShadow = '0 0 10px {highlight_color}55';
                            }});
                        }}
                        idx++;
                    }});
                }})()
            '''
            self.browser.page.evaluate(js_code)
            self.logger.info("Đã highlight tất cả các element có thể tương tác với giao diện chuyên nghiệp.")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi highlight all interactive elements: {e}")
            return False
