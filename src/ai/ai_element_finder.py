"""
AI Element Finder Module
Sử dụng AI để xác định phần tử trên trang web khi không tìm thấy bằng selector thông thường
"""

import os
import base64
import time
import hashlib
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Đảm bảo biến môi trường được tải
load_dotenv()

class AIElementFinder:
    """Sử dụng AI để xác định và tìm phần tử trên trang web"""
    
    def __init__(self, browser_controller):
        """Khởi tạo AI Element Finder với browser controller"""
        self.browser = browser_controller
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Cấu hình logging
        try:
            from src.utils.logging_utils import get_logger
            self.logger = get_logger("AIElementFinder")
        except ImportError:
            import logging
            self.logger = logging.getLogger("AIElementFinder")
        
        if not self.openai_api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Xử lý định dạng khóa API mới
        api_key = self.openai_api_key.strip()
        # Không cần thay đổi định dạng vì khóa mới OpenAI đã hỗ trợ cả dạng sk-proj- và sk-
        self.logger.info("Đang sử dụng khóa API OpenAI với định dạng: " + 
                        ('mới (sk-proj-)' if api_key.startswith('sk-proj-') else 'cũ (sk-)'))
        
        # Khởi tạo OpenAI client
        try:
            self.client = OpenAI(api_key=api_key)
            self.logger.info("Đã khởi tạo OpenAI client thành công")
        except Exception as e:
            self.logger.error(f"Lỗi khởi tạo OpenAI client: {str(e)}")
            raise
            
        # Cache cho kết quả AI
        self.selector_cache = {}
        
        # Tạo thư mục cache nếu chưa tồn tại
        os.makedirs(os.path.join(os.getcwd(), "data", "ai_cache"), exist_ok=True)
    
    def find_element_by_description(self, description, context=None):
        """
        Tìm phần tử dựa trên mô tả bằng ngôn ngữ tự nhiên
        
        Args:
            description (str): Mô tả phần tử cần tìm (ví dụ: "nút đăng nhập", "ô tìm kiếm")
            context (str, optional): Bối cảnh bổ sung để giúp AI hiểu rõ hơn
            
        Returns:
            str: CSS selector hoặc XPath cho phần tử, hoặc None nếu không tìm thấy
        """
        if not self.browser.page:
            import logging
            logger = logging.getLogger("AIElementFinder")
            logger.error("Browser not started. Please start browser first.")
            return None
        # Chuẩn hóa mô tả và context để tăng cache hit
        url = self.browser.get_current_url()
        norm_desc = description.strip().lower() if description else ""
        norm_context = context.strip().lower() if context else ""
        cache_key = f"{url}::{norm_desc}::{norm_context}"
        # Kiểm tra cache trước
        if cache_key in self.selector_cache:
            self.logger.info(f"[AIElementFinder] Sử dụng selector từ cache cho '{description}'")
            selector = self.selector_cache[cache_key]
            try:
                element = self.browser.page.query_selector(selector)
                if element:
                    return selector
                else:
                    del self.selector_cache[cache_key]
            except Exception:
                del self.selector_cache[cache_key]
        # 1. Thử tìm bằng heuristic (JS) trước khi gọi AI
        try:
            js_code = f"""(desc) => {{
                const matches = [];
                const all = document.querySelectorAll('*');
                desc = desc.toLowerCase();
                for (const el of all) {{
                    const text = el.textContent?.trim().toLowerCase() || '';
                    const aria = el.getAttribute('aria-label')?.toLowerCase() || '';
                    const placeholder = el.getAttribute('placeholder')?.toLowerCase() || '';
                    const role = el.getAttribute('role')?.toLowerCase() || '';
                    if (text.includes(desc) || aria.includes(desc) || placeholder.includes(desc) || role.includes(desc)) {{
                        let selector = '';
                        if (el.id) selector = '#' + el.id;
                        else if (el.name) selector = el.tagName.toLowerCase() + '[name="' + el.name + '"]';
                        else if (el.classList.length > 0) selector = el.tagName.toLowerCase() + (Array.from(el.classList).length > 0 ? '.' + Array.from(el.classList).join('.') : '');
                        else selector = el.tagName.toLowerCase();
                        matches.push(selector);
                    }}
                }}
                return matches;
            }}"""
            found = self.browser.page.evaluate(js_code, [norm_desc])
            if found and len(found) > 0:
                selector = found[0]
                self.logger.info(f"[AIElementFinder] Heuristic tìm thấy selector: {selector}")
                self.selector_cache[cache_key] = selector
                return selector
        except Exception as e:
            self.logger.warning(f"[AIElementFinder] Lỗi khi tìm heuristic: {str(e)}")
        # 2. Nếu không tìm thấy, tiếp tục với AI như cũ
        screenshot_path = self.browser.take_screenshot("temp_screenshot_for_ai.png")
        html_content = self.browser.page.content()
        prompt = self._prepare_prompt(description, html_content, context)
        selectors = self._analyze_with_ai(prompt, screenshot_path, cache_key=cache_key)
        if selectors:
            valid_selector = self._validate_selectors(selectors)
            if valid_selector:
                self.selector_cache[cache_key] = valid_selector
                self.logger.info(f"[AIElementFinder] AI tìm thấy selector: {valid_selector}")
                return valid_selector
        # 3. Thử OCR nếu có element_inspector
        if hasattr(self.browser, 'element_inspector') and self.browser.element_inspector:
            try:
                candidates = self.browser.element_inspector.find_element_advanced(description, context=context, vision=True, ocr=True, top_n=1, debug=False)
                if candidates and len(candidates) > 0:
                    selector = candidates[0]['selector']
                    self.selector_cache[cache_key] = selector
                    self.logger.info(f"[AIElementFinder] OCR tìm thấy selector: {selector}")
                    return selector
            except Exception as e:
                self.logger.warning(f"[AIElementFinder] OCR fallback error: {str(e)}")
        self.logger.warning(f"[AIElementFinder] Không tìm thấy selector cho mô tả: {description}")
        return None
    
    def _prepare_prompt(self, description, html_content, context=None):
        """Chuẩn bị prompt cho AI"""
        # Giới hạn độ dài HTML để tránh vượt quá token limit
        max_html_length = 15000  # Giới hạn hợp lý
        truncated_html = html_content[:max_html_length]
        if len(html_content) > max_html_length:
            truncated_html += "\n... (HTML truncated) ..."
        
        prompt = f"""Bạn là một chuyên gia phân tích và tìm kiếm phần tử trên trang web.
        
Mô tả phần tử cần tìm: "{description}"

{"Bối cảnh bổ sung: " + context if context else ""}

Dựa trên HTML trang sau, hãy cung cấp 5 CSS selector hoặc XPath khác nhau có thể giúp tôi tìm thấy phần tử này.
Hãy bắt đầu từ selector cụ thể nhất và đơn giản nhất.
Chỉ trả lời dưới dạng danh sách selector, mỗi dòng một selector, không có giải thích.

HTML trang:
```html
{truncated_html}
```
"""
        return prompt
    
    def _analyze_with_ai(self, prompt, screenshot_path=None, cache_key=None):
        """Gửi prompt và ảnh chụp màn hình (nếu có) tới OpenAI để phân tích"""
        try:
            # Kiểm tra file cache nếu có cache_key
            if cache_key:
                cache_file = os.path.join(os.getcwd(), "data", "ai_cache", f"{hashlib.md5(cache_key.encode()).hexdigest()}.json")
                if os.path.exists(cache_file):
                    try:
                        import json
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            self.logger.info(f"Đã tìm thấy kết quả AI trong cache")
                            return cache_data.get('selectors', [])
                    except Exception as e:
                        self.logger.warning(f"Lỗi khi đọc cache: {str(e)}")
            
            messages = [{"role": "user", "content": prompt}]
            
            # Thêm ảnh chụp màn hình nếu được cung cấp và sử dụng model hỗ trợ vision
            if screenshot_path:
                # Mã hóa ảnh thành base64
                with open(screenshot_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                
                # Sử dụng GPT-4 Vision API với client mới
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user", 
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                            ]
                        }
                    ],
                    max_tokens=1000
                )
            else:
                # Sử dụng GPT-4 standard với client mới
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                    max_tokens=1000
                )
            
            # Trích xuất danh sách selector từ phản hồi
            selectors_text = response.choices[0].message.content
            selectors = [line.strip() for line in selectors_text.split("\n") if line.strip()]
            
            # Lưu kết quả vào cache nếu có cache_key
            if cache_key and selectors:
                try:
                    import json
                    cache_file = os.path.join(os.getcwd(), "data", "ai_cache", f"{hashlib.md5(cache_key.encode()).hexdigest()}.json")
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'timestamp': time.time(),
                            'selectors': selectors
                        }, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"Đã lưu kết quả AI vào cache")
                except Exception as e:
                    self.logger.warning(f"Lỗi khi lưu cache: {str(e)}")
            
            return selectors
            
        except Exception as e:
            self.logger.error(f"Error analyzing with AI: {str(e)}")
            return None
    
    def _validate_selectors(self, selectors):
        """Kiểm tra từng selector xem có hoạt động không"""
        for selector in selectors:
            try:
                # Làm sạch selector
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
                    except:
                        pass
                
                if element:
                    # Làm nổi bật phần tử và chụp ảnh màn hình để debug
                    self.browser.page.evaluate("""(element) => {
                        const originalStyle = element.getAttribute('style') || '';
                        element.setAttribute('style', originalStyle + '; border: 2px solid red; background-color: rgba(255, 0, 0, 0.2);');
                        setTimeout(() => {
                            element.setAttribute('style', originalStyle);
                        }, 2000);
                    }""", element)
                    
                    # Chờ 1 giây để nhìn thấy viền đỏ
                    time.sleep(1)
                    
                    # Trả về selector hoạt động
                    if clean_selector.startswith('/') or clean_selector.startswith('./'):
                        return f"xpath={clean_selector}"
                    return clean_selector
            except Exception as e:
                self.logger.warning(f"Error validating selector {selector}: {str(e)}")
                continue
        
        return None
    
    def interact_with_element_by_description(self, description, action="click", value=None, context=None, target_description=None, attribute=None, option=None):
        """
        Tìm và tương tác với phần tử bằng cách mô tả
        Args:
            description (str): Mô tả phần tử cần tìm
            action (str): Hành động ('click', 'type', ...)
            value (str, optional): Giá trị cần nhập (cho action='type')
            context (str, optional): Bối cảnh bổ sung
            target_description (str, optional): Mô tả phần tử đích (cho drag_and_drop)
            attribute (str, optional): Tên thuộc tính (cho get_attribute)
            option (str, optional): Giá trị option (cho select_option)
        Returns:
            bool/str: True nếu thành công, False nếu thất bại, hoặc giá trị trả về nếu là extract_text/get_attribute
        """
        # CHUẨN HÓA: Chỉ cho phép các action đã hỗ trợ
        supported_actions = {
            "navigate", "click", "type", "wait", "scroll", "view", "find_and_click",
            "double_click", "right_click", "hover", "drag_and_drop", "check", "uncheck", "select",
            "extract_text", "get_attribute", "focus", "blur", "file_upload", "contenteditable", "custom_input"
        }
        if action not in supported_actions:
            self.logger.warning(f"[AIElementFinder] Action không hỗ trợ: {action}. Bỏ qua.")
            return False
        selector = self.find_element_by_description(description, context)
        if not selector:
            self.logger.warning(f"Could not find element: {description}")
            return False
        page = self.browser.page
        try:
            if action == "click":
                return self.browser.click_element(selector)
            elif action == "type" and value:
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
                element = page.query_selector(selector)
                if element:
                    page.evaluate("""(element) => {
                        const originalStyle = element.getAttribute('style') || '';
                        element.setAttribute('style', originalStyle + '; border: 2px solid red; background-color: rgba(255, 0, 0, 0.2);');
                        setTimeout(() => {
                            element.setAttribute('style', originalStyle);
                        }, 5000);
                    }""", element)
                    return True
                return False
            elif action == "extract_text":
                try:
                    element = page.query_selector(selector)
                    if element:
                        return element.inner_text()
                    return None
                except Exception as e:
                    self.logger.warning(f"Error extracting text: {str(e)}")
                    return None
            elif action == "get_attribute" and attribute:
                try:
                    element = page.query_selector(selector)
                    if element:
                        return element.get_attribute(attribute)
                    return None
                except Exception as e:
                    self.logger.warning(f"Error getting attribute: {str(e)}")
                    return None
            elif action == "check":
                element = page.query_selector(selector)
                if element:
                    if not element.is_checked():
                        element.check()
                    return True
                return False
            elif action == "uncheck":
                element = page.query_selector(selector)
                if element:
                    if element.is_checked():
                        element.uncheck()
                    return True
                return False
            elif action == "select_option" and option:
                element = page.query_selector(selector)
                if element:
                    element.select_option(value=option)
                    return True
                return False
            elif action == "focus":
                element = page.query_selector(selector)
                if element:
                    element.focus()
                    return True
                return False
            elif action == "blur":
                element = page.query_selector(selector)
                if element:
                    page.evaluate("(element) => element.blur()", element)
                    return True
                return False
            else:
                self.logger.warning(f"Unsupported action: {action}")
                return False
        except Exception as e:
            self.logger.error(f"Error interacting with element: {str(e)}")
            return False
