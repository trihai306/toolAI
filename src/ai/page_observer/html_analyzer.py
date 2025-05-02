"""
HTML Analyzer Module
Phân tích HTML và trích xuất thông tin về cấu trúc trang để tìm phần tử
"""

import os
import time
import base64
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# Đảm bảo biến môi trường được tải
load_dotenv()

class HTMLAnalyzer:
    """
    Phân tích cấu trúc HTML và tạo bản đồ phần tử để tìm kiếm nhanh
    """
    
    def __init__(self, use_ai=True, cache_dir=None):
        """
        Khởi tạo HTML Analyzer
        
        Args:
            use_ai (bool): Sử dụng AI để phân tích HTML
            cache_dir (str, optional): Thư mục lưu trữ cache
        """
        # Cấu hình logging
        try:
            from utils.logging_utils import get_logger
            self.logger = get_logger("HTMLAnalyzer")
        except ImportError:
            import logging
            self.logger = logging.getLogger("HTMLAnalyzer")
        
        self.use_ai = use_ai
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if self.use_ai and not self.openai_api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            self.use_ai = False
        
        # Khởi tạo OpenAI client nếu dùng AI
        if self.use_ai:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                self.logger.error(f"Lỗi khởi tạo OpenAI client: {str(e)}")
                self.use_ai = False
        
        # Thư mục lưu trữ cache và dữ liệu phân tích
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data/html_analysis")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Lưu trữ bản đồ phần tử của trang hiện tại
        self.current_page_url = None
        self.current_page_html = None
        self.current_page_element_map = {}
        self.current_page_soup = None
        
        self.logger.info("HTML Analyzer đã được khởi tạo")
    
    def analyze_page(self, url, html, screenshot_path=None):
        """
        Phân tích trang web và tạo bản đồ phần tử
        
        Args:
            url (str): URL của trang
            html (str): Nội dung HTML
            screenshot_path (str, optional): Đường dẫn đến ảnh chụp màn hình
            
        Returns:
            dict: Bản đồ phần tử của trang
        """
        try:
            self.logger.info(f"Bắt đầu phân tích trang: {url}")
            start_time = time.time()
            
            # Cập nhật thông tin trang hiện tại
            self.current_page_url = url
            self.current_page_html = html
            
            # Parse HTML bằng BeautifulSoup
            self.current_page_soup = BeautifulSoup(html, 'html.parser')
            
            # Tạo bản đồ phần tử cơ bản
            element_map = self._create_basic_element_map()
            
            # Nếu dùng AI, tăng cường bản đồ phần tử với phân tích AI
            if self.use_ai:
                element_map = self._enhance_element_map_with_ai(element_map, screenshot_path)
            
            # Lưu bản đồ phần tử
            self.current_page_element_map = element_map
            
            # Lưu cache bản đồ phần tử
            self._save_element_map_cache(url, element_map)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Phân tích trang hoàn tất trong {elapsed_time:.2f}s. Đã tìm thấy {len(element_map)} phần tử.")
            
            return element_map
        except Exception as e:
            self.logger.error(f"Lỗi khi phân tích trang {url}: {str(e)}")
            return {}
    
    def _create_basic_element_map(self):
        """
        Tạo bản đồ phần tử cơ bản từ HTML
        
        Returns:
            dict: Bản đồ phần tử
        """
        element_map = {}
        try:
            soup = self.current_page_soup
            
            # Trích xuất tiêu đề trang
            page_title = soup.title.string if soup.title else ""
            
            # Thu thập tất cả phần tử có thuộc tính id
            elements_with_id = soup.select("[id]")
            for element in elements_with_id:
                element_id = element.get("id")
                if element_id:
                    element_type = element.name
                    element_text = element.get_text(strip=True)
                    element_attrs = dict(element.attrs)
                    
                    # Tạo selector
                    selector = f"#{element_id}"
                    
                    # Thêm vào bản đồ phần tử
                    element_map[selector] = {
                        "type": element_type,
                        "text": element_text,
                        "attributes": element_attrs,
                        "selector": selector,
                        "source": "id"
                    }
            
            # Thu thập các phần tử có thuộc tính name
            elements_with_name = soup.select("[name]")
            for element in elements_with_name:
                element_name = element.get("name")
                if element_name and element.name != "meta":
                    element_type = element.name
                    element_text = element.get_text(strip=True)
                    element_attrs = dict(element.attrs)
                    
                    # Tạo selector
                    selector = f"{element_type}[name='{element_name}']"
                    
                    # Thêm vào bản đồ phần tử
                    element_map[selector] = {
                        "type": element_type,
                        "text": element_text,
                        "attributes": element_attrs,
                        "selector": selector,
                        "source": "name"
                    }
            
            # Thu thập các phần tử có thuộc tính class
            elements_with_class = soup.select("[class]")
            for element in elements_with_class:
                element_classes = element.get("class")
                if element_classes:
                    element_type = element.name
                    element_text = element.get_text(strip=True)
                    element_attrs = dict(element.attrs)
                    
                    # Tạo selector
                    class_selector = f"{element_type}.{'.'.join(element_classes)}"
                    
                    # Thêm vào bản đồ phần tử
                    element_map[class_selector] = {
                        "type": element_type,
                        "text": element_text,
                        "attributes": element_attrs,
                        "selector": class_selector,
                        "source": "class"
                    }
            
            # Thu thập các phần tử input, button, a, select, textarea
            for element_type in ["input", "button", "a", "select", "textarea"]:
                elements = soup.find_all(element_type)
                for i, element in enumerate(elements):
                    element_text = element.get_text(strip=True)
                    element_attrs = dict(element.attrs)
                    
                    # Tạo selector dựa trên vị trí
                    position_selector = f"{element_type}:nth-of-type({i+1})"
                    
                    # Tạo selector dựa trên text cho các phần tử có text
                    text_selector = None
                    if element_text and element_type in ["button", "a"]:
                        text_selector = f"{element_type}:contains('{element_text}')"
                    
                    # Thêm vào bản đồ phần tử
                    if position_selector not in element_map:
                        element_map[position_selector] = {
                            "type": element_type,
                            "text": element_text,
                            "attributes": element_attrs,
                            "selector": position_selector,
                            "text_selector": text_selector,
                            "source": "position"
                        }
            
            # Thu thập các phần tử heading (h1, h2, h3, h4, h5, h6)
            headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            for heading in headings:
                heading_type = heading.name
                heading_text = heading.get_text(strip=True)
                heading_attrs = dict(heading.attrs)
                
                # Tạo selector dựa trên text
                if heading_text:
                    selector = f"{heading_type}:contains('{heading_text}')"
                    
                    # Thêm vào bản đồ phần tử
                    element_map[selector] = {
                        "type": heading_type,
                        "text": heading_text,
                        "attributes": heading_attrs,
                        "selector": selector,
                        "source": "heading"
                    }
            
            # Thu thập các phần tử có aria-label
            elements_with_aria_label = soup.select("[aria-label]")
            for element in elements_with_aria_label:
                aria_label = element.get("aria-label")
                if aria_label:
                    element_type = element.name
                    element_text = element.get_text(strip=True)
                    element_attrs = dict(element.attrs)
                    
                    # Tạo selector
                    selector = f"{element_type}[aria-label='{aria_label}']"
                    
                    # Thêm vào bản đồ phần tử
                    element_map[selector] = {
                        "type": element_type,
                        "text": element_text,
                        "attributes": element_attrs,
                        "selector": selector,
                        "source": "aria-label"
                    }
            
            # Thu thập labels và liên kết với input
            labels = soup.find_all("label")
            for label in labels:
                label_for = label.get("for")
                label_text = label.get_text(strip=True)
                
                if label_for:
                    # Tìm input liên kết
                    input_element = soup.find(id=label_for)
                    if input_element:
                        input_selector = f"#{label_for}"
                        
                        # Thêm thông tin label vào element map nếu input đã tồn tại
                        if input_selector in element_map:
                            element_map[input_selector]["label_text"] = label_text
                        
                        # Thêm selector dựa trên label
                        label_based_selector = f"input[id='{label_for}']"
                        if label_based_selector not in element_map:
                            element_map[label_based_selector] = {
                                "type": input_element.name,
                                "text": input_element.get_text(strip=True),
                                "attributes": dict(input_element.attrs),
                                "selector": label_based_selector,
                                "label_text": label_text,
                                "source": "label"
                            }
            
            return element_map
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo bản đồ phần tử cơ bản: {str(e)}")
            return {}
    
    def _enhance_element_map_with_ai(self, element_map, screenshot_path=None):
        """
        Tăng cường bản đồ phần tử với phân tích AI - đã tối ưu token
        
        Args:
            element_map (dict): Bản đồ phần tử cơ bản
            screenshot_path (str, optional): Đường dẫn đến ảnh chụp màn hình
            
        Returns:
            dict: Bản đồ phần tử đã được tăng cường
        """
        try:
            if not self.use_ai or not self.openai_api_key:
                return element_map
                
            self.logger.info("Đang tăng cường bản đồ phần tử với AI...")
            
            # Kiểm tra bộ nhớ cache trước
            cache_key = f"ai_analysis_{self.current_page_url}"
            cache_path = self.cache_dir / f"{hashlib.md5(cache_key.encode()).hexdigest()}.json"
            
            # Nếu có cache hợp lệ trong vòng 30 phút, sử dụng cache
            if cache_path.exists():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                        
                    cache_timestamp = cache_data.get("timestamp", 0)
                    if time.time() - cache_timestamp < 1800:  # 30 phút
                        cached_elements = cache_data.get("elements", {})
                        if cached_elements:
                            self.logger.info(f"Sử dụng cache cho phân tích AI: {len(cached_elements)} phần tử")
                            # Thêm các phần tử từ cache vào bản đồ
                            for key, value in cached_elements.items():
                                element_map[key] = value
                            return element_map
                except Exception as e:
                    self.logger.warning(f"Lỗi khi đọc cache AI: {str(e)}")
            
            # Chuẩn bị dữ liệu cho AI
            page_info = {
                "url": self.current_page_url,
                "title": self.current_page_soup.title.string if self.current_page_soup.title else "",
                "element_count": len(element_map)
            }
            
            # Lọc chỉ lấy các phần tử tương tác quan trọng để giảm token
            important_elements = {}
            interactive_types = ["input", "button", "a", "select", "textarea", "form"]
            
            for selector, element_info in element_map.items():
                element_type = element_info.get("type", "")
                
                # Chỉ bao gồm các phần tử tương tác hoặc tiêu đề
                if element_type in interactive_types or element_type.startswith("h"):
                    # Chỉ chọn các thuộc tính quan trọng
                    filtered_attributes = {}
                    if "attributes" in element_info:
                        for attr in ["id", "name", "type", "placeholder", "aria-label", "role"]:
                            if attr in element_info["attributes"]:
                                filtered_attributes[attr] = element_info["attributes"][attr]
                    
                    important_elements[selector] = {
                        "type": element_type,
                        "text": element_info.get("text", "")[:100] if element_info.get("text") else "",  # Giới hạn độ dài text
                        "label": element_info.get("label_text", "")[:100] if element_info.get("label_text") else "",  # Giới hạn độ dài label
                        "attributes": filtered_attributes
                    }
            
            # Giới hạn số lượng phần tử để giảm token
            if len(important_elements) > 15:
                # Ưu tiên phần tử theo loại
                priority_elements = {}
                for selector, info in important_elements.items():
                    if info["type"] in ["button", "input", "a"]:
                        priority_elements[selector] = info
                        if len(priority_elements) >= 15:
                            break
                
                # Nếu chưa đủ 15 phần tử, thêm các phần tử khác
                if len(priority_elements) < 15:
                    for selector, info in important_elements.items():
                        if selector not in priority_elements:
                            priority_elements[selector] = info
                            if len(priority_elements) >= 15:
                                break
                
                important_elements = priority_elements
            
            # Chuẩn bị prompt cho AI - đã tối ưu
            prompt = f"""Phân tích các phần tử tương tác chính trên trang web: {page_info['title']} ({page_info['url']}).
Cho mỗi phần tử, tạo: 1) Mô tả ngắn gọn (ví dụ: "nút đăng nhập") 2) CSS selector chính xác.
Tập trung vào phần tử: form, button, input, link, dropdown.

Phần tử quan trọng (tối đa 15):
{json.dumps(important_elements, ensure_ascii=False)}

Trả về JSON ngắn gọn:
{{"key_elements":[{{"description":"..","selector":"..","element_type":"..","common_actions":["click"]}}],"page_summary":".."}}"""
            
            # Phân tích với AI
            response = None
            
            # Quyết định model dựa trên độ phức tạp của trang
            if len(important_elements) <= 5:
                model_to_use = "gpt-3.5-turbo-0125"  # Sử dụng model rẻ hơn cho trang đơn giản
                max_tokens = 800
            else:
                model_to_use = "gpt-4-turbo"
                max_tokens = 1000
                
            # Nếu có client và screenshot, sử dụng vision
            if screenshot_path and len(important_elements) > 8:  # Sử dụng vision chỉ khi cần thiết
                # Nén ảnh trước khi chuyển đổi sang base64
                try:
                    from PIL import Image
                    import io
                    
                    # Nén ảnh để giảm kích thước
                    img = Image.open(screenshot_path)
                    img_width, img_height = img.size
                    
                    # Giảm kích thước nếu ảnh quá lớn
                    if img_width > 800 or img_height > 800:
                        ratio = min(800/img_width, 800/img_height)
                        new_size = (int(img_width * ratio), int(img_height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    # Nén và lưu vào buffer
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=70)
                    compressed_image = buffer.getvalue()
                    base64_image = base64.b64encode(compressed_image).decode("utf-8")
                except Exception:
                    # Fallback to original image if compression fails
                    with open(screenshot_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                
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
            else:
                # Sử dụng model tiêu chuẩn không vision
                response = self.client.chat.completions.create(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens
                )
            
            # Xử lý phản hồi
            if response:
                ai_analysis = response.choices[0].message.content
                try:
                    # Trích xuất phần JSON từ phản hồi
                    ai_analysis = ai_analysis.strip()
                    
                    # Trích xuất JSON từ bất kỳ định dạng nào
                    start_pos = ai_analysis.find('{')
                    end_pos = ai_analysis.rfind('}')
                    
                    if start_pos != -1 and end_pos != -1:
                        ai_analysis = ai_analysis[start_pos:end_pos+1]
                        
                    ai_data = json.loads(ai_analysis)
                    
                    # Lưu phần tử được AI phân tích để cache
                    ai_elements = {}
                    
                    # Thêm các phần tử đã được phân tích vào bản đồ
                    if "key_elements" in ai_data:
                        for element_info in ai_data["key_elements"]:
                            description = element_info.get("description")
                            selector = element_info.get("selector")
                            
                            if description and selector:
                                # Tạo khóa duy nhất
                                key = f"ai_desc:{description}"
                                
                                # Tạo thông tin phần tử
                                element_data = {
                                    "description": description,
                                    "selector": selector,
                                    "element_type": element_info.get("element_type"),
                                    "common_actions": element_info.get("common_actions", []),
                                    "source": "ai_analysis"
                                }
                                
                                # Thêm vào bản đồ phần tử
                                element_map[key] = element_data
                                ai_elements[key] = element_data
                    
                    # Lưu thông tin tổng quát về trang
                    if "page_summary" in ai_data:
                        page_info_data = {
                            "summary": ai_data["page_summary"],
                            "source": "ai_analysis"
                        }
                        element_map["page_info"] = page_info_data
                        ai_elements["page_info"] = page_info_data
                    
                    # Lưu cache
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "timestamp": time.time(),
                            "elements": ai_elements
                        }, f, ensure_ascii=False)
                        
                    self.logger.info(f"Đã tăng cường bản đồ phần tử với {len(ai_data.get('key_elements', []))} phần tử từ AI")
                except Exception as e:
                    self.logger.error(f"Lỗi khi xử lý phản hồi AI: {str(e)}")
            
            return element_map
        except Exception as e:
            self.logger.error(f"Lỗi khi tăng cường bản đồ phần tử với AI: {str(e)}")
            return element_map
    
    def _save_element_map_cache(self, url, element_map):
        """
        Lưu cache bản đồ phần tử
        
        Args:
            url (str): URL của trang
            element_map (dict): Bản đồ phần tử
        """
        try:
            # Tạo tên tệp từ URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = self.cache_dir / f"{url_hash}.json"
            
            # Lưu dữ liệu
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "url": url,
                    "timestamp": time.time(),
                    "element_map": element_map
                }, f, ensure_ascii=False, indent=2)
                
            self.logger.debug(f"Đã lưu cache bản đồ phần tử: {cache_file}")
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu cache bản đồ phần tử: {str(e)}")
    
    def _load_element_map_cache(self, url):
        """
        Tải cache bản đồ phần tử
        
        Args:
            url (str): URL của trang
            
        Returns:
            dict: Bản đồ phần tử hoặc None nếu không tìm thấy
        """
        try:
            # Tạo tên tệp từ URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = self.cache_dir / f"{url_hash}.json"
            
            # Kiểm tra nếu tệp tồn tại
            if not cache_file.exists():
                return None
                
            # Tải dữ liệu
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Kiểm tra nếu cache quá cũ (hơn 1 giờ)
            if time.time() - data.get("timestamp", 0) > 3600:
                self.logger.debug(f"Cache đã hết hạn: {cache_file}")
                return None
                
            return data.get("element_map")
        except Exception as e:
            self.logger.error(f"Lỗi khi tải cache bản đồ phần tử: {str(e)}")
            return None
    
    def find_element_by_description(self, description, context=None):
        """
        Tìm phần tử dựa trên mô tả
        
        Args:
            description (str): Mô tả phần tử (ví dụ: "nút đăng nhập", "ô tìm kiếm")
            context (str, optional): Bối cảnh bổ sung
            
        Returns:
            str: CSS selector hoặc XPath của phần tử, hoặc None nếu không tìm thấy
        """
        try:
            if not description:
                return None
                
            self.logger.info(f"Tìm phần tử với mô tả: {description}")
            
            # Chuẩn hóa mô tả
            desc_lower = description.lower().strip()
            
            # Kiểm tra cache
            cache_dir = self.cache_dir / "selectors"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            cache_key = f"{desc_lower}_{context or ''}"
            cache_file = cache_dir / f"{hashlib.md5(cache_key.encode()).hexdigest()}.txt"
            
            # Kiểm tra cache (hợp lệ trong 1 giờ)
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if len(lines) >= 2:
                            timestamp = float(lines[0].strip())
                            if time.time() - timestamp < 3600:  # 1 giờ
                                selector = lines[1].strip()
                                self.logger.info(f"Đã tìm thấy phần tử từ cache: {selector}")
                                return selector
                except Exception as e:
                    self.logger.debug(f"Lỗi khi đọc cache: {str(e)}")
            
            # Bước 1: Tìm trong bản đồ phần tử dựa trên mô tả
            best_match = {"selector": None, "score": 0, "key": None}
            
            for key, element_info in self.current_page_element_map.items():
                score = 0
                element_text = element_info.get("text", "").lower()
                element_label = element_info.get("label_text", "").lower()
                
                # So khớp với text của phần tử
                if element_text:
                    if element_text == desc_lower:
                        score += 10  # Khớp hoàn toàn
                    elif desc_lower in element_text:
                        score += 5   # Desc là substring
                    elif element_text in desc_lower:
                        score += 3   # Text là substring của desc
                
                # So khớp với label text
                if element_label:
                    if element_label == desc_lower:
                        score += 8  # Khớp hoàn toàn với label
                    elif desc_lower in element_label:
                        score += 4  # Desc là substring của label
                
                # So khớp với thuộc tính
                if "attributes" in element_info:
                    attrs = element_info["attributes"]
                    for attr in ["placeholder", "name", "title", "aria-label", "alt"]:
                        if attr in attrs and attrs[attr]:
                            attr_value_lower = attrs[attr].lower()
                            if attr_value_lower == desc_lower:
                                score += 7  # Khớp hoàn toàn với thuộc tính
                            elif attr_value_lower in desc_lower:
                                score += 3  # Thuộc tính là substring
                            elif desc_lower in attr_value_lower:
                                score += 2  # Description là substring của thuộc tính
                
                # Phần tử loại button/input/a được ưu tiên hơn
                if element_info.get("type") in ["button", "input", "a"]:
                    score += 2
                
                # Cập nhật best match
                if score > best_match["score"] and element_info.get("selector"):
                    best_match = {
                        "selector": element_info.get("selector"),
                        "score": score,
                        "key": key
                    }
            
            # Nếu có match tốt (score > 3), sử dụng ngay
            if best_match["score"] > 3:
                self.logger.info(f"Tìm thấy phần tử phù hợp nhất: {best_match['key']} (score: {best_match['score']})")
                # Lưu vào cache
                self._save_selector_to_cache(cache_file, best_match["selector"])
                return best_match["selector"]
            
            # Bước 3: Sử dụng AI để tìm phần tử nếu các phương pháp trên thất bại
            if self.use_ai and self.openai_api_key:
                self.logger.info(f"Đang sử dụng AI để tìm phần tử với mô tả: {description}")
                
                # Chuẩn bị dữ liệu đầu vào cho AI
                # Sử dụng tóm tắt HTML thay vì HTML đầy đủ
                html_summary = self._get_html_summary()
                
                # Chuẩn bị prompt tối ưu 
                prompt = f"""Tìm CSS selector hoặc XPath cho phần tử: "{description}"{f" ({context})" if context else ""}.
Dựa trên cấu trúc HTML:
{html_summary[:1500]}

Chỉ trả về một selector chính xác, không giải thích, không có dấu backtick."""
                
                # Quyết định model dựa trên độ phức tạp
                model_to_use = "gpt-3.5-turbo-0125"  # Mặc định dùng model rẻ hơn
                
                # Sử dụng API mới
                response = self.client.chat.completions.create(
                    model=model_to_use,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,  # Giảm xuống vì chỉ cần selector
                    temperature=0.3  # Giảm temperature để tăng tính chính xác
                )
                
                # Xử lý phản hồi
                if response:
                    selector = response.choices[0].message.content.strip()
                    
                    # Làm sạch selector
                    for char in ['`', '"', "'"]:
                        selector = selector.replace(char, '')
                    
                    # Loại bỏ các dòng thừa
                    selector = selector.split('\n')[0].strip()
                    
                    self.logger.info(f"AI đề xuất selector: {selector}")
                    
                    # Lưu vào cache
                    self._save_selector_to_cache(cache_file, selector)
                    return selector
            
            self.logger.warning(f"Không tìm thấy phần tử nào khớp với mô tả: {description}")
            return None
        except Exception as e:
            self.logger.error(f"Lỗi khi tìm phần tử theo mô tả: {str(e)}")
            return None
    
    def _save_selector_to_cache(self, cache_file, selector):
        """
        Lưu selector vào cache để tái sử dụng
        
        Args:
            cache_file (Path): Đường dẫn tệp cache
            selector (str): Selector cần lưu
        """
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(f"{time.time()}\n{selector}")
        except Exception as e:
            self.logger.debug(f"Lỗi lưu selector vào cache: {str(e)}")
    
    def _get_html_summary(self):
        """
        Tạo tóm tắt cấu trúc HTML cho trang hiện tại
        
        Returns:
            str: Tóm tắt cấu trúc HTML
        """
        try:
            soup = self.current_page_soup
            if not soup:
                return ""
                
            # Tạo tóm tắt
            summary = []
            
            # Thêm thông tin cơ bản
            if soup.title:
                summary.append(f"Title: {soup.title.string}")
            
            # Thu thập forms
            forms = soup.find_all("form")
            if forms:
                summary.append(f"\nForms ({len(forms)}):")
                for i, form in enumerate(forms):
                    form_id = form.get("id", "")
                    form_class = " ".join(form.get("class", []))
                    form_action = form.get("action", "")
                    summary.append(f"  Form {i+1}: id='{form_id}', class='{form_class}', action='{form_action}'")
                    
                    # Thu thập các input trong form
                    inputs = form.find_all(["input", "select", "textarea", "button"])
                    for input_elem in inputs:
                        input_type = input_elem.name
                        input_id = input_elem.get("id", "")
                        input_name = input_elem.get("name", "")
                        input_class = " ".join(input_elem.get("class", []))
                        input_type_attr = input_elem.get("type", "") if input_type == "input" else ""
                        input_placeholder = input_elem.get("placeholder", "")
                        
                        input_desc = f"    {input_type}"
                        if input_type_attr:
                            input_desc += f"[type='{input_type_attr}']"
                        if input_id:
                            input_desc += f", id='{input_id}'"
                        if input_name:
                            input_desc += f", name='{input_name}'"
                        if input_placeholder:
                            input_desc += f", placeholder='{input_placeholder}'"
                        if input_class:
                            input_desc += f", class='{input_class}'"
                            
                        summary.append(input_desc)
            
            # Thu thập buttons
            buttons = soup.find_all("button")
            if buttons:
                summary.append(f"\nButtons ({len(buttons)}):")
                for i, button in enumerate(buttons):
                    button_id = button.get("id", "")
                    button_class = " ".join(button.get("class", []))
                    button_text = button.get_text(strip=True)
                    button_desc = f"  Button {i+1}: text='{button_text}'"
                    if button_id:
                        button_desc += f", id='{button_id}'"
                    if button_class:
                        button_desc += f", class='{button_class}'"
                    summary.append(button_desc)
            
            # Thu thập links
            links = soup.find_all("a")
            if links:
                summary.append(f"\nLinks ({len(links)}):")
                for i, link in enumerate(links[:10]):  # Giới hạn 10 links
                    link_id = link.get("id", "")
                    link_class = " ".join(link.get("class", []))
                    link_text = link.get_text(strip=True)
                    link_href = link.get("href", "")
                    link_desc = f"  Link {i+1}: text='{link_text}'"
                    if link_id:
                        link_desc += f", id='{link_id}'"
                    if link_class:
                        link_desc += f", class='{link_class}'"
                    if link_href:
                        link_desc += f", href='{link_href}'"
                    summary.append(link_desc)
                
                if len(links) > 10:
                    summary.append(f"  ... and {len(links) - 10} more links")
            
            # Thu thập headings
            headings = soup.find_all(["h1", "h2", "h3"])
            if headings:
                summary.append(f"\nHeadings:")
                for heading in headings:
                    heading_type = heading.name
                    heading_text = heading.get_text(strip=True)
                    summary.append(f"  {heading_type}: {heading_text}")
            
            return "\n".join(summary)
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo tóm tắt HTML: {str(e)}")
            return ""
