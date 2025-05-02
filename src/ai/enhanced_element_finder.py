"""
Enhanced Element Finder Module
Tìm kiếm phần tử sử dụng sự kết hợp của AI và PageObserver để phân tích HTML realtime
"""

import os
from pathlib import Path
import time
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import json
import base64
import traceback
import re
from bs4 import BeautifulSoup

# Import phiên bản fixed
from .page_observer.page_observer_fixed import PageObserverFixed

# Đảm bảo biến môi trường được tải
load_dotenv()

class EnhancedElementFinder:
    """
    Phiên bản nâng cao của trình tìm kiếm phần tử kết hợp theo dõi trang realtime
    """
    
    def __init__(self, browser_controller, use_page_observer=True, debug=False):
        """
        Khởi tạo Enhanced Element Finder
        
        Args:
            browser_controller: Controller trình duyệt
            use_page_observer (bool): Kích hoạt theo dõi trang realtime
            debug (bool): Kích hoạt mode debug
        """
        # Cấu hình logging
        try:
            from utils.logging_utils import get_logger
            self.logger = get_logger("EnhancedElementFinder")
        except ImportError:
            import logging
            self.logger = logging.getLogger("EnhancedElementFinder")
        
        self.browser = browser_controller
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Khởi tạo OpenAI API nếu có khóa
        if self.openai_api_key:
            # Khởi tạo OpenAI client với API mới
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                self.logger.error(f"Lỗi khởi tạo OpenAI client: {str(e)}")
        
        # Khởi tạo PageObserver và HTMLAnalyzer nếu được yêu cầu
        self.use_page_observer = use_page_observer
        self.debug = debug
        
        # Thư mục lưu trữ cache
        self.cache_dir = Path("data/element_finder_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if self.use_page_observer:
            try:
                from .page_observer.html_analyzer import HTMLAnalyzer
                self.html_analyzer = HTMLAnalyzer(use_ai=True)
                self.page_observer = PageObserverFixed(browser_controller, self.html_analyzer, debug=debug)
                self.page_observer.start()
                if self.debug:
                    self.logger.info("Đã khởi động PageObserverFixed (debug mode)")
            except Exception as e:
                self.logger.error(f"Không thể khởi tạo PageObserver/HTMLAnalyzer: {str(e)}")
                if self.debug:
                    self.logger.error(traceback.format_exc())
                self.html_analyzer = None
                self.page_observer = None
                self.use_page_observer = False
        else:
            self.html_analyzer = None
            self.page_observer = None
            self.logger.info("PageObserver không được kích hoạt")
        
        # Lưu trữ AI call cache
        self._ai_call_count = {}
        self._selector_cache = {}
        
        self.logger.info("Enhanced Element Finder đã được khởi tạo")
    
    def find_element_by_description(self, description, context=None):
        """
        Tìm phần tử dựa trên mô tả
        
        Args:
            description (str): Mô tả phần tử
            context (str, optional): Bối cảnh bổ sung
            
        Returns:
            str: CSS selector hoặc XPath, hoặc None nếu không tìm thấy
        """
        if not self.browser or not hasattr(self.browser, 'page') or not self.browser.page:
            self.logger.error("Browser not started. Please start browser first.")
            return None
        
        try:
            url = self.browser.get_current_url() if hasattr(self.browser, 'get_current_url') else ""
            norm_desc = description.strip().lower() if description else ""
            norm_context = context.strip().lower() if context else ""
            cache_key = f"{url}::{norm_desc}::{norm_context}"
            
            # Kiểm tra cache nội bộ trước
            if cache_key in self._selector_cache:
                selector = self._selector_cache[cache_key]
                self.logger.info(f"[EnhancedElementFinder] Đã tìm thấy phần tử từ cache: {selector}")
                
                # Kiểm tra xem selector có tồn tại không
                if self._validate_selector(selector):
                    return selector
                else:
                    # Xóa selector không hợp lệ khỏi cache
                    del self._selector_cache[cache_key]
                    self.logger.info(f"[EnhancedElementFinder] Đã xóa selector không hợp lệ khỏi cache: {selector}")
            
            # 1. Thử tìm phần tử bằng PageObserver nếu được kích hoạt
            if self.use_page_observer and self.page_observer:
                self.logger.info(f"[EnhancedElementFinder] Đang tìm phần tử qua PageObserver với mô tả: {description}")
                try:
                    selector = self.page_observer.find_element_by_description(description, context)
                    if selector:
                        self.logger.info(f"[EnhancedElementFinder] Đã tìm thấy phần tử với PageObserver: {selector}")
                        self._selector_cache[cache_key] = selector
                        return selector
                except Exception as e:
                    self.logger.warning(f"[EnhancedElementFinder] Lỗi khi tìm phần tử qua PageObserver: {str(e)}")
                    if self.debug:
                        self.logger.warning(traceback.format_exc())
            
            # 2. Tìm bằng các heuristic
            heuristic_selector = self._find_by_heuristic(description, context)
            if heuristic_selector:
                self.logger.info(f"[EnhancedElementFinder] Đã tìm thấy phần tử bằng heuristic: {heuristic_selector}")
                self._selector_cache[cache_key] = heuristic_selector
                return heuristic_selector
            
            # 3. Nếu không tìm thấy, chụp ảnh và dùng phương pháp truyền thống
            screenshot_path = None
            try:
                screenshot_path = self.browser.take_screenshot("temp_screenshot_for_ai.png")
            except Exception as screenshot_e:
                self.logger.warning(f"[EnhancedElementFinder] Không thể chụp ảnh màn hình: {str(screenshot_e)}")
            
            # Lấy HTML của trang
            try:
                html_content = self.browser.page.content()
            except Exception as html_e:
                self.logger.warning(f"[EnhancedElementFinder] Không thể lấy HTML của trang: {str(html_e)}")
                html_content = "<html><body>Error getting page content</body></html>"
            
            # Chuẩn bị prompt cho AI (tối ưu chỉ lấy phần HTML quan trọng)
            prompt = self._prepare_prompt(description, html_content, context)
            
            # Giới hạn số lần gọi AI cho 1 mô tả
            if self._ai_call_count.get(cache_key, 0) > 3:
                if self.debug:
                    self.logger.warning(f"[EnhancedElementFinder] Đã vượt quá số lần gọi AI cho mô tả: {description}")
                return None
            
            # Gọi API OpenAI để phân tích
            selectors = self._analyze_with_ai(prompt, screenshot_path)
            self._ai_call_count[cache_key] = self._ai_call_count.get(cache_key, 0) + 1
            
            # Thử từng selector được đề xuất
            if selectors:
                result = self._validate_selectors(selectors)
                if result:
                    self._selector_cache[cache_key] = result
                    self.logger.info(f"[EnhancedElementFinder] AI tìm thấy selector: {result}")
                    return result
            
            # 4. Thử phương pháp fallback với XPath thay vì CSS selector
            fallback_selector = self._fallback_search(description)
            if fallback_selector:
                self._selector_cache[cache_key] = fallback_selector
                self.logger.info(f"[EnhancedElementFinder] Fallback tìm thấy selector: {fallback_selector}")
                return fallback_selector
            
            # 5. Thử OCR nếu có
            if hasattr(self.browser, 'element_inspector') and self.browser.element_inspector:
                try:
                    candidates = self.browser.element_inspector.find_element_advanced(description, context=context, vision=True, ocr=True, top_n=1, debug=self.debug)
                    if candidates and len(candidates) > 0:
                        selector = candidates[0]['selector']
                        self._selector_cache[cache_key] = selector
                        self.logger.info(f"[EnhancedElementFinder] OCR tìm thấy selector: {selector}")
                        return selector
                except Exception as e:
                    self.logger.debug(f"OCR fallback error: {str(e)}")
            
            self.logger.warning(f"[EnhancedElementFinder] Không tìm thấy selector cho mô tả: {description}")
            return None
        except Exception as e:
            self.logger.error(f"[EnhancedElementFinder] Lỗi khi tìm phần tử theo mô tả: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return None
    
    def _find_by_heuristic(self, description, context=None):
        """
        Tìm phần tử bằng các phương pháp heuristic
        
        Args:
            description (str): Mô tả phần tử
            context (str, optional): Bối cảnh bổ sung
            
        Returns:
            str: Selector nếu tìm thấy, None nếu không
        """
        try:
            # Chuẩn hóa mô tả
            desc_lower = description.lower().strip()
            
            # JavaScript để tìm phần tử dựa trên text, placeholder, aria-label, alt, title
            js_code = f"""(description) => {{
                // Danh sách kết quả, mỗi phần tử là [selector, điểm số]
                const results = [];
                
                // 1. Tìm phần tử có text chính xác như mô tả
                const findByText = (exactMatch) => {{
                    const elements = Array.from(document.querySelectorAll('*'));
                    for (const element of elements) {{
                        const elementText = element.textContent?.trim().toLowerCase() || '';
                        const matching = exactMatch ? elementText === description : elementText.includes(description);
                        if (matching) {{
                            // Tính điểm phù hợp
                            let score = exactMatch ? 10 : 5;
                            
                            // Ưu tiên các phần tử tương tác
                            if (element.tagName === 'BUTTON' || element.tagName === 'A' || 
                                element.tagName === 'INPUT' || element.tagName === 'SELECT') {{
                                score += 3;
                            }}
                            
                            // Ưu tiên phần tử hiện thị
                            const style = window.getComputedStyle(element);
                            if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {{
                                score += 2;
                            }}
                            
                            // Tạo selector
                            let selector = '';
                            if (element.id) {{
                                selector = '#' + element.id;
                                score += 2;  // Ưu tiên selector ID
                            }} else if (element.className && typeof element.className === 'string' && element.className.trim()) {{
                                const classes = element.className.trim().split(/\\s+/);
                                selector = element.tagName.toLowerCase() + '.' + classes.join('.');
                            }} else {{
                                const tag = element.tagName.toLowerCase();
                                if (exactMatch && elementText) {{
                                    selector = `${tag}:contains("${elementText}")`;
                                    if (selector.includes("'")) selector = `${tag}`;
                                }} else {{
                                    selector = tag;
                                }}
                            }}
                            
                            results.push([selector, score, element]);
                        }}
                    }}
                }};
                
                // 2. Tìm phần tử dựa trên các thuộc tính
                const findByAttributes = () => {{
                    const attributeSelectors = [
                        `[placeholder*="${description}"]`,
                        `[aria-label*="${description}"]`,
                        `[alt*="${description}"]`,
                        `[title*="${description}"]`,
                        `[name*="${description}"]`
                    ];
                    
                    for (const selector of attributeSelectors) {{
                        try {{
                            const elements = document.querySelectorAll(selector);
                            for (const element of elements) {{
                                const score = 8;  // Điểm cao vì đây là thuộc tính cụ thể
                                results.push([selector, score, element]);
                            }}
                        }} catch (e) {{
                            // Bỏ qua selector không hợp lệ
                        }}
                    }}
                }};
                
                // 3. Tìm phần tử dựa trên nhãn
                const findByLabel = () => {{
                    const labels = document.querySelectorAll('label');
                    for (const label of labels) {{
                        const labelText = label.textContent?.trim().toLowerCase() || '';
                        if (labelText.includes(description)) {{
                            const forAttr = label.getAttribute('for');
                            if (forAttr) {{
                                const target = document.getElementById(forAttr);
                                if (target) {{
                                    results.push([`#${forAttr}`, 9, target]);
                                }}
                            }}
                        }}
                    }}
                }};
                
                // Thực hiện tìm kiếm
                findByText(true);   // Tìm chính xác
                findByText(false);  // Tìm gần đúng
                findByAttributes();
                findByLabel();
                
                // Sắp xếp kết quả theo điểm số
                results.sort((a, b) => b[1] - a[1]);
                
                // Trả về các selector hợp lệ
                return results.slice(0, 5).map(r => r[0]);
            }}"""
            
            try:
                selectors = self.browser.page.evaluate(js_code, desc_lower)
                if selectors and len(selectors) > 0:
                    # Kiểm tra từng selector
                    for selector in selectors:
                        if self._validate_selector(selector):
                            return selector
            except Exception as js_e:
                self.logger.warning(f"Lỗi khi thực thi JavaScript heuristic: {str(js_e)}")
            
            return None
        except Exception as e:
            self.logger.warning(f"Lỗi khi tìm phần tử bằng heuristic: {str(e)}")
            return None
    
    def _prepare_prompt(self, description, html_content, context=None):
        """Chuẩn bị prompt cho AI - tối ưu token"""
        
        try:
            # 1. Trích xuất thông tin quan trọng từ HTML thay vì gửi toàn bộ HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Lấy tiêu đề trang
            page_title = soup.title.string if soup.title else ""
            page_url = self.browser.get_current_url() if hasattr(self.browser, 'get_current_url') else ""
            
            # Trích xuất các phần tử tương tác quan trọng
            important_elements = []
            
            # Thu thập forms
            forms = soup.find_all("form", limit=3)
            for form in forms:
                form_info = f"FORM: id='{form.get('id', '')}' class='{' '.join(form.get('class', []))}'"
                important_elements.append(form_info)
                
                # Thu thập inputs trong form
                for input_elem in form.find_all(["input", "button", "select", "textarea"], limit=5):
                    input_info = f"  {input_elem.name} type='{input_elem.get('type', '')}' id='{input_elem.get('id', '')}' name='{input_elem.get('name', '')}' placeholder='{input_elem.get('placeholder', '')}'"
                    important_elements.append(input_info)
            
            # Thu thập buttons
            buttons = soup.find_all("button", limit=10)
            for button in buttons:
                button_text = button.get_text(strip=True)[:50] if button.get_text(strip=True) else ""
                button_info = f"BUTTON: text='{button_text}' id='{button.get('id', '')}' class='{' '.join(button.get('class', []) if hasattr(button.get('class', []), '__iter__') else [])}'"
                important_elements.append(button_info)
            
            # Thu thập inputs
            inputs = soup.find_all("input", limit=10)
            for input_elem in inputs:
                input_info = f"INPUT: type='{input_elem.get('type', '')}' id='{input_elem.get('id', '')}' name='{input_elem.get('name', '')}' placeholder='{input_elem.get('placeholder', '')}'"
                important_elements.append(input_info)
            
            # Thu thập links đáng chú ý
            links = soup.find_all("a", limit=10)
            for link in links:
                link_text = link.get_text(strip=True)[:50] if link.get_text(strip=True) else ""
                if link_text:
                    link_info = f"LINK: text='{link_text}' href='{link.get('href', '')}' id='{link.get('id', '')}'"
                    important_elements.append(link_info)
            
            # Tìm phần tử có text tương tự mô tả
            desc_lower = description.lower() if description else ""
            matching_elements = []
            
            if desc_lower:
                for elem in soup.find_all(text=lambda text: text and desc_lower in text.lower()):
                    parent = elem.parent
                    if parent and parent.name:
                        elem_info = f"MATCHED: <{parent.name}> text='{elem.strip()[:50] if hasattr(elem, 'strip') else ''}' id='{parent.get('id', '')}' class='{' '.join(parent.get('class', []) if hasattr(parent.get('class', []), '__iter__') else [])}'"
                        matching_elements.append(elem_info)
                        if len(matching_elements) >= 5:
                            break
            
            # HTML tối ưu cho việc tìm phần tử thay vì HTML đầy đủ
            html_summary = "\n".join(important_elements + ["", "MATCHED ELEMENTS:"] + matching_elements)
            
        except Exception as e:
            self.logger.warning(f"Lỗi khi phân tích HTML: {str(e)}")
            if self.debug:
                self.logger.warning(traceback.format_exc())
            # Fallback: cắt giảm HTML thông thường
            max_html_length = 8000  # Giảm xuống để tiết kiệm token
            html_summary = html_content[:max_html_length]
            if len(html_content) > max_html_length:
                html_summary += "\n... (HTML truncated) ..."
        
        # 2. Tối ưu prompt
        prompt = f"""Tìm CSS selector hoặc XPath cho: "{description}"{f" ({context})" if context else ""} trên trang web {page_title}.
Phân tích cấu trúc trang:

{html_summary}

Trả về 3 selector tốt nhất, mỗi dòng một selector, bắt đầu từ selector chính xác nhất.
Ưu tiên CSS selector như #id, .class, tagname, [attribute]. Nếu không thể dùng CSS, trả về XPath.
Chỉ trả về các selector, không giải thích."""
        
        return prompt
    
    def _analyze_with_ai(self, prompt, screenshot_path=None):
        """Gửi prompt và ảnh chụp màn hình (nếu có) tới OpenAI để phân tích - đã tối ưu token"""
        try:
            # 1. Kiểm tra cache trước khi gọi API
            cache_dir = self.cache_dir / "selectors"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Tạo cache key từ prompt
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            cache_file = cache_dir / f"selector_{prompt_hash}.json"
            
            # Thử đọc từ cache (hợp lệ trong 30 phút)
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                    
                    if time.time() - cache_data.get("timestamp", 0) < 1800:
                        selectors = cache_data.get("selectors", [])
                        if selectors:
                            self.logger.info(f"Sử dụng selectors từ cache ({len(selectors)} selectors)")
                            return selectors
                except Exception as e:
                    self.logger.debug(f"Lỗi khi đọc cache: {str(e)}")
            
            # 2. Quyết định model dựa trên độ phức tạp của yêu cầu
            prompt_length = len(prompt)
            
            if prompt_length < 1000:
                model_to_use = "gpt-3.5-turbo-0125"  # Sử dụng model rẻ hơn cho yêu cầu đơn giản
                max_tokens = 150  # Ít token hơn cho output
            else:
                model_to_use = "gpt-4-turbo"
                max_tokens = 250
            
            # 3. Quyết định có sử dụng screenshot hay không
            use_screenshot = False
            if screenshot_path:
                # Phân tích prompt để xác định độ phức tạp
                complex_elements = ["dropdown", "menu", "complex", "dynamic", "hover"]
                use_screenshot = any(term in prompt.lower() for term in complex_elements)
                
            messages = [{"role": "user", "content": prompt}]
            response = None
            
            # 4. Nếu cần sử dụng screenshot
            if use_screenshot:
                try:
                    # Nén ảnh để giảm kích thước và tiết kiệm token
                    from PIL import Image
                    import io
                    
                    img = Image.open(screenshot_path)
                    img_width, img_height = img.size
                    
                    # Giảm kích thước và nén ảnh
                    if img_width > 600 or img_height > 600:
                        ratio = min(600/img_width, 600/img_height)
                        new_size = (int(img_width * ratio), int(img_height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    # Nén ảnh
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=70)
                    compressed_image = buffer.getvalue()
                    base64_image = base64.b64encode(compressed_image).decode("utf-8")
                    
                    # Sử dụng GPT-4 Vision API với ảnh đã nén
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user", 
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ],
                        max_tokens=max_tokens
                    )
                except Exception as e:
                    self.logger.warning(f"Lỗi khi xử lý ảnh: {str(e)}, fallback sang text-only")
                    use_screenshot = False
            
            # 5. Nếu không sử dụng screenshot hoặc có lỗi khi xử lý ảnh
            if not use_screenshot or not response:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_use,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0.3  # Giảm temperature để tăng tính chính xác
                    )
                except Exception as e:
                    self.logger.error(f"Lỗi khi gọi OpenAI API: {str(e)}")
                    if self.debug:
                        self.logger.error(traceback.format_exc())
                    # Fallback cho lỗi API
                    return None
            
            # 6. Xử lý phản hồi
            if response:
                selectors_text = response.choices[0].message.content
                selectors = [line.strip() for line in selectors_text.split("\n") if line.strip()]
                
                # Lọc các dòng không phải selectors
                selectors = [s for s in selectors if not s.startswith("Selector") and not s.startswith("-")]
                
                # Làm sạch selectors
                clean_selectors = []
                for selector in selectors:
                    # Loại bỏ số thứ tự và dấu bullet
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "•", "*", "-", "+"]:
                        if selector.startswith(prefix):
                            selector = selector[len(prefix):].strip()
                            break
                    
                    # Loại bỏ dấu nháy
                    for char in ['`', '"', "'"]:
                        selector = selector.replace(char, '')
                    
                    if selector:
                        clean_selectors.append(selector)
                
                # Lưu vào cache
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "timestamp": time.time(),
                            "selectors": clean_selectors
                        }, f)
                except Exception as e:
                    self.logger.debug(f"Lỗi khi lưu cache: {str(e)}")
                
                return clean_selectors
            
            return None
        except Exception as e:
            self.logger.error(f"Lỗi khi phân tích với AI: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return None
    
    def _validate_selector(self, selector):
        """
        Kiểm tra selector có hợp lệ không
        
        Args:
            selector (str): Selector cần kiểm tra
            
        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if not selector:
            return False
            
        try:
            # Kiểm tra nếu selector là XPath
            is_xpath = selector.startswith('xpath=') or selector.startswith('/') or selector.startswith('.//')
            
            # Xử lý selector XPath
            if is_xpath:
                xpath_selector = selector
                if not selector.startswith('xpath='):
                    xpath_selector = f"xpath={selector}"
                    
                element = self.browser.page.query_selector(xpath_selector)
                return element is not None
            else:
                # Xử lý CSS selector
                element = self.browser.page.query_selector(selector)
                return element is not None
        except Exception as e:
            self.logger.debug(f"Lỗi khi validate selector '{selector}': {str(e)}")
            return False
    
    def _validate_selectors(self, selectors):
        """Kiểm tra từng selector xem có hoạt động không"""
        for selector in selectors:
            try:
                clean_selector = selector
                for prefix in ["CSS: ", "XPath: ", "- ", "* "]:
                    if clean_selector.startswith(prefix):
                        clean_selector = clean_selector[len(prefix):].strip()
                
                # Kiểm tra xem selector có hoạt động không
                element = None
                
                # Thử dùng CSS selector
                try:
                    element = self.browser.page.query_selector(clean_selector)
                except:
                    pass
                
                # Nếu không hoạt động, thử dùng XPath
                if not element and (clean_selector.startswith('/') or clean_selector.startswith('.//')):
                    try:
                        element = self.browser.page.query_selector(f"xpath={clean_selector}")
                        if element:
                            clean_selector = f"xpath={clean_selector}"
                    except:
                        pass
                
                if element:
                    if self.debug:
                        try:
                            self.browser.page.evaluate("""(element) => {
                                const originalStyle = element.getAttribute('style') || '';
                                element.setAttribute('style', originalStyle + '; border: 2px solid red; background-color: rgba(255, 0, 0, 0.2);');
                                setTimeout(() => {
                                    element.setAttribute('style', originalStyle);
                                }, 2000);
                            }""", element)
                            time.sleep(1)
                        except Exception as highlight_e:
                            self.logger.debug(f"Không thể highlight phần tử: {str(highlight_e)}")
                    return clean_selector
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"Error validating selector {selector}: {str(e)}")
                continue
        
        return None
    
    def _fallback_search(self, description):
        """
        Tìm kiếm phương pháp fallback khi AI và heuristic thất bại
        
        Args:
            description (str): Mô tả phần tử
            
        Returns:
            str: Selector nếu tìm thấy, None nếu không
        """
        try:
            # Chuẩn hóa mô tả
            desc_lower = description.lower().strip()
            
            # 1. Tạo XPath tìm theo text chính xác
            xpath_exact = f"//*/text()[normalize-space(.)='{desc_lower}']/parent::*"
            if self._validate_selector(f"xpath={xpath_exact}"):
                return f"xpath={xpath_exact}"
            
            # 2. Tạo XPath tìm theo text một phần
            xpath_contains = f"//*/text()[contains(normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')), '{desc_lower}')]/parent::*"
            if self._validate_selector(f"xpath={xpath_contains}"):
                return f"xpath={xpath_contains}"
            
            # 3. Tạo XPath tìm theo thuộc tính
            xpath_attrs = f"""
                //*[
                    contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower}') or
                    contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower}') or
                    contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower}') or
                    contains(translate(@alt, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower}')
                ]
            """
            if self._validate_selector(f"xpath={xpath_attrs}"):
                return f"xpath={xpath_attrs}"
            
            # 4. Tạo XPath tìm theo label
            xpath_label = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower}')]/@for"
            try:
                # Lấy giá trị của thuộc tính 'for'
                result = self.browser.page.evaluate(f"document.evaluate(\"{xpath_label}\", document, null, XPathResult.STRING_TYPE, null).stringValue")
                if result:
                    # Tạo selector cho input tương ứng
                    input_selector = f"#{result}"
                    if self._validate_selector(input_selector):
                        return input_selector
            except Exception as xpath_e:
                self.logger.debug(f"Lỗi khi thực thi XPath label: {str(xpath_e)}")
            
            return None
        except Exception as e:
            self.logger.warning(f"Lỗi khi thực hiện tìm kiếm fallback: {str(e)}")
            if self.debug:
                self.logger.warning(traceback.format_exc())
            return None
    
    def interact_with_element_by_description(self, description, action="click", value=None, context=None, target_description=None, attribute=None, option=None):
        """
        Tìm và tương tác với phần tử bằng cách mô tả
        
        Args:
            description (str): Mô tả phần tử cần tìm
            action (str): Hành động ('click', 'type', 'hover', 'drag_and_drop', 'scroll_to', 'highlight', ...)
            value (str, optional): Giá trị cần nhập (cho action='type')
            context (str, optional): Bối cảnh bổ sung
            target_description (str, optional): Mô tả phần tử đích (cho drag_and_drop)
            attribute (str, optional): Tên thuộc tính (cho get_attribute)
            option (str, optional): Giá trị option (cho select_option)
            
        Returns:
            bool/str: True nếu thành công, False nếu thất bại, hoặc giá trị trả về nếu là extract_text/get_attribute
        """
        try:
            selector = self.find_element_by_description(description, context)
            if not selector:
                # Thử tìm kiếm nhiều lần nếu lần đầu thất bại
                for _ in range(2):
                    time.sleep(0.5)  # Đợi một chút và thử lại
                    selector = self.find_element_by_description(description, context)
                    if selector:
                        break
                        
                if not selector:
                    self.logger.warning(f"Could not find element: {description}")
                    return False
            
            page = self.browser.page
            
            try:
                # Nếu selector là XPath, điều chỉnh trước khi sử dụng
                is_xpath = selector.startswith('xpath=') or selector.startswith('/') or selector.startswith('.//')
                
                if action == "click":
                    if is_xpath and not selector.startswith('xpath='):
                        return self.browser.click_element(f"xpath={selector}")
                    return self.browser.click_element(selector)
                elif action == "type" and value is not None:
                    if is_xpath and not selector.startswith('xpath='):
                        return self.browser.type_text(f"xpath={selector}", value)
                    return self.browser.type_text(selector, value)
                elif action == "hover":
                    page.hover(selector)
                    return True
                elif action == "double_click":
                    page.dblclick(selector)
                    return True
                elif action == "right_click":
                    page.click(selector, button="right")
                    return True
                elif action == "drag_and_drop" and target_description:
                    target_selector = self.find_element_by_description(target_description, context)
                    if not target_selector:
                        self.logger.warning(f"Could not find target element: {target_description}")
                        return False
                    source = page.query_selector(selector)
                    target = page.query_selector(target_selector)
                    if source and target:
                        source.drag_to(target)
                        return True
                    return False
                elif action == "scroll_to":
                    element = page.query_selector(selector)
                    if element:
                        element.scroll_into_view_if_needed()
                        return True
                    return False
                elif action == "highlight":
                    page.evaluate("""(element) => {
                        const originalStyle = element.getAttribute('style') || '';
                        element.setAttribute('style', originalStyle + '; border: 2px solid orange; background-color: yellow;');
                        setTimeout(() => {
                            element.setAttribute('style', originalStyle);
                        }, 2000);
                    }""", page.query_selector(selector))
                    return True
                elif action == "extract_text":
                    return page.text_content(selector)
                elif action == "get_attribute" and attribute:
                    return page.get_attribute(selector, attribute)
                elif action == "check":
                    page.check(selector)
                    return True
                elif action == "uncheck":
                    page.uncheck(selector)
                    return True
                elif action == "select_option" and option:
                    page.select_option(selector, option)
                    return True
                elif action == "focus":
                    page.focus(selector)
                    return True
                elif action == "blur":
                    page.evaluate("el => el.blur()", page.query_selector(selector))
                    return True
                else:
                    self.logger.error(f"Unsupported action: {action}")
                    return False
            except Exception as action_e:
                self.logger.error(f"Error performing action '{action}' on element '{description}': {str(action_e)}")
                if self.debug:
                    self.logger.error(traceback.format_exc())
                
                # Thử xử lý overlay nếu tương tác thất bại
                if hasattr(self.browser, 'overlay_handler') and self.browser.overlay_handler:
                    try:
                        self.logger.info("Đang thử xử lý overlay để tương tác với phần tử...")
                        self.browser.overlay_handler.close_overlay(close_all=True)
                        self.browser.overlay_handler.make_element_clickable(selector)
                        
                        # Thử tương tác lần nữa
                        if action == "click":
                            return self.browser.click_element(selector)
                        elif action == "type" and value is not None:
                            return self.browser.type_text(selector, value)
                        # Các hành động khác tương tự...
                    except Exception as overlay_e:
                        self.logger.warning(f"Không thể xử lý overlay: {str(overlay_e)}")
                
                return False
        except Exception as e:
            self.logger.error(f"Lỗi trong interact_with_element_by_description: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False
    
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        try:
            if self.use_page_observer and self.page_observer:
                self.page_observer.stop()
                if self.debug:
                    self.logger.info("Đã dừng PageObserver")
        except Exception as e:
            self.logger.error(f"Lỗi khi dọn dẹp tài nguyên: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
    
    def clear_cache_on_page_change(self, url):
        """Xóa cache selector khi trang thay đổi lớn"""
        keys_to_delete = [k for k in self._selector_cache if k.startswith(url)]
        for k in keys_to_delete:
            del self._selector_cache[k]
        self.logger.info(f"[EnhancedElementFinder] Đã xóa cache selector cho URL: {url}")
