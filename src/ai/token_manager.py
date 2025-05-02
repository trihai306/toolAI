"""
Token Manager Module
Quản lý hiệu quả việc sử dụng token OpenAI, tối ưu hóa chi phí và hiệu suất
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Thử import tiktoken, nhưng không gây lỗi nếu không có
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not installed. Token counting will use approximation.")


class TokenManager:
    """
    Quản lý hiệu quả việc sử dụng token khi tương tác với API OpenAI
    Cung cấp các chức năng để tối ưu hóa prompt, cache kết quả và ước tính chi phí
    """
    
    # Map các model và giá của chúng (USD per 1K tokens, giá gần đúng tại thời điểm tạo)
    MODEL_PRICE = {
        "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o-mini": {"input": 0.01, "output": 0.03},
        "gpt-4-32k": {"input": 0.06, "output": 0.12},
        "gpt-4": {"input": 0.03, "output": 0.06}
    }
    
    # Map token encoders cho các model khác nhau
    TOKEN_ENCODERS = {}
    
    def __init__(self, cache_dir: str = None):
        """
        Khởi tạo Token Manager
        
        Args:
            cache_dir (str, optional): Thư mục lưu cache
        """
        # Cấu hình logging
        try:
            from utils.logging_utils import get_logger
            self.logger = get_logger("TokenManager")
        except ImportError:
            import logging
            self.logger = logging.getLogger("TokenManager")
        
        # Thiết lập thư mục cache
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data/token_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Theo dõi sử dụng token
        self.token_usage = {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "requests": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "model_usage": {}
        }
        
        # Thời gian giữa các lần lưu thống kê
        self.stats_save_interval = 600  # 10 phút
        self.last_stats_save = time.time()
        
        self.logger.info("Token Manager đã được khởi tạo")
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo-0125") -> int:
        """
        Đếm số lượng token trong text đối với model cụ thể
        
        Args:
            text (str): Văn bản cần đếm token
            model (str): Tên model để sử dụng encoding phù hợp
            
        Returns:
            int: Số lượng token
        """
        # Nếu không có tiktoken, sử dụng ước tính đơn giản
        if not TIKTOKEN_AVAILABLE:
            # Sử dụng heuristic đơn giản để ước tính số token
            # Trung bình 1 token ~ 4 ký tự cho tiếng Anh, 
            # nhưng với tiếng Việt và unicode, tỷ lệ có thể khác
            words = text.split()
            word_count = len(words)
            char_count = len(text)
            
            # Ước tính dựa trên cả số từ và số ký tự
            return max(word_count, char_count // 4)
        
        try:
            # Sử dụng cache để tránh tạo encoder mới mỗi lần
            if model not in TokenManager.TOKEN_ENCODERS:
                # Xác định encoding phù hợp cho model
                if "gpt-4" in model:
                    encoding_name = "cl100k_base"  # GPT-4 models
                elif "gpt-3.5-turbo" in model:
                    encoding_name = "cl100k_base"  # GPT-3.5-turbo models
                else:
                    encoding_name = "cl100k_base"  # Default
                
                # Tạo encoder mới
                TokenManager.TOKEN_ENCODERS[model] = tiktoken.get_encoding(encoding_name)
            
            # Lấy encoder từ cache
            encoder = TokenManager.TOKEN_ENCODERS[model]
            
            # Đếm token
            tokens = len(encoder.encode(text))
            return tokens
        except Exception as e:
            self.logger.warning(f"Lỗi khi đếm token: {str(e)}")
            # Ước tính thô nếu không đếm được chính xác
            return len(text) // 4
    
    def optimize_prompt(self, prompt: str, model: str = "gpt-3.5-turbo-0125", max_tokens: int = 4096) -> str:
        """
        Tối ưu hóa prompt để giảm số lượng token, đảm bảo không vượt quá giới hạn
        
        Args:
            prompt (str): Prompt gốc
            model (str): Model sẽ sử dụng
            max_tokens (int): Số token tối đa cho phép
            
        Returns:
            str: Prompt đã được tối ưu
        """
        # Đếm token hiện tại
        current_tokens = self.count_tokens(prompt, model)
        
        # Nếu đã trong giới hạn, trả về prompt gốc
        if current_tokens <= max_tokens:
            return prompt
        
        self.logger.info(f"Cần tối ưu prompt: {current_tokens} tokens > {max_tokens} max tokens")
        
        # Chia prompt thành các phần
        lines = prompt.split("\n")
        prompt_parts = {"intro": [], "context": [], "html": [], "outro": []}
        
        current_section = "intro"
        html_started = False
        
        # Phân loại các dòng trong prompt
        for line in lines:
            if "```html" in line:
                current_section = "html"
                html_started = True
                prompt_parts[current_section].append(line)
            elif html_started and "```" in line:
                prompt_parts[current_section].append(line)
                current_section = "outro"
                html_started = False
            elif "HTML trang:" in line or "HTML:" in line:
                current_section = "context"
                prompt_parts[current_section].append(line)
            elif current_section == "intro" and "Mô tả phần tử" in line:
                prompt_parts[current_section].append(line)
            elif current_section == "intro" and "Bối cảnh bổ sung" in line:
                prompt_parts[current_section].append(line)
            elif current_section == "outro" and "Chỉ trả lời" in line:
                prompt_parts[current_section].append(line)
            else:
                prompt_parts[current_section].append(line)
        
        # Tạo lại prompt với HTML được cắt bớt
        optimized_prompt = "\n".join(prompt_parts["intro"])
        optimized_prompt += "\n" + "\n".join(prompt_parts["context"]) + "\n"
        
        # Tính toán token còn lại cho HTML
        other_parts_tokens = self.count_tokens(optimized_prompt + "\n" + "\n".join(prompt_parts["outro"]), model)
        html_tokens_available = max_tokens - other_parts_tokens - 100  # Để lại 100 token buffer
        
        if html_tokens_available <= 0:
            # Cắt bớt phần intro và outro nếu cần
            optimized_prompt = "\n".join(prompt_parts["intro"][:3])
            optimized_prompt += "\n" + "\n".join(prompt_parts["context"][:1]) + "\n"
            other_parts_tokens = self.count_tokens(optimized_prompt + "\n" + "\n".join(prompt_parts["outro"][-2:]), model)
            html_tokens_available = max_tokens - other_parts_tokens - 100
        
        # Xử lý HTML
        html_content = "\n".join(prompt_parts["html"])
        html_tokens = self.count_tokens(html_content, model)
        
        if html_tokens > html_tokens_available and html_tokens_available > 0:
            # Cắt bớt HTML để phù hợp với giới hạn token
            html_reduction_ratio = html_tokens_available / html_tokens
            html_content_lines = prompt_parts["html"]
            
            if html_content_lines and len(html_content_lines) > 2:
                # Giữ lại dòng đầu và cuối (```html và ```)
                first_line = html_content_lines[0]
                last_line = html_content_lines[-1]
                
                # Xác định nội dung HTML
                html_body = "\n".join(html_content_lines[1:-1])
                html_body_length = len(html_body)
                
                # Cắt HTML còn khoảng 60% độ dài
                keep_length = int(html_body_length * min(0.6, html_reduction_ratio))
                if keep_length < 100:  # Nếu còn quá ít, cắt còn đoạn đầu và thông báo
                    truncated_html = html_body[:100] + "\n... (HTML has been heavily truncated to fit token limits) ..."
                else:
                    # Lấy 2/3 từ đầu và 1/3 từ cuối
                    start_portion = int(keep_length * 0.67)
                    truncated_html = html_body[:start_portion] + "\n... (HTML truncated) ...\n" + html_body[-(keep_length-start_portion):]
                
                html_content = f"{first_line}\n{truncated_html}\n{last_line}"
        
        # Hoàn thiện prompt
        optimized_prompt += html_content + "\n"
        optimized_prompt += "\n".join(prompt_parts["outro"])
        
        # Kiểm tra lại số token
        final_tokens = self.count_tokens(optimized_prompt, model)
        self.logger.info(f"Prompt sau tối ưu: {final_tokens} tokens (giảm {current_tokens - final_tokens} tokens)")
        
        return optimized_prompt
    
    def cache_api_response(self, prompt: str, model: str, response: Any) -> None:
        """
        Lưu cache kết quả API để tái sử dụng
        
        Args:
            prompt (str): Prompt gốc
            model (str): Model đã sử dụng
            response (Any): Kết quả từ API
        """
        try:
            # Tạo key từ prompt và model
            key = f"{model}_{hashlib.md5(prompt.encode()).hexdigest()}"
            cache_file = self.cache_dir / f"{key}.json"
            
            # Chuyển đổi response object thành dict
            if hasattr(response, 'model_dump'):
                response_data = response.model_dump()
            elif hasattr(response, 'to_dict'):
                response_data = response.to_dict()
            elif hasattr(response, '__dict__'):
                response_data = vars(response)
            else:
                # Thử convert sang JSON strings
                import json
                response_data = json.loads(json.dumps(response, default=str))
            
            # Lưu cache
            cache_data = {
                "timestamp": time.time(),
                "model": model,
                "response": response_data
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)
                
            self.logger.debug(f"Đã lưu cache API response: {cache_file}")
        except Exception as e:
            self.logger.warning(f"Lỗi khi lưu cache API response: {str(e)}")
    
    def get_cached_response(self, prompt: str, model: str, max_age: int = 3600) -> Optional[Dict]:
        """
        Lấy kết quả từ cache nếu có
        
        Args:
            prompt (str): Prompt gốc
            model (str): Model muốn sử dụng
            max_age (int): Thời gian tối đa cache còn hợp lệ (giây)
            
        Returns:
            Optional[Dict]: Kết quả từ cache hoặc None nếu không tìm thấy/hết hạn
        """
        try:
            # Tạo key từ prompt và model
            key = f"{model}_{hashlib.md5(prompt.encode()).hexdigest()}"
            cache_file = self.cache_dir / f"{key}.json"
            
            if not cache_file.exists():
                return None
                
            # Đọc dữ liệu cache
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                
            # Kiểm tra tính hợp lệ của cache
            if time.time() - cache_data.get("timestamp", 0) > max_age:
                return None
            
            # Ghi nhận cache hit
            self.token_usage["cache_hits"] += 1
            
            return cache_data.get("response")
        except Exception as e:
            self.logger.warning(f"Lỗi khi đọc cache API response: {str(e)}")
            return None
    
    def track_token_usage(self, prompt: str, response: Any, model: str) -> None:
        """
        Theo dõi sử dụng token và ước tính chi phí
        
        Args:
            prompt (str): Prompt gốc
            response (Any): Kết quả từ API
            model (str): Model đã sử dụng
        """
        try:
            # Đếm token trong prompt
            prompt_tokens = self.count_tokens(prompt, model)
            
            # Lấy token từ response nếu có
            completion_tokens = 0
            if hasattr(response, 'usage') and hasattr(response.usage, 'completion_tokens'):
                completion_tokens = response.usage.completion_tokens
            elif isinstance(response, dict) and 'usage' in response:
                completion_tokens = response['usage'].get('completion_tokens', 0)
            else:
                # Ước tính từ output
                output_text = ""
                if hasattr(response, 'choices') and response.choices:
                    first_choice = response.choices[0]
                    if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'content'):
                        output_text = first_choice.message.content
                elif isinstance(response, dict) and 'choices' in response:
                    first_choice = response['choices'][0]
                    if isinstance(first_choice, dict) and 'message' in first_choice:
                        output_text = first_choice['message'].get('content', '')
                
                if output_text:
                    completion_tokens = self.count_tokens(output_text, model)
            
            # Tính tổng token
            total_tokens = prompt_tokens + completion_tokens
            
            # Ước tính chi phí
            cost = 0.0
            if model in self.MODEL_PRICE:
                input_cost = (prompt_tokens / 1000) * self.MODEL_PRICE[model]["input"]
                output_cost = (completion_tokens / 1000) * self.MODEL_PRICE[model]["output"]
                cost = input_cost + output_cost
            
            # Cập nhật thống kê
            self.token_usage["total_tokens"] += total_tokens
            self.token_usage["input_tokens"] += prompt_tokens
            self.token_usage["output_tokens"] += completion_tokens
            self.token_usage["estimated_cost"] += cost
            self.token_usage["requests"] += 1
            self.token_usage["api_calls"] += 1
            
            # Cập nhật thống kê theo model
            if model not in self.token_usage["model_usage"]:
                self.token_usage["model_usage"][model] = {
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost": 0.0,
                    "requests": 0
                }
            
            self.token_usage["model_usage"][model]["total_tokens"] += total_tokens
            self.token_usage["model_usage"][model]["input_tokens"] += prompt_tokens
            self.token_usage["model_usage"][model]["output_tokens"] += completion_tokens
            self.token_usage["model_usage"][model]["estimated_cost"] += cost
            self.token_usage["model_usage"][model]["requests"] += 1
            
            # Lưu thống kê theo định kỳ
            if time.time() - self.last_stats_save > self.stats_save_interval:
                self.save_usage_stats()
                self.last_stats_save = time.time()
        except Exception as e:
            self.logger.warning(f"Lỗi khi theo dõi sử dụng token: {str(e)}")
    
    def save_usage_stats(self) -> None:
        """Lưu thống kê sử dụng token"""
        try:
            stats_file = self.cache_dir / "token_usage_stats.json"
            
            # Thêm timestamp
            stats_data = {
                "timestamp": time.time(),
                "stats": self.token_usage
            }
            
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Đã lưu thống kê sử dụng token: {stats_file}")
        except Exception as e:
            self.logger.warning(f"Lỗi khi lưu thống kê sử dụng token: {str(e)}")
    
    def suggest_model(self, prompt: str, context_complexity: str = "medium") -> Tuple[str, int]:
        """
        Gợi ý model phù hợp nhất để tiết kiệm token/chi phí dựa trên độ phức tạp
        
        Args:
            prompt (str): Prompt gốc
            context_complexity (str): Độ phức tạp của ngữ cảnh ("low", "medium", "high")
            
        Returns:
            Tuple[str, int]: (model được gợi ý, max_tokens đề xuất cho output)
        """
        prompt_tokens = self.count_tokens(prompt, "gpt-3.5-turbo-0125")
        
        # Tự động xác định độ phức tạp nếu không được cung cấp
        if context_complexity == "auto":
            if prompt_tokens < 1000:
                context_complexity = "low"
            elif prompt_tokens < 3000:
                context_complexity = "medium"
            else:
                context_complexity = "high"
        
        # Logic để chọn model phù hợp
        if context_complexity == "low":
            if prompt_tokens < 2000:
                return "gpt-3.5-turbo-0125", 150
            else:
                return "gpt-3.5-turbo-0125", 300
        elif context_complexity == "medium":
            if prompt_tokens < 2500:
                return "gpt-3.5-turbo-0125", 400
            else:
                return "gpt-4-turbo", 300
        else:  # high
            if prompt_tokens < 4000:
                return "gpt-4-turbo", 500
            else:
                return "gpt-4-32k", 800
                
    def optimize_selector_query(self, description: str) -> Tuple[str, str, int]:
        """
        Tối ưu hóa query về việc tìm selector để giảm thiểu token
        
        Args:
            description (str): Mô tả phần tử cần tìm
            
        Returns:
            Tuple[str, str, int]: (Prompt tối ưu, model đề xuất, max_tokens đề xuất)
        """
        # Tạo prompt ngắn gọn
        prompt = f"""Find best CSS selector for: "{description}".
Return a single CSS selector or XPath (no explanations, no backticks).
Choose the most specific and reliable selector."""
        
        # Luôn sử dụng model rẻ nhất cho việc tìm selector đơn giản
        model = "gpt-3.5-turbo-0125"
        max_tokens = 50
        
        return prompt, model, max_tokens
    
    def extract_important_elements(self, html_content: str, description: str = None) -> str:
        """
        Trích xuất các phần tử quan trọng từ HTML để giảm token
        
        Args:
            html_content (str): Nội dung HTML đầy đủ
            description (str, optional): Mô tả phần tử cần tìm
            
        Returns:
            str: HTML đã được trích xuất chỉ gồm các phần tử quan trọng
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Danh sách các phần tử quan trọng
            important_elements = []
            
            # 1. Nếu có description, tìm các phần tử có thể phù hợp
            if description:
                desc_lower = description.lower()
                # Tìm các phần tử có text tương tự với description
                matching_elements = soup.find_all(text=lambda text: text and desc_lower in text.lower())
                for text_elem in matching_elements[:5]:  # Giới hạn 5 phần tử
                    parent = text_elem.parent
                    if parent and parent.name:
                        important_elements.append(str(parent))
                
                # Tìm các phần tử có thuộc tính chứa description
                for attr in ["id", "name", "placeholder", "aria-label", "title", "alt"]:
                    for elem in soup.find_all(attrs={attr: lambda x: x and desc_lower in x.lower()}):
                        important_elements.append(str(elem))
                        if len(important_elements) >= 10:
                            break
                    if len(important_elements) >= 10:
                        break
            
            # 2. Lấy các phần tử tương tác quan trọng
            for tag in ["form", "button", "input", "a", "select", "textarea"]:
                for elem in soup.find_all(tag, limit=5):
                    important_elements.append(str(elem))
            
            # 3. Lấy header và các phần tử có cấu trúc
            for tag in ["header", "nav", "footer", "main", "h1", "h2", "h3"]:
                for elem in soup.find_all(tag, limit=3):
                    important_elements.append(str(elem))
            
            # Tạo HTML mới chỉ với các phần tử quan trọng
            head_content = soup.head.prettify() if soup.head else ""
            body_start = "<body>"
            body_end = "</body>"
            extracted_content = f"{head_content}\n{body_start}\n"
            
            # Thêm các phần tử quan trọng
            seen = set()  # Tránh trùng lặp
            for elem in important_elements:
                if elem not in seen:
                    extracted_content += elem + "\n"
                    seen.add(elem)
            
            extracted_content += f"{body_end}"
            
            return extracted_content
        except Exception as e:
            self.logger.warning(f"Lỗi khi trích xuất phần tử quan trọng: {str(e)}")
            # Trả về HTML ban đầu nếu có lỗi
            return html_content
